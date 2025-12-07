"""Static mTLS identity provider for development and testing.

This module provides a fallback identity provider that uses static certificate
files instead of connecting to a SPIFFE Workload API. It's intended for:
- Local development without SPIRE infrastructure
- Testing scenarios
- Legacy systems that use static certificates

WARNING: This provider does NOT support automatic certificate rotation.
It should only be used in development/testing environments.
"""

import logging
import os
import ssl
from pathlib import Path
from typing import Optional

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from spiffe import X509Svid, X509Bundle, SpiffeId

from .base import IdentityProvider, IdentityError, TrustDomainError


logger = logging.getLogger(__name__)


class StaticMTLSProvider(IdentityProvider):
    """Static mTLS identity provider using file-based certificates.

    This provider loads certificates and keys from files and uses them
    for mTLS authentication. Unlike the SPIFFE provider, it does not
    support automatic rotation or dynamic trust bundles.

    Example:
        >>> provider = StaticMTLSProvider(
        ...     cert_path="/etc/certs/agent.crt",
        ...     key_path="/etc/certs/agent.key",
        ...     ca_bundle_path="/etc/certs/ca.crt",
        ...     spiffe_id="spiffe://agentweave.io/agent/test"
        ... )
        >>> await provider.initialize()
        >>> svid = await provider.get_svid()
    """

    def __init__(
        self,
        cert_path: str,
        key_path: str,
        ca_bundle_path: str,
        spiffe_id: str,
        tls_min_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_3,
    ):
        """Initialize the static mTLS provider.

        Args:
            cert_path: Path to the certificate file (PEM format)
            key_path: Path to the private key file (PEM format)
            ca_bundle_path: Path to the CA bundle for peer verification (PEM format)
            spiffe_id: The SPIFFE ID to associate with this certificate
            tls_min_version: Minimum TLS version for SSL contexts.
                            Defaults to TLS 1.3.

        Raises:
            ValueError: If any of the required paths are invalid
        """
        self._cert_path = Path(cert_path)
        self._key_path = Path(key_path)
        self._ca_bundle_path = Path(ca_bundle_path)
        self._spiffe_id = SpiffeId.parse(spiffe_id)
        self._tls_min_version = tls_min_version

        self._svid: Optional[X509Svid] = None
        self._bundle: Optional[X509Bundle] = None
        self._initialized = False

        logger.warning(
            "Using StaticMTLSProvider - this is NOT recommended for production. "
            "Use SPIFFEIdentityProvider for automatic rotation and better security."
        )

    async def initialize(self) -> None:
        """Initialize the provider by loading certificates from files.

        Raises:
            IdentityError: If certificates cannot be loaded or are invalid
        """
        if self._initialized:
            logger.warning("StaticMTLSProvider already initialized")
            return

        try:
            logger.info("Initializing static mTLS provider")

            # Validate file paths
            self._validate_file_paths()

            # Load certificate
            cert_bytes = self._cert_path.read_bytes()
            cert = x509.load_pem_x509_certificate(cert_bytes, default_backend())

            # Load private key
            key_bytes = self._key_path.read_bytes()
            private_key = serialization.load_pem_private_key(
                key_bytes,
                password=None,
                backend=default_backend()
            )

            # Create X509Svid
            self._svid = X509Svid(
                spiffe_id=self._spiffe_id,
                cert_chain=[cert],
                private_key=private_key
            )

            # Load CA bundle
            ca_bundle_bytes = self._ca_bundle_path.read_bytes()
            self._bundle = X509Bundle.parse_raw(
                self._spiffe_id.trust_domain,
                ca_bundle_bytes
            )

            self._initialized = True
            logger.info(f"Static mTLS provider initialized with ID: {self._spiffe_id}")

        except FileNotFoundError as e:
            logger.error(f"Certificate file not found: {e}")
            raise IdentityError(f"Certificate file not found: {e}") from e
        except Exception as e:
            logger.error(f"Failed to initialize static mTLS provider: {e}")
            raise IdentityError(f"Failed to load certificates: {e}") from e

    async def shutdown(self) -> None:
        """Shutdown the provider.

        For static provider, this is a no-op as there are no connections to close.
        """
        logger.info("Shutting down static mTLS provider")
        self._initialized = False

    async def get_identity(self) -> str:
        """Get the SPIFFE ID of this workload.

        Returns:
            str: The SPIFFE ID in the format spiffe://trust-domain/path

        Raises:
            IdentityError: If identity cannot be determined
        """
        self._ensure_initialized()
        return str(self._spiffe_id)

    async def get_svid(self) -> X509Svid:
        """Get the X.509 SVID for this workload.

        Returns the static SVID loaded from files. This does NOT rotate.

        Returns:
            X509Svid: The X.509 SVID containing certificate and private key

        Raises:
            IdentityError: If SVID is not available
        """
        self._ensure_initialized()

        # Check if certificate is expired
        if self._svid.leaf.not_valid_after_utc < self._svid.leaf.not_valid_after_utc:
            logger.warning(
                f"Certificate has expired: {self._svid.leaf.not_valid_after_utc}. "
                "Update certificate files and restart the agent."
            )

        return self._svid

    async def get_trust_bundle(self, trust_domain: Optional[str] = None) -> X509Bundle:
        """Get the trust bundle for verifying peer SVIDs.

        Args:
            trust_domain: The trust domain to get the bundle for.
                         If None, returns the bundle for this workload's trust domain.

        Returns:
            X509Bundle: The trust bundle containing CA certificates

        Raises:
            IdentityError: If trust bundle cannot be obtained
            TrustDomainError: If the requested trust domain doesn't match
        """
        self._ensure_initialized()

        # If no trust domain specified, use our own
        if trust_domain is None:
            trust_domain = self._spiffe_id.trust_domain

        # Check if requested trust domain matches
        if trust_domain != self._spiffe_id.trust_domain:
            raise TrustDomainError(
                f"Trust domain '{trust_domain}' not available. "
                f"This provider only supports '{self._spiffe_id.trust_domain}'. "
                "Use SPIFFEIdentityProvider for federated trust domains."
            )

        return self._bundle

    async def create_tls_context(self, server: bool = False) -> ssl.SSLContext:
        """Create an SSL context configured for mTLS.

        The context is configured with:
        - Static certificate and private key from files
        - CA bundle for peer verification
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
            ctx.load_cert_chain(
                certfile=str(self._cert_path),
                keyfile=str(self._key_path)
            )

            # Load CA bundle for peer verification
            ctx.load_verify_locations(cafile=str(self._ca_bundle_path))

            logger.debug(f"Created {'server' if server else 'client'} SSL context with TLS {self._tls_min_version.name}")
            return ctx

        except Exception as e:
            logger.error(f"Failed to create TLS context: {e}")
            raise IdentityError(f"Cannot create TLS context: {e}") from e

    def _validate_file_paths(self) -> None:
        """Validate that all required certificate files exist.

        Raises:
            IdentityError: If any required file is missing
        """
        missing_files = []

        if not self._cert_path.exists():
            missing_files.append(str(self._cert_path))
        if not self._key_path.exists():
            missing_files.append(str(self._key_path))
        if not self._ca_bundle_path.exists():
            missing_files.append(str(self._ca_bundle_path))

        if missing_files:
            raise IdentityError(
                f"Certificate files not found: {', '.join(missing_files)}"
            )

        # Verify key file permissions
        key_mode = self._key_path.stat().st_mode
        if key_mode & 0o077:  # Check if group/other have any permissions
            logger.warning(
                f"Private key file {self._key_path} has overly permissive permissions. "
                "Recommend chmod 600 for security."
            )

    def _ensure_initialized(self) -> None:
        """Ensure the provider has been initialized.

        Raises:
            IdentityError: If the provider is not initialized
        """
        if not self._initialized:
            raise IdentityError(
                "Static mTLS provider not initialized. "
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
            # Check if certificate files still exist
            self._validate_file_paths()

            # Check if certificate is not expired
            svid = await self.get_svid()
            if svid.leaf.not_valid_after_utc < svid.leaf.not_valid_after_utc:
                logger.error("Health check failed: certificate expired")
                return False

            logger.debug("Health check passed")
            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False


class EnvironmentMTLSProvider(StaticMTLSProvider):
    """Static mTLS provider that reads paths from environment variables.

    This is a convenience wrapper around StaticMTLSProvider that reads
    certificate paths from environment variables instead of constructor args.

    Required environment variables:
    - AGENTWEAVE_CERT_PATH: Path to certificate file
    - AGENTWEAVE_KEY_PATH: Path to private key file
    - AGENTWEAVE_CA_BUNDLE_PATH: Path to CA bundle
    - AGENTWEAVE_SPIFFE_ID: SPIFFE ID for this workload

    Example:
        >>> provider = EnvironmentMTLSProvider()
        >>> await provider.initialize()
    """

    def __init__(self, tls_min_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_3):
        """Initialize provider from environment variables.

        Args:
            tls_min_version: Minimum TLS version for SSL contexts

        Raises:
            ValueError: If required environment variables are not set
        """
        cert_path = os.environ.get("AGENTWEAVE_CERT_PATH")
        key_path = os.environ.get("AGENTWEAVE_KEY_PATH")
        ca_bundle_path = os.environ.get("AGENTWEAVE_CA_BUNDLE_PATH")
        spiffe_id = os.environ.get("AGENTWEAVE_SPIFFE_ID")

        missing_vars = []
        if not cert_path:
            missing_vars.append("AGENTWEAVE_CERT_PATH")
        if not key_path:
            missing_vars.append("AGENTWEAVE_KEY_PATH")
        if not ca_bundle_path:
            missing_vars.append("AGENTWEAVE_CA_BUNDLE_PATH")
        if not spiffe_id:
            missing_vars.append("AGENTWEAVE_SPIFFE_ID")

        if missing_vars:
            raise ValueError(
                f"Required environment variables not set: {', '.join(missing_vars)}"
            )

        super().__init__(
            cert_path=cert_path,
            key_path=key_path,
            ca_bundle_path=ca_bundle_path,
            spiffe_id=spiffe_id,
            tls_min_version=tls_min_version,
        )

        logger.info("Initialized environment-based mTLS provider")
