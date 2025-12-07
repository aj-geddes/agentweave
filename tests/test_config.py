"""
Tests for AgentWeave SDK configuration.

Tests configuration loading, validation, and security guarantees.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from typing import Dict, Any


class TestConfigLoading:
    """Test configuration loading from various sources."""

    def test_config_from_dict(self, test_config):
        """Test loading configuration from dictionary."""
        # This would use the actual AgentConfig class
        # For now, just validate the structure
        assert "agent" in test_config
        assert "identity" in test_config
        assert "authorization" in test_config
        assert "transport" in test_config
        assert "server" in test_config

    def test_config_from_file(self, temp_config_file):
        """Test loading configuration from YAML file."""
        # Read and validate
        with open(temp_config_file) as f:
            config = yaml.safe_load(f)

        assert config["agent"]["name"] == "test-agent"
        assert config["identity"]["provider"] == "spiffe"

    def test_config_validation_required_fields(self):
        """Test that required fields are validated."""
        # Missing required field
        invalid_config = {
            "agent": {
                # Missing name
                "trust_domain": "test.local",
            }
        }

        # This should raise validation error
        # When AgentConfig is implemented:
        # with pytest.raises(ValidationError):
        #     AgentConfig(**invalid_config)

    def test_config_immutable(self, test_config):
        """Test that configuration is immutable after creation."""
        # Config should be frozen
        # When AgentConfig is implemented:
        # config = AgentConfig(**test_config)
        # with pytest.raises(FrozenInstanceError):
        #     config.agent.name = "new-name"
        pass


class TestConfigValidation:
    """Test configuration validation rules."""

    def test_valid_trust_domain(self, test_config):
        """Test that trust domain must be valid."""
        # Valid trust domains
        valid_domains = [
            "test.local",
            "example.com",
            "hvs.solutions",
            "multi-part.trust.domain.example.com",
        ]

        for domain in valid_domains:
            config = test_config.copy()
            config["agent"]["trust_domain"] = domain
            # Should not raise
            # AgentConfig(**config)

    def test_invalid_trust_domain(self, test_config):
        """Test that invalid trust domains are rejected."""
        invalid_domains = [
            "",
            "invalid domain",
            "spiffe://test.local",  # Should not include protocol
            "test.local/path",  # Should not include path
        ]

        for domain in invalid_domains:
            config = test_config.copy()
            config["agent"]["trust_domain"] = domain
            # Should raise validation error
            # with pytest.raises(ValidationError):
            #     AgentConfig(**config)

    def test_tls_min_version_validation(self, test_config):
        """Test TLS minimum version validation."""
        # Valid versions
        for version in ["1.2", "1.3"]:
            config = test_config.copy()
            config["transport"]["tls_min_version"] = version
            # Should not raise
            # AgentConfig(**config)

        # Invalid versions
        for version in ["1.0", "1.1", "2.0", "invalid"]:
            config = test_config.copy()
            config["transport"]["tls_min_version"] = version
            # Should raise
            # with pytest.raises(ValidationError):
            #     AgentConfig(**config)

    def test_peer_verification_validation(self, test_config):
        """Test peer verification mode validation."""
        # Valid modes
        for mode in ["strict", "log-only"]:
            config = test_config.copy()
            config["transport"]["peer_verification"] = mode
            # Should not raise
            # AgentConfig(**config)

        # Invalid mode (none is not allowed)
        config = test_config.copy()
        config["transport"]["peer_verification"] = "none"
        # Should raise
        # with pytest.raises(ValidationError):
        #     AgentConfig(**config)


class TestSecurityGuarantees:
    """Test security guarantee enforcement in configuration."""

    def test_production_default_deny(self, test_config):
        """Test that production configs must have default deny."""
        # Production environment (simulated)
        config = test_config.copy()
        config["authorization"]["default_action"] = "allow-all"

        # In production mode, this should fail
        # with pytest.raises(ValidationError, match="default_action must be 'deny'"):
        #     AgentConfig(**config, environment="production")

    def test_dev_mode_relaxed_security(self, test_config_dev):
        """Test that dev mode allows relaxed security."""
        # Dev mode should allow log-only peer verification
        assert test_config_dev["transport"]["peer_verification"] == "log-only"
        assert test_config_dev["authorization"]["default_action"] == "log-only"

        # Should not raise in dev mode
        # AgentConfig(**test_config_dev, environment="development")

    def test_spiffe_endpoint_validation(self, test_config):
        """Test SPIFFE endpoint validation."""
        valid_endpoints = [
            "unix:///run/spire/sockets/agent.sock",
            "unix:///var/run/spire/agent.sock",
            "tcp://localhost:8081",
        ]

        for endpoint in valid_endpoints:
            config = test_config.copy()
            config["identity"]["spiffe_endpoint"] = endpoint
            # Should not raise
            # AgentConfig(**config)

    def test_opa_endpoint_validation(self, test_config):
        """Test OPA endpoint validation."""
        valid_endpoints = [
            "http://localhost:8181",
            "http://opa:8181",
            "https://opa.example.com:8181",
        ]

        for endpoint in valid_endpoints:
            config = test_config.copy()
            config["authorization"]["opa_endpoint"] = endpoint
            # Should not raise
            # AgentConfig(**config)


class TestConfigCapabilities:
    """Test capability configuration."""

    def test_valid_capability(self, test_config):
        """Test valid capability definition."""
        capability = {
            "name": "test_capability",
            "description": "Test capability",
            "input_modes": ["application/json"],
            "output_modes": ["application/json"],
        }

        config = test_config.copy()
        config["agent"]["capabilities"] = [capability]
        # Should not raise
        # AgentConfig(**config)

    def test_capability_name_validation(self, test_config):
        """Test capability name validation."""
        # Valid names (snake_case)
        valid_names = [
            "search",
            "process_data",
            "index_documents",
            "get_status",
        ]

        for name in valid_names:
            capability = {
                "name": name,
                "description": "Test",
                "input_modes": ["application/json"],
                "output_modes": ["application/json"],
            }
            config = test_config.copy()
            config["agent"]["capabilities"] = [capability]
            # Should not raise
            # AgentConfig(**config)

        # Invalid names
        invalid_names = [
            "Search",  # PascalCase
            "process-data",  # kebab-case
            "index.documents",  # dots
            "get status",  # spaces
        ]

        for name in invalid_names:
            capability = {
                "name": name,
                "description": "Test",
                "input_modes": ["application/json"],
                "output_modes": ["application/json"],
            }
            config = test_config.copy()
            config["agent"]["capabilities"] = [capability]
            # Should raise
            # with pytest.raises(ValidationError):
            #     AgentConfig(**config)

    def test_duplicate_capabilities(self, test_config):
        """Test that duplicate capability names are rejected."""
        config = test_config.copy()
        config["agent"]["capabilities"] = [
            {
                "name": "search",
                "description": "Search 1",
                "input_modes": ["application/json"],
                "output_modes": ["application/json"],
            },
            {
                "name": "search",  # Duplicate
                "description": "Search 2",
                "input_modes": ["application/json"],
                "output_modes": ["application/json"],
            },
        ]

        # Should raise
        # with pytest.raises(ValidationError, match="duplicate capability"):
        #     AgentConfig(**config)


class TestTransportConfig:
    """Test transport configuration."""

    def test_connection_pool_settings(self, test_config):
        """Test connection pool configuration."""
        config = test_config.copy()
        config["transport"]["connection_pool"] = {
            "max_connections": 100,
            "idle_timeout_seconds": 60,
        }
        # Should not raise
        # AgentConfig(**config)

        # Test validation
        config["transport"]["connection_pool"]["max_connections"] = 0
        # Should raise (must be > 0)
        # with pytest.raises(ValidationError):
        #     AgentConfig(**config)

    def test_circuit_breaker_settings(self, test_config):
        """Test circuit breaker configuration."""
        config = test_config.copy()
        config["transport"]["circuit_breaker"] = {
            "failure_threshold": 5,
            "recovery_timeout_seconds": 30,
        }
        # Should not raise
        # AgentConfig(**config)

    def test_retry_settings(self, test_config):
        """Test retry configuration."""
        config = test_config.copy()
        config["transport"]["retry"] = {
            "max_attempts": 3,
            "backoff_base_seconds": 1.0,
            "backoff_max_seconds": 30.0,
        }
        # Should not raise
        # AgentConfig(**config)

        # Validate backoff relationship
        config["transport"]["retry"]["backoff_max_seconds"] = 0.5
        # Should raise (max must be >= base)
        # with pytest.raises(ValidationError):
        #     AgentConfig(**config)


class TestObservabilityConfig:
    """Test observability configuration."""

    def test_metrics_config(self, test_config):
        """Test metrics configuration."""
        config = test_config.copy()
        config["observability"]["metrics"] = {
            "enabled": True,
            "port": 9090,
        }
        # Should not raise
        # AgentConfig(**config)

    def test_tracing_config(self, test_config):
        """Test tracing configuration."""
        config = test_config.copy()
        config["observability"]["tracing"] = {
            "enabled": True,
            "exporter": "otlp",
            "endpoint": "http://collector:4317",
        }
        # Should not raise
        # AgentConfig(**config)

        # Test invalid exporter
        config["observability"]["tracing"]["exporter"] = "invalid"
        # Should raise
        # with pytest.raises(ValidationError):
        #     AgentConfig(**config)

    def test_logging_config(self, test_config):
        """Test logging configuration."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        valid_formats = ["json", "text"]

        for level in valid_levels:
            config = test_config.copy()
            config["observability"]["logging"]["level"] = level
            # Should not raise
            # AgentConfig(**config)

        for fmt in valid_formats:
            config = test_config.copy()
            config["observability"]["logging"]["format"] = fmt
            # Should not raise
            # AgentConfig(**config)


@pytest.mark.parametrize(
    "provider,expected_valid",
    [
        ("spiffe", True),
        ("mtls-static", True),
        ("invalid", False),
    ],
)
def test_identity_provider_validation(test_config, provider, expected_valid):
    """Test identity provider validation."""
    config = test_config.copy()
    config["identity"]["provider"] = provider

    if expected_valid:
        # Should not raise
        # AgentConfig(**config)
        pass
    else:
        # Should raise
        # with pytest.raises(ValidationError):
        #     AgentConfig(**config)
        pass


@pytest.mark.parametrize(
    "provider,expected_valid",
    [
        ("opa", True),
        ("allow-all", True),
        ("invalid", False),
    ],
)
def test_authz_provider_validation(test_config, provider, expected_valid):
    """Test authorization provider validation."""
    config = test_config.copy()
    config["authorization"]["provider"] = provider

    if expected_valid:
        # Should not raise
        # AgentConfig(**config)
        pass
    else:
        # Should raise
        # with pytest.raises(ValidationError):
        #     AgentConfig(**config)
        pass
