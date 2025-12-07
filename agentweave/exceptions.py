"""
Custom exceptions for the AgentWeave SDK.

All exceptions inherit from AgentWeaveError for easy catching of SDK-specific errors.
These exceptions are used throughout the SDK to provide clear error messages and
enable proper error handling in agent implementations.
"""

from typing import Optional


class AgentWeaveError(Exception):
    """
    Base exception for all AgentWeave SDK errors.

    All SDK exceptions inherit from this class, allowing users to catch
    any SDK-specific error with a single exception handler.
    """

    def __init__(self, message: str, details: Optional[dict] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} ({details_str})"
        return self.message


class IdentityError(AgentWeaveError):
    """
    Raised when there are issues with identity management.

    This includes:
    - Failed SVID acquisition
    - SVID rotation failures
    - Trust bundle retrieval errors
    - SPIFFE Workload API connection issues
    - Invalid SPIFFE IDs

    Examples:
        - Cannot connect to SPIRE agent socket
        - SVID has expired and rotation failed
        - Trust domain not in allowed list
        - Invalid SPIFFE ID format
    """

    pass


class AuthorizationError(AgentWeaveError):
    """
    Raised when authorization checks fail.

    This includes:
    - OPA policy denials
    - Invalid policy evaluations
    - OPA connection failures
    - Missing required permissions

    Examples:
        - Caller not authorized to invoke this capability
        - OPA policy denied the request
        - Cannot connect to OPA endpoint
        - Policy evaluation timeout

    Note:
        This is different from authentication (identity verification).
        Authorization happens after identity is verified.
    """

    pass


class TransportError(AgentWeaveError):
    """
    Raised when there are issues with the transport layer.

    This includes:
    - mTLS connection failures
    - Peer verification failures
    - TLS version/cipher mismatches
    - Network connectivity issues
    - Circuit breaker activations
    - Connection pool exhaustion

    Examples:
        - Peer SPIFFE ID does not match expected
        - TLS handshake failed
        - Peer certificate verification failed
        - Connection timeout
        - Circuit breaker is open
    """

    pass


class ConfigurationError(AgentWeaveError):
    """
    Raised when there are issues with agent configuration.

    This includes:
    - Invalid configuration files
    - Validation failures
    - Missing required fields
    - Insecure configuration in production
    - Invalid YAML/environment variables

    Examples:
        - default_action must be 'deny' in production
        - peer_verification cannot be 'none'
        - Invalid trust domain format
        - Missing required configuration field
        - TLS version below minimum

    Note:
        Configuration errors are typically caught at startup, preventing
        the agent from running with insecure settings.
    """

    pass


class A2AProtocolError(AgentWeaveError):
    """
    Raised when there are issues with A2A protocol communication.

    This includes:
    - Invalid Agent Card format
    - Task lifecycle violations
    - Protocol version mismatches
    - Invalid message structure
    - Discovery endpoint failures

    Examples:
        - Agent Card missing required fields
        - Task state transition not allowed
        - Unsupported A2A protocol version
        - Malformed JSON-RPC request
        - Discovery endpoint returned invalid data

    Note:
        This is separate from TransportError (connection issues) and
        AuthorizationError (permission issues). This focuses on the
        A2A protocol layer specifically.
    """

    pass


class PeerVerificationError(TransportError):
    """
    Raised when peer identity verification fails.

    This is a specific type of TransportError that occurs when the
    peer's SPIFFE ID does not match expectations or cannot be verified.

    Examples:
        - Expected spiffe://agentweave.io/agent/search, got spiffe://evil.com/agent/fake
        - Cannot extract SPIFFE ID from peer certificate
        - Peer certificate chain validation failed
    """

    pass


class PolicyEvaluationError(AuthorizationError):
    """
    Raised when OPA policy evaluation fails.

    This is a specific type of AuthorizationError that occurs when
    there are technical issues evaluating the policy (not policy denials).

    Examples:
        - OPA returned malformed response
        - Policy evaluation timeout
        - OPA server error (500)
        - Invalid policy input document
    """

    pass


class SVIDError(IdentityError):
    """
    Raised when there are issues with SVIDs.

    This is a specific type of IdentityError focused on SVID operations.

    Examples:
        - SVID has expired
        - Cannot parse SVID certificate
        - SVID rotation failed
        - Private key mismatch
    """

    pass
