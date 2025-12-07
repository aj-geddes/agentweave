"""
Audit trail for AgentWeave SDK.

Provides comprehensive audit event recording with pluggable backends.
"""

import asyncio
import json
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, Protocol, List
from pathlib import Path


class AuditEventType(str, Enum):
    """Types of audit events."""

    AUTH_CHECK = "AUTH_CHECK"
    CAPABILITY_CALL = "CAPABILITY_CALL"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    STARTUP = "STARTUP"
    SHUTDOWN = "SHUTDOWN"
    IDENTITY_ROTATION = "IDENTITY_ROTATION"
    PEER_VERIFICATION = "PEER_VERIFICATION"
    POLICY_UPDATE = "POLICY_UPDATE"


@dataclass
class AuditEvent:
    """
    Immutable audit event record.

    All security-relevant operations generate audit events that are
    permanently recorded for compliance and forensics.
    """

    event_type: AuditEventType
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    agent_name: str = ""
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

    # Identity fields
    caller_id: Optional[str] = None
    peer_id: Optional[str] = None

    # Authorization fields
    action: Optional[str] = None
    resource: Optional[str] = None
    decision: Optional[str] = None
    reason: Optional[str] = None

    # Performance fields
    duration: Optional[float] = None

    # Additional context
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert event to dictionary.

        Returns:
            Dictionary representation of the event
        """
        data = asdict(self)
        data["event_type"] = self.event_type.value
        return data

    def to_json(self) -> str:
        """
        Convert event to JSON string.

        Returns:
            JSON representation of the event
        """
        return json.dumps(self.to_dict())


class AuditBackend(Protocol):
    """
    Protocol for audit event backends.

    Backends are responsible for persisting audit events to various
    destinations (files, databases, external audit services, etc.).
    """

    async def emit(self, event: AuditEvent) -> None:
        """
        Emit an audit event.

        Args:
            event: Audit event to emit
        """
        ...

    async def flush(self) -> None:
        """Flush any buffered events."""
        ...

    async def close(self) -> None:
        """Close the backend and release resources."""
        ...


class FileAuditBackend:
    """
    File-based audit backend.

    Writes audit events to a file in JSON Lines format (one event per line).
    """

    def __init__(self, file_path: str, buffer_size: int = 100):
        """
        Initialize file audit backend.

        Args:
            file_path: Path to audit log file
            buffer_size: Number of events to buffer before flushing
        """
        self.file_path = Path(file_path)
        self.buffer_size = buffer_size
        self._buffer: List[AuditEvent] = []
        self._file = None
        self._lock = asyncio.Lock()

        # Ensure parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Open file in append mode
        self._file = open(self.file_path, "a", encoding="utf-8")

    async def emit(self, event: AuditEvent) -> None:
        """
        Emit an audit event to file.

        Args:
            event: Audit event to emit
        """
        async with self._lock:
            self._buffer.append(event)

            # Flush if buffer is full
            if len(self._buffer) >= self.buffer_size:
                await self._flush_internal()

    async def flush(self) -> None:
        """Flush buffered events to file."""
        async with self._lock:
            await self._flush_internal()

    async def _flush_internal(self) -> None:
        """Internal flush implementation (not thread-safe)."""
        if not self._buffer:
            return

        for event in self._buffer:
            self._file.write(event.to_json() + "\n")

        self._file.flush()
        self._buffer.clear()

    async def close(self) -> None:
        """Close file and flush remaining events."""
        await self.flush()
        if self._file:
            self._file.close()


class StdoutAuditBackend:
    """
    Stdout-based audit backend.

    Writes audit events to stdout in JSON format.
    Useful for containerized environments with log aggregation.
    """

    async def emit(self, event: AuditEvent) -> None:
        """
        Emit an audit event to stdout.

        Args:
            event: Audit event to emit
        """
        print(event.to_json(), file=sys.stdout, flush=True)

    async def flush(self) -> None:
        """Flush stdout."""
        sys.stdout.flush()

    async def close(self) -> None:
        """Close backend (no-op for stdout)."""
        await self.flush()


class MultiBackend:
    """
    Composite backend that emits to multiple backends.

    Useful for sending audit events to multiple destinations
    (e.g., file + external audit service).
    """

    def __init__(self, backends: List[AuditBackend]):
        """
        Initialize multi-backend.

        Args:
            backends: List of backends to emit to
        """
        self.backends = backends

    async def emit(self, event: AuditEvent) -> None:
        """
        Emit event to all backends.

        Args:
            event: Audit event to emit
        """
        await asyncio.gather(*[backend.emit(event) for backend in self.backends])

    async def flush(self) -> None:
        """Flush all backends."""
        await asyncio.gather(*[backend.flush() for backend in self.backends])

    async def close(self) -> None:
        """Close all backends."""
        await asyncio.gather(*[backend.close() for backend in self.backends])


class AuditTrail:
    """
    Central audit trail manager for secure agents.

    Coordinates audit event creation and emission to configured backends.
    All security-relevant operations should generate audit events.
    """

    def __init__(
        self,
        agent_name: str,
        backend: AuditBackend,
        enabled: bool = True,
    ):
        """
        Initialize audit trail.

        Args:
            agent_name: Name of the agent
            backend: Backend for emitting events
            enabled: Whether audit trail is enabled
        """
        self.agent_name = agent_name
        self.backend = backend
        self.enabled = enabled

    async def record_auth_check(
        self,
        caller_id: str,
        action: str,
        resource: str,
        decision: str,
        duration: float,
        reason: str = "",
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record an authorization check event.

        Args:
            caller_id: SPIFFE ID of the caller
            action: Action being performed
            resource: Resource being accessed
            decision: Authorization decision (allow/deny)
            duration: Duration of the check
            reason: Reason for the decision
            trace_id: Distributed trace ID
            span_id: Current span ID
            context: Additional context
        """
        if not self.enabled:
            return

        event = AuditEvent(
            event_type=AuditEventType.AUTH_CHECK,
            agent_name=self.agent_name,
            caller_id=caller_id,
            action=action,
            resource=resource,
            decision=decision,
            reason=reason,
            duration=duration,
            trace_id=trace_id,
            span_id=span_id,
            context=context or {},
        )

        await self.backend.emit(event)

    async def record_capability_call(
        self,
        caller_id: str,
        capability: str,
        status: str,
        duration: float,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a capability invocation event.

        Args:
            caller_id: SPIFFE ID of the caller
            capability: Capability that was invoked
            status: Status of the call (success/error)
            duration: Duration of the call
            trace_id: Distributed trace ID
            span_id: Current span ID
            context: Additional context
        """
        if not self.enabled:
            return

        event = AuditEvent(
            event_type=AuditEventType.CAPABILITY_CALL,
            agent_name=self.agent_name,
            caller_id=caller_id,
            resource=capability,
            decision=status,
            duration=duration,
            trace_id=trace_id,
            span_id=span_id,
            context=context or {},
        )

        await self.backend.emit(event)

    async def record_config_change(
        self,
        initiator: str,
        change_type: str,
        details: Dict[str, Any],
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ) -> None:
        """
        Record a configuration change event.

        Args:
            initiator: Who initiated the change
            change_type: Type of configuration change
            details: Details of the change
            trace_id: Distributed trace ID
            span_id: Current span ID
        """
        if not self.enabled:
            return

        event = AuditEvent(
            event_type=AuditEventType.CONFIG_CHANGE,
            agent_name=self.agent_name,
            caller_id=initiator,
            action=change_type,
            trace_id=trace_id,
            span_id=span_id,
            context=details,
        )

        await self.backend.emit(event)

    async def record_startup(
        self,
        version: str,
        config: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Record agent startup event.

        Args:
            version: Agent version
            config: Sanitized configuration (no secrets)
            trace_id: Distributed trace ID
        """
        if not self.enabled:
            return

        event = AuditEvent(
            event_type=AuditEventType.STARTUP,
            agent_name=self.agent_name,
            trace_id=trace_id,
            context={"version": version, "config": config},
        )

        await self.backend.emit(event)

    async def record_shutdown(
        self,
        reason: str = "normal",
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Record agent shutdown event.

        Args:
            reason: Reason for shutdown
            trace_id: Distributed trace ID
        """
        if not self.enabled:
            return

        event = AuditEvent(
            event_type=AuditEventType.SHUTDOWN,
            agent_name=self.agent_name,
            reason=reason,
            trace_id=trace_id,
        )

        await self.backend.emit(event)

    async def record_identity_rotation(
        self,
        old_spiffe_id: str,
        new_spiffe_id: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ) -> None:
        """
        Record SVID rotation event.

        Args:
            old_spiffe_id: Previous SPIFFE ID
            new_spiffe_id: New SPIFFE ID
            trace_id: Distributed trace ID
            span_id: Current span ID
        """
        if not self.enabled:
            return

        event = AuditEvent(
            event_type=AuditEventType.IDENTITY_ROTATION,
            agent_name=self.agent_name,
            trace_id=trace_id,
            span_id=span_id,
            context={
                "old_spiffe_id": old_spiffe_id,
                "new_spiffe_id": new_spiffe_id,
            },
        )

        await self.backend.emit(event)

    async def record_peer_verification(
        self,
        peer_id: str,
        status: str,
        reason: str = "",
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ) -> None:
        """
        Record peer verification event.

        Args:
            peer_id: SPIFFE ID of the peer
            status: Verification status (success/failure)
            reason: Reason for failure (if applicable)
            trace_id: Distributed trace ID
            span_id: Current span ID
        """
        if not self.enabled:
            return

        event = AuditEvent(
            event_type=AuditEventType.PEER_VERIFICATION,
            agent_name=self.agent_name,
            peer_id=peer_id,
            decision=status,
            reason=reason,
            trace_id=trace_id,
            span_id=span_id,
        )

        await self.backend.emit(event)

    async def flush(self) -> None:
        """Flush all buffered events."""
        if self.enabled:
            await self.backend.flush()

    async def close(self) -> None:
        """Close audit trail and backend."""
        if self.enabled:
            await self.backend.close()
