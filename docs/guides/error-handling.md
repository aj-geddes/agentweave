---
layout: page
title: Error Handling Best Practices
description: Handle errors gracefully in AgentWeave agents
parent: How-To Guides
nav_order: 4
---

# Error Handling Best Practices

This guide shows you how to handle errors properly in AgentWeave agents, including retry strategies, circuit breakers, and graceful degradation.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## AgentWeave Exception Hierarchy

All AgentWeave exceptions inherit from `AgentWeaveError`:

```
AgentWeaveError
├── IdentityError
│   └── SVIDError
├── AuthorizationError
│   └── PolicyEvaluationError
├── TransportError
│   └── PeerVerificationError
├── ConfigurationError
├── A2AProtocolError
```

### When Each Exception Is Raised

| Exception | When Raised | Recoverable? |
|-----------|-------------|--------------|
| `IdentityError` | Cannot get SVID, SPIRE unreachable | Maybe (retry) |
| `SVIDError` | SVID expired and rotation failed | Maybe (retry) |
| `AuthorizationError` | OPA denies request | No (fix policy) |
| `PolicyEvaluationError` | OPA unreachable or error | Maybe (retry) |
| `TransportError` | Network/connection failure | Maybe (retry) |
| `PeerVerificationError` | Peer SPIFFE ID mismatch | No (security issue) |
| `ConfigurationError` | Invalid configuration | No (fix config) |
| `A2AProtocolError` | Invalid A2A message format | No (fix message) |

---

## Handling AuthorizationError

Authorization failures indicate the caller doesn't have permission to perform the requested action.

### Basic Error Handling

```python
from agentweave import SecureAgent, capability
from agentweave.exceptions import AuthorizationError

class DataProcessor(SecureAgent):
    @capability("process")
    async def process(self, data: dict) -> dict:
        try:
            # Call search agent
            result = await self.call_agent(
                callee_id="spiffe://yourdomain.com/agent/search",
                action="search",
                payload={"query": data["query"]}
            )
            return result
        except AuthorizationError as e:
            # Log the denial
            self.logger.warning(
                "Authorization denied",
                extra={
                    "callee": "spiffe://yourdomain.com/agent/search",
                    "action": "search",
                    "reason": e.message,
                    "details": e.details
                }
            )

            # Return graceful error to user
            return {
                "status": "error",
                "error": "Not authorized to perform search",
                "error_code": "AUTHZ_DENIED"
            }
```

### Checking Authorization Before Calling

Proactively check if a call will be authorized:

```python
from agentweave import SecureAgent, capability
from agentweave.exceptions import AuthorizationError

class OrchestratorAgent(SecureAgent):
    @capability("orchestrate")
    async def orchestrate(self, task: dict) -> dict:
        # Check if we're authorized before making the call
        can_search = await self._can_call(
            callee_id="spiffe://yourdomain.com/agent/search",
            action="search"
        )

        if not can_search:
            # Handle authorization failure gracefully
            self.logger.info("Search not authorized, using fallback")
            return await self._fallback_search(task)

        # Proceed with authorized call
        return await self.call_agent(
            callee_id="spiffe://yourdomain.com/agent/search",
            action="search",
            payload=task
        )

    async def _can_call(self, callee_id: str, action: str) -> bool:
        """Check if we can call an agent before making the call."""
        try:
            decision = await self.authz_provider.check_outbound(
                caller_id=self.identity_provider.get_spiffe_id(),
                callee_id=callee_id,
                action=action
            )
            return decision.allowed
        except Exception as e:
            # If authz check fails, assume denied
            self.logger.warning(f"Authorization check failed: {e}")
            return False

    async def _fallback_search(self, task: dict) -> dict:
        """Fallback when search is not authorized."""
        return {
            "status": "partial",
            "results": [],
            "note": "Search capability not available"
        }
```

### User-Facing Error Messages

Don't expose internal authorization details to users:

```python
from agentweave.exceptions import AuthorizationError

class APIAgent(SecureAgent):
    @capability("api_request")
    async def handle_request(self, request: dict) -> dict:
        try:
            result = await self._process_request(request)
            return {"status": "success", "data": result}

        except AuthorizationError as e:
            # Log detailed error internally
            self.logger.error(
                "Authorization failed",
                extra={
                    "request_id": request.get("id"),
                    "user": request.get("user"),
                    "details": e.details
                }
            )

            # Return generic error to user (don't leak internal details)
            return {
                "status": "error",
                "error": "You don't have permission to perform this action",
                "error_code": "FORBIDDEN"
            }
```

---

## Handling IdentityError

Identity errors occur when the agent can't fetch or verify its SPIFFE identity.

### Retry on SVID Fetch Failure

```python
import asyncio
from agentweave.exceptions import IdentityError, SVIDError

class ResilientAgent(SecureAgent):
    async def start(self):
        """Start agent with identity retry logic."""
        max_retries = 5
        retry_delay = 2.0

        for attempt in range(max_retries):
            try:
                # Try to fetch SVID
                svid = await self.identity_provider.get_svid()
                self.logger.info(
                    f"Identity acquired: {svid.spiffe_id}",
                    extra={"expiry": svid.expiry}
                )
                break

            except IdentityError as e:
                if attempt < max_retries - 1:
                    self.logger.warning(
                        f"Failed to fetch SVID (attempt {attempt + 1}/{max_retries}): {e}",
                        extra={"retry_in": retry_delay}
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    # Final attempt failed
                    self.logger.error("Cannot start agent: Identity unavailable")
                    raise

        # Continue with agent initialization
        await super().start()
```

### Handling SVID Expiration

```python
from agentweave.exceptions import SVIDError

class MonitoredAgent(SecureAgent):
    async def _monitor_svid_expiry(self):
        """Background task to monitor SVID expiration."""
        while self.is_running:
            try:
                svid = await self.identity_provider.get_svid()

                # Check if SVID is close to expiring
                time_to_expiry = (svid.expiry - datetime.utcnow()).total_seconds()

                if time_to_expiry < 300:  # Less than 5 minutes
                    self.logger.warning(
                        "SVID expiring soon, rotation should occur",
                        extra={"expires_in_seconds": time_to_expiry}
                    )

                if svid.is_expired():
                    # SVID expired - try to rotate
                    self.logger.error("SVID has expired!")
                    await self._handle_expired_svid()

            except SVIDError as e:
                self.logger.error(f"SVID error: {e}")
                await self._handle_expired_svid()

            # Check every minute
            await asyncio.sleep(60)

    async def _handle_expired_svid(self):
        """Handle expired SVID."""
        try:
            # Attempt rotation
            new_svid = await self.identity_provider.rotate_svid()
            self.logger.info("SVID successfully rotated")
        except Exception as e:
            # Rotation failed - this is critical
            self.logger.critical(f"SVID rotation failed: {e}")

            # Optionally: Stop accepting new requests
            self.accepting_requests = False

            # Alert monitoring system
            await self._send_alert("SVID rotation failed")
```

---

## Handling ConnectionError

Connection errors occur when the transport layer fails (network issues, peer unavailable, etc.).

### Retry with Exponential Backoff

```python
import asyncio
from agentweave.exceptions import TransportError

class RetryAgent(SecureAgent):
    async def call_with_retry(
        self,
        callee_id: str,
        action: str,
        payload: dict,
        max_retries: int = 3,
        base_delay: float = 1.0
    ) -> dict:
        """Call another agent with exponential backoff retry."""
        last_error = None

        for attempt in range(max_retries):
            try:
                result = await self.call_agent(
                    callee_id=callee_id,
                    action=action,
                    payload=payload
                )
                return result

            except TransportError as e:
                last_error = e
                if attempt < max_retries - 1:
                    delay = base_delay * (2 ** attempt)  # Exponential backoff
                    self.logger.warning(
                        f"Call failed (attempt {attempt + 1}/{max_retries}): {e}",
                        extra={
                            "callee": callee_id,
                            "action": action,
                            "retry_in": delay
                        }
                    )
                    await asyncio.sleep(delay)
                else:
                    # All retries exhausted
                    self.logger.error(
                        f"Call failed after {max_retries} attempts: {e}",
                        extra={"callee": callee_id, "action": action}
                    )

        # All retries failed
        raise last_error
```

### Timeout Handling

```python
import asyncio
from agentweave.exceptions import TransportError

class TimeoutAgent(SecureAgent):
    @capability("process")
    async def process(self, data: dict) -> dict:
        try:
            # Set timeout for the call
            result = await asyncio.wait_for(
                self.call_agent(
                    callee_id="spiffe://yourdomain.com/agent/slow-service",
                    action="process",
                    payload=data
                ),
                timeout=10.0  # 10 second timeout
            )
            return result

        except asyncio.TimeoutError:
            self.logger.warning(
                "Call timed out",
                extra={
                    "callee": "spiffe://yourdomain.com/agent/slow-service",
                    "timeout": 10.0
                }
            )
            return {
                "status": "error",
                "error": "Request timed out",
                "error_code": "TIMEOUT"
            }

        except TransportError as e:
            self.logger.error(f"Transport error: {e}")
            return {
                "status": "error",
                "error": "Service unavailable",
                "error_code": "SERVICE_UNAVAILABLE"
            }
```

---

## Retry Strategies

AgentWeave provides built-in retry configuration in the transport layer.

### Configuring Retries

```yaml
# config.yaml
transport:
  retry:
    max_attempts: 3
    backoff_base_seconds: 1.0
    backoff_max_seconds: 30.0
    retry_on_errors:
      - TransportError
      - ConnectionError
      - TimeoutError
    # Don't retry these
    do_not_retry:
      - AuthorizationError
      - PeerVerificationError
```

### Custom Retry Logic

```python
from agentweave.transport.retry import RetryPolicy, ExponentialBackoff

class CustomRetryAgent(SecureAgent):
    def __init__(self):
        super().__init__()

        # Define custom retry policy
        self.retry_policy = RetryPolicy(
            max_attempts=5,
            backoff=ExponentialBackoff(
                base=1.0,
                max_delay=60.0,
                jitter=True  # Add randomness to prevent thundering herd
            ),
            retryable_exceptions=[
                TransportError,
                ConnectionError,
            ],
            non_retryable_exceptions=[
                AuthorizationError,
                PeerVerificationError,
            ]
        )

    async def call_with_custom_retry(
        self,
        callee_id: str,
        action: str,
        payload: dict
    ) -> dict:
        """Make call with custom retry policy."""
        return await self.retry_policy.execute(
            lambda: self.call_agent(callee_id, action, payload)
        )
```

---

## Circuit Breaker Patterns

Circuit breakers prevent cascading failures by stopping calls to failing services.

### Using Built-in Circuit Breaker

```yaml
# config.yaml
transport:
  circuit_breaker:
    failure_threshold: 5        # Open after 5 failures
    recovery_timeout_seconds: 30 # Try again after 30 seconds
    success_threshold: 2        # Close after 2 successes
```

### Custom Circuit Breaker Logic

```python
from agentweave.transport.circuit import CircuitBreaker, CircuitState

class CircuitBreakerAgent(SecureAgent):
    def __init__(self):
        super().__init__()
        self.circuit_breakers = {}

    def _get_circuit_breaker(self, callee_id: str) -> CircuitBreaker:
        """Get or create circuit breaker for a callee."""
        if callee_id not in self.circuit_breakers:
            self.circuit_breakers[callee_id] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=30.0,
                success_threshold=2
            )
        return self.circuit_breakers[callee_id]

    async def call_with_circuit_breaker(
        self,
        callee_id: str,
        action: str,
        payload: dict
    ) -> dict:
        """Make call with circuit breaker protection."""
        circuit = self._get_circuit_breaker(callee_id)

        # Check circuit state
        if circuit.state == CircuitState.OPEN:
            self.logger.warning(
                f"Circuit breaker OPEN for {callee_id}",
                extra={"recovery_in": circuit.time_until_recovery()}
            )
            raise TransportError(
                f"Circuit breaker open for {callee_id}",
                details={"state": "open", "callee": callee_id}
            )

        try:
            # Make the call
            result = await self.call_agent(callee_id, action, payload)

            # Record success
            circuit.record_success()
            return result

        except TransportError as e:
            # Record failure
            circuit.record_failure()

            if circuit.state == CircuitState.OPEN:
                self.logger.error(
                    f"Circuit breaker opened for {callee_id}",
                    extra={"consecutive_failures": circuit.failure_count}
                )

            raise
```

### Fallback When Circuit is Open

```python
class FallbackAgent(SecureAgent):
    @capability("search")
    async def search(self, query: str) -> dict:
        primary_service = "spiffe://yourdomain.com/agent/search-primary"
        fallback_service = "spiffe://yourdomain.com/agent/search-fallback"

        try:
            # Try primary service
            return await self.call_with_circuit_breaker(
                callee_id=primary_service,
                action="search",
                payload={"query": query}
            )

        except TransportError as e:
            # Check if circuit breaker is open
            if "circuit breaker open" in str(e).lower():
                self.logger.info(
                    "Primary service circuit open, using fallback",
                    extra={"primary": primary_service, "fallback": fallback_service}
                )

                # Use fallback service
                try:
                    return await self.call_agent(
                        callee_id=fallback_service,
                        action="search",
                        payload={"query": query}
                    )
                except Exception as fallback_error:
                    # Both services failed
                    self.logger.error(
                        "Both primary and fallback services failed",
                        extra={"error": str(fallback_error)}
                    )
                    raise

            # Not a circuit breaker issue, re-raise
            raise
```

---

## Graceful Degradation

Continue operating with reduced functionality when dependencies fail.

### Degraded Mode Pattern

```python
from enum import Enum

class ServiceMode(Enum):
    FULL = "full"
    DEGRADED = "degraded"
    EMERGENCY = "emergency"


class DegradableAgent(SecureAgent):
    def __init__(self):
        super().__init__()
        self.mode = ServiceMode.FULL
        self.failed_services = set()

    @capability("process")
    async def process(self, data: dict) -> dict:
        results = {}

        # Try enrichment service (optional)
        try:
            enrichment = await self._call_enrichment(data)
            results["enrichment"] = enrichment
        except Exception as e:
            self.logger.warning(f"Enrichment service failed: {e}")
            self._mark_service_failed("enrichment")
            results["enrichment"] = None

        # Try validation service (optional)
        try:
            validation = await self._call_validation(data)
            results["validation"] = validation
        except Exception as e:
            self.logger.warning(f"Validation service failed: {e}")
            self._mark_service_failed("validation")
            results["validation"] = None

        # Core processing (required)
        try:
            core_result = await self._core_processing(data)
            results["core"] = core_result
        except Exception as e:
            self.logger.error(f"Core processing failed: {e}")
            raise

        # Update service mode based on failures
        self._update_service_mode()

        results["mode"] = self.mode.value
        return results

    def _mark_service_failed(self, service: str):
        """Mark a service as failed."""
        self.failed_services.add(service)

    def _update_service_mode(self):
        """Update service mode based on failed services."""
        if not self.failed_services:
            self.mode = ServiceMode.FULL
        elif len(self.failed_services) < 2:
            self.mode = ServiceMode.DEGRADED
        else:
            self.mode = ServiceMode.EMERGENCY

        self.logger.info(
            f"Service mode: {self.mode.value}",
            extra={"failed_services": list(self.failed_services)}
        )
```

### Cache Fallback Pattern

```python
from typing import Optional
import json

class CachedAgent(SecureAgent):
    def __init__(self):
        super().__init__()
        self.cache = {}

    @capability("lookup")
    async def lookup(self, key: str) -> dict:
        try:
            # Try real service
            result = await self.call_agent(
                callee_id="spiffe://yourdomain.com/agent/lookup-service",
                action="lookup",
                payload={"key": key}
            )

            # Cache successful result
            self.cache[key] = result
            return result

        except TransportError as e:
            # Service unavailable, check cache
            if key in self.cache:
                self.logger.warning(
                    f"Service unavailable, using cached data for {key}",
                    extra={"error": str(e)}
                )
                return {
                    **self.cache[key],
                    "cached": True,
                    "warning": "Data may be stale"
                }
            else:
                # No cache available
                self.logger.error(f"Service unavailable and no cache for {key}")
                raise
```

---

## Logging Errors Properly

### Structured Error Logging

```python
import logging
from agentweave.exceptions import AgentWeaveError

class LoggingAgent(SecureAgent):
    def __init__(self):
        super().__init__()

        # Configure structured logging
        self.logger = logging.getLogger(__name__)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", '
            '"message": "%(message)s", "extra": %(extra)s}'
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    async def handle_with_logging(self, request: dict) -> dict:
        try:
            result = await self._process_request(request)
            return result

        except AgentWeaveError as e:
            # Log structured error with full context
            self.logger.error(
                "AgentWeave error occurred",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": e.message,
                    "error_details": e.details,
                    "request_id": request.get("id"),
                    "spiffe_id": self.identity_provider.get_spiffe_id(),
                }
            )
            raise

        except Exception as e:
            # Log unexpected errors
            self.logger.exception(
                "Unexpected error",
                extra={
                    "error_type": type(e).__name__,
                    "request_id": request.get("id"),
                }
            )
            raise
```

### Error Context for Debugging

```python
from contextvars import ContextVar
import uuid

# Context var for request tracking
request_context: ContextVar[dict] = ContextVar("request_context", default={})


class ContextualAgent(SecureAgent):
    @capability("process")
    async def process(self, data: dict) -> dict:
        # Set request context
        context = {
            "request_id": str(uuid.uuid4()),
            "caller": self.get_caller_id(),  # From request context
            "timestamp": datetime.utcnow().isoformat(),
        }
        request_context.set(context)

        try:
            result = await self._do_processing(data)
            return result

        except Exception as e:
            # Error logging includes request context automatically
            ctx = request_context.get()
            self.logger.error(
                f"Processing failed: {e}",
                extra={
                    "request_id": ctx.get("request_id"),
                    "caller": ctx.get("caller"),
                    "error": str(e),
                    "error_type": type(e).__name__,
                }
            )
            raise
        finally:
            # Clear context
            request_context.set({})
```

---

## User-Facing Error Messages

Never expose internal errors directly to users.

### Error Message Translation

```python
from agentweave.exceptions import (
    AuthorizationError,
    IdentityError,
    TransportError,
    AgentWeaveError
)

class UserFriendlyAgent(SecureAgent):
    def _translate_error(self, error: Exception) -> dict:
        """Translate internal error to user-friendly message."""
        if isinstance(error, AuthorizationError):
            return {
                "error": "You don't have permission to perform this action",
                "error_code": "FORBIDDEN",
                "status_code": 403
            }

        elif isinstance(error, IdentityError):
            return {
                "error": "Service authentication failed. Please try again later.",
                "error_code": "SERVICE_ERROR",
                "status_code": 503
            }

        elif isinstance(error, TransportError):
            return {
                "error": "Service temporarily unavailable. Please try again.",
                "error_code": "SERVICE_UNAVAILABLE",
                "status_code": 503
            }

        elif isinstance(error, AgentWeaveError):
            return {
                "error": "An internal error occurred. Please contact support.",
                "error_code": "INTERNAL_ERROR",
                "status_code": 500
            }

        else:
            # Unexpected error
            return {
                "error": "An unexpected error occurred. Please contact support.",
                "error_code": "UNKNOWN_ERROR",
                "status_code": 500
            }

    @capability("api_request")
    async def handle_api_request(self, request: dict) -> dict:
        try:
            result = await self._process_request(request)
            return {
                "status": "success",
                "data": result
            }

        except Exception as e:
            # Log internal error
            self.logger.error(
                f"Request failed: {e}",
                extra={
                    "request_id": request.get("id"),
                    "error_details": getattr(e, "details", {})
                }
            )

            # Return user-friendly error
            error_response = self._translate_error(e)
            return {
                "status": "error",
                **error_response
            }
```

---

## Related Guides

- [Testing Your Agents](testing.md) - Test error handling
- [Common Authorization Patterns](policy-patterns.md) - Prevent AuthorizationError
- [Performance Tuning](performance.md) - Configure retries and circuit breakers
- [Production Checklist](production-checklist.md) - Error handling checklist

---

## External Resources

- [Python Exception Handling Best Practices](https://realpython.com/python-exceptions/)
- [Circuit Breaker Pattern](https://martinfowler.com/bliki/CircuitBreaker.html)
- [Retry Pattern](https://docs.microsoft.com/en-us/azure/architecture/patterns/retry)
- [Graceful Degradation](https://en.wikipedia.org/wiki/Fault_tolerance)
