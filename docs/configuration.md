# Configuration Reference

Complete reference for AgentWeave SDK configuration.

## Configuration File Format

The SDK accepts configuration in YAML format. All paths below use dot notation (e.g., `agent.name` refers to the `name` field under `agent`).

## Top-Level Structure

```yaml
agent:           # Agent identity and capabilities
identity:        # Identity provider configuration
authorization:   # Authorization engine configuration
transport:       # Network transport settings
server:          # Server configuration
observability:   # Metrics, tracing, logging
```

## Agent Section

Defines the agent's identity and advertised capabilities.

```yaml
agent:
  name: string                    # Required. Agent name (alphanumeric, hyphens, underscores)
  trust_domain: string            # Required. SPIFFE trust domain (e.g., "example.com")
  description: string             # Optional. Human-readable description
  version: string                 # Optional. Agent version (default: "1.0.0")
  capabilities: array             # Optional. List of capabilities this agent provides
```

### Agent Capabilities

```yaml
capabilities:
  - name: string                  # Required. Capability name (must be unique)
    description: string           # Optional. What this capability does
    input_modes: array            # Optional. Accepted MIME types (default: ["application/json"])
    output_modes: array           # Optional. Response MIME types (default: ["application/json"])
    parameters: object            # Optional. JSON Schema for parameters
    timeout_seconds: number       # Optional. Maximum execution time (default: 30)
```

**Example**:

```yaml
agent:
  name: "data-processor"
  trust_domain: "agentweave.io"
  description: "Processes structured data"
  capabilities:
    - name: "process"
      description: "Process data records"
      input_modes: ["application/json", "application/x-ndjson"]
      output_modes: ["application/json"]
      timeout_seconds: 60
    - name: "validate"
      description: "Validate data schema"
      input_modes: ["application/json"]
      output_modes: ["application/json"]
      timeout_seconds: 10
```

## Identity Section

Configures how the agent obtains and manages its cryptographic identity.

```yaml
identity:
  provider: string                # Required. "spiffe" | "mtls-static"
  spiffe_endpoint: string         # SPIFFE socket path
  allowed_trust_domains: array   # List of trusted domains
  certificate_path: string        # For mtls-static provider
  private_key_path: string        # For mtls-static provider
  ca_cert_path: string            # For mtls-static provider
```

### SPIFFE Provider (Recommended)

```yaml
identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"
  allowed_trust_domains:
    - "agentweave.io"              # Own domain
    - "partner.example.com"        # Federated domain
```

**Environment Variable Override**: `SPIFFE_ENDPOINT_SOCKET`

### Static mTLS Provider (Development Only)

```yaml
identity:
  provider: "mtls-static"
  certificate_path: "/etc/certs/agent.crt"
  private_key_path: "/etc/certs/agent.key"
  ca_cert_path: "/etc/certs/ca.crt"
  allowed_trust_domains:
    - "dev.local"
```

**Warning**: Static certificates don't rotate. Only use for development.

## Authorization Section

Configures policy enforcement and audit logging.

```yaml
authorization:
  provider: string                # Required. "opa" | "allow-all"
  opa_endpoint: string            # OPA server URL
  policy_path: string             # Policy path in OPA
  default_action: string          # "deny" | "log-only"
  cache_ttl_seconds: number       # Policy decision cache TTL
  audit: object                   # Audit logging configuration
```

### OPA Provider (Production)

```yaml
authorization:
  provider: "opa"
  opa_endpoint: "http://localhost:8181"
  policy_path: "agentweave/authz"
  default_action: "deny"
  cache_ttl_seconds: 60
  audit:
    enabled: true
    destination: "file:///var/log/agentweave/audit.log"
    format: "json"
    include_request_body: false   # Don't log sensitive data
    include_response_body: false
```

**Environment Variable Overrides**:
- `AGENTWEAVE_OPA_ENDPOINT`
- `AGENTWEAVE_AUTHZ_DEFAULT_ACTION`

### Allow-All Provider (Development Only)

```yaml
authorization:
  provider: "allow-all"
  audit:
    enabled: true
    destination: "stdout"
```

**Warning**: Allows all requests. Never use in production.

### Audit Destinations

- `stdout` - Standard output (JSON)
- `stderr` - Standard error (JSON)
- `file://path` - File (rotated daily)
- `syslog://host:port` - Syslog server
- `http://endpoint` - HTTP webhook

## Transport Section

Controls network transport, mTLS, retries, and circuit breaking.

```yaml
transport:
  tls_min_version: string         # "1.2" | "1.3"
  peer_verification: string       # "strict" | "log-only"
  connection_pool: object         # Connection pooling
  circuit_breaker: object         # Circuit breaker settings
  retry: object                   # Retry policy
  timeout_seconds: number         # Default request timeout
```

### Full Transport Configuration

```yaml
transport:
  tls_min_version: "1.3"
  peer_verification: "strict"     # Never use "none"

  connection_pool:
    max_connections: 100          # Per target agent
    idle_timeout_seconds: 60      # Close idle connections after
    max_lifetime_seconds: 300     # Force reconnect after

  circuit_breaker:
    enabled: true
    failure_threshold: 5          # Open after N failures
    recovery_timeout_seconds: 30  # Try again after
    half_open_requests: 1         # Test with 1 request

  retry:
    max_attempts: 3               # Total attempts
    backoff_base_seconds: 1.0     # Initial delay
    backoff_max_seconds: 30.0     # Maximum delay
    backoff_multiplier: 2.0       # Exponential factor
    retryable_status_codes:       # HTTP codes to retry
      - 502
      - 503
      - 504

  timeout_seconds: 30             # Default for all requests
```

### TLS Version Constraints

| Version | Support | Notes |
|---------|---------|-------|
| TLS 1.0 | Never | Removed |
| TLS 1.1 | Never | Removed |
| TLS 1.2 | Allowed | Minimum for compatibility |
| TLS 1.3 | Recommended | Default, best performance |

### Peer Verification Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `strict` | Reject on verification failure | Production (required) |
| `log-only` | Log but allow | Development debugging |
| ~~`none`~~ | Not allowed | SDK rejects this value |

## Server Section

Configures the agent's inbound server.

```yaml
server:
  host: string                    # Bind address
  port: number                    # Listen port
  protocol: string                # "a2a" | "grpc"
  max_concurrent_requests: number # Request limit
  request_timeout_seconds: number # Per-request timeout
  graceful_shutdown_seconds: number # Shutdown grace period
```

**Example**:

```yaml
server:
  host: "0.0.0.0"
  port: 8443
  protocol: "a2a"
  max_concurrent_requests: 1000
  request_timeout_seconds: 60
  graceful_shutdown_seconds: 30
```

**Environment Variable Overrides**:
- `AGENTWEAVE_SERVER_HOST`
- `AGENTWEAVE_SERVER_PORT`

## Observability Section

Enables metrics, distributed tracing, and structured logging.

```yaml
observability:
  metrics: object                 # Prometheus metrics
  tracing: object                 # OpenTelemetry tracing
  logging: object                 # Structured logging
```

### Metrics (Prometheus)

```yaml
observability:
  metrics:
    enabled: true
    port: 9090                    # Metrics endpoint port
    path: "/metrics"              # Metrics path
    include_exemplars: true       # Include trace exemplars
```

Metrics endpoint: `http://localhost:9090/metrics`

### Tracing (OpenTelemetry)

```yaml
observability:
  tracing:
    enabled: true
    exporter: "otlp"              # "otlp" | "jaeger" | "zipkin"
    endpoint: "http://collector:4317"
    service_name: null            # Defaults to agent.name
    sample_rate: 1.0              # 1.0 = 100%, 0.1 = 10%
    headers:                      # Optional headers
      x-api-key: "secret"
```

### Logging

```yaml
observability:
  logging:
    level: "INFO"                 # "DEBUG" | "INFO" | "WARN" | "ERROR"
    format: "json"                # "json" | "text"
    output: "stdout"              # "stdout" | "stderr" | "file://path"
    include_caller: true          # Include file:line
    include_trace_id: true        # Include OpenTelemetry trace ID
```

**Example JSON Log**:

```json
{
  "timestamp": "2025-12-06T10:30:00.123Z",
  "level": "INFO",
  "message": "Request completed",
  "agent": "data-processor",
  "caller_spiffe_id": "spiffe://agentweave.io/agent/orchestrator",
  "action": "process",
  "duration_ms": 45,
  "trace_id": "a1b2c3d4e5f6...",
  "caller": "agent.py:123"
}
```

## Environment Variables

The SDK supports environment variable overrides for common settings:

| Variable | Config Path | Example |
|----------|-------------|---------|
| `AGENTWEAVE_AGENT_NAME` | `agent.name` | `data-processor` |
| `AGENTWEAVE_TRUST_DOMAIN` | `agent.trust_domain` | `agentweave.io` |
| `SPIFFE_ENDPOINT_SOCKET` | `identity.spiffe_endpoint` | `unix:///run/spire/sockets/agent.sock` |
| `AGENTWEAVE_OPA_ENDPOINT` | `authorization.opa_endpoint` | `http://opa:8181` |
| `AGENTWEAVE_SERVER_HOST` | `server.host` | `0.0.0.0` |
| `AGENTWEAVE_SERVER_PORT` | `server.port` | `8443` |
| `AGENTWEAVE_LOG_LEVEL` | `observability.logging.level` | `DEBUG` |
| `AGENTWEAVE_CONFIG_PATH` | - | Path to config file |

**Priority**: Environment variables override config file values.

## Configuration Validation

The SDK validates configuration at startup and rejects invalid configs:

### Validation Rules

1. **Agent Name**: Alphanumeric, hyphens, underscores only
2. **Trust Domain**: Valid DNS name
3. **TLS Version**: Must be 1.2 or 1.3
4. **Peer Verification**: Cannot be "none"
5. **Default Action**: Must be "deny" in production
6. **Capabilities**: Names must be unique
7. **Allowed Trust Domains**: Must include own trust domain

### Validation Example

```bash
# Validate before starting
agentweave validate config.yaml
```

Output:

```json
{
  "valid": false,
  "errors": [
    {
      "path": "authorization.default_action",
      "message": "Must be 'deny' in production (detected by AGENTWEAVE_ENV=production)"
    },
    {
      "path": "transport.peer_verification",
      "message": "Cannot be 'none'. Use 'strict' or 'log-only'."
    }
  ]
}
```

## Configuration Profiles

Use profiles for different environments:

**config.yaml** (base):
```yaml
agent:
  name: "data-processor"
  trust_domain: "${AGENTWEAVE_TRUST_DOMAIN}"

# Include environment-specific overrides
include:
  - "config.${AGENTWEAVE_ENV}.yaml"
```

**config.production.yaml**:
```yaml
authorization:
  default_action: "deny"
  audit:
    enabled: true
    destination: "file:///var/log/hvs-agent/audit.log"

observability:
  logging:
    level: "WARN"
```

**config.development.yaml**:
```yaml
authorization:
  default_action: "log-only"
  audit:
    enabled: true
    destination: "stdout"

observability:
  logging:
    level: "DEBUG"
```

Run with profile:

```bash
AGENTWEAVE_ENV=production python agent.py
```

## Configuration Best Practices

1. **Never commit secrets**: Use environment variables or secret managers
2. **Validate early**: Run `agentweave validate` in CI/CD
3. **Use profiles**: Separate dev/staging/prod configs
4. **Enable audit logging**: Required for compliance
5. **Start strict**: Use `default_action: deny`, whitelist allowed calls
6. **Monitor metrics**: Set up Prometheus scraping
7. **Version control**: Keep configs in git with agent code

## Example Complete Configuration

```yaml
agent:
  name: "production-processor"
  trust_domain: "agentweave.io"
  description: "Production data processing agent"
  version: "2.1.0"
  capabilities:
    - name: "process"
      description: "Process data records"
      input_modes: ["application/json"]
      output_modes: ["application/json"]
      timeout_seconds: 120

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"
  allowed_trust_domains:
    - "agentweave.io"

authorization:
  provider: "opa"
  opa_endpoint: "http://opa:8181"
  policy_path: "agentweave/authz"
  default_action: "deny"
  cache_ttl_seconds: 60
  audit:
    enabled: true
    destination: "file:///var/log/agentweave/audit.log"
    format: "json"
    include_request_body: false
    include_response_body: false

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"
  connection_pool:
    max_connections: 100
    idle_timeout_seconds: 60
  circuit_breaker:
    enabled: true
    failure_threshold: 5
    recovery_timeout_seconds: 30
  retry:
    max_attempts: 3
    backoff_base_seconds: 1.0
    backoff_max_seconds: 30.0
  timeout_seconds: 30

server:
  host: "0.0.0.0"
  port: 8443
  protocol: "a2a"
  max_concurrent_requests: 1000
  graceful_shutdown_seconds: 30

observability:
  metrics:
    enabled: true
    port: 9090
  tracing:
    enabled: true
    exporter: "otlp"
    endpoint: "http://otel-collector:4317"
    sample_rate: 0.1
  logging:
    level: "INFO"
    format: "json"
    output: "stdout"
    include_caller: true
    include_trace_id: true
```

## See Also

- [Quick Start Guide](quickstart.md)
- [Security Guide](security.md)
- [Example Configurations](../examples/)
