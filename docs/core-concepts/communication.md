---
layout: page
title: A2A Protocol
description: Agent-to-agent communication using the A2A protocol in AgentWeave
permalink: /core-concepts/communication/
parent: Core Concepts
nav_order: 5
---

# A2A Protocol

The A2A (Agent-to-Agent) protocol is a standardized way for AI agents to communicate. This document explains how AgentWeave implements A2A for secure agent communication.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## What is Agent-to-Agent Communication?

**Agent-to-agent (A2A) communication** is when one AI agent sends work to another AI agent and receives results back.

Unlike human-agent interaction (chat interfaces), A2A is:
- **Machine-to-machine**: Structured data, not natural language
- **Task-oriented**: "Do this work" rather than "tell me about..."
- **Programmatic**: Called from code, not from UI

### Why A2A Protocol?

Before A2A, every agent framework used its own communication protocol:
- LangGraph: Custom message format
- CrewAI: Different custom format
- ADK: Yet another format

This meant agents built with different frameworks **couldn't talk to each other**.

**A2A solves this** by providing a universal protocol for agent communication.

{: .note }
The A2A protocol was originally developed by Google and donated to the Linux Foundation. It's framework-agnostic and designed for interoperability.

---

## A2A Protocol Overview

A2A is built on **JSON-RPC 2.0** over **HTTPS**.

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Agent Card** | Metadata document advertising capabilities (like OpenAPI for agents) |
| **Task** | A unit of work sent from one agent to another |
| **Message** | Data exchanged within a task (can contain text, JSON, files) |
| **Artifact** | Output produced when a task completes |
| **Part** | A piece of content within a message (text, data, file, tool call) |

### Request Flow

```
Agent A (Caller)                        Agent B (Callee)
      │                                       │
      ├─► 1. Discover capabilities           │
      │       GET /.well-known/agent.json    │
      │◄──────────────────────────────────────┤
      │   Agent Card (capabilities list)     │
      │                                       │
      ├─► 2. Send task                       │
      │       POST /tasks/send               │
      │       {                               │
      │         "type": "search",             │
      │         "messages": [...]             │
      │       }                               │
      │                                       │
      │                              3. Process task
      │                                 Execute capability
      │                                       │
      │◄─────────────────────────────────────┤
      │   4. Return result                   │
      │       {                               │
      │         "status": "completed",        │
      │         "artifacts": [...]            │
      │       }                               │
      │                                       │
```

---

## JSON-RPC 2.0 Message Format

A2A uses JSON-RPC 2.0 for all requests and responses.

### Request

```json
{
  "jsonrpc": "2.0",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "method": "tasks/send",
  "params": {
    "task": {
      "id": "task-123",
      "type": "search",
      "state": "submitted",
      "messages": [
        {
          "role": "user",
          "parts": [
            {
              "type": "data",
              "data": {
                "query": "AI security best practices",
                "max_results": 10
              }
            }
          ]
        }
      ]
    }
  }
}
```

### Response (Success)

```json
{
  "jsonrpc": "2.0",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "result": {
    "task": {
      "id": "task-123",
      "type": "search",
      "state": "completed",
      "messages": [
        {
          "role": "agent",
          "parts": [
            {
              "type": "data",
              "data": {
                "results": [
                  {"title": "...", "url": "..."},
                  {"title": "...", "url": "..."}
                ]
              }
            }
          ]
        }
      ],
      "artifacts": [
        {
          "type": "search_results",
          "data": {
            "count": 2,
            "results": [...]
          }
        }
      ]
    }
  }
}
```

### Response (Error)

```json
{
  "jsonrpc": "2.0",
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "error": {
    "code": -32000,
    "message": "Authorization denied",
    "data": {
      "reason": "Caller not authorized for action 'search'"
    }
  }
}
```

---

## Agent Cards

An **Agent Card** is a JSON document that describes an agent's capabilities. It's the A2A equivalent of an OpenAPI spec.

### Structure

```json
{
  "name": "search-agent",
  "description": "Searches data stores for information",
  "version": "1.0.0",
  "url": "https://search-agent.company.com",

  "capabilities": [
    {
      "name": "search",
      "description": "Full-text search across documents",
      "input_modes": ["application/json"],
      "output_modes": ["application/json"],
      "parameters": {
        "query": {
          "type": "string",
          "description": "Search query",
          "required": true
        },
        "max_results": {
          "type": "integer",
          "description": "Maximum number of results",
          "default": 10
        }
      }
    },
    {
      "name": "index",
      "description": "Index new documents",
      "input_modes": ["application/json"],
      "output_modes": ["application/json"]
    }
  ],

  "authentication": {
    "schemes": [
      {
        "type": "mtls",
        "spiffe_id": "spiffe://company.com/agent/search/prod"
      }
    ]
  },

  "extensions": {
    "spiffe_id": "spiffe://company.com/agent/search/prod",
    "trust_domain": "company.com",
    "opa_policies": "https://company.com/policies/search-agent.rego"
  }
}
```

### Discovery

Agent Cards are published at `/.well-known/agent.json`:

```bash
# Discover search agent's capabilities
curl https://search-agent.company.com/.well-known/agent.json
```

In AgentWeave:

```python
from agentweave.comms.a2a import AgentCard

# Fetch Agent Card from another agent
card = await AgentCard.fetch("https://search-agent.company.com")

print(f"Agent: {card.name}")
print(f"Description: {card.description}")
print(f"Capabilities:")
for cap in card.capabilities:
    print(f"  - {cap.name}: {cap.description}")
```

### Generating Agent Cards

AgentWeave generates Agent Cards automatically from your agent definition:

```python
class SearchAgent(SecureAgent):
    @capability("search")
    async def search(self, query: str, max_results: int = 10) -> TaskResult:
        """Full-text search across documents."""
        ...

# Agent Card is generated automatically
agent = SearchAgent.from_config("config.yaml")
card = agent.get_agent_card()

# Serve at /.well-known/agent.json
# (SDK handles this automatically)
```

---

## Task Lifecycle

A **task** represents a unit of work. Tasks move through states:

```
┌───────────┐
│ SUBMITTED │  Task created and sent to agent
└─────┬─────┘
      │
      ▼
┌───────────┐
│  WORKING  │  Agent is processing the task
└─────┬─────┘
      │
      ├─────────────────┐
      │                 │
      ▼                 ▼
┌───────────┐     ┌──────────┐
│ COMPLETED │     │  FAILED  │
└───────────┘     └──────────┘
```

### Task States

| State | Description |
|-------|-------------|
| `submitted` | Task sent to agent, not yet started |
| `working` | Agent is actively processing |
| `completed` | Task finished successfully, artifacts available |
| `failed` | Task failed, error message available |

### Task Object

```python
from agentweave.comms.a2a import Task, TaskState, Message, DataPart

task = Task(
    id="task-123",
    type="search",  # Capability name
    state=TaskState.SUBMITTED,
    messages=[
        Message(
            role="user",
            parts=[
                DataPart(data={
                    "query": "AI security",
                    "max_results": 10
                })
            ]
        )
    ]
)
```

### Sending Tasks

```python
class OrchestratorAgent(SecureAgent):
    @capability("orchestrate")
    async def orchestrate(self, query: str) -> TaskResult:
        # Create task
        result = await self.call_agent(
            target="spiffe://company.com/agent/search",
            task_type="search",
            payload={"query": query, "max_results": 20}
        )

        # result is a TaskResult
        if result.status == "completed":
            data = result.artifacts[0]["data"]
            return TaskResult(
                status="completed",
                artifacts=[{"type": "aggregated", "data": data}]
            )
        else:
            return TaskResult(
                status="failed",
                error=f"Search failed: {result.error}"
            )
```

---

## Calling Other Agents

Agents call each other using the `call_agent()` method.

### Basic Call

```python
result = await self.call_agent(
    target="spiffe://company.com/agent/search",
    task_type="search",
    payload={"query": "test"}
)
```

**Parameters:**
- `target`: SPIFFE ID of the target agent
- `task_type`: Capability name to invoke
- `payload`: Input data (dict)
- `timeout`: Request timeout in seconds (default: 30)

### Full Example

```python
from agentweave import SecureAgent, capability
from agentweave.types import TaskResult

class DataPipeline(SecureAgent):
    @capability("process_pipeline")
    async def process_pipeline(self, data_source: str) -> TaskResult:
        # Step 1: Fetch data
        fetch_result = await self.call_agent(
            target="spiffe://company.com/agent/fetcher",
            task_type="fetch",
            payload={"source": data_source},
            timeout=60.0
        )

        if fetch_result.status != "completed":
            return TaskResult(
                status="failed",
                error=f"Fetch failed: {fetch_result.error}"
            )

        raw_data = fetch_result.artifacts[0]["data"]

        # Step 2: Process data
        process_result = await self.call_agent(
            target="spiffe://company.com/agent/processor",
            task_type="process",
            payload={"data": raw_data}
        )

        if process_result.status != "completed":
            return TaskResult(
                status="failed",
                error=f"Processing failed: {process_result.error}"
            )

        processed = process_result.artifacts[0]["data"]

        # Step 3: Store results
        store_result = await self.call_agent(
            target="spiffe://company.com/agent/storage",
            task_type="store",
            payload={"data": processed}
        )

        return store_result
```

### Error Handling

```python
from agentweave.exceptions import (
    AuthorizationError,
    IdentityError,
    TransportError,
    A2AProtocolError
)

@capability("robust_call")
async def robust_call(self, target: str, action: str) -> TaskResult:
    try:
        result = await self.call_agent(
            target=target,
            task_type=action,
            payload={},
            timeout=30.0
        )
        return result

    except AuthorizationError as e:
        # Not authorized to call this agent
        self.logger.error(f"Authorization denied: {e}")
        return TaskResult(
            status="failed",
            error="Not authorized",
            metadata={"error_type": "authorization"}
        )

    except IdentityError as e:
        # Identity verification failed
        self.logger.error(f"Identity error: {e}")
        return TaskResult(
            status="failed",
            error="Identity verification failed",
            metadata={"error_type": "identity"}
        )

    except TransportError as e:
        # Network error, connection refused, etc.
        self.logger.error(f"Transport error: {e}")
        return TaskResult(
            status="failed",
            error="Connection error",
            metadata={"error_type": "transport"}
        )

    except A2AProtocolError as e:
        # Invalid A2A response
        self.logger.error(f"Protocol error: {e}")
        return TaskResult(
            status="failed",
            error="Invalid response",
            metadata={"error_type": "protocol"}
        )

    except TimeoutError:
        # Request timed out
        return TaskResult(
            status="failed",
            error="Request timed out",
            metadata={"error_type": "timeout"}
        )
```

### Parallel Calls

Call multiple agents concurrently:

```python
import asyncio

@capability("search_all")
async def search_all(self, query: str) -> TaskResult:
    # Call multiple search agents in parallel
    results = await asyncio.gather(
        self.call_agent(
            target="spiffe://company.com/agent/search-docs",
            task_type="search",
            payload={"query": query}
        ),
        self.call_agent(
            target="spiffe://company.com/agent/search-code",
            task_type="search",
            payload={"query": query}
        ),
        self.call_agent(
            target="spiffe://company.com/agent/search-chat",
            task_type="search",
            payload={"query": query}
        ),
        return_exceptions=True  # Don't fail if one agent fails
    )

    # Aggregate results
    all_results = []
    for result in results:
        if isinstance(result, TaskResult) and result.status == "completed":
            all_results.extend(result.artifacts)
        elif isinstance(result, Exception):
            self.logger.warning(f"Agent call failed: {result}")

    return TaskResult(
        status="completed",
        artifacts=all_results,
        metadata={"sources": len(results), "succeeded": len(all_results)}
    )
```

---

## Handling Incoming Requests

When another agent calls your agent, the SDK routes the request to the appropriate capability handler.

### Capability Handler

```python
@capability("search")
async def search(self, query: str, max_results: int = 10) -> TaskResult:
    """
    This method is called when another agent sends a task with type="search".

    The SDK has already:
    - Verified the caller's identity (mTLS)
    - Checked authorization (OPA policy)
    - Parsed the A2A task
    - Extracted parameters from payload

    You just implement the business logic.
    """
    results = await self._database.search(query, limit=max_results)

    return TaskResult(
        status="completed",
        artifacts=[{
            "type": "search_results",
            "data": {
                "query": query,
                "count": len(results),
                "results": results
            }
        }]
    )
```

### Request Context

Access information about the incoming request:

```python
from agentweave.context import get_request_context

@capability("process")
async def process(self, data: dict) -> TaskResult:
    # Get request context
    ctx = get_request_context()

    self.logger.info(
        f"Processing request from {ctx.caller_spiffe_id}",
        extra={
            "caller": ctx.caller_spiffe_id,
            "task_id": ctx.task_id,
            "correlation_id": ctx.correlation_id
        }
    )

    # Process data
    result = await process_data(data)

    return TaskResult(status="completed", artifacts=[result])
```

**Context fields:**
- `caller_spiffe_id`: Who is calling this agent
- `task_id`: Unique ID for this task
- `correlation_id`: ID for distributed tracing
- `timestamp`: When the request was received
- `metadata`: Additional request metadata

---

## Streaming Responses

For long-running tasks, agents can stream progress updates using Server-Sent Events (SSE).

### Server Side (Not Yet Implemented)

```python
# Future feature - not yet available
@capability("analyze_large_dataset")
async def analyze(self, dataset_url: str) -> AsyncIterator[TaskProgress]:
    """Stream progress for a long-running task."""
    total_items = await get_dataset_size(dataset_url)

    for i, item in enumerate(fetch_dataset(dataset_url)):
        result = await analyze_item(item)

        # Yield progress update
        yield TaskProgress(
            state="working",
            progress=i / total_items,
            message=f"Processed {i+1}/{total_items}"
        )

    # Final result
    yield TaskProgress(
        state="completed",
        progress=1.0,
        artifacts=[{"type": "analysis", "data": {...}}]
    )
```

### Client Side (Not Yet Implemented)

```python
# Future feature - not yet available
@capability("orchestrate_analysis")
async def orchestrate(self, dataset: str) -> TaskResult:
    async for update in self.stream_agent(
        target="spiffe://company.com/agent/analyzer",
        task_type="analyze_large_dataset",
        payload={"dataset_url": dataset}
    ):
        self.logger.info(f"Progress: {update.progress:.0%} - {update.message}")

        if update.state == "completed":
            return TaskResult(
                status="completed",
                artifacts=update.artifacts
            )
        elif update.state == "failed":
            return TaskResult(
                status="failed",
                error=update.error
            )
```

{: .note }
**Streaming is a planned feature.** Currently, AgentWeave uses request/response. Streaming support will be added in a future release.

---

## A2A vs Other Protocols

### A2A vs REST

| Feature | A2A | REST |
|---------|-----|------|
| **Message format** | JSON-RPC 2.0 | Various (JSON, XML) |
| **Discovery** | Agent Cards | OpenAPI specs |
| **State** | Tasks with lifecycle | Stateless requests |
| **Streaming** | SSE for long tasks | Polling or WebSockets |
| **Use case** | Agent-to-agent | General APIs |

### A2A vs gRPC

| Feature | A2A | gRPC |
|---------|-----|------|
| **Protocol** | JSON over HTTPS | Protobuf over HTTP/2 |
| **Schema** | JSON Schema | Protobuf definitions |
| **Streaming** | SSE | Bidirectional streams |
| **Browser support** | Yes | Limited |
| **Use case** | Agent communication | High-performance services |

### When to Use A2A

**Use A2A when:**
- Communicating between AI agents
- You need standardized agent discovery
- Task-oriented workflows are a good fit
- You want framework interoperability

**Use REST/gRPC when:**
- Integrating with non-agent systems
- You need maximum performance (gRPC)
- Existing systems already use REST/gRPC

{: .note }
AgentWeave agents can make regular HTTP/gRPC calls in addition to A2A. A2A is for agent-to-agent communication; use whatever protocol makes sense for external integrations.

---

## Best Practices

### 1. Design Coarse-Grained Capabilities

A2A calls have overhead (network, mTLS, authorization). Design capabilities that do meaningful work:

```python
# ✅ Good: Coarse-grained capability
@capability("search")
async def search(self, query: str, max_results: int = 10) -> TaskResult:
    results = await self._db.search(query, limit=max_results)
    return TaskResult(status="completed", artifacts=[results])

# ❌ Bad: Too fine-grained
@capability("get_item")
async def get_item(self, id: str) -> TaskResult:
    # Calling this in a loop is inefficient
    item = await self._db.get(id)
    return TaskResult(status="completed", artifacts=[item])
```

### 2. Include Metadata in Artifacts

Help callers understand the results:

```python
@capability("analyze")
async def analyze(self, text: str) -> TaskResult:
    analysis = await perform_analysis(text)

    return TaskResult(
        status="completed",
        artifacts=[{
            "type": "sentiment_analysis",
            "data": {
                "sentiment": analysis.sentiment,
                "confidence": analysis.confidence,
                "entities": analysis.entities
            }
        }],
        metadata={
            "model_version": "1.2.0",
            "processing_time_ms": analysis.duration_ms,
            "language": analysis.detected_language
        }
    )
```

### 3. Use Structured Error Messages

Return actionable errors:

```python
@capability("process")
async def process(self, data: dict) -> TaskResult:
    try:
        result = await process_data(data)
        return TaskResult(status="completed", artifacts=[result])

    except ValidationError as e:
        return TaskResult(
            status="failed",
            error=str(e),
            metadata={
                "error_type": "validation",
                "invalid_fields": e.fields
            }
        )

    except Exception as e:
        self.logger.exception("Processing failed")
        return TaskResult(
            status="failed",
            error="Internal error",
            metadata={
                "error_type": "internal",
                "error_id": str(uuid.uuid4())  # For support lookup
            }
        )
```

### 4. Set Appropriate Timeouts

```python
# Short timeout for quick operations
result = await self.call_agent(
    target="spiffe://company.com/agent/cache",
    task_type="get",
    payload={"key": "value"},
    timeout=5.0  # 5 seconds
)

# Longer timeout for heavy processing
result = await self.call_agent(
    target="spiffe://company.com/agent/analyzer",
    task_type="analyze_large_file",
    payload={"file_url": url},
    timeout=300.0  # 5 minutes
)
```

### 5. Handle Partial Failures

When calling multiple agents, handle partial failures gracefully:

```python
@capability("aggregate")
async def aggregate(self, sources: list[str]) -> TaskResult:
    results = await asyncio.gather(
        *[self.call_agent(
            target=source,
            task_type="fetch",
            payload={}
        ) for source in sources],
        return_exceptions=True
    )

    successes = []
    failures = []

    for i, result in enumerate(results):
        if isinstance(result, TaskResult) and result.status == "completed":
            successes.append(result.artifacts[0])
        else:
            failures.append({
                "source": sources[i],
                "error": str(result) if isinstance(result, Exception) else result.error
            })

    # Return partial success
    return TaskResult(
        status="completed" if successes else "failed",
        artifacts=successes,
        metadata={
            "total_sources": len(sources),
            "successful": len(successes),
            "failed": len(failures),
            "failures": failures
        }
    )
```

---

## What's Next?

Now that you understand A2A communication, see how it all fits together:

- [Security Model](security-model/): How A2A, identity, and authorization work together for zero-trust
- [System Architecture](architecture/): See the complete request flow with all layers

{: .note }
The A2A protocol specification is evolving. AgentWeave tracks the latest spec and provides backward compatibility when possible.
