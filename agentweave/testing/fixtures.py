"""
Pytest fixtures for AgentWeave SDK testing.

This module provides reusable pytest fixtures for testing agents.
Import these fixtures in your conftest.py or test files.
"""

import pytest
from typing import Dict, Any
from .mocks import (
    MockIdentityProvider,
    MockAuthorizationProvider,
    MockTransport,
)


@pytest.fixture
def mock_identity_provider():
    """
    Provides a mock identity provider for testing.

    Returns:
        MockIdentityProvider configured with test SPIFFE ID

    Example:
        def test_agent_identity(mock_identity_provider):
            svid = await mock_identity_provider.get_svid()
            assert svid.spiffe_id == "spiffe://test.local/agent/test"
    """
    return MockIdentityProvider(
        spiffe_id="spiffe://test.local/agent/test",
        trust_domain="test.local",
        rotation_interval=3600,
        auto_rotate=False,
    )


@pytest.fixture
def mock_identity_provider_with_rotation():
    """
    Provides a mock identity provider with auto-rotation enabled.

    Returns:
        MockIdentityProvider with 60-second rotation interval

    Example:
        async def test_svid_rotation(mock_identity_provider_with_rotation):
            provider = mock_identity_provider_with_rotation
            await provider.start_auto_rotation()
            # Wait and verify rotation occurs
            await asyncio.sleep(61)
            # ...
    """
    return MockIdentityProvider(
        spiffe_id="spiffe://test.local/agent/test",
        trust_domain="test.local",
        rotation_interval=60,
        auto_rotate=True,
    )


@pytest.fixture
def mock_authz_provider():
    """
    Provides a mock authorization provider with default deny.

    Returns:
        MockAuthorizationProvider configured to deny by default

    Example:
        async def test_authz(mock_authz_provider):
            decision = await mock_authz_provider.check_inbound(
                caller_id="spiffe://test.local/agent/caller",
                action="search"
            )
            assert decision.allowed == False
    """
    return MockAuthorizationProvider(
        default_allow=False,
        policy_rules={},
    )


@pytest.fixture
def mock_authz_provider_permissive():
    """
    Provides a permissive mock authorization provider (allow all).

    Returns:
        MockAuthorizationProvider configured to allow all requests

    Example:
        async def test_agent_call(mock_authz_provider_permissive):
            decision = await mock_authz_provider_permissive.check_inbound(
                caller_id="spiffe://test.local/agent/caller",
                action="any_action"
            )
            assert decision.allowed == True
    """
    return MockAuthorizationProvider(
        default_allow=True,
        policy_rules={},
    )


@pytest.fixture
def mock_transport():
    """
    Provides a mock transport layer for testing.

    Returns:
        MockTransport for simulating HTTP requests/responses

    Example:
        async def test_http_call(mock_transport):
            mock_transport.add_response(
                url="https://example.com/api",
                status_code=200,
                body=b'{"result": "ok"}'
            )
            response = await mock_transport.get("https://example.com/api")
            assert response.status_code == 200
    """
    return MockTransport()


@pytest.fixture
def test_config() -> Dict[str, Any]:
    """
    Provides a valid test configuration for agents.

    Returns:
        Dict containing valid agent configuration

    Example:
        def test_config_validation(test_config):
            config = AgentConfig(**test_config)
            assert config.agent.name == "test-agent"
    """
    return {
        "agent": {
            "name": "test-agent",
            "trust_domain": "test.local",
            "description": "Test agent for unit testing",
            "capabilities": [
                {
                    "name": "test_capability",
                    "description": "Test capability",
                    "input_modes": ["application/json"],
                    "output_modes": ["application/json"],
                }
            ],
        },
        "identity": {
            "provider": "spiffe",
            "spiffe_endpoint": "unix:///run/spire/sockets/agent.sock",
            "allowed_trust_domains": ["test.local"],
        },
        "authorization": {
            "provider": "opa",
            "opa_endpoint": "http://localhost:8181",
            "policy_path": "agentweave/authz",
            "default_action": "deny",
            "audit": {
                "enabled": True,
                "destination": "file:///tmp/agentweave-audit.log",
            },
        },
        "transport": {
            "tls_min_version": "1.3",
            "peer_verification": "strict",
            "connection_pool": {
                "max_connections": 100,
                "idle_timeout_seconds": 60,
            },
            "circuit_breaker": {
                "failure_threshold": 5,
                "recovery_timeout_seconds": 30,
            },
            "retry": {
                "max_attempts": 3,
                "backoff_base_seconds": 1.0,
                "backoff_max_seconds": 30.0,
            },
        },
        "server": {
            "host": "0.0.0.0",
            "port": 8443,
            "protocol": "a2a",
        },
        "observability": {
            "metrics": {
                "enabled": True,
                "port": 9090,
            },
            "tracing": {
                "enabled": False,
                "exporter": "otlp",
                "endpoint": "http://localhost:4317",
            },
            "logging": {
                "level": "INFO",
                "format": "json",
            },
        },
    }


@pytest.fixture
def test_config_dev() -> Dict[str, Any]:
    """
    Provides a development-mode test configuration.

    Returns:
        Dict containing dev configuration with relaxed security

    Example:
        def test_dev_mode(test_config_dev):
            config = AgentConfig(**test_config_dev)
            assert config.authorization.default_action == "log-only"
    """
    return {
        "agent": {
            "name": "dev-agent",
            "trust_domain": "dev.local",
            "description": "Development test agent",
            "capabilities": [],
        },
        "identity": {
            "provider": "mtls-static",
            "allowed_trust_domains": ["dev.local"],
        },
        "authorization": {
            "provider": "allow-all",
            "default_action": "log-only",
            "audit": {
                "enabled": False,
            },
        },
        "transport": {
            "tls_min_version": "1.2",
            "peer_verification": "log-only",
            "connection_pool": {
                "max_connections": 10,
                "idle_timeout_seconds": 30,
            },
        },
        "server": {
            "host": "127.0.0.1",
            "port": 8080,
            "protocol": "a2a",
        },
        "observability": {
            "metrics": {"enabled": False},
            "tracing": {"enabled": False},
            "logging": {"level": "DEBUG", "format": "text"},
        },
    }


@pytest.fixture
async def test_agent(mock_identity_provider, mock_authz_provider, test_config):
    """
    Provides a fully configured test agent with mocks.

    Returns:
        SecureAgent instance configured with mock providers

    Example:
        async def test_agent_capability(test_agent):
            result = await test_agent.call_capability("test_capability", {})
            assert result is not None

    Note:
        This fixture requires the actual SecureAgent implementation.
        Placeholder implementation shown here.
    """
    # This would be the actual agent initialization
    # For now, return a mock agent configuration
    class MockAgent:
        def __init__(self, identity, authz, config):
            self.identity = identity
            self.authz = authz
            self.config = config
            self.spiffe_id = identity.get_spiffe_id()

        async def start(self):
            """Start the agent."""
            pass

        async def stop(self):
            """Stop the agent."""
            pass

        async def call_capability(self, capability: str, payload: Dict[str, Any]):
            """Call a capability."""
            return {"status": "completed", "result": {}}

    agent = MockAgent(
        identity=mock_identity_provider,
        authz=mock_authz_provider,
        config=test_config,
    )

    await agent.start()
    yield agent
    await agent.stop()


@pytest.fixture
def spiffe_ids():
    """
    Provides a collection of test SPIFFE IDs.

    Returns:
        Dict of named SPIFFE IDs for testing

    Example:
        def test_authz_policy(spiffe_ids, mock_authz_provider):
            mock_authz_provider.add_rule(
                caller_id=spiffe_ids["orchestrator"],
                callee_id=spiffe_ids["search"],
                action="search",
                allowed=True
            )
    """
    return {
        "orchestrator": "spiffe://test.local/agent/orchestrator",
        "search": "spiffe://test.local/agent/search",
        "processor": "spiffe://test.local/agent/processor",
        "indexer": "spiffe://test.local/agent/indexer",
        "unknown": "spiffe://unknown.com/agent/malicious",
    }


@pytest.fixture
def sample_tasks():
    """
    Provides sample A2A tasks for testing.

    Returns:
        Dict of sample task payloads

    Example:
        async def test_task_handling(test_agent, sample_tasks):
            result = await test_agent.handle_task(sample_tasks["search"])
            assert result.status == "completed"
    """
    return {
        "search": {
            "id": "task-001",
            "type": "search",
            "state": "submitted",
            "messages": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "type": "data",
                            "data": {"query": "test query", "limit": 10},
                        }
                    ],
                }
            ],
        },
        "process": {
            "id": "task-002",
            "type": "process",
            "state": "submitted",
            "messages": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "type": "data",
                            "data": {"items": [1, 2, 3]},
                        }
                    ],
                }
            ],
        },
        "index": {
            "id": "task-003",
            "type": "index",
            "state": "submitted",
            "messages": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "type": "data",
                            "data": {
                                "documents": [
                                    {"id": "doc1", "content": "test content"}
                                ]
                            },
                        }
                    ],
                }
            ],
        },
    }


# Async fixture helper for pytest-asyncio
@pytest.fixture(scope="session")
def event_loop():
    """
    Provides event loop for async tests.

    This fixture ensures a single event loop for all async tests
    in a session.
    """
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
