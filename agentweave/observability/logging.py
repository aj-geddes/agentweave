"""
Structured JSON logging for AgentWeave SDK.

Provides JSON-formatted logs with trace correlation and security audit logging.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from enum import Enum


class LogLevel(str, Enum):
    """Log level enumeration."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    AUDIT = "AUDIT"


class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.

    Outputs logs in JSON format with standard fields:
    - timestamp: ISO 8601 timestamp
    - level: Log level
    - logger: Logger name
    - message: Log message
    - trace_id: Distributed trace ID (if available)
    - span_id: Current span ID (if available)
    - agent_name: Name of the agent
    - extra: Additional fields from log record
    """

    def __init__(
        self,
        agent_name: str,
        include_trace_ids: bool = True,
        *args,
        **kwargs,
    ):
        """
        Initialize JSON formatter.

        Args:
            agent_name: Name of the agent (included in all logs)
            include_trace_ids: Whether to include trace/span IDs
        """
        super().__init__(*args, **kwargs)
        self.agent_name = agent_name
        self.include_trace_ids = include_trace_ids

    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON.

        Args:
            record: Log record to format

        Returns:
            JSON-formatted log string
        """
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "agent_name": self.agent_name,
        }

        # Add trace IDs if available and enabled
        if self.include_trace_ids:
            if hasattr(record, "trace_id") and record.trace_id:
                log_data["trace_id"] = record.trace_id
            if hasattr(record, "span_id") and record.span_id:
                log_data["span_id"] = record.span_id

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields from record
        extra_fields = {}
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "created",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "thread",
                "threadName",
                "exc_info",
                "exc_text",
                "stack_info",
                "trace_id",
                "span_id",
            ]:
                extra_fields[key] = value

        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data)


class AuditLogger:
    """
    Security audit logger for AgentWeave SDK.

    Records security-relevant events with structured fields:
    - timestamp: When the event occurred
    - trace_id: Correlation with distributed traces
    - span_id: Correlation with current span
    - agent_name: Name of this agent
    - caller_id: SPIFFE ID of the caller
    - action: Action being performed
    - resource: Resource being accessed (capability)
    - decision: Authorization decision (allow/deny)
    - duration: Duration of the operation in seconds
    - reason: Reason for the decision
    - context: Additional context

    IMPORTANT: Audit logging cannot be disabled in production environments.
    """

    def __init__(
        self,
        agent_name: str,
        logger: Optional[logging.Logger] = None,
        production_mode: bool = True,
    ):
        """
        Initialize audit logger.

        Args:
            agent_name: Name of the agent
            logger: Python logger instance (creates new if not provided)
            production_mode: If True, audit logging cannot be disabled
        """
        self.agent_name = agent_name
        self.production_mode = production_mode
        self._enabled = True

        # Create or use provided logger
        if logger is None:
            self.logger = logging.getLogger(f"{__name__}.audit")
            self.logger.setLevel(logging.INFO)

            # Add handler if not already configured
            if not self.logger.handlers:
                handler = logging.StreamHandler(sys.stdout)
                handler.setFormatter(
                    JSONFormatter(agent_name=agent_name, include_trace_ids=True)
                )
                self.logger.addHandler(handler)
        else:
            self.logger = logger

    @property
    def enabled(self) -> bool:
        """Check if audit logging is enabled."""
        return self._enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """
        Set audit logging enabled state.

        Raises:
            RuntimeError: If attempting to disable in production mode
        """
        if self.production_mode and not value:
            raise RuntimeError(
                "Cannot disable audit logging in production mode. "
                "Set production_mode=False if this is a development environment."
            )
        self._enabled = value

    def audit_auth_check(
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
        Log an authorization check event.

        Args:
            caller_id: SPIFFE ID of the caller
            action: Action being performed
            resource: Resource being accessed (capability name)
            decision: Authorization decision (allow/deny)
            duration: Duration of the check in seconds
            reason: Reason for the decision
            trace_id: Distributed trace ID
            span_id: Current span ID
            context: Additional context
        """
        if not self._enabled:
            return

        self.logger.info(
            "Authorization check",
            extra={
                "event_type": "AUTH_CHECK",
                "agent_name": self.agent_name,
                "caller_id": caller_id,
                "action": action,
                "resource": resource,
                "decision": decision,
                "duration": duration,
                "reason": reason,
                "trace_id": trace_id,
                "span_id": span_id,
                "context": context or {},
            },
        )

    def audit_capability_call(
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
        Log a capability invocation event.

        Args:
            caller_id: SPIFFE ID of the caller
            capability: Capability that was invoked
            status: Status of the call (success/error)
            duration: Duration of the call in seconds
            trace_id: Distributed trace ID
            span_id: Current span ID
            context: Additional context (e.g., payload size)
        """
        if not self._enabled:
            return

        self.logger.info(
            "Capability invocation",
            extra={
                "event_type": "CAPABILITY_CALL",
                "agent_name": self.agent_name,
                "caller_id": caller_id,
                "capability": capability,
                "status": status,
                "duration": duration,
                "trace_id": trace_id,
                "span_id": span_id,
                "context": context or {},
            },
        )

    def audit_config_change(
        self,
        initiator: str,
        change_type: str,
        details: Dict[str, Any],
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ) -> None:
        """
        Log a configuration change event.

        Args:
            initiator: Who initiated the change (SPIFFE ID or "system")
            change_type: Type of configuration change
            details: Details of the change
            trace_id: Distributed trace ID
            span_id: Current span ID
        """
        if not self._enabled:
            return

        self.logger.info(
            "Configuration change",
            extra={
                "event_type": "CONFIG_CHANGE",
                "agent_name": self.agent_name,
                "initiator": initiator,
                "change_type": change_type,
                "details": details,
                "trace_id": trace_id,
                "span_id": span_id,
            },
        )

    def audit_startup(
        self,
        version: str,
        config: Dict[str, Any],
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Log agent startup event.

        Args:
            version: Agent version
            config: Sanitized configuration (no secrets)
            trace_id: Distributed trace ID
        """
        if not self._enabled:
            return

        self.logger.info(
            "Agent startup",
            extra={
                "event_type": "STARTUP",
                "agent_name": self.agent_name,
                "version": version,
                "config": config,
                "trace_id": trace_id,
            },
        )

    def audit_shutdown(
        self,
        reason: str = "normal",
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Log agent shutdown event.

        Args:
            reason: Reason for shutdown (normal, error, signal)
            trace_id: Distributed trace ID
        """
        if not self._enabled:
            return

        self.logger.info(
            "Agent shutdown",
            extra={
                "event_type": "SHUTDOWN",
                "agent_name": self.agent_name,
                "reason": reason,
                "trace_id": trace_id,
            },
        )

    def audit_identity_rotation(
        self,
        old_spiffe_id: str,
        new_spiffe_id: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None,
    ) -> None:
        """
        Log SVID rotation event.

        Args:
            old_spiffe_id: Previous SPIFFE ID
            new_spiffe_id: New SPIFFE ID
            trace_id: Distributed trace ID
            span_id: Current span ID
        """
        if not self._enabled:
            return

        self.logger.info(
            "Identity rotation",
            extra={
                "event_type": "IDENTITY_ROTATION",
                "agent_name": self.agent_name,
                "old_spiffe_id": old_spiffe_id,
                "new_spiffe_id": new_spiffe_id,
                "trace_id": trace_id,
                "span_id": span_id,
            },
        )


def setup_logging(
    agent_name: str,
    level: str = "INFO",
    json_format: bool = True,
    include_trace_ids: bool = True,
) -> logging.Logger:
    """
    Setup standard logging configuration for an agent.

    Args:
        agent_name: Name of the agent
        level: Log level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON formatter (recommended for production)
        include_trace_ids: Include trace/span IDs in logs

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger("agentweave")
    logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    logger.handlers.clear()

    # Create handler
    handler = logging.StreamHandler(sys.stdout)

    # Set formatter
    if json_format:
        formatter = JSONFormatter(
            agent_name=agent_name, include_trace_ids=include_trace_ids
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
