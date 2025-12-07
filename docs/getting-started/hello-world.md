---
layout: page
title: Hello World Tutorial
description: Build a complete multi-agent system with detailed explanations
nav_order: 4
parent: Getting Started
---

# Hello World Tutorial

This tutorial walks you through building a complete two-agent system: a **GreeterAgent** that provides greetings, and an **ClientAgent** that calls the greeter. You'll learn about agent structure, configuration, deployment, and testing.

{: .note }
> **Tutorial Goal**: Build a working multi-agent system and understand every component. This is more detailed than the [5-Minute Quickstart](quickstart.md).

## Prerequisites

- AgentWeave installed ([Installation Guide](installation.md))
- Docker running with SPIRE and OPA ([Quickstart Step 2](quickstart.md#step-2-start-infrastructure))
- Basic understanding of [Core Concepts](concepts.md)

## Project Structure

We'll create this structure:

```
hello-world/
├── greeter_agent.py          # Greeter agent implementation
├── client_agent.py           # Client agent implementation
├── greeter_config.yaml       # Greeter configuration
├── client_config.yaml        # Client configuration
├── policies/
│   └── authz.rego           # OPA authorization policy
└── README.md                # Project documentation
```

## Part 1: The Greeter Agent

### Step 1.1: Create the Agent Class

Create `greeter_agent.py`:

```python
from agentweave import SecureAgent, capability
from agentweave.types import TaskResult
from datetime import datetime

class GreeterAgent(SecureAgent):
    """
    A friendly agent that greets users in multiple languages.

    Capabilities:
    - greet: Simple greeting
    - greet_formal: Formal greeting
    - get_time: Return current time
    """

    @capability("greet")
    async def greet(self, name: str, language: str = "en") -> TaskResult:
        """
        Greet someone by name.

        Args:
            name: Person's name
            language: Language code (en, es, fr, de)

        Returns:
            TaskResult with greeting message
        """
        greetings = {
            "en": f"Hello, {name}!",
            "es": f"¡Hola, {name}!",
            "fr": f"Bonjour, {name}!",
            "de": f"Guten Tag, {name}!"
        }

        message = greetings.get(language, greetings["en"])

        # Log the greeting (for audit trail)
        self.logger.info(
            "Generated greeting",
            extra={
                "name": name,
                "language": language,
                "caller": self.context.caller_id
            }
        )

        return TaskResult(
            status="completed",
            artifacts=[{
                "type": "greeting",
                "data": {
                    "message": message,
                    "language": language,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }]
        )

    @capability("greet_formal")
    async def greet_formal(self, title: str, last_name: str) -> TaskResult:
        """
        Provide a formal greeting.

        Args:
            title: Title (Mr., Ms., Dr., etc.)
            last_name: Last name

        Returns:
            TaskResult with formal greeting
        """
        message = f"Good day, {title} {last_name}. How may I assist you?"

        return TaskResult(
            status="completed",
            artifacts=[{
                "type": "greeting",
                "data": {"message": message}
            }]
        )

    @capability("get_time")
    async def get_time(self, timezone: str = "UTC") -> TaskResult:
        """
        Return current time.

        Args:
            timezone: Timezone (for simplicity, only UTC supported)

        Returns:
            TaskResult with current time
        """
        current_time = datetime.utcnow().isoformat()

        return TaskResult(
            status="completed",
            artifacts=[{
                "type": "time",
                "data": {
                    "time": current_time,
                    "timezone": timezone
                }
            }]
        )


if __name__ == "__main__":
    # Load configuration and run the agent
    agent = GreeterAgent.from_config("greeter_config.yaml")
    agent.run()
```

**Key Points**:

1. **Inherit from SecureAgent**: This gives you identity, authorization, and communication
2. **@capability decorator**: Marks methods as callable by other agents
3. **TaskResult**: Standard return type for A2A protocol
4. **self.logger**: Built-in structured logger
5. **self.context**: Request context (caller ID, trace ID, etc.)

### Step 1.2: Create Configuration

Create `greeter_config.yaml`:

```yaml
# Agent identity and metadata
agent:
  name: "greeter-agent"
  trust_domain: "helloworld.local"
  description: "Provides greeting services in multiple languages"

  # Advertised capabilities (must match @capability decorators)
  capabilities:
    - name: "greet"
      description: "Greet someone by name"
      input_modes: ["application/json"]
      output_modes: ["application/json"]

    - name: "greet_formal"
      description: "Provide a formal greeting"
      input_modes: ["application/json"]
      output_modes: ["application/json"]

    - name: "get_time"
      description: "Get current time"
      input_modes: ["application/json"]
      output_modes: ["application/json"]

# Identity configuration
identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///tmp/spire-agent/public/api.sock"

  # Which trust domains we trust
  allowed_trust_domains:
    - "helloworld.local"

# Authorization configuration
authorization:
  provider: "opa"
  opa_endpoint: "http://localhost:8181"
  policy_path: "agentweave/authz"
  default_action: "deny"  # Secure by default

  # Audit all authorization decisions
  audit:
    enabled: true
    destination: "file:///var/log/agentweave/greeter-audit.log"

# Transport configuration
transport:
  tls_min_version: "1.3"
  peer_verification: "strict"

  # Connection pool settings
  connection_pool:
    max_connections: 100
    idle_timeout_seconds: 60

  # Circuit breaker for resilience
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout_seconds: 30

# Server configuration
server:
  host: "0.0.0.0"
  port: 8443
  protocol: "a2a"

# Observability configuration
observability:
  # Prometheus metrics
  metrics:
    enabled: true
    port: 9090

  # Distributed tracing
  tracing:
    enabled: true
    exporter: "otlp"
    endpoint: "http://localhost:4317"

  # Structured logging
  logging:
    level: "INFO"
    format: "json"
```

**Configuration Explained**:

- **agent**: Metadata about your agent (name must be unique)
- **identity**: How to get SPIFFE identity (SPIRE endpoint)
- **authorization**: OPA settings (default deny = secure)
- **transport**: mTLS settings (TLS 1.3 required)
- **server**: Where to listen for requests
- **observability**: Metrics, tracing, logging

### Step 1.3: Register with SPIRE

Give the greeter agent a SPIFFE identity:

```bash
docker exec spire-server spire-server entry create \
  -spiffeID spiffe://helloworld.local/agent/greeter \
  -parentID spiffe://helloworld.local/spire/agent \
  -selector unix:uid:$(id -u) \
  -ttl 3600
```

**What this does**:
- **-spiffeID**: Identity for the greeter agent
- **-parentID**: Parent identity (SPIRE Agent)
- **-selector**: How to identify this workload (Unix user ID)
- **-ttl**: Certificate lifetime (1 hour)

Verify the entry:

```bash
docker exec spire-server spire-server entry show \
  -spiffeID spiffe://helloworld.local/agent/greeter
```

## Part 2: The Client Agent

### Step 2.1: Create the Client Agent

Create `client_agent.py`:

```python
import asyncio
from agentweave import SecureAgent, capability
from agentweave.types import TaskResult

class ClientAgent(SecureAgent):
    """
    Client agent that calls the greeter agent.

    Demonstrates:
    - Calling other agents
    - Error handling
    - Result processing
    """

    async def demo_greetings(self):
        """Run a demonstration of calling the greeter agent."""
        greeter_id = "spiffe://helloworld.local/agent/greeter"

        print("=== AgentWeave Hello World Demo ===\n")

        # Example 1: Simple greeting
        print("1. Simple greeting:")
        result = await self.call_agent(
            target=greeter_id,
            task_type="greet",
            payload={"name": "Alice", "language": "en"}
        )
        print(f"   {result.artifacts[0]['data']['message']}\n")

        # Example 2: Spanish greeting
        print("2. Spanish greeting:")
        result = await self.call_agent(
            target=greeter_id,
            task_type="greet",
            payload={"name": "Carlos", "language": "es"}
        )
        print(f"   {result.artifacts[0]['data']['message']}\n")

        # Example 3: Formal greeting
        print("3. Formal greeting:")
        result = await self.call_agent(
            target=greeter_id,
            task_type="greet_formal",
            payload={"title": "Dr.", "last_name": "Smith"}
        )
        print(f"   {result.artifacts[0]['data']['message']}\n")

        # Example 4: Get time
        print("4. Get current time:")
        result = await self.call_agent(
            target=greeter_id,
            task_type="get_time",
            payload={"timezone": "UTC"}
        )
        print(f"   Time: {result.artifacts[0]['data']['time']}\n")

        print("=== Demo Complete ===")

    @capability("run_demo")
    async def run_demo(self) -> TaskResult:
        """
        Capability to run the demo (can be called by other agents).
        """
        await self.demo_greetings()

        return TaskResult(
            status="completed",
            artifacts=[{"type": "demo_result", "data": {"status": "success"}}]
        )


async def main():
    """Run the client agent in demo mode."""
    # Load configuration
    client = ClientAgent.from_config("client_config.yaml")

    # Initialize (acquire identity, connect to OPA)
    await client.initialize()

    # Run demo
    await client.demo_greetings()

    # Cleanup
    await client.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
```

**Key Points**:

1. **call_agent()**: SDK method to call other agents
2. **target**: SPIFFE ID of the agent to call
3. **task_type**: Capability name (must match @capability)
4. **payload**: Arguments to pass (becomes kwargs in the handler)
5. **Error handling**: SDK raises exceptions for auth/network failures

### Step 2.2: Create Configuration

Create `client_config.yaml`:

```yaml
agent:
  name: "client-agent"
  trust_domain: "helloworld.local"
  description: "Client that demonstrates calling other agents"
  capabilities:
    - name: "run_demo"
      description: "Run the greeting demo"

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///tmp/spire-agent/public/api.sock"
  allowed_trust_domains:
    - "helloworld.local"

authorization:
  provider: "opa"
  opa_endpoint: "http://localhost:8181"
  policy_path: "agentweave/authz"
  default_action: "deny"

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"

server:
  host: "0.0.0.0"
  port: 8444  # Different port than greeter

observability:
  logging:
    level: "INFO"
    format: "json"
```

### Step 2.3: Register with SPIRE

```bash
docker exec spire-server spire-server entry create \
  -spiffeID spiffe://helloworld.local/agent/client \
  -parentID spiffe://helloworld.local/spire/agent \
  -selector unix:uid:$(id -u) \
  -ttl 3600
```

## Part 3: Authorization Policy

### Step 3.1: Create OPA Policy

Create `policies/authz.rego`:

```rego
package agentweave.authz

import rego.v1

# Default deny - must explicitly allow
default allow := false

# Helper: Extract trust domain from SPIFFE ID
trust_domain(spiffe_id) := domain if {
    parts := split(spiffe_id, "/")
    domain := parts[2]  # spiffe://DOMAIN/path
}

# Helper: Extract agent name from SPIFFE ID
agent_name(spiffe_id) := name if {
    parts := split(spiffe_id, "/")
    name := parts[4]  # spiffe://domain/agent/NAME
}

# Rule 1: Allow agents in same trust domain to communicate
allow if {
    caller_domain := trust_domain(input.caller_spiffe_id)
    callee_domain := trust_domain(input.callee_spiffe_id)
    caller_domain == callee_domain
    caller_domain == "helloworld.local"
}

# Rule 2: Specific capability restrictions
# Client can call all greeter capabilities
allow if {
    agent_name(input.caller_spiffe_id) == "client"
    agent_name(input.callee_spiffe_id) == "greeter"
    input.action in ["greet", "greet_formal", "get_time"]
}

# Rule 3: Deny calls to unknown capabilities
deny_reason := reason if {
    not allow
    reason := sprintf(
        "Agent %s not authorized to call %s.%s",
        [agent_name(input.caller_spiffe_id), agent_name(input.callee_spiffe_id), input.action]
    )
}
```

**Policy Explained**:

1. **default allow := false**: Secure by default (deny everything)
2. **Helper functions**: Extract trust domain and agent name
3. **Rule 1**: Same trust domain can communicate
4. **Rule 2**: Explicit allow for client → greeter calls
5. **Rule 3**: Helpful denial message for debugging

### Step 3.2: Load Policy into OPA

```bash
# Load the policy
curl -X PUT http://localhost:8181/v1/policies/authz \
  --data-binary @policies/authz.rego

# Verify it loaded
curl http://localhost:8181/v1/policies/authz
```

### Step 3.3: Test Policy

Test the policy before running agents:

```bash
# Should allow: client calling greeter
curl -X POST http://localhost:8181/v1/data/agentweave/authz/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "caller_spiffe_id": "spiffe://helloworld.local/agent/client",
      "callee_spiffe_id": "spiffe://helloworld.local/agent/greeter",
      "action": "greet"
    }
  }'

# Expected: {"result": true}
```

## Part 4: Running the System

### Step 4.1: Start the Greeter Agent

In one terminal:

```bash
export SPIFFE_ENDPOINT_SOCKET=unix:///tmp/spire-agent/public/api.sock
python greeter_agent.py
```

You should see:

```json
{"level": "INFO", "message": "Agent starting", "agent": "greeter-agent"}
{"level": "INFO", "message": "Identity acquired", "spiffe_id": "spiffe://helloworld.local/agent/greeter"}
{"level": "INFO", "message": "OPA connection verified"}
{"level": "INFO", "message": "Server listening", "port": 8443}
{"level": "INFO", "message": "Agent ready"}
```

### Step 4.2: Run the Client Agent

In another terminal:

```bash
export SPIFFE_ENDPOINT_SOCKET=unix:///tmp/spire-agent/public/api.sock
python client_agent.py
```

You should see:

```
=== AgentWeave Hello World Demo ===

1. Simple greeting:
   Hello, Alice!

2. Spanish greeting:
   ¡Hola, Carlos!

3. Formal greeting:
   Good day, Dr. Smith. How may I assist you?

4. Get current time:
   Time: 2025-12-07T10:30:00.123456

=== Demo Complete ===
```

## Part 5: Understanding the Logs

### Greeter Agent Logs

Watch the greeter's logs to see incoming requests:

```json
{"level": "INFO", "message": "Incoming request", "caller": "spiffe://helloworld.local/agent/client", "capability": "greet"}
{"level": "INFO", "message": "Authorization check", "caller": "spiffe://helloworld.local/agent/client", "action": "greet", "decision": "allow"}
{"level": "INFO", "message": "Generated greeting", "name": "Alice", "language": "en"}
{"level": "INFO", "message": "Request completed", "duration_ms": 12}
```

**What you see**:
1. Incoming request from client (caller SPIFFE ID verified via mTLS)
2. OPA authorization check (allowed based on policy)
3. Business logic execution
4. Request completion

### Client Agent Logs

The client logs outbound calls:

```json
{"level": "INFO", "message": "Calling agent", "target": "spiffe://helloworld.local/agent/greeter", "capability": "greet"}
{"level": "INFO", "message": "mTLS handshake complete", "peer": "spiffe://helloworld.local/agent/greeter"}
{"level": "INFO", "message": "Request sent"}
{"level": "INFO", "message": "Response received", "status": "completed"}
```

## Part 6: Testing and Debugging

### Test 1: Check Agent Health

```bash
# Greeter health
curl http://localhost:8443/health

# Client health
curl http://localhost:8444/health
```

### Test 2: View Agent Cards

```bash
# Greeter's capabilities
curl http://localhost:8443/.well-known/agent.json | jq

# Client's capabilities
curl http://localhost:8444/.well-known/agent.json | jq
```

### Test 3: View Metrics

```bash
# Greeter metrics
curl http://localhost:9090/metrics | grep agentweave

# Look for:
# - agentweave_requests_total{capability="greet"}
# - agentweave_request_duration_seconds
# - agentweave_authorization_checks_total
```

### Test 4: Simulate Authorization Failure

Modify the OPA policy to deny client → greeter calls:

```rego
# Add to authz.rego
deny if {
    agent_name(input.caller_spiffe_id) == "client"
}
```

Reload policy:

```bash
curl -X PUT http://localhost:8181/v1/policies/authz \
  --data-binary @policies/authz.rego
```

Run client again - should see:

```
Error: AuthorizationError: Agent client not authorized to call greeter.greet
```

## Exercises for the Reader

Try these to deepen your understanding:

### Exercise 1: Add a New Capability

Add a `goodbye` capability to the greeter:

```python
@capability("goodbye")
async def goodbye(self, name: str) -> TaskResult:
    return TaskResult(
        status="completed",
        artifacts=[{"type": "farewell", "data": {"message": f"Goodbye, {name}!"}}]
    )
```

Remember to:
1. Add to `capabilities` in config
2. Update OPA policy to allow it
3. Call it from the client

### Exercise 2: Implement Error Handling

Modify `greet` to validate the language parameter:

```python
@capability("greet")
async def greet(self, name: str, language: str = "en") -> TaskResult:
    greetings = {"en": "Hello", "es": "Hola", "fr": "Bonjour", "de": "Guten Tag"}

    if language not in greetings:
        return TaskResult(
            status="failed",
            error={
                "code": "INVALID_LANGUAGE",
                "message": f"Language '{language}' not supported. Supported: {list(greetings.keys())}"
            }
        )

    # ... rest of implementation
```

### Exercise 3: Add a Third Agent

Create a `logger-agent` that:
1. Accepts messages to log
2. Can only be called by greeter or client
3. Writes to a file

Update policies to enforce this.

### Exercise 4: Implement Caching

Add simple caching to avoid redundant greetings:

```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._cache = {}

@capability("greet")
async def greet(self, name: str, language: str = "en") -> TaskResult:
    cache_key = f"{name}:{language}"

    if cache_key in self._cache:
        self.logger.info("Cache hit", cache_key=cache_key)
        return self._cache[cache_key]

    # ... generate greeting
    result = TaskResult(...)
    self._cache[cache_key] = result
    return result
```

## Next Steps

Congratulations! You've built a complete multi-agent system with:
- Cryptographic identity (SPIFFE)
- Mutual authentication (mTLS)
- Authorization (OPA)
- Agent-to-agent communication (A2A)
- Observability (metrics, logs)

### Go Deeper

- **[Configuration Reference](../configuration.md)** - All config options explained
- **[Security Guide](../security.md)** - Production hardening checklist
- **[A2A Protocol](../a2a-protocol.md)** - Deep dive into communication
- **[Deployment Guide](../deployment/kubernetes.md)** - Deploy to Kubernetes
- **[Testing Guide](../testing/unit-tests.md)** - Write tests for your agents

### Explore Examples

- **Orchestrator Pattern** - `examples/orchestrator/`
- **Data Pipeline** - `examples/data_pipeline/`
- **LLM Integration** - `examples/llm_agent/`
- **Multi-Cloud** - `examples/multi_cloud/`

---

**Previous**: [← Core Concepts](concepts.md) | **Next**: [Configuration Reference →](../configuration.md)
