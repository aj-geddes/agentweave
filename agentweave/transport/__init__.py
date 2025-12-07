"""
AgentWeave SDK - Transport Layer

This module provides secure transport components with mandatory mTLS authentication.

Components:
    - SecureChannel: mTLS-enforced HTTP client with SPIFFE verification
    - ConnectionPool: Connection pooling with health checking
    - CircuitBreaker: Circuit breaker pattern for fault tolerance
    - RetryPolicy: Exponential backoff retry logic

Security guarantees:
    - Mutual TLS authentication is MANDATORY (cannot be disabled)
    - SPIFFE ID verification on all connections
    - TLS 1.3 preferred, 1.2 minimum enforcement
    - Automatic certificate rotation support
    - Full audit logging of all connections

Example:
    from agentweave.transport import SecureChannel, TransportConfig

    config = TransportConfig(tls_min_version=ssl.TLSVersion.TLSv1_3)
    channel = SecureChannel(
        identity_provider=identity,
        peer_spiffe_id="spiffe://example.com/service",
        config=config
    )

    async with channel:
        response = await channel.get("https://service.example.com/api")
"""

from .channel import (
    SecureChannel,
    TransportConfig,
    PeerVerificationError,
    IdentityProvider,
)

from .pool import (
    ConnectionPool,
    PoolConfig,
    PooledConnection,
    PooledChannelContext,
    ConnectionPoolError,
    PoolExhaustedError,
)

from .circuit import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerMetrics,
    CircuitBreakerRegistry,
    CircuitState,
    CircuitOpenError,
)

from .retry import (
    RetryPolicy,
    RetryConfig,
    with_retry,
)

__all__ = [
    # Channel
    "SecureChannel",
    "TransportConfig",
    "PeerVerificationError",
    "IdentityProvider",

    # Pool
    "ConnectionPool",
    "PoolConfig",
    "PooledConnection",
    "PooledChannelContext",
    "ConnectionPoolError",
    "PoolExhaustedError",

    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerMetrics",
    "CircuitBreakerRegistry",
    "CircuitState",
    "CircuitOpenError",

    # Retry
    "RetryPolicy",
    "RetryConfig",
    "with_retry",
]

__version__ = "1.0.0"
