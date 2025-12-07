# AgentWeave SDK (hvs-agent-pathfinder)

## Project Overview

**Product**: AgentWeave SDK (agentweave)

**Purpose**: Python SDK for building secure, cross-cloud AI agents with cryptographic identity and automatic authorization

**Core Principle**: "The secure path is the only path" - developers cannot bypass security

**Product Specification**: See `spec.md` for detailed specifications

## Development Instructions

**ALWAYS Use Sub-agents for every task**

**Never use the main context for tasks**

All development work should be done through sub-agents to maintain proper context isolation and task management.

## Key Technologies

- **SPIFFE/SPIRE** - Cryptographic workload identity
- **A2A Protocol** - Agent-to-agent communication (JSON-RPC 2.0)
- **OPA** - Policy-based authorization (Rego)
- **Tailscale (optional)** - Cross-cloud mesh networking

## Project Structure

```
agentweave/
├── __init__.py, config.py, exceptions.py  # Core
├── agent.py, decorators.py, context.py    # Agent classes
├── identity/                               # SPIFFE identity layer
├── authz/                                  # OPA authorization
├── transport/                              # mTLS transport
├── comms/a2a/                             # A2A protocol
├── observability/                          # Metrics, tracing, logging
├── cli/                                    # CLI tools
└── testing/                                # Test utilities
```

## Development Guidelines

1. **ALWAYS use sub-agents for tasks** - Maintain proper context isolation
2. **Security is mandatory** - No bypass allowed; security is always enforced
3. **All communication uses mTLS** - Cryptographic identity required
4. **Default deny authorization in production** - Explicit policies required

## Key Commands

- `agentweave validate <config.yaml>` - Validate configuration
- `agentweave serve <config.yaml>` - Start agent server
- `agentweave card generate <config.yaml>` - Generate Agent Card
- `agentweave authz check` - Test authorization policies

## Testing

- Run tests: `pytest`
- With coverage: `pytest --cov=agentweave`
- Integration tests: `pytest --run-integration`

## Documentation

- `docs/quickstart.md` - Getting started guide
- `docs/configuration.md` - Configuration reference
- `docs/security.md` - Security guide
- `docs/a2a-protocol.md` - A2A protocol reference

## Deployment

- Kubernetes manifests in `deploy/kubernetes/`
- Helm chart in `deploy/helm/agentweave/`
- Docker Compose for development in `deploy/docker-compose.yaml`

## Security Principles

- Cryptographic identity for all workloads
- mTLS for all agent-to-agent communication
- Policy-based authorization with OPA
- Zero-trust architecture by default
- Secure by design - no security bypasses possible
