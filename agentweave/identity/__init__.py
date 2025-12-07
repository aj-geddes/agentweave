"""Identity management for AgentWeave SDK.

This package provides identity providers for cryptographic workload identity
using SPIFFE/SPIRE or static mTLS certificates.

The identity layer is responsible for:
- Obtaining and maintaining cryptographic identity (SVIDs)
- Managing trust bundles for peer verification
- Creating TLS contexts for secure communication
- Handling certificate rotation

Example usage with SPIFFE:
    >>> from agentweave.identity import SPIFFEIdentityProvider
    >>>
    >>> provider = SPIFFEIdentityProvider()
    >>> await provider.initialize()
    >>>
    >>> # Get identity
    >>> identity = await provider.get_identity()
    >>> print(identity)  # spiffe://agentweave.io/agent/my-agent
    >>>
    >>> # Create mTLS context
    >>> ssl_context = await provider.create_tls_context()

Example usage with static certificates:
    >>> from agentweave.identity import StaticMTLSProvider
    >>>
    >>> provider = StaticMTLSProvider(
    ...     cert_path="/etc/certs/agent.crt",
    ...     key_path="/etc/certs/agent.key",
    ...     ca_bundle_path="/etc/certs/ca.crt",
    ...     spiffe_id="spiffe://agentweave.io/agent/test"
    ... )
    >>> await provider.initialize()
"""

from .base import (
    IdentityProvider,
    IdentityError,
    TrustDomainError,
    SVIDExpiredError,
    ConnectionError,
)
from .spiffe import SPIFFEIdentityProvider
from .mtls import StaticMTLSProvider, EnvironmentMTLSProvider


__all__ = [
    # Base classes and interfaces
    "IdentityProvider",

    # Exceptions
    "IdentityError",
    "TrustDomainError",
    "SVIDExpiredError",
    "ConnectionError",

    # SPIFFE provider
    "SPIFFEIdentityProvider",

    # Static mTLS providers
    "StaticMTLSProvider",
    "EnvironmentMTLSProvider",
]
