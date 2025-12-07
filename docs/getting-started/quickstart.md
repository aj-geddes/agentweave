---
layout: page
title: 5-Minute Quickstart
description: Run your first secure agent in 5 minutes
nav_order: 2
parent: Getting Started
---

# 5-Minute Quickstart

Get your first AgentWeave agent running in 5 minutes. This guide assumes you have [installed AgentWeave](installation.md) and have Docker running.

{: .note }
> **Goal**: Build and run a secure agent that can greet users. Understand the basic AgentWeave workflow without getting into complex details.

## Step 1: Install AgentWeave

If you haven't already:

```bash
pip install agentweave
```

Verify installation:

```bash
agentweave --version
```

## Step 2: Start Infrastructure

Start SPIRE and OPA using Docker Compose:

```bash
# Download the starter template
curl -O https://raw.githubusercontent.com/agentweave/agentweave-starter/main/docker-compose.yaml

# Start services
docker-compose up -d

# Verify they're running
docker-compose ps
```

You should see `spire-server`, `spire-agent`, and `opa` running.

## Step 3: Create Your Agent

Create a file called `hello_agent.py`:

```python
from agentweave import SecureAgent, capability

class HelloAgent(SecureAgent):
    """A simple greeting agent."""

    @capability("greet")
    async def greet(self, name: str = "World") -> dict:
        """Greet someone by name."""
        return {
            "message": f"Hello, {name}! I'm a secure agent.",
            "agent": self.config.agent.name
        }

if __name__ == "__main__":
    agent = HelloAgent.from_config("config.yaml")
    agent.run()
```

That's it! Just 15 lines of code for a fully secure, production-ready agent.

## Step 4: Create Configuration

Create `config.yaml`:

```yaml
agent:
  name: "hello-agent"
  trust_domain: "quickstart.local"
  description: "My first secure agent"
  capabilities:
    - name: "greet"
      description: "Greet someone"

identity:
  provider: "spiffe"
  allowed_trust_domains:
    - "quickstart.local"

authorization:
  provider: "opa"
  opa_endpoint: "http://localhost:8181"
  default_action: "log-only"  # Permissive for quickstart

server:
  port: 8443
```

{: .warning }
> **Development Only**: We're using `default_action: "log-only"` for this quickstart. In production, always use `"deny"` and write explicit policies.

## Step 5: Register with SPIRE

Register your agent to get a cryptographic identity:

```bash
docker exec spire-server spire-server entry create \
  -spiffeID spiffe://quickstart.local/agent/hello-agent \
  -parentID spiffe://quickstart.local/spire/agent \
  -selector unix:uid:$(id -u)
```

You should see:

```
Entry ID         : <uuid>
SPIFFE ID        : spiffe://quickstart.local/agent/hello-agent
Parent ID        : spiffe://quickstart.local/spire/agent
Revision         : 0
X509-SVID TTL    : default
JWT-SVID TTL     : default
Selector         : unix:uid:1000
```

## Step 6: Run Your Agent

Start your agent:

```bash
export SPIFFE_ENDPOINT_SOCKET=unix:///tmp/spire-agent/public/api.sock
python hello_agent.py
```

You should see logs indicating the agent started successfully:

```json
{"level": "INFO", "message": "Agent starting", "agent": "hello-agent"}
{"level": "INFO", "message": "Identity acquired", "spiffe_id": "spiffe://quickstart.local/agent/hello-agent"}
{"level": "INFO", "message": "Server listening", "port": 8443}
```

## Step 7: Test Your Agent

Open a new terminal and test your agent:

### Check Health

```bash
curl http://localhost:8443/health
```

Response:
```json
{"status": "healthy", "timestamp": "2025-12-07T10:30:00Z"}
```

### View Agent Card

```bash
curl http://localhost:8443/.well-known/agent.json | jq
```

Response:
```json
{
  "name": "hello-agent",
  "description": "My first secure agent",
  "version": "1.0.0",
  "capabilities": [
    {
      "name": "greet",
      "description": "Greet someone"
    }
  ],
  "extensions": {
    "spiffe_id": "spiffe://quickstart.local/agent/hello-agent"
  }
}
```

### Call the Agent

To call the agent from another agent, create `caller.py`:

```python
import asyncio
from agentweave import SecureAgent

async def main():
    # Create a caller agent
    caller = SecureAgent.from_config("caller-config.yaml")

    # Call the hello agent
    result = await caller.call_agent(
        target="spiffe://quickstart.local/agent/hello-agent",
        task_type="greet",
        payload={"name": "Alice"}
    )

    print(f"Response: {result.artifacts[0]['data']}")

if __name__ == "__main__":
    asyncio.run(main())
```

{: .note }
> **Note**: You'll need to create `caller-config.yaml` and register the caller agent with SPIRE. See the [Hello World Tutorial](hello-world.md) for a complete multi-agent example.

## What Just Happened?

Behind the scenes, AgentWeave handled:

1. **Identity**: Fetched your agent's X.509 certificate (SVID) from SPIRE
2. **Server**: Started an HTTPS server with mTLS on port 8443
3. **Protocol**: Implemented the A2A (Agent-to-Agent) protocol
4. **Discovery**: Published your capabilities at `/.well-known/agent.json`
5. **Authorization**: Connected to OPA for policy enforcement
6. **Observability**: Set up logging and metrics

When another agent calls your `greet` capability:

```
Caller Agent                          Hello Agent
     |                                      |
     |  1. Get own SVID from SPIRE          |
     |  2. Check OPA: can I call hello?     |
     |  3. Establish mTLS connection   ---> |
     |                                  4. Verify caller's SVID
     |                                  5. Check OPA: is caller allowed?
     |                                  6. Execute greet()
     | <--- 7. Return result over mTLS     |
```

All of this is automatic - you just implement the `@capability` method.

## What's Next?

You've just run your first secure agent! Here's where to go next:

### Learn More
- **[Core Concepts](concepts.md)** - Understand SPIFFE, A2A, and the security model
- **[Hello World Tutorial](hello-world.md)** - Build a complete multi-agent system
- **[Configuration Reference](../configuration.md)** - Detailed config options

### Try Examples
- **Multi-agent orchestration** - See `examples/orchestrator/`
- **Data pipeline** - See `examples/data_pipeline/`
- **LLM integration** - See `examples/llm_agent/`

### Production Readiness
- **[Security Guide](../security.md)** - Harden for production
- **[Deployment](../deployment/kubernetes.md)** - Deploy to Kubernetes
- **[Monitoring](../observability/metrics.md)** - Set up metrics and tracing

## Common Issues

### "Failed to connect to SPIRE Agent"

Make sure the SPIRE Agent is running and the socket path is correct:

```bash
# Check if socket exists
ls -l /tmp/spire-agent/public/api.sock

# Check SPIRE Agent logs
docker-compose logs spire-agent

# Verify environment variable
echo $SPIFFE_ENDPOINT_SOCKET
```

### "No SPIFFE ID found"

You need to register your agent with SPIRE:

```bash
# List existing entries
docker exec spire-server spire-server entry show

# Create entry if missing (see Step 5)
```

### "Port 8443 already in use"

Change the port in your config:

```yaml
server:
  port: 9443  # Use a different port
```

### "OPA connection refused"

Ensure OPA is running:

```bash
# Check OPA status
docker-compose ps opa

# Test OPA endpoint
curl http://localhost:8181/health
```

## Tips for Development

### Use the CLI

The `agentweave` CLI has helpful commands:

```bash
# Validate your config before running
agentweave validate config.yaml

# Generate SPIRE registration command
agentweave spire-entry config.yaml

# Test connectivity to another agent
agentweave ping spiffe://quickstart.local/agent/other-agent
```

### Enable Debug Logging

For more verbose output:

```yaml
observability:
  logging:
    level: "DEBUG"
```

### Auto-reload on Changes

During development, use watch mode:

```bash
# Install watchdog
pip install watchdog

# Run with auto-reload
agentweave serve config.yaml --reload
```

## Clean Up

When you're done:

```bash
# Stop your agent (Ctrl+C)

# Stop infrastructure
docker-compose down

# Remove volumes (optional)
docker-compose down -v
```

---

**Previous**: [← Installation](installation.md) | **Next**: [Core Concepts →](concepts.md)
