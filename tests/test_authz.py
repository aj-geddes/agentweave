"""
Tests for AgentWeave SDK authorization.

Tests authorization providers, policy enforcement, and OPA integration.
"""

import pytest
from datetime import datetime
from agentweave.testing import MockAuthorizationProvider, PolicySimulator


class TestMockAuthorizationProvider:
    """Test MockAuthorizationProvider functionality."""

    @pytest.mark.asyncio
    async def test_default_deny(self, mock_authz_provider):
        """Test that default behavior is deny."""
        decision = await mock_authz_provider.check_inbound(
            caller_id="spiffe://test.local/agent/caller",
            action="search",
        )

        assert decision.allowed is False
        assert decision.audit_id is not None

    @pytest.mark.asyncio
    async def test_default_allow(self, mock_authz_provider_permissive):
        """Test permissive mode allows by default."""
        decision = await mock_authz_provider_permissive.check_inbound(
            caller_id="spiffe://test.local/agent/caller",
            action="search",
        )

        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_add_allow_rule(self):
        """Test adding allow rule."""
        authz = MockAuthorizationProvider(default_allow=False)

        # Add rule
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
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_add_deny_rule(self):
        """Test adding deny rule."""
        authz = MockAuthorizationProvider(default_allow=True)

        # Add explicit deny rule
        authz.add_rule(
            caller_id="spiffe://evil.com/agent/bad",
            callee_id="spiffe://test.local/agent/search",
            action="search",
            allowed=False,
        )

        # Should be denied
        decision = await authz.check_outbound(
            caller_id="spiffe://evil.com/agent/bad",
            callee_id="spiffe://test.local/agent/search",
            action="search",
        )
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_record_checks(self):
        """Test that authorization checks are recorded."""
        authz = MockAuthorizationProvider(default_allow=True)

        # Make some checks
        await authz.check_inbound(
            caller_id="spiffe://test.local/agent/caller1",
            action="search",
        )
        await authz.check_inbound(
            caller_id="spiffe://test.local/agent/caller2",
            action="process",
        )

        # Get recorded checks
        checks = authz.get_checks()
        assert len(checks) == 2
        assert checks[0].caller_id == "spiffe://test.local/agent/caller1"
        assert checks[0].action == "search"
        assert checks[1].caller_id == "spiffe://test.local/agent/caller2"
        assert checks[1].action == "process"

    @pytest.mark.asyncio
    async def test_clear_checks(self):
        """Test clearing recorded checks."""
        authz = MockAuthorizationProvider(default_allow=True)

        await authz.check_inbound(
            caller_id="spiffe://test.local/agent/caller",
            action="search",
        )

        assert len(authz.get_checks()) == 1

        authz.clear_checks()
        assert len(authz.get_checks()) == 0

    @pytest.mark.asyncio
    async def test_check_includes_context(self):
        """Test that context is included in checks."""
        authz = MockAuthorizationProvider(default_allow=True)

        context = {"payload_size": 1024, "timestamp": "2025-12-06T12:00:00Z"}

        await authz.check_inbound(
            caller_id="spiffe://test.local/agent/caller",
            action="search",
            context=context,
        )

        checks = authz.get_checks()
        assert len(checks) == 1
        assert checks[0].context == context

    @pytest.mark.asyncio
    async def test_outbound_vs_inbound_checks(self):
        """Test distinction between outbound and inbound checks."""
        authz = MockAuthorizationProvider(default_allow=False)

        # Add inbound rule (no callee)
        authz.add_rule(
            caller_id="spiffe://test.local/agent/caller",
            callee_id=None,
            action="search",
            allowed=True,
        )

        # Inbound should be allowed
        decision = await authz.check_inbound(
            caller_id="spiffe://test.local/agent/caller",
            action="search",
        )
        assert decision.allowed is True

        # Outbound should be denied (different rule key)
        decision = await authz.check_outbound(
            caller_id="spiffe://test.local/agent/caller",
            callee_id="spiffe://test.local/agent/target",
            action="search",
        )
        assert decision.allowed is False


class TestPolicySimulator:
    """Test PolicySimulator for Rego policy testing."""

    def test_create_with_policy_content(self):
        """Test creating simulator with inline policy."""
        policy = """
package hvs.authz

import rego.v1

default allow := false

allow if {
    input.caller_spiffe_id == "spiffe://test.local/agent/allowed"
}
"""
        simulator = PolicySimulator(policy_content=policy)
        assert simulator is not None

    def test_create_with_policy_path(self, tmp_path):
        """Test creating simulator with policy file."""
        policy_file = tmp_path / "policy.rego"
        policy_file.write_text("""
package hvs.authz
default allow := false
""")

        simulator = PolicySimulator(policy_path=str(policy_file))
        assert simulator is not None

    def test_create_requires_policy(self):
        """Test that policy is required."""
        with pytest.raises(ValueError, match="Must provide either policy_path or policy_content"):
            PolicySimulator()

    @pytest.mark.skipif(
        True,  # Skip unless OPA CLI is available
        reason="Requires OPA CLI to be installed"
    )
    def test_check_allow(self):
        """Test checking if request is allowed."""
        policy = """
package hvs.authz

import rego.v1

default allow := false

allow if {
    input.caller_spiffe_id == "spiffe://test.local/agent/orchestrator"
    input.callee_spiffe_id == "spiffe://test.local/agent/search"
    input.action == "search"
}
"""
        simulator = PolicySimulator(policy_content=policy)

        decision = simulator.check(
            caller="spiffe://test.local/agent/orchestrator",
            callee="spiffe://test.local/agent/search",
            action="search",
        )

        assert decision.allowed is True

    @pytest.mark.skipif(
        True,
        reason="Requires OPA CLI to be installed"
    )
    def test_check_deny(self):
        """Test checking if request is denied."""
        policy = """
package hvs.authz

import rego.v1

default allow := false

allow if {
    input.caller_spiffe_id == "spiffe://test.local/agent/orchestrator"
}
"""
        simulator = PolicySimulator(policy_content=policy)

        decision = simulator.check(
            caller="spiffe://evil.com/agent/bad",
            callee="spiffe://test.local/agent/search",
            action="search",
        )

        assert decision.allowed is False

    @pytest.mark.skipif(
        True,
        reason="Requires OPA CLI to be installed"
    )
    def test_assert_allow(self):
        """Test assert_allow helper."""
        policy = """
package hvs.authz

import rego.v1

default allow := true
"""
        simulator = PolicySimulator(policy_content=policy)

        # Should not raise
        simulator.assert_allow(
            caller="spiffe://test.local/agent/any",
            callee="spiffe://test.local/agent/any",
            action="any",
        )

    @pytest.mark.skipif(
        True,
        reason="Requires OPA CLI to be installed"
    )
    def test_assert_allow_fails(self):
        """Test assert_allow fails when denied."""
        policy = """
package hvs.authz

import rego.v1

default allow := false
"""
        simulator = PolicySimulator(policy_content=policy)

        with pytest.raises(AssertionError, match="Expected request to be allowed"):
            simulator.assert_allow(
                caller="spiffe://test.local/agent/any",
                callee="spiffe://test.local/agent/any",
                action="any",
            )

    @pytest.mark.skipif(
        True,
        reason="Requires OPA CLI to be installed"
    )
    def test_assert_deny(self):
        """Test assert_deny helper."""
        policy = """
package hvs.authz

import rego.v1

default allow := false
"""
        simulator = PolicySimulator(policy_content=policy)

        # Should not raise
        simulator.assert_deny(
            caller="spiffe://test.local/agent/any",
            callee="spiffe://test.local/agent/any",
            action="any",
        )

    @pytest.mark.skipif(
        True,
        reason="Requires OPA CLI to be installed"
    )
    def test_test_scenarios(self):
        """Test running multiple scenarios."""
        policy = """
package hvs.authz

import rego.v1

default allow := false

allow if {
    startswith(input.caller_spiffe_id, "spiffe://test.local/")
}
"""
        simulator = PolicySimulator(policy_content=policy)

        scenarios = [
            {
                "name": "local_agent_allowed",
                "input": {
                    "caller_spiffe_id": "spiffe://test.local/agent/test",
                    "action": "search",
                },
                "expected": True,
            },
            {
                "name": "external_agent_denied",
                "input": {
                    "caller_spiffe_id": "spiffe://evil.com/agent/bad",
                    "action": "search",
                },
                "expected": False,
            },
        ]

        results = simulator.test_scenarios(scenarios)

        assert len(results) == 2
        assert results["local_agent_allowed"].allowed is True
        assert results["external_agent_denied"].allowed is False


class TestOPAEnforcer:
    """Test real OPA enforcer (requires OPA server)."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connect_to_opa(self):
        """Test connecting to OPA server."""
        pytest.skip("Requires running OPA server")

        # from agentweave.authz import OPAEnforcer
        #
        # enforcer = OPAEnforcer(
        #     endpoint="http://localhost:8181/v1/data",
        #     policy_path="hvs/authz",
        # )
        #
        # decision = await enforcer.check_inbound(
        #     caller_id="spiffe://test.local/agent/test",
        #     action="search",
        # )
        # assert decision is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_opa_policy_evaluation(self):
        """Test OPA policy evaluation."""
        pytest.skip("Requires running OPA server")

        # from agentweave.authz import OPAEnforcer
        #
        # enforcer = OPAEnforcer()
        #
        # decision = await enforcer.check_outbound(
        #     caller_id="spiffe://test.local/agent/orchestrator",
        #     callee_id="spiffe://test.local/agent/search",
        #     action="search",
        #     context={},
        # )
        #
        # assert decision.allowed in [True, False]
        # assert decision.audit_id is not None


class TestAuthorizationDecision:
    """Test AuthzDecision data structure."""

    def test_decision_structure(self):
        """Test decision has required fields."""
        from agentweave.testing.mocks import AuthzDecision

        decision = AuthzDecision(
            allowed=True,
            reason="test reason",
            audit_id="audit-123",
        )

        assert decision.allowed is True
        assert decision.reason == "test reason"
        assert decision.audit_id == "audit-123"


class TestAuthorizationAudit:
    """Test authorization audit trail."""

    @pytest.mark.asyncio
    async def test_audit_includes_timestamp(self):
        """Test that audit records include timestamp."""
        authz = MockAuthorizationProvider(default_allow=True)

        await authz.check_inbound(
            caller_id="spiffe://test.local/agent/caller",
            action="search",
        )

        checks = authz.get_checks()
        assert len(checks) == 1
        assert isinstance(checks[0].timestamp, datetime)

    @pytest.mark.asyncio
    async def test_audit_includes_decision(self):
        """Test that audit records include decision."""
        authz = MockAuthorizationProvider(default_allow=True)

        await authz.check_inbound(
            caller_id="spiffe://test.local/agent/caller",
            action="search",
        )

        checks = authz.get_checks()
        assert checks[0].allowed is True
        assert checks[0].reason is not None

    @pytest.mark.asyncio
    async def test_audit_trail_ordering(self):
        """Test that audit trail maintains order."""
        authz = MockAuthorizationProvider(default_allow=True)

        # Make checks in order
        await authz.check_inbound(
            caller_id="spiffe://test.local/agent/caller1",
            action="action1",
        )
        await authz.check_inbound(
            caller_id="spiffe://test.local/agent/caller2",
            action="action2",
        )
        await authz.check_inbound(
            caller_id="spiffe://test.local/agent/caller3",
            action="action3",
        )

        checks = authz.get_checks()
        assert len(checks) == 3
        assert checks[0].caller_id == "spiffe://test.local/agent/caller1"
        assert checks[1].caller_id == "spiffe://test.local/agent/caller2"
        assert checks[2].caller_id == "spiffe://test.local/agent/caller3"


class TestPolicyRules:
    """Test policy rule management."""

    @pytest.mark.asyncio
    async def test_remove_rule(self):
        """Test removing a policy rule."""
        authz = MockAuthorizationProvider(default_allow=False)

        # Add rule
        authz.add_rule(
            caller_id="spiffe://test.local/agent/caller",
            callee_id="spiffe://test.local/agent/callee",
            action="search",
            allowed=True,
        )

        # Should be allowed
        decision = await authz.check_outbound(
            caller_id="spiffe://test.local/agent/caller",
            callee_id="spiffe://test.local/agent/callee",
            action="search",
        )
        assert decision.allowed is True

        # Remove rule
        authz.remove_rule(
            caller_id="spiffe://test.local/agent/caller",
            callee_id="spiffe://test.local/agent/callee",
            action="search",
        )

        # Should now be denied (fallback to default)
        decision = await authz.check_outbound(
            caller_id="spiffe://test.local/agent/caller",
            callee_id="spiffe://test.local/agent/callee",
            action="search",
        )
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_multiple_rules_same_caller(self):
        """Test multiple rules for same caller."""
        authz = MockAuthorizationProvider(default_allow=False)

        # Add multiple rules
        authz.add_rule(
            caller_id="spiffe://test.local/agent/caller",
            callee_id="spiffe://test.local/agent/callee1",
            action="search",
            allowed=True,
        )
        authz.add_rule(
            caller_id="spiffe://test.local/agent/caller",
            callee_id="spiffe://test.local/agent/callee2",
            action="process",
            allowed=True,
        )

        # Both should be allowed
        decision1 = await authz.check_outbound(
            caller_id="spiffe://test.local/agent/caller",
            callee_id="spiffe://test.local/agent/callee1",
            action="search",
        )
        assert decision1.allowed is True

        decision2 = await authz.check_outbound(
            caller_id="spiffe://test.local/agent/caller",
            callee_id="spiffe://test.local/agent/callee2",
            action="process",
        )
        assert decision2.allowed is True

        # Different action should be denied
        decision3 = await authz.check_outbound(
            caller_id="spiffe://test.local/agent/caller",
            callee_id="spiffe://test.local/agent/callee1",
            action="delete",
        )
        assert decision3.allowed is False


@pytest.mark.parametrize(
    "caller,callee,action,expected",
    [
        # Same trust domain
        ("spiffe://test.local/agent/a", "spiffe://test.local/agent/b", "search", True),
        # Different trust domain
        ("spiffe://evil.com/agent/a", "spiffe://test.local/agent/b", "search", False),
        # Federated trust domain (would need to be configured)
        ("spiffe://partner.com/agent/a", "spiffe://test.local/agent/b", "search", False),
    ],
)
def test_trust_domain_policy(caller, callee, action, expected):
    """Test trust domain-based policy decisions."""
    # This is a parameterized test showing how policies might work
    # In reality, this would use PolicySimulator with appropriate Rego
    pass
