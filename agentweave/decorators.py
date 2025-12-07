"""
Security decorators for agent capabilities.

This module provides decorators that enable declarative security controls
on agent methods, including capability registration, peer verification,
and audit logging.
"""

import functools
import logging
import time
import fnmatch
from typing import Callable, Optional, Any
from dataclasses import dataclass, field

from agentweave.context import get_current_context


logger = logging.getLogger(__name__)


@dataclass
class CapabilityMetadata:
    """Metadata for a capability."""
    name: str
    description: Optional[str] = None
    handler: Optional[Callable] = None
    requires_peer_patterns: list[str] = field(default_factory=list)
    audit_level: Optional[str] = None


# Registry to store capability metadata
_capability_registry: dict[str, CapabilityMetadata] = {}


def capability(name: str, description: Optional[str] = None):
    """
    Decorator to register a method as an agent capability.

    This decorator:
    - Registers the method in the capability registry
    - Auto-generates capability metadata
    - Wraps the method with authorization checks

    Args:
        name: The name of the capability
        description: Optional description of what the capability does

    Example:
        @capability("search", description="Search the database")
        async def search(self, query: str) -> dict:
            return {"results": [...]}
    """
    def decorator(func: Callable) -> Callable:
        # Store metadata
        metadata = CapabilityMetadata(
            name=name,
            description=description or func.__doc__,
            handler=func
        )

        # Register the capability
        _capability_registry[name] = metadata

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get current request context
            context = get_current_context()

            if context is None:
                logger.warning(f"Capability '{name}' called without request context")
            else:
                # Check authorization using the agent's authz enforcer
                if hasattr(self, '_authz'):
                    caller_id = context.caller_id
                    my_id = self.get_spiffe_id()

                    decision = await self._authz.check_inbound(
                        caller_id=caller_id,
                        action=name,
                        context={"metadata": context.metadata}
                    )

                    if not decision.allowed:
                        logger.error(
                            f"Authorization denied for {caller_id} to call {name}: {decision.reason}"
                        )
                        raise PermissionError(
                            f"Not authorized to call capability '{name}': {decision.reason}"
                        )

                    logger.info(
                        f"Authorization granted for {caller_id} to call {name} "
                        f"(audit_id: {decision.audit_id})"
                    )

            # Execute the actual capability
            return await func(self, *args, **kwargs)

        # Store the capability metadata on the function for introspection
        wrapper._capability_metadata = metadata

        return wrapper

    return decorator


def requires_peer(spiffe_pattern: str):
    """
    Decorator to restrict a capability to specific SPIFFE ID patterns.

    This decorator enforces that only callers matching the given SPIFFE ID
    pattern can invoke the capability. Supports wildcards using fnmatch syntax.

    Args:
        spiffe_pattern: SPIFFE ID pattern (e.g., "spiffe://domain/agent/*")

    Example:
        @capability("search")
        @requires_peer("spiffe://agentweave.io/agent/*")
        async def search(self, query: str) -> dict:
            return {"results": [...]}

    Note:
        This decorator should be used in combination with @capability and
        placed after it in the decorator stack.
    """
    def decorator(func: Callable) -> Callable:
        # Update capability metadata if it exists
        if hasattr(func, '_capability_metadata'):
            func._capability_metadata.requires_peer_patterns.append(spiffe_pattern)

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get current request context
            context = get_current_context()

            if context is None:
                logger.error("requires_peer check failed: No request context")
                raise PermissionError("No request context available for peer verification")

            caller_id = context.caller_id

            # Check if caller matches the pattern
            if not fnmatch.fnmatch(caller_id, spiffe_pattern):
                logger.error(
                    f"Peer verification failed: {caller_id} does not match pattern {spiffe_pattern}"
                )
                raise PermissionError(
                    f"Caller {caller_id} does not match required peer pattern {spiffe_pattern}"
                )

            logger.debug(f"Peer verification passed: {caller_id} matches {spiffe_pattern}")

            # Call the wrapped function
            return await func(self, *args, **kwargs)

        return wrapper

    return decorator


def audit_log(level: str = "info"):
    """
    Decorator to enforce audit logging for capability calls.

    This decorator logs:
    - Caller identity
    - Action (capability name)
    - Result (success/failure)
    - Timing information

    Args:
        level: Logging level ("debug", "info", "warning", "error")

    Example:
        @capability("delete_data")
        @audit_log(level="warning")
        async def delete_data(self, id: str) -> dict:
            return {"deleted": id}

    Note:
        This decorator should be used in combination with @capability and
        can be stacked with @requires_peer.
    """
    # Validate level
    valid_levels = {"debug", "info", "warning", "error"}
    if level.lower() not in valid_levels:
        raise ValueError(f"Invalid log level: {level}. Must be one of {valid_levels}")

    log_func = getattr(logger, level.lower())

    def decorator(func: Callable) -> Callable:
        # Update capability metadata if it exists
        if hasattr(func, '_capability_metadata'):
            func._capability_metadata.audit_level = level

        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get current request context
            context = get_current_context()

            caller_id = context.caller_id if context else "unknown"
            task_id = context.task_id if context else "no-task-id"
            capability_name = getattr(func, '_capability_metadata', None)
            action = capability_name.name if capability_name else func.__name__

            start_time = time.time()
            success = False
            error_msg = None

            try:
                # Execute the function
                result = await func(self, *args, **kwargs)
                success = True
                return result
            except Exception as e:
                error_msg = str(e)
                raise
            finally:
                # Log the audit entry
                duration = time.time() - start_time

                audit_entry = {
                    "task_id": task_id,
                    "caller": caller_id,
                    "action": action,
                    "success": success,
                    "duration_ms": round(duration * 1000, 2),
                }

                if error_msg:
                    audit_entry["error"] = error_msg

                log_func(f"AUDIT: {audit_entry}")

        return wrapper

    return decorator


def get_registered_capabilities() -> dict[str, CapabilityMetadata]:
    """
    Get all registered capabilities.

    Returns:
        Dictionary mapping capability names to their metadata.
    """
    return _capability_registry.copy()


def clear_capability_registry() -> None:
    """
    Clear the capability registry.

    This is primarily useful for testing purposes.
    """
    _capability_registry.clear()
