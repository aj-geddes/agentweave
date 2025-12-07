# AgentWeave SDK - Quick Start Guide

Get your first secure agent running in minutes.

## Prerequisites

- Python 3.10 or higher
- Docker and Docker Compose (for local development)
- Basic understanding of async/await in Python

## Installation

### Install the SDK

```bash
pip install agentweave
```

### Install Infrastructure (Development)

For local development, you'll need SPIRE and OPA running:

```bash
# Clone the starter template
git clone https://github.com/agentweave/agentweave-starter
cd agentweave-starter

# Start SPIRE Server, SPIRE Agent, and OPA
docker-compose up -d

# Verify services are running
docker-compose ps
```

This sets up:
- SPIRE Server (identity provider)
- SPIRE Agent (workload API)
- OPA (policy engine)

## Your First Agent

### 1. Create Agent Code

Create `my_agent.py`:

```python
from agentweave import SecureAgent, capability

class HelloAgent(SecureAgent):
    """My first secure agent."""

    @capability("greet")
    async def greet(self, name: str) -> dict:
        """Greet someone by name."""
        return {
            "message": f"Hello, {name}!",
            "from": self.config.agent.name
        }

if __name__ == "__main__":
    agent = HelloAgent.from_config("config.yaml")
    agent.run()
```

### 2. Create Configuration

Create `config.yaml`:

```yaml
agent:
  name: "hello-agent"
  trust_domain: "my-domain.local"
  description: "My first secure agent"
  capabilities:
    - name: "greet"
      description: "Greet someone"
      input_modes: ["application/json"]
      output_modes: ["application/json"]

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"
  allowed_trust_domains:
    - "my-domain.local"

authorization:
  provider: "opa"
  opa_endpoint: "http://localhost:8181"
  policy_path: "agentweave/authz"
  default_action: "deny"
  audit:
    enabled: true
    destination: "stdout"

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"

server:
  host: "0.0.0.0"
  port: 8443
  protocol: "a2a"

observability:
  metrics:
    enabled: true
    port: 9090
  logging:
    level: "INFO"
    format: "json"
```

### 3. Register with SPIRE

Before starting your agent, register it with SPIRE:

```bash
# Create a registration entry
docker exec spire-server spire-server entry create \
  -spiffeID spiffe://my-domain.local/agent/hello-agent/dev \
  -parentID spiffe://my-domain.local/spire/agent/docker \
  -selector unix:uid:1000
```

### 4. Create OPA Policy

Create `policies/authz.rego`:

```rego
package agentweave.authz

import rego.v1

default allow := false

# Allow all agents in the same trust domain
allow if {
    startswith(input.caller_spiffe_id, "spiffe://my-domain.local/")
    startswith(input.callee_spiffe_id, "spiffe://my-domain.local/")
}
```

Load the policy into OPA:

```bash
curl -X PUT http://localhost:8181/v1/policies/authz \
  --data-binary @policies/authz.rego
```

### 5. Run Your Agent

```bash
# Set SPIFFE endpoint
export SPIFFE_ENDPOINT_SOCKET=unix:///run/spire/sockets/agent.sock

# Run the agent
python my_agent.py
```

You should see:

```json
{
  "timestamp": "2025-12-06T10:30:00Z",
  "level": "INFO",
  "message": "Agent starting",
  "agent": "hello-agent",
  "spiffe_id": "spiffe://my-domain.local/agent/hello-agent/dev"
}
{
  "level": "INFO",
  "message": "Server listening",
  "host": "0.0.0.0",
  "port": 8443
}
```

## Testing Your Agent

### 1. Check Agent Health

```bash
curl http://localhost:8443/health
```

### 2. View Agent Card

```bash
curl http://localhost:8443/.well-known/agent.json
```

Response:

```json
{
  "name": "hello-agent",
  "description": "My first secure agent",
  "url": "https://localhost:8443",
  "version": "1.0.0",
  "capabilities": [
    {
      "name": "greet",
      "description": "Greet someone",
      "input_modes": ["application/json"],
      "output_modes": ["application/json"]
    }
  ],
  "extensions": {
    "spiffe_id": "spiffe://my-domain.local/agent/hello-agent/dev"
  }
}
```

### 3. Call the Agent (from another agent)

Create a second agent to call the first:

```python
from agentweave import SecureAgent

class CallerAgent(SecureAgent):
    async def test_call(self):
        result = await self.call_agent(
            target="spiffe://my-domain.local/agent/hello-agent/dev",
            task_type="greet",
            payload={"name": "World"}
        )
        print(result.artifacts[0]["data"])

# Register this agent with SPIRE first!
agent = CallerAgent.from_config("caller-config.yaml")
asyncio.run(agent.test_call())
```

## What Just Happened?

Behind the scenes, the SDK:

1. **Identity**: Fetched X.509 SVID from SPIRE Agent
2. **Server**: Started A2A protocol server with mTLS
3. **Authorization**: Connected to OPA for policy enforcement
4. **Discovery**: Published Agent Card at `/.well-known/agent.json`
5. **Observability**: Exposed metrics at `:9090/metrics`

When the caller agent invokes `greet`:

1. SDK checks OPA policy (allowed because same trust domain)
2. Establishes mTLS connection using SPIFFE identities
3. Sends A2A task over secure channel
4. HelloAgent executes `greet` capability
5. Result returned over same secure channel
6. All calls audited and logged

## Next Steps

- [Configuration Reference](configuration.md) - Detailed config options
- [Security Guide](security.md) - Production hardening
- [A2A Protocol](a2a-protocol.md) - Deep dive on agent communication
- [Multi-Agent Example](../examples/multi_agent/) - Orchestrator pattern

## Common Issues

### "Failed to connect to SPIRE Agent"

Ensure SPIRE Agent is running and socket is accessible:

```bash
docker-compose ps spire-agent
ls -l /run/spire/sockets/agent.sock
```

### "OPA authorization denied"

Check your policy allows the caller:

```bash
# Test policy decision
curl -X POST http://localhost:8181/v1/data/agentweave/authz/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "caller_spiffe_id": "spiffe://my-domain.local/agent/caller/dev",
      "callee_spiffe_id": "spiffe://my-domain.local/agent/hello-agent/dev",
      "action": "greet"
    }
  }'
```

### "Certificate verification failed"

Check trust domains match and SPIRE registration is correct:

```bash
# List registered entries
docker exec spire-server spire-server entry show

# Verify SVID was issued
docker exec spire-agent spire-agent api fetch
```

## Development Tips

### Use Log-Only Mode for Debugging

During development, you can use log-only mode for authorization:

```yaml
authorization:
  provider: "opa"
  default_action: "log-only"  # Logs denials but allows them
```

**Warning**: Never use in production!

### Hot Reload Configuration

```bash
# Agent watches config file for changes
python my_agent.py --watch-config
```

### CLI Helpers

```bash
# Validate config
agentweave validate config.yaml

# Generate SPIRE registration command
agentweave spire-entry config.yaml

# Test agent connectivity
agentweave ping spiffe://my-domain.local/agent/hello-agent/dev
```

## Learn More

- Browse [example agents](../examples/)
- Read the [architecture overview](../README.md#architecture)
- Join the [community discussions](https://github.com/agentweave/agentweave/discussions)
