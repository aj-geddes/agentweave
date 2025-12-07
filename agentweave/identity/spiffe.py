"""SPIFFE-based identity provider implementation.

This module implements identity management using the SPIFFE Workload API,
typically provided by a SPIRE agent. It handles automatic SVID fetching,
caching, rotation, and trust bundle management.
"""

import asyncio
import logging
import os
import ssl
import tempfile
from pathlib import Path
from typing import Optional, Dict, Callable, Awaitable

from spiffe import X509Svid, X509Bundle, WorkloadApiClient
from spiffe.errors import SpiffeError

from .base import IdentityProvider, IdentityError, TrustDomainError, ConnectionError as IdentityConnectionError


logger = logging.getLogger(__name__)


class SPIFFEIdentityProvider(IdentityProvider):
    """SPIFFE Workload API-based identity provider.

    This provider connects to a SPIRE agent (or other SPIFFE Workload API
    implementation) to obtain X.509 SVIDs for workload identity. It handles:
    - Automatic SVID fetching and caching
    - Certificate rotation with callbacks
    - Trust bundle management for multiple trust domains
    - mTLS SSL context creation

    The provider will automatically watch for SVID updates and invoke
    registered callbacks when rotation occurs.

    Example:
        >>> provider = SPIFFEIdentityProvider()
        >>> await provider.initialize()
        >>> svid = await provider.get_svid()
        >>> print(svid.spiffe_id)
        spiffe://agentweave.io/agent/my-agent/prod
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        tls_min_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_3,
    ):
        """Initialize the SPIFFE identity provider.

        Args:
            endpoint: The SPIFFE Workload API endpoint. If None, will use
                     the SPIFFE_ENDPOINT_SOCKET environment variable, or
                     default to unix:///run/spire/sockets/agent.sock
            tls_min_version: Minimum TLS version for SSL contexts.
                            Defaults to TLS 1.3.
        """
        self._endpoint = endpoint or os.environ.get(
            "SPIFFE_ENDPOINT_SOCKET",
            "unix:///run/spire/sockets/agent.sock"
        )
        self._tls_min_version = tls_min_version
        self._client: Optional[WorkloadApiClient] = None
        self._svid_cache: Optional[X509Svid] = None
        self._bundle_cache: Dict[str, X509Bundle] = {}
        self._rotation_callbacks: list[Callable[[X509Svid], Awaitable[None]]] = []
        self._watch_task: Optional[asyncio.Task] = None
        self._initialized = False
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None

        logger.info(f"SPIFFE identity provider configured with endpoint: {self._endpoint}")

    async def initialize(self) -> None:
        """Initialize the connection to the SPIFFE Workload API.

        This method must be called before using the provider. It establishes
        the connection to the SPIRE agent and fetches the initial SVID.

        Raises:
            IdentityConnectionError: If connection to Workload API fails
            IdentityError: If initial SVID cannot be fetched
        """
        if self._initialized:
            logger.warning("SPIFFE identity provider already initialized")
            return

        try:
            logger.info("Initializing SPIFFE identity provider")
            self._client = WorkloadApiClient(self._endpoint)

            # Create temporary directory for certificate files
            self._temp_dir = tempfile.TemporaryDirectory(prefix="agentweave_svid_")

            # Fetch initial SVID
            await self._fetch_svid()

            # Start watching for updates
            self._watch_task = asyncio.create_task(self._watch_svid_updates())

            self._initialized = True
            logger.info(f"SPIFFE identity provider initialized with ID: {self._svid_cache.spiffe_id}")

        except SpiffeError as e:
            logger.error(f"Failed to connect to SPIFFE Workload API: {e}")
            raise IdentityConnectionError(
                f"Cannot connect to SPIFFE Workload API at {self._endpoint}: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Failed to initialize SPIFFE identity provider: {e}")
            raise IdentityError(f"Failed to initialize identity provider: {e}") from e

    async def shutdown(self) -> None:
        """Shutdown the identity provider and cleanup resources.

        This cancels the SVID watch task and cleans up temporary files.
        """
        logger.info("Shutting down SPIFFE identity provider")

        if self._watch_task:
            self._watch_task.cancel()
            try:
                await self._watch_task
            except asyncio.CancelledError:
                pass

        if self._client:
            self._client.close()

        if self._temp_dir:
            try:
                self._temp_dir.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up temporary directory: {e}")

        self._initialized = False
        logger.info("SPIFFE identity provider shutdown complete")

    async def get_identity(self) -> str:
        """Get the SPIFFE ID of this workload.

        Returns:
            str: The SPIFFE ID in the format spiffe://trust-domain/path

        Raises:
            IdentityError: If identity cannot be determined
        """
        self._ensure_initialized()

        if not self._svid_cache:
            await self._fetch_svid()

        return str(self._svid_cache.spiffe_id)

    async def get_svid(self) -> X509Svid:
        """Get the current X.509 SVID for this workload.

        Returns a cached SVID if available, or fetches a new one.
        The SVID is automatically rotated when it approaches expiration.

        Returns:
            X509Svid: The X.509 SVID containing certificate and private key

        Raises:
            IdentityError: If SVID cannot be obtained
        """
        self._ensure_initialized()

        if not self._svid_cache:
            await self._fetch_svid()

        return self._svid_cache

    async def get_trust_bundle(self, trust_domain: Optional[str] = None) -> X509Bundle:
        """Get the trust bundle for verifying peer SVIDs.

        Args:
            trust_domain: The trust domain to get the bundle for.
                         If None, returns the bundle for this workload's trust domain.

        Returns:
            X509Bundle: The trust bundle containing CA certificates

        Raises:
            IdentityError: If trust bundle cannot be obtained
            TrustDomainError: If the trust domain is not recognized
        """
        self._ensure_initialized()

        # If no trust domain specified, use our own
        if trust_domain is None:
            svid = await self.get_svid()
            trust_domain = svid.spiffe_id.trust_domain

        # Check cache first
        if trust_domain in self._bundle_cache:
            return self._bundle_cache[trust_domain]

        # Fetch bundles from Workload API
        try:
            bundles = await asyncio.to_thread(self._client.fetch_x509_bundles)
            self._bundle_cache.update(bundles)

            if trust_domain not in self._bundle_cache:
                raise TrustDomainError(
                    f"Trust domain '{trust_domain}' not found in available bundles. "
                    f"Available: {list(bundles.keys())}"
                )

            logger.debug(f"Fetched trust bundle for domain: {trust_domain}")
            return self._bundle_cache[trust_domain]

        except SpiffeError as e:
            logger.error(f"Failed to fetch trust bundles: {e}")
            raise IdentityError(f"Cannot fetch trust bundles: {e}") from e

    async def create_tls_context(self, server: bool = False) -> ssl.SSLContext:
        """Create an SSL context configured for mTLS.

        The context is configured with:
        - Current SVID certificate and private key
        - Trust bundle for peer verification
        - TLS 1.3 minimum version (configurable)
        - Mutual authentication enabled
        - Hostname checking disabled (SPIFFE uses SPIFFE ID verification)

        Args:
            server: If True, create a server-side SSL context.
                   If False (default), create a client-side context.

        Returns:
            ssl.SSLContext: Configured SSL context ready for use

        Raises:
            IdentityError: If SSL context cannot be created
        """
        self._ensure_initialized()

        try:
            # Get current SVID and trust bundle
            svid = await self.get_svid()
            bundle = await self.get_trust_bundle()

            # Write SVID to temporary files
            cert_path, key_path = self._write_svid_to_files(svid)
            bundle_path = self._write_bundle_to_file(bundle)

            # Create SSL context
            if server:
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            else:
                ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)

            # Configure TLS version
            ctx.minimum_version = self._tls_min_version

            # Require mutual authentication
            ctx.verify_mode = ssl.CERT_REQUIRED

            # SPIFFE uses SPIFFE ID verification, not hostname
            ctx.check_hostname = False

            # Load our certificate and key
            ctx.load_cert_chain(certfile=cert_path, keyfile=key_path)

            # Load trust bundle for peer verification
            ctx.load_verify_locations(cafile=bundle_path)

            logger.debug(f"Created {'server' if server else 'client'} SSL context with TLS {self._tls_min_version.name}")
            return ctx

        except Exception as e:
            logger.error(f"Failed to create TLS context: {e}")
            raise IdentityError(f"Cannot create TLS context: {e}") from e

    def register_rotation_callback(
        self,
        callback: Callable[[X509Svid], Awaitable[None]]
    ) -> None:
        """Register a callback to be invoked when SVID rotates.

        The callback will be called with the new SVID whenever automatic
        rotation occurs. This is useful for updating SSL contexts or
        notifying other components.

        Args:
            callback: Async function that takes an X509Svid parameter
        """
        self._rotation_callbacks.append(callback)
        logger.debug(f"Registered SVID rotation callback: {callback.__name__}")

    async def _fetch_svid(self) -> None:
        """Fetch a new SVID from the Workload API."""
        try:
            logger.debug("Fetching X.509 SVID from Workload API")
            svid = await asyncio.to_thread(self._client.fetch_x509_svid)
            self._svid_cache = svid
            logger.info(f"Fetched SVID: {svid.spiffe_id}, expires: {svid.leaf.not_valid_after_utc}")
        except SpiffeError as e:
            logger.error(f"Failed to fetch SVID: {e}")
            raise IdentityError(f"Cannot fetch SVID: {e}") from e

    async def _watch_svid_updates(self) -> None:
        """Watch for SVID updates and invoke rotation callbacks.

        This runs in the background and automatically updates the cached
        SVID when the Workload API provides a new one.
        """
        logger.info("Starting SVID update watcher")

        try:
            while True:
                try:
                    # The py-spiffe library doesn't have built-in async watching,
                    # so we poll periodically. In production, this would ideally
                    # use the streaming watch API if available.
                    await asyncio.sleep(30)  # Check every 30 seconds

                    # Fetch latest SVID
                    old_svid = self._svid_cache
                    await self._fetch_svid()

                    # If SVID changed, invoke callbacks
                    if old_svid and self._svid_cache and old_svid != self._svid_cache:
                        logger.info("SVID rotated, invoking callbacks")
                        for callback in self._rotation_callbacks:
                            try:
                                await callback(self._svid_cache)
                            except Exception as e:
                                logger.error(f"Error in rotation callback {callback.__name__}: {e}")

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.error(f"Error watching SVID updates: {e}")
                    # Continue watching even if there's an error
                    await asyncio.sleep(10)

        except asyncio.CancelledError:
            logger.info("SVID update watcher cancelled")

    def _write_svid_to_files(self, svid: X509Svid) -> tuple[str, str]:
        """Write SVID certificate and key to temporary files.

        Args:
            svid: The X.509 SVID to write

        Returns:
            tuple: (cert_path, key_path)
        """
        cert_path = Path(self._temp_dir.name) / "cert.pem"
        key_path = Path(self._temp_dir.name) / "key.pem"

        # Write certificate chain
        cert_path.write_bytes(svid.cert_chain_bytes)

        # Write private key
        key_path.write_bytes(svid.private_key_bytes)

        # Secure the key file
        os.chmod(key_path, 0o600)

        return str(cert_path), str(key_path)

    def _write_bundle_to_file(self, bundle: X509Bundle) -> str:
        """Write trust bundle to temporary file.

        Args:
            bundle: The X.509 bundle to write

        Returns:
            str: Path to the bundle file
        """
        bundle_path = Path(self._temp_dir.name) / "bundle.pem"
        bundle_path.write_bytes(bundle.x509_authorities_bytes)
        return str(bundle_path)

    def _ensure_initialized(self) -> None:
        """Ensure the provider has been initialized.

        Raises:
            IdentityError: If the provider is not initialized
        """
        if not self._initialized:
            raise IdentityError(
                "SPIFFE identity provider not initialized. "
                "Call initialize() before using the provider."
            )

    async def health_check(self) -> bool:
        """Check if the identity provider is healthy.

        Returns:
            bool: True if healthy, False otherwise
        """
        if not self._initialized:
            logger.warning("Health check failed: provider not initialized")
            return False

        try:
            await self.get_identity()
            await self.get_svid()
            await self.get_trust_bundle()
            logger.debug("Health check passed")
            return True
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False

    def __del__(self):
        """Cleanup on deletion."""
        if self._temp_dir:
            try:
                self._temp_dir.cleanup()
            except Exception:
                pass
