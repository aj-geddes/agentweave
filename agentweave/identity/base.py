"""Abstract base class for identity providers.

This module defines the interface that all identity providers must implement
to provide cryptographic identity for agents in the AgentWeave SDK.
"""

from abc import ABC, abstractmethod
import ssl
from typing import Optional

from spiffe import X509Svid, X509Bundle


class IdentityProvider(ABC):
    """Abstract base class for identity providers.

    Identity providers are responsible for:
    - Obtaining and maintaining cryptographic identity (SVIDs)
    - Managing trust bundles for peer verification
    - Creating TLS contexts for secure communication
    - Handling certificate rotation
    """

    @abstractmethod
    async def get_identity(self) -> str:
        """Get the SPIFFE ID of this workload.

        Returns:
            str: The SPIFFE ID in the format spiffe://trust-domain/path

        Raises:
            IdentityError: If identity cannot be determined
        """
        ...

    @abstractmethod
    async def get_svid(self) -> X509Svid:
        """Get the current X.509 SVID for this workload.

        This method should return a cached SVID if available and valid,
        or fetch a new one if needed. The SVID contains the certificate
        chain and private key needed for mTLS.

        Returns:
            X509Svid: The X.509 SVID containing certificate and private key

        Raises:
            IdentityError: If SVID cannot be obtained
        """
        ...

    @abstractmethod
    async def get_trust_bundle(self, trust_domain: Optional[str] = None) -> X509Bundle:
        """Get the trust bundle for verifying peer SVIDs.

        The trust bundle contains the CA certificates needed to verify
        SVIDs from peers in the specified trust domain.

        Args:
            trust_domain: The trust domain to get the bundle for.
                         If None, returns the bundle for this workload's trust domain.

        Returns:
            X509Bundle: The trust bundle containing CA certificates

        Raises:
            IdentityError: If trust bundle cannot be obtained
            TrustDomainError: If the trust domain is not recognized
        """
        ...

    @abstractmethod
    async def create_tls_context(self, server: bool = False) -> ssl.SSLContext:
        """Create an SSL context configured for mTLS.

        The SSL context will be configured with:
        - Current SVID certificate and private key
        - Trust bundle for peer verification
        - TLS 1.3 minimum version (or as configured)
        - Mutual authentication enabled

        Args:
            server: If True, create a server-side SSL context.
                   If False (default), create a client-side context.

        Returns:
            ssl.SSLContext: Configured SSL context ready for use

        Raises:
            IdentityError: If SSL context cannot be created
        """
        ...

    async def health_check(self) -> bool:
        """Check if the identity provider is healthy.

        This method verifies that the provider can obtain identity
        and trust bundles. It's useful for readiness probes.

        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            await self.get_identity()
            await self.get_svid()
            await self.get_trust_bundle()
            return True
        except Exception:
            return False


class IdentityError(Exception):
    """Base exception for identity-related errors."""
    pass


class TrustDomainError(IdentityError):
    """Exception raised when a trust domain is not recognized or trusted."""
    pass


class SVIDExpiredError(IdentityError):
    """Exception raised when an SVID has expired and cannot be renewed."""
    pass


class ConnectionError(IdentityError):
    """Exception raised when connection to identity provider fails."""
    pass
