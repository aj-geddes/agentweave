# AgentWeave SDK

**Build cross-cloud AI agents with security by default.**

The AgentWeave SDK (`agentweave`) is a Python library for building AI agents with cryptographic identity, mutual TLS authentication, and policy-based authorization built-in. The SDK ensures **the secure path is the only path**—developers cannot accidentally bypass security controls.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![SPIFFE](https://img.shields.io/badge/SPIFFE-compliant-green.svg)](https://spiffe.io/)
[![A2A](https://img.shields.io/badge/A2A-protocol-orange.svg)](https://a2a-protocol.org/)

## Features

- **Cryptographic Identity**: SPIFFE/SPIRE workload identities with automatic rotation
- **Mutual TLS**: All agent communication encrypted and authenticated by default
- **Policy Enforcement**: Open Policy Agent (OPA) authorization on every request
- **A2A Protocol**: Standards-based agent-to-agent communication
- **Framework Agnostic**: Works with any agent framework (LangGraph, CrewAI, etc.)
- **Cross-Cloud**: Deploy agents across AWS, GCP, Azure, on-prem
- **Zero Trust**: No shared secrets, no API keys, no passwords

## Quick Start

### Installation

```bash
pip install agentweave
```

### Your First Agent

```python
from agentweave import SecureAgent, capability

class HelloAgent(SecureAgent):
    @capability("greet")
    async def greet(self, name: str) -> dict:
        return {"message": f"Hello, {name}!"}

if __name__ == "__main__":
    agent = HelloAgent.from_config("config.yaml")
    agent.run()
```

**config.yaml**:
```yaml
agent:
  name: "hello-agent"
  trust_domain: "example.com"
  capabilities:
    - name: "greet"
      description: "Greet someone"

identity:
  provider: "spiffe"
  allowed_trust_domains:
    - "example.com"

authorization:
  provider: "opa"
  default_action: "deny"

server:
  port: 8443
```

The SDK wires together:
- **SPIFFE identity** — fetched from your local SPIRE agent (or via static mTLS certs for development)
- **OPA authorization** — policy checked before every capability is executed
- **A2A server** — FastAPI-based JSON-RPC 2.0 endpoint with Agent Card discovery
- **mTLS transport** — all outbound calls use your SVID certificate

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      AgentWeave SDK                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Your Agent Code                                                │
│  └── @capability decorators                                    │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Identity Layer (SPIFFE)                                  │ │
│  │  • Cryptographic workload identity                        │ │
│  │  • Automatic certificate rotation                         │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Authorization Layer (OPA)                                │ │
│  │  • Policy-based access control                            │ │
│  │  • Default deny, explicit allow                           │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Communication Layer (A2A)                                │ │
│  │  • Agent-to-agent protocol                                │ │
│  │  • Capability discovery                                   │ │
│  │  • Task-based communication                               │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │  Transport Layer (mTLS)                                   │ │
│  │  • TLS 1.3 enforced                                       │ │
│  │  • Mutual authentication                                  │ │
│  │  • Connection pooling, circuit breakers                   │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │ SPIRE Agent       │ (identity)
                    │ OPA               │ (policy)
                    └───────────────────┘
```

## Key Concepts

### Identity with SPIFFE

Every agent has a cryptographic identity (SPIFFE ID):

```
spiffe://agentweave.io/agent/data-processor/prod
         └── trust domain    └── workload path
```

SPIRE automatically:
- Issues X.509 certificates (SVIDs) to workloads
- Rotates certificates before expiry
- Federates trust across organizations

### Authorization with OPA

All requests are authorized by policy before execution:

```rego
package agentweave.authz

default allow = false

# Allow orchestrator to call processor
allow {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/orchestrator/prod"
    input.callee_spiffe_id == "spiffe://agentweave.io/agent/processor/prod"
    input.action == "process"
}
```

### Communication with A2A

Agents communicate using the A2A protocol:

```python
# Orchestrator calls processor
result = await self.call_agent(
    target="spiffe://agentweave.io/agent/processor/prod",
    task_type="process",
    payload={"data": records}
)
```

Behind the scenes:
1. SDK checks OPA policy (can orchestrator call processor?)
2. Establishes mTLS using SPIFFE identities
3. Sends A2A task over encrypted channel
4. Processor validates caller identity
5. Processor checks OPA policy (allow this caller?)
6. Executes business logic, returns result
7. All steps audited and logged

## Examples

### Simple Agent

See [examples/simple_agent/](examples/simple_agent/) for a minimal echo agent.

### Multi-Agent System

See [examples/multi_agent/](examples/multi_agent/) for an orchestrator + worker pattern with:
- Agent-to-agent communication
- Load distribution
- Error handling
- Health checks

Run it:
```bash
cd examples/multi_agent
docker-compose up
```

### Federated Agents

See [examples/federated/](examples/federated/) for cross-organization agent communication.

## Documentation

- [Quick Start Guide](docs/quickstart.md) - Get your first agent running
- [Configuration Reference](docs/configuration.md) - All config options
- [Security Guide](docs/security.md) - SPIFFE/SPIRE setup, hardening
- [A2A Protocol](docs/a2a-protocol.md) - Agent communication deep dive

## Use Cases

### Multi-Cloud Agent Coordination

Deploy agents across AWS, GCP, Azure with automatic secure communication:

```yaml
# AWS Agent
agent:
  name: "aws-processor"
  trust_domain: "agentweave.io"

# GCP Agent
agent:
  name: "gcp-analytics"
  trust_domain: "agentweave.io"
```

SPIRE federation enables cross-cloud identity trust. Tailscale (optional) provides network connectivity.

### Hierarchical Agent Systems

Build orchestrator agents that coordinate specialist agents:

```
Orchestrator
├── Search Agent (queries databases)
├── Analytics Agent (runs ML models)
└── Reporting Agent (generates reports)
```

Each agent:
- Has unique SPIFFE identity
- Enforces OPA policies
- Communicates via A2A
- Independently deployable

### Third-Party Agent Integration

Integrate with agents from other frameworks:

```python
# Call another AgentWeave agent (SPIFFE mTLS enforced)
result = await self.call_agent(
    target="spiffe://partner.example.com/agent/summarizer",
    task_type="summarize",
    payload={"text": document},
)
```

AgentWeave agents communicate via mTLS with SPIFFE identity. For non-AgentWeave agents, use the `A2AClient` directly with appropriate transport configuration.

## Security Guarantees

| Guarantee | Mechanism |
|-----------|-----------|
| Every agent has cryptographic identity | SPIFFE SVID |
| No agent can start without identity | SDK refuses to start |
| All traffic encrypted | TLS 1.3 mandatory |
| Mutual authentication | mTLS with peer verification |
| No request without authorization | OPA check before handler |
| Credentials auto-rotate | SPIRE handles rotation |
| No hardcoded secrets | Runtime identity issuance |
| Full audit trail | Every decision logged |

**Design Principle**: "Can't mess it up unless the config is wrong."

Security is enforced by the SDK, not by developer discipline.

## Deployment

### Kubernetes

```bash
# Install SPIRE
helm install spire spiffe/spire --namespace spire-system

# Register agent
spire-server entry create \
  -spiffeID spiffe://agentweave.io/agent/processor/prod \
  -parentID spiffe://agentweave.io/k8s-node \
  -selector k8s:ns:agentweave \
  -selector k8s:sa:processor

# Deploy agent
kubectl apply -f agent-deployment.yaml
```

See [docs/security.md](docs/security.md) for complete Kubernetes setup.

### Docker Compose

```bash
cd examples/multi_agent
docker-compose up
```

Includes:
- SPIRE Server + Agent
- OPA
- Orchestrator agent
- 3x Worker agents
- OpenTelemetry Collector

## Requirements

- Python 3.11+
- SPIRE Server + Agent (for SPIFFE identity in production; optional for dev with static mTLS)
- OPA (for authorization; optional for dev with `allow-all` provider)
- Docker (for local development and integration tests)
- Kubernetes (for production deployment)

## Development

### Install from Source

```bash
git clone https://github.com/aj-geddes/agentweave
cd agentweave
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### Run Tests

```bash
pytest
```

### Run Examples

```bash
# Start infrastructure
docker-compose up -d

# Run simple agent
cd examples/simple_agent
python main.py
```

## CLI Tools

```bash
# Validate configuration
agentweave validate config.yaml

# Generate Agent Card
agentweave card generate config.yaml

# Test connectivity
agentweave ping spiffe://agentweave.io/agent/target

# Check authorization
agentweave authz check \
  --caller spiffe://agentweave.io/agent/a \
  --callee spiffe://agentweave.io/agent/b \
  --action process
```

## Observability

### Metrics

Prometheus metrics at `:9090/metrics`:

```
agentweave_requests_total{action="process",status="success"}
agentweave_request_duration_seconds{action="process"}
agentweave_authz_denied_total{reason="policy"}
agentweave_svid_rotation_total
```

### Tracing

OpenTelemetry traces with automatic context propagation:

```python
# Traces include:
# - Agent-to-agent calls
# - SPIRE identity fetches
# - OPA policy evaluations
# - Business logic execution
```

### Logging

Structured JSON logs:

```json
{
  "timestamp": "2025-12-06T10:30:00Z",
  "level": "INFO",
  "message": "Request completed",
  "caller_spiffe_id": "spiffe://agentweave.io/agent/orchestrator",
  "action": "process",
  "duration_ms": 45,
  "trace_id": "a1b2c3d4..."
}
```

## Roadmap

### Phase 1: Foundation (v1.0 — current)
- [x] SPIFFE identity integration
- [x] OPA authorization with decision caching and circuit breaker
- [x] A2A protocol server and client (JSON-RPC 2.0 + SSE)
- [x] mTLS transport (TLS 1.3 by default)
- [x] Static mTLS provider for development
- [x] CLI tools (validate, card, authz check, health)
- [x] Testing utilities (mocks, fixtures, OPA policy simulator)

### Phase 2: Production Hardening (v1.1)
- [ ] Helm chart and production Kubernetes manifests
- [ ] Full OpenTelemetry observability integration
- [ ] OPA policy library (common agent patterns)
- [ ] SVID watcher using SPIFFE streaming API (replace polling)
- [ ] Load testing benchmarks
- [ ] Security audit

### Phase 3: Ecosystem (v1.2+)
- [ ] LangGraph integration example
- [ ] CrewAI integration example
- [ ] Google ADK compatibility layer
- [ ] SPIRE federation cookbook

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

Apache 2.0 - See [LICENSE](LICENSE)

## Support

- Documentation: [docs/](docs/)
- Examples: [examples/](examples/)
- Issues: [GitHub Issues](https://github.com/aj-geddes/agentweave/issues)
- Discussions: [GitHub Discussions](https://github.com/aj-geddes/agentweave/discussions)

## Acknowledgments

Built on top of excellent open source projects:
- [SPIFFE/SPIRE](https://spiffe.io/) - Identity framework
- [Open Policy Agent](https://www.openpolicyagent.org/) - Policy engine
- [A2A Protocol](https://a2a-protocol.org/) - Agent communication standard
- [py-spiffe](https://github.com/HewlettPackard/py-spiffe) - Python SPIFFE library

## Citation

If you use AgentWeave SDK in research, please cite:

```bibtex
@software{agentweave,
  title = {AgentWeave SDK},
  author = {AgentWeave Team},
  year = {2026},
  url = {https://github.com/aj-geddes/agentweave}
}
```

---

**AgentWeave SDK** - Building secure AI agent systems, one capability at a time.
