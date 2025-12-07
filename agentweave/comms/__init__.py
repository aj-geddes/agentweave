"""
Communication components for AgentWeave SDK.

Provides A2A protocol implementation, agent discovery, and secure communication channels.
"""

from agentweave.comms.a2a.card import AgentCard, Capability, AuthScheme
from agentweave.comms.a2a.task import Task, TaskState, TaskManager
from agentweave.comms.a2a.client import A2AClient
from agentweave.comms.a2a.server import A2AServer
from agentweave.comms.discovery import DiscoveryClient

__all__ = [
    "AgentCard",
    "Capability",
    "AuthScheme",
    "Task",
    "TaskState",
    "TaskManager",
    "A2AClient",
    "A2AServer",
    "DiscoveryClient",
]
