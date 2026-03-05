"""
Secure RAG Knowledge Base Agent

Demonstrates:
- Multiple capabilities (search, index, summarize, stats)
- Peer-restricted capabilities (@requires_peer)
- Audit logging (@audit_log)
- RequestContext for caller-aware behavior
- In-memory vector-like document store
- Agent-to-agent calls via call_agent()
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from agentweave import (
    SecureAgent,
    AgentConfig,
    capability,
    requires_peer,
    audit_log,
    get_current_context,
)


class KnowledgeBaseAgent(SecureAgent):
    """
    A secure knowledge base agent that stores and retrieves documents.

    Capabilities:
    - search: Find documents matching a query (any authorized peer)
    - index: Add new documents (admin agent only)
    - summarize: Get a summary of a specific document (any authorized peer)
    - stats: Get knowledge base statistics (any authorized peer)
    """

    def __init__(self, config: AgentConfig, **kwargs):
        super().__init__(config=config, **kwargs)
        # In-memory document store (replace with vector DB in production)
        self._documents: dict[str, dict] = {}
        self._access_log: list[dict] = []

    @capability("search")
    @audit_log()
    async def search(
        self,
        query: str,
        max_results: int = 5,
        filters: Optional[dict] = None,
    ) -> dict:
        """Search the knowledge base for documents matching a query."""
        ctx = get_current_context()
        caller = ctx.caller_id if ctx else "unknown"

        # Simple keyword search (replace with vector similarity in production)
        results = []
        query_lower = query.lower()
        for doc_id, doc in self._documents.items():
            # Check if query matches title or content
            if (
                query_lower in doc["title"].lower()
                or query_lower in doc["content"].lower()
            ):
                # Apply filters if provided
                if filters:
                    if not all(
                        doc.get("metadata", {}).get(k) == v
                        for k, v in filters.items()
                    ):
                        continue
                results.append(
                    {
                        "id": doc_id,
                        "title": doc["title"],
                        "snippet": doc["content"][:200] + "...",
                        "relevance": 1.0,  # Placeholder score
                        "metadata": doc.get("metadata", {}),
                    }
                )
                if len(results) >= max_results:
                    break

        # Log access for compliance
        self._access_log.append(
            {
                "caller": caller,
                "action": "search",
                "query": query,
                "results_count": len(results),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

        return {
            "query": query,
            "results": results,
            "total": len(results),
            "searched_by": caller,
        }

    @capability("index")
    @requires_peer("spiffe://*/agent/admin*")
    @audit_log()
    async def index(
        self,
        title: str,
        content: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Index a new document into the knowledge base.

        Restricted to admin agents only via @requires_peer.
        All indexing operations are audit-logged.
        """
        ctx = get_current_context()
        caller = ctx.caller_id if ctx else "unknown"

        doc_id = f"doc_{len(self._documents) + 1:04d}"
        self._documents[doc_id] = {
            "title": title,
            "content": content,
            "metadata": metadata or {},
            "indexed_by": caller,
            "indexed_at": datetime.now(timezone.utc).isoformat(),
        }

        return {
            "status": "indexed",
            "document_id": doc_id,
            "title": title,
            "indexed_by": caller,
        }

    @capability("summarize")
    @audit_log()
    async def summarize(self, document_id: str) -> dict:
        """Get a summary of a specific document."""
        if document_id not in self._documents:
            return {"error": "Document not found", "document_id": document_id}

        doc = self._documents[document_id]
        # In production, this would call an LLM for summarization
        summary = doc["content"][:500]

        return {
            "document_id": document_id,
            "title": doc["title"],
            "summary": summary,
            "word_count": len(doc["content"].split()),
        }

    @capability("stats")
    async def stats(self) -> dict:
        """Get knowledge base statistics."""
        return {
            "total_documents": len(self._documents),
            "total_queries": len(self._access_log),
            "recent_queries": self._access_log[-10:],
        }


class ResearchAssistantAgent(SecureAgent):
    """
    A research assistant that uses the knowledge base to answer questions.

    Demonstrates agent-to-agent calls via call_agent().
    """

    @capability("research")
    async def research(self, question: str) -> dict:
        """
        Answer a research question by searching the knowledge base
        and synthesizing results.
        """
        # Step 1: Search the knowledge base agent
        search_results = await self.call_agent(
            target="spiffe://research.example/agent/knowledge-base",
            task_type="search",
            payload={"query": question, "max_results": 3},
        )

        # Step 2: Get summaries of top results
        summaries = []
        for result in search_results.get("results", []):
            summary = await self.call_agent(
                target="spiffe://research.example/agent/knowledge-base",
                task_type="summarize",
                payload={"document_id": result["id"]},
            )
            summaries.append(summary)

        # Step 3: Synthesize answer (in production, use an LLM)
        return {
            "question": question,
            "sources": search_results.get("results", []),
            "summaries": summaries,
            "answer": (
                f"Based on {len(summaries)} sources, here is what "
                f"I found about '{question}'..."
            ),
        }


async def main():
    """Run the knowledge base agent."""
    config = AgentConfig(
        name="knowledge-base",
        trust_domain="research.example",
        description="Secure RAG Knowledge Base Agent",
        identity_provider="mtls-static",
        authz_provider="allow-all",
    )
    agent = KnowledgeBaseAgent(config)

    # Pre-load some sample documents
    now = datetime.now(timezone.utc).isoformat()
    agent._documents = {
        "doc_0001": {
            "title": "AgentWeave Security Architecture",
            "content": (
                "AgentWeave uses SPIFFE for cryptographic identity. "
                "Every agent receives an X.509 SVID that proves its "
                "identity without relying on network location or secrets. "
                "mTLS is enforced on every connection."
            ),
            "metadata": {"category": "security", "author": "engineering"},
            "indexed_by": "system",
            "indexed_at": now,
        },
        "doc_0002": {
            "title": "OPA Authorization Policies",
            "content": (
                "Open Policy Agent evaluates Rego policies on every request. "
                "Default deny in production ensures no unauthorized access. "
                "Policies can inspect caller SPIFFE ID, action, resource, and "
                "arbitrary context attributes."
            ),
            "metadata": {"category": "security", "author": "engineering"},
            "indexed_by": "system",
            "indexed_at": now,
        },
        "doc_0003": {
            "title": "A2A Protocol Specification",
            "content": (
                "The Agent-to-Agent protocol uses JSON-RPC 2.0 over HTTPS "
                "with mTLS. It defines a standard envelope for task submission, "
                "status polling, streaming results, and capability discovery."
            ),
            "metadata": {"category": "protocol", "author": "standards"},
            "indexed_by": "system",
            "indexed_at": now,
        },
    }

    await agent.start()
    print(f"Knowledge Base Agent running as {agent.get_spiffe_id()}")

    # Keep running
    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
