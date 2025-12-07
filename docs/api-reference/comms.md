---
layout: api
title: Communications Module API Reference
parent: API Reference
nav_order: 2
---

# Communications Module API Reference

The `agentweave.comms` module provides A2A (Agent-to-Agent) protocol implementation based on JSON-RPC 2.0, enabling secure, standardized communication between agents.

**Key Features:**
- JSON-RPC 2.0 based protocol
- Agent capability advertisement via Agent Cards
- Task lifecycle management
- Server-Sent Events (SSE) for streaming updates
- Discovery mechanisms for finding agents
- mTLS authentication integration

---

## A2A Protocol Components

### AgentCard

**Import:** `from agentweave.comms.a2a import AgentCard`

Agent Card for capability advertisement, served at `/.well-known/agent.json` endpoint.

#### Constructor

```python
AgentCard(
    name: str,
    description: str,
    url: str,
    version: str = "1.0.0",
    capabilities: list[Capability] = [],
    authentication: dict[str, Any] = {"schemes": []},
    extensions: dict[str, Any] = {}
)
```

**Parameters:**
- `name` (str): Agent name
- `description` (str): Agent description
- `url` (str): Agent base URL (must start with http:// or https://)
- `version` (str): Agent version (default: "1.0.0")
- `capabilities` (list[Capability]): List of agent capabilities
- `authentication` (dict): Authentication configuration
- `extensions` (dict): Custom extensions (e.g., SPIFFE ID)

**Raises:**
- `ValueError`: If URL format is invalid

#### Class Methods

##### from_config
```python
@classmethod
def from_config(
    cls,
    name: str,
    description: str,
    url: str,
    spiffe_id: str,
    version: str = "1.0.0",
    capabilities: list[Capability] | None = None,
    auth_schemes: list[AuthScheme] | None = None
) -> AgentCard
```
Create an AgentCard from agent configuration with automatic SPIFFE authentication setup.

**Parameters:**
- `name` (str): Agent name
- `description` (str): Agent description
- `url` (str): Agent base URL
- `spiffe_id` (str): SPIFFE ID for this agent
- `version` (str): Agent version
- `capabilities` (list[Capability], optional): List of capabilities
- `auth_schemes` (list[AuthScheme], optional): Authentication schemes (defaults to SPIFFE)

**Returns:** `AgentCard` instance

##### from_json
```python
@classmethod
def from_json(cls, json_str: str) -> AgentCard
```
Deserialize AgentCard from JSON string.

**Parameters:**
- `json_str` (str): JSON string representation

**Returns:** `AgentCard` instance

##### from_dict
```python
@classmethod
def from_dict(cls, data: dict[str, Any]) -> AgentCard
```
Create AgentCard from dictionary.

**Parameters:**
- `data` (dict): Dictionary representation

**Returns:** `AgentCard` instance

#### Instance Methods

##### to_json
```python
def to_json() -> str
```
Serialize AgentCard to JSON string.

**Returns:** JSON string representation

##### to_dict
```python
def to_dict() -> dict[str, Any]
```
Convert AgentCard to dictionary.

**Returns:** Dictionary representation suitable for JSON serialization

##### get_spiffe_id
```python
def get_spiffe_id() -> str | None
```
Extract SPIFFE ID from extensions.

**Returns:** SPIFFE ID if present, None otherwise

##### has_capability
```python
def has_capability(capability_name: str) -> bool
```
Check if agent has a specific capability.

**Parameters:**
- `capability_name` (str): Name of the capability to check

**Returns:** True if capability exists, False otherwise

##### get_capability
```python
def get_capability(capability_name: str) -> Capability | None
```
Get a capability by name.

**Parameters:**
- `capability_name` (str): Name of the capability to retrieve

**Returns:** Capability if found, None otherwise

#### Example

```python
from agentweave.comms.a2a import AgentCard, Capability

# Create agent card
card = AgentCard.from_config(
    name="search-agent",
    description="Semantic search agent",
    url="https://search.example.com",
    spiffe_id="spiffe://example.com/search-agent",
    capabilities=[
        Capability(
            name="search",
            description="Perform semantic search",
            input_modes=["application/json"],
            output_modes=["application/json"]
        )
    ]
)

# Serialize to JSON
json_str = card.to_json()

# Check capabilities
if card.has_capability("search"):
    cap = card.get_capability("search")
```

---

### Capability

**Import:** `from agentweave.comms.a2a import Capability`

Represents an agent capability as per A2A protocol.

#### Constructor

```python
Capability(
    name: str,
    description: str,
    input_modes: list[str] = ["application/json"],
    output_modes: list[str] = ["application/json"],
    parameters: dict[str, Any] | None = None
)
```

**Parameters:**
- `name` (str): Capability identifier
- `description` (str): Human-readable description
- `input_modes` (list[str]): Supported input content types
- `output_modes` (list[str]): Supported output content types
- `parameters` (dict, optional): JSON Schema for capability parameters

#### Methods

##### to_dict
```python
def to_dict() -> dict[str, Any]
```
Convert to dictionary for JSON serialization.

---

### AuthScheme

**Import:** `from agentweave.comms.a2a import AuthScheme`

Authentication scheme specification.

#### Constructor

```python
AuthScheme(
    type: str,
    description: str | None = None,
    metadata: dict[str, Any] = {}
)
```

**Parameters:**
- `type` (str): Auth type (e.g., "spiffe", "oauth2", "api_key")
- `description` (str, optional): Scheme description
- `metadata` (dict): Scheme-specific metadata

---

## A2AClient

**Import:** `from agentweave.comms.a2a import A2AClient`

Client for A2A protocol communication with remote agents.

### Constructor

```python
A2AClient(
    identity_provider=None,
    authz_enforcer=None,
    timeout: float = 30.0,
    max_retries: int = 3
)
```

**Parameters:**
- `identity_provider` (optional): Identity provider for mTLS
- `authz_enforcer` (optional): Authorization enforcer
- `timeout` (float): Default request timeout in seconds (default: 30.0)
- `max_retries` (int): Maximum number of retry attempts (default: 3)

### Methods

#### discover_agent
```python
async def discover_agent(url: str) -> AgentCard
```
Discover agent by fetching its agent card from `/.well-known/agent.json`.

**Parameters:**
- `url` (str): Base URL of the agent

**Returns:** `AgentCard` for the discovered agent

**Raises:**
- `DiscoveryError`: If agent card cannot be retrieved

#### send_task
```python
async def send_task(
    target_url: str,
    task_type: str,
    payload: dict[str, Any],
    messages: list | None = None,
    metadata: dict[str, Any] | None = None,
    timeout: float | None = None
) -> Task
```
Send a task to a remote agent.

**Parameters:**
- `target_url` (str): Base URL of target agent
- `task_type` (str): Type of task/capability to invoke
- `payload` (dict): Task payload data
- `messages` (list, optional): Optional message history
- `metadata` (dict, optional): Optional task metadata
- `timeout` (float, optional): Optional timeout override

**Returns:** `Task` with initial response

**Raises:**
- `TaskSubmissionError`: If task submission fails

#### get_task_status
```python
async def get_task_status(
    target_url: str,
    task_id: str,
    timeout: float | None = None
) -> Task
```
Get the status of a task.

**Parameters:**
- `target_url` (str): Base URL of target agent
- `task_id` (str): ID of the task
- `timeout` (float, optional): Optional timeout override

**Returns:** `Task` with current status

**Raises:**
- `TaskStatusError`: If status retrieval fails

#### stream_task_updates
```python
async def stream_task_updates(
    target_url: str,
    task_id: str,
    timeout: float | None = None
) -> AsyncIterator[Task]
```
Stream task updates via Server-Sent Events (SSE).

**Parameters:**
- `target_url` (str): Base URL of target agent
- `task_id` (str): ID of the task
- `timeout` (float, optional): Optional timeout override

**Yields:** `Task` updates as they occur

**Raises:**
- `TaskStatusError`: If streaming fails

#### poll_until_complete
```python
async def poll_until_complete(
    target_url: str,
    task_id: str,
    poll_interval: float = 1.0,
    max_wait: float | None = None
) -> Task
```
Poll task status until completion.

**Parameters:**
- `target_url` (str): Base URL of target agent
- `task_id` (str): ID of the task
- `poll_interval` (float): Seconds between polls (default: 1.0)
- `max_wait` (float, optional): Maximum seconds to wait (None = unlimited)

**Returns:** Completed task

**Raises:**
- `TaskStatusError`: If polling fails
- `TimeoutError`: If max_wait is exceeded

#### cancel_task
```python
async def cancel_task(
    target_url: str,
    task_id: str,
    timeout: float | None = None
) -> Task
```
Cancel a running task.

**Parameters:**
- `target_url` (str): Base URL of target agent
- `task_id` (str): ID of the task to cancel
- `timeout` (float, optional): Optional timeout override

**Returns:** Cancelled task

**Raises:**
- `TaskStatusError`: If cancellation fails

#### close
```python
async def close() -> None
```
Close HTTP client and cleanup resources.

### Context Manager Support

```python
async with A2AClient() as client:
    card = await client.discover_agent("https://agent.example.com")
    task = await client.send_task(url, "search", {"query": "example"})
```

### Example

```python
from agentweave.comms.a2a import A2AClient

async with A2AClient(timeout=30.0) as client:
    # Discover agent
    card = await client.discover_agent("https://search.example.com")
    print(f"Found agent: {card.name}")

    # Send task
    task = await client.send_task(
        target_url="https://search.example.com",
        task_type="search",
        payload={"query": "AI agents"}
    )

    # Poll until complete
    completed = await client.poll_until_complete(
        target_url="https://search.example.com",
        task_id=task.id,
        max_wait=60.0
    )

    print(f"Result: {completed.result}")
```

---

## A2AServer

**Import:** `from agentweave.comms.a2a import A2AServer`

FastAPI-based A2A protocol server with JSON-RPC endpoints and SSE streaming.

### Constructor

```python
A2AServer(
    agent_card: AgentCard,
    task_manager: TaskManager | None = None,
    authz_enforcer=None,
    enable_cors: bool = True
)
```

**Parameters:**
- `agent_card` (AgentCard): Agent card to serve
- `task_manager` (TaskManager, optional): Task manager instance (creates new if None)
- `authz_enforcer` (optional): Authorization enforcer
- `enable_cors` (bool): Enable CORS middleware (default: True)

### Properties

#### app
```python
@property
def app(self) -> FastAPI
```
Get FastAPI application instance.

**Returns:** FastAPI app

### Methods

#### register_task_handler
```python
def register_task_handler(
    task_type: str,
    handler: Callable[[Task], Awaitable[Task]]
) -> None
```
Register a handler for a task type.

**Parameters:**
- `task_type` (str): Type of task (matches capability name)
- `handler` (Callable): Async function that takes a Task and returns updated Task

#### get_app
```python
def get_app() -> FastAPI
```
Get FastAPI application instance.

**Returns:** FastAPI app for use with ASGI server

#### start
```python
async def start(host: str = "0.0.0.0", port: int = 8443) -> None
```
Start the server (convenience method, use uvicorn in production).

**Parameters:**
- `host` (str): Host to bind to (default: "0.0.0.0")
- `port` (int): Port to bind to (default: 8443)

### Endpoints

The server automatically provides these endpoints:

- `GET /.well-known/agent.json` - Serve agent card
- `POST /rpc` - Handle JSON-RPC 2.0 requests
  - `task.send` - Submit new task
  - `task.status` - Get task status
  - `task.cancel` - Cancel task
- `GET /tasks/{task_id}/stream` - Stream task updates via SSE
- `GET /health` - Health check endpoint

### Example

```python
from agentweave.comms.a2a import A2AServer, AgentCard
from agentweave.comms.a2a import Task, TaskState

# Create agent card
card = AgentCard.from_config(
    name="processor",
    description="Data processor agent",
    url="https://processor.example.com",
    spiffe_id="spiffe://example.com/processor"
)

# Create server
server = A2AServer(agent_card=card)

# Register task handler
async def process_handler(task: Task) -> Task:
    # Process task
    result = process_data(task.payload)

    task.mark_completed(result=result)
    return task

server.register_task_handler("process", process_handler)

# Get FastAPI app for use with uvicorn
app = server.get_app()

# Run with: uvicorn main:app --host 0.0.0.0 --port 8443
```

---

## Task

**Import:** `from agentweave.comms.a2a import Task`

A2A Task representing a unit of work with lifecycle management.

### Constructor

```python
Task(
    id: str = <auto-generated>,
    type: str,
    state: TaskState = TaskState.PENDING,
    payload: dict[str, Any] = {},
    messages: list[Message] = [],
    result: Any | None = None,
    artifacts: list[Artifact] = [],
    error: str | None = None,
    created_at: datetime = <now>,
    updated_at: datetime = <now>,
    metadata: dict[str, Any] = {}
)
```

**Parameters:**
- `id` (str): Unique task ID (auto-generated if not provided)
- `type` (str): Task type/capability name
- `state` (TaskState): Current task state (default: PENDING)
- `payload` (dict): Task input payload
- `messages` (list[Message]): Message history
- `result` (Any, optional): Task result
- `artifacts` (list[Artifact]): Output artifacts
- `error` (str, optional): Error message if failed
- `created_at` (datetime): Task creation timestamp
- `updated_at` (datetime): Last update timestamp
- `metadata` (dict): Additional task metadata

### Methods

#### update_state
```python
def update_state(new_state: TaskState, error: str | None = None) -> None
```
Update task state and timestamp.

**Parameters:**
- `new_state` (TaskState): New task state
- `error` (str, optional): Error message if state is FAILED

#### add_message
```python
def add_message(role: str, parts: list[MessagePart]) -> None
```
Add a message to the task.

**Parameters:**
- `role` (str): Message role (user, assistant, system)
- `parts` (list[MessagePart]): Message parts

#### add_artifact
```python
def add_artifact(
    artifact_type: str,
    data: Any,
    metadata: dict[str, Any] | None = None
) -> None
```
Add an artifact to the task.

**Parameters:**
- `artifact_type` (str): Type of artifact
- `data` (Any): Artifact data
- `metadata` (dict, optional): Optional metadata

#### mark_running
```python
def mark_running() -> None
```
Mark task as running.

#### mark_completed
```python
def mark_completed(result: Any = None) -> None
```
Mark task as completed.

**Parameters:**
- `result` (Any, optional): Task result

#### mark_failed
```python
def mark_failed(error: str) -> None
```
Mark task as failed.

**Parameters:**
- `error` (str): Error message

#### mark_cancelled
```python
def mark_cancelled() -> None
```
Mark task as cancelled.

#### is_terminal
```python
def is_terminal() -> bool
```
Check if task is in a terminal state.

**Returns:** True if state is COMPLETED, FAILED, or CANCELLED

#### to_jsonrpc
```python
def to_jsonrpc(method: str = "task.send") -> dict[str, Any]
```
Convert task to JSON-RPC 2.0 request format.

**Parameters:**
- `method` (str): JSON-RPC method name (default: "task.send")

**Returns:** JSON-RPC request dictionary

#### to_dict
```python
def to_dict() -> dict[str, Any]
```
Convert task to dictionary.

**Returns:** Dictionary representation

---

## TaskState

**Import:** `from agentweave.comms.a2a import TaskState`

Task lifecycle states enumeration.

```python
class TaskState(str, Enum):
    PENDING = "pending"      # Task created, not started
    RUNNING = "running"      # Task is being processed
    COMPLETED = "completed"  # Task completed successfully
    FAILED = "failed"        # Task failed with error
    CANCELLED = "cancelled"  # Task was cancelled
```

### Method

```python
def is_terminal() -> bool
```
Check if this is a terminal state.

**Returns:** True for COMPLETED, FAILED, CANCELLED

---

## TaskManager

**Import:** `from agentweave.comms.a2a import TaskManager`

Manages task lifecycle and status tracking for long-running tasks.

### Constructor

```python
TaskManager()
```

### Methods

#### create_task
```python
async def create_task(
    task_type: str,
    payload: dict[str, Any] | None = None,
    messages: list[Message] | None = None,
    metadata: dict[str, Any] | None = None
) -> Task
```
Create a new task.

**Parameters:**
- `task_type` (str): Type of task
- `payload` (dict, optional): Task payload
- `messages` (list[Message], optional): Initial messages
- `metadata` (dict, optional): Task metadata

**Returns:** Created task

#### get_task
```python
async def get_task(task_id: str) -> Task | None
```
Retrieve a task by ID.

**Parameters:**
- `task_id` (str): Task ID

**Returns:** Task if found, None otherwise

#### update_task
```python
async def update_task(
    task_id: str,
    state: TaskState | None = None,
    result: Any | None = None,
    error: str | None = None
) -> Task | None
```
Update task state and data.

**Parameters:**
- `task_id` (str): Task ID
- `state` (TaskState, optional): New state
- `result` (Any, optional): Task result
- `error` (str, optional): Error message

**Returns:** Updated task if found, None otherwise

#### delete_task
```python
async def delete_task(task_id: str) -> bool
```
Delete a task.

**Parameters:**
- `task_id` (str): Task ID

**Returns:** True if deleted, False if not found

#### list_tasks
```python
async def list_tasks(
    state: TaskState | None = None,
    task_type: str | None = None
) -> list[Task]
```
List tasks with optional filtering.

**Parameters:**
- `state` (TaskState, optional): Filter by state
- `task_type` (str, optional): Filter by type

**Returns:** List of matching tasks

#### wait_for_completion
```python
async def wait_for_completion(
    task_id: str,
    timeout: float | None = None
) -> Task | None
```
Wait for a task to reach a terminal state.

**Parameters:**
- `task_id` (str): Task ID
- `timeout` (float, optional): Optional timeout in seconds

**Returns:** Completed task if found, None otherwise

**Raises:**
- `asyncio.TimeoutError`: If timeout is reached

#### cleanup_completed_tasks
```python
async def cleanup_completed_tasks(max_age_seconds: int = 3600) -> int
```
Clean up old completed tasks.

**Parameters:**
- `max_age_seconds` (int): Maximum age for completed tasks (default: 3600)

**Returns:** Number of tasks cleaned up

---

## Discovery

### DiscoveryClient

**Import:** `from agentweave.comms import DiscoveryClient`

Client for discovering agents via well-known endpoints with caching.

#### Constructor

```python
DiscoveryClient(
    cache_ttl: int = 300,
    timeout: float = 10.0,
    enable_cache: bool = True
)
```

**Parameters:**
- `cache_ttl` (int): Cache TTL in seconds (default: 300)
- `timeout` (float): Request timeout in seconds (default: 10.0)
- `enable_cache` (bool): Enable agent card caching (default: True)

#### Methods

##### discover_agent
```python
async def discover_agent(
    url: str,
    force_refresh: bool = False
) -> AgentCard
```
Discover agent by URL.

**Parameters:**
- `url` (str): Base URL of the agent
- `force_refresh` (bool): Force cache refresh (default: False)

**Returns:** `AgentCard` for the discovered agent

**Raises:**
- `DiscoveryError`: If discovery fails

##### discover_by_spiffe_id
```python
async def discover_by_spiffe_id(
    spiffe_id: str,
    service_mesh_resolver: callable | None = None
) -> AgentCard
```
Discover agent by SPIFFE ID using service mesh resolver.

**Parameters:**
- `spiffe_id` (str): SPIFFE ID of the agent
- `service_mesh_resolver` (callable, optional): Function to resolve SPIFFE ID to URL

**Returns:** `AgentCard` for the agent

**Raises:**
- `DiscoveryError`: If discovery fails
- `ValueError`: If service_mesh_resolver not provided

##### discover_multiple
```python
async def discover_multiple(
    urls: list[str],
    ignore_errors: bool = False
) -> list[AgentCard]
```
Discover multiple agents concurrently.

**Parameters:**
- `urls` (list[str]): List of agent URLs
- `ignore_errors` (bool): Continue on errors (default: False)

**Returns:** List of discovered agent cards

**Raises:**
- `DiscoveryError`: If any discovery fails and ignore_errors=False

##### verify_agent_capability
```python
async def verify_agent_capability(
    url: str,
    capability_name: str
) -> bool
```
Verify that an agent has a specific capability.

**Parameters:**
- `url` (str): Agent URL
- `capability_name` (str): Name of capability to check

**Returns:** True if agent has capability, False otherwise

**Raises:**
- `DiscoveryError`: If discovery fails

##### find_agents_with_capability
```python
async def find_agents_with_capability(
    urls: list[str],
    capability_name: str
) -> list[AgentCard]
```
Find all agents with a specific capability.

**Parameters:**
- `urls` (list[str]): List of agent URLs to check
- `capability_name` (str): Capability to search for

**Returns:** List of agent cards with the capability

##### clear_cache
```python
async def clear_cache(url: str | None = None) -> None
```
Clear agent card cache.

**Parameters:**
- `url` (str, optional): Specific URL to clear (None = clear all)

##### get_cache_stats
```python
def get_cache_stats() -> dict[str, int]
```
Get cache statistics.

**Returns:** Dictionary with cache stats (total_entries, expired_entries, active_entries)

##### close
```python
async def close() -> None
```
Close HTTP client and cleanup resources.

#### Example

```python
from agentweave.comms import DiscoveryClient

async with DiscoveryClient(cache_ttl=300) as discovery:
    # Discover single agent
    card = await discovery.discover_agent("https://agent.example.com")

    # Find agents with specific capability
    agents = await discovery.find_agents_with_capability(
        urls=["https://agent1.com", "https://agent2.com"],
        capability_name="search"
    )

    # Get cache stats
    stats = discovery.get_cache_stats()
```

---

## Exceptions

### A2AClientError
Base exception for A2A client errors.

### TaskSubmissionError
Error submitting task to remote agent.

### TaskStatusError
Error retrieving task status.

### DiscoveryError
Error discovering agent card.

---

## Complete Example

```python
from agentweave.comms.a2a import A2AClient, A2AServer, AgentCard, Task, TaskState
from agentweave.comms import DiscoveryClient

# Server side
card = AgentCard.from_config(
    name="data-processor",
    description="Process data",
    url="https://processor.example.com",
    spiffe_id="spiffe://example.com/processor"
)

server = A2AServer(agent_card=card)

async def process_data_handler(task: Task) -> Task:
    data = task.payload.get("data")
    result = {"processed": data.upper()}
    task.mark_completed(result=result)
    return task

server.register_task_handler("process", process_data_handler)
app = server.get_app()  # Use with uvicorn

# Client side
async with A2AClient() as client:
    # Discover agent
    card = await client.discover_agent("https://processor.example.com")

    # Send task
    task = await client.send_task(
        target_url="https://processor.example.com",
        task_type="process",
        payload={"data": "hello world"}
    )

    # Wait for completion
    completed = await client.poll_until_complete(
        target_url="https://processor.example.com",
        task_id=task.id
    )

    print(f"Result: {completed.result}")
```
