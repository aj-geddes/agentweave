"""
Base authorization provider interface for AgentWeave SDK.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import uuid


@dataclass(frozen=True)
class AuthzDecision:
    """
    Authorization decision result.

    Attributes:
        allowed: Whether the action is permitted
        reason: Human-readable explanation for the decision
        policy_id: ID of the policy that made the decision (if applicable)
        audit_id: Unique identifier for audit trail correlation
    """
    allowed: bool
    reason: str
    policy_id: Optional[str] = None
    audit_id: str = ""

    def __post_init__(self):
        # Generate audit_id if not provided
        if not self.audit_id:
            object.__setattr__(self, 'audit_id', str(uuid.uuid4()))


class AuthorizationProvider(ABC):
    """
    Abstract base class for authorization providers.

    Implementations must enforce fine-grained access control based on:
    - Caller identity (SPIFFE ID)
    - Resource being accessed
    - Action being performed
    - Additional context (request metadata, environment, etc.)
    """

    @abstractmethod
    async def check(
        self,
        caller_id: str,
        resource: str,
        action: str,
        context: Optional[dict] = None
    ) -> AuthzDecision:
        """
        Check if a caller is authorized to perform an action on a resource.

        Args:
            caller_id: SPIFFE ID of the caller
            resource: Resource being accessed (e.g., SPIFFE ID of target agent)
            action: Action being performed (e.g., "search", "process")
            context: Additional context for policy evaluation

        Returns:
            AuthzDecision with the authorization result

        Raises:
            AuthorizationError: If the authorization check fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the authorization provider is healthy and reachable.

        Returns:
            True if healthy, False otherwise
        """
        pass
