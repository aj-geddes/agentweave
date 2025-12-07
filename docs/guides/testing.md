---
layout: page
title: Testing Your Agents
description: Unit testing, integration testing, and CI/CD for AgentWeave agents
parent: How-To Guides
nav_order: 3
---

# Testing Your Agents

This guide shows you how to test AgentWeave agents using mocks, fixtures, and integration tests.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

AgentWeave provides comprehensive testing utilities to make testing easy:

- **Mock Providers** - Test without SPIRE or OPA
- **Pytest Fixtures** - Reusable test components
- **Test Utilities** - Helper functions for common testing tasks
- **Integration Test Support** - Test real agent interactions

---

## Unit Testing Capabilities

Test your agent capabilities in isolation without external dependencies.

### Basic Capability Test

```python
import pytest
from agentweave import SecureAgent, capability
from agentweave.testing import MockIdentityProvider, MockAuthorizationProvider

class SearchAgent(SecureAgent):
    @capability("search")
    async def search(self, query: str, limit: int = 10) -> dict:
        # Your actual search logic
        results = await self._perform_search(query, limit)
        return {"results": results, "count": len(results)}

    async def _perform_search(self, query: str, limit: int) -> list:
        # Simulate search
        return [{"id": i, "title": f"Result {i}"} for i in range(limit)]


@pytest.mark.asyncio
async def test_search_capability():
    # Create mock providers
    identity = MockIdentityProvider(
        spiffe_id="spiffe://test.local/agent/search"
    )
    authz = MockAuthorizationProvider(default_allow=True)

    # Initialize agent with mocks
    agent = SearchAgent()
    agent.identity_provider = identity
    agent.authz_provider = authz

    # Test capability
    result = await agent.search(query="test", limit=5)

    assert result["count"] == 5
    assert len(result["results"]) == 5
    assert result["results"][0]["title"] == "Result 0"
```

### Test with Authorization Checks

```python
@pytest.mark.asyncio
async def test_search_authorization():
    # Setup mock authorization with specific rules
    authz = MockAuthorizationProvider(default_allow=False)
    authz.add_rule(
        caller_id="spiffe://test.local/agent/orchestrator",
        callee_id="spiffe://test.local/agent/search",
        action="search",
        allowed=True
    )

    # Test that allowed caller succeeds
    decision = await authz.check_outbound(
        caller_id="spiffe://test.local/agent/orchestrator",
        callee_id="spiffe://test.local/agent/search",
        action="search"
    )
    assert decision.allowed == True

    # Test that unauthorized caller is denied
    decision = await authz.check_outbound(
        caller_id="spiffe://test.local/agent/unknown",
        callee_id="spiffe://test.local/agent/search",
        action="search"
    )
    assert decision.allowed == False
```

---

## Using MockIdentityProvider

The `MockIdentityProvider` simulates SPIFFE identity without requiring SPIRE.

### Basic Usage

```python
from agentweave.testing import MockIdentityProvider

# Create provider with custom SPIFFE ID
identity = MockIdentityProvider(
    spiffe_id="spiffe://test.local/agent/test-agent",
    trust_domain="test.local",
    rotation_interval=3600,  # Rotate every hour
    auto_rotate=False
)

# Get SVID
svid = await identity.get_svid()
assert svid.spiffe_id == "spiffe://test.local/agent/test-agent"
assert not svid.is_expired()

# Get trust bundle
bundle = await identity.get_trust_bundle("test.local")
assert bundle.trust_domain == "test.local"
```

### Testing SVID Rotation

```python
@pytest.mark.asyncio
async def test_svid_rotation():
    identity = MockIdentityProvider(
        spiffe_id="spiffe://test.local/agent/test",
        rotation_interval=1,  # Rotate every 1 second for testing
        auto_rotate=False
    )

    # Get initial SVID
    svid1 = await identity.get_svid()
    initial_expiry = svid1.expiry

    # Wait for expiration
    await asyncio.sleep(2)

    # Manually rotate
    svid2 = await identity.rotate_svid()

    # Verify new SVID
    assert svid2.expiry > initial_expiry
    assert svid2.spiffe_id == svid1.spiffe_id
```

### Testing Trust Bundles

```python
@pytest.mark.asyncio
async def test_cross_domain_trust():
    identity = MockIdentityProvider(
        spiffe_id="spiffe://yourdomain.com/agent/test"
    )

    # Get trust bundle for our domain
    local_bundle = await identity.get_trust_bundle("yourdomain.com")
    assert local_bundle.trust_domain == "yourdomain.com"

    # Get trust bundle for federated domain
    partner_bundle = await identity.get_trust_bundle("partner.example.com")
    assert partner_bundle.trust_domain == "partner.example.com"
```

---

## Using MockAuthorizationProvider

The `MockAuthorizationProvider` simulates OPA policy evaluation.

### Default Deny Configuration

```python
from agentweave.testing import MockAuthorizationProvider

# Default deny (production-like)
authz = MockAuthorizationProvider(default_allow=False)

# Add specific allow rules
authz.add_rule(
    caller_id="spiffe://test.local/agent/caller",
    callee_id="spiffe://test.local/agent/callee",
    action="search",
    allowed=True
)

# Test allowed case
decision = await authz.check_outbound(
    caller_id="spiffe://test.local/agent/caller",
    callee_id="spiffe://test.local/agent/callee",
    action="search"
)
assert decision.allowed == True

# Test denied case
decision = await authz.check_outbound(
    caller_id="spiffe://test.local/agent/other",
    callee_id="spiffe://test.local/agent/callee",
    action="search"
)
assert decision.allowed == False
```

### Recording Authorization Checks

```python
@pytest.mark.asyncio
async def test_authorization_audit():
    authz = MockAuthorizationProvider(default_allow=True)

    # Make several checks
    await authz.check_inbound(
        caller_id="spiffe://test.local/agent/caller1",
        action="search"
    )
    await authz.check_inbound(
        caller_id="spiffe://test.local/agent/caller2",
        action="process"
    )

    # Verify all checks were recorded
    checks = authz.get_checks()
    assert len(checks) == 2
    assert checks[0].caller_id == "spiffe://test.local/agent/caller1"
    assert checks[0].action == "search"
    assert checks[1].caller_id == "spiffe://test.local/agent/caller2"
    assert checks[1].action == "process"

    # Clear for next test
    authz.clear_checks()
    assert len(authz.get_checks()) == 0
```

### Complex Policy Rules

```python
@pytest.mark.asyncio
async def test_complex_authz_rules():
    authz = MockAuthorizationProvider(default_allow=False)

    # Orchestrator can call anyone
    authz.add_rule(
        caller_id="spiffe://test.local/agent/orchestrator",
        callee_id="spiffe://test.local/agent/search",
        action="search",
        allowed=True
    )
    authz.add_rule(
        caller_id="spiffe://test.local/agent/orchestrator",
        callee_id="spiffe://test.local/agent/processor",
        action="process",
        allowed=True
    )

    # Search can only call indexer
    authz.add_rule(
        caller_id="spiffe://test.local/agent/search",
        callee_id="spiffe://test.local/agent/indexer",
        action="query",
        allowed=True
    )

    # Test orchestrator -> search (allowed)
    decision = await authz.check_outbound(
        caller_id="spiffe://test.local/agent/orchestrator",
        callee_id="spiffe://test.local/agent/search",
        action="search"
    )
    assert decision.allowed == True

    # Test search -> indexer (allowed)
    decision = await authz.check_outbound(
        caller_id="spiffe://test.local/agent/search",
        callee_id="spiffe://test.local/agent/indexer",
        action="query"
    )
    assert decision.allowed == True

    # Test search -> processor (denied - no rule)
    decision = await authz.check_outbound(
        caller_id="spiffe://test.local/agent/search",
        callee_id="spiffe://test.local/agent/processor",
        action="process"
    )
    assert decision.allowed == False
```

---

## Using TestA2AClient

Test agent-to-agent communication without real network calls.

### Basic A2A Testing

```python
from agentweave.comms.a2a import A2AClient
from agentweave.testing import MockTransport

@pytest.mark.asyncio
async def test_a2a_communication():
    # Create mock transport
    transport = MockTransport()

    # Add expected response
    transport.add_response(
        url="https://search-agent.example.com/task",
        status_code=200,
        body=b'{"status": "completed", "result": {"results": [1, 2, 3]}}'
    )

    # Create A2A client with mock transport
    client = A2AClient(transport=transport)

    # Make request
    response = await client.post(
        "https://search-agent.example.com/task",
        data=b'{"action": "search", "query": "test"}'
    )

    assert response.status_code == 200

    # Verify request was made
    requests = transport.get_requests()
    assert len(requests) == 1
    assert requests[0].url == "https://search-agent.example.com/task"
```

### Testing Error Conditions

```python
@pytest.mark.asyncio
async def test_a2a_timeout():
    transport = MockTransport()
    transport.set_failure_mode("timeout")

    client = A2AClient(transport=transport)

    with pytest.raises(asyncio.TimeoutError):
        await client.post(
            "https://agent.example.com/task",
            data=b'{"action": "test"}',
            timeout=5.0
        )

@pytest.mark.asyncio
async def test_a2a_connection_failure():
    transport = MockTransport()
    transport.set_failure_mode("connection")

    client = A2AClient(transport=transport)

    with pytest.raises(ConnectionError):
        await client.post(
            "https://agent.example.com/task",
            data=b'{"action": "test"}'
        )
```

---

## Integration Testing

Test real agents communicating with each other.

### Multi-Agent Integration Test

```python
import pytest
from agentweave import SecureAgent, capability
from agentweave.testing import MockIdentityProvider, MockAuthorizationProvider

class OrchestratorAgent(SecureAgent):
    @capability("orchestrate")
    async def orchestrate(self, task: str) -> dict:
        # Call search agent
        search_result = await self.call_agent(
            "spiffe://test.local/agent/search",
            "search",
            {"query": task}
        )
        return {"status": "completed", "search": search_result}


class SearchAgent(SecureAgent):
    @capability("search")
    async def search(self, query: str) -> dict:
        return {"results": [f"Result for: {query}"]}


@pytest.mark.asyncio
async def test_multi_agent_orchestration():
    # Setup authorization rules
    authz = MockAuthorizationProvider(default_allow=False)
    authz.add_rule(
        caller_id="spiffe://test.local/agent/orchestrator",
        callee_id="spiffe://test.local/agent/search",
        action="search",
        allowed=True
    )

    # Create orchestrator
    orchestrator = OrchestratorAgent()
    orchestrator.identity_provider = MockIdentityProvider(
        spiffe_id="spiffe://test.local/agent/orchestrator"
    )
    orchestrator.authz_provider = authz

    # Create search agent
    search_agent = SearchAgent()
    search_agent.identity_provider = MockIdentityProvider(
        spiffe_id="spiffe://test.local/agent/search"
    )
    search_agent.authz_provider = authz

    # Start both agents
    await orchestrator.start()
    await search_agent.start()

    try:
        # Test orchestration
        result = await orchestrator.orchestrate(task="test query")

        assert result["status"] == "completed"
        assert "search" in result
        assert len(result["search"]["results"]) > 0
    finally:
        await orchestrator.stop()
        await search_agent.stop()
```

---

## Testing Policies with OPA

Test your Rego policies directly with OPA.

### Policy Unit Tests

Create `policy_test.rego`:

```rego
package agentweave.authz

import rego.v1

# Test same trust domain allows
test_same_trust_domain_allows if {
    allow with input as {
        "caller_spiffe_id": "spiffe://test.local/agent/caller",
        "resource_spiffe_id": "spiffe://test.local/agent/callee",
        "action": "search",
        "caller_trust_domain": "test.local",
        "resource_trust_domain": "test.local"
    }
}

# Test different trust domain denies
test_different_trust_domain_denies if {
    not allow with input as {
        "caller_spiffe_id": "spiffe://test.local/agent/caller",
        "resource_spiffe_id": "spiffe://other.local/agent/callee",
        "action": "search",
        "caller_trust_domain": "test.local",
        "resource_trust_domain": "other.local"
    }
}

# Test orchestrator can call workers
test_orchestrator_can_call_workers if {
    allow with input as {
        "caller_spiffe_id": "spiffe://test.local/agent/orchestrator",
        "resource_spiffe_id": "spiffe://test.local/agent/worker",
        "action": "process",
        "caller_trust_domain": "test.local",
        "resource_trust_domain": "test.local"
    }
}
```

Run tests:

```bash
# Run OPA tests
opa test policy.rego policy_test.rego

# With verbose output
opa test -v policy.rego policy_test.rego

# With coverage
opa test --coverage policy.rego policy_test.rego
```

### Integration Testing with OPA

```python
import pytest
from agentweave.authz import OPAAuthzProvider

@pytest.mark.integration
@pytest.mark.asyncio
async def test_opa_policy_integration():
    """
    This test requires OPA running with your policy loaded.

    Start OPA with:
    opa run --server --addr localhost:8181 policy.rego
    """
    authz = OPAAuthzProvider(
        opa_endpoint="http://localhost:8181",
        policy_path="agentweave/authz"
    )

    # Test allowed case
    decision = await authz.check_outbound(
        caller_id="spiffe://test.local/agent/orchestrator",
        callee_id="spiffe://test.local/agent/search",
        action="search",
        context={"request_id": "test-123"}
    )

    assert decision.allowed == True
    assert decision.reason != ""

    # Test denied case
    decision = await authz.check_outbound(
        caller_id="spiffe://test.local/agent/unknown",
        callee_id="spiffe://test.local/agent/search",
        action="admin",
        context={"request_id": "test-124"}
    )

    assert decision.allowed == False
```

---

## Pytest Fixtures Provided by AgentWeave

AgentWeave includes reusable pytest fixtures.

### Available Fixtures

```python
# In your conftest.py
from agentweave.testing.fixtures import *

# Now available in all tests:
# - mock_identity_provider
# - mock_authz_provider
# - mock_authz_provider_permissive
# - mock_transport
# - test_config
# - test_config_dev
# - spiffe_ids
# - sample_tasks
```

### Using Fixtures in Tests

```python
def test_agent_with_fixtures(
    mock_identity_provider,
    mock_authz_provider,
    test_config
):
    """Test using provided fixtures."""
    agent = SearchAgent()
    agent.identity_provider = mock_identity_provider
    agent.authz_provider = mock_authz_provider

    # Identity is already configured
    assert agent.identity_provider.spiffe_id == "spiffe://test.local/agent/test"

    # Authorization is default deny
    assert agent.authz_provider.default_allow == False


def test_multiple_agents(spiffe_ids, mock_authz_provider):
    """Test with predefined SPIFFE IDs."""
    # spiffe_ids fixture provides common test identities
    orchestrator_id = spiffe_ids["orchestrator"]
    search_id = spiffe_ids["search"]

    # Setup authorization
    mock_authz_provider.add_rule(
        caller_id=orchestrator_id,
        callee_id=search_id,
        action="search",
        allowed=True
    )

    # Test...
```

---

## Example Test File

Complete example `test_search_agent.py`:

```python
import pytest
from agentweave import SecureAgent, capability
from agentweave.testing import (
    MockIdentityProvider,
    MockAuthorizationProvider,
    MockTransport
)
from agentweave.exceptions import AuthorizationError


class SearchAgent(SecureAgent):
    @capability("search")
    async def search(self, query: str, limit: int = 10) -> dict:
        results = await self._perform_search(query, limit)
        return {"query": query, "results": results, "count": len(results)}

    async def _perform_search(self, query: str, limit: int) -> list:
        # Mock search implementation
        return [{"id": i, "title": f"Result {i}"} for i in range(limit)]


class TestSearchAgent:
    """Test suite for SearchAgent."""

    @pytest.fixture
    def search_agent(self):
        """Create SearchAgent with mock providers."""
        agent = SearchAgent()
        agent.identity_provider = MockIdentityProvider(
            spiffe_id="spiffe://test.local/agent/search"
        )
        agent.authz_provider = MockAuthorizationProvider(default_allow=True)
        return agent

    @pytest.mark.asyncio
    async def test_search_returns_results(self, search_agent):
        """Test that search returns expected results."""
        result = await search_agent.search(query="test", limit=5)

        assert result["query"] == "test"
        assert result["count"] == 5
        assert len(result["results"]) == 5

    @pytest.mark.asyncio
    async def test_search_respects_limit(self, search_agent):
        """Test that limit parameter works."""
        result = await search_agent.search(query="test", limit=3)
        assert result["count"] == 3

        result = await search_agent.search(query="test", limit=10)
        assert result["count"] == 10

    @pytest.mark.asyncio
    async def test_search_with_authorization_check(self):
        """Test authorization is checked."""
        agent = SearchAgent()
        agent.identity_provider = MockIdentityProvider(
            spiffe_id="spiffe://test.local/agent/search"
        )

        # Setup strict authorization
        authz = MockAuthorizationProvider(default_allow=False)
        authz.add_rule(
            caller_id="spiffe://test.local/agent/allowed",
            callee_id=None,
            action="search",
            allowed=True
        )
        agent.authz_provider = authz

        # This would be called by the framework during request handling
        # Testing the authorization provider directly
        decision = await authz.check_inbound(
            caller_id="spiffe://test.local/agent/allowed",
            action="search"
        )
        assert decision.allowed == True

        decision = await authz.check_inbound(
            caller_id="spiffe://test.local/agent/denied",
            action="search"
        )
        assert decision.allowed == False

    @pytest.mark.asyncio
    async def test_search_records_authz_checks(self, search_agent):
        """Test that authorization checks are recorded."""
        authz = search_agent.authz_provider

        await authz.check_inbound(
            caller_id="spiffe://test.local/agent/caller",
            action="search"
        )

        checks = authz.get_checks()
        assert len(checks) == 1
        assert checks[0].action == "search"
        assert checks[0].allowed == True  # default_allow=True
```

Run tests:

```bash
# Run all tests
pytest test_search_agent.py

# Run with coverage
pytest --cov=search_agent test_search_agent.py

# Run only async tests
pytest -m asyncio test_search_agent.py

# Verbose output
pytest -v test_search_agent.py
```

---

## CI/CD Integration Tips

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Test AgentWeave Agents

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio pytest-cov

      - name: Run unit tests
        run: |
          pytest tests/ -v --cov=agentweave --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml

  integration-test:
    runs-on: ubuntu-latest
    needs: test

    services:
      opa:
        image: openpolicyagent/opa:latest
        ports:
          - 8181:8181
        options: >-
          --health-cmd "wget --spider http://localhost:8181/health"
          --health-interval 10s

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -e .
          pip install pytest pytest-asyncio

      - name: Load OPA policies
        run: |
          curl -X PUT --data-binary @agentweave/authz/policies/default.rego \
            http://localhost:8181/v1/policies/default

      - name: Run integration tests
        run: |
          pytest tests/ -v --run-integration
```

### pytest Configuration

```ini
# pytest.ini
[pytest]
asyncio_mode = auto
markers =
    asyncio: mark test as async
    integration: mark test as integration test (requires external services)
    slow: mark test as slow running

testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Coverage settings
addopts =
    --cov=agentweave
    --cov-report=html
    --cov-report=term-missing
    --cov-fail-under=80
```

### Makefile for Testing

```makefile
# Makefile
.PHONY: test test-unit test-integration test-coverage lint

test: test-unit test-integration

test-unit:
	pytest tests/ -v -m "not integration"

test-integration:
	pytest tests/ -v -m integration

test-coverage:
	pytest tests/ --cov=agentweave --cov-report=html --cov-report=term

lint:
	ruff check agentweave/
	mypy agentweave/

ci: lint test-unit
	@echo "CI checks passed!"
```

---

## Best Practices

1. **Use mocks for unit tests** - Test capabilities in isolation
2. **Use real OPA for integration tests** - Validate policies work correctly
3. **Test both allow and deny cases** - Ensure authorization works both ways
4. **Record authorization checks** - Verify the right checks are made
5. **Test error handling** - Ensure errors are handled gracefully
6. **Use fixtures** - Reduce boilerplate in tests
7. **Run tests in CI/CD** - Catch issues before production
8. **Measure coverage** - Aim for >80% test coverage

---

## Related Guides

- [Error Handling](error-handling.md) - Test error conditions
- [Common Authorization Patterns](policy-patterns.md) - Policies to test
- [Production Checklist](production-checklist.md) - Testing before deployment

---

## External Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://github.com/pytest-dev/pytest-asyncio)
- [OPA Policy Testing](https://www.openpolicyagent.org/docs/latest/policy-testing/)
- [Python Testing Best Practices](https://realpython.com/python-testing/)
