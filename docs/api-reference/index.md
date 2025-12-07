---
layout: api
title: API Reference
parent: API Reference
nav_order: 1
---

# API Reference

Welcome to the AgentWeave SDK API reference documentation. This section provides detailed information about all classes, functions, and modules in the SDK.

## Package Structure

The AgentWeave SDK is organized into the following modules:

```
agentweave/
├── agent.py              # Core agent classes (BaseAgent, SecureAgent)
├── decorators.py         # Security decorators (@capability, @requires_peer, @audit_log)
├── context.py            # Request context management
├── config.py             # Configuration models (Pydantic-based)
├── exceptions.py         # Custom exceptions
├── identity/             # Identity providers (SPIFFE, mTLS)
├── authz/                # Authorization (OPA)
├── transport/            # Transport layer (mTLS channels, connection pools)
├── comms/                # Communication (A2A protocol, discovery)
└── observability/        # Metrics, tracing, logging
```

## Import Conventions

### Basic Imports

```python
from agentweave import SecureAgent, BaseAgent, AgentConfig
from agentweave import capability, requires_peer, audit_log
from agentweave import RequestContext, get_current_context
```

### Advanced Imports

```python
from agentweave.config import (
    AgentConfig,
    Environment,
    IdentityProvider,
    AuthorizationProvider,
)
from agentweave.identity import SPIFFEIdentityProvider
from agentweave.authz import OPAEnforcer
from agentweave.transport import SecureChannel
```

## Version Information

**Current Version**: 1.0.0

**License**: Apache-2.0

**Author**: High Velocity Solutions LLC

## Core Modules

### Agent Module
[agent.md](agent.md) - Core agent classes for building secure agents

**Key Classes:**
- `AgentConfig` - Agent configuration dataclass (legacy, see config module for full Pydantic version)
- `BaseAgent` - Abstract base class for all agents
- `SecureAgent` - Concrete agent with automatic capability registration

### Decorators Module
[decorators.md](decorators.md) - Security decorators for capability methods

**Key Decorators:**
- `@capability(name, description)` - Register a method as an agent capability
- `@requires_peer(spiffe_pattern)` - Restrict capability to specific SPIFFE IDs
- `@audit_log(level)` - Enable audit logging for capability calls

### Context Module
[context.md](context.md) - Request context management for tracking caller identity

**Key Classes:**
- `RequestContext` - Dataclass containing caller identity and task metadata

**Key Functions:**
- `get_current_context()` - Get the current request context
- `set_current_context(context)` - Set the request context

### Configuration Module
[config.md](config.md) - Comprehensive Pydantic-based configuration system

**Key Classes:**
- `AgentConfig` - Main configuration class with security validation
- `AgentSettings` - Core agent settings
- `IdentityConfig` - Identity provider configuration
- `AuthorizationConfig` - Authorization settings
- `TransportConfig` - Transport layer configuration
- `ServerConfig` - Server endpoint configuration
- `ObservabilityConfig` - Metrics, tracing, and logging

## Quick Reference

### Creating an Agent

```python
from agentweave import SecureAgent, capability

class DataSearchAgent(SecureAgent):
    @capability("search", description="Search the database")
    async def search(self, query: str) -> dict:
        return {"results": [...]}

# From config file
agent = DataSearchAgent.from_config("config.yaml")

# From dict
config = {
    "name": "search-agent",
    "trust_domain": "agentweave.io"
}
agent = DataSearchAgent.from_dict(config)
```

### Calling Another Agent

```python
result = await agent.call_agent(
    target="spiffe://agentweave.io/agent/data-processor",
    task_type="process",
    payload={"data": [1, 2, 3]},
    timeout=30.0
)
```

### Adding Security Controls

```python
from agentweave import capability, requires_peer, audit_log

class SecureDataAgent(SecureAgent):
    @capability("delete_data", description="Delete sensitive data")
    @requires_peer("spiffe://agentweave.io/agent/admin-*")
    @audit_log(level="warning")
    async def delete_data(self, id: str) -> dict:
        # Only admin agents can call this
        return {"deleted": id}
```

## Design Principles

The AgentWeave SDK is built on the principle of **"The secure path is the only path"**:

- **No agent can start without verified identity** - SPIFFE/SPIRE integration is mandatory
- **No communication without mTLS** - All agent-to-agent communication is mutually authenticated
- **No request without authorization** - OPA policies enforce access control on every request
- **Security is SDK-internal** - Developers cannot bypass or disable security features

## Next Steps

- Read the [agent module documentation](agent.md) to understand agent lifecycle
- Explore the [decorators documentation](decorators.md) to add capabilities
- Review the [configuration reference](config.md) for deployment options
- Check the [context documentation](context.md) for request tracking

## Additional Resources

- [Quickstart Guide](../quickstart.md)
- [Security Documentation](../security.md)
- [A2A Protocol Reference](../a2a-protocol.md)
- [Configuration Guide](../configuration.md)
