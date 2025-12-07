---
layout: page
title: Authorization Module
description: API reference for the agentweave.authz module
nav_order: 2
parent: API Reference
---

# Authorization Module

The `agentweave.authz` module provides policy-based authorization using Open Policy Agent (OPA). All agent-to-agent communication is subject to authorization checks to enforce fine-grained access control.

## Module Overview

```python
from agentweave.authz import (
    AuthorizationProvider,     # Abstract base class
    AuthzDecision,            # Authorization decision dataclass
    OPAProvider,              # OPA implementation
    AuthorizationError,       # Base exception
    PolicyEvaluationError,    # Policy evaluation errors
    CircuitBreakerError,      # Circuit breaker errors
)
```

## Classes

### AuthorizationProvider

Abstract base class that defines the interface for all authorization providers.

```python
from abc import ABC, abstractmethod
from typing import Optional

class AuthorizationProvider(ABC):
    """Abstract base class for authorization providers."""
```

Implementations must enforce fine-grained access control based on:
- Caller identity (SPIFFE ID)
- Resource being accessed
- Action being performed
- Additional context (request metadata, environment, etc.)

#### Methods

##### check()

Check if a caller is authorized to perform an action on a resource.

```python
async def check(
    self,
    caller_id: str,
    resource: str,
    action: str,
    context: Optional[dict] = None
) -> AuthzDecision
```

**Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `caller_id` | `str` | SPIFFE ID of the caller | Required |
| `resource` | `str` | Resource being accessed (e.g., SPIFFE ID of target agent) | Required |
| `action` | `str` | Action being performed (e.g., "search", "process") | Required |
| `context` | `Optional[dict]` | Additional context for policy evaluation | `None` |

**Returns:**
- `AuthzDecision`: Authorization decision with result and metadata

**Raises:**
- `AuthorizationError`: If the authorization check fails

**Example:**

```python
decision = await provider.check(
    caller_id="spiffe://agentweave.io/agent/frontend",
    resource="spiffe://agentweave.io/agent/database",
    action="query",
    context={"request_id": "123", "environment": "production"}
)

if decision.allowed:
    # Proceed with request
    pass
else:
    # Deny request
    raise PermissionDenied(decision.reason)
```

---

##### health_check()

Check if the authorization provider is healthy and reachable.

```python
async def health_check(self) -> bool
```

**Returns:**
- `bool`: True if healthy, False otherwise

**Example:**

```python
if await provider.health_check():
    print("Authorization provider is healthy")
else:
    print("Authorization provider is unhealthy")
```

---

### AuthzDecision

Authorization decision result dataclass.

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class AuthzDecision:
    """Authorization decision result."""
    allowed: bool
    reason: str
    policy_id: Optional[str] = None
    audit_id: str = ""
```

This immutable dataclass represents the result of an authorization check.

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `allowed` | `bool` | Whether the action is permitted |
| `reason` | `str` | Human-readable explanation for the decision |
| `policy_id` | `Optional[str]` | ID of the policy that made the decision (if applicable) |
| `audit_id` | `str` | Unique identifier for audit trail correlation (auto-generated if not provided) |

#### Usage Examples

```python
# Allow decision
decision = AuthzDecision(
    allowed=True,
    reason="Caller has admin role",
    policy_id="admin-access-policy"
)

# Deny decision
decision = AuthzDecision(
    allowed=False,
    reason="Caller not in allowed trust domain",
    policy_id="trust-domain-policy"
)

# Access decision fields
if decision.allowed:
    print(f"Access granted: {decision.reason}")
    print(f"Audit ID: {decision.audit_id}")
else:
    print(f"Access denied: {decision.reason}")
```

---

### OPAProvider

OPA-based authorization provider with circuit breaker and caching.

```python
class OPAProvider(AuthorizationProvider):
    """OPA-based authorization provider."""
```

Features:
- REST API integration with OPA
- Circuit breaker for OPA failures
- Decision caching with TTL
- Automatic audit logging
- Default deny in production mode
- SPIFFE ID aware policy context

#### Constructor

```python
def __init__(
    self,
    endpoint: str = "http://localhost:8181",
    policy_path: str = "agentweave/authz/allow",
    default_deny: bool = True,
    cache_ttl: float = 60.0,
    cache_size: int = 1000,
    timeout: float = 5.0,
    circuit_breaker_threshold: int = 5,
    circuit_breaker_timeout: float = 30.0
)
```

**Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `endpoint` | `str` | OPA server base URL | `"http://localhost:8181"` |
| `policy_path` | `str` | Path to the policy decision endpoint (relative to `/v1/data/`) | `"agentweave/authz/allow"` |
| `default_deny` | `bool` | If True, deny requests when OPA is unavailable. **Should always be True in production.** | `True` |
| `cache_ttl` | `float` | Cache TTL in seconds | `60.0` |
| `cache_size` | `int` | Maximum number of cached decisions (LRU eviction) | `1000` |
| `timeout` | `float` | Request timeout in seconds | `5.0` |
| `circuit_breaker_threshold` | `int` | Number of consecutive failures before opening circuit | `5` |
| `circuit_breaker_timeout` | `float` | Seconds before attempting recovery from OPEN state | `30.0` |

**Example:**

```python
from agentweave.authz import OPAProvider

# Default configuration
provider = OPAProvider()

# Production configuration
provider = OPAProvider(
    endpoint="http://opa.internal:8181",
    policy_path="agentweave/authz/allow",
    default_deny=True,  # Always deny when OPA unavailable
    cache_ttl=120.0,   # Cache for 2 minutes
    timeout=10.0,      # 10 second timeout
)

# Development configuration (NOT for production)
provider = OPAProvider(
    endpoint="http://localhost:8181",
    default_deny=False,  # Allow when OPA unavailable (dev only!)
    cache_ttl=10.0,
)
```

#### Methods

##### check()

Check authorization via OPA.

```python
async def check(
    self,
    caller_id: str,
    resource: str,
    action: str,
    context: Optional[dict] = None
) -> AuthzDecision
```

This method:
1. Checks the decision cache first
2. Builds OPA input document with SPIFFE context
3. Queries OPA via circuit breaker protection
4. Caches the decision
5. Audit logs the decision

**Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `caller_id` | `str` | SPIFFE ID of the caller | Required |
| `resource` | `str` | Resource being accessed (typically target SPIFFE ID) | Required |
| `action` | `str` | Action being performed | Required |
| `context` | `Optional[dict]` | Additional context for policy evaluation | `None` |

**Returns:**
- `AuthzDecision`: The authorization decision

**Example:**

```python
decision = await provider.check(
    caller_id="spiffe://agentweave.io/agent/search/prod",
    resource="spiffe://agentweave.io/agent/database/prod",
    action="read",
    context={
        "query_type": "customer_data",
        "environment": "production",
        "request_id": "req-12345"
    }
)

if decision.allowed:
    # Execute the action
    result = await perform_action()
else:
    # Log denial and reject
    logger.warning(
        f"Access denied: {decision.reason} "
        f"(audit_id={decision.audit_id})"
    )
    raise PermissionDenied(decision.reason)
```

**OPA Input Document Format:**

The provider builds an input document with the following structure:

```json
{
  "caller_spiffe_id": "spiffe://agentweave.io/agent/search/prod",
  "resource_spiffe_id": "spiffe://agentweave.io/agent/database/prod",
  "action": "read",
  "timestamp": "2025-12-07T12:34:56.789Z",
  "caller_trust_domain": "agentweave.io",
  "resource_trust_domain": "agentweave.io",
  "context": {
    "query_type": "customer_data",
    "environment": "production",
    "request_id": "req-12345"
  }
}
```

**OPA Response Format:**

OPA can return either a boolean or an object:

```json
// Boolean response
{"result": true}

// Object response
{
  "result": {
    "allow": true,
    "reason": "Caller has read permission",
    "policy_id": "database-read-policy"
  }
}
```

---

##### health_check()

Check if OPA is healthy and reachable.

```python
async def health_check(self) -> bool
```

Sends a GET request to the OPA `/health` endpoint.

**Returns:**
- `bool`: True if OPA is healthy (HTTP 200), False otherwise

**Example:**

```python
if await provider.health_check():
    await agent.start()
else:
    logger.error("OPA is unhealthy, cannot start agent")
    sys.exit(1)
```

---

##### close()

Close the HTTP client.

```python
async def close(self) -> None
```

Call this to cleanup the internal HTTP client when shutting down.

**Example:**

```python
try:
    # Use provider
    await provider.check(...)
finally:
    await provider.close()
```

---

### CircuitBreaker

Circuit breaker for protecting against OPA failures.

```python
class CircuitBreaker:
    """Circuit breaker for OPA failures."""
```

The circuit breaker has three states:

| State | Description | Behavior |
|-------|-------------|----------|
| `CLOSED` | Normal operation | All requests pass through to OPA |
| `OPEN` | Too many failures | Requests fail immediately without calling OPA |
| `HALF_OPEN` | Testing recovery | Limited requests pass through to test if OPA recovered |

#### Constructor

```python
def __init__(
    self,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    success_threshold: int = 2
)
```

**Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `failure_threshold` | `int` | Number of consecutive failures before opening circuit | `5` |
| `recovery_timeout` | `float` | Seconds to wait in OPEN state before entering HALF_OPEN | `30.0` |
| `success_threshold` | `int` | Number of consecutive successes in HALF_OPEN to close circuit | `2` |

#### State Transitions

```
CLOSED --[failure_threshold failures]--> OPEN
OPEN --[recovery_timeout elapsed]--> HALF_OPEN
HALF_OPEN --[success_threshold successes]--> CLOSED
HALF_OPEN --[any failure]--> OPEN
```

#### Behavior

- **CLOSED**: Normal operation, failures increment counter
- **OPEN**: Immediately raises `CircuitBreakerError` without calling OPA
- **HALF_OPEN**: Allows requests through; success closes circuit, failure opens it

---

### DecisionCache

LRU cache for authorization decisions with TTL.

```python
class DecisionCache:
    """LRU cache for authorization decisions with TTL."""
```

Caches authorization decisions to reduce load on OPA and improve performance.

#### Constructor

```python
def __init__(
    self,
    max_size: int = 1000,
    ttl_seconds: float = 60.0
)
```

**Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `max_size` | `int` | Maximum number of cached decisions | `1000` |
| `ttl_seconds` | `float` | Time-to-live for cached decisions in seconds | `60.0` |

#### Behavior

- **LRU Eviction**: When cache is full, least recently used entries are evicted
- **TTL Expiration**: Entries older than TTL are automatically expired on access
- **Cache Key**: Hash of (caller_id, resource, action, context)

---

## Usage Examples

### Basic Usage

```python
from agentweave.authz import OPAProvider

# Create provider
provider = OPAProvider(
    endpoint="http://opa:8181",
    policy_path="agentweave/authz/allow",
    default_deny=True
)

# Check authorization
decision = await provider.check(
    caller_id="spiffe://agentweave.io/agent/api",
    resource="spiffe://agentweave.io/agent/database",
    action="write"
)

if decision.allowed:
    await database.write(data)
else:
    raise PermissionDenied(decision.reason)

# Cleanup
await provider.close()
```

### With Context

```python
decision = await provider.check(
    caller_id="spiffe://agentweave.io/agent/frontend",
    resource="spiffe://agentweave.io/agent/payment",
    action="process_payment",
    context={
        "amount": 1000.00,
        "currency": "USD",
        "user_id": "user-12345",
        "environment": "production",
        "request_id": "req-abc123"
    }
)

if not decision.allowed:
    logger.warning(
        f"Payment processing denied: {decision.reason} "
        f"(audit_id={decision.audit_id})"
    )
```

### Custom Configuration

```python
from agentweave.authz import OPAProvider

provider = OPAProvider(
    endpoint="https://opa.production.internal:8181",
    policy_path="myorg/agent_authz/allow",
    default_deny=True,          # Always deny when OPA unavailable
    cache_ttl=300.0,           # Cache for 5 minutes
    cache_size=5000,           # Large cache
    timeout=10.0,              # 10 second timeout
    circuit_breaker_threshold=3,  # Open after 3 failures
    circuit_breaker_timeout=60.0  # Wait 60s before retry
)
```

### Health Monitoring

```python
import asyncio
from agentweave.authz import OPAProvider

async def monitor_opa_health(provider: OPAProvider):
    """Monitor OPA health and alert on failures."""
    while True:
        is_healthy = await provider.health_check()

        if not is_healthy:
            logger.error("OPA health check failed!")
            # Send alert, trigger runbook, etc.

        await asyncio.sleep(30)  # Check every 30 seconds

provider = OPAProvider()
asyncio.create_task(monitor_opa_health(provider))
```

### Error Handling

```python
from agentweave.authz import (
    OPAProvider,
    AuthorizationError,
    PolicyEvaluationError,
    CircuitBreakerError
)

provider = OPAProvider(default_deny=True)

try:
    decision = await provider.check(
        caller_id="spiffe://agentweave.io/agent/test",
        resource="spiffe://agentweave.io/agent/prod",
        action="delete"
    )

except CircuitBreakerError:
    logger.error("Circuit breaker is open, OPA unavailable")
    # Fall back to default deny
    decision = AuthzDecision(
        allowed=False,
        reason="Circuit breaker open",
        policy_id="circuit-breaker"
    )

except PolicyEvaluationError as e:
    logger.error(f"Policy evaluation failed: {e}")
    # Fall back to default deny
    decision = AuthzDecision(
        allowed=False,
        reason=f"Policy evaluation error: {e}",
        policy_id="error-fallback"
    )

except AuthorizationError as e:
    logger.error(f"Authorization check failed: {e}")
    raise
```

### Cache Usage

```python
from agentweave.authz import OPAProvider

# Configure aggressive caching
provider = OPAProvider(
    cache_ttl=600.0,   # 10 minute TTL
    cache_size=10000   # Large cache
)

# First call - cache miss, queries OPA
decision1 = await provider.check(
    caller_id="spiffe://agentweave.io/agent/a",
    resource="spiffe://agentweave.io/agent/b",
    action="read"
)

# Second call - cache hit, no OPA query
decision2 = await provider.check(
    caller_id="spiffe://agentweave.io/agent/a",
    resource="spiffe://agentweave.io/agent/b",
    action="read"
)

# Different context - cache miss
decision3 = await provider.check(
    caller_id="spiffe://agentweave.io/agent/a",
    resource="spiffe://agentweave.io/agent/b",
    action="read",
    context={"user": "different"}  # Different cache key
)
```

---

## Exceptions

### AuthorizationError

Base exception for authorization-related errors.

```python
class AuthorizationError(Exception):
    """Raised when authorization check fails."""
```

**Usage:**

```python
from agentweave.authz import AuthorizationError

try:
    decision = await provider.check(...)
except AuthorizationError as e:
    logger.error(f"Authorization failed: {e}")
```

---

### PolicyEvaluationError

Raised when OPA policy evaluation fails.

```python
class PolicyEvaluationError(AuthorizationError):
    """Raised when OPA policy evaluation fails."""
```

This is a specific type of AuthorizationError that occurs when there are technical issues evaluating the policy (not policy denials).

**Examples:**
- OPA returned malformed response
- Policy evaluation timeout
- OPA server error (500)
- Invalid policy input document

**Usage:**

```python
from agentweave.authz import PolicyEvaluationError

try:
    decision = await provider.check(...)
except PolicyEvaluationError as e:
    logger.error(f"Policy evaluation failed: {e}")
    # Fall back to default deny
```

---

### CircuitBreakerError

Raised when circuit breaker is open.

```python
class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
```

**Usage:**

```python
from agentweave.authz import CircuitBreakerError

try:
    decision = await provider.check(...)
except CircuitBreakerError:
    logger.warning("Circuit breaker open, OPA unavailable")
    # Apply default policy
```

---

## OPA Policy Examples

### Basic Allow Policy

```rego
package agentweave.authz

default allow = false

# Allow all agents in same trust domain
allow {
    input.caller_trust_domain == input.resource_trust_domain
}
```

### Role-Based Access Control

```rego
package agentweave.authz

default allow = {
    "allow": false,
    "reason": "Default deny"
}

# Admin agents can do anything
allow = {
    "allow": true,
    "reason": "Caller has admin role",
    "policy_id": "admin-access"
} {
    contains(input.caller_spiffe_id, "/admin/")
}

# Read-only agents can only read
allow = {
    "allow": true,
    "reason": "Caller has read role",
    "policy_id": "read-access"
} {
    contains(input.caller_spiffe_id, "/reader/")
    input.action == "read"
}
```

### Environment-Based Access

```rego
package agentweave.authz

default allow = false

# Production agents can only access production
allow {
    contains(input.caller_spiffe_id, "/prod/")
    contains(input.resource_spiffe_id, "/prod/")
}

# Dev agents can only access dev
allow {
    contains(input.caller_spiffe_id, "/dev/")
    contains(input.resource_spiffe_id, "/dev/")
}
```

---

## Best Practices

### 1. Always Use Default Deny in Production

```python
# GOOD - Production
provider = OPAProvider(default_deny=True)

# BAD - Never in production!
provider = OPAProvider(default_deny=False)
```

### 2. Configure Appropriate Cache TTL

```python
# For frequently changing policies - short TTL
provider = OPAProvider(cache_ttl=10.0)

# For stable policies - longer TTL
provider = OPAProvider(cache_ttl=300.0)
```

### 3. Monitor Circuit Breaker State

```python
if provider._circuit_breaker.state == "OPEN":
    logger.error("Circuit breaker is OPEN!")
    # Alert operations team
```

### 4. Include Rich Context

```python
decision = await provider.check(
    caller_id=caller,
    resource=resource,
    action=action,
    context={
        "request_id": request_id,
        "environment": environment,
        "user_id": user_id,
        "timestamp": datetime.utcnow().isoformat(),
        # Include any data needed for policy decisions
    }
)
```

### 5. Log Denials for Security Auditing

```python
decision = await provider.check(...)

if not decision.allowed:
    logger.warning(
        f"AUTHZ_DENY: {decision.audit_id} | "
        f"caller={caller_id} | "
        f"resource={resource} | "
        f"action={action} | "
        f"reason={decision.reason}"
    )
```

### 6. Use Health Checks in Readiness Probes

```python
# Kubernetes readiness probe
async def readiness():
    return await authz_provider.health_check()
```

---

## See Also

- [Identity Module](identity.md) - Cryptographic identity management
- [Security Guide](../security.md) - Security architecture and best practices
- [OPA Documentation](https://www.openpolicyagent.org/docs/) - Official OPA documentation
- [Rego Language](https://www.openpolicyagent.org/docs/latest/policy-language/) - OPA policy language reference
