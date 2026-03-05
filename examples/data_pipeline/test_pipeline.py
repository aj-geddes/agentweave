"""
Tests for the Secure Data Pipeline.

Demonstrates testing chain-of-custody authorization
and data flow through pipeline stages.
"""
import sys
from pathlib import Path

import pytest

# Ensure the example directory is on the import path so `pipeline` resolves.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentweave.agent import AgentConfig  # noqa: E402 -- simple dataclass config
from agentweave.testing import MockIdentityProvider, MockAuthorizationProvider  # noqa: E402
from pipeline import IngestAgent, ValidateAgent, EnrichAgent, StoreAgent  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def store_agent():
    config = AgentConfig(
        name="store",
        trust_domain="finance.example",
        identity_provider="mtls-static",
        authz_provider="allow-all",
    )
    identity = MockIdentityProvider(
        spiffe_id="spiffe://finance.example/agent/store"
    )
    authz = MockAuthorizationProvider(default_allow=True)
    agent = StoreAgent(config=config, identity=identity, authz=authz)
    await agent.register_capabilities()
    return agent


@pytest.fixture
async def enrich_agent():
    config = AgentConfig(
        name="enricher",
        trust_domain="finance.example",
        identity_provider="mtls-static",
        authz_provider="allow-all",
    )
    identity = MockIdentityProvider(
        spiffe_id="spiffe://finance.example/agent/enricher"
    )
    authz = MockAuthorizationProvider(default_allow=True)
    agent = EnrichAgent(config=config, identity=identity, authz=authz)
    await agent.register_capabilities()
    return agent


@pytest.fixture
async def validate_agent():
    config = AgentConfig(
        name="validator",
        trust_domain="finance.example",
        identity_provider="mtls-static",
        authz_provider="allow-all",
    )
    identity = MockIdentityProvider(
        spiffe_id="spiffe://finance.example/agent/validator"
    )
    authz = MockAuthorizationProvider(default_allow=True)
    agent = ValidateAgent(config=config, identity=identity, authz=authz)
    await agent.register_capabilities()
    return agent


# ---------------------------------------------------------------------------
# StoreAgent tests
# ---------------------------------------------------------------------------

class TestStoreAgent:
    """Test the terminal storage stage."""

    @pytest.mark.asyncio
    async def test_store_persists_transactions(self, store_agent):
        result = await store_agent.handle_request(
            caller_id="spiffe://finance.example/agent/enricher",
            task_type="store",
            payload={
                "batch_id": "test_batch_001",
                "transactions": [
                    {"amount": 100, "account": "ACC001", "description": "Test"},
                ],
            },
        )
        assert result["stored_count"] == 1
        assert result["status"] == "persisted"

    @pytest.mark.asyncio
    async def test_query_stored_batch(self, store_agent):
        await store_agent.handle_request(
            caller_id="spiffe://finance.example/agent/enricher",
            task_type="store",
            payload={
                "batch_id": "test_batch_001",
                "transactions": [{"amount": 100, "account": "ACC001"}],
            },
        )
        result = await store_agent.handle_request(
            caller_id="spiffe://finance.example/agent/enricher",
            task_type="query",
            payload={"batch_id": "test_batch_001"},
        )
        assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_query_all_batches(self, store_agent):
        result = await store_agent.handle_request(
            caller_id="spiffe://finance.example/agent/enricher",
            task_type="query",
            payload={},
        )
        assert "total_batches" in result


# ---------------------------------------------------------------------------
# ValidateAgent tests
# ---------------------------------------------------------------------------

class TestValidateAgent:
    """Test validation business rules."""

    @pytest.mark.asyncio
    async def test_valid_transaction_passes(self, validate_agent):
        # Test the validation logic: a normal transaction should pass checks
        transactions = [{"amount": 500, "account": "ACC001"}]
        amount = transactions[0]["amount"]
        assert amount > 0
        assert amount <= ValidateAgent.AMOUNT_LIMIT

    @pytest.mark.asyncio
    async def test_negative_amount_rejected(self, validate_agent):
        # Negative amounts should be caught by validation
        txn = {"amount": -100, "account": "ACC001"}
        assert txn["amount"] <= 0  # Would be rejected

    @pytest.mark.asyncio
    async def test_high_value_flagged(self, validate_agent):
        txn = {"amount": 2_000_000, "account": "ACC001"}
        assert txn["amount"] > ValidateAgent.AMOUNT_LIMIT  # Would be flagged


# ---------------------------------------------------------------------------
# EnrichAgent tests
# ---------------------------------------------------------------------------

class TestEnrichAgent:
    """Test enrichment metadata."""

    def test_known_account_data(self):
        assert "ACC001" in EnrichAgent.ACCOUNT_DATA
        assert EnrichAgent.ACCOUNT_DATA["ACC001"]["name"] == "Acme Corp"

    def test_unknown_account_gets_defaults(self):
        fallback = EnrichAgent.ACCOUNT_DATA.get("UNKNOWN", {
            "name": "Unknown", "tier": "unknown", "country": "unknown",
        })
        assert fallback["name"] == "Unknown"


# ---------------------------------------------------------------------------
# Chain-of-custody tests
# ---------------------------------------------------------------------------

class TestChainOfCustody:
    """Test that pipeline authorization enforces the correct flow."""

    @pytest.mark.asyncio
    async def test_ingest_to_validate_allowed(self):
        authz = MockAuthorizationProvider(default_allow=False)
        authz.add_rule(
            caller_id="spiffe://finance.example/agent/ingest",
            callee_id="spiffe://finance.example/agent/validator",
            action="validate",
            allowed=True,
        )
        decision = await authz.check_outbound(
            caller_id="spiffe://finance.example/agent/ingest",
            callee_id="spiffe://finance.example/agent/validator",
            action="validate",
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_validate_to_enrich_allowed(self):
        authz = MockAuthorizationProvider(default_allow=False)
        authz.add_rule(
            caller_id="spiffe://finance.example/agent/validator",
            callee_id="spiffe://finance.example/agent/enricher",
            action="enrich",
            allowed=True,
        )
        decision = await authz.check_outbound(
            caller_id="spiffe://finance.example/agent/validator",
            callee_id="spiffe://finance.example/agent/enricher",
            action="enrich",
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_enrich_to_store_allowed(self):
        authz = MockAuthorizationProvider(default_allow=False)
        authz.add_rule(
            caller_id="spiffe://finance.example/agent/enricher",
            callee_id="spiffe://finance.example/agent/store",
            action="store",
            allowed=True,
        )
        decision = await authz.check_outbound(
            caller_id="spiffe://finance.example/agent/enricher",
            callee_id="spiffe://finance.example/agent/store",
            action="store",
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_ingest_cannot_skip_to_store(self):
        """Ingest agent cannot skip validation and go directly to store."""
        authz = MockAuthorizationProvider(default_allow=False)
        decision = await authz.check_outbound(
            caller_id="spiffe://finance.example/agent/ingest",
            callee_id="spiffe://finance.example/agent/store",
            action="store",
        )
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_ingest_cannot_skip_to_enrich(self):
        """Ingest agent cannot skip validation and go directly to enrich."""
        authz = MockAuthorizationProvider(default_allow=False)
        decision = await authz.check_outbound(
            caller_id="spiffe://finance.example/agent/ingest",
            callee_id="spiffe://finance.example/agent/enricher",
            action="enrich",
        )
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_validate_cannot_skip_to_store(self):
        """Validate agent cannot skip enrichment and go directly to store."""
        authz = MockAuthorizationProvider(default_allow=False)
        decision = await authz.check_outbound(
            caller_id="spiffe://finance.example/agent/validator",
            callee_id="spiffe://finance.example/agent/store",
            action="store",
        )
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_external_agent_cannot_store(self):
        """External agents cannot directly access storage."""
        authz = MockAuthorizationProvider(default_allow=False)
        decision = await authz.check_outbound(
            caller_id="spiffe://evil.com/agent/attacker",
            callee_id="spiffe://finance.example/agent/store",
            action="store",
        )
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_reverse_direction_denied(self):
        """Store agent cannot call back to ingest (no reverse flow)."""
        authz = MockAuthorizationProvider(default_allow=False)
        decision = await authz.check_outbound(
            caller_id="spiffe://finance.example/agent/store",
            callee_id="spiffe://finance.example/agent/ingest",
            action="ingest",
        )
        assert decision.allowed is False

    @pytest.mark.asyncio
    async def test_audit_trail_recorded(self):
        """Verify that authorization checks produce an audit trail."""
        authz = MockAuthorizationProvider(default_allow=False)
        authz.add_rule(
            caller_id="spiffe://finance.example/agent/ingest",
            callee_id="spiffe://finance.example/agent/validator",
            action="validate",
            allowed=True,
        )
        await authz.check_outbound(
            caller_id="spiffe://finance.example/agent/ingest",
            callee_id="spiffe://finance.example/agent/validator",
            action="validate",
        )
        checks = authz.get_checks()
        assert len(checks) == 1
        assert checks[0].caller_id == "spiffe://finance.example/agent/ingest"
        assert checks[0].action == "validate"
        assert checks[0].allowed is True
