# HVS Agent SDK - Quick Start Testing Guide

## Installation

```bash
# Install test dependencies
pip install -r requirements-test.txt
```

## Running Tests

```bash
# Run all unit tests
pytest

# Run specific test file
pytest tests/test_identity.py

# Run with coverage
pytest --cov=agentweave --cov-report=html

# Run integration tests (requires Docker)
pytest --run-integration
```

## Basic Usage

### 1. Test with Mock Identity

```python
import pytest
from agentweave.testing import MockIdentityProvider

@pytest.mark.asyncio
async def test_identity():
    provider = MockIdentityProvider(
        spiffe_id="spiffe://test.local/agent/my-agent"
    )
    
    # Get SVID
    svid = await provider.get_svid()
    assert svid.spiffe_id == "spiffe://test.local/agent/my-agent"
    
    # Get trust bundle
    bundle = await provider.get_trust_bundle("test.local")
    assert bundle is not None
```

### 2. Test with Mock Authorization

```python
import pytest
from agentweave.testing import MockAuthorizationProvider

@pytest.mark.asyncio
async def test_authz():
    authz = MockAuthorizationProvider(default_allow=False)
    
    # Add allow rule
    authz.add_rule(
        caller_id="spiffe://test.local/agent/caller",
        callee_id="spiffe://test.local/agent/target",
        action="search",
        allowed=True,
    )
    
    # Check authorization
    decision = await authz.check_outbound(
        caller_id="spiffe://test.local/agent/caller",
        callee_id="spiffe://test.local/agent/target",
        action="search",
    )
    assert decision.allowed == True
```

### 3. Test with Fixtures

```python
import pytest

@pytest.mark.asyncio
async def test_with_fixtures(test_agent, mock_authz_provider):
    # Fixtures are automatically injected
    result = await test_agent.call_capability("test_capability", {})
    assert result["status"] == "completed"
```

### 4. Test OPA Policies

```python
from agentweave.testing import PolicySimulator

def test_policy():
    simulator = PolicySimulator("policies/authz.rego")
    
    # Test allow
    simulator.assert_allow(
        caller="spiffe://test.local/agent/orchestrator",
        callee="spiffe://test.local/agent/search",
        action="search"
    )
    
    # Test deny
    simulator.assert_deny(
        caller="spiffe://evil.com/agent/bad",
        callee="spiffe://test.local/agent/search",
        action="search"
    )
```

### 5. Integration Test

```python
import pytest
from agentweave.testing import TestCluster

@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_real_spire():
    async with TestCluster() as cluster:
        # Register agent
        await cluster.register_agent(
            spiffe_id="spiffe://test.local/agent/my-agent",
            selectors=["unix:uid:1000"]
        )
        
        # Test with real infrastructure
        # ...
```

## Available Fixtures

- `mock_identity_provider` - Mock SPIFFE identity
- `mock_authz_provider` - Mock OPA authorization (default deny)
- `mock_authz_provider_permissive` - Mock OPA (allow all)
- `mock_transport` - Mock HTTP transport
- `test_agent` - Fully configured test agent
- `test_config` - Valid test configuration
- `test_config_dev` - Development mode config
- `spiffe_ids` - Collection of test SPIFFE IDs
- `sample_tasks` - Sample A2A tasks

## Test Markers

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration --run-integration

# Skip slow tests
pytest -m "not slow"
```

## Common Patterns

### Testing SVID Rotation

```python
@pytest.mark.asyncio
async def test_rotation():
    provider = MockIdentityProvider(
        spiffe_id="spiffe://test.local/agent/test"
    )
    
    svid1 = await provider.get_svid()
    svid2 = await provider.rotate_svid()
    
    assert svid2.cert_chain != svid1.cert_chain
```

### Testing Authorization Rules

```python
@pytest.mark.asyncio
async def test_authz_rules():
    authz = MockAuthorizationProvider(default_allow=False)
    
    # Add rule
    authz.add_rule("spiffe://test.local/agent/a",
                   "spiffe://test.local/agent/b",
                   "action", True)
    
    # Verify
    decision = await authz.check_outbound(
        "spiffe://test.local/agent/a",
        "spiffe://test.local/agent/b",
        "action"
    )
    assert decision.allowed == True
```

### Testing Network Failures

```python
@pytest.mark.asyncio
async def test_timeout():
    transport = MockTransport()
    transport.set_failure_mode("timeout")
    
    # Will timeout
    with pytest.raises(asyncio.TimeoutError):
        await transport.get("https://example.com")
```

## Documentation

- Full guide: See TESTING.md
- Specification: See spec.md
- Examples: See tests/ directory

## Need Help?

- Check TESTING.md for detailed documentation
- Review test_*.py files for examples
- See spec.md for architecture details
