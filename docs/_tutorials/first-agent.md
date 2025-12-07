---
layout: tutorial
title: Building Your First Agent
permalink: /tutorials/first-agent/
nav_order: 2
parent: Tutorials
difficulty: Beginner
duration: 30 minutes
---

# Building Your First Agent

In this tutorial, you'll build a complete, secure AI agent from scratch using the AgentWeave SDK. By the end, you'll have a working agent with cryptographic identity, authorization policies, and the ability to communicate securely with other agents.

## Learning Objectives

By completing this tutorial, you will:
- Understand the basic structure of an AgentWeave project
- Create a configuration file with identity and authorization
- Define agent capabilities using decorators
- Run your agent with the AgentWeave server
- Test your agent manually

## Prerequisites

Before starting, ensure you have:
- **AgentWeave SDK installed** - See [Installation Guide](/getting-started/installation/)
- **SPIRE server running** - For cryptographic identity
- **OPA running** - For authorization (optional for this tutorial)
- **Python 3.9+** installed
- **Basic Python knowledge** - Familiarity with classes and decorators

**Time estimate:** 30 minutes

## What You'll Build

A "Math Agent" that can perform basic arithmetic operations. This simple example demonstrates all the core AgentWeave concepts you need to build more sophisticated agents.

## Step 1: Create Your Project Structure

Let's start by creating a clean project structure:

```bash
mkdir my-first-agent
cd my-first-agent
mkdir config policies
touch agent.py config/agent.yaml policies/policy.rego
```

Your project should look like this:

```
my-first-agent/
├── agent.py           # Agent implementation
├── config/
│   └── agent.yaml     # Configuration file
└── policies/
    └── policy.rego    # Authorization policy
```

## Step 2: Write the Configuration File

The configuration file defines your agent's identity, authorization, and server settings. Create `config/agent.yaml`:

```yaml
# Agent Identity Configuration
identity:
  # SPIFFE ID uniquely identifies this agent
  spiffe_id: "spiffe://example.org/math-agent"

  # SPIRE socket path (adjust for your installation)
  spire_socket: "/tmp/spire-agent/public/api.sock"

  # Trust domain for SPIFFE federation
  trust_domain: "example.org"

# Authorization Configuration
authorization:
  # Use OPA for policy-based authorization
  engine: "opa"

  # Default policy: deny all in production, allow all in development
  default_policy: "allow_all"  # Change to "deny_all" for production

  # Path to OPA policy files
  policy_path: "./policies"

  # OPA server configuration (if using external OPA)
  opa:
    enabled: false
    url: "http://localhost:8181"

# Server Configuration
server:
  # Host and port to listen on
  host: "0.0.0.0"
  port: 8443

  # mTLS is always enabled (the secure path is the only path)
  mtls:
    enabled: true
    # Certificates from SPIRE
    cert_source: "spire"

# Observability Configuration
observability:
  # Structured logging
  logging:
    level: "INFO"
    format: "json"

  # Metrics (optional)
  metrics:
    enabled: true
    port: 9090
    path: "/metrics"

  # Tracing (optional)
  tracing:
    enabled: false

# Agent Metadata
metadata:
  name: "Math Agent"
  version: "1.0.0"
  description: "A simple agent that performs arithmetic operations"
```

### Understanding the Configuration

Let's break down the key sections:

**Identity Section:**
- `spiffe_id`: Your agent's cryptographic identity (like a username)
- `spire_socket`: How to communicate with the SPIRE agent
- `trust_domain`: Security boundary for your agents

**Authorization Section:**
- `engine`: Which authorization system to use (OPA)
- `default_policy`: For development, we allow all requests
- `policy_path`: Where to find policy files

**Server Section:**
- `host` and `port`: Where your agent listens
- `mtls.enabled`: Always true - security cannot be bypassed
- `cert_source`: Get certificates from SPIRE

{: .note }
> In production, always use `default_policy: "deny_all"` and write explicit OPA policies to allow specific actions.

## Step 3: Write the Authorization Policy

Even though we're using `allow_all` for development, let's create a proper policy file. Create `policies/policy.rego`:

```rego
package agentweave.authz

# Default deny - only allow what we explicitly permit
default allow = false

# Allow all requests from the same trust domain
allow {
    # Get the caller's SPIFFE ID from input
    caller_spiffe_id := input.caller.spiffe_id

    # Extract trust domain from caller's SPIFFE ID
    caller_trust_domain := split(caller_spiffe_id, "/")[2]

    # Get our trust domain
    our_trust_domain := input.agent.trust_domain

    # Allow if trust domains match
    caller_trust_domain == our_trust_domain
}

# Allow specific operations for authenticated callers
allow {
    # Must have valid SPIFFE identity
    input.caller.spiffe_id != ""

    # Allow these methods
    input.request.method == "add"
}

allow {
    input.caller.spiffe_id != ""
    input.request.method == "subtract"
}

allow {
    input.caller.spiffe_id != ""
    input.request.method == "multiply"
}

allow {
    input.caller.spiffe_id != ""
    input.request.method == "divide"
}
```

### Understanding the Policy

This Rego policy:
1. **Default denies** all requests (security first!)
2. **Allows requests from the same trust domain** (same organization)
3. **Allows specific math operations** if the caller has a valid identity

{: .tip }
> OPA policies use the Rego language. Don't worry if it looks unfamiliar - we'll cover policies in depth in the [Writing OPA Policies](/tutorials/opa-policies/) tutorial.

## Step 4: Implement the Agent

Now for the fun part - writing the agent code! Create `agent.py`:

```python
"""
Math Agent - A simple agent demonstrating AgentWeave basics
"""
from typing import Dict, Any
from agentweave import Agent, capability
from agentweave.context import AgentContext

class MathAgent(Agent):
    """
    A simple agent that performs basic arithmetic operations.

    This agent demonstrates:
    - Using the @capability decorator
    - Input validation
    - Error handling
    - Returning structured responses
    """

    def __init__(self, config_path: str):
        """Initialize the Math Agent."""
        super().__init__(config_path)
        self.logger.info("Math Agent initialized")

    @capability(
        name="add",
        description="Add two numbers together",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First number"},
                "b": {"type": "number", "description": "Second number"}
            },
            "required": ["a", "b"]
        }
    )
    async def add(self, context: AgentContext, a: float, b: float) -> Dict[str, Any]:
        """
        Add two numbers.

        Args:
            context: Request context (contains caller identity, metadata, etc.)
            a: First number
            b: Second number

        Returns:
            Dictionary with the result
        """
        self.logger.info(f"Adding {a} + {b}")

        result = a + b

        return {
            "operation": "add",
            "operands": [a, b],
            "result": result,
            "message": f"{a} + {b} = {result}"
        }

    @capability(
        name="subtract",
        description="Subtract one number from another",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "Number to subtract from"},
                "b": {"type": "number", "description": "Number to subtract"}
            },
            "required": ["a", "b"]
        }
    )
    async def subtract(self, context: AgentContext, a: float, b: float) -> Dict[str, Any]:
        """Subtract b from a."""
        self.logger.info(f"Subtracting {a} - {b}")

        result = a - b

        return {
            "operation": "subtract",
            "operands": [a, b],
            "result": result,
            "message": f"{a} - {b} = {result}"
        }

    @capability(
        name="multiply",
        description="Multiply two numbers",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number"},
                "b": {"type": "number"}
            },
            "required": ["a", "b"]
        }
    )
    async def multiply(self, context: AgentContext, a: float, b: float) -> Dict[str, Any]:
        """Multiply two numbers."""
        self.logger.info(f"Multiplying {a} * {b}")

        result = a * b

        return {
            "operation": "multiply",
            "operands": [a, b],
            "result": result,
            "message": f"{a} * {b} = {result}"
        }

    @capability(
        name="divide",
        description="Divide one number by another",
        input_schema={
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "Dividend"},
                "b": {"type": "number", "description": "Divisor (cannot be zero)"}
            },
            "required": ["a", "b"]
        }
    )
    async def divide(self, context: AgentContext, a: float, b: float) -> Dict[str, Any]:
        """
        Divide a by b.

        Raises:
            ValueError: If b is zero
        """
        if b == 0:
            raise ValueError("Cannot divide by zero")

        self.logger.info(f"Dividing {a} / {b}")

        result = a / b

        return {
            "operation": "divide",
            "operands": [a, b],
            "result": result,
            "message": f"{a} / {b} = {result}"
        }


def main():
    """Main entry point for the agent."""
    import asyncio
    import sys

    # Get config path from command line or use default
    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/agent.yaml"

    # Create and run the agent
    agent = MathAgent(config_path)

    # Run the agent server
    asyncio.run(agent.serve())


if __name__ == "__main__":
    main()
```

### Understanding the Agent Code

Let's break down the key parts:

**1. Agent Class:**
```python
class MathAgent(Agent):
```
All agents inherit from the `Agent` base class, which provides identity, authorization, and communication.

**2. The @capability Decorator:**
```python
@capability(
    name="add",
    description="Add two numbers together",
    input_schema={...}
)
```
This decorator:
- Registers a method as an agent capability
- Defines the JSON Schema for input validation
- Makes the capability discoverable by other agents
- Handles serialization/deserialization

**3. AgentContext Parameter:**
```python
async def add(self, context: AgentContext, a: float, b: float):
```
Every capability receives an `AgentContext` with:
- Caller's SPIFFE ID (who's calling)
- Request metadata
- Trace ID for distributed tracing
- Authorization context

**4. Structured Responses:**
```python
return {
    "operation": "add",
    "result": result,
    "message": f"{a} + {b} = {result}"
}
```
Return dictionaries that can be serialized to JSON for the A2A protocol.

{: .tip }
> Always make your capabilities `async`. AgentWeave uses asyncio for high-performance concurrent request handling.

## Step 5: Run Your Agent

Now let's start the agent:

```bash
# Make sure SPIRE is running
sudo systemctl status spire-agent

# Run the agent
python agent.py config/agent.yaml
```

You should see output like:

```
{"timestamp": "2025-12-07T10:30:00Z", "level": "INFO", "message": "Math Agent initialized"}
{"timestamp": "2025-12-07T10:30:00Z", "level": "INFO", "message": "Loaded SPIFFE identity", "spiffe_id": "spiffe://example.org/math-agent"}
{"timestamp": "2025-12-07T10:30:00Z", "level": "INFO", "message": "Registered capability", "name": "add"}
{"timestamp": "2025-12-07T10:30:00Z", "level": "INFO", "message": "Registered capability", "name": "subtract"}
{"timestamp": "2025-12-07T10:30:00Z", "level": "INFO", "message": "Registered capability", "name": "multiply"}
{"timestamp": "2025-12-07T10:30:00Z", "level": "INFO", "message": "Registered capability", "name": "divide"}
{"timestamp": "2025-12-07T10:30:00Z", "level": "INFO", "message": "Agent server started", "host": "0.0.0.0", "port": 8443}
{"timestamp": "2025-12-07T10:30:00Z", "level": "INFO", "message": "Metrics server started", "port": 9090}
```

Congratulations! Your agent is running!

{: .note }
> If you see SPIRE connection errors, verify that SPIRE is running and the socket path in your config is correct.

## Step 6: Test Your Agent

While your agent is running (in another terminal), let's test it using the AgentWeave CLI:

### Test the add capability:

```bash
agentweave-cli call \
  --agent spiffe://example.org/math-agent \
  --capability add \
  --params '{"a": 10, "b": 5}'
```

Response:
```json
{
  "operation": "add",
  "operands": [10, 5],
  "result": 15,
  "message": "10 + 5 = 15"
}
```

### Test division:

```bash
agentweave-cli call \
  --agent spiffe://example.org/math-agent \
  --capability divide \
  --params '{"a": 20, "b": 4}'
```

Response:
```json
{
  "operation": "divide",
  "operands": [20, 4],
  "result": 5.0,
  "message": "20 / 4 = 5.0"
}
```

### Test error handling (divide by zero):

```bash
agentweave-cli call \
  --agent spiffe://example.org/math-agent \
  --capability divide \
  --params '{"a": 10, "b": 0}'
```

Response:
```json
{
  "error": {
    "code": "INVALID_ARGUMENT",
    "message": "Cannot divide by zero"
  }
}
```

Perfect! Your agent correctly handles errors.

## Step 7: Check the Metrics

Visit http://localhost:9090/metrics to see Prometheus metrics:

```
# HELP agentweave_requests_total Total number of requests
# TYPE agentweave_requests_total counter
agentweave_requests_total{capability="add",status="success"} 1.0
agentweave_requests_total{capability="divide",status="success"} 1.0
agentweave_requests_total{capability="divide",status="error"} 1.0

# HELP agentweave_request_duration_seconds Request duration in seconds
# TYPE agentweave_request_duration_seconds histogram
agentweave_request_duration_seconds_bucket{capability="add",le="0.005"} 1.0
...
```

## Complete Code Listing

Here's the complete code for easy reference:

### config/agent.yaml
```yaml
identity:
  spiffe_id: "spiffe://example.org/math-agent"
  spire_socket: "/tmp/spire-agent/public/api.sock"
  trust_domain: "example.org"

authorization:
  engine: "opa"
  default_policy: "allow_all"
  policy_path: "./policies"

server:
  host: "0.0.0.0"
  port: 8443
  mtls:
    enabled: true
    cert_source: "spire"

observability:
  logging:
    level: "INFO"
    format: "json"
  metrics:
    enabled: true
    port: 9090

metadata:
  name: "Math Agent"
  version: "1.0.0"
```

### policies/policy.rego
```rego
package agentweave.authz

default allow = false

allow {
    caller_spiffe_id := input.caller.spiffe_id
    caller_trust_domain := split(caller_spiffe_id, "/")[2]
    our_trust_domain := input.agent.trust_domain
    caller_trust_domain == our_trust_domain
}

allow {
    input.caller.spiffe_id != ""
    input.request.method == "add"
}

allow {
    input.caller.spiffe_id != ""
    input.request.method == "subtract"
}

allow {
    input.caller.spiffe_id != ""
    input.request.method == "multiply"
}

allow {
    input.caller.spiffe_id != ""
    input.request.method == "divide"
}
```

### agent.py
See Step 4 for the complete agent.py code.

## Summary

Congratulations! You've built your first AgentWeave agent. You've learned:

- How to structure an AgentWeave project
- Writing configuration files with identity and authorization
- Defining capabilities with the `@capability` decorator
- Running agents with the built-in server
- Testing agents with the CLI
- Viewing metrics

## Exercises

Try these exercises to deepen your understanding:

1. **Add a new capability:** Implement a `power` operation that raises a to the power of b
2. **Improve validation:** Add checks that operands are not negative for square root
3. **Add logging:** Log the caller's SPIFFE ID on each request
4. **Test the policy:** Change `default_policy` to `"deny_all"` and verify authorization works
5. **Add metadata:** Include the caller's identity in the response

## What's Next?

Now that you've built a basic agent, explore:

- **[Agent-to-Agent Communication](/tutorials/agent-communication/)** - Build multi-agent systems
- **[Writing OPA Policies](/tutorials/opa-policies/)** - Master authorization
- **[How-To: Custom Tools](/guides/custom-tools/)** - Give your agent advanced capabilities
- **[Examples: Research Assistant](/examples/research-assistant/)** - See a real-world agent

## Troubleshooting

### "Cannot connect to SPIRE"
- Verify SPIRE is running: `sudo systemctl status spire-agent`
- Check socket path in config matches SPIRE installation
- Ensure user has permission to access socket

### "Authorization denied"
- If using `deny_all`, ensure OPA policy allows the request
- Check OPA logs: `docker logs opa` (if using Docker)
- Verify caller has valid SPIFFE ID

### "Port already in use"
- Another agent is using port 8443
- Change `server.port` in config
- Or stop the other agent

See the [Troubleshooting Guide](/troubleshooting/) for more help.
