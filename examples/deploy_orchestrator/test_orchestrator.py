"""
Tests for CI/CD Deployment Orchestrator.

Demonstrates testing deployment state machines, production safety gates,
and rollback behavior using AgentWeave mock providers.
"""

import sys
from pathlib import Path

import pytest

# Ensure the example directory is on the import path so `orchestrator` resolves.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentweave.agent import AgentConfig  # noqa: E402
from agentweave.context import RequestContext, set_current_context  # noqa: E402
from agentweave.testing import MockIdentityProvider, MockAuthorizationProvider  # noqa: E402

from orchestrator import DeployOrchestrator, EnvironmentAgent, DeployState  # noqa: E402


@pytest.fixture
def orchestrator_config():
    return AgentConfig(
        name="test-orchestrator",
        trust_domain="devops.example",
        identity_provider="mtls-static",
        authz_provider="allow-all",
    )


@pytest.fixture
def env_config():
    return AgentConfig(
        name="test-env-staging",
        trust_domain="devops.example",
        identity_provider="mtls-static",
        authz_provider="allow-all",
    )


@pytest.fixture
async def orchestrator(orchestrator_config):
    identity = MockIdentityProvider(
        spiffe_id="spiffe://devops.example/agent/orchestrator",
        trust_domain="devops.example",
    )
    authz = MockAuthorizationProvider(default_allow=True)
    agent = DeployOrchestrator(
        config=orchestrator_config,
        identity=identity,
        authz=authz,
    )
    await agent.register_capabilities()
    return agent


@pytest.fixture
async def staging_agent(env_config):
    identity = MockIdentityProvider(
        spiffe_id="spiffe://devops.example/agent/env-staging",
        trust_domain="devops.example",
    )
    authz = MockAuthorizationProvider(default_allow=True)
    agent = EnvironmentAgent(
        config=env_config,
        env_name="staging",
        identity=identity,
        authz=authz,
    )
    await agent.register_capabilities()
    return agent


# --- Orchestrator Tests ---

class TestDeployOrchestrator:
    @pytest.mark.asyncio
    async def test_staging_deployment_succeeds(self, orchestrator):
        """Deploying to staging should succeed without prerequisites."""
        result = await orchestrator.deploy(
            service="web-app", version="2.0.0", environment="staging"
        )
        assert result["state"] == "complete"
        assert result["service"] == "web-app"
        assert result["version"] == "2.0.0"
        assert result["environment"] == "staging"
        assert "deploy_id" in result

    @pytest.mark.asyncio
    async def test_production_blocked_without_staging(self, orchestrator):
        """Production deployment should fail if staging hasn't succeeded."""
        result = await orchestrator.deploy(
            service="web-app", version="2.0.0", environment="production"
        )
        assert "error" in result
        assert "not been successfully deployed to staging" in result["reason"]

    @pytest.mark.asyncio
    async def test_production_succeeds_after_staging(self, orchestrator):
        """Production should succeed after the same version passes staging."""
        # First deploy to staging
        staging_result = await orchestrator.deploy(
            service="web-app", version="2.0.0", environment="staging"
        )
        assert staging_result["state"] == "complete"

        # Now deploy to production
        prod_result = await orchestrator.deploy(
            service="web-app", version="2.0.0", environment="production"
        )
        assert prod_result["state"] == "complete"
        assert prod_result["environment"] == "production"

    @pytest.mark.asyncio
    async def test_production_blocked_version_mismatch(self, orchestrator):
        """Production should fail if a different version was staged."""
        # Stage v1.0.0
        await orchestrator.deploy(
            service="web-app", version="1.0.0", environment="staging"
        )

        # Try to deploy v2.0.0 to production
        result = await orchestrator.deploy(
            service="web-app", version="2.0.0", environment="production"
        )
        assert "error" in result
        assert "1.0.0" in result["reason"]  # mentions staged version

    @pytest.mark.asyncio
    async def test_rollback_on_failure(self, orchestrator):
        """deploy_with_rollback should rollback when verification fails."""
        result = await orchestrator.deploy_with_rollback(
            service="web-app", version="2.0.0", environment="staging",
            simulate_failure=True,
        )
        assert result["state"] == "rolled_back"
        assert "verification failed" in result["reason"].lower()
        # Should have steps showing the rollback progression
        states = [s["state"] for s in result["steps"]]
        assert "deploying" in states
        assert "verifying" in states
        assert "rolling_back" in states
        assert "rolled_back" in states

    @pytest.mark.asyncio
    async def test_deployment_state_tracking(self, orchestrator):
        """Deployment should track all state transitions."""
        result = await orchestrator.deploy(
            service="api", version="3.0.0", environment="staging"
        )
        states = [s["state"] for s in result["steps"]]
        assert states == ["deploying", "verifying", "complete"]

    @pytest.mark.asyncio
    async def test_list_deployments(self, orchestrator):
        """List deployments, optionally filtered by environment."""
        await orchestrator.deploy(service="a", version="1.0", environment="staging")
        await orchestrator.deploy(service="b", version="1.0", environment="staging")

        all_deps = await orchestrator.list_deployments()
        assert all_deps["count"] == 2

        staging = await orchestrator.list_deployments(environment="staging")
        assert staging["count"] == 2

        prod = await orchestrator.list_deployments(environment="production")
        assert prod["count"] == 0

    @pytest.mark.asyncio
    async def test_get_deployment_not_found(self, orchestrator):
        """Getting a non-existent deployment returns error."""
        result = await orchestrator.get_deployment(deploy_id="nonexistent")
        assert "error" in result


# --- Environment Agent Tests ---

class TestEnvironmentAgent:
    @pytest.mark.asyncio
    async def test_health_check(self, staging_agent):
        """Health check returns environment status."""
        result = await staging_agent.health_check()
        assert result["environment"] == "staging"
        assert result["healthy"] is True
        assert result["current_version"] is None

    @pytest.mark.asyncio
    async def test_apply_deployment(self, staging_agent):
        """Apply deployment updates the current version."""
        ctx = RequestContext.create(
            caller_id="spiffe://devops.example/agent/orchestrator",
            metadata={"task_type": "apply_deployment"},
        )
        set_current_context(ctx)
        try:
            result = await staging_agent.apply_deployment(
                service="web-app", version="2.0.0"
            )
            assert result["status"] == "deployed"
            assert result["version"] == "2.0.0"
            assert result["previous_version"] is None

            # Second deployment should track previous version
            result2 = await staging_agent.apply_deployment(
                service="web-app", version="3.0.0"
            )
            assert result2["version"] == "3.0.0"
            assert result2["previous_version"] == "2.0.0"
        finally:
            set_current_context(None)

    @pytest.mark.asyncio
    async def test_verify_deployment(self, staging_agent):
        """Verify deployment checks version match and health."""
        ctx = RequestContext.create(
            caller_id="spiffe://devops.example/agent/orchestrator",
            metadata={"task_type": "verify_deployment"},
        )
        set_current_context(ctx)
        try:
            await staging_agent.apply_deployment(service="web-app", version="2.0.0")

            # Correct version
            result = await staging_agent.verify_deployment(
                service="web-app", version="2.0.0"
            )
            assert result["healthy"] is True
            assert result["version_match"] is True

            # Wrong version
            result2 = await staging_agent.verify_deployment(
                service="web-app", version="1.0.0"
            )
            assert result2["healthy"] is False
            assert result2["version_match"] is False
        finally:
            set_current_context(None)

    @pytest.mark.asyncio
    async def test_rollback(self, staging_agent):
        """Rollback restores the previous version."""
        ctx = RequestContext.create(
            caller_id="spiffe://devops.example/agent/orchestrator",
            metadata={"task_type": "rollback"},
        )
        set_current_context(ctx)
        try:
            await staging_agent.apply_deployment(service="web-app", version="1.0.0")
            await staging_agent.apply_deployment(service="web-app", version="2.0.0")

            result = await staging_agent.rollback(
                service="web-app", reason="verification failed"
            )
            assert result["status"] == "rolled_back"
            assert result["rolled_back_from"] == "2.0.0"
            assert result["current_version"] == "1.0.0"
        finally:
            set_current_context(None)

    @pytest.mark.asyncio
    async def test_deploy_history(self, staging_agent):
        """Deploy history tracks all operations."""
        ctx = RequestContext.create(
            caller_id="spiffe://devops.example/agent/orchestrator",
            metadata={"task_type": "apply_deployment"},
        )
        set_current_context(ctx)
        try:
            await staging_agent.apply_deployment(service="web-app", version="1.0.0")
            await staging_agent.apply_deployment(service="web-app", version="2.0.0")
            await staging_agent.rollback(service="web-app", reason="bad deploy")

            result = await staging_agent.get_deploy_history()
            assert len(result["history"]) == 3
            assert result["history"][0]["action"] == "deploy"
            assert result["history"][2]["action"] == "rollback"
        finally:
            set_current_context(None)
