---
layout: page
title: "About AgentWeave - Secure AI Agent Framework"
description: "AgentWeave is an open-source Python SDK providing cryptographic identity, mandatory mTLS, and policy-based authorization for AI agents. Built on CNCF-graduated SPIFFE and OPA for zero-trust agent security."
permalink: /about/
nav_order: 12
---

# About AgentWeave

AgentWeave is the open-source security infrastructure for AI agents. It is a Python SDK that gives every agent a cryptographic identity, enforces mutual TLS on every connection, and evaluates authorization policies on every request. Built on CNCF-graduated standards, AgentWeave makes security the architecture itself -- not a feature you enable or a library you configure.

---

## Mission

**Make secure AI agents the default, not the exception.**

The AI agent economy is growing faster than the trust infrastructure to support it. Agents are negotiating contracts, processing payments, accessing sensitive data, and making decisions on behalf of organizations. The frameworks that power these agents overwhelmingly treat security as optional -- a configuration flag, an add-on library, a best practice that developers may or may not follow.

AgentWeave exists to close that gap. Our mission is to provide the trust layer that every AI agent needs so that organizations can deploy agents with confidence that they are authenticated, authorized, and auditable.

---

## The Problem We Solve

AI agent frameworks focus on what agents can do. AgentWeave focuses on ensuring agents can be trusted.

### The Current State of Agent Security

Most agent frameworks share the same security profile:

- **Identity**: API keys or bearer tokens passed in HTTP headers. Shared secrets that can be leaked, stolen, or reused. No mutual authentication.
- **Authorization**: Application-level if-statements scattered through business logic. No policy enforcement layer. No default deny.
- **Transport**: Optional TLS with no peer verification. Easy to downgrade, skip, or misconfigure.
- **Audit**: Application logging at best. No structured audit trail. No cryptographic proof of which agent performed which action.

This is not a theoretical concern. **Gartner reports that 40% of agentic AI projects are cancelled due to inadequate risk controls.** The agents work -- they just cannot be trusted in production.

### What AgentWeave Provides

AgentWeave replaces each weak link with a production-proven standard:

| Problem | Traditional Approach | AgentWeave Approach |
|---------|---------------------|---------------------|
| Identity | API keys, shared secrets | SPIFFE cryptographic identity (X.509 SVIDs) |
| Authentication | One-way TLS or none | Mandatory mutual TLS, no exceptions |
| Authorization | Application code | OPA policies with default deny |
| Audit | Application logs | OpenTelemetry traces, metrics, structured audit logs |
| Transport security | Configurable, optional | Enforced at the SDK level, cannot be bypassed |

The core design principle is simple: **the secure path is the only path.** There is no configuration option to disable identity verification. There is no flag to skip authorization. There is no way to downgrade from mTLS to plaintext. Developers using AgentWeave write business logic. The SDK handles trust.

---

## Our Approach

AgentWeave is built entirely on open standards from the Cloud Native Computing Foundation and the Linux Foundation. We chose established, battle-tested projects over proprietary alternatives for every layer of the stack.

### Why Open Standards Matter

Vendor lock-in is a security risk. When your trust infrastructure depends on a proprietary service, you inherit that vendor's security posture, uptime guarantees, and business continuity risks. Open standards eliminate this dependency.

More importantly, open standards benefit from community-wide security review. SPIFFE, OPA, and OpenTelemetry are maintained by large, active communities and have been deployed at scale by organizations including Netflix, Uber, Pinterest, Square, and major financial institutions. The security properties of these systems are well understood and continuously tested.

### Design Principles

**1. The Secure Path is the Only Path**
Security is enforced at the SDK level. Developers cannot accidentally or intentionally bypass identity verification, mTLS, or authorization. This eliminates the most common source of security failures: misconfiguration.

**2. Identity Over Credentials**
Cryptographic identity replaces shared secrets. Every agent has a SPIFFE Verifiable Identity Document (SVID) -- an X.509 certificate that is automatically rotated, cannot be exfiltrated, and provides mutual authentication. No API keys to manage, rotate, or leak.

**3. Zero Trust by Default**
Every agent-to-agent interaction requires mutual authentication and authorization. Default deny in production. Trust is verified on every request, not assumed based on network location.

**4. Policy as Code**
Authorization rules are expressed as OPA Rego policies that are version-controlled, testable, and auditable. Business rules, compliance requirements, and access controls are decoupled from application code.

**5. Observable by Default**
OpenTelemetry-native metrics, distributed tracing, and structured logging provide complete visibility into agent behavior. Every authorization decision, certificate rotation, and agent interaction is captured.

**6. Developer Experience Matters**
Security should be transparent. AgentWeave uses Python decorators, type hints, and sensible defaults to make secure development feel natural. Developers focus on business logic -- the SDK handles the security infrastructure.

---

## Technology Stack

AgentWeave integrates four CNCF-graduated or Linux Foundation projects into a cohesive security layer for AI agents.

### SPIFFE / SPIRE -- Cryptographic Identity

[SPIFFE](https://spiffe.io) (Secure Production Identity Framework for Everyone) is the CNCF-graduated standard for workload identity. SPIRE is the reference implementation. Together, they provide automatic, cryptographic identity for every AgentWeave agent.

Every agent receives a SPIFFE Verifiable Identity Document (SVID) -- an X.509 certificate with a SPIFFE ID like `spiffe://yourorg.com/agents/shopper-v2`. Certificates are automatically rotated. No shared secrets, no API keys, no manual certificate management.

### Open Policy Agent (OPA) -- Authorization

[OPA](https://www.openpolicyagent.org) is the CNCF-graduated policy engine that powers AgentWeave's authorization layer. Authorization policies are written in Rego, a purpose-built policy language that is declarative, testable, and auditable.

AgentWeave evaluates OPA policies on every agent interaction with default-deny enforcement. Policies control which agents can perform which actions, under what conditions, with what spending limits, at what times -- all without modifying agent code.

### A2A Protocol -- Agent Communication

The [A2A (Agent-to-Agent) protocol](https://a2a-protocol.org), maintained by the Linux Foundation, is an open standard for framework-agnostic agent communication. AgentWeave provides native A2A support including Agent Cards for capability discovery, JSON-RPC 2.0 messaging, task management, and streaming.

A2A enables AgentWeave agents to interoperate with agents built on other frameworks -- Google ADK, Microsoft AutoGen, LangChain, or custom platforms -- without custom integration code.

### OpenTelemetry -- Observability and Audit

[OpenTelemetry](https://opentelemetry.io) is the CNCF-graduated observability standard that powers AgentWeave's metrics, distributed tracing, and structured logging. Prometheus-compatible metrics, OTLP trace export, and structured audit logs provide complete visibility into agent behavior.

For compliance-sensitive deployments, the observability stack produces immutable audit trails that link every agent action to a cryptographic identity, a policy decision, and a timestamp.

---

## Open Source

AgentWeave is released under the **Apache License 2.0** -- a permissive, patent-safe, enterprise-friendly license.

### What Apache 2.0 Means

- **Use freely** in commercial and non-commercial projects
- **Modify and distribute** modified versions
- **Patent protection** via explicit patent grant
- **Attribution required** -- include copyright and license notice
- **Compatible** with most other open-source licenses

### Why Open Source

Agent security infrastructure must be transparent. Organizations deploying agents that process payments, access customer data, or make purchasing decisions need to audit the security layer those agents depend on. Proprietary security infrastructure requires trust in the vendor. Open-source infrastructure requires trust in the code -- which anyone can verify.

### Contributing

AgentWeave welcomes contributions from the community. Whether you are fixing a bug, adding a feature, improving documentation, or sharing deployment patterns, your contributions make agent security better for everyone.

- **GitHub Repository**: [github.com/aj-geddes/agentweave](https://github.com/aj-geddes/agentweave)
- **Issues**: [Report bugs and request features](https://github.com/aj-geddes/agentweave/issues)
- **Discussions**: [Ask questions and share patterns](https://github.com/aj-geddes/agentweave/discussions)
- **Contributing Guide**: [How to contribute]({{ '/contributing/' | relative_url }})

---

## Project Leadership

**AJ Geddes** -- Project Lead and Chief Architect
GitHub: [@aj-geddes](https://github.com/aj-geddes)
Focus: Architecture, security model, identity systems

AgentWeave is open to new maintainers. Start by contributing, demonstrate expertise, and active maintainers will invite you to join the core team. See the [Contributing Guide]({{ '/contributing/' | relative_url }}) for details.

---

## Getting Started

Ready to build secure AI agents?

1. **Install**: `pip install agentweave` (Python 3.11+)
2. **Quick Start**: [Build your first secure agent in 10 minutes]({{ '/getting-started/quickstart/' | relative_url }})
3. **Core Concepts**: [Understand the security architecture]({{ '/core-concepts/' | relative_url }})
4. **Use Cases**: [See real-world applications]({{ '/use-cases/' | relative_url }})
5. **Examples**: [Run production-ready code samples]({{ '/examples/' | relative_url }})

<div class="cta-box">
  <a href="{{ '/getting-started/quickstart/' | relative_url }}" class="btn btn-primary btn-large">Get Started</a>
  <a href="https://github.com/aj-geddes/agentweave" class="btn btn-secondary btn-large">View on GitHub</a>
</div>

---

**Related Documentation:**
- [Security Model]({{ '/core-concepts/security-model/' | relative_url }})
- [Agentic Commerce Use Case]({{ '/use-cases/agentic-commerce/' | relative_url }})
- [Deployment Guide]({{ '/deployment/' | relative_url }})
- [Changelog]({{ '/changelog/' | relative_url }})
