"""
Task lifecycle management for A2A protocol.

Implements task state tracking, lifecycle management, and status polling
for long-running agent operations.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import asyncio
from collections import defaultdict


class TaskState(str, Enum):
    """Task lifecycle states as per A2A protocol."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

    def is_terminal(self) -> bool:
        """Check if this is a terminal state."""
        return self in (TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED)


class MessagePart(BaseModel):
    """Part of a message (text, data, file, etc.)."""

    type: str = Field(..., description="Part type: text, data, file, etc.")
    content: Any = Field(..., description="Part content")


class Message(BaseModel):
    """A2A protocol message."""

    role: str = Field(..., description="Message role: user, assistant, system")
    parts: List[MessagePart] = Field(default_factory=list, description="Message parts")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Artifact(BaseModel):
    """Output artifact from task completion."""

    type: str = Field(..., description="Artifact type")
    data: Any = Field(..., description="Artifact data")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class Task(BaseModel):
    """
    A2A Task representing a unit of work.

    Tasks have a lifecycle: PENDING -> RUNNING -> COMPLETED/FAILED/CANCELLED
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique task ID")
    type: str = Field(..., description="Task type/capability name")
    state: TaskState = Field(default=TaskState.PENDING, description="Current task state")

    payload: Dict[str, Any] = Field(default_factory=dict, description="Task input payload")
    messages: List[Message] = Field(default_factory=list, description="Message history")

    result: Optional[Any] = Field(default=None, description="Task result")
    artifacts: List[Artifact] = Field(default_factory=list, description="Output artifacts")
    error: Optional[str] = Field(default=None, description="Error message if failed")

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Task creation timestamp"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Last update timestamp"
    )

    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional task metadata"
    )

    class Config:
        use_enum_values = True

    def update_state(self, new_state: TaskState, error: Optional[str] = None) -> None:
        """
        Update task state and timestamp.

        Args:
            new_state: New task state
            error: Error message if state is FAILED
        """
        self.state = new_state
        self.updated_at = datetime.now(timezone.utc)
        if error:
            self.error = error

    def add_message(self, role: str, parts: List[MessagePart]) -> None:
        """
        Add a message to the task.

        Args:
            role: Message role
            parts: Message parts
        """
        message = Message(role=role, parts=parts)
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)

    def add_artifact(self, artifact_type: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> None:
        """
        Add an artifact to the task.

        Args:
            artifact_type: Type of artifact
            data: Artifact data
            metadata: Optional metadata
        """
        artifact = Artifact(
            type=artifact_type,
            data=data,
            metadata=metadata or {}
        )
        self.artifacts.append(artifact)
        self.updated_at = datetime.now(timezone.utc)

    def mark_running(self) -> None:
        """Mark task as running."""
        self.update_state(TaskState.RUNNING)

    def mark_completed(self, result: Any = None) -> None:
        """
        Mark task as completed.

        Args:
            result: Task result
        """
        self.result = result
        self.update_state(TaskState.COMPLETED)

    def mark_failed(self, error: str) -> None:
        """
        Mark task as failed.

        Args:
            error: Error message
        """
        self.update_state(TaskState.FAILED, error=error)

    def mark_cancelled(self) -> None:
        """Mark task as cancelled."""
        self.update_state(TaskState.CANCELLED)

    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.state.is_terminal()

    def to_jsonrpc(self, method: str = "task.send") -> Dict[str, Any]:
        """
        Convert task to JSON-RPC 2.0 request format.

        Args:
            method: JSON-RPC method name

        Returns:
            JSON-RPC request dictionary
        """
        return {
            "jsonrpc": "2.0",
            "method": method,
            "params": {
                "task_id": self.id,
                "task_type": self.type,
                "payload": self.payload,
                "messages": [
                    {
                        "role": msg.role,
                        "parts": [{"type": part.type, "content": part.content} for part in msg.parts],
                        "timestamp": msg.timestamp.isoformat()
                    }
                    for msg in self.messages
                ]
            },
            "id": self.id
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert task to dictionary.

        Returns:
            Dictionary representation
        """
        return {
            "id": self.id,
            "type": self.type,
            "state": self.state.value,
            "payload": self.payload,
            "messages": [
                {
                    "role": msg.role,
                    "parts": [{"type": part.type, "content": part.content} for part in msg.parts],
                    "timestamp": msg.timestamp.isoformat()
                }
                for msg in self.messages
            ],
            "result": self.result,
            "artifacts": [
                {
                    "type": art.type,
                    "data": art.data,
                    "metadata": art.metadata
                }
                for art in self.artifacts
            ],
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata
        }


class TaskManager:
    """
    Manages task lifecycle and status tracking.

    Provides task storage, retrieval, and status monitoring for long-running tasks.
    """

    def __init__(self):
        """Initialize task manager."""
        self._tasks: Dict[str, Task] = {}
        self._task_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self._task_events: Dict[str, asyncio.Event] = {}

    async def create_task(
        self,
        task_type: str,
        payload: Optional[Dict[str, Any]] = None,
        messages: Optional[List[Message]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Task:
        """
        Create a new task.

        Args:
            task_type: Type of task
            payload: Task payload
            messages: Initial messages
            metadata: Task metadata

        Returns:
            Created task
        """
        task = Task(
            type=task_type,
            payload=payload or {},
            messages=messages or [],
            metadata=metadata or {}
        )

        async with self._task_locks[task.id]:
            self._tasks[task.id] = task
            self._task_events[task.id] = asyncio.Event()

        return task

    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Retrieve a task by ID.

        Args:
            task_id: Task ID

        Returns:
            Task if found, None otherwise
        """
        return self._tasks.get(task_id)

    async def update_task(
        self,
        task_id: str,
        state: Optional[TaskState] = None,
        result: Optional[Any] = None,
        error: Optional[str] = None
    ) -> Optional[Task]:
        """
        Update task state and data.

        Args:
            task_id: Task ID
            state: New state
            result: Task result
            error: Error message

        Returns:
            Updated task if found, None otherwise
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        async with self._task_locks[task_id]:
            if state:
                task.update_state(state, error=error)
            if result is not None:
                task.result = result

            # Notify waiters if state changed to terminal
            if task.is_terminal() and task_id in self._task_events:
                self._task_events[task_id].set()

        return task

    async def delete_task(self, task_id: str) -> bool:
        """
        Delete a task.

        Args:
            task_id: Task ID

        Returns:
            True if deleted, False if not found
        """
        if task_id not in self._tasks:
            return False

        async with self._task_locks[task_id]:
            del self._tasks[task_id]
            if task_id in self._task_events:
                del self._task_events[task_id]
            del self._task_locks[task_id]

        return True

    async def list_tasks(
        self,
        state: Optional[TaskState] = None,
        task_type: Optional[str] = None
    ) -> List[Task]:
        """
        List tasks with optional filtering.

        Args:
            state: Filter by state
            task_type: Filter by type

        Returns:
            List of matching tasks
        """
        tasks = list(self._tasks.values())

        if state:
            tasks = [t for t in tasks if t.state == state]

        if task_type:
            tasks = [t for t in tasks if t.type == task_type]

        return tasks

    async def wait_for_completion(
        self,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Optional[Task]:
        """
        Wait for a task to reach a terminal state.

        Args:
            task_id: Task ID
            timeout: Optional timeout in seconds

        Returns:
            Completed task if found, None otherwise

        Raises:
            asyncio.TimeoutError: If timeout is reached
        """
        task = self._tasks.get(task_id)
        if not task:
            return None

        if task.is_terminal():
            return task

        event = self._task_events.get(task_id)
        if not event:
            return None

        if timeout:
            await asyncio.wait_for(event.wait(), timeout=timeout)
        else:
            await event.wait()

        return self._tasks.get(task_id)

    async def cleanup_completed_tasks(self, max_age_seconds: int = 3600) -> int:
        """
        Clean up old completed tasks.

        Args:
            max_age_seconds: Maximum age for completed tasks

        Returns:
            Number of tasks cleaned up
        """
        now = datetime.now(timezone.utc)
        to_delete = []

        for task_id, task in self._tasks.items():
            if task.is_terminal():
                age = (now - task.updated_at).total_seconds()
                if age > max_age_seconds:
                    to_delete.append(task_id)

        for task_id in to_delete:
            await self.delete_task(task_id)

        return len(to_delete)
