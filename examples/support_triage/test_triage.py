"""
Tests for the Customer Support Triage System.

Demonstrates testing classification, routing, and authorization.
Run with: pytest test_triage.py -v
"""

import sys
from pathlib import Path

import pytest

# Allow importing the example module from this directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentweave import AgentConfig
from agentweave.testing import MockIdentityProvider, MockAuthorizationProvider
from triage import TriageAgent, BillingAgent, TechnicalAgent, AccountAgent


@pytest.fixture
def triage_agent():
    config = AgentConfig(
        name="triage",
        trust_domain="support.example",
        identity_provider="mtls-static",
        authz_provider="allow-all",
    )
    identity = MockIdentityProvider(
        spiffe_id="spiffe://support.example/agent/triage"
    )
    authz = MockAuthorizationProvider(default_allow=True)
    return TriageAgent(config=config, identity=identity, authz=authz)


@pytest.fixture
def billing_agent():
    config = AgentConfig(
        name="billing",
        trust_domain="support.example",
        identity_provider="mtls-static",
        authz_provider="allow-all",
    )
    identity = MockIdentityProvider(
        spiffe_id="spiffe://support.example/agent/billing"
    )
    authz = MockAuthorizationProvider(default_allow=True)
    return BillingAgent(config=config, identity=identity, authz=authz)


@pytest.fixture
def technical_agent():
    config = AgentConfig(
        name="technical",
        trust_domain="support.example",
        identity_provider="mtls-static",
        authz_provider="allow-all",
    )
    identity = MockIdentityProvider(
        spiffe_id="spiffe://support.example/agent/technical"
    )
    authz = MockAuthorizationProvider(default_allow=True)
    return TechnicalAgent(config=config, identity=identity, authz=authz)


@pytest.fixture
def account_agent():
    config = AgentConfig(
        name="account",
        trust_domain="support.example",
        identity_provider="mtls-static",
        authz_provider="allow-all",
    )
    identity = MockIdentityProvider(
        spiffe_id="spiffe://support.example/agent/account"
    )
    authz = MockAuthorizationProvider(default_allow=True)
    return AccountAgent(config=config, identity=identity, authz=authz)


class TestClassification:
    """Test ticket classification logic."""

    def test_billing_classification(self, triage_agent):
        category, confidence = triage_agent._classify(
            "Invoice issue", "I need a refund for my last payment"
        )
        assert category == "billing"
        assert confidence > 0

    def test_technical_classification(self, triage_agent):
        category, confidence = triage_agent._classify(
            "API errors", "Getting timeout errors on the API endpoint"
        )
        assert category == "technical"
        assert confidence > 0

    def test_account_classification(self, triage_agent):
        category, confidence = triage_agent._classify(
            "Can't login", "My account is locked after failed password attempts"
        )
        assert category == "account"
        assert confidence > 0

    def test_general_classification(self, triage_agent):
        category, confidence = triage_agent._classify(
            "Question", "What time does the office open?"
        )
        assert category == "general"
        assert confidence == 0.0

    def test_mixed_keywords_highest_wins(self, triage_agent):
        """When multiple categories match, the one with the most keywords wins."""
        category, confidence = triage_agent._classify(
            "Billing and payment",
            "I have a charge on my invoice and need a refund for the subscription fee",
        )
        assert category == "billing"
        assert confidence > 0.5

    def test_confidence_reflects_dominance(self, triage_agent):
        """Confidence should be higher when one category clearly dominates."""
        _, conf_clear = triage_agent._classify(
            "Refund request", "I need a refund for my invoice payment charge"
        )
        _, conf_mixed = triage_agent._classify(
            "Refund and error", "I need a refund because of an error"
        )
        assert conf_clear > conf_mixed


class TestSpecialistAgents:
    """Test specialist agent ticket handling."""

    @pytest.mark.asyncio
    async def test_billing_handles_refund(self, billing_agent):
        result = await billing_agent.handle_ticket(
            ticket_id="TKT-00001",
            subject="Refund request",
            description="Please refund my last invoice",
            customer_id="CUST001",
        )
        assert result["handler"] == "billing_agent"
        assert result["status"] == "processing"
        assert any(a["type"] == "refund_review" for a in result["actions"])

    @pytest.mark.asyncio
    async def test_billing_handles_invoice(self, billing_agent):
        result = await billing_agent.handle_ticket(
            ticket_id="TKT-00002",
            subject="Invoice question",
            description="Can I get a copy of my invoice?",
            customer_id="CUST002",
        )
        assert any(a["type"] == "invoice_lookup" for a in result["actions"])

    @pytest.mark.asyncio
    async def test_billing_general_fallback(self, billing_agent):
        result = await billing_agent.handle_ticket(
            ticket_id="TKT-00003",
            subject="Billing question",
            description="How does your pricing model work?",
            customer_id="CUST003",
        )
        assert any(a["type"] == "general_billing" for a in result["actions"])

    @pytest.mark.asyncio
    async def test_billing_urgent_priority(self, billing_agent):
        result = await billing_agent.handle_ticket(
            ticket_id="TKT-00004",
            subject="Urgent refund",
            description="Need a refund immediately",
            customer_id="CUST004",
            priority="urgent",
        )
        assert result["estimated_resolution"] == "4 hours"

    @pytest.mark.asyncio
    async def test_technical_handles_error(self, technical_agent):
        result = await technical_agent.handle_ticket(
            ticket_id="TKT-00005",
            subject="500 errors",
            description="API returning 500 error codes",
            customer_id="CUST005",
        )
        assert result["handler"] == "technical_agent"
        assert result["status"] == "investigating"
        assert any(d["check"] == "error_logs" for d in result["diagnostics"])

    @pytest.mark.asyncio
    async def test_technical_handles_performance(self, technical_agent):
        result = await technical_agent.handle_ticket(
            ticket_id="TKT-00006",
            subject="Slow responses",
            description="The API is slow and requests are hitting a timeout",
            customer_id="CUST006",
        )
        assert any(d["check"] == "performance" for d in result["diagnostics"])

    @pytest.mark.asyncio
    async def test_technical_handles_certificates(self, technical_agent):
        result = await technical_agent.handle_ticket(
            ticket_id="TKT-00007",
            subject="TLS issue",
            description="Certificate has expired and connections are failing",
            customer_id="CUST007",
        )
        assert any(d["check"] == "certificates" for d in result["diagnostics"])

    @pytest.mark.asyncio
    async def test_account_handles_locked(self, account_agent):
        result = await account_agent.handle_ticket(
            ticket_id="TKT-00008",
            subject="Account locked",
            description="My account is locked after too many failed password attempts",
            customer_id="CUST008",
        )
        assert result["handler"] == "account_agent"
        assert result["security_review_required"] is True
        assert any(a["type"] == "account_unlock" for a in result["actions"])

    @pytest.mark.asyncio
    async def test_account_handles_mfa(self, account_agent):
        result = await account_agent.handle_ticket(
            ticket_id="TKT-00009",
            subject="MFA reset",
            description="I lost my phone and need to reset MFA",
            customer_id="CUST009",
        )
        assert any(a["type"] == "mfa_reset" for a in result["actions"])
        assert result["security_review_required"] is True

    @pytest.mark.asyncio
    async def test_account_handles_access_review(self, account_agent):
        result = await account_agent.handle_ticket(
            ticket_id="TKT-00010",
            subject="Permission request",
            description="I need access to the admin dashboard",
            customer_id="CUST010",
        )
        assert any(a["type"] == "access_review" for a in result["actions"])


class TestTriageRouting:
    """Test triage routing and ticket submission."""

    @pytest.mark.asyncio
    async def test_submit_ticket_classifies_correctly(self, triage_agent):
        result = await triage_agent.submit_ticket(
            subject="Invoice discrepancy",
            description="I was charged twice on my invoice",
            customer_id="CUST001",
        )
        assert result["category"] == "billing"
        assert result["ticket_id"].startswith("TKT-")
        assert result["confidence"] > 0

    @pytest.mark.asyncio
    async def test_submit_ticket_routes_to_specialist(self, triage_agent):
        result = await triage_agent.submit_ticket(
            subject="API error",
            description="500 error on the endpoint",
            customer_id="CUST002",
        )
        assert result["status"] == "routed"
        assert result["specialist_response"] is not None

    @pytest.mark.asyncio
    async def test_general_ticket_goes_to_queue(self, triage_agent):
        result = await triage_agent.submit_ticket(
            subject="General question",
            description="What are your business hours?",
            customer_id="CUST003",
        )
        assert result["category"] == "general"
        assert result["status"] == "unrouted"

    @pytest.mark.asyncio
    async def test_get_ticket_status(self, triage_agent):
        # Submit a ticket first
        submit_result = await triage_agent.submit_ticket(
            subject="Payment issue",
            description="My payment was declined",
            customer_id="CUST004",
        )
        ticket_id = submit_result["ticket_id"]

        # Check its status
        status = await triage_agent.get_ticket_status(ticket_id)
        assert status["ticket_id"] == ticket_id
        assert status["customer_id"] == "CUST004"

    @pytest.mark.asyncio
    async def test_get_ticket_status_not_found(self, triage_agent):
        result = await triage_agent.get_ticket_status("TKT-99999")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_metrics_increment(self, triage_agent):
        # Submit multiple tickets
        await triage_agent.submit_ticket(
            subject="Refund", description="Need a refund",
            customer_id="CUST001",
        )
        await triage_agent.submit_ticket(
            subject="Error", description="Getting 500 errors",
            customer_id="CUST002",
        )

        metrics = await triage_agent.get_metrics()
        assert metrics["total_tickets"] == 2
        assert metrics["by_category"]["billing"] >= 1
        assert metrics["by_category"]["technical"] >= 1


class TestTriageAuthorization:
    """Test triage routing authorization rules."""

    @pytest.mark.asyncio
    async def test_triage_can_route_to_billing(self):
        authz = MockAuthorizationProvider(default_allow=False)
        authz.add_rule(
            caller_id="spiffe://support.example/agent/triage",
            callee_id="spiffe://support.example/agent/billing",
            action="handle_ticket",
            allowed=True,
        )
        decision = await authz.check_outbound(
            caller_id="spiffe://support.example/agent/triage",
            callee_id="spiffe://support.example/agent/billing",
            action="handle_ticket",
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_triage_can_route_to_technical(self):
        authz = MockAuthorizationProvider(default_allow=False)
        authz.add_rule(
            caller_id="spiffe://support.example/agent/triage",
            callee_id="spiffe://support.example/agent/technical",
            action="handle_ticket",
            allowed=True,
        )
        decision = await authz.check_outbound(
            caller_id="spiffe://support.example/agent/triage",
            callee_id="spiffe://support.example/agent/technical",
            action="handle_ticket",
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_triage_can_route_to_account(self):
        authz = MockAuthorizationProvider(default_allow=False)
        authz.add_rule(
            caller_id="spiffe://support.example/agent/triage",
            callee_id="spiffe://support.example/agent/account",
            action="handle_ticket",
            allowed=True,
        )
        decision = await authz.check_outbound(
            caller_id="spiffe://support.example/agent/triage",
            callee_id="spiffe://support.example/agent/account",
            action="handle_ticket",
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_billing_cannot_route_to_technical(self):
        """Specialists should not call other specialists directly."""
        authz = MockAuthorizationProvider(default_allow=False)
        decision = await authz.check_outbound(
            caller_id="spiffe://support.example/agent/billing",
            callee_id="spiffe://support.example/agent/technical",
            action="handle_ticket",
        )
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_external_cannot_access_specialists(self):
        """External agents cannot bypass triage."""
        authz = MockAuthorizationProvider(default_allow=False)
        decision = await authz.check_outbound(
            caller_id="spiffe://external.com/agent/unknown",
            callee_id="spiffe://support.example/agent/billing",
            action="handle_ticket",
        )
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_internal_agent_can_submit_ticket(self):
        """Any agent in the trust domain can submit tickets."""
        authz = MockAuthorizationProvider(default_allow=False)
        authz.add_rule(
            caller_id="spiffe://support.example/agent/frontend",
            callee_id="spiffe://support.example/agent/triage",
            action="submit_ticket",
            allowed=True,
        )
        decision = await authz.check_outbound(
            caller_id="spiffe://support.example/agent/frontend",
            callee_id="spiffe://support.example/agent/triage",
            action="submit_ticket",
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_external_cannot_submit_ticket(self):
        """External agents cannot submit tickets."""
        authz = MockAuthorizationProvider(default_allow=False)
        decision = await authz.check_outbound(
            caller_id="spiffe://external.com/agent/attacker",
            callee_id="spiffe://support.example/agent/triage",
            action="submit_ticket",
        )
        assert decision.allowed is False
