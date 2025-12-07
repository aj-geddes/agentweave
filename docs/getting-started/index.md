---
layout: page
title: Getting Started
description: Learn how to build secure, cross-cloud AI agents with AgentWeave SDK
nav_order: 2
has_children: true
---

# Getting Started with AgentWeave

Welcome to AgentWeave, the Python SDK for building secure, cross-cloud AI agents with cryptographic identity and automatic authorization.

## What You'll Learn

This Getting Started guide will take you from installation to running your first secure agent in minutes. You'll learn:

- How to install and set up the AgentWeave SDK
- Core concepts and security principles
- Building and running your first agent
- Understanding the agent lifecycle and communication patterns
- Testing and debugging your agents

## Prerequisites

Before you begin, ensure you have:

- **Python 3.10 or higher** - AgentWeave uses modern Python features including async/await
- **Docker** (optional) - For running local SPIRE and OPA infrastructure during development
- **Basic async knowledge** - Familiarity with Python's `async`/`await` syntax
- **Terminal/command line** - Comfortable running commands and editing files

## Learning Path

We recommend following this sequence:

1. **[Installation](installation.md)** - Install AgentWeave and verify your setup
2. **[5-Minute Quickstart](quickstart.md)** - Get your first agent running immediately
3. **[Core Concepts](concepts.md)** - Understand AgentWeave's architecture and security model
4. **[Hello World Tutorial](hello-world.md)** - Build a complete agent with detailed explanations

## The AgentWeave Philosophy

AgentWeave is built on a core principle: **"The secure path is the only path."**

This means:
- You cannot accidentally bypass security
- Identity verification is automatic and mandatory
- All communication uses mutual TLS authentication
- Authorization is enforced before your code runs
- Developers focus on business logic, not security plumbing

Traditional agent frameworks require you to:
```python
# Manual security - easy to get wrong
if not verify_caller(request.cert):
    raise Unauthorized()
if not check_permissions(caller, action):
    raise Forbidden()
# Finally... business logic
return process_data(request.data)
```

With AgentWeave, security is handled automatically:
```python
from agentweave import SecureAgent, capability

class MyAgent(SecureAgent):
    @capability("process_data")
    async def process(self, data: dict) -> dict:
        # Identity verified ✓
        # Authorization checked ✓
        # Just implement your logic
        return await self._process(data)
```

## What Makes AgentWeave Different?

### Cryptographic Identity
Every agent has a SPIFFE identity (like `spiffe://yourorg.com/agent/processor`). No API keys, no passwords, no secrets to leak.

### Zero-Trust by Default
Agents authenticate each other using mutual TLS. Authorization policies are enforced via Open Policy Agent (OPA). Default deny in production.

### Cross-Cloud Ready
Built on cloud-native technologies (SPIFFE, mTLS, OPA). Deploy agents across AWS, GCP, Azure, or on-premises and they can securely communicate.

### Framework Agnostic
Uses the A2A (Agent-to-Agent) protocol, an open standard. Your AgentWeave agents can communicate with agents built using Google's ADK, AWS Bedrock AgentCore, or any A2A-compatible framework.

### Developer Friendly
- Decorator-based API for defining capabilities
- Type-safe communication
- Comprehensive testing utilities
- Rich observability (metrics, tracing, logging)
- Helpful CLI tools

## Support and Resources

- **Documentation**: Full reference at [aj-geddes.github.io/agentweave](https://aj-geddes.github.io/agentweave/)
- **Examples**: Check the [examples/](https://github.com/aj-geddes/agentweave/tree/main/examples) directory
- **Issues**: Report bugs at [GitHub Issues](https://github.com/aj-geddes/agentweave/issues)
- **Discussions**: Ask questions in [GitHub Discussions](https://github.com/aj-geddes/agentweave/discussions)
- **Specification**: Read the full [spec.md](https://github.com/aj-geddes/agentweave/blob/main/spec.md)

## Ready to Start?

Head over to [Installation](installation.md) to get AgentWeave installed and begin your journey!

---

**Next**: [Installation Guide →](installation.md)
