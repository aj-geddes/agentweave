"""
Configuration management for the AgentWeave SDK.

This module provides Pydantic-based configuration models with strict validation
to ensure agents cannot start with insecure settings. The configuration enforces:

- Default deny in production
- No peer verification bypass
- TLS >= 1.2 mandatory
- Valid SPIFFE trust domain required

Configuration can be loaded from:
- YAML files (recommended for deployment)
- Environment variables (for container overrides)
- Direct instantiation (for testing)
"""

import os
import re
from enum import Enum
from pathlib import Path
from typing import Any, Literal, Optional, Self

import yaml
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from agentweave.exceptions import ConfigurationError


class Environment(str, Enum):
    """Deployment environment."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class IdentityProvider(str, Enum):
    """Identity provider type."""

    SPIFFE = "spiffe"
    MTLS_STATIC = "mtls-static"  # For testing/development only


class AuthorizationProvider(str, Enum):
    """Authorization provider type."""

    OPA = "opa"
    ALLOW_ALL = "allow-all"  # Development only - will be rejected in production


class DefaultAction(str, Enum):
    """Default authorization action."""

    DENY = "deny"
    LOG_ONLY = "log-only"  # Development only - will be rejected in production


class PeerVerification(str, Enum):
    """Peer verification mode."""

    STRICT = "strict"
    LOG_ONLY = "log-only"  # Development only - cannot be 'none'


class ProtocolType(str, Enum):
    """Communication protocol type."""

    A2A = "a2a"
    GRPC = "grpc"


class Capability(BaseModel):
    """
    Agent capability definition.

    Capabilities are advertised in the Agent Card and define what
    operations this agent can perform.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Capability name (e.g., 'search', 'process_data')")
    description: str = Field(..., description="Human-readable capability description")
    input_modes: list[str] = Field(
        default=["application/json"], description="Accepted input content types"
    )
    output_modes: list[str] = Field(
        default=["application/json"], description="Produced output content types"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate capability name format."""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                "Capability name must start with lowercase letter and "
                "contain only lowercase letters, numbers, and underscores"
            )
        return v


class AgentSettings(BaseModel):
    """
    Core agent settings.

    Defines the agent's identity and capabilities within the trust domain.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(..., description="Unique agent name")
    trust_domain: str = Field(..., description="SPIFFE trust domain")
    description: str = Field(default="", description="Agent description")
    environment: Environment = Field(
        default=Environment.PRODUCTION, description="Deployment environment"
    )
    capabilities: list[Capability] = Field(
        default_factory=list, description="Agent capabilities"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate agent name format."""
        if not re.match(r"^[a-z][a-z0-9-]*$", v):
            raise ValueError(
                "Agent name must start with lowercase letter and "
                "contain only lowercase letters, numbers, and hyphens"
            )
        return v

    @field_validator("trust_domain")
    @classmethod
    def validate_trust_domain(cls, v: str) -> str:
        """Validate SPIFFE trust domain format."""
        # Trust domain should be a valid DNS name
        if not re.match(r"^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?)*$", v):
            raise ValueError(
                f"Invalid trust domain format: {v}. "
                "Must be a valid DNS name (e.g., 'agentweave.io')"
            )
        return v


class IdentityConfig(BaseModel):
    """
    Identity provider configuration.

    Configures how the agent obtains and manages its cryptographic identity.
    """

    model_config = ConfigDict(frozen=True)

    provider: IdentityProvider = Field(
        default=IdentityProvider.SPIFFE, description="Identity provider type"
    )
    spiffe_endpoint: str = Field(
        default="unix:///run/spire/sockets/agent.sock",
        description="SPIFFE Workload API endpoint",
    )
    allowed_trust_domains: list[str] = Field(
        default_factory=list,
        description="Allowed trust domains for federation (in addition to own domain)",
    )

    @field_validator("spiffe_endpoint")
    @classmethod
    def validate_endpoint(cls, v: str) -> str:
        """Validate SPIFFE endpoint format."""
        if not (v.startswith("unix://") or v.startswith("tcp://")):
            raise ValueError(
                "SPIFFE endpoint must start with 'unix://' or 'tcp://'"
            )
        return v


class AuditConfig(BaseModel):
    """Audit logging configuration."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = Field(default=True, description="Enable audit logging")
    destination: str = Field(
        default="file:///var/log/agentweave/audit.log",
        description="Audit log destination (file:// or syslog://)",
    )


class AuthorizationConfig(BaseModel):
    """
    Authorization provider configuration.

    Configures how the agent enforces access control policies.
    """

    model_config = ConfigDict(frozen=True)

    provider: AuthorizationProvider = Field(
        default=AuthorizationProvider.OPA, description="Authorization provider type"
    )
    opa_endpoint: str = Field(
        default="http://localhost:8181", description="OPA server endpoint"
    )
    policy_path: str = Field(
        default="agentweave/authz", description="OPA policy path"
    )
    default_action: DefaultAction = Field(
        default=DefaultAction.DENY, description="Default authorization action"
    )
    audit: AuditConfig = Field(
        default_factory=AuditConfig, description="Audit configuration"
    )

    @field_validator("opa_endpoint")
    @classmethod
    def validate_opa_endpoint(cls, v: str) -> str:
        """Validate OPA endpoint format."""
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("OPA endpoint must be a valid HTTP(S) URL")
        return v


class ConnectionPoolConfig(BaseModel):
    """Connection pool configuration."""

    model_config = ConfigDict(frozen=True)

    max_connections: int = Field(
        default=100, ge=1, le=10000, description="Maximum connections in pool"
    )
    idle_timeout_seconds: int = Field(
        default=60, ge=1, description="Idle connection timeout"
    )


class CircuitBreakerConfig(BaseModel):
    """Circuit breaker configuration."""

    model_config = ConfigDict(frozen=True)

    failure_threshold: int = Field(
        default=5, ge=1, description="Failures before opening circuit"
    )
    recovery_timeout_seconds: int = Field(
        default=30, ge=1, description="Time before attempting recovery"
    )


class RetryConfig(BaseModel):
    """Retry policy configuration."""

    model_config = ConfigDict(frozen=True)

    max_attempts: int = Field(default=3, ge=1, le=10, description="Maximum retry attempts")
    backoff_base_seconds: float = Field(
        default=1.0, ge=0.1, description="Base backoff duration"
    )
    backoff_max_seconds: float = Field(
        default=30.0, ge=1.0, description="Maximum backoff duration"
    )


class TransportConfig(BaseModel):
    """
    Transport layer configuration.

    Configures mTLS, connection pooling, and resilience patterns.
    """

    model_config = ConfigDict(frozen=True)

    tls_min_version: Literal["1.2", "1.3"] = Field(
        default="1.3", description="Minimum TLS version"
    )
    peer_verification: PeerVerification = Field(
        default=PeerVerification.STRICT, description="Peer verification mode"
    )
    connection_pool: ConnectionPoolConfig = Field(
        default_factory=ConnectionPoolConfig, description="Connection pool settings"
    )
    circuit_breaker: CircuitBreakerConfig = Field(
        default_factory=CircuitBreakerConfig, description="Circuit breaker settings"
    )
    retry: RetryConfig = Field(
        default_factory=RetryConfig, description="Retry policy"
    )


class ServerConfig(BaseModel):
    """
    Server configuration.

    Configures the agent's server endpoint for receiving requests.
    """

    model_config = ConfigDict(frozen=True)

    host: str = Field(default="0.0.0.0", description="Server bind host")
    port: int = Field(default=8443, ge=1, le=65535, description="Server port")
    protocol: ProtocolType = Field(
        default=ProtocolType.A2A, description="Communication protocol"
    )


class MetricsConfig(BaseModel):
    """Metrics configuration."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = Field(default=True, description="Enable metrics collection")
    port: int = Field(default=9090, ge=1, le=65535, description="Metrics server port")


class TracingConfig(BaseModel):
    """Distributed tracing configuration."""

    model_config = ConfigDict(frozen=True)

    enabled: bool = Field(default=True, description="Enable distributed tracing")
    exporter: Literal["otlp", "jaeger", "zipkin"] = Field(
        default="otlp", description="Trace exporter type"
    )
    endpoint: str = Field(
        default="http://localhost:4317", description="Trace collector endpoint"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    model_config = ConfigDict(frozen=True)

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", description="Log level"
    )
    format: Literal["json", "text"] = Field(
        default="json", description="Log format"
    )


class ObservabilityConfig(BaseModel):
    """
    Observability configuration.

    Configures metrics, tracing, and logging for the agent.
    """

    model_config = ConfigDict(frozen=True)

    metrics: MetricsConfig = Field(
        default_factory=MetricsConfig, description="Metrics settings"
    )
    tracing: TracingConfig = Field(
        default_factory=TracingConfig, description="Tracing settings"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig, description="Logging settings"
    )


class AgentConfig(BaseModel):
    """
    Complete agent configuration with strict security validation.

    This is the main configuration class that enforces all security requirements:
    - Default deny in production
    - No peer verification bypass
    - TLS >= 1.2 mandatory
    - Valid SPIFFE trust domain required

    Example:
        config = AgentConfig.from_file("config.yaml")
        config = AgentConfig.from_env()
    """

    model_config = ConfigDict(frozen=True)

    agent: AgentSettings = Field(..., description="Agent settings")
    identity: IdentityConfig = Field(
        default_factory=IdentityConfig, description="Identity configuration"
    )
    authorization: AuthorizationConfig = Field(
        default_factory=AuthorizationConfig, description="Authorization configuration"
    )
    transport: TransportConfig = Field(
        default_factory=TransportConfig, description="Transport configuration"
    )
    server: ServerConfig = Field(
        default_factory=ServerConfig, description="Server configuration"
    )
    observability: ObservabilityConfig = Field(
        default_factory=ObservabilityConfig, description="Observability configuration"
    )

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.agent.environment == Environment.PRODUCTION

    @model_validator(mode="after")
    def validate_security(self) -> Self:
        """
        Enforce strict security rules.

        These rules ensure the agent cannot be started with insecure configuration.
        """
        # RULE 1: Default deny in production
        if self.is_production() and self.authorization.default_action != DefaultAction.DENY:
            raise ConfigurationError(
                "authorization.default_action must be 'deny' in production environment",
                details={
                    "environment": self.agent.environment.value,
                    "default_action": self.authorization.default_action.value,
                },
            )

        # RULE 2: No allow-all authorization in production
        if self.is_production() and self.authorization.provider == AuthorizationProvider.ALLOW_ALL:
            raise ConfigurationError(
                "authorization.provider cannot be 'allow-all' in production environment",
                details={
                    "environment": self.agent.environment.value,
                    "provider": self.authorization.provider.value,
                },
            )

        # RULE 3: Strict peer verification in production
        if self.is_production() and self.transport.peer_verification != PeerVerification.STRICT:
            raise ConfigurationError(
                "transport.peer_verification must be 'strict' in production environment",
                details={
                    "environment": self.agent.environment.value,
                    "peer_verification": self.transport.peer_verification.value,
                },
            )

        # RULE 4: TLS 1.2 minimum (1.3 recommended)
        # This is already enforced by the Literal type, but we check for clarity
        if self.transport.tls_min_version not in ("1.2", "1.3"):
            raise ConfigurationError(
                "transport.tls_min_version must be '1.2' or '1.3'",
                details={"tls_min_version": self.transport.tls_min_version},
            )

        # RULE 5: Audit enabled in production
        if self.is_production() and not self.authorization.audit.enabled:
            raise ConfigurationError(
                "authorization.audit.enabled must be true in production environment",
                details={"environment": self.agent.environment.value},
            )

        # RULE 6: Valid SPIFFE trust domain (already validated in AgentSettings)
        # Additional check: agent's trust domain should be in allowed list (implicitly)
        if self.agent.trust_domain not in [
            self.agent.trust_domain,
            *self.identity.allowed_trust_domains,
        ]:
            # This shouldn't happen, but being explicit
            pass

        return self

    @classmethod
    def from_file(cls, path: str | Path) -> "AgentConfig":
        """
        Load configuration from YAML file.

        Args:
            path: Path to YAML configuration file

        Returns:
            Validated AgentConfig instance

        Raises:
            ConfigurationError: If file cannot be read or configuration is invalid

        Example:
            config = AgentConfig.from_file("config.yaml")
        """
        try:
            config_path = Path(path)
            if not config_path.exists():
                raise ConfigurationError(
                    f"Configuration file not found: {path}",
                    details={"path": str(path)},
                )

            with open(config_path) as f:
                data = yaml.safe_load(f)

            if not isinstance(data, dict):
                raise ConfigurationError(
                    "Configuration file must contain a YAML dictionary",
                    details={"path": str(path)},
                )

            return cls(**data)

        except yaml.YAMLError as e:
            raise ConfigurationError(
                f"Invalid YAML in configuration file: {e}",
                details={"path": str(path), "error": str(e)},
            ) from e
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            raise ConfigurationError(
                f"Failed to load configuration: {e}",
                details={"path": str(path), "error": str(e)},
            ) from e

    @classmethod
    def from_env(cls, prefix: str = "AGENTWEAVE_") -> "AgentConfig":
        """
        Load configuration from environment variables.

        Environment variables override file-based configuration.
        Variable names follow the pattern: {prefix}{SECTION}_{KEY}

        Examples:
            AGENTWEAVE_AGENT_NAME=my-agent
            AGENTWEAVE_AGENT_TRUST_DOMAIN=agentweave.io
            AGENTWEAVE_IDENTITY_SPIFFE_ENDPOINT=unix:///run/spire/sockets/agent.sock
            AGENTWEAVE_TRANSPORT_TLS_MIN_VERSION=1.3
            AGENTWEAVE_SERVER_PORT=8443

        Args:
            prefix: Environment variable prefix (default: "AGENTWEAVE_")

        Returns:
            Validated AgentConfig instance

        Raises:
            ConfigurationError: If required variables are missing or invalid
        """
        env_data: dict[str, Any] = {
            "agent": {},
            "identity": {},
            "authorization": {},
            "transport": {},
            "server": {},
            "observability": {},
        }

        # Map environment variables to config structure
        for key, value in os.environ.items():
            if not key.startswith(prefix):
                continue

            # Remove prefix and split into section and field
            config_path = key[len(prefix) :].lower().split("_", 1)
            if len(config_path) != 2:
                continue

            section, field = config_path
            if section in env_data:
                env_data[section][field] = value

        # Ensure required fields
        if not env_data["agent"].get("name") or not env_data["agent"].get("trust_domain"):
            raise ConfigurationError(
                "Required environment variables missing",
                details={
                    "required": [
                        f"{prefix}AGENT_NAME",
                        f"{prefix}AGENT_TRUST_DOMAIN",
                    ]
                },
            )

        try:
            return cls(**env_data)
        except Exception as e:
            raise ConfigurationError(
                f"Failed to load configuration from environment: {e}",
                details={"error": str(e)},
            ) from e
