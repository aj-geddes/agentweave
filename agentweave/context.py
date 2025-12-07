"""
Request context management for agent-to-agent communication.

This module provides context propagation for tracking caller identity,
task IDs, and request metadata across async calls.
"""

from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
import uuid


@dataclass
class RequestContext:
    """
    Context information for an agent request.

    Attributes:
        caller_id: SPIFFE ID of the calling agent
        task_id: Unique identifier for this task
        timestamp: When the request was initiated
        metadata: Additional context metadata
    """
    caller_id: str
    task_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict = field(default_factory=dict)

    @classmethod
    def create(cls, caller_id: str, metadata: Optional[dict] = None) -> "RequestContext":
        """Create a new request context with generated task ID."""
        return cls(
            caller_id=caller_id,
            task_id=str(uuid.uuid4()),
            metadata=metadata or {}
        )


# ContextVar for async context propagation
_request_context: ContextVar[Optional[RequestContext]] = ContextVar(
    "request_context",
    default=None
)


def get_current_context() -> Optional[RequestContext]:
    """
    Get the current request context.

    Returns:
        The current RequestContext if one is set, None otherwise.
    """
    return _request_context.get()


def set_current_context(context: Optional[RequestContext]) -> None:
    """
    Set the current request context.

    Args:
        context: The RequestContext to set, or None to clear.
    """
    _request_context.set(context)
