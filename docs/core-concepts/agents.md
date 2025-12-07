---
layout: page
title: Understanding Agents
description: Agent classes, lifecycle, capabilities, and configuration in AgentWeave
permalink: /core-concepts/agents/
parent: Core Concepts
nav_order: 2
---

# Understanding Agents

Agents are the fundamental building blocks of AgentWeave. This document explains what agents are, how they work, and how to build them.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## What is a SecureAgent?

A **SecureAgent** is a Python class that represents an autonomous AI agent with built-in security. It:

- Has a **cryptographic identity** (SPIFFE ID)
- Exposes **capabilities** (things it can do)
- Communicates with other agents using the **A2A protocol**
- Enforces **authorization policies** automatically
- Handles **lifecycle events** (startup, shutdown, health checks)

Think of an agent as a secure microservice specifically designed for AI workloads.

### SecureAgent Example

```python
from agentweave import SecureAgent, capability
from agentweave.types import TaskResult

class SearchAgent(SecureAgent):
    """Agent that searches a data store."""

    async def on_start(self):
        """Called when agent starts."""
        self._database = await connect_to_database()
        self.logger.info("SearchAgent started")

    @capability("search")
    async def search(self, query: str, max_results: int = 10) -> TaskResult:
        """
        Search for documents matching the query.

        Args:
            query: Search query string
            max_results: Maximum number of results to return

        Returns:
            TaskResult with search results as artifacts
        """
        results = await self._database.search(query, limit=max_results)

        return TaskResult(
            status="completed",
            artifacts=[{
                "type": "search_results",
                "data": results
            }]
        )

    @capability("index")
    async def index(self, documents: list[dict]) -> TaskResult:
        """Index new documents into the search database."""
        await self._database.bulk_index(documents)

        return TaskResult(
            status="completed",
            artifacts=[{
                "type": "index_summary",
                "data": {"count": len(documents)}
            }]
        )

    async def on_stop(self):
        """Called when agent shuts down."""
        await self._database.close()
        self.logger.info("SearchAgent stopped")
```

---

## BaseAgent vs SecureAgent

AgentWeave provides two base classes:

### BaseAgent

**Purpose**: Minimal agent with lifecycle management, no security enforcement.

**Use cases:**
- Local development and testing
- Quick prototyping
- Integration with non-SPIFFE environments

```python
from agentweave import BaseAgent

class SimpleAgent(BaseAgent):
    """Agent without security enforcement."""
    pass
```

{: .warning }
**Never use BaseAgent in production.** It has no identity verification, no authorization, and no mTLS. It's designed solely for development.

### SecureAgent

**Purpose**: Production-ready agent with automatic security enforcement.

**Features:**
- Requires SPIFFE identity (agent won't start without SVID)
- Enforces authorization policies on all requests
- Uses mTLS for all communication
- Logs all security decisions

```python
from agentweave import SecureAgent

class ProductionAgent(SecureAgent):
    """Agent with full security enforcement."""
    pass
```

{: .note }
**Always use SecureAgent for production deployments.** The SDK is designed so the secure path is the only path.

---

## Agent Lifecycle

Agents have a well-defined lifecycle with hooks for initialization and cleanup:

```
┌──────────┐
│   init   │  Agent instance created (config loaded)
└────┬─────┘
     │
     ▼
┌──────────┐
│on_start()│  Resources initialized (DB connections, etc.)
└────┬─────┘
     │
     ▼
┌──────────┐
│ Running  │  Agent serving requests, handling tasks
│          │  Capabilities are active
└────┬─────┘
     │
     ▼
┌──────────┐
│on_stop() │  Cleanup (close connections, flush logs)
└────┬─────┘
     │
     ▼
┌──────────┐
│ Stopped  │  Agent terminated
└──────────┘
```

### Lifecycle Hooks

#### `__init__(self, config: AgentConfig)`

**Called**: When the agent instance is created
**Purpose**: Basic initialization (usually handled by base class)
**Do**: Store configuration, initialize simple attributes
**Don't**: Open connections, start threads, make network calls

```python
class MyAgent(SecureAgent):
    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self._cache = {}  # Simple initialization only
```

#### `async def on_start(self)`

**Called**: Before the agent begins serving requests
**Purpose**: Resource initialization
**Do**: Open database connections, load models, start background tasks
**Don't**: Block indefinitely, raise exceptions unnecessarily

```python
class MyAgent(SecureAgent):
    async def on_start(self):
        # Load ML model
        self._model = await load_model("model.pkl")

        # Connect to database
        self._db = await Database.connect(self.config.database_url)

        # Start background task
        self._task = asyncio.create_task(self._periodic_cleanup())

        self.logger.info("MyAgent started successfully")
```

#### `async def on_stop(self)`

**Called**: When the agent is shutting down (SIGTERM, SIGINT)
**Purpose**: Graceful cleanup
**Do**: Close connections, flush buffers, cancel background tasks
**Don't**: Start new work, make blocking calls

```python
class MyAgent(SecureAgent):
    async def on_stop(self):
        # Cancel background tasks
        if self._task:
            self._task.cancel()

        # Close database connection
        if self._db:
            await self._db.close()

        self.logger.info("MyAgent stopped gracefully")
```

### Starting an Agent

```python
# From code
agent = SearchAgent.from_config("config.yaml")
await agent.start()  # Calls on_start(), then serves requests

# Or use the blocking run() method
agent.run()  # Blocks until SIGTERM/SIGINT
```

```bash
# From CLI
agentweave serve config.yaml
```

---

## Capabilities and the @capability Decorator

**Capabilities** are the actions an agent can perform. They're defined using the `@capability` decorator.

### Basic Capability

```python
class DataAgent(SecureAgent):
    @capability("process")
    async def process_data(self, data: dict) -> TaskResult:
        """Process incoming data."""
        result = await process(data)
        return TaskResult(status="completed", artifacts=[result])
```

### What @capability Does

The `@capability` decorator:

1. **Registers** the method as a callable capability
2. **Advertises** it in the Agent Card
3. **Routes** incoming A2A tasks to this method
4. **Enforces** authorization before execution
5. **Validates** input/output types (if type hints provided)

### Capability Naming

Capability names should be:
- **Descriptive**: `search`, `index`, `analyze` (not `do_thing`)
- **Verb-based**: Actions the agent performs
- **Unique**: Within the agent (no duplicates)

```python
# ✅ Good capability names
@capability("search")
@capability("analyze_sentiment")
@capability("generate_report")

# ❌ Bad capability names
@capability("thing")
@capability("process")  # Too vague
@capability("search_1")  # Use parameters instead
```

### Capability Parameters

Capabilities accept parameters via function arguments:

```python
@capability("search")
async def search(
    self,
    query: str,              # Required parameter
    max_results: int = 10,   # Optional with default
    filters: dict = None     # Optional, None default
) -> TaskResult:
    """Search with configurable parameters."""
    results = await self._db.search(
        query=query,
        limit=max_results,
        filters=filters or {}
    )
    return TaskResult(status="completed", artifacts=[results])
```

When calling this capability:

```python
result = await agent.call_agent(
    target="spiffe://company.com/agent/search",
    task_type="search",
    payload={
        "query": "AI security",
        "max_results": 20,
        "filters": {"date_range": "2024"}
    }
)
```

### Capability Return Values

Capabilities must return a `TaskResult`:

```python
from agentweave.types import TaskResult

@dataclass
class TaskResult:
    status: str                    # "completed", "failed", "working"
    artifacts: list[dict] = None   # Output data
    error: str = None              # Error message if failed
    metadata: dict = None          # Additional context
```

**Example:**

```python
@capability("analyze")
async def analyze(self, text: str) -> TaskResult:
    try:
        analysis = await perform_analysis(text)

        return TaskResult(
            status="completed",
            artifacts=[{
                "type": "sentiment_analysis",
                "data": {
                    "sentiment": analysis.sentiment,
                    "confidence": analysis.confidence
                }
            }],
            metadata={"model_version": "1.2.0"}
        )
    except Exception as e:
        return TaskResult(
            status="failed",
            error=str(e)
        )
```

---

## Agent Configuration

Agents are configured using YAML files and the `AgentConfig` dataclass.

### Configuration Structure

```yaml
agent:
  name: "search-agent"
  trust_domain: "mycompany.com"
  description: "Searches data stores for information"
  capabilities:
    - name: "search"
      description: "Full-text search"
      input_modes: ["application/json"]
      output_modes: ["application/json"]

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"

authorization:
  provider: "opa"
  opa_endpoint: "http://localhost:8181"
  policy_path: "mycompany/authz"
  default_action: "deny"

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"

server:
  host: "0.0.0.0"
  port: 8443

observability:
  metrics:
    enabled: true
    port: 9090
  logging:
    level: "INFO"
    format: "json"
```

### AgentConfig Dataclass

```python
from agentweave.config import AgentConfig

config = AgentConfig.from_file("config.yaml")

# Access configuration
print(config.agent.name)           # "search-agent"
print(config.agent.trust_domain)   # "mycompany.com"
print(config.identity.provider)    # "spiffe"
```

### Configuration Validation

The SDK validates configuration at load time:

```python
# This will raise ValidationError
config = AgentConfig.from_file("bad-config.yaml")

# Example validation errors:
# - Invalid SPIFFE trust domain
# - Missing required fields
# - Security violations (peer_verification: "none")
# - Invalid TLS version
```

{: .important }
**Configuration is immutable.** Once loaded, `AgentConfig` cannot be modified. This prevents accidental security downgrades at runtime.

### Environment Variable Overrides

Configuration can be overridden with environment variables:

```bash
export AGENTWEAVE_AGENT_NAME="search-agent-override"
export AGENTWEAVE_IDENTITY_PROVIDER="spiffe"
export AGENTWEAVE_AUTHORIZATION_DEFAULT_ACTION="deny"
```

```python
# Load from environment
config = AgentConfig.from_env()
```

---

## Agent Cards

An **Agent Card** is a JSON document that describes the agent's capabilities and metadata. It's published at `/.well-known/agent.json` for discovery.

### Agent Card Structure

```json
{
  "name": "search-agent",
  "description": "Searches data stores for information",
  "version": "1.0.0",
  "url": "https://search-agent.mycompany.com",
  "capabilities": [
    {
      "name": "search",
      "description": "Full-text search across documents",
      "input_modes": ["application/json"],
      "output_modes": ["application/json"],
      "parameters": {
        "query": {"type": "string", "required": true},
        "max_results": {"type": "integer", "default": 10}
      }
    }
  ],
  "authentication": {
    "schemes": [
      {
        "type": "mtls",
        "spiffe_id": "spiffe://mycompany.com/agent/search/prod"
      }
    ]
  },
  "extensions": {
    "spiffe_id": "spiffe://mycompany.com/agent/search/prod",
    "trust_domain": "mycompany.com"
  }
}
```

### Generating Agent Cards

```python
# Programmatically
agent = SearchAgent.from_config("config.yaml")
card = agent.get_agent_card()
print(card.to_json())
```

```bash
# From CLI
agentweave card generate config.yaml
```

### Agent Card Discovery

Other agents discover capabilities by fetching the Agent Card:

```python
# Fetch Agent Card from another agent
card_url = "https://search-agent.mycompany.com/.well-known/agent.json"
card = await AgentCard.fetch(card_url)

print(f"Agent: {card.name}")
print(f"Capabilities: {[c.name for c in card.capabilities]}")
```

---

## Calling Other Agents

Agents call each other using the `call_agent()` method:

### Basic Call

```python
class OrchestratorAgent(SecureAgent):
    @capability("orchestrate")
    async def orchestrate(self, query: str) -> TaskResult:
        # Call search agent
        search_result = await self.call_agent(
            target="spiffe://mycompany.com/agent/search/prod",
            task_type="search",
            payload={"query": query, "max_results": 20}
        )

        # Process results
        if search_result.status == "completed":
            data = search_result.artifacts[0]["data"]
            # ... do something with data

        return TaskResult(status="completed", artifacts=[...])
```

### Error Handling

```python
from agentweave.exceptions import AuthorizationError, IdentityError

@capability("process")
async def process(self, data: dict) -> TaskResult:
    try:
        result = await self.call_agent(
            target="spiffe://mycompany.com/agent/processor",
            task_type="process",
            payload=data,
            timeout=60.0  # 60 second timeout
        )
        return result

    except AuthorizationError as e:
        # Not allowed to call this agent
        self.logger.error(f"Authorization denied: {e}")
        return TaskResult(status="failed", error="Not authorized")

    except IdentityError as e:
        # Identity verification failed
        self.logger.error(f"Identity error: {e}")
        return TaskResult(status="failed", error="Identity verification failed")

    except TimeoutError:
        # Request timed out
        return TaskResult(status="failed", error="Timeout")
```

### Parallel Calls

```python
import asyncio

@capability("search_all")
async def search_all(self, query: str) -> TaskResult:
    # Call multiple agents in parallel
    results = await asyncio.gather(
        self.call_agent(
            target="spiffe://mycompany.com/agent/search-docs",
            task_type="search",
            payload={"query": query}
        ),
        self.call_agent(
            target="spiffe://mycompany.com/agent/search-code",
            task_type="search",
            payload={"query": query}
        ),
        self.call_agent(
            target="spiffe://mycompany.com/agent/search-chat",
            task_type="search",
            payload={"query": query}
        ),
        return_exceptions=True  # Don't fail if one agent fails
    )

    # Combine results
    combined = []
    for result in results:
        if isinstance(result, TaskResult) and result.status == "completed":
            combined.extend(result.artifacts)

    return TaskResult(status="completed", artifacts=combined)
```

---

## Best Practices

### 1. Keep Capabilities Focused

Each capability should do one thing well:

```python
# ✅ Good: Focused capabilities
@capability("search")
async def search(self, query: str) -> TaskResult: ...

@capability("index")
async def index(self, documents: list) -> TaskResult: ...

# ❌ Bad: Kitchen sink capability
@capability("do_everything")
async def do_everything(self, action: str, **kwargs) -> TaskResult: ...
```

### 2. Use Type Hints

Type hints enable validation and better error messages:

```python
# ✅ Good: Type hints for parameters and return
@capability("analyze")
async def analyze(self, text: str, language: str = "en") -> TaskResult:
    ...

# ❌ Bad: No type hints
@capability("analyze")
async def analyze(self, text, language="en"):
    ...
```

### 3. Handle Errors Gracefully

Return structured errors instead of raising exceptions:

```python
@capability("process")
async def process(self, data: dict) -> TaskResult:
    try:
        result = await process_data(data)
        return TaskResult(status="completed", artifacts=[result])
    except ValidationError as e:
        return TaskResult(
            status="failed",
            error=f"Invalid input: {e}",
            metadata={"error_type": "validation"}
        )
    except Exception as e:
        self.logger.exception("Unexpected error in process")
        return TaskResult(
            status="failed",
            error="Internal error",
            metadata={"error_type": "internal"}
        )
```

### 4. Log Important Events

Use the built-in logger for observability:

```python
@capability("search")
async def search(self, query: str) -> TaskResult:
    self.logger.info(f"Search request: query={query}")

    results = await self._db.search(query)

    self.logger.info(f"Search completed: found {len(results)} results")

    return TaskResult(status="completed", artifacts=[results])
```

### 5. Validate Input

Validate inputs before processing:

```python
from pydantic import BaseModel, validator

class SearchRequest(BaseModel):
    query: str
    max_results: int = 10

    @validator('query')
    def query_not_empty(cls, v):
        if not v.strip():
            raise ValueError("Query cannot be empty")
        return v

    @validator('max_results')
    def max_results_valid(cls, v):
        if v < 1 or v > 100:
            raise ValueError("max_results must be between 1 and 100")
        return v

@capability("search")
async def search(self, query: str, max_results: int = 10) -> TaskResult:
    # Validate input
    try:
        request = SearchRequest(query=query, max_results=max_results)
    except ValidationError as e:
        return TaskResult(status="failed", error=str(e))

    # Process validated input
    results = await self._db.search(request.query, limit=request.max_results)
    return TaskResult(status="completed", artifacts=[results])
```

---

## What's Next?

Now that you understand agents, explore the security layers:

- [Identity & SPIFFE](/agentweave/core-concepts/identity/): How agents get cryptographic identity
- [Authorization & OPA](/agentweave/core-concepts/authorization/): How agents enforce access control
- [A2A Protocol](/agentweave/core-concepts/communication/): How agents communicate with each other

{: .note }
The agent abstraction is designed to feel like writing a regular Python class. The SDK handles all security concerns automatically, letting you focus on business logic.
