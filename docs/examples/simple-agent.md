---
layout: page
title: Simple Agent Example
permalink: /examples/simple-agent/
parent: Examples Overview
nav_order: 1
---

# Simple Agent Example

**Complexity:** Beginner
**Time to Complete:** 15 minutes
**Prerequisites:** Python 3.11+, Docker

This example demonstrates the simplest possible AgentWeave agent: a single agent with one capability that echoes back messages. Perfect for understanding AgentWeave basics.

## What You'll Learn

- How to define an agent with the `SecureAgent` base class
- Using the `@capability` decorator to expose functionality
- Agent configuration with SPIFFE identity
- Running an agent with SPIRE and OPA
- Testing agent capabilities

## Architecture

```
┌─────────────────────────────────────┐
│       Client (CLI/HTTP)             │
└────────────┬────────────────────────┘
             │
             │ HTTPS + mTLS
             │
┌────────────▼────────────────────────┐
│      Echo Agent                     │
│                                     │
│  Capability: "echo"                 │
│  - Receives message                 │
│  - Returns same message             │
│                                     │
│  Security:                          │
│  - SPIFFE ID verification           │
│  - OPA policy check                 │
│  - Audit logging                    │
└────────┬────────────────────────────┘
         │
    ┌────┴────┐
    │ SPIRE   │  ← Provides identity
    │ OPA     │  ← Enforces policy
    └─────────┘
```

## Complete Code

### Agent Implementation

```python
# echo_agent.py
"""
Simple Echo Agent - Demonstrates AgentWeave basics.

This agent has a single capability: echo messages back to the caller.
All security (identity, mTLS, authorization) is handled by the SDK.
"""

import asyncio
from typing import Dict, Any

from agentweave import SecureAgent, capability
from agentweave.types import TaskResult, Message, TextPart


class EchoAgent(SecureAgent):
    """
    An agent that echoes messages back.

    This demonstrates:
    - Minimal agent implementation
    - @capability decorator for exposing functionality
    - Type-safe message handling
    - Automatic security enforcement
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._echo_count = 0  # Track number of echoes

    @capability("echo")
    async def echo(self, message: str, metadata: Dict[str, Any] = None) -> TaskResult:
        """
        Echo a message back to the caller.

        Security automatically enforced by SDK:
        - Caller's SPIFFE ID verified
        - OPA policy checked before this runs
        - Request/response logged for audit

        Args:
            message: The message to echo
            metadata: Optional metadata to include in response

        Returns:
            TaskResult with the echoed message
        """
        self._echo_count += 1

        # Get caller information from request context
        # This is automatically populated by the SDK
        caller_id = self.context.caller_spiffe_id

        # Log for observability
        self.logger.info(
            "Echo request received",
            extra={
                "caller": caller_id,
                "message_length": len(message),
                "echo_count": self._echo_count
            }
        )

        # Build response
        response_text = f"[Echo #{self._echo_count}] {message}"

        if metadata:
            response_text += f"\nMetadata: {metadata}"

        # Return as A2A TaskResult
        return TaskResult(
            status="completed",
            messages=[
                Message(
                    role="assistant",
                    parts=[TextPart(text=response_text)]
                )
            ],
            artifacts=[
                {
                    "type": "echo_stats",
                    "data": {
                        "original_message": message,
                        "echo_count": self._echo_count,
                        "caller": caller_id
                    }
                }
            ]
        )

    @capability("stats")
    async def get_stats(self) -> TaskResult:
        """
        Get agent statistics.

        Returns:
            TaskResult with agent stats
        """
        return TaskResult(
            status="completed",
            messages=[
                Message(
                    role="assistant",
                    parts=[
                        TextPart(
                            text=f"Echo Agent Statistics\n"
                                 f"Total echoes: {self._echo_count}\n"
                                 f"Agent ID: {self.spiffe_id}"
                        )
                    ]
                )
            ]
        )


async def main():
    """Run the echo agent."""
    # Load configuration from file
    # This includes identity, authorization, transport settings
    agent = EchoAgent.from_config("config/agent.yaml")

    # Start the agent server
    # This will:
    # 1. Connect to SPIRE to get SVID
    # 2. Start HTTPS server with mTLS
    # 3. Publish Agent Card at /.well-known/agent.json
    # 4. Listen for incoming tasks
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Configuration File

```yaml
# config/agent.yaml
agent:
  name: "echo"
  trust_domain: "agentweave.io"
  description: "Simple echo agent for testing and demonstration"

  capabilities:
    - name: "echo"
      description: "Echo messages back to caller"
      input_modes: ["text/plain", "application/json"]
      output_modes: ["text/plain", "application/json"]

    - name: "stats"
      description: "Get agent statistics"
      input_modes: []
      output_modes: ["application/json"]

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"
  allowed_trust_domains:
    - "agentweave.io"

authorization:
  provider: "opa"
  opa_endpoint: "http://localhost:8181"
  policy_path: "agentweave/authz"
  default_action: "deny"

  audit:
    enabled: true
    destination: "stdout"  # For demo; use file:// in production

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"

  connection_pool:
    max_connections: 10
    idle_timeout_seconds: 30

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

### Authorization Policy

```rego
# config/policies/authz.rego
package agentweave.authz

import rego.v1

# Default deny - nothing allowed unless explicitly permitted
default allow := false

# Allow any agent in our trust domain to call echo
allow if {
    is_same_trust_domain
    input.action == "echo"
}

# Allow any agent in our trust domain to get stats
allow if {
    is_same_trust_domain
    input.action == "stats"
}

# Helper: Check if caller is in same trust domain
is_same_trust_domain if {
    caller_domain := extract_trust_domain(input.caller_spiffe_id)
    caller_domain == "agentweave.io"
}

# Helper: Extract trust domain from SPIFFE ID
extract_trust_domain(spiffe_id) := domain if {
    parts := split(spiffe_id, "/")
    domain := parts[2]  # spiffe://trust-domain/...
}
```

## Infrastructure Setup

### Docker Compose

```yaml
# docker-compose.yaml
version: '3.8'

services:
  # SPIRE Server - Issues SVIDs
  spire-server:
    image: ghcr.io/spiffe/spire-server:1.9.0
    hostname: spire-server
    volumes:
      - ./spire/server.conf:/opt/spire/conf/server/server.conf:ro
      - spire-server-data:/opt/spire/data
    command: ["-config", "/opt/spire/conf/server/server.conf"]
    networks:
      - agentweave
    healthcheck:
      test: ["CMD", "/opt/spire/bin/spire-server", "healthcheck"]
      interval: 10s
      timeout: 5s
      retries: 5

  # SPIRE Agent - Provides Workload API
  spire-agent:
    image: ghcr.io/spiffe/spire-agent:1.9.0
    hostname: spire-agent
    depends_on:
      spire-server:
        condition: service_healthy
    volumes:
      - ./spire/agent.conf:/opt/spire/conf/agent/agent.conf:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - spire-agent-socket:/run/spire/sockets
    command: ["-config", "/opt/spire/conf/agent/agent.conf"]
    networks:
      - agentweave
    healthcheck:
      test: ["CMD", "/opt/spire/bin/spire-agent", "healthcheck"]
      interval: 10s
      timeout: 5s
      retries: 5

  # OPA - Policy enforcement
  opa:
    image: openpolicyagent/opa:0.62.0
    hostname: opa
    volumes:
      - ./config/policies:/policies:ro
    command:
      - "run"
      - "--server"
      - "--addr=0.0.0.0:8181"
      - "/policies"
    ports:
      - "8181:8181"
    networks:
      - agentweave
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:8181/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Echo Agent
  echo-agent:
    build:
      context: .
      dockerfile: Dockerfile
    depends_on:
      spire-agent:
        condition: service_healthy
      opa:
        condition: service_healthy
    volumes:
      - spire-agent-socket:/run/spire/sockets:ro
      - ./config:/etc/agentweave:ro
    ports:
      - "8443:8443"  # Agent API
      - "9090:9090"  # Metrics
    networks:
      - agentweave
    environment:
      - AGENTWEAVE_CONFIG=/etc/agentweave/agent.yaml

volumes:
  spire-server-data:
  spire-agent-socket:

networks:
  agentweave:
    driver: bridge
```

### SPIRE Configuration

```hcl
# spire/server.conf
server {
    bind_address = "0.0.0.0"
    bind_port = "8081"
    trust_domain = "agentweave.io"
    data_dir = "/opt/spire/data"
    log_level = "DEBUG"
}

plugins {
    DataStore "sql" {
        plugin_data {
            database_type = "sqlite3"
            connection_string = "/opt/spire/data/datastore.sqlite3"
        }
    }

    KeyManager "memory" {
        plugin_data {}
    }

    NodeAttestor "join_token" {
        plugin_data {}
    }
}
```

```hcl
# spire/agent.conf
agent {
    data_dir = "/opt/spire/data"
    log_level = "DEBUG"
    server_address = "spire-server"
    server_port = "8081"
    socket_path = "/run/spire/sockets/agent.sock"
    trust_domain = "agentweave.io"
}

plugins {
    NodeAttestor "join_token" {
        plugin_data {}
    }

    KeyManager "memory" {
        plugin_data {}
    }

    WorkloadAttestor "docker" {
        plugin_data {}
    }
}
```

## Running the Example

### Step 1: Clone and Setup

```bash
# Clone examples repository
git clone https://github.com/agentweave/examples.git
cd examples/simple-agent

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Start Infrastructure

```bash
# Start SPIRE and OPA
docker-compose up -d spire-server spire-agent opa

# Wait for services to be healthy
docker-compose ps

# Register the echo agent workload with SPIRE
docker-compose exec spire-server \
    /opt/spire/bin/spire-server entry create \
    -spiffeID spiffe://agentweave.io/agent/echo \
    -parentID spiffe://agentweave.io/agent/spire-agent \
    -selector docker:label:com.docker.compose.service:echo-agent
```

### Step 3: Run the Agent

```bash
# Option 1: Run with Docker Compose
docker-compose up echo-agent

# Option 2: Run locally (requires SPIRE agent socket access)
python echo_agent.py
```

### Step 4: Test the Agent

```bash
# Install AgentWeave CLI
pip install agentweave-cli

# Call the echo capability
agentweave call \
    --target spiffe://agentweave.io/agent/echo \
    --capability echo \
    --data '{"message": "Hello, AgentWeave!"}'

# Get agent statistics
agentweave call \
    --target spiffe://agentweave.io/agent/echo \
    --capability stats
```

## Expected Output

### Echo Capability Response

```json
{
  "status": "completed",
  "messages": [
    {
      "role": "assistant",
      "parts": [
        {
          "type": "text",
          "text": "[Echo #1] Hello, AgentWeave!"
        }
      ]
    }
  ],
  "artifacts": [
    {
      "type": "echo_stats",
      "data": {
        "original_message": "Hello, AgentWeave!",
        "echo_count": 1,
        "caller": "spiffe://agentweave.io/client/cli"
      }
    }
  ]
}
```

### Agent Logs

```json
{
  "timestamp": "2025-12-07T10:30:15Z",
  "level": "INFO",
  "message": "Echo request received",
  "caller": "spiffe://agentweave.io/client/cli",
  "message_length": 20,
  "echo_count": 1
}
```

### Metrics

```
# HELP agentweave_tasks_total Total tasks processed
# TYPE agentweave_tasks_total counter
agentweave_tasks_total{capability="echo",status="completed"} 1.0

# HELP agentweave_task_duration_seconds Task processing duration
# TYPE agentweave_task_duration_seconds histogram
agentweave_task_duration_seconds_bucket{capability="echo",le="0.01"} 1.0
```

## Key Takeaways

### What the SDK Did Automatically

1. **Identity Management**
   - Connected to SPIRE agent
   - Fetched X.509 SVID
   - Set up automatic rotation

2. **Security**
   - Established mTLS connection
   - Verified caller's SPIFFE ID
   - Checked OPA policy before executing capability
   - Logged all requests for audit

3. **Communication**
   - Started HTTPS server
   - Published Agent Card at `/.well-known/agent.json`
   - Handled A2A protocol encoding/decoding

4. **Observability**
   - Exposed Prometheus metrics
   - Structured JSON logging
   - Request tracing

### What You Wrote

- Business logic (12 lines in `echo()` method)
- Configuration (YAML)
- Authorization policy (Rego)

## Next Steps

- **Add More Capabilities**: Extend with `@capability` decorators
- **Multi-Agent**: See [Multi-Agent Example](multi-agent/) to call other agents
- **Custom Policies**: Learn [Authorization Guide](/agentweave/guides/policy-patterns/)
- **Production Deploy**: See [Kubernetes Deployment](/agentweave/deployment/kubernetes/)

## Troubleshooting

### Agent Won't Start

```bash
# Check SPIRE agent is running
docker-compose ps spire-agent

# Check SVID was issued
docker-compose exec spire-server \
    /opt/spire/bin/spire-server entry show \
    -spiffeID spiffe://agentweave.io/agent/echo
```

### Authorization Denied

```bash
# Test OPA policy directly
curl -X POST http://localhost:8181/v1/data/agentweave/authz \
  -d '{
    "input": {
      "caller_spiffe_id": "spiffe://agentweave.io/client/test",
      "action": "echo"
    }
  }'
```

### Connection Refused

```bash
# Check agent is listening
netstat -tlnp | grep 8443

# Check firewall/Docker network
docker-compose logs echo-agent
```

---

**Complete Code**: [GitHub Repository](https://github.com/agentweave/examples/tree/main/simple-agent)
