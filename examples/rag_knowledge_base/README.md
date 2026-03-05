# Secure RAG Knowledge Base

A complete example demonstrating how to build a **Retrieval-Augmented Generation (RAG) knowledge base agent** with AgentWeave, where security is enforced at every layer.

## Scenario

A company has sensitive internal documents. They build a knowledge base agent that lets authorized agents search and query documents securely. The security model enforces:

- **Only agents in the same trust domain** (`research.example`) can search or summarize documents.
- **Only the admin agent** (`spiffe://research.example/agent/admin*`) can index new documents.
- **All document access is audit-logged** for compliance.
- **Cross-domain access is denied** by default (zero-trust).

## Architecture

```
+----------------------------+       A2A (mTLS)       +----------------------------+
|   ResearchAssistantAgent   | --------------------->  |   KnowledgeBaseAgent       |
|                            |                         |                            |
|  spiffe://research.example |  search, summarize      |  spiffe://research.example |
|  /agent/researcher         |                         |  /agent/knowledge-base     |
+----------------------------+                         +----------------------------+
                                                         |  search   (any peer)     |
+----------------------------+       A2A (mTLS)          |  summarize (any peer)    |
|   AdminAgent               | --------------------->   |  index     (admin only)  |
|                            |                           |  stats     (any peer)    |
|  spiffe://research.example |  index                    +----------------------------+
|  /agent/admin              |                                      |
+----------------------------+                                      v
                                                         +----------------------------+
                                                         |  OPA Policy Engine         |
                                                         |  (authz.rego)              |
                                                         |                            |
                                                         |  - default deny            |
                                                         |  - domain-scoped search    |
                                                         |  - admin-only indexing     |
                                                         +----------------------------+
```

### Request Flow

1. A research assistant agent calls `search` on the knowledge base agent.
2. AgentWeave establishes an mTLS connection using both agents' SPIFFE SVIDs.
3. The knowledge base agent's `@capability("search")` decorator triggers an authorization check against the injected authz provider (OPA in production, mock in tests).
4. The `@audit_log()` decorator records who searched, what they searched for, and when.
5. `get_current_context()` gives the handler the caller's SPIFFE ID so it can log per-caller access.
6. Results are returned over the authenticated channel.

For indexing, the `@requires_peer("spiffe://*/agent/admin*")` decorator adds an additional check: only callers whose SPIFFE ID matches the admin pattern can invoke `index`.

## AgentWeave Features Demonstrated

| Feature | Where | Purpose |
|---|---|---|
| `@capability` decorator | `search`, `index`, `summarize`, `stats` | Register methods as A2A-callable capabilities |
| `@requires_peer` decorator | `index` | Restrict indexing to admin agents only |
| `@audit_log()` decorator | `search`, `index`, `summarize` | Log every access for compliance |
| `get_current_context()` | `search`, `index` | Retrieve caller SPIFFE ID inside handlers |
| `call_agent()` | `ResearchAssistantAgent.research` | Agent-to-agent communication over mTLS |
| OPA policy (`authz.rego`) | `policies/authz.rego` | Fine-grained Rego rules for access control |
| `MockIdentityProvider` | `test_knowledge_agent.py` | Test without a real SPIRE deployment |
| `MockAuthorizationProvider` | `test_knowledge_agent.py` | Test authorization rules in isolation |

## Files

```
rag_knowledge_base/
  README.md                   # This file
  knowledge_agent.py          # KnowledgeBaseAgent and ResearchAssistantAgent
  config.yaml                 # Production-style configuration
  policies/
    authz.rego                # OPA authorization policy
  test_knowledge_agent.py     # Tests using mock providers
```

## Running the Example

### Prerequisites

```bash
# From the repository root, install AgentWeave in development mode
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### Run the Agent (standalone)

The `main()` function in `knowledge_agent.py` starts the agent with an in-memory document store pre-loaded with sample documents. In a real deployment, SPIFFE and OPA would be running alongside the agent.

```bash
cd examples/rag_knowledge_base
python knowledge_agent.py
```

Note: Without a running SPIRE agent and OPA server, the agent will use the simplified `AgentConfig` from `agent.py` with `mtls-static` identity and `allow-all` authorization for local development.

### Run the Tests

The tests use `MockIdentityProvider` and `MockAuthorizationProvider` so they run without any external infrastructure.

```bash
# From the repository root
pytest examples/rag_knowledge_base/test_knowledge_agent.py -v
```

Expected output:

```
test_knowledge_agent.py::TestKnowledgeBaseSearch::test_search_returns_matching_documents PASSED
test_knowledge_agent.py::TestKnowledgeBaseSearch::test_search_with_no_results PASSED
test_knowledge_agent.py::TestKnowledgeBaseSearch::test_search_respects_max_results PASSED
test_knowledge_agent.py::TestKnowledgeBaseSearch::test_search_with_filters PASSED
test_knowledge_agent.py::TestKnowledgeBaseIndex::test_index_creates_document PASSED
test_knowledge_agent.py::TestKnowledgeBaseSummarize::test_summarize_existing_document PASSED
test_knowledge_agent.py::TestKnowledgeBaseSummarize::test_summarize_missing_document PASSED
test_knowledge_agent.py::TestKnowledgeBaseStats::test_stats_returns_counts PASSED
test_knowledge_agent.py::TestAuthorizationRules::test_researcher_can_search PASSED
test_knowledge_agent.py::TestAuthorizationRules::test_admin_can_index PASSED
test_knowledge_agent.py::TestAuthorizationRules::test_researcher_cannot_index PASSED
```

## OPA Policy Details

The Rego policy in `policies/authz.rego` implements three rules:

1. **Search, summarize, and stats** are allowed for any agent whose SPIFFE ID starts with `spiffe://research.example/`. This scopes access to the trust domain.

2. **Index** is allowed only for agents whose SPIFFE ID starts with `spiffe://research.example/agent/admin`. This restricts document ingestion to administrators.

3. **Cross-domain deny** blocks any request where the caller's trust domain differs from the resource's trust domain, enforcing zero-trust boundaries.

To test the policy with OPA locally:

```bash
# Start OPA with the policy
opa run --server policies/

# Test a search request (should be allowed)
curl -X POST http://localhost:8181/v1/data/agentweave/authz/allow \
  -d '{
    "input": {
      "caller_spiffe_id": "spiffe://research.example/agent/researcher",
      "resource_spiffe_id": "spiffe://research.example/agent/knowledge-base",
      "action": "search"
    }
  }'

# Test an index request from researcher (should be denied)
curl -X POST http://localhost:8181/v1/data/agentweave/authz/allow \
  -d '{
    "input": {
      "caller_spiffe_id": "spiffe://research.example/agent/researcher",
      "resource_spiffe_id": "spiffe://research.example/agent/knowledge-base",
      "action": "index"
    }
  }'
```

## Extending This Example

- **Add a real vector store**: Replace the in-memory `_documents` dict with a vector database (e.g., ChromaDB, Pinecone) for semantic search.
- **Add LLM summarization**: Replace the truncation-based `summarize` with a call to an LLM via another AgentWeave agent.
- **Add document-level ACLs**: Extend the OPA policy to check per-document metadata (e.g., classification level, department) against caller attributes.
- **Add streaming**: Use A2A streaming to return search results incrementally for large result sets.
