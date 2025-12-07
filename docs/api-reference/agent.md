---
layout: api
title: Agent Module
parent: API Reference
nav_order: 2
---

# Agent Module

The agent module (`agentweave.agent`) provides the core classes for building secure agents with built-in identity verification, authorization, and A2A communication.

## Classes

### AgentConfig

**Dataclass** for agent configuration (simplified legacy version).

**Note:** For production use, prefer the comprehensive `AgentConfig` from `agentweave.config` which uses Pydantic for validation.

#### Fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `name` | `str` | *required* | Unique agent name |
| `trust_domain` | `str` | *required* | SPIFFE trust domain |
| `description` | `str` | `None` | Optional agent description |
| `identity_provider` | `str` | `"spiffe"` | Identity provider type |
| `authz_provider` | `str` | `"opa"` | Authorization provider type |
| `spiffe_endpoint` | `str` | `None` | SPIFFE Workload API endpoint |
| `opa_endpoint` | `str` | `"http://localhost:8181"` | OPA server endpoint |
| `server_host` | `str` | `"0.0.0.0"` | Server bind host |
| `server_port` | `int` | `8443` | Server port |

#### Methods

##### from_file

```python
@classmethod
def from_file(cls, path: str) -> AgentConfig
```

Load configuration from a YAML file.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `path` | `str` | Path to YAML configuration file |

**Returns:** `AgentConfig` - Initialized configuration instance

**Example:**

```python
config = AgentConfig.from_file("config.yaml")
```

**YAML Format:**

```yaml
agent:
  name: my-agent
  trust_domain: agentweave.io
  description: My secure agent

identity:
  provider: spiffe
  spiffe_endpoint: unix:///run/spire/sockets/agent.sock

authorization:
  provider: opa
  opa_endpoint: http://localhost:8181

server:
  host: 0.0.0.0
  port: 8443
```

##### from_dict

```python
@classmethod
def from_dict(cls, data: dict) -> AgentConfig
```

Create configuration from a dictionary.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `data` | `dict` | Configuration dictionary |

**Returns:** `AgentConfig` - Initialized configuration instance

**Example:**

```python
config = AgentConfig.from_dict({
    "name": "my-agent",
    "trust_domain": "agentweave.io",
    "server_port": 8443
})
```

---

## BaseAgent

**Abstract base class** for all secure agents.

This class provides core functionality including:
- Configuration loading and validation
- Identity provider setup (SPIFFE or mTLS)
- Authorization provider setup (OPA)
- Transport layer with connection pool
- Lifecycle management (start, stop, health checks)

Subclasses must implement `register_capabilities()` to define their agent-specific capabilities.

### Constructor

```python
def __init__(
    self,
    config: Optional[AgentConfig] = None,
    identity: Optional[Any] = None,
    authz: Optional[Any] = None,
    transport: Optional[Any] = None
)
```

Initialize the base agent.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `config` | `AgentConfig` | Agent configuration |
| `identity` | `Any` | Identity provider (for testing/dependency injection) |
| `authz` | `Any` | Authorization enforcer (for testing/dependency injection) |
| `transport` | `Any` | Transport layer (for testing/dependency injection) |

**Example:**

```python
# With config
config = AgentConfig.from_file("config.yaml")
agent = MyAgent(config=config)

# With dependency injection (testing)
agent = MyAgent(
    config=config,
    identity=mock_identity,
    authz=mock_authz
)
```

### Class Methods

#### from_config

```python
@classmethod
def from_config(cls, config_path: str) -> BaseAgent
```

Create agent from a configuration file.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `config_path` | `str` | Path to YAML configuration file |

**Returns:** `BaseAgent` - Initialized agent instance

**Example:**

```python
agent = MyAgent.from_config("config.yaml")
```

#### from_dict

```python
@classmethod
def from_dict(cls, config_dict: dict) -> BaseAgent
```

Create agent from a configuration dictionary.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `config_dict` | `dict` | Configuration dictionary |

**Returns:** `BaseAgent` - Initialized agent instance

**Example:**

```python
agent = MyAgent.from_dict({
    "name": "my-agent",
    "trust_domain": "agentweave.io"
})
```

### Instance Methods

#### get_spiffe_id

```python
def get_spiffe_id(self) -> str
```

Get this agent's SPIFFE ID.

**Returns:** `str` - The agent's SPIFFE ID in the format `spiffe://{trust_domain}/agent/{name}`

**Example:**

```python
spiffe_id = agent.get_spiffe_id()
# Returns: "spiffe://agentweave.io/agent/my-agent"
```

#### start

```python
async def start(self) -> None
```

Start the agent.

This method:
1. Validates identity is available
2. Starts the A2A server
3. Registers capabilities
4. Marks agent as running

**Raises:**

| Exception | Description |
|-----------|-------------|
| `RuntimeError` | If identity cannot be verified |

**Example:**

```python
await agent.start()
```

#### stop

```python
async def stop(self) -> None
```

Stop the agent gracefully.

This method:
1. Stops accepting new requests
2. Waits for in-flight requests to complete
3. Closes connection pool
4. Shuts down server

**Example:**

```python
await agent.stop()
```

#### health_check

```python
async def health_check(self) -> dict[str, Any]
```

Perform a health check.

**Returns:** `dict[str, Any]` - Health status dictionary

**Response Format:**

```python
{
    "status": "healthy" | "stopped" | "degraded",
    "spiffe_id": "spiffe://agentweave.io/agent/my-agent",
    "components": {
        "identity": "healthy" | "unhealthy: {error}",
        "authorization": "healthy",
        "server": "running" | "starting"
    }
}
```

**Example:**

```python
health = await agent.health_check()
if health["status"] == "healthy":
    print("Agent is healthy")
```

#### run

```python
def run(self) -> None
```

Run the agent (blocking).

This is a convenience method for running the agent as a standalone application. It handles the async event loop and graceful shutdown.

**Example:**

```python
if __name__ == "__main__":
    agent = MyAgent.from_config("config.yaml")
    agent.run()  # Blocks until SIGINT/SIGTERM
```

### Abstract Methods

#### register_capabilities

```python
@abstractmethod
async def register_capabilities(self) -> None
```

Register agent capabilities.

Subclasses must implement this method to define their available capabilities. For `SecureAgent`, this is automatic via decorator scanning.

**Example:**

```python
class MyAgent(BaseAgent):
    async def register_capabilities(self) -> None:
        # Manually register capabilities
        self._capabilities["search"] = {
            "name": "search",
            "description": "Search the database",
            "handler": self.search
        }
```

### Context Manager Support

BaseAgent supports async context manager protocol:

```python
async with MyAgent.from_config("config.yaml") as agent:
    # Agent is started
    result = await agent.call_agent(...)
    # Agent is automatically stopped on exit
```

**Methods:**

- `__aenter__(self)` - Start the agent
- `__aexit__(self, exc_type, exc_val, exc_tb)` - Stop the agent

---

## SecureAgent

**Concrete agent class** with automatic capability registration from decorated methods.

This class extends `BaseAgent` to provide:
- Automatic capability discovery from `@capability` decorated methods
- Built-in A2A server for handling requests
- Simplified agent-to-agent communication via `call_agent()`
- Context manager support for easy lifecycle management

### Constructor

```python
def __init__(
    self,
    config: Optional[AgentConfig] = None,
    identity: Optional[Any] = None,
    authz: Optional[Any] = None,
    transport: Optional[Any] = None
)
```

Initialize the secure agent. Parameters are the same as `BaseAgent`.

**Example:**

```python
class DataSearchAgent(SecureAgent):
    @capability("search", description="Search the database")
    @requires_peer("spiffe://agentweave.io/agent/*")
    async def search(self, query: str) -> dict:
        return {"results": [...]}

agent = DataSearchAgent.from_config("config.yaml")
```

### Methods

#### register_capabilities

```python
async def register_capabilities(self) -> None
```

Automatically register capabilities from decorated methods.

This method scans the instance for methods decorated with `@capability` and registers them as available capabilities.

**Note:** This method is called automatically by `start()`. You don't need to call it manually.

**Example:**

The following capabilities are automatically registered:

```python
class MyAgent(SecureAgent):
    @capability("search")
    async def search(self, query: str) -> dict:
        return {"results": [...]}

    @capability("process")
    async def process(self, data: dict) -> dict:
        return {"status": "processed"}
```

#### call_agent

```python
async def call_agent(
    self,
    target: str,
    task_type: str,
    payload: dict,
    timeout: float = 30.0
) -> Any
```

Call another agent.

This method handles the complete A2A call flow:
1. Authorization check (outbound policy)
2. Secure channel establishment
3. Task submission via A2A protocol
4. Result retrieval

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target` | `str` | *required* | Target agent's SPIFFE ID |
| `task_type` | `str` | *required* | The capability/task type to invoke |
| `payload` | `dict` | *required* | Request payload |
| `timeout` | `float` | `30.0` | Request timeout in seconds |

**Returns:** `Any` - Task result from the target agent

**Raises:**

| Exception | Description |
|-----------|-------------|
| `PermissionError` | If authorization fails |
| `TimeoutError` | If request times out |
| `ConnectionError` | If unable to reach target |

**Example:**

```python
# Call another agent
result = await agent.call_agent(
    target="spiffe://agentweave.io/agent/data-processor",
    task_type="process",
    payload={"data": [1, 2, 3]},
    timeout=60.0
)

print(f"Result: {result}")
```

#### handle_request

```python
async def handle_request(
    self,
    caller_id: str,
    task_type: str,
    payload: dict
) -> Any
```

Handle an incoming A2A request.

This method is called by the A2A server when a request arrives. It sets up the request context and dispatches to the appropriate capability handler.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `caller_id` | `str` | SPIFFE ID of the calling agent |
| `task_type` | `str` | The capability being invoked |
| `payload` | `dict` | Request payload |

**Returns:** `Any` - Result from the capability handler

**Raises:**

| Exception | Description |
|-----------|-------------|
| `ValueError` | If capability not found |
| `PermissionError` | If authorization fails |

**Note:** This method is called internally by the A2A server. You typically don't call it directly.

**Example:**

```python
# Called internally by A2A server
result = await agent.handle_request(
    caller_id="spiffe://agentweave.io/agent/caller",
    task_type="search",
    payload={"query": "example"}
)
```

#### get_capabilities

```python
def get_capabilities(self) -> list[dict]
```

Get list of registered capabilities.

**Returns:** `list[dict]` - List of capability metadata dictionaries

**Response Format:**

```python
[
    {
        "name": "search",
        "description": "Search the database",
        "requires_peer_patterns": ["spiffe://agentweave.io/agent/*"],
        "audit_level": None
    },
    {
        "name": "delete_data",
        "description": "Delete sensitive data",
        "requires_peer_patterns": ["spiffe://agentweave.io/agent/admin-*"],
        "audit_level": "warning"
    }
]
```

**Example:**

```python
capabilities = agent.get_capabilities()
for cap in capabilities:
    print(f"{cap['name']}: {cap['description']}")
```

## Complete Example

```python
from agentweave import SecureAgent, capability, requires_peer, audit_log

class DataManagementAgent(SecureAgent):
    """Agent for managing sensitive data."""

    @capability("search", description="Search the database")
    @requires_peer("spiffe://agentweave.io/agent/*")
    async def search(self, query: str) -> dict:
        """Search for data matching the query."""
        results = await self._search_database(query)
        return {"results": results, "count": len(results)}

    @capability("delete_data", description="Delete sensitive data")
    @requires_peer("spiffe://agentweave.io/agent/admin-*")
    @audit_log(level="warning")
    async def delete_data(self, id: str) -> dict:
        """Delete data by ID. Only admin agents can call this."""
        await self._delete_from_database(id)
        return {"deleted": id, "status": "success"}

    async def _search_database(self, query: str) -> list:
        # Implementation
        return []

    async def _delete_from_database(self, id: str) -> None:
        # Implementation
        pass

# Create and run agent
if __name__ == "__main__":
    agent = DataManagementAgent.from_config("config.yaml")
    agent.run()
```

## See Also

- [Decorators Module](decorators.md) - Security decorators for capabilities
- [Context Module](context.md) - Request context management
- [Configuration Module](config.md) - Comprehensive configuration reference
