---
layout: page
title: Exceptions Reference
description: Complete reference for AgentWeave SDK exceptions and error handling
parent: API Reference
nav_order: 2
---

# Exceptions Reference

Complete reference for all exceptions in the AgentWeave SDK.

All SDK exceptions inherit from `AgentWeaveError`, making it easy to catch any SDK-specific error. The SDK uses specific exception types to help you handle different error conditions appropriately.

## Exception Hierarchy

```
AgentWeaveError (base)
├── IdentityError
│   └── SVIDError
├── AuthorizationError
│   └── PolicyEvaluationError
├── TransportError
│   └── PeerVerificationError
├── ConfigurationError
└── A2AProtocolError
```

---

## Base Exception

### `AgentWeaveError`

Base exception for all AgentWeave SDK errors.

All SDK exceptions inherit from this class, allowing you to catch any SDK-specific error with a single exception handler.

**Module:** `agentweave.exceptions`

**Constructor:**
```python
AgentWeaveError(message: str, details: Optional[dict] = None)
```

**Attributes:**
- `message` (str) - Human-readable error message
- `details` (dict) - Optional dictionary with additional error context

**String Representation:**

If `details` are provided, they are included in the string representation:

```python
# Without details
raise AgentWeaveError("Something went wrong")
# Output: "Something went wrong"

# With details
raise AgentWeaveError("Connection failed", {"host": "localhost", "port": 8443})
# Output: "Connection failed (host=localhost, port=8443)"
```

**Examples:**

```python
from agentweave.exceptions import AgentWeaveError

# Catch all SDK errors
try:
    agent.call_capability("search", {"query": "test"})
except AgentWeaveError as e:
    logger.error(f"SDK error: {e}")
    if e.details:
        logger.error(f"Details: {e.details}")
```

**When to Use:**

Use this as a catch-all for any SDK error when you want to handle all errors uniformly:

```python
try:
    result = await agent.call_agent(
        target="spiffe://example.com/agent/search",
        task_type="search",
        payload={"query": "machine learning"}
    )
except AgentWeaveError as e:
    # Handle any SDK error
    return {"error": str(e)}
```

---

## Identity Exceptions

### `IdentityError`

Raised when there are issues with identity management.

**Module:** `agentweave.exceptions`

**Inherits:** `AgentWeaveError`

**When Raised:**

This exception is raised when the SDK encounters problems with:
- SVID acquisition from SPIRE Workload API
- SVID rotation failures
- Trust bundle retrieval errors
- SPIFFE Workload API connection issues
- Invalid SPIFFE ID formats
- Trust domain validation failures

**Common Causes:**

1. **SPIRE Agent not running** - Cannot connect to SPIFFE Workload API socket
2. **No registration entry** - Agent not registered in SPIRE
3. **Expired SVID** - SVID expired and rotation failed
4. **Trust domain mismatch** - Peer's trust domain not in allowed list
5. **Invalid SPIFFE ID** - Malformed SPIFFE ID format

**Examples:**

```python
from agentweave.exceptions import IdentityError

try:
    agent = SecureAgent.from_config("config.yaml")
    await agent.initialize()
except IdentityError as e:
    logger.error(f"Identity acquisition failed: {e}")
    if "connection refused" in str(e).lower():
        logger.error("Is SPIRE agent running?")
    elif "not registered" in str(e).lower():
        logger.error("Agent needs to be registered with SPIRE")
```

**Handling Strategies:**

```python
# Retry with exponential backoff
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10),
    retry=retry_if_exception_type(IdentityError)
)
async def initialize_agent():
    agent = SecureAgent.from_config("config.yaml")
    await agent.initialize()
    return agent

# Graceful degradation
try:
    agent = await initialize_agent()
except IdentityError as e:
    logger.critical(f"Cannot start without identity: {e}")
    sys.exit(1)  # Cannot operate without identity
```

**Related:**
- `SVIDError` - Specific SVID issues

---

### `SVIDError`

Raised when there are specific issues with SVIDs (SPIFFE Verifiable Identity Documents).

**Module:** `agentweave.exceptions`

**Inherits:** `IdentityError`

**When Raised:**

This exception is raised for SVID-specific problems:
- SVID parsing failures
- Certificate chain validation errors
- SVID rotation failures
- Private key mismatches
- Expired SVIDs

**Common Causes:**

1. **SVID expired** - Certificate validity period has passed
2. **Parse error** - Malformed X.509 certificate
3. **Rotation failed** - Could not refresh SVID before expiration
4. **Key mismatch** - Private key doesn't match certificate public key
5. **Invalid chain** - Certificate chain validation failed

**Examples:**

```python
from agentweave.exceptions import SVIDError

try:
    await agent.rotate_svid()
except SVIDError as e:
    logger.error(f"SVID rotation failed: {e}")
    # Alert operations team
    send_alert(f"Agent SVID rotation failed: {e}")
```

**Handling Strategies:**

```python
# Monitor SVID expiration
import datetime

async def check_svid_health(agent):
    try:
        svid_info = await agent.get_svid_info()
        expires_at = svid_info["expires_at"]
        time_remaining = expires_at - datetime.datetime.utcnow()

        if time_remaining.total_seconds() < 3600:  # Less than 1 hour
            logger.warning(f"SVID expires soon: {time_remaining}")
            try:
                await agent.rotate_svid()
            except SVIDError as e:
                logger.critical(f"Emergency SVID rotation failed: {e}")
                # Trigger incident
    except SVIDError as e:
        logger.error(f"Cannot check SVID status: {e}")
```

**Related:**
- `IdentityError` - Parent exception

---

## Authorization Exceptions

### `AuthorizationError`

Raised when authorization checks fail.

**Module:** `agentweave.exceptions`

**Inherits:** `AgentWeaveError`

**When Raised:**

This exception is raised when:
- OPA policy denies the request
- Cannot connect to OPA endpoint
- Policy evaluation returns an error
- Missing required permissions
- Invalid authorization configuration

**Common Causes:**

1. **Policy denial** - OPA policy explicitly denied the request
2. **OPA unreachable** - Cannot connect to OPA endpoint
3. **Policy error** - Policy contains errors or undefined rules
4. **Timeout** - Policy evaluation timed out
5. **Missing policy** - Required policy not loaded in OPA

**Important:**

This is different from authentication (identity verification). Authorization happens after identity is successfully verified. You can be authenticated but not authorized.

**Examples:**

```python
from agentweave.exceptions import AuthorizationError

try:
    result = await agent.call_agent(
        target="spiffe://example.com/agent/sensitive-data",
        task_type="get_secrets",
        payload={}
    )
except AuthorizationError as e:
    logger.warning(f"Authorization denied: {e}")
    # Don't retry - policy denial is intentional
    return {"error": "Access denied", "reason": str(e)}
```

**Handling Strategies:**

```python
# Differentiate between policy denial and technical issues
try:
    result = await agent.call_agent(target, task_type, payload)
except AuthorizationError as e:
    if "denied" in str(e).lower():
        # Policy denial - expected behavior
        logger.info(f"Access denied by policy: {e}")
        return {"error": "Forbidden", "status": 403}
    elif "connection" in str(e).lower() or "timeout" in str(e).lower():
        # Technical issue - may be transient
        logger.error(f"Authorization system unavailable: {e}")
        return {"error": "Service Unavailable", "status": 503}
    else:
        # Unknown authorization error
        logger.error(f"Authorization error: {e}")
        return {"error": "Internal Server Error", "status": 500}

# Graceful degradation in development (NOT PRODUCTION)
try:
    result = await agent.call_agent(target, task_type, payload)
except AuthorizationError as e:
    if os.getenv("ENV") == "development":
        logger.warning(f"Auth denied but allowing in dev: {e}")
        # Dangerous - only for development!
    else:
        raise
```

**Best Practices:**

```python
# Log authorization denials for security auditing
try:
    result = await agent.call_agent(target, task_type, payload)
except AuthorizationError as e:
    audit_log.warning({
        "event": "authorization_denied",
        "caller": agent.spiffe_id,
        "target": target,
        "action": task_type,
        "reason": str(e),
        "timestamp": datetime.utcnow().isoformat()
    })
    raise
```

**Related:**
- `PolicyEvaluationError` - Technical policy evaluation issues

---

### `PolicyEvaluationError`

Raised when there are technical issues evaluating OPA policies.

**Module:** `agentweave.exceptions`

**Inherits:** `AuthorizationError`

**When Raised:**

This exception is raised for technical problems during policy evaluation:
- OPA returned malformed response
- Policy evaluation timeout
- OPA server error (HTTP 500)
- Invalid policy input document
- Network errors communicating with OPA

**Important Distinction:**

This is NOT raised for policy denials. This is only for technical issues evaluating the policy. A policy denial raises `AuthorizationError`.

**Common Causes:**

1. **Malformed response** - OPA returned invalid JSON
2. **Timeout** - Policy evaluation exceeded timeout
3. **Server error** - OPA returned HTTP 500
4. **Invalid input** - Input document doesn't match policy expectations
5. **Network error** - Connection to OPA failed mid-request

**Examples:**

```python
from agentweave.exceptions import PolicyEvaluationError
from tenacity import retry, stop_after_attempt, wait_fixed

# Retry on technical policy evaluation issues
@retry(
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    retry=retry_if_exception_type(PolicyEvaluationError)
)
async def call_with_retry(agent, target, task_type, payload):
    return await agent.call_agent(target, task_type, payload)

try:
    result = await call_with_retry(agent, target, task_type, payload)
except PolicyEvaluationError as e:
    logger.error(f"Policy evaluation failed after retries: {e}")
    # This is a system issue, not a policy denial
    # Alert operations team
    send_alert(f"OPA policy evaluation failing: {e}")
```

**Handling Strategies:**

```python
# Distinguish between policy denial and evaluation errors
try:
    result = await agent.call_agent(target, task_type, payload)
except PolicyEvaluationError as e:
    # Technical issue - should retry
    logger.error(f"Policy evaluation error (retryable): {e}")
    raise
except AuthorizationError as e:
    # Policy denial - don't retry
    logger.info(f"Policy denied request (not retrying): {e}")
    return {"error": "Forbidden"}

# Circuit breaker for OPA health
from pybreaker import CircuitBreaker

opa_breaker = CircuitBreaker(fail_max=5, timeout_duration=60)

@opa_breaker
async def check_authz(agent, target, action):
    try:
        return await agent.check_authorization(target, action)
    except PolicyEvaluationError:
        # Increment circuit breaker failure count
        raise
```

**Related:**
- `AuthorizationError` - Parent exception

---

## Transport Exceptions

### `TransportError`

Raised when there are issues with the transport layer.

**Module:** `agentweave.exceptions`

**Inherits:** `AgentWeaveError`

**When Raised:**

This exception is raised for transport-layer problems:
- mTLS connection failures
- TLS handshake errors
- Network connectivity issues
- Connection timeouts
- Circuit breaker activations
- Connection pool exhaustion
- TLS version or cipher mismatches

**Common Causes:**

1. **Connection refused** - Target agent not reachable
2. **TLS handshake failed** - Incompatible TLS versions or ciphers
3. **Connection timeout** - Network latency or unresponsive target
4. **Circuit breaker open** - Too many recent failures
5. **Pool exhausted** - All connection pool slots in use
6. **DNS resolution failed** - Cannot resolve target hostname

**Examples:**

```python
from agentweave.exceptions import TransportError

try:
    result = await agent.call_agent(
        target="spiffe://example.com/agent/remote",
        task_type="process",
        payload={"data": "test"}
    )
except TransportError as e:
    logger.error(f"Transport error: {e}")
    if e.details:
        logger.error(f"Details: {e.details}")
    # Retry with exponential backoff
```

**Handling Strategies:**

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)

# Retry with exponential backoff
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    retry=retry_if_exception_type(TransportError)
)
async def call_with_retry(agent, target, task_type, payload):
    return await agent.call_agent(target, task_type, payload)

try:
    result = await call_with_retry(agent, target, task_type, payload)
except TransportError as e:
    logger.error(f"Transport error after all retries: {e}")
    # Fallback strategy
    return await fallback_handler(task_type, payload)

# Circuit breaker pattern
from pybreaker import CircuitBreaker

breaker = CircuitBreaker(fail_max=5, timeout_duration=60)

@breaker
async def call_agent_with_breaker(agent, target, task_type, payload):
    try:
        return await agent.call_agent(target, task_type, payload)
    except TransportError:
        # Let circuit breaker track failures
        raise

# Timeout with fallback
import asyncio

try:
    result = await asyncio.wait_for(
        agent.call_agent(target, task_type, payload),
        timeout=10.0
    )
except asyncio.TimeoutError:
    logger.warning("Call timed out, using fallback")
    result = await fallback_handler(task_type, payload)
except TransportError as e:
    logger.error(f"Transport error: {e}")
    raise
```

**Related:**
- `PeerVerificationError` - Specific peer identity issues

---

### `PeerVerificationError`

Raised when peer identity verification fails.

**Module:** `agentweave.exceptions`

**Inherits:** `TransportError`

**When Raised:**

This exception is raised when the peer's SPIFFE ID does not match expectations or cannot be verified:
- Peer SPIFFE ID doesn't match expected ID
- Cannot extract SPIFFE ID from peer certificate
- Peer certificate chain validation failed
- Trust domain not in allowed list
- Peer certificate expired or not yet valid

**Common Causes:**

1. **SPIFFE ID mismatch** - Expected one ID, got another
2. **Trust domain mismatch** - Peer from untrusted domain
3. **Certificate validation failed** - Invalid cert chain
4. **Cannot extract SPIFFE ID** - Certificate doesn't contain SPIFFE ID
5. **Expired certificate** - Peer's certificate expired

**Examples:**

```python
from agentweave.exceptions import PeerVerificationError

try:
    result = await agent.call_agent(
        target="spiffe://example.com/agent/trusted",
        task_type="process",
        payload={"data": "test"}
    )
except PeerVerificationError as e:
    logger.critical(f"Peer identity verification failed: {e}")
    # This is a security issue - don't retry
    # Alert security team
    send_security_alert(f"Peer verification failed: {e}")
    raise
```

**Important Security Note:**

`PeerVerificationError` indicates a potential security issue. Unlike `TransportError` (which might be transient), peer verification failures should NOT be automatically retried without investigation.

**Handling Strategies:**

```python
# Log security events
try:
    result = await agent.call_agent(target, task_type, payload)
except PeerVerificationError as e:
    security_audit_log.critical({
        "event": "peer_verification_failed",
        "expected": target,
        "actual": e.details.get("actual_spiffe_id"),
        "reason": str(e),
        "timestamp": datetime.utcnow().isoformat()
    })
    # Don't retry - this is a security issue
    raise

# Strict vs lenient modes (for testing only)
try:
    result = await agent.call_agent(target, task_type, payload)
except PeerVerificationError as e:
    if os.getenv("ENV") == "test" and os.getenv("ALLOW_ANY_PEER") == "true":
        logger.warning(f"Peer verification failed but allowing in test mode: {e}")
        # DANGEROUS - only for isolated test environments
    else:
        # Production - always fail
        logger.critical(f"Peer verification failed: {e}")
        raise
```

**Expected vs Actual:**

```python
# The exception details often include expected vs actual SPIFFE IDs
try:
    result = await agent.call_agent(
        target="spiffe://agentweave.io/agent/search",
        task_type="search",
        payload={"query": "test"}
    )
except PeerVerificationError as e:
    expected = e.details.get("expected_spiffe_id")
    actual = e.details.get("actual_spiffe_id")
    logger.critical(
        f"SPIFFE ID mismatch! Expected: {expected}, Actual: {actual}"
    )
```

**Related:**
- `TransportError` - Parent exception

---

## Configuration Exceptions

### `ConfigurationError`

Raised when there are issues with agent configuration.

**Module:** `agentweave.exceptions`

**Inherits:** `AgentWeaveError`

**When Raised:**

This exception is raised for configuration problems:
- Invalid configuration files
- Validation failures
- Missing required fields
- Insecure configuration in production mode
- Invalid YAML syntax
- Environment variable errors
- Security constraint violations

**Common Causes:**

1. **Missing required field** - Required configuration key not present
2. **Security violation** - Insecure setting in production (e.g., `peer_verification: none`)
3. **Invalid YAML** - Syntax errors in configuration file
4. **Invalid value** - Configuration value doesn't meet constraints
5. **TLS version too low** - Minimum TLS version not met

**Important:**

Configuration errors are typically caught at startup, preventing the agent from running with insecure or invalid settings. This is by design - the agent will not start if configuration is invalid.

**Examples:**

```python
from agentweave.exceptions import ConfigurationError

try:
    agent = SecureAgent.from_config("config.yaml")
except ConfigurationError as e:
    logger.critical(f"Invalid configuration: {e}")
    if "peer_verification" in str(e):
        logger.critical("peer_verification must be 'strict' in production")
    elif "default_action" in str(e):
        logger.critical("default_action must be 'deny' in production")
    sys.exit(1)  # Cannot start with invalid config
```

**Validation Examples:**

```python
# The SDK validates security settings at startup
# These will raise ConfigurationError:

# ✗ Peer verification cannot be 'none'
config = {
    "transport": {
        "peer_verification": "none"  # ConfigurationError
    }
}

# ✗ Default action must be 'deny' in production
config = {
    "authorization": {
        "default_action": "allow"  # ConfigurationError in production
    }
}

# ✗ TLS version too low
config = {
    "transport": {
        "tls_min_version": "1.0"  # ConfigurationError
    }
}

# ✓ Valid configuration
config = {
    "transport": {
        "peer_verification": "strict",
        "tls_min_version": "1.3"
    },
    "authorization": {
        "default_action": "deny"
    }
}
```

**Handling Strategies:**

```python
# Validate configuration before deployment (CI/CD)
def validate_config(config_path):
    try:
        config = load_config(config_path)
        # SDK validates on load
        agent = SecureAgent.from_config(config)
        return True
    except ConfigurationError as e:
        logger.error(f"Configuration validation failed: {e}")
        return False

# In CI/CD pipeline
if not validate_config("config.yaml"):
    sys.exit(1)  # Fail the build

# Provide helpful error messages
try:
    agent = SecureAgent.from_config("config.yaml")
except ConfigurationError as e:
    if "default_action" in str(e):
        print("ERROR: default_action must be 'deny' in production")
        print("Fix: Set authorization.default_action: deny")
    elif "peer_verification" in str(e):
        print("ERROR: peer_verification cannot be 'none'")
        print("Fix: Set transport.peer_verification: strict")
    else:
        print(f"Configuration error: {e}")
    sys.exit(1)
```

**Security Constraints:**

The SDK enforces these security constraints in production:

1. `transport.peer_verification` must be `"strict"` (not `"none"` or `"optional"`)
2. `authorization.default_action` must be `"deny"` (not `"allow"` or `"log-only"`)
3. `transport.tls_min_version` must be `"1.2"` or higher
4. `identity.provider` must be `"spiffe"` (not `"none"` or `"static"`)

**Related:**
- None - standalone exception

---

## Protocol Exceptions

### `A2AProtocolError`

Raised when there are issues with A2A protocol communication.

**Module:** `agentweave.exceptions`

**Inherits:** `AgentWeaveError`

**When Raised:**

This exception is raised for A2A protocol violations:
- Invalid Agent Card format
- Task lifecycle violations
- Protocol version mismatches
- Invalid message structure
- Discovery endpoint failures
- Malformed JSON-RPC requests/responses

**Important:**

This is separate from `TransportError` (connection issues) and `AuthorizationError` (permission issues). This focuses on the A2A protocol layer specifically.

**Common Causes:**

1. **Invalid Agent Card** - Missing required fields or malformed JSON
2. **Task state violation** - Invalid task state transition
3. **Version mismatch** - Unsupported A2A protocol version
4. **Malformed JSON-RPC** - Invalid request/response structure
5. **Discovery failure** - Cannot fetch `/.well-known/agent.json`
6. **Invalid capability** - Requested capability not in Agent Card

**Examples:**

```python
from agentweave.exceptions import A2AProtocolError

try:
    result = await agent.call_agent(
        target="spiffe://example.com/agent/search",
        task_type="search",
        payload={"query": "test"}
    )
except A2AProtocolError as e:
    logger.error(f"A2A protocol error: {e}")
    if "capability not found" in str(e).lower():
        logger.error("Target agent doesn't support this capability")
    elif "agent card" in str(e).lower():
        logger.error("Target agent's Agent Card is invalid")
```

**Agent Card Validation:**

```python
# The SDK validates Agent Cards automatically
try:
    agent_card = await agent.discover_agent(
        "spiffe://example.com/agent/search"
    )
except A2AProtocolError as e:
    logger.error(f"Invalid Agent Card: {e}")
    # Details might include:
    # - Missing required fields
    # - Invalid capability structure
    # - Malformed JSON
```

**Task Lifecycle Violations:**

```python
# Tasks have specific lifecycle states
# Invalid transitions raise A2AProtocolError

try:
    # Create task
    task = await agent.create_task(target, task_type, payload)

    # Can't complete a task that's already completed
    await task.complete()
    await task.complete()  # A2AProtocolError: Task already completed

except A2AProtocolError as e:
    logger.error(f"Invalid task state transition: {e}")
```

**Handling Strategies:**

```python
# Validate Agent Card before calling
try:
    agent_card = await agent.discover_agent(target)

    # Check if capability exists
    capabilities = [c["name"] for c in agent_card["capabilities"]]
    if task_type not in capabilities:
        logger.error(f"Capability {task_type} not supported by {target}")
        return {"error": "Capability not supported"}

    # Proceed with call
    result = await agent.call_agent(target, task_type, payload)

except A2AProtocolError as e:
    logger.error(f"Protocol error: {e}")
    # Don't retry - protocol errors usually indicate bugs
    return {"error": "Protocol error", "details": str(e)}

# Version negotiation
try:
    result = await agent.call_agent(target, task_type, payload)
except A2AProtocolError as e:
    if "version" in str(e).lower():
        logger.error(f"A2A protocol version mismatch: {e}")
        # Try to negotiate version or use fallback
        # This is advanced - usually indicates incompatible agents
    raise
```

**Related:**
- None - standalone exception

---

## Exception Handling Patterns

### Catch All SDK Errors

```python
from agentweave.exceptions import AgentWeaveError

try:
    result = await agent.call_agent(target, task_type, payload)
except AgentWeaveError as e:
    logger.error(f"SDK error: {e}")
    if e.details:
        logger.error(f"Details: {e.details}")
```

### Specific Exception Handling

```python
from agentweave.exceptions import (
    IdentityError,
    AuthorizationError,
    TransportError,
    PeerVerificationError
)

try:
    result = await agent.call_agent(target, task_type, payload)
except PeerVerificationError as e:
    # Security issue - alert and don't retry
    logger.critical(f"Peer verification failed: {e}")
    send_security_alert(str(e))
    raise
except AuthorizationError as e:
    # Policy denial - log and return error
    logger.warning(f"Authorization denied: {e}")
    return {"error": "Forbidden", "status": 403}
except TransportError as e:
    # Network issue - retry with backoff
    logger.error(f"Transport error: {e}")
    raise  # Let retry decorator handle it
except IdentityError as e:
    # Identity issue - critical error
    logger.critical(f"Identity error: {e}")
    sys.exit(1)
```

### Retry Patterns

```python
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type
)
from agentweave.exceptions import TransportError, PolicyEvaluationError

# Retry transient errors
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((TransportError, PolicyEvaluationError))
)
async def call_with_retry(agent, target, task_type, payload):
    return await agent.call_agent(target, task_type, payload)

# Don't retry security or policy denials
from agentweave.exceptions import AuthorizationError, PeerVerificationError

try:
    result = await call_with_retry(agent, target, task_type, payload)
except (AuthorizationError, PeerVerificationError) as e:
    # These should not be retried
    logger.error(f"Non-retryable error: {e}")
    raise
```

### Circuit Breaker Pattern

```python
from pybreaker import CircuitBreaker
from agentweave.exceptions import TransportError, PolicyEvaluationError

# Create circuit breaker
breaker = CircuitBreaker(fail_max=5, timeout_duration=60)

@breaker
async def call_with_breaker(agent, target, task_type, payload):
    try:
        return await agent.call_agent(target, task_type, payload)
    except (TransportError, PolicyEvaluationError):
        # Let circuit breaker track failures
        raise

# Use circuit breaker
try:
    result = await call_with_breaker(agent, target, task_type, payload)
except Exception as e:
    if breaker.opened:
        logger.error("Circuit breaker is open - too many failures")
    else:
        logger.error(f"Call failed: {e}")
```

### Logging and Monitoring

```python
from agentweave.exceptions import AgentWeaveError
import structlog

logger = structlog.get_logger()

try:
    result = await agent.call_agent(target, task_type, payload)
except AgentWeaveError as e:
    logger.error(
        "agent_call_failed",
        exception_type=type(e).__name__,
        message=str(e),
        details=e.details,
        target=target,
        task_type=task_type
    )

    # Emit metric
    metrics.increment(
        "agent.call.errors",
        tags=[
            f"exception:{type(e).__name__}",
            f"target:{target}",
            f"task_type:{task_type}"
        ]
    )
```

### Graceful Degradation

```python
from agentweave.exceptions import TransportError, AuthorizationError

async def call_with_fallback(agent, target, task_type, payload):
    try:
        # Try primary agent
        return await agent.call_agent(target, task_type, payload)
    except TransportError as e:
        logger.warning(f"Primary agent unavailable: {e}")
        # Try fallback agent
        fallback_target = get_fallback_target(target)
        if fallback_target:
            logger.info(f"Trying fallback: {fallback_target}")
            return await agent.call_agent(fallback_target, task_type, payload)
        else:
            raise
    except AuthorizationError:
        # Don't fallback on authz errors
        raise
```

---

## Best Practices

### 1. Always Catch Specific Exceptions

```python
# Good - specific handling
try:
    result = await agent.call_agent(target, task_type, payload)
except AuthorizationError as e:
    return {"error": "Forbidden"}
except TransportError as e:
    return {"error": "Service Unavailable"}

# Avoid - too broad
try:
    result = await agent.call_agent(target, task_type, payload)
except Exception as e:  # Too broad
    pass
```

### 2. Don't Retry Security Errors

```python
# Good - don't retry security errors
try:
    result = await call_with_retry(agent, target, task_type, payload)
except (PeerVerificationError, AuthorizationError):
    # Security errors should not be retried
    raise

# Bad - retrying everything
@retry(stop=stop_after_attempt(10))  # Don't do this
async def call_agent_retry_everything(...):
    # This will retry security errors - bad!
    pass
```

### 3. Log with Context

```python
# Good - include context
try:
    result = await agent.call_agent(target, task_type, payload)
except AgentWeaveError as e:
    logger.error(
        f"Agent call failed: {e}",
        extra={
            "target": target,
            "task_type": task_type,
            "exception_type": type(e).__name__,
            "details": e.details
        }
    )

# Avoid - missing context
try:
    result = await agent.call_agent(target, task_type, payload)
except AgentWeaveError as e:
    logger.error(str(e))  # Missing context
```

### 4. Use Exception Details

```python
# Good - use exception details
try:
    result = await agent.call_agent(target, task_type, payload)
except AgentWeaveError as e:
    logger.error(f"Error: {e}")
    if e.details:
        for key, value in e.details.items():
            logger.error(f"  {key}: {value}")

# Avoid - ignoring details
try:
    result = await agent.call_agent(target, task_type, payload)
except AgentWeaveError as e:
    pass  # Details ignored
```

### 5. Fail Fast on Configuration Errors

```python
# Good - fail at startup
def main():
    try:
        agent = SecureAgent.from_config("config.yaml")
    except ConfigurationError as e:
        logger.critical(f"Invalid configuration: {e}")
        sys.exit(1)  # Don't continue with invalid config

    # Start agent
    agent.run()

# Avoid - catching and continuing
try:
    agent = SecureAgent.from_config("config.yaml")
except ConfigurationError:
    agent = None  # Don't do this
```

---

## See Also

- [CLI Reference](cli.md) - Command-line tools
- [Configuration Reference](../configuration.md) - Configuration options
- [Security Guide](../security.md) - Security best practices
