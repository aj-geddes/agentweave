---
layout: api
title: Configuration Module
parent: API Reference
nav_order: 5
---

# Configuration Module

The configuration module (`agentweave.config`) provides a comprehensive Pydantic-based configuration system with strict validation to ensure agents cannot start with insecure settings.

## Overview

The configuration system enforces:
- **Default deny in production** - Explicit policies required
- **No peer verification bypass** - mTLS verification cannot be disabled
- **TLS >= 1.2 mandatory** - Modern TLS versions only
- **Valid SPIFFE trust domain** - Proper identity domain configuration

Configuration can be loaded from:
- YAML files (recommended for deployment)
- Environment variables (for container overrides)
- Direct instantiation (for testing)

---

## Enumerations

### Environment

```python
class Environment(str, Enum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
```

**Values:**

| Value | Description |
|-------|-------------|
| `DEVELOPMENT` | Development environment (relaxed security rules) |
| `STAGING` | Staging environment |
| `PRODUCTION` | Production environment (strict security enforced) |

**Example:**

```yaml
agent:
  environment: production
```

---

### IdentityProvider

```python
class IdentityProvider(str, Enum):
    """Identity provider type."""

    SPIFFE = "spiffe"
    MTLS_STATIC = "mtls-static"  # For testing/development only
```

**Values:**

| Value | Description |
|-------|-------------|
| `SPIFFE` | SPIFFE/SPIRE identity provider (recommended) |
| `MTLS_STATIC` | Static mTLS certificates (development/testing only) |

**Example:**

```yaml
identity:
  provider: spiffe
```

---

### AuthorizationProvider

```python
class AuthorizationProvider(str, Enum):
    """Authorization provider type."""

    OPA = "opa"
    ALLOW_ALL = "allow-all"  # Development only - rejected in production
```

**Values:**

| Value | Description |
|-------|-------------|
| `OPA` | Open Policy Agent for policy-based authorization |
| `ALLOW_ALL` | Allow all requests (development only, rejected in production) |

**Example:**

```yaml
authorization:
  provider: opa
```

---

### DefaultAction

```python
class DefaultAction(str, Enum):
    """Default authorization action."""

    DENY = "deny"
    LOG_ONLY = "log-only"  # Development only - rejected in production
```

**Values:**

| Value | Description |
|-------|-------------|
| `DENY` | Deny requests by default (required in production) |
| `LOG_ONLY` | Log authorization decisions but allow all (development only) |

**Example:**

```yaml
authorization:
  default_action: deny
```

---

### PeerVerification

```python
class PeerVerification(str, Enum):
    """Peer verification mode."""

    STRICT = "strict"
    LOG_ONLY = "log-only"  # Development only
```

**Values:**

| Value | Description |
|-------|-------------|
| `STRICT` | Strict peer verification (required in production) |
| `LOG_ONLY` | Log verification failures but allow connection (development only) |

**Example:**

```yaml
transport:
  peer_verification: strict
```

---

### ProtocolType

```python
class ProtocolType(str, Enum):
    """Communication protocol type."""

    A2A = "a2a"
    GRPC = "grpc"
```

**Values:**

| Value | Description |
|-------|-------------|
| `A2A` | Agent-to-Agent JSON-RPC protocol |
| `GRPC` | gRPC protocol (future support) |

**Example:**

```yaml
server:
  protocol: a2a
```

---

## Configuration Models

### Capability

```python
class Capability(BaseModel):
    """Agent capability definition."""

    name: str
    description: str
    input_modes: list[str] = ["application/json"]
    output_modes: list[str] = ["application/json"]
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | *required* | Capability name (lowercase, underscores allowed) |
| `description` | `str` | *required* | Human-readable description |
| `input_modes` | `list[str]` | `["application/json"]` | Accepted input content types |
| `output_modes` | `list[str]` | `["application/json"]` | Produced output content types |

**Validation Rules:**

- `name` must match pattern `^[a-z][a-z0-9_]*$`
- Must start with lowercase letter
- Can contain lowercase letters, numbers, and underscores

**Example:**

```yaml
agent:
  capabilities:
    - name: search_users
      description: Search for users in the directory
      input_modes:
        - application/json
      output_modes:
        - application/json
```

**Python:**

```python
from agentweave.config import Capability

cap = Capability(
    name="search_users",
    description="Search for users in the directory"
)
```

---

### AgentSettings

```python
class AgentSettings(BaseModel):
    """Core agent settings."""

    name: str
    trust_domain: str
    description: str = ""
    environment: Environment = Environment.PRODUCTION
    capabilities: list[Capability] = []
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | *required* | Unique agent name |
| `trust_domain` | `str` | *required* | SPIFFE trust domain |
| `description` | `str` | `""` | Agent description |
| `environment` | `Environment` | `PRODUCTION` | Deployment environment |
| `capabilities` | `list[Capability]` | `[]` | Agent capabilities |

**Validation Rules:**

- `name` must match pattern `^[a-z][a-z0-9-]*$` (lowercase, hyphens allowed)
- `trust_domain` must be valid DNS name (e.g., `agentweave.io`)

**Example:**

```yaml
agent:
  name: data-search-agent
  trust_domain: agentweave.io
  description: Agent for searching data across systems
  environment: production
  capabilities:
    - name: search
      description: Search the database
```

**Python:**

```python
from agentweave.config import AgentSettings, Environment, Capability

settings = AgentSettings(
    name="data-search-agent",
    trust_domain="agentweave.io",
    environment=Environment.PRODUCTION,
    capabilities=[
        Capability(name="search", description="Search the database")
    ]
)
```

---

### IdentityConfig

```python
class IdentityConfig(BaseModel):
    """Identity provider configuration."""

    provider: IdentityProvider = IdentityProvider.SPIFFE
    spiffe_endpoint: str = "unix:///run/spire/sockets/agent.sock"
    allowed_trust_domains: list[str] = []
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | `IdentityProvider` | `SPIFFE` | Identity provider type |
| `spiffe_endpoint` | `str` | `unix:///run/spire/sockets/agent.sock` | SPIFFE Workload API endpoint |
| `allowed_trust_domains` | `list[str]` | `[]` | Allowed trust domains for federation |

**Validation Rules:**

- `spiffe_endpoint` must start with `unix://` or `tcp://`

**Example:**

```yaml
identity:
  provider: spiffe
  spiffe_endpoint: unix:///run/spire/sockets/agent.sock
  allowed_trust_domains:
    - partner.io
    - trusted-domain.com
```

**Python:**

```python
from agentweave.config import IdentityConfig, IdentityProvider

identity = IdentityConfig(
    provider=IdentityProvider.SPIFFE,
    spiffe_endpoint="unix:///run/spire/sockets/agent.sock",
    allowed_trust_domains=["partner.io"]
)
```

---

### AuditConfig

```python
class AuditConfig(BaseModel):
    """Audit logging configuration."""

    enabled: bool = True
    destination: str = "file:///var/log/agentweave/audit.log"
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `True` | Enable audit logging |
| `destination` | `str` | `file:///var/log/agentweave/audit.log` | Audit log destination |

**Example:**

```yaml
authorization:
  audit:
    enabled: true
    destination: file:///var/log/agentweave/audit.log
```

---

### AuthorizationConfig

```python
class AuthorizationConfig(BaseModel):
    """Authorization provider configuration."""

    provider: AuthorizationProvider = AuthorizationProvider.OPA
    opa_endpoint: str = "http://localhost:8181"
    policy_path: str = "agentweave/authz"
    default_action: DefaultAction = DefaultAction.DENY
    audit: AuditConfig = AuditConfig()
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `provider` | `AuthorizationProvider` | `OPA` | Authorization provider |
| `opa_endpoint` | `str` | `http://localhost:8181` | OPA server endpoint |
| `policy_path` | `str` | `agentweave/authz` | OPA policy path |
| `default_action` | `DefaultAction` | `DENY` | Default authorization action |
| `audit` | `AuditConfig` | `AuditConfig()` | Audit configuration |

**Validation Rules:**

- `opa_endpoint` must be valid HTTP(S) URL

**Example:**

```yaml
authorization:
  provider: opa
  opa_endpoint: http://localhost:8181
  policy_path: agentweave/authz
  default_action: deny
  audit:
    enabled: true
    destination: file:///var/log/agentweave/audit.log
```

**Python:**

```python
from agentweave.config import AuthorizationConfig, AuthorizationProvider, DefaultAction

authz = AuthorizationConfig(
    provider=AuthorizationProvider.OPA,
    opa_endpoint="http://localhost:8181",
    default_action=DefaultAction.DENY
)
```

---

### ConnectionPoolConfig

```python
class ConnectionPoolConfig(BaseModel):
    """Connection pool configuration."""

    max_connections: int = Field(default=100, ge=1, le=10000)
    idle_timeout_seconds: int = Field(default=60, ge=1)
```

**Fields:**

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `max_connections` | `int` | `100` | 1-10000 | Maximum connections in pool |
| `idle_timeout_seconds` | `int` | `60` | >= 1 | Idle connection timeout |

**Example:**

```yaml
transport:
  connection_pool:
    max_connections: 200
    idle_timeout_seconds: 120
```

---

### CircuitBreakerConfig

```python
class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    failure_threshold: int = Field(default=5, ge=1)
    recovery_timeout_seconds: int = Field(default=30, ge=1)
```

**Fields:**

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `failure_threshold` | `int` | `5` | >= 1 | Failures before opening circuit |
| `recovery_timeout_seconds` | `int` | `30` | >= 1 | Time before attempting recovery |

**Example:**

```yaml
transport:
  circuit_breaker:
    failure_threshold: 10
    recovery_timeout_seconds: 60
```

---

### RetryConfig

```python
class RetryConfig(BaseModel):
    """Retry policy configuration."""

    max_attempts: int = Field(default=3, ge=1, le=10)
    backoff_base_seconds: float = Field(default=1.0, ge=0.1)
    backoff_max_seconds: float = Field(default=30.0, ge=1.0)
```

**Fields:**

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `max_attempts` | `int` | `3` | 1-10 | Maximum retry attempts |
| `backoff_base_seconds` | `float` | `1.0` | >= 0.1 | Base backoff duration |
| `backoff_max_seconds` | `float` | `30.0` | >= 1.0 | Maximum backoff duration |

**Example:**

```yaml
transport:
  retry:
    max_attempts: 5
    backoff_base_seconds: 2.0
    backoff_max_seconds: 60.0
```

---

### TransportConfig

```python
class TransportConfig(BaseModel):
    """Transport layer configuration."""

    tls_min_version: Literal["1.2", "1.3"] = "1.3"
    peer_verification: PeerVerification = PeerVerification.STRICT
    connection_pool: ConnectionPoolConfig = ConnectionPoolConfig()
    circuit_breaker: CircuitBreakerConfig = CircuitBreakerConfig()
    retry: RetryConfig = RetryConfig()
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tls_min_version` | `"1.2"` or `"1.3"` | `"1.3"` | Minimum TLS version |
| `peer_verification` | `PeerVerification` | `STRICT` | Peer verification mode |
| `connection_pool` | `ConnectionPoolConfig` | default | Connection pool settings |
| `circuit_breaker` | `CircuitBreakerConfig` | default | Circuit breaker settings |
| `retry` | `RetryConfig` | default | Retry policy |

**Example:**

```yaml
transport:
  tls_min_version: "1.3"
  peer_verification: strict
  connection_pool:
    max_connections: 200
    idle_timeout_seconds: 120
  circuit_breaker:
    failure_threshold: 10
    recovery_timeout_seconds: 60
  retry:
    max_attempts: 5
    backoff_base_seconds: 2.0
    backoff_max_seconds: 60.0
```

---

### ServerConfig

```python
class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = "0.0.0.0"
    port: int = Field(default=8443, ge=1, le=65535)
    protocol: ProtocolType = ProtocolType.A2A
```

**Fields:**

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `host` | `str` | `"0.0.0.0"` | - | Server bind host |
| `port` | `int` | `8443` | 1-65535 | Server port |
| `protocol` | `ProtocolType` | `A2A` | - | Communication protocol |

**Example:**

```yaml
server:
  host: 0.0.0.0
  port: 8443
  protocol: a2a
```

---

### MetricsConfig

```python
class MetricsConfig(BaseModel):
    """Metrics configuration."""

    enabled: bool = True
    port: int = Field(default=9090, ge=1, le=65535)
```

**Fields:**

| Field | Type | Default | Constraints | Description |
|-------|------|---------|-------------|-------------|
| `enabled` | `bool` | `True` | - | Enable metrics collection |
| `port` | `int` | `9090` | 1-65535 | Metrics server port |

**Example:**

```yaml
observability:
  metrics:
    enabled: true
    port: 9090
```

---

### TracingConfig

```python
class TracingConfig(BaseModel):
    """Distributed tracing configuration."""

    enabled: bool = True
    exporter: Literal["otlp", "jaeger", "zipkin"] = "otlp"
    endpoint: str = "http://localhost:4317"
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `enabled` | `bool` | `True` | Enable distributed tracing |
| `exporter` | `"otlp"`, `"jaeger"`, or `"zipkin"` | `"otlp"` | Trace exporter type |
| `endpoint` | `str` | `http://localhost:4317` | Trace collector endpoint |

**Example:**

```yaml
observability:
  tracing:
    enabled: true
    exporter: otlp
    endpoint: http://localhost:4317
```

---

### LoggingConfig

```python
class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    format: Literal["json", "text"] = "json"
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `level` | Log level | `"INFO"` | Log level |
| `format` | `"json"` or `"text"` | `"json"` | Log format |

**Example:**

```yaml
observability:
  logging:
    level: INFO
    format: json
```

---

### ObservabilityConfig

```python
class ObservabilityConfig(BaseModel):
    """Observability configuration."""

    metrics: MetricsConfig = MetricsConfig()
    tracing: TracingConfig = TracingConfig()
    logging: LoggingConfig = LoggingConfig()
```

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `metrics` | `MetricsConfig` | default | Metrics settings |
| `tracing` | `TracingConfig` | default | Tracing settings |
| `logging` | `LoggingConfig` | default | Logging settings |

**Example:**

```yaml
observability:
  metrics:
    enabled: true
    port: 9090
  tracing:
    enabled: true
    exporter: otlp
    endpoint: http://localhost:4317
  logging:
    level: INFO
    format: json
```

---

## AgentConfig (Main Configuration)

```python
class AgentConfig(BaseModel):
    """Complete agent configuration with strict security validation."""

    agent: AgentSettings
    identity: IdentityConfig = IdentityConfig()
    authorization: AuthorizationConfig = AuthorizationConfig()
    transport: TransportConfig = TransportConfig()
    server: ServerConfig = ServerConfig()
    observability: ObservabilityConfig = ObservabilityConfig()
```

### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `agent` | `AgentSettings` | *required* | Agent settings |
| `identity` | `IdentityConfig` | default | Identity configuration |
| `authorization` | `AuthorizationConfig` | default | Authorization configuration |
| `transport` | `TransportConfig` | default | Transport configuration |
| `server` | `ServerConfig` | default | Server configuration |
| `observability` | `ObservabilityConfig` | default | Observability configuration |

### Methods

#### is_production

```python
def is_production(self) -> bool
```

Check if running in production environment.

**Returns:** `bool` - True if environment is production

**Example:**

```python
config = AgentConfig.from_file("config.yaml")
if config.is_production():
    print("Running in production mode")
```

#### from_file

```python
@classmethod
def from_file(cls, path: str | Path) -> AgentConfig
```

Load configuration from YAML file.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `str` or `Path` | Path to YAML configuration file |

**Returns:** `AgentConfig` - Validated configuration instance

**Raises:**

| Exception | Description |
|-----------|-------------|
| `ConfigurationError` | If file not found, invalid YAML, or validation fails |

**Example:**

```python
from agentweave.config import AgentConfig

config = AgentConfig.from_file("config.yaml")
```

#### from_env

```python
@classmethod
def from_env(cls, prefix: str = "AGENTWEAVE_") -> AgentConfig
```

Load configuration from environment variables.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `prefix` | `str` | `"AGENTWEAVE_"` | Environment variable prefix |

**Returns:** `AgentConfig` - Validated configuration instance

**Raises:**

| Exception | Description |
|-----------|-------------|
| `ConfigurationError` | If required variables missing or validation fails |

**Environment Variable Format:**

```
{prefix}{SECTION}_{KEY}
```

**Examples:**

```bash
export AGENTWEAVE_AGENT_NAME=my-agent
export AGENTWEAVE_AGENT_TRUST_DOMAIN=agentweave.io
export AGENTWEAVE_IDENTITY_SPIFFE_ENDPOINT=unix:///run/spire/sockets/agent.sock
export AGENTWEAVE_TRANSPORT_TLS_MIN_VERSION=1.3
export AGENTWEAVE_SERVER_PORT=8443
```

**Python:**

```python
from agentweave.config import AgentConfig

# Load from environment
config = AgentConfig.from_env()

# Custom prefix
config = AgentConfig.from_env(prefix="MYAPP_")
```

### Security Validation Rules

The `AgentConfig` enforces strict security rules during validation:

#### Rule 1: Default Deny in Production

```python
if self.is_production() and self.authorization.default_action != DefaultAction.DENY:
    raise ConfigurationError(
        "authorization.default_action must be 'deny' in production environment"
    )
```

#### Rule 2: No Allow-All in Production

```python
if self.is_production() and self.authorization.provider == AuthorizationProvider.ALLOW_ALL:
    raise ConfigurationError(
        "authorization.provider cannot be 'allow-all' in production environment"
    )
```

#### Rule 3: Strict Peer Verification in Production

```python
if self.is_production() and self.transport.peer_verification != PeerVerification.STRICT:
    raise ConfigurationError(
        "transport.peer_verification must be 'strict' in production environment"
    )
```

#### Rule 4: TLS 1.2 Minimum

```python
if self.transport.tls_min_version not in ("1.2", "1.3"):
    raise ConfigurationError(
        "transport.tls_min_version must be '1.2' or '1.3'"
    )
```

#### Rule 5: Audit Enabled in Production

```python
if self.is_production() and not self.authorization.audit.enabled:
    raise ConfigurationError(
        "authorization.audit.enabled must be true in production environment"
    )
```

---

## Complete Configuration Example

```yaml
# config.yaml
agent:
  name: data-search-agent
  trust_domain: agentweave.io
  description: Agent for searching data across systems
  environment: production
  capabilities:
    - name: search
      description: Search the database
      input_modes:
        - application/json
      output_modes:
        - application/json

identity:
  provider: spiffe
  spiffe_endpoint: unix:///run/spire/sockets/agent.sock
  allowed_trust_domains:
    - partner.io

authorization:
  provider: opa
  opa_endpoint: http://localhost:8181
  policy_path: agentweave/authz
  default_action: deny
  audit:
    enabled: true
    destination: file:///var/log/agentweave/audit.log

transport:
  tls_min_version: "1.3"
  peer_verification: strict
  connection_pool:
    max_connections: 200
    idle_timeout_seconds: 120
  circuit_breaker:
    failure_threshold: 10
    recovery_timeout_seconds: 60
  retry:
    max_attempts: 5
    backoff_base_seconds: 2.0
    backoff_max_seconds: 60.0

server:
  host: 0.0.0.0
  port: 8443
  protocol: a2a

observability:
  metrics:
    enabled: true
    port: 9090
  tracing:
    enabled: true
    exporter: otlp
    endpoint: http://localhost:4317
  logging:
    level: INFO
    format: json
```

**Load in Python:**

```python
from agentweave.config import AgentConfig
from agentweave import SecureAgent

# Load configuration
config = AgentConfig.from_file("config.yaml")

# Use with agent
class MyAgent(SecureAgent):
    pass

agent = MyAgent(config=config.agent)  # Pass AgentSettings
```

---

## See Also

- [Agent Module](agent.md) - Using configuration with agents
- [Configuration Guide](../configuration.md) - Detailed configuration examples
- [Security Guide](../security.md) - Security best practices
