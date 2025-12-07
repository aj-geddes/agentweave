"""
AgentWeave SDK - Authorization Layer

This module provides authorization enforcement for secure agent-to-agent communication.
"""

from agentweave.authz.base import (
    AuthorizationProvider,
    AuthzDecision,
)
from agentweave.authz.opa import OPAProvider

__all__ = [
    "AuthorizationProvider",
    "AuthzDecision",
    "OPAProvider",
]
