---
layout: api
title: Observability Module API Reference
parent: API Reference
nav_order: 3
---

# Observability Module API Reference

The `agentweave.observability` module provides comprehensive monitoring, tracing, logging, and auditing capabilities for secure agents.

**Key Features:**
- Prometheus metrics collection
- OpenTelemetry distributed tracing
- Structured JSON logging
- Security audit trails
- Trace context propagation
- Multiple audit backends

---

## Metrics

### MetricsCollector

**Import:** `from agentweave.observability import MetricsCollector`

Collects and exposes Prometheus metrics for secure agents.

#### Constructor

```python
MetricsCollector(
    agent_name: str,
    registry: CollectorRegistry | None = None,
    enabled: bool = True
)
```

**Parameters:**
- `agent_name` (str): Name of the agent (added as label to all metrics)
- `registry` (CollectorRegistry, optional): Prometheus registry (defaults to global REGISTRY)
- `enabled` (bool): Whether metrics collection is enabled (default: True)

#### Available Metrics

##### Counters

**agentweave_requests_total**
- Description: Total number of requests received
- Labels: `agent_name`, `capability`, `status`

**agentweave_auth_decisions_total**
- Description: Total number of authorization decisions
- Labels: `agent_name`, `peer_id`, `capability`, `decision`

**agentweave_errors_total**
- Description: Total number of errors
- Labels: `agent_name`, `error_type`, `capability`

##### Histograms

**agentweave_request_duration_seconds**
- Description: Request processing duration in seconds
- Labels: `agent_name`, `capability`, `status`
- Buckets: 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0

**agentweave_auth_check_duration_seconds**
- Description: Authorization check duration in seconds
- Labels: `agent_name`, `peer_id`, `capability`
- Buckets: 0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0

##### Gauges

**agentweave_active_connections**
- Description: Number of active connections
- Labels: `agent_name`, `peer_id`

**agentweave_circuit_breaker_state**
- Description: Circuit breaker state (0=closed, 1=open, 2=half-open)
- Labels: `agent_name`, `peer_id`

#### Methods

##### record_request
```python
def record_request(capability: str, status: str) -> None
```
Record a completed request.

**Parameters:**
- `capability` (str): Capability that was invoked
- `status` (str): Status of the request (success, error, denied)

##### record_auth_decision
```python
def record_auth_decision(
    peer_id: str,
    capability: str,
    decision: str
) -> None
```
Record an authorization decision.

**Parameters:**
- `peer_id` (str): SPIFFE ID of the peer
- `capability` (str): Capability being checked
- `decision` (str): Decision result (allow, deny)

##### record_error
```python
def record_error(
    error_type: str,
    capability: str = "unknown"
) -> None
```
Record an error.

**Parameters:**
- `error_type` (str): Type of error (auth_error, transport_error, etc.)
- `capability` (str): Capability where error occurred

##### time_request
```python
@contextmanager
def time_request(capability: str, status: str)
```
Context manager to time request duration.

**Parameters:**
- `capability` (str): Capability being invoked
- `status` (str): Expected status

**Example:**
```python
with metrics.time_request("search", "success"):
    await process_search()
```

##### time_auth_check
```python
@contextmanager
def time_auth_check(peer_id: str, capability: str)
```
Context manager to time authorization check duration.

**Parameters:**
- `peer_id` (str): SPIFFE ID of the peer
- `capability` (str): Capability being checked

**Example:**
```python
with metrics.time_auth_check(peer_id, "search"):
    decision = await check_authorization()
```

##### set_active_connections
```python
def set_active_connections(peer_id: str, count: int) -> None
```
Set the number of active connections to a peer.

**Parameters:**
- `peer_id` (str): SPIFFE ID of the peer
- `count` (int): Number of active connections

##### increment_active_connections
```python
def increment_active_connections(peer_id: str) -> None
```
Increment active connections counter.

**Parameters:**
- `peer_id` (str): SPIFFE ID of the peer

##### decrement_active_connections
```python
def decrement_active_connections(peer_id: str) -> None
```
Decrement active connections counter.

**Parameters:**
- `peer_id` (str): SPIFFE ID of the peer

##### set_circuit_breaker_state
```python
def set_circuit_breaker_state(peer_id: str, state: str) -> None
```
Set circuit breaker state for a peer.

**Parameters:**
- `peer_id` (str): SPIFFE ID of the peer
- `state` (str): State of circuit breaker (closed, open, half_open)

##### start_exposition_endpoint
```python
def start_exposition_endpoint(
    port: int = 9090,
    addr: str = "0.0.0.0"
) -> None
```
Start Prometheus metrics exposition HTTP server.

**Parameters:**
- `port` (int): Port to listen on (default: 9090)
- `addr` (str): Address to bind to (default: "0.0.0.0")

#### Example

```python
from agentweave.observability import MetricsCollector

# Create metrics collector
metrics = MetricsCollector(agent_name="search-agent", enabled=True)

# Start metrics endpoint
metrics.start_exposition_endpoint(port=9090)

# Record metrics
metrics.record_request("search", "success")
metrics.record_auth_decision(
    peer_id="spiffe://example.com/client",
    capability="search",
    decision="allow"
)

# Time operations
with metrics.time_request("search", "success"):
    result = await perform_search()

# Track connections
metrics.increment_active_connections("spiffe://example.com/client")
```

---

## Tracing

### TracingProvider

**Import:** `from agentweave.observability import TracingProvider`

Manages OpenTelemetry distributed tracing for secure agents with W3C Trace Context propagation.

#### Constructor

```python
TracingProvider(
    agent_name: str,
    service_version: str = "1.0.0",
    otlp_endpoint: str | None = None,
    enabled: bool = True
)
```

**Parameters:**
- `agent_name` (str): Name of the agent (added to trace metadata)
- `service_version` (str): Version of the service (default: "1.0.0")
- `otlp_endpoint` (str, optional): OTLP collector endpoint (e.g., "http://collector:4317")
- `enabled` (bool): Whether tracing is enabled (default: True)

#### Context Managers

##### trace_incoming_request
```python
@contextmanager
def trace_incoming_request(
    capability: str,
    caller_id: str,
    context: dict[str, str] | None = None
)
```
Create a span for an incoming request with automatic parent context extraction.

**Parameters:**
- `capability` (str): Capability being invoked
- `caller_id` (str): SPIFFE ID of the caller
- `context` (dict, optional): Trace context from caller (for propagation)

**Yields:** Span object for adding additional attributes

**Example:**
```python
with tracer.trace_incoming_request("search", caller_id, headers) as span:
    result = await handle_search()
    span.set_attribute("result_count", len(result))
```

##### trace_outgoing_call
```python
@contextmanager
def trace_outgoing_call(
    target_agent: str,
    capability: str
)
```
Create a span for an outgoing A2A call with trace context injection.

**Parameters:**
- `target_agent` (str): SPIFFE ID of target agent
- `capability` (str): Capability being invoked

**Yields:** Tuple of (span, carrier dict with trace context)

**Example:**
```python
with tracer.trace_outgoing_call(target_id, "search") as (span, carrier):
    response = await client.call(target_id, capability, headers=carrier)
```

##### trace_auth_check
```python
@contextmanager
def trace_auth_check(
    peer_id: str,
    capability: str,
    direction: str = "inbound"
)
```
Create a span for an authorization check.

**Parameters:**
- `peer_id` (str): SPIFFE ID of the peer
- `capability` (str): Capability being checked
- `direction` (str): Direction of check (inbound or outbound)

**Yields:** Span object for adding decision result

**Example:**
```python
with tracer.trace_auth_check(peer_id, "search", "inbound") as span:
    decision = await opa.check(peer_id, capability)
    span.set_attribute("authz.decision", "allow" if decision else "deny")
```

##### trace_identity_operation
```python
@contextmanager
def trace_identity_operation(operation: str)
```
Create a span for an identity operation.

**Parameters:**
- `operation` (str): Type of operation (fetch_svid, verify_peer, etc.)

**Yields:** Span object for adding additional attributes

**Example:**
```python
with tracer.trace_identity_operation("fetch_svid") as span:
    svid = await identity_provider.get_svid()
    span.set_attribute("svid.spiffe_id", svid.spiffe_id)
```

#### Methods

##### get_current_trace_id
```python
def get_current_trace_id() -> str | None
```
Get the current trace ID for correlation with logs.

**Returns:** Trace ID in hexadecimal format, or None if no active span

##### get_current_span_id
```python
def get_current_span_id() -> str | None
```
Get the current span ID for correlation with logs.

**Returns:** Span ID in hexadecimal format, or None if no active span

##### inject_context
```python
def inject_context(carrier: dict[str, str]) -> None
```
Inject current trace context into carrier for propagation.

**Parameters:**
- `carrier` (dict): Dictionary to inject context into (e.g., HTTP headers)

##### extract_context
```python
def extract_context(carrier: dict[str, str]) -> Any
```
Extract trace context from carrier.

**Parameters:**
- `carrier` (dict): Dictionary containing trace context (e.g., HTTP headers)

**Returns:** Extracted context for use in span creation

#### Example

```python
from agentweave.observability import TracingProvider

# Initialize tracing
tracer = TracingProvider(
    agent_name="search-agent",
    service_version="1.0.0",
    otlp_endpoint="http://jaeger:4317",
    enabled=True
)

# Trace incoming request
with tracer.trace_incoming_request("search", caller_id, headers) as span:
    span.set_attribute("query", query_text)
    results = await perform_search(query_text)
    span.set_attribute("result_count", len(results))

# Trace outgoing call
with tracer.trace_outgoing_call(target_id, "process") as (span, carrier):
    response = await client.post("/process", headers=carrier, json=data)

# Get trace ID for logging
trace_id = tracer.get_current_trace_id()
logger.info(f"Processing request", extra={"trace_id": trace_id})
```

---

## Logging

### JSONFormatter

**Import:** `from agentweave.observability import JSONFormatter`

JSON formatter for structured logging with trace correlation.

#### Constructor

```python
JSONFormatter(
    agent_name: str,
    include_trace_ids: bool = True
)
```

**Parameters:**
- `agent_name` (str): Name of the agent (included in all logs)
- `include_trace_ids` (bool): Whether to include trace/span IDs (default: True)

#### Output Format

Standard fields in JSON logs:
- `timestamp`: ISO 8601 timestamp
- `level`: Log level
- `logger`: Logger name
- `message`: Log message
- `trace_id`: Distributed trace ID (if available)
- `span_id`: Current span ID (if available)
- `agent_name`: Name of the agent
- `extra`: Additional fields from log record
- `exception`: Exception traceback (if present)

---

### AuditLogger

**Import:** `from agentweave.observability import AuditLogger`

Security audit logger for recording security-relevant events.

**IMPORTANT:** Audit logging cannot be disabled in production mode.

#### Constructor

```python
AuditLogger(
    agent_name: str,
    logger: logging.Logger | None = None,
    production_mode: bool = True
)
```

**Parameters:**
- `agent_name` (str): Name of the agent
- `logger` (logging.Logger, optional): Python logger instance (creates new if not provided)
- `production_mode` (bool): If True, audit logging cannot be disabled (default: True)

#### Properties

##### enabled
```python
@property
def enabled(self) -> bool
```
Check if audit logging is enabled.

```python
@enabled.setter
def enabled(value: bool) -> None
```
Set audit logging enabled state.

**Raises:**
- `RuntimeError`: If attempting to disable in production mode

#### Methods

##### audit_auth_check
```python
def audit_auth_check(
    caller_id: str,
    action: str,
    resource: str,
    decision: str,
    duration: float,
    reason: str = "",
    trace_id: str | None = None,
    span_id: str | None = None,
    context: dict[str, Any] | None = None
) -> None
```
Log an authorization check event.

**Parameters:**
- `caller_id` (str): SPIFFE ID of the caller
- `action` (str): Action being performed
- `resource` (str): Resource being accessed (capability name)
- `decision` (str): Authorization decision (allow/deny)
- `duration` (float): Duration of the check in seconds
- `reason` (str): Reason for the decision
- `trace_id` (str, optional): Distributed trace ID
- `span_id` (str, optional): Current span ID
- `context` (dict, optional): Additional context

##### audit_capability_call
```python
def audit_capability_call(
    caller_id: str,
    capability: str,
    status: str,
    duration: float,
    trace_id: str | None = None,
    span_id: str | None = None,
    context: dict[str, Any] | None = None
) -> None
```
Log a capability invocation event.

**Parameters:**
- `caller_id` (str): SPIFFE ID of the caller
- `capability` (str): Capability that was invoked
- `status` (str): Status of the call (success/error)
- `duration` (float): Duration of the call in seconds
- `trace_id` (str, optional): Distributed trace ID
- `span_id` (str, optional): Current span ID
- `context` (dict, optional): Additional context

##### audit_config_change
```python
def audit_config_change(
    initiator: str,
    change_type: str,
    details: dict[str, Any],
    trace_id: str | None = None,
    span_id: str | None = None
) -> None
```
Log a configuration change event.

**Parameters:**
- `initiator` (str): Who initiated the change (SPIFFE ID or "system")
- `change_type` (str): Type of configuration change
- `details` (dict): Details of the change
- `trace_id` (str, optional): Distributed trace ID
- `span_id` (str, optional): Current span ID

##### audit_startup
```python
def audit_startup(
    version: str,
    config: dict[str, Any],
    trace_id: str | None = None
) -> None
```
Log agent startup event.

**Parameters:**
- `version` (str): Agent version
- `config` (dict): Sanitized configuration (no secrets)
- `trace_id` (str, optional): Distributed trace ID

##### audit_shutdown
```python
def audit_shutdown(
    reason: str = "normal",
    trace_id: str | None = None
) -> None
```
Log agent shutdown event.

**Parameters:**
- `reason` (str): Reason for shutdown (normal, error, signal)
- `trace_id` (str, optional): Distributed trace ID

##### audit_identity_rotation
```python
def audit_identity_rotation(
    old_spiffe_id: str,
    new_spiffe_id: str,
    trace_id: str | None = None,
    span_id: str | None = None
) -> None
```
Log SVID rotation event.

**Parameters:**
- `old_spiffe_id` (str): Previous SPIFFE ID
- `new_spiffe_id` (str): New SPIFFE ID
- `trace_id` (str, optional): Distributed trace ID
- `span_id` (str, optional): Current span ID

#### Example

```python
from agentweave.observability import AuditLogger

# Create audit logger
audit = AuditLogger(agent_name="api-agent", production_mode=True)

# Log authorization check
audit.audit_auth_check(
    caller_id="spiffe://example.com/client",
    action="invoke",
    resource="search",
    decision="allow",
    duration=0.002,
    reason="Policy matched: allow_search",
    trace_id=trace_id,
    span_id=span_id
)

# Log capability call
audit.audit_capability_call(
    caller_id="spiffe://example.com/client",
    capability="search",
    status="success",
    duration=0.5,
    trace_id=trace_id,
    context={"query_length": 25}
)
```

---

### setup_logging

**Import:** `from agentweave.observability import setup_logging`

Setup standard logging configuration for an agent.

```python
def setup_logging(
    agent_name: str,
    level: str = "INFO",
    json_format: bool = True,
    include_trace_ids: bool = True
) -> logging.Logger
```

**Parameters:**
- `agent_name` (str): Name of the agent
- `level` (str): Log level (DEBUG, INFO, WARNING, ERROR) (default: "INFO")
- `json_format` (bool): Use JSON formatter (default: True)
- `include_trace_ids` (bool): Include trace/span IDs in logs (default: True)

**Returns:** Configured logger instance

**Example:**
```python
from agentweave.observability import setup_logging

logger = setup_logging(
    agent_name="api-agent",
    level="INFO",
    json_format=True
)

logger.info("Agent started")
```

---

## Audit Trail

### AuditTrail

**Import:** `from agentweave.observability import AuditTrail`

Central audit trail manager with pluggable backends for persisting audit events.

#### Constructor

```python
AuditTrail(
    agent_name: str,
    backend: AuditBackend,
    enabled: bool = True
)
```

**Parameters:**
- `agent_name` (str): Name of the agent
- `backend` (AuditBackend): Backend for emitting events
- `enabled` (bool): Whether audit trail is enabled (default: True)

#### Methods

##### record_auth_check
```python
async def record_auth_check(
    caller_id: str,
    action: str,
    resource: str,
    decision: str,
    duration: float,
    reason: str = "",
    trace_id: str | None = None,
    span_id: str | None = None,
    context: dict[str, Any] | None = None
) -> None
```
Record an authorization check event.

##### record_capability_call
```python
async def record_capability_call(
    caller_id: str,
    capability: str,
    status: str,
    duration: float,
    trace_id: str | None = None,
    span_id: str | None = None,
    context: dict[str, Any] | None = None
) -> None
```
Record a capability invocation event.

##### record_config_change
```python
async def record_config_change(
    initiator: str,
    change_type: str,
    details: dict[str, Any],
    trace_id: str | None = None,
    span_id: str | None = None
) -> None
```
Record a configuration change event.

##### record_startup
```python
async def record_startup(
    version: str,
    config: dict[str, Any],
    trace_id: str | None = None
) -> None
```
Record agent startup event.

##### record_shutdown
```python
async def record_shutdown(
    reason: str = "normal",
    trace_id: str | None = None
) -> None
```
Record agent shutdown event.

##### record_identity_rotation
```python
async def record_identity_rotation(
    old_spiffe_id: str,
    new_spiffe_id: str,
    trace_id: str | None = None,
    span_id: str | None = None
) -> None
```
Record SVID rotation event.

##### record_peer_verification
```python
async def record_peer_verification(
    peer_id: str,
    status: str,
    reason: str = "",
    trace_id: str | None = None,
    span_id: str | None = None
) -> None
```
Record peer verification event.

##### flush
```python
async def flush() -> None
```
Flush all buffered events.

##### close
```python
async def close() -> None
```
Close audit trail and backend.

---

### AuditEvent

**Import:** `from agentweave.observability import AuditEvent`

Immutable audit event record.

#### Constructor

```python
AuditEvent(
    event_type: AuditEventType,
    timestamp: str = <now>,
    agent_name: str = "",
    trace_id: str | None = None,
    span_id: str | None = None,
    caller_id: str | None = None,
    peer_id: str | None = None,
    action: str | None = None,
    resource: str | None = None,
    decision: str | None = None,
    reason: str | None = None,
    duration: float | None = None,
    context: dict[str, Any] = {}
)
```

#### Methods

##### to_dict
```python
def to_dict() -> dict[str, Any]
```
Convert event to dictionary.

##### to_json
```python
def to_json() -> str
```
Convert event to JSON string.

---

### AuditEventType

**Import:** `from agentweave.observability import AuditEventType`

Types of audit events enumeration.

```python
class AuditEventType(str, Enum):
    AUTH_CHECK = "AUTH_CHECK"
    CAPABILITY_CALL = "CAPABILITY_CALL"
    CONFIG_CHANGE = "CONFIG_CHANGE"
    STARTUP = "STARTUP"
    SHUTDOWN = "SHUTDOWN"
    IDENTITY_ROTATION = "IDENTITY_ROTATION"
    PEER_VERIFICATION = "PEER_VERIFICATION"
    POLICY_UPDATE = "POLICY_UPDATE"
```

---

### Audit Backends

#### FileAuditBackend

**Import:** `from agentweave.observability import FileAuditBackend`

File-based audit backend writing events in JSON Lines format.

```python
FileAuditBackend(
    file_path: str,
    buffer_size: int = 100
)
```

**Parameters:**
- `file_path` (str): Path to audit log file
- `buffer_size` (int): Number of events to buffer before flushing (default: 100)

#### StdoutAuditBackend

**Import:** `from agentweave.observability import StdoutAuditBackend`

Stdout-based audit backend for containerized environments.

```python
StdoutAuditBackend()
```

#### MultiBackend

**Import:** `from agentweave.observability import MultiBackend`

Composite backend that emits to multiple backends.

```python
MultiBackend(backends: list[AuditBackend])
```

**Parameters:**
- `backends` (list[AuditBackend]): List of backends to emit to

#### Example

```python
from agentweave.observability import (
    AuditTrail,
    FileAuditBackend,
    StdoutAuditBackend,
    MultiBackend
)

# Create multiple backends
file_backend = FileAuditBackend("/var/log/agent/audit.jsonl")
stdout_backend = StdoutAuditBackend()
multi_backend = MultiBackend([file_backend, stdout_backend])

# Create audit trail
audit = AuditTrail(
    agent_name="api-agent",
    backend=multi_backend,
    enabled=True
)

# Record events
await audit.record_auth_check(
    caller_id="spiffe://example.com/client",
    action="invoke",
    resource="search",
    decision="allow",
    duration=0.002,
    reason="Policy matched"
)

# Flush and close
await audit.flush()
await audit.close()
```

---

## Complete Observability Setup

```python
from agentweave.observability import (
    MetricsCollector,
    TracingProvider,
    setup_logging,
    AuditTrail,
    FileAuditBackend
)

# Setup logging
logger = setup_logging(
    agent_name="api-agent",
    level="INFO",
    json_format=True
)

# Setup metrics
metrics = MetricsCollector(agent_name="api-agent")
metrics.start_exposition_endpoint(port=9090)

# Setup tracing
tracer = TracingProvider(
    agent_name="api-agent",
    service_version="1.0.0",
    otlp_endpoint="http://jaeger:4317"
)

# Setup audit trail
audit = AuditTrail(
    agent_name="api-agent",
    backend=FileAuditBackend("/var/log/agent/audit.jsonl")
)

# Use in handler
async def handle_request(caller_id: str, capability: str, payload: dict):
    # Trace request
    with tracer.trace_incoming_request(capability, caller_id) as span:
        trace_id = tracer.get_current_trace_id()

        # Time request
        with metrics.time_request(capability, "success"):
            # Log request
            logger.info(
                f"Processing {capability}",
                extra={"trace_id": trace_id, "caller_id": caller_id}
            )

            # Record metrics
            metrics.record_request(capability, "success")

            # Audit
            await audit.record_capability_call(
                caller_id=caller_id,
                capability=capability,
                status="success",
                duration=0.5,
                trace_id=trace_id
            )

            # Process
            result = await process(payload)

            return result
```
