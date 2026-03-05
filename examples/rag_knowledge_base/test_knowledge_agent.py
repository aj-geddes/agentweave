"""
Tests for the Knowledge Base Agent.

Demonstrates how to test AgentWeave agents using mock providers.
Run with: pytest test_knowledge_agent.py
"""

import sys
from pathlib import Path

import pytest

# Allow importing the example module from this directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentweave import AgentConfig
from agentweave.context import RequestContext, set_current_context
from agentweave.testing import MockIdentityProvider, MockAuthorizationProvider
from knowledge_agent import KnowledgeBaseAgent


@pytest.fixture
def identity():
    return MockIdentityProvider(
        spiffe_id="spiffe://research.example/agent/knowledge-base",
        trust_domain="research.example",
    )


@pytest.fixture
def authz():
    provider = MockAuthorizationProvider(default_allow=False)

    # ----- Outbound rules (caller -> callee, used by call_agent) -----
    # Allow search from any agent in the trust domain
    provider.add_rule(
        caller_id="spiffe://research.example/agent/researcher",
        callee_id="spiffe://research.example/agent/knowledge-base",
        action="search",
        allowed=True,
    )
    # Allow index from admin only
    provider.add_rule(
        caller_id="spiffe://research.example/agent/admin",
        callee_id="spiffe://research.example/agent/knowledge-base",
        action="index",
        allowed=True,
    )
    # Deny index from non-admin
    provider.add_rule(
        caller_id="spiffe://research.example/agent/researcher",
        callee_id="spiffe://research.example/agent/knowledge-base",
        action="index",
        allowed=False,
    )

    # ----- Inbound rules (caller -> action, used by @capability) -----
    # Admin can call index inbound
    provider.add_rule(
        caller_id="spiffe://research.example/agent/admin",
        callee_id=None,
        action="index",
        allowed=True,
    )
    # Researcher is denied index inbound
    provider.add_rule(
        caller_id="spiffe://research.example/agent/researcher",
        callee_id=None,
        action="index",
        allowed=False,
    )

    return provider


@pytest.fixture
def agent(identity, authz):
    config = AgentConfig(
        name="knowledge-base",
        trust_domain="research.example",
        identity_provider="mtls-static",
        authz_provider="allow-all",
    )
    agent = KnowledgeBaseAgent(config=config, identity=identity, authz=authz)
    # Pre-load test documents
    agent._documents = {
        "doc_0001": {
            "title": "Test Document About Security",
            "content": (
                "This document covers security best practices "
                "for agent communication."
            ),
            "metadata": {"category": "security"},
            "indexed_by": "test",
            "indexed_at": "2024-01-01T00:00:00",
        },
        "doc_0002": {
            "title": "Test Document About Protocols",
            "content": (
                "The A2A protocol enables standardized "
                "agent-to-agent communication."
            ),
            "metadata": {"category": "protocol"},
            "indexed_by": "test",
            "indexed_at": "2024-01-01T00:00:00",
        },
    }
    return agent


class TestKnowledgeBaseSearch:
    """Test the search capability."""

    @pytest.mark.asyncio
    async def test_search_returns_matching_documents(self, agent):
        result = await agent.search(query="security")
        assert result["total"] >= 1
        assert result["results"][0]["title"] == "Test Document About Security"

    @pytest.mark.asyncio
    async def test_search_with_no_results(self, agent):
        result = await agent.search(query="nonexistent_topic_xyz")
        assert result["total"] == 0
        assert result["results"] == []

    @pytest.mark.asyncio
    async def test_search_respects_max_results(self, agent):
        result = await agent.search(query="document", max_results=1)
        assert len(result["results"]) <= 1

    @pytest.mark.asyncio
    async def test_search_with_filters(self, agent):
        result = await agent.search(
            query="document",
            filters={"category": "protocol"},
        )
        for r in result["results"]:
            assert r["metadata"]["category"] == "protocol"


class TestKnowledgeBaseIndex:
    """Test the index capability (admin-restricted)."""

    @pytest.mark.asyncio
    async def test_index_creates_document(self, agent):
        # The @requires_peer decorator on index checks the caller's
        # SPIFFE ID from the request context. Set up an admin context
        # so the peer verification passes.
        ctx = RequestContext.create(
            caller_id="spiffe://research.example/agent/admin",
            metadata={"task_type": "index"},
        )
        set_current_context(ctx)
        try:
            result = await agent.index(
                title="New Document",
                content="This is a new document about testing.",
                metadata={"category": "testing"},
            )
            assert result["status"] == "indexed"
            assert result["document_id"] in agent._documents
        finally:
            set_current_context(None)

    @pytest.mark.asyncio
    async def test_index_denied_for_non_admin(self, agent):
        # A non-admin caller is rejected. The @capability decorator's
        # inbound authz check fires first (denied by policy), and even
        # if it passed, @requires_peer would reject the SPIFFE pattern.
        ctx = RequestContext.create(
            caller_id="spiffe://research.example/agent/researcher",
            metadata={"task_type": "index"},
        )
        set_current_context(ctx)
        try:
            with pytest.raises(PermissionError):
                await agent.index(
                    title="Unauthorized",
                    content="Should not be indexed.",
                )
        finally:
            set_current_context(None)


class TestKnowledgeBaseSummarize:
    """Test the summarize capability."""

    @pytest.mark.asyncio
    async def test_summarize_existing_document(self, agent):
        result = await agent.summarize(document_id="doc_0001")
        assert result["title"] == "Test Document About Security"
        assert "word_count" in result

    @pytest.mark.asyncio
    async def test_summarize_missing_document(self, agent):
        result = await agent.summarize(document_id="doc_9999")
        assert "error" in result


class TestKnowledgeBaseStats:
    """Test the stats capability."""

    @pytest.mark.asyncio
    async def test_stats_returns_counts(self, agent):
        result = await agent.stats()
        assert result["total_documents"] == 2


class TestAuthorizationRules:
    """Test that authorization rules are properly configured."""

    @pytest.mark.asyncio
    async def test_researcher_can_search(self, authz):
        decision = await authz.check_outbound(
            caller_id="spiffe://research.example/agent/researcher",
            callee_id="spiffe://research.example/agent/knowledge-base",
            action="search",
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_admin_can_index(self, authz):
        decision = await authz.check_outbound(
            caller_id="spiffe://research.example/agent/admin",
            callee_id="spiffe://research.example/agent/knowledge-base",
            action="index",
        )
        assert decision.allowed is True

    @pytest.mark.asyncio
    async def test_researcher_cannot_index(self, authz):
        decision = await authz.check_outbound(
            caller_id="spiffe://research.example/agent/researcher",
            callee_id="spiffe://research.example/agent/knowledge-base",
            action="index",
        )
        assert decision.allowed is False
