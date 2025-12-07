# A2A Protocol Reference

The Agent-to-Agent (A2A) Protocol is an open standard for AI agent communication. This guide explains how the AgentWeave SDK implements A2A.

## Overview

A2A provides:
- **Standardized communication**: Agents from different frameworks can interoperate
- **Task-based model**: Request/response with long-running task support
- **Capability discovery**: Agents advertise what they can do via Agent Cards
- **Framework agnostic**: Works with any agent framework (LangGraph, CrewAI, ADK, etc.)

**Specification**: https://a2a-protocol.org/latest/

## Core Concepts

### Agent Card

An Agent Card is JSON metadata describing an agent's capabilities and endpoints.

**Location**: `/.well-known/agent.json`

**Example**:
```json
{
  "name": "data-processor",
  "description": "Processes structured data",
  "url": "https://data-processor.agentweaves.svc.cluster.local:8443",
  "version": "1.0.0",
  "capabilities": [
    {
      "name": "process",
      "description": "Process data records",
      "input_modes": ["application/json"],
      "output_modes": ["application/json"],
      "parameters": {
        "type": "object",
        "properties": {
          "data": {
            "type": "array",
            "items": {"type": "object"}
          },
          "options": {
            "type": "object",
            "properties": {
              "validate": {"type": "boolean"},
              "transform": {"type": "string"}
            }
          }
        },
        "required": ["data"]
      }
    }
  ],
  "authentication": {
    "schemes": [
      {
        "type": "mtls",
        "description": "SPIFFE mTLS authentication"
      }
    ]
  },
  "extensions": {
    "spiffe_id": "spiffe://agentweave.io/agent/data-processor/prod"
  }
}
```

### Task

A task represents a unit of work with a lifecycle:

```
submitted → working → completed
                   ↘ failed
```

**Task Structure**:
```json
{
  "id": "task-123",
  "type": "process",
  "state": "submitted",
  "messages": [
    {
      "role": "user",
      "parts": [
        {
          "type": "data",
          "data": {
            "records": [...]
          }
        }
      ]
    }
  ]
}
```

### Message

Messages contain the actual data being exchanged. Each message has:
- **Role**: `user` (requester) or `assistant` (agent)
- **Parts**: Content pieces (text, data, files)

**Part Types**:
- `text`: Plain text or markdown
- `data`: Structured data (JSON)
- `file`: File reference with URI
- `tool_use`: Tool invocation
- `tool_result`: Tool execution result

### Artifact

Artifacts are the outputs produced by task completion:

```json
{
  "type": "processed_data",
  "name": "results.json",
  "data": {
    "processed": true,
    "record_count": 1000
  }
}
```

## SDK Implementation

### Defining Capabilities

Use the `@capability` decorator:

```python
from agentweave import SecureAgent, capability
from agentweave.types import TaskResult

class DataProcessor(SecureAgent):
    @capability("process")
    async def process(self, data: list[dict], options: dict = None) -> TaskResult:
        """
        Process data records.

        The decorator automatically:
        - Registers this in the Agent Card
        - Validates input against type hints
        - Wraps response in A2A format
        """
        processed = [self._transform(record) for record in data]

        return TaskResult(
            status="completed",
            artifacts=[{
                "type": "processed_data",
                "data": {"records": processed}
            }]
        )
```

The SDK automatically generates the Agent Card from your capabilities.

### Calling Other Agents

```python
class OrchestratorAgent(SecureAgent):
    async def coordinate(self):
        # Discover processor agent
        processor_card = await self.discover_agent(
            "spiffe://agentweave.io/agent/data-processor/prod"
        )

        # Check if it has the capability we need
        if not processor_card.has_capability("process"):
            raise ValueError("Processor doesn't support 'process'")

        # Call the agent
        result = await self.call_agent(
            target="spiffe://agentweave.io/agent/data-processor/prod",
            task_type="process",
            payload={
                "data": [{"id": 1, "value": "test"}],
                "options": {"validate": True}
            }
        )

        # Extract result
        processed_data = result.artifacts[0]["data"]
        return processed_data
```

## A2A Endpoints

The SDK automatically implements these A2A endpoints:

### Discovery Endpoint

**GET** `/.well-known/agent.json`

Returns the Agent Card.

```bash
curl https://agent.example.com/.well-known/agent.json
```

### Task Submission

**POST** `/.well-known/a2a/tasks/send`

Submit a new task for execution.

**Request**:
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "method": "tasks.send",
  "params": {
    "task": {
      "type": "process",
      "messages": [
        {
          "role": "user",
          "parts": [
            {
              "type": "data",
              "data": {
                "data": [{"id": 1}],
                "options": {"validate": true}
              }
            }
          ]
        }
      ]
    }
  }
}
```

**Response** (synchronous):
```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "result": {
    "task": {
      "id": "task-456",
      "type": "process",
      "state": "completed",
      "messages": [
        {
          "role": "user",
          "parts": [...]
        },
        {
          "role": "assistant",
          "parts": [
            {
              "type": "data",
              "data": {
                "processed": true
              }
            }
          ]
        }
      ],
      "artifacts": [
        {
          "type": "processed_data",
          "data": {"records": [...]}
        }
      ]
    }
  }
}
```

### Task Status

**GET** `/.well-known/a2a/tasks/{task_id}`

Get status of a long-running task.

```bash
curl https://agent.example.com/.well-known/a2a/tasks/task-456
```

**Response**:
```json
{
  "task": {
    "id": "task-456",
    "type": "process",
    "state": "working",
    "progress": 0.45,
    "messages": [...]
  }
}
```

### Task Streaming

**GET** `/.well-known/a2a/tasks/{task_id}/stream`

Stream task updates via Server-Sent Events (SSE).

```bash
curl -N https://agent.example.com/.well-known/a2a/tasks/task-456/stream
```

**Response**:
```
event: state_change
data: {"state": "working", "progress": 0.2}

event: state_change
data: {"state": "working", "progress": 0.5}

event: state_change
data: {"state": "completed"}

event: message
data: {"role": "assistant", "parts": [...]}

event: artifact
data: {"type": "processed_data", "data": {...}}
```

## Long-Running Tasks

For tasks that take more than a few seconds:

```python
from agentweave import SecureAgent, capability
from agentweave.types import TaskResult, TaskProgress

class BatchProcessor(SecureAgent):
    @capability("batch_process")
    async def batch_process(self, items: list[dict]) -> TaskResult:
        """Process a large batch with progress updates."""

        total = len(items)
        processed = []

        for idx, item in enumerate(items):
            # Process item
            result = await self._process_item(item)
            processed.append(result)

            # Report progress
            await self.report_progress(
                TaskProgress(
                    state="working",
                    progress=idx / total,
                    message=f"Processed {idx}/{total} items"
                )
            )

        return TaskResult(
            status="completed",
            artifacts=[{
                "type": "batch_results",
                "data": {"items": processed}
            }]
        )
```

Callers can stream progress:

```python
async for progress in orchestrator.call_agent_streaming(
    target="spiffe://agentweave.io/agent/batch-processor/prod",
    task_type="batch_process",
    payload={"items": large_batch}
):
    print(f"Progress: {progress.progress * 100:.0f}% - {progress.message}")

# Final result
result = progress.result
```

## Message Parts

### Text Part

```json
{
  "type": "text",
  "text": "Process these records with validation enabled"
}
```

```python
TaskResult(
    artifacts=[{
        "type": "text",
        "text": "Processing completed successfully"
    }]
)
```

### Data Part

```json
{
  "type": "data",
  "data": {
    "records": [...],
    "metadata": {...}
  }
}
```

```python
TaskResult(
    artifacts=[{
        "type": "data",
        "data": {"results": processed_records}
    }]
)
```

### File Part

```json
{
  "type": "file",
  "uri": "s3://bucket/results.csv",
  "mime_type": "text/csv",
  "size": 1024000
}
```

```python
TaskResult(
    artifacts=[{
        "type": "file",
        "uri": "s3://results/output.csv",
        "mime_type": "text/csv"
    }]
)
```

### Tool Use (Advanced)

For agents that use tools:

```json
{
  "type": "tool_use",
  "tool_use_id": "tool-123",
  "name": "search_database",
  "input": {
    "query": "customer records",
    "limit": 100
  }
}
```

```python
# Agent using a tool
@capability("search")
async def search(self, query: str) -> TaskResult:
    # Invoke tool
    tool_result = await self.use_tool(
        "database_search",
        {"query": query}
    )

    return TaskResult(
        status="completed",
        artifacts=[{
            "type": "tool_result",
            "tool_use_id": tool_result.id,
            "result": tool_result.data
        }]
    )
```

## Error Handling

### Error Response

```json
{
  "jsonrpc": "2.0",
  "id": "req-123",
  "error": {
    "code": -32000,
    "message": "Task execution failed",
    "data": {
      "task": {
        "id": "task-456",
        "type": "process",
        "state": "failed",
        "error": {
          "type": "ValidationError",
          "message": "Invalid data format",
          "details": {...}
        }
      }
    }
  }
}
```

### In SDK

```python
from agentweave import SecureAgent, capability
from agentweave.types import TaskResult, TaskError

class Processor(SecureAgent):
    @capability("process")
    async def process(self, data: list[dict]) -> TaskResult:
        try:
            result = await self._process(data)
            return TaskResult(
                status="completed",
                artifacts=[{"type": "data", "data": result}]
            )
        except ValidationError as e:
            return TaskResult(
                status="failed",
                error=TaskError(
                    type="ValidationError",
                    message=str(e),
                    details={"field": e.field}
                )
            )
```

## Authentication

HVS SDK extends A2A with SPIFFE mTLS authentication.

**Agent Card Extension**:
```json
{
  "authentication": {
    "schemes": [
      {
        "type": "mtls",
        "description": "SPIFFE mTLS authentication"
      }
    ]
  },
  "extensions": {
    "spiffe_id": "spiffe://agentweave.io/agent/data-processor/prod",
    "allowed_callers": [
      "spiffe://agentweave.io/agent/*"
    ]
  }
}
```

All A2A requests must:
1. Use HTTPS with mTLS
2. Present valid SPIFFE SVID
3. Pass OPA authorization check

## Interoperability

### Calling Non-HVS Agents

The SDK can call any A2A-compliant agent:

```python
# Call Google ADK agent
result = await self.call_agent(
    target="https://adk-agent.example.com",
    task_type="summarize",
    payload={"text": "Long document..."},
    auth_scheme="oauth2",  # Instead of mTLS
    auth_token=oauth_token
)
```

### Being Called by Non-HVS Agents

Configure optional OAuth2 for external callers:

```yaml
server:
  authentication:
    schemes:
      - type: "mtls"        # For HVS agents
        required: true
      - type: "oauth2"      # For external agents
        required: false
        issuer: "https://auth.example.com"
        audience: "agentweaves"
```

```python
class Processor(SecureAgent):
    @capability("process")
    @requires_auth("mtls", "oauth2")  # Accept either
    async def process(self, data: list[dict]) -> TaskResult:
        # Check caller type
        if self.current_request_context.auth_type == "oauth2":
            # Different authorization logic
            pass
```

## Testing A2A Integration

### Manual Testing

```bash
# Get Agent Card
curl https://agent.example.com/.well-known/agent.json

# Submit task (with mTLS)
curl -X POST https://agent.example.com/.well-known/a2a/tasks/send \
  --cert client.crt \
  --key client.key \
  --cacert ca.crt \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-1",
    "method": "tasks.send",
    "params": {
      "task": {
        "type": "process",
        "messages": [{
          "role": "user",
          "parts": [{
            "type": "data",
            "data": {"test": "data"}
          }]
        }]
      }
    }
  }'
```

### Automated Testing

```python
import pytest
from agentweave.testing import A2ATestClient

@pytest.fixture
async def agent_client():
    async with A2ATestClient("http://localhost:8443") as client:
        yield client

async def test_process_capability(agent_client):
    # Get Agent Card
    card = await agent_client.get_agent_card()
    assert "process" in card.capability_names

    # Submit task
    result = await agent_client.send_task(
        task_type="process",
        payload={"data": [{"id": 1}]}
    )

    assert result.status == "completed"
    assert len(result.artifacts) > 0
```

## A2A vs gRPC

The SDK supports both A2A (default) and gRPC:

**A2A**:
- JSON-based (human-readable)
- HTTP/2 with Server-Sent Events
- Easy debugging with curl
- Interoperable with any framework

**gRPC**:
- Protobuf-based (efficient)
- Native streaming
- Better performance
- Requires .proto definitions

Choose A2A for interoperability, gRPC for performance.

## Reference Implementation

See [examples/multi_agent/](../examples/multi_agent/) for complete working examples of:
- Capability definition
- Agent-to-agent calls
- Long-running tasks with progress
- Error handling
- Discovery and invocation

## Specification Compliance

The HVS SDK implements:
- A2A Protocol v1.0
- Agent Card format
- Task lifecycle
- Message/Part/Artifact structures
- JSON-RPC 2.0 transport

**Extensions**:
- SPIFFE mTLS authentication
- OPA authorization
- Streaming progress updates

## Further Reading

- [A2A Specification](https://a2a-protocol.org/latest/)
- [A2A GitHub](https://github.com/a2aproject/A2A)
- [Quick Start Guide](quickstart.md)
- [Multi-Agent Example](../examples/multi_agent/)
