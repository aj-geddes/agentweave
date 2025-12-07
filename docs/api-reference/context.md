---
layout: api
title: Context Module
parent: API Reference
nav_order: 4
---

# Context Module

The context module (`agentweave.context`) provides request context management for tracking caller identity, task IDs, and request metadata across async calls.

## Overview

The context module uses Python's `contextvars` to propagate request information through async call chains. This enables:

- **Caller identity tracking** - Know which agent made the request
- **Task correlation** - Track requests across distributed operations
- **Metadata propagation** - Pass additional context through the call chain
- **Authorization context** - Provide context for OPA policy decisions

## Classes

### RequestContext

**Dataclass** containing context information for an agent request.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `caller_id` | `str` | *required* | SPIFFE ID of the calling agent |
| `task_id` | `str` | *required* | Unique identifier for this task |
| `timestamp` | `datetime` | `datetime.utcnow()` | When the request was initiated |
| `metadata` | `dict` | `{}` | Additional context metadata |

#### Constructor

```python
RequestContext(
    caller_id: str,
    task_id: str,
    timestamp: datetime = datetime.utcnow(),
    metadata: dict = {}
)
```

**Example:**

```python
from agentweave.context import RequestContext
from datetime import datetime
import uuid

context = RequestContext(
    caller_id="spiffe://agentweave.io/agent/caller",
    task_id=str(uuid.uuid4()),
    timestamp=datetime.utcnow(),
    metadata={"priority": "high"}
)
```

#### Class Methods

##### create

```python
@classmethod
def create(cls, caller_id: str, metadata: Optional[dict] = None) -> RequestContext
```

Create a new request context with automatically generated task ID.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `caller_id` | `str` | *required* | SPIFFE ID of the calling agent |
| `metadata` | `dict` | `None` | Additional context metadata |

**Returns:** `RequestContext` - New context with generated UUID task_id and current timestamp

**Example:**

```python
from agentweave.context import RequestContext

# Simple context
context = RequestContext.create(
    caller_id="spiffe://agentweave.io/agent/caller"
)

# With metadata
context = RequestContext.create(
    caller_id="spiffe://agentweave.io/agent/caller",
    metadata={
        "priority": "high",
        "source": "api",
        "user_id": "user-123"
    }
)

print(context.task_id)  # e.g., "550e8400-e29b-41d4-a716-446655440000"
print(context.timestamp)  # e.g., 2024-01-15 10:30:45.123456
```

---

## Functions

### get_current_context

```python
def get_current_context() -> Optional[RequestContext]
```

Get the current request context.

This function retrieves the context for the current async task. Returns `None` if no context has been set.

**Returns:** `Optional[RequestContext]` - The current RequestContext if one is set, None otherwise

**Example:**

```python
from agentweave.context import get_current_context

async def my_capability_handler(self, data: dict) -> dict:
    context = get_current_context()

    if context:
        print(f"Called by: {context.caller_id}")
        print(f"Task ID: {context.task_id}")
        print(f"Metadata: {context.metadata}")
    else:
        print("No context available")

    return {"status": "ok"}
```

**Usage in Decorators:**

The context is automatically available in `@capability` decorated methods:

```python
from agentweave import SecureAgent, capability
from agentweave.context import get_current_context

class MyAgent(SecureAgent):
    @capability("process_data")
    async def process_data(self, data: dict) -> dict:
        context = get_current_context()

        # Use caller ID for logging
        self.logger.info(f"Processing data for {context.caller_id}")

        # Add task ID to response for correlation
        return {
            "status": "processed",
            "task_id": context.task_id
        }
```

---

### set_current_context

```python
def set_current_context(context: Optional[RequestContext]) -> None
```

Set the current request context.

This function sets the context for the current async task. Pass `None` to clear the context.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `context` | `Optional[RequestContext]` | The RequestContext to set, or None to clear |

**Note:** This function is primarily used internally by the SDK. You typically don't need to call it directly.

**Example:**

```python
from agentweave.context import RequestContext, set_current_context

# Set context (typically done by SDK)
context = RequestContext.create(
    caller_id="spiffe://agentweave.io/agent/caller"
)
set_current_context(context)

# Your code runs with this context
await some_capability()

# Clear context
set_current_context(None)
```

**Internal Usage:**

The SDK uses this function when handling requests:

```python
async def handle_request(self, caller_id: str, task_type: str, payload: dict):
    # Create and set context
    context = RequestContext.create(
        caller_id=caller_id,
        metadata={"task_type": task_type}
    )
    set_current_context(context)

    try:
        # Call handler with context available
        result = await self._capabilities[task_type]["handler"](**payload)
        return result
    finally:
        # Clear context
        set_current_context(None)
```

---

## Usage Patterns

### 1. Accessing Caller Identity

```python
from agentweave import SecureAgent, capability
from agentweave.context import get_current_context

class DataAgent(SecureAgent):
    @capability("get_user_data")
    async def get_user_data(self, user_id: str) -> dict:
        context = get_current_context()

        # Log who is accessing the data
        self.logger.info(
            f"Agent {context.caller_id} accessing data for user {user_id}"
        )

        return {"user_id": user_id, "data": [...]}
```

### 2. Propagating Context Metadata

```python
from agentweave import SecureAgent, capability
from agentweave.context import get_current_context

class OrchestratorAgent(SecureAgent):
    @capability("orchestrate")
    async def orchestrate(self, workflow: str) -> dict:
        context = get_current_context()

        # Pass original caller info to downstream agents
        result1 = await self.call_agent(
            target="spiffe://agentweave.io/agent/worker-1",
            task_type="process",
            payload={
                "data": "...",
                "original_caller": context.caller_id,
                "task_id": context.task_id
            }
        )

        return {"status": "completed"}
```

### 3. Conditional Logic Based on Caller

```python
from agentweave import SecureAgent, capability
from agentweave.context import get_current_context

class DataAgent(SecureAgent):
    @capability("query_data")
    async def query_data(self, query: str) -> dict:
        context = get_current_context()

        # Different behavior based on caller
        if "admin" in context.caller_id:
            # Admins get full results
            return await self._query_full(query)
        else:
            # Others get filtered results
            return await self._query_filtered(query)
```

### 4. Audit Logging with Context

```python
from agentweave import SecureAgent, capability
from agentweave.context import get_current_context
import logging

class AuditedAgent(SecureAgent):
    @capability("sensitive_operation")
    async def sensitive_operation(self, action: str) -> dict:
        context = get_current_context()

        # Detailed audit log
        logging.warning(
            "Sensitive operation executed",
            extra={
                "caller": context.caller_id,
                "task_id": context.task_id,
                "action": action,
                "timestamp": context.timestamp.isoformat()
            }
        )

        result = await self._perform_operation(action)
        return result
```

### 5. Error Context

```python
from agentweave import SecureAgent, capability
from agentweave.context import get_current_context

class ResilientAgent(SecureAgent):
    @capability("risky_operation")
    async def risky_operation(self, data: dict) -> dict:
        context = get_current_context()

        try:
            return await self._do_risky_thing(data)
        except Exception as e:
            # Include context in error for troubleshooting
            self.logger.error(
                f"Operation failed for task {context.task_id} "
                f"from caller {context.caller_id}: {e}"
            )
            raise
```

---

## Context Lifecycle

### Request Flow

```
1. Agent receives A2A request
   ↓
2. SDK creates RequestContext with caller's SPIFFE ID
   ↓
3. SDK calls set_current_context(context)
   ↓
4. Decorators can access context via get_current_context()
   ↓
5. Capability handler executes with context available
   ↓
6. SDK calls set_current_context(None) to clean up
```

### Example Flow

```python
# 1. Request arrives at agent
# Caller: spiffe://agentweave.io/agent/caller
# Task: "search"
# Payload: {"query": "example"}

# 2. SDK creates context
context = RequestContext.create(
    caller_id="spiffe://agentweave.io/agent/caller",
    metadata={"task_type": "search"}
)

# 3. SDK sets context
set_current_context(context)

# 4. Your handler runs with context
@capability("search")
async def search(self, query: str) -> dict:
    ctx = get_current_context()
    print(f"Caller: {ctx.caller_id}")  # spiffe://agentweave.io/agent/caller
    print(f"Task: {ctx.task_id}")      # 550e8400-e29b-41d4-a716-446655440000
    return {"results": [...]}

# 5. SDK clears context
set_current_context(None)
```

---

## Integration with Authorization

The request context is used by OPA for authorization decisions:

```python
# In @capability decorator
context = get_current_context()

decision = await self._authz.check_inbound(
    caller_id=context.caller_id,  # From context
    action=capability_name,
    context={"metadata": context.metadata}  # Additional context for OPA
)
```

**OPA Policy Example:**

```rego
package agentweave.authz

default allow = false

allow {
    # Access context
    input.caller_id == "spiffe://agentweave.io/agent/trusted-agent"
    input.action == "sensitive_operation"

    # Access metadata
    input.context.metadata.priority == "high"
}
```

---

## Complete Example

```python
from agentweave import SecureAgent, capability, requires_peer
from agentweave.context import get_current_context, RequestContext
import logging

logger = logging.getLogger(__name__)


class WorkflowAgent(SecureAgent):
    """Agent that orchestrates a multi-step workflow."""

    @capability("execute_workflow", description="Execute a multi-step workflow")
    @requires_peer("spiffe://agentweave.io/agent/*")
    async def execute_workflow(self, workflow_id: str, steps: list) -> dict:
        context = get_current_context()

        logger.info(
            f"Starting workflow {workflow_id} for {context.caller_id}",
            extra={
                "task_id": context.task_id,
                "workflow_id": workflow_id,
                "step_count": len(steps)
            }
        )

        results = []
        for i, step in enumerate(steps):
            logger.debug(
                f"Executing step {i+1}/{len(steps)}",
                extra={"task_id": context.task_id, "step": step}
            )

            # Call worker agent with context propagation
            result = await self.call_agent(
                target=step["agent"],
                task_type=step["capability"],
                payload={
                    **step["payload"],
                    # Propagate original context
                    "_original_caller": context.caller_id,
                    "_original_task_id": context.task_id
                }
            )

            results.append(result)

        logger.info(
            f"Workflow {workflow_id} completed",
            extra={
                "task_id": context.task_id,
                "result_count": len(results)
            }
        )

        return {
            "workflow_id": workflow_id,
            "task_id": context.task_id,
            "results": results,
            "status": "completed"
        }


if __name__ == "__main__":
    agent = WorkflowAgent.from_config("config.yaml")
    agent.run()
```

---

## See Also

- [Agent Module](agent.md) - Agent classes and request handling
- [Decorators Module](decorators.md) - Security decorators that use context
- [A2A Protocol](../a2a-protocol.md) - Request/response protocol details
