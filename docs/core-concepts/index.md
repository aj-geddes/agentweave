---
layout: page
title: Core Concepts
description: Fundamental concepts behind the AgentWeave SDK's secure-by-default architecture
permalink: /core-concepts/
nav_order: 3
has_children: true
---

# Core Concepts

Understanding the core concepts behind AgentWeave is essential for building secure, production-ready AI agents. This section explains the fundamental principles, components, and patterns that make AgentWeave unique.

## Why These Concepts Matter

AgentWeave isn't just another agent framework—it's a **security-first SDK** built on battle-tested, production-grade infrastructure components. Unlike traditional frameworks where security is an afterthought or opt-in feature, AgentWeave makes **the secure path the only path**.

Every agent you build automatically gets:
- **Cryptographic identity** via SPIFFE/SPIRE
- **Mutual TLS authentication** for all communication
- **Policy-based authorization** via OPA
- **Comprehensive audit logging**

You cannot accidentally build an insecure agent. The SDK's architecture prevents security bypasses at compile time and runtime.

## How These Concepts Work Together

```
┌──────────────────────────────────────────────────────────┐
│                    Your Agent Code                       │
│           @capability decorated methods                  │
└─────────────────────┬────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────┐
│                  SecureAgent Base                        │
│  • Lifecycle management                                  │
│  • Configuration loading                                 │
│  • Capability registration                               │
└───┬──────────────────┬─────────────────┬────────────────┘
    │                  │                 │
    │ Identity         │ Authorization   │ Communication
    │                  │                 │
┌───▼──────┐     ┌─────▼─────┐    ┌─────▼──────────┐
│ SPIFFE   │     │    OPA    │    │  A2A Protocol  │
│ Identity │────▶│  Policies │    │  Task System   │
└──────────┘     └───────────┘    └────────────────┘
     │                  │                 │
     └──────────────────┴─────────────────┘
                        │
                ┌───────▼────────┐
                │  mTLS Channel  │
                │  TLS 1.3       │
                └────────────────┘
```

Every agent request flows through these security layers automatically:

1. **Identity Layer**: Proves "who" is making the request using SPIFFE SVIDs
2. **Transport Layer**: Encrypts and authenticates the connection using mTLS
3. **Authorization Layer**: Decides "what" the caller is allowed to do via OPA policies
4. **Communication Layer**: Delivers the request using A2A protocol

## Learning Path

We recommend reading these documents in order:

### 1. Start with Architecture
[**System Architecture**](/agentweave/core-concepts/architecture/) provides the big picture—how all components fit together and how requests flow through the system.

### 2. Understand Agents
[**Understanding Agents**](/agentweave/core-concepts/agents/) explains what SecureAgent is, the agent lifecycle, capabilities, and how to configure agents.

### 3. Master Identity
[**Identity & SPIFFE**](/agentweave/core-concepts/identity/) covers cryptographic identity—the foundation of AgentWeave's security model.

### 4. Learn Authorization
[**Authorization & OPA**](/agentweave/core-concepts/authorization/) shows how policy-based access control protects your agents.

### 5. Explore Communication
[**A2A Protocol**](/agentweave/core-concepts/communication/) details how agents talk to each other using the Agent-to-Agent protocol.

### 6. Internalize the Security Model
[**Security Model**](/agentweave/core-concepts/security-model/) ties everything together, explaining the zero-trust architecture and defense-in-depth approach.

## Key Principles

### The Secure Path is the Only Path

Unlike traditional frameworks where you might do this:

```python
# ❌ Traditional framework - insecure by default
class MyAgent:
    def process(self, request):
        # No identity verification
        # No authorization check
        # No encryption
        return process_data(request)
```

With AgentWeave, security is **mandatory and automatic**:

```python
# ✅ AgentWeave - secure by default
class MyAgent(SecureAgent):
    @capability("process")
    async def process(self, request: dict) -> TaskResult:
        # SDK already verified caller identity
        # SDK already checked authorization policy
        # SDK already established encrypted channel
        # You just write business logic
        return await process_data(request)
```

### Configuration, Not Code

Security decisions are made in **configuration and policies**, not in your application code:

```yaml
# config.yaml - Security is declarative
identity:
  provider: "spiffe"
  trust_domain: "mycompany.com"

authorization:
  provider: "opa"
  default_action: "deny"  # Default deny in production

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"  # Cannot be disabled
```

### Defense in Depth

AgentWeave implements multiple security layers. Even if one layer has a misconfiguration, other layers provide protection:

- **Layer 1**: Identity verification prevents impersonation
- **Layer 2**: mTLS prevents man-in-the-middle attacks
- **Layer 3**: Authorization prevents privilege escalation
- **Layer 4**: Audit logging detects anomalies

## Common Questions

### Do I need to understand SPIFFE/SPIRE deeply?

**No.** You need to understand the concepts (SPIFFE IDs, SVIDs, trust domains) but the SDK handles the complexity. You'll mainly interact with configuration.

### Do I need to learn the Rego policy language?

**For basic use, no.** AgentWeave provides default policies that work for most scenarios. For advanced authorization rules, yes—but Rego is straightforward and well-documented.

### Can I use AgentWeave without Kubernetes?

**Yes.** While Kubernetes is the primary deployment target, AgentWeave works anywhere you can run containers (Docker, ECS, Cloud Run, etc.). SPIRE and OPA can run as sidecars or daemons.

### What if I need to integrate with non-AgentWeave systems?

AgentWeave agents can call external services. The A2A protocol is optional for external integrations—you can make standard HTTP/gRPC calls with the same mTLS transport layer.

## What's Next?

Start with [System Architecture](/agentweave/core-concepts/architecture/) to understand how AgentWeave components work together, then dive into each concept in depth.

{: .note }
Throughout this documentation, you'll see callouts highlighting important security considerations, best practices, and common pitfalls. Pay special attention to these—they represent lessons learned from production deployments.
