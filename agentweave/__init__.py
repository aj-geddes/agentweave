"""
AgentWeave SDK

A Python library for building cross-cloud AI agents with hardened security by default.
The SDK combines SPIFFE/SPIRE for cryptographic workload identity, A2A Protocol for
standardized agent-to-agent communication, and OPA for fine-grained authorization.

Design Principle: "The secure path is the only path"
- No agent can start without verified identity
- No communication without mutual TLS authentication
- No request without authorization check
- All security decisions are SDK-internal, not developer-facing

Example:
    from agentweave import SecureAgent, capability

    class MyAgent(SecureAgent):
        @capability("process_data")
        async def process(self, data: dict) -> TaskResult:
            return await self._process(data)
"""

__version__ = "1.0.0"
__author__ = "High Velocity Solutions LLC"
__license__ = "Apache-2.0"

# Core agent classes
from agentweave.agent import BaseAgent, SecureAgent, AgentConfig

# Security decorators
from agentweave.decorators import capability, requires_peer, audit_log

# Request context
from agentweave.context import RequestContext, get_current_context

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    # Core agent classes
    "BaseAgent",
    "SecureAgent",
    "AgentConfig",
    # Decorators
    "capability",
    "requires_peer",
    "audit_log",
    # Context
    "RequestContext",
    "get_current_context",
]
