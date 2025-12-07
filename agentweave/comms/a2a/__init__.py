"""
A2A (Agent-to-Agent) Protocol implementation.

Implements the A2A protocol for standardized agent-to-agent communication,
including agent cards, task management, client/server components.
"""

from agentweave.comms.a2a.card import AgentCard, Capability, AuthScheme
from agentweave.comms.a2a.task import Task, TaskState, TaskManager
from agentweave.comms.a2a.client import A2AClient
from agentweave.comms.a2a.server import A2AServer

__all__ = [
    "AgentCard",
    "Capability",
    "AuthScheme",
    "Task",
    "TaskState",
    "TaskManager",
    "A2AClient",
    "A2AServer",
]
