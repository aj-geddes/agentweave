# AgentWeave SDK - Testing Guide

This guide covers the testing utilities and best practices for testing agents built with the AgentWeave SDK.

## Table of Contents

1. [Overview](#overview)
2. [Testing Utilities](#testing-utilities)
3. [Mock Providers](#mock-providers)
4. [Pytest Fixtures](#pytest-fixtures)
5. [Integration Testing](#integration-testing)
6. [Policy Testing](#policy-testing)
7. [Running Tests](#running-tests)
8. [Example Tests](#example-tests)

---

## Overview

The AgentWeave SDK includes comprehensive testing utilities that allow you to:

- Test agents without requiring SPIRE or OPA infrastructure
- Mock identity and authorization providers
- Simulate network conditions and failures
- Run integration tests with real SPIRE and OPA (optional)
- Test OPA policies locally without a server

---

## Testing Utilities

### Module Structure

```
hvs_agent/testing/
├── __init__.py          # Public API exports
├── mocks.py             # Mock providers (Identity, Authorization, Transport)
├── fixtures.py          # Pytest fixtures
├── cluster.py           # TestCluster for integration tests
└── policy.py            # PolicySimulator for Rego testing
```

### Installation

```bash
# Install test dependencies
pip install -r requirements-test.txt
```

---

## Mock Providers

### MockIdentityProvider

Simulates SPIFFE identity without requiring SPIRE.

**Features:**
- Returns configurable SPIFFE ID
- Generates self-signed certificates
- Simulates certificate rotation
- No SPIRE connection required

**Example:**

```python
from agentweave.testing import MockIdentityProvider

# Create mock provider
provider = MockIdentityProvider(
    spiffe_id="spiffe://test.local/agent/my-agent",
    rotation_interval=3600,  # 1 hour
)

# Get SVID
svid = await provider.get_svid()
assert svid.spiffe_id == "spiffe://test.local/agent/my-agent"

# Get trust bundle
bundle = await provider.get_trust_bundle("test.local")

# Manual rotation
new_svid = await provider.rotate_svid()

# Watch for updates
async for svid in provider.watch_updates():
    print(f"SVID rotated: {svid.spiffe_id}")
```

### MockAuthorizationProvider

Simulates OPA authorization without requiring OPA server.

**Features:**
- Configurable allow/deny responses
- Records all authorization checks
- Policy-based rules
- Audit trail

**Example:**

```python
from agentweave.testing import MockAuthorizationProvider

# Create mock authz (default deny)
authz = MockAuthorizationProvider(default_allow=False)

# Add allow rule
authz.add_rule(
    caller_id="spiffe://test.local/agent/orchestrator",
    callee_id="spiffe://test.local/agent/search",
    action="search",
    allowed=True,
)

# Check authorization
decision = await authz.check_outbound(
    caller_id="spiffe://test.local/agent/orchestrator",
    callee_id="spiffe://test.local/agent/search",
    action="search",
)
assert decision.allowed == True

# Get audit trail
checks = authz.get_checks()
print(f"Made {len(checks)} authorization checks")
```

### MockTransport

Simulates HTTP transport layer for testing.

**Features:**
- Records all requests
- Returns configurable responses
- Simulates network failures
- SSL context verification

**Example:**

```python
from agentweave.testing import MockTransport

# Create mock transport
transport = MockTransport()

# Add canned response
transport.add_response(
    url="https://agent.example.com/task",
    status_code=200,
    body=b'{"status": "completed"}',
)

# Make request
response = await transport.post(
    "https://agent.example.com/task",
    data=b'{"task": "test"}',
)
assert response.status_code == 200

# Get request history
requests = transport.get_requests()
print(f"Made {len(requests)} requests")

# Simulate failures
transport.set_failure_mode("timeout")
# Next request will timeout
```

---

## Pytest Fixtures

The SDK provides ready-to-use pytest fixtures.

### Available Fixtures

```python
# Import fixtures
from agentweave.testing import (
    mock_identity_provider,
    mock_authz_provider,
    test_agent,
    test_config,
)

# Use in tests
@pytest.mark.asyncio
async def test_my_agent(test_agent, mock_authz_provider):
    # test_agent is fully configured with mocks
    result = await test_agent.call_capability("search", {"query": "test"})
    assert result is not None

    # Check authorization was called
    checks = mock_authz_provider.get_checks()
    assert len(checks) > 0
```

### Custom Fixtures

Create your own fixtures in `tests/conftest.py`:

```python
import pytest
from agentweave.testing import MockIdentityProvider

@pytest.fixture
def my_custom_identity():
    return MockIdentityProvider(
        spiffe_id="spiffe://my-domain.com/agent/custom",
    )
```

---

## Integration Testing

### TestCluster

Spins up real SPIRE and OPA servers for integration testing.

**Features:**
- Docker-based SPIRE server and agent
- Docker-based OPA server
- Automatic agent registration
- Cleanup on exit

**Example:**

```python
from agentweave.testing import TestCluster

@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_real_spire():
    async with TestCluster() as cluster:
        # Register agent with SPIRE
        await cluster.register_agent(
            spiffe_id="spiffe://test.local/agent/search",
            selectors=["unix:uid:1000"],
        )

        # Deploy your agent
        agent = await cluster.deploy_agent(MySearchAgent)

        # Test with real identity and authorization
        result = await agent.search("test query")
        assert result is not None
```

### Running Integration Tests

```bash
# Integration tests are skipped by default
pytest

# Run integration tests (requires Docker)
pytest --run-integration

# Run only integration tests
pytest -m integration --run-integration
```

---

## Policy Testing

### PolicySimulator

Test OPA Rego policies without running an OPA server.

**Features:**
- Load Rego policies from file or string
- Evaluate policies against test inputs
- Assert allow/deny scenarios
- Test multiple scenarios at once

**Requirements:**
- OPA CLI must be installed: https://www.openpolicyagent.org/docs/latest/#running-opa

**Example:**

```python
from agentweave.testing import PolicySimulator

# Create simulator with policy
simulator = PolicySimulator("policies/authz.rego")

# Test allow scenario
decision = simulator.check(
    caller="spiffe://test.local/agent/orchestrator",
    callee="spiffe://test.local/agent/search",
    action="search",
)
assert decision.allowed == True

# Test deny scenario
decision = simulator.check(
    caller="spiffe://evil.com/agent/attacker",
    callee="spiffe://test.local/agent/search",
    action="search",
)
assert decision.allowed == False

# Use assertion helpers
simulator.assert_allow(
    caller="spiffe://test.local/agent/orchestrator",
    callee="spiffe://test.local/agent/search",
    action="search",
)

simulator.assert_deny(
    caller="spiffe://evil.com/agent/attacker",
    callee="spiffe://test.local/agent/search",
    action="search",
)
```

### Testing Multiple Scenarios

```python
scenarios = [
    {
        "name": "orchestrator_can_search",
        "input": {
            "caller_spiffe_id": "spiffe://test.local/agent/orchestrator",
            "callee_spiffe_id": "spiffe://test.local/agent/search",
            "action": "search",
        },
        "expected": True,
    },
    {
        "name": "unknown_agent_denied",
        "input": {
            "caller_spiffe_id": "spiffe://evil.com/agent/bad",
            "callee_spiffe_id": "spiffe://test.local/agent/search",
            "action": "search",
        },
        "expected": False,
    },
]

results = simulator.test_scenarios(scenarios)
for name, decision in results.items():
    print(f"{name}: {'PASS' if decision.allowed else 'FAIL'}")
```

---

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_identity.py

# Run specific test
pytest tests/test_identity.py::TestMockIdentityProvider::test_get_svid

# Run tests matching pattern
pytest -k "test_svid"
```

### Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests (requires Docker)
pytest -m integration --run-integration

# Run slow tests
pytest -m slow --run-slow

# Skip slow tests
pytest -m "not slow"
```

### Coverage Reports

```bash
# Run with coverage
pytest --cov=agentweave --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Parallel Execution

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel
pytest -n auto
```

---

## Example Tests

### Testing an Agent

```python
import pytest
from agentweave.testing import MockIdentityProvider, MockAuthorizationProvider

class MySearchAgent:
    def __init__(self, identity, authz):
        self.identity = identity
        self.authz = authz

    async def search(self, query: str):
        # Agent implementation
        return {"results": []}

@pytest.mark.asyncio
async def test_search_agent():
    # Setup mocks
    identity = MockIdentityProvider(
        spiffe_id="spiffe://test.local/agent/search",
    )
    authz = MockAuthorizationProvider(default_allow=True)

    # Create agent
    agent = MySearchAgent(identity, authz)

    # Test search
    result = await agent.search("test query")
    assert "results" in result
```

### Testing Authorization

```python
import pytest
from agentweave.testing import MockAuthorizationProvider

@pytest.mark.asyncio
async def test_authorization_rules():
    authz = MockAuthorizationProvider(default_allow=False)

    # Add rule: orchestrator can call search
    authz.add_rule(
        caller_id="spiffe://test.local/agent/orchestrator",
        callee_id="spiffe://test.local/agent/search",
        action="search",
        allowed=True,
    )

    # Should be allowed
    decision = await authz.check_outbound(
        caller_id="spiffe://test.local/agent/orchestrator",
        callee_id="spiffe://test.local/agent/search",
        action="search",
    )
    assert decision.allowed == True

    # Different caller should be denied
    decision = await authz.check_outbound(
        caller_id="spiffe://test.local/agent/other",
        callee_id="spiffe://test.local/agent/search",
        action="search",
    )
    assert decision.allowed == False
```

### Testing SVID Rotation

```python
import pytest
import asyncio
from agentweave.testing import MockIdentityProvider

@pytest.mark.asyncio
async def test_svid_rotation():
    provider = MockIdentityProvider(
        spiffe_id="spiffe://test.local/agent/test",
        rotation_interval=2,  # 2 seconds
    )

    # Get initial SVID
    svid1 = await provider.get_svid()

    # Rotate
    svid2 = await provider.rotate_svid()

    # Should be different
    assert svid2.cert_chain != svid1.cert_chain

    # New SVID should not be expired
    assert not svid2.is_expired()
```

### Testing with Fixtures

```python
import pytest

@pytest.mark.asyncio
async def test_with_fixtures(test_agent, mock_authz_provider, spiffe_ids):
    # Setup authorization
    mock_authz_provider.add_rule(
        caller_id=spiffe_ids["orchestrator"],
        callee_id=None,
        action="test_capability",
        allowed=True,
    )

    # Test agent
    result = await test_agent.call_capability("test_capability", {})
    assert result["status"] == "completed"

    # Verify authorization was checked
    checks = mock_authz_provider.get_checks()
    assert len(checks) > 0
```

---

## Best Practices

### 1. Use Fixtures for Common Setup

```python
@pytest.fixture
def configured_authz():
    authz = MockAuthorizationProvider(default_allow=False)
    # Add common rules
    authz.add_rule("spiffe://test.local/agent/orchestrator",
                   "spiffe://test.local/agent/search",
                   "search", True)
    return authz
```

### 2. Test Both Success and Failure Paths

```python
async def test_success_path(test_agent):
    result = await test_agent.call_capability("search", {"query": "test"})
    assert result["status"] == "completed"

async def test_failure_path(test_agent):
    with pytest.raises(ValidationError):
        await test_agent.call_capability("search", {"invalid": "data"})
```

### 3. Verify Authorization Checks

```python
async def test_authorization_enforced(test_agent, mock_authz_provider):
    mock_authz_provider.clear_checks()

    await test_agent.call_capability("search", {})

    # Verify authorization was checked
    assert len(mock_authz_provider.get_checks()) > 0
```

### 4. Use Parametrized Tests for Multiple Scenarios

```python
@pytest.mark.parametrize("caller,action,expected", [
    ("spiffe://test.local/agent/orchestrator", "search", True),
    ("spiffe://test.local/agent/processor", "search", True),
    ("spiffe://evil.com/agent/bad", "search", False),
])
async def test_authz_scenarios(mock_authz_provider, caller, action, expected):
    decision = await mock_authz_provider.check_inbound(caller, action)
    assert decision.allowed == expected
```

### 5. Clean Up After Tests

```python
@pytest.fixture
async def my_agent():
    agent = MyAgent()
    await agent.start()
    yield agent
    await agent.stop()  # Cleanup
```

---

## Troubleshooting

### OPA CLI Not Found

If you see "OPA CLI not found" when running policy tests:

1. Install OPA: https://www.openpolicyagent.org/docs/latest/#running-opa
2. Verify installation: `opa version`

### Docker Not Available

If integration tests fail with Docker errors:

1. Ensure Docker is installed and running
2. Verify Docker socket is accessible: `docker ps`
3. Run tests without integration: `pytest -m "not integration"`

### Async Test Warnings

If you see warnings about event loops:

1. Ensure `pytest-asyncio` is installed
2. Check `pytest.ini` has `asyncio_mode = auto`
3. Use `@pytest.mark.asyncio` on async tests

---

## Summary

The AgentWeave SDK provides comprehensive testing utilities:

- **Mock Providers**: Test without infrastructure
- **Fixtures**: Reusable test components
- **TestCluster**: Integration testing with real services
- **PolicySimulator**: Test OPA policies locally

Use these tools to build robust, well-tested secure agents!

For more information, see:
- [SDK Specification](spec.md)
- [Example Tests](tests/)
- [API Documentation](docs/)
