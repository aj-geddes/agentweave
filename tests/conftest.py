"""
Shared pytest configuration for AgentWeave SDK tests.

This module configures pytest and imports all fixtures for use in tests.
"""

import asyncio
import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import all fixtures from agentweave.testing
from agentweave.testing import (
    mock_identity_provider,
    mock_authz_provider,
    test_agent,
    test_config,
)

# Re-export fixtures so they're available to all tests
__all__ = [
    "mock_identity_provider",
    "mock_authz_provider",
    "test_agent",
    "test_config",
]


# Configure pytest-asyncio
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async (automatically applied to async tests)"
    )
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires Docker)"
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers",
        "unit: mark test as unit test"
    )


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the entire test session.

    This ensures all async tests use the same event loop.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def anyio_backend():
    """
    Specify backend for anyio-based async tests.

    Returns:
        str: Backend name (asyncio)
    """
    return "asyncio"


# Additional custom fixtures for common test scenarios

@pytest.fixture
def mock_spiffe_ids():
    """
    Provides common SPIFFE IDs for testing.

    Returns:
        Dict of named SPIFFE IDs
    """
    return {
        "orchestrator": "spiffe://test.local/agent/orchestrator",
        "search": "spiffe://test.local/agent/search",
        "processor": "spiffe://test.local/agent/processor",
        "indexer": "spiffe://test.local/agent/indexer",
        "unknown": "spiffe://unknown.com/agent/malicious",
        "federated": "spiffe://partner.example.com/agent/partner",
    }


@pytest.fixture
def sample_a2a_task():
    """
    Provides a sample A2A task for testing.

    Returns:
        Dict representing an A2A task
    """
    return {
        "id": "task-test-001",
        "type": "search",
        "state": "submitted",
        "messages": [
            {
                "role": "user",
                "parts": [
                    {
                        "type": "data",
                        "data": {
                            "query": "test query",
                            "limit": 10,
                        },
                    }
                ],
            }
        ],
    }


@pytest.fixture
def sample_authz_input():
    """
    Provides sample authorization input for policy testing.

    Returns:
        Dict representing authorization input
    """
    return {
        "caller_spiffe_id": "spiffe://test.local/agent/orchestrator",
        "callee_spiffe_id": "spiffe://test.local/agent/search",
        "action": "search",
        "context": {
            "timestamp": "2025-12-06T12:00:00Z",
            "payload_size": 1024,
        },
    }


@pytest.fixture
def temp_config_file(tmp_path, test_config):
    """
    Create a temporary config file for testing.

    Args:
        tmp_path: pytest temporary path fixture
        test_config: test configuration dict

    Returns:
        Path to temporary config file
    """
    import yaml

    config_file = tmp_path / "config.yaml"
    with open(config_file, "w") as f:
        yaml.dump(test_config, f)

    return config_file


# Hooks for test collection and reporting

def pytest_collection_modifyitems(config, items):
    """
    Modify test items during collection.

    Automatically marks async tests with asyncio marker.
    """
    for item in items:
        # Auto-mark async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)

        # Auto-mark integration tests
        if "cluster" in item.fixturenames or "test_cluster" in item.fixturenames:
            item.add_marker(pytest.mark.integration)


def pytest_addoption(parser):
    """Add custom command-line options."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires Docker)",
    )
    parser.addoption(
        "--run-slow",
        action="store_true",
        default=False,
        help="Run slow tests",
    )


def pytest_runtest_setup(item):
    """
    Setup hook for test execution.

    Skip integration tests unless --run-integration is passed.
    Skip slow tests unless --run-slow is passed.
    """
    # Skip integration tests if flag not set
    if "integration" in item.keywords and not item.config.getoption("--run-integration"):
        pytest.skip("integration tests not enabled (use --run-integration)")

    # Skip slow tests if flag not set
    if "slow" in item.keywords and not item.config.getoption("--run-slow"):
        pytest.skip("slow tests not enabled (use --run-slow)")
