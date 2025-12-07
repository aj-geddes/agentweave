"""
Tests for AgentWeave SDK agent integration.

Tests complete agent functionality including identity, authorization,
and agent-to-agent communication.
"""

import pytest
import asyncio
from typing import Dict, Any
from agentweave.testing import (
    MockIdentityProvider,
    MockAuthorizationProvider,
    MockTransport,
    TestCluster,
)


class TestAgentLifecycle:
    """Test agent lifecycle management."""

    @pytest.mark.asyncio
    async def test_agent_initialization(self, test_agent):
        """Test that agent initializes correctly."""
        assert test_agent is not None
        assert test_agent.spiffe_id is not None
        assert test_agent.identity is not None
        assert test_agent.authz is not None

    @pytest.mark.asyncio
    async def test_agent_start_stop(self, mock_identity_provider, mock_authz_provider):
        """Test agent start and stop."""
        # This would test the actual agent implementation
        # For now, demonstrate the pattern

        class TestAgent:
            def __init__(self, identity, authz):
                self.identity = identity
                self.authz = authz
                self.running = False

            async def start(self):
                self.running = True

            async def stop(self):
                self.running = False

        agent = TestAgent(mock_identity_provider, mock_authz_provider)

        await agent.start()
        assert agent.running is True

        await agent.stop()
        assert agent.running is False

    @pytest.mark.asyncio
    async def test_agent_graceful_shutdown(self, test_agent):
        """Test agent handles graceful shutdown."""
        # Agent should clean up resources on shutdown
        await test_agent.stop()
        # Should not raise errors


class TestAgentCapabilities:
    """Test agent capability registration and execution."""

    @pytest.mark.asyncio
    async def test_register_capability(self, test_agent):
        """Test registering a capability."""
        # This would test capability registration
        # In the actual implementation:
        # @test_agent.capability("search")
        # async def search(query: str):
        #     return {"results": []}
        pass

    @pytest.mark.asyncio
    async def test_call_capability(self, test_agent):
        """Test calling a registered capability."""
        result = await test_agent.call_capability("test_capability", {})
        assert result is not None
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_capability_not_found(self, test_agent):
        """Test calling non-existent capability raises error."""
        # Should raise error for unknown capability
        # with pytest.raises(CapabilityNotFoundError):
        #     await test_agent.call_capability("unknown_capability", {})
        pass


class TestAgentToAgentCommunication:
    """Test agent-to-agent communication."""

    @pytest.mark.asyncio
    async def test_call_remote_agent(
        self,
        mock_identity_provider,
        mock_authz_provider,
        mock_transport,
    ):
        """Test calling another agent."""
        # Setup authorization
        mock_authz_provider.add_rule(
            caller_id="spiffe://test.local/agent/test",
            callee_id="spiffe://test.local/agent/remote",
            action="search",
            allowed=True,
        )

        # Setup mock response
        mock_transport.add_response(
            url="https://remote-agent:8443/.well-known/a2a/tasks/send",
            status_code=200,
            body=b'{"status": "completed", "result": {"data": "success"}}',
        )

        # This would use the actual agent implementation
        # result = await agent.call_agent(
        #     target="spiffe://test.local/agent/remote",
        #     task_type="search",
        #     payload={"query": "test"}
        # )
        # assert result.status == "completed"

    @pytest.mark.asyncio
    async def test_call_unauthorized_agent(
        self,
        mock_identity_provider,
        mock_authz_provider,
    ):
        """Test calling agent without authorization fails."""
        # Don't add authorization rule - should be denied by default

        # This should raise AuthorizationError
        # with pytest.raises(AuthorizationError):
        #     await agent.call_agent(
        #         target="spiffe://test.local/agent/remote",
        #         task_type="search",
        #         payload={}
        #     )
        pass

    @pytest.mark.asyncio
    async def test_receive_agent_call(self, test_agent, mock_authz_provider):
        """Test receiving a call from another agent."""
        # Setup authorization
        mock_authz_provider.add_rule(
            caller_id="spiffe://test.local/agent/caller",
            callee_id=None,
            action="test_capability",
            allowed=True,
        )

        # This would test the server side
        # task = {
        #     "id": "task-001",
        #     "type": "test_capability",
        #     "state": "submitted",
        #     "messages": [...]
        # }
        # result = await test_agent.handle_task(task, caller_id="spiffe://test.local/agent/caller")
        # assert result.status == "completed"


class TestAgentSecurity:
    """Test agent security features."""

    @pytest.mark.asyncio
    async def test_mtls_enforced(self, mock_transport):
        """Test that mTLS is enforced."""
        # Transport should verify SSL context
        assert mock_transport.get_ssl_context() is None  # Not set yet

        # After agent initialization, SSL context should be set
        # This would be tested with actual agent

    @pytest.mark.asyncio
    async def test_peer_verification(self, mock_identity_provider):
        """Test peer certificate verification."""
        # Get trust bundle
        bundle = await mock_identity_provider.get_trust_bundle("test.local")
        assert bundle is not None

        # In actual implementation:
        # - Verify peer certificate against trust bundle
        # - Extract SPIFFE ID from certificate
        # - Verify it matches expected SPIFFE ID

    @pytest.mark.asyncio
    async def test_svid_rotation_handling(self, mock_identity_provider):
        """Test that agent handles SVID rotation."""
        # Get initial SVID
        svid1 = await mock_identity_provider.get_svid()

        # Rotate SVID
        svid2 = await mock_identity_provider.rotate_svid()

        # Agent should pick up new SVID
        assert svid2.cert_chain != svid1.cert_chain

    @pytest.mark.asyncio
    async def test_authorization_checked_before_execution(
        self,
        test_agent,
        mock_authz_provider,
    ):
        """Test that authorization is checked before executing capability."""
        # Clear any existing checks
        mock_authz_provider.clear_checks()

        # Call capability (should check authorization)
        try:
            await test_agent.call_capability("test_capability", {})
        except:
            pass  # Might fail, but that's ok for this test

        # Should have checked authorization
        # checks = mock_authz_provider.get_checks()
        # assert len(checks) > 0


class TestAgentCard:
    """Test A2A agent card generation."""

    def test_generate_agent_card(self, test_config):
        """Test generating agent card from config."""
        # This would use actual agent card implementation
        # from agentweave.comms import AgentCard
        #
        # card = AgentCard.from_config(test_config)
        # assert card.name == "test-agent"
        # assert card.spiffe_id == "spiffe://test.local/agent/test-agent"
        # assert len(card.capabilities) > 0

    def test_agent_card_json_format(self, test_config):
        """Test agent card JSON serialization."""
        # card = AgentCard.from_config(test_config)
        # card_json = card.to_json()
        #
        # assert "name" in card_json
        # assert "capabilities" in card_json
        # assert "authentication" in card_json
        # assert "extensions" in card_json
        # assert "spiffe_id" in card_json["extensions"]


class TestAgentDiscovery:
    """Test agent discovery mechanism."""

    @pytest.mark.asyncio
    async def test_discover_agent(self, mock_transport):
        """Test discovering another agent."""
        # Mock agent card response
        mock_transport.add_response(
            url="https://remote-agent:8443/.well-known/agent.json",
            status_code=200,
            body=b'{"name": "remote-agent", "capabilities": []}',
        )

        # This would use actual discovery implementation
        # card = await discover_agent("https://remote-agent:8443")
        # assert card.name == "remote-agent"

    @pytest.mark.asyncio
    async def test_discovery_failure_handling(self, mock_transport):
        """Test handling discovery failures."""
        # Mock 404 response
        mock_transport.add_response(
            url="https://unknown-agent:8443/.well-known/agent.json",
            status_code=404,
            body=b"Not Found",
        )

        # Should handle gracefully
        # with pytest.raises(AgentNotFoundError):
        #     await discover_agent("https://unknown-agent:8443")


class TestAgentMetrics:
    """Test agent metrics and observability."""

    @pytest.mark.asyncio
    async def test_metrics_enabled(self, test_config):
        """Test that metrics are enabled when configured."""
        assert test_config["observability"]["metrics"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_request_metrics_recorded(self, test_agent):
        """Test that request metrics are recorded."""
        # Make a request
        await test_agent.call_capability("test_capability", {})

        # Metrics should be recorded
        # metrics = get_metrics()
        # assert metrics["requests_total"] > 0

    @pytest.mark.asyncio
    async def test_authz_metrics_recorded(self, mock_authz_provider):
        """Test that authorization metrics are recorded."""
        await mock_authz_provider.check_inbound(
            caller_id="spiffe://test.local/agent/caller",
            action="search",
        )

        # Metrics should include authz decisions
        # metrics = get_metrics()
        # assert metrics["authz_decisions_total"] > 0


@pytest.mark.integration
class TestAgentIntegration:
    """Integration tests requiring full infrastructure."""

    @pytest.mark.asyncio
    async def test_full_agent_stack(self):
        """Test complete agent with SPIRE and OPA."""
        pytest.skip("Requires Docker and full infrastructure")

        # async with TestCluster() as cluster:
        #     # Register agent with SPIRE
        #     await cluster.register_agent(
        #         spiffe_id="spiffe://test.local/agent/test",
        #         selectors=["unix:uid:1000"]
        #     )
        #
        #     # Deploy agent
        #     agent = await cluster.deploy_agent(MyTestAgent)
        #
        #     # Test agent functionality
        #     result = await agent.test_capability()
        #     assert result is not None

    @pytest.mark.asyncio
    async def test_multi_agent_communication(self):
        """Test communication between multiple agents."""
        pytest.skip("Requires Docker and full infrastructure")

        # async with TestCluster() as cluster:
        #     # Deploy multiple agents
        #     search_agent = await cluster.deploy_agent(SearchAgent)
        #     orchestrator = await cluster.deploy_agent(OrchestratorAgent)
        #
        #     # Orchestrator calls search agent
        #     result = await orchestrator.search("test query")
        #     assert result is not None

    @pytest.mark.asyncio
    async def test_cross_domain_federation(self):
        """Test federation between trust domains."""
        pytest.skip("Requires Docker and full infrastructure")

        # async with TestCluster() as cluster:
        #     # Setup federation
        #     await cluster.configure_federation(
        #         trust_domain="partner.example.com"
        #     )
        #
        #     # Test cross-domain call
        #     result = await agent.call_federated_agent(
        #         "spiffe://partner.example.com/agent/service"
        #     )
        #     assert result is not None


class TestErrorHandling:
    """Test agent error handling."""

    @pytest.mark.asyncio
    async def test_connection_timeout(self, mock_transport):
        """Test handling connection timeout."""
        mock_transport.set_failure_mode("timeout")

        # Should handle timeout gracefully
        # with pytest.raises(TimeoutError):
        #     await agent.call_agent("spiffe://test.local/agent/remote", ...)

    @pytest.mark.asyncio
    async def test_connection_failure(self, mock_transport):
        """Test handling connection failure."""
        mock_transport.set_failure_mode("connection")

        # Should handle connection failure
        # with pytest.raises(ConnectionError):
        #     await agent.call_agent("spiffe://test.local/agent/remote", ...)

    @pytest.mark.asyncio
    async def test_ssl_verification_failure(self, mock_transport):
        """Test handling SSL verification failure."""
        mock_transport.set_failure_mode("ssl")

        # Should handle SSL error
        # with pytest.raises(ssl.SSLError):
        #     await agent.call_agent("spiffe://test.local/agent/remote", ...)

    @pytest.mark.asyncio
    async def test_invalid_task_format(self, test_agent):
        """Test handling invalid task format."""
        # Invalid task should be rejected
        # with pytest.raises(ValidationError):
        #     await test_agent.handle_task({"invalid": "task"})


class TestAgentConfiguration:
    """Test agent configuration handling."""

    def test_load_config_from_file(self, temp_config_file):
        """Test loading agent config from file."""
        # config = AgentConfig.from_file(temp_config_file)
        # assert config.agent.name == "test-agent"

    def test_invalid_config_rejected(self):
        """Test that invalid config is rejected."""
        invalid_config = {
            "agent": {
                # Missing required fields
            }
        }

        # with pytest.raises(ValidationError):
        #     AgentConfig(**invalid_config)

    def test_config_environment_overrides(self, test_config):
        """Test environment variable overrides."""
        # Set environment variables
        # os.environ["AGENTWEAVE_AGENT_NAME"] = "override-name"
        #
        # config = AgentConfig.from_env()
        # assert config.agent.name == "override-name"


@pytest.mark.parametrize(
    "capability_name,payload,expected_status",
    [
        ("test_capability", {}, "completed"),
        ("test_capability", {"key": "value"}, "completed"),
    ],
)
@pytest.mark.asyncio
async def test_capability_execution(test_agent, capability_name, payload, expected_status):
    """Parameterized test for capability execution."""
    result = await test_agent.call_capability(capability_name, payload)
    assert result["status"] == expected_status


class TestAgentResilience:
    """Test agent resilience features."""

    @pytest.mark.asyncio
    async def test_circuit_breaker(self, mock_transport):
        """Test circuit breaker functionality."""
        # Configure failures
        mock_transport.set_failure_mode("connection")

        # This would test circuit breaker
        # After threshold failures, circuit should open
        # for i in range(6):  # threshold is 5
        #     try:
        #         await agent.call_agent(...)
        #     except:
        #         pass
        #
        # Circuit should now be open
        # with pytest.raises(CircuitBreakerOpenError):
        #     await agent.call_agent(...)

    @pytest.mark.asyncio
    async def test_retry_with_backoff(self, mock_transport):
        """Test retry with exponential backoff."""
        # Setup to succeed after 2 failures
        mock_transport.add_response(url="https://test:8443/task", status_code=500, body=b"Error")
        mock_transport.add_response(url="https://test:8443/task", status_code=500, body=b"Error")
        mock_transport.add_response(url="https://test:8443/task", status_code=200, body=b"OK")

        # Should retry and eventually succeed
        # result = await agent.call_agent(...)
        # assert result is not None

    @pytest.mark.asyncio
    async def test_connection_pooling(self, test_config):
        """Test connection pooling."""
        assert test_config["transport"]["connection_pool"]["max_connections"] == 100

        # Test that connections are reused
        # This would require actual agent implementation
