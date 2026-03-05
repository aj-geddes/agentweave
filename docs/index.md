---
layout: home
title: "AgentWeave SDK - The Trust Layer for Agentic Commerce"
description: "AgentWeave is the security infrastructure for the AI agent economy. Cryptographic identity, mandatory mTLS, and policy-based authorization for agentic commerce, B2B negotiation, and cross-platform agent orchestration. Built on CNCF-graduated SPIFFE and OPA."
extra_css:
  - /assets/css/home.css
permalink: /

hero:
  title: "The Trust Layer for Agentic Commerce"
  tagline: "Secure the $20.9 billion AI agent economy"
  description: "AI agents are buying, selling, and negotiating across every major platform. AgentWeave is the security infrastructure that makes it safe. Cryptographic identity, mandatory mTLS, and policy-based authorization — built in, not bolted on."
  code_example: |
    from agentweave import SecureAgent, capability

    class PurchaseAgent(SecureAgent):
        @capability("negotiate", description="Negotiate terms with supplier agents")
        async def negotiate(self, order: dict) -> dict:
            # Identity verified. mTLS enforced. Authorization checked.
            # You write business logic. AgentWeave handles trust.
            return {"status": "accepted", "order_id": order["id"]}

    agent = PurchaseAgent.from_config("config.yaml")
    agent.run()

features:
  title: "Security Infrastructure for the Agent Economy"
  subtitle: "Every component AI agents need to transact with verifiable trust"
  items:
    - icon: "shield"
      title: "Agentic Commerce Ready"
      description: "Purpose-built for the $20.9B agentic commerce market. Agents that buy, sell, and negotiate need cryptographic proof of identity — not API keys. AgentWeave delivers the trust layer that Visa, Mastercard, and Cloudflare are converging toward."
      link:
        text: "Learn about security"
        url: "/security/"

    - icon: "lock"
      title: "Cryptographic Agent Identity"
      description: "SPIFFE-based workload identity gives every agent a verifiable, non-forgeable credential. Automatic certificate rotation. No shared secrets. The same standard Netflix, Uber, and Square use to secure production infrastructure."
      link:
        text: "Identity concepts"
        url: "/core-concepts/identity/"

    - icon: "code"
      title: "A2A Protocol Native"
      description: "First-class support for the Linux Foundation A2A standard. Framework-agnostic agent-to-agent communication with built-in capability discovery via Agent Cards. Interoperate with any A2A-compatible system."
      link:
        text: "A2A protocol guide"
        url: "/core-concepts/communication/"

    - icon: "zap"
      title: "Policy-Based Authorization"
      description: "OPA-powered fine-grained access control with default-deny enforcement. Policies as code in Rego. Every authorization decision is audited. Decouple who-can-do-what from business logic entirely."
      link:
        text: "Authorization guide"
        url: "/core-concepts/authorization/"

    - icon: "layers"
      title: "Mandatory mTLS Transport"
      description: "Mutual TLS for every agent interaction — no exceptions, no downgrades. TLS 1.3 enforced. Peer verification mandatory. The secure path is the only path, which means you cannot ship an insecure agent."
      link:
        text: "Transport layer"
        url: "/core-concepts/security-model/"

    - icon: "cloud"
      title: "Full-Stack Observability"
      description: "OpenTelemetry-native metrics, distributed tracing, and structured audit logging. Prometheus-compatible. See every agent interaction, authorization decision, and certificate rotation in production."
      link:
        text: "Observability guide"
        url: "/api-reference/observability/"

technologies:
  title: "Built on Battle-Tested, CNCF-Graduated Standards"
  items:
    - name: "SPIFFE/SPIRE"
      description: "CNCF-graduated cryptographic identity framework. Production-proven at Netflix, Pinterest, Uber, and Square. The emerging standard for agent identity that Visa and Mastercard are building toward."
      link: "https://spiffe.io"

    - name: "Open Policy Agent"
      description: "CNCF-graduated policy engine trusted across cloud-native infrastructure. Powers authorization at scale for organizations that cannot afford access control failures."
      link: "https://www.openpolicyagent.org"

    - name: "A2A Protocol"
      description: "Linux Foundation standard for agent-to-agent communication. Framework-agnostic interoperability that works across Google, OpenAI, Microsoft, and custom agent platforms."
      link: "https://a2a-protocol.org"

    - name: "OpenTelemetry"
      description: "CNCF-graduated observability standard. Unified metrics, traces, and logs across your entire agent infrastructure. Vendor-neutral with broad ecosystem support."
      link: "https://opentelemetry.io"

getting_started:
  title: "Ship a Secure Agent in Minutes"
  steps:
    - title: "Install AgentWeave"
      description: "Install the SDK with pip. Python 3.11+ required."
      code: "pip install agentweave"

    - title: "Create Your Agent"
      description: "Define capabilities with decorators. Identity, mTLS, and authorization are automatic."
      code: |
        from agentweave import SecureAgent, capability

        class MyAgent(SecureAgent):
            @capability("greet")
            async def greet(self, name: str) -> dict:
                return {"message": f"Hello, {name}!"}

    - title: "Configure & Run"
      description: "Point to your SPIFFE trust domain and OPA policies, then start serving."
      code: |
        agent = MyAgent.from_config("config.yaml")
        agent.run()

  cta:
    text: "Read the Quick Start Guide"
    url: "/getting-started/quickstart/"

community:
  title: "Community & Support"
  items:
    - icon: "github"
      title: "GitHub Repository"
      description: "Star the project, report issues, contribute code, and view the latest releases."
      url: "https://github.com/aj-geddes/agentweave"

    - icon: "docs"
      title: "Documentation"
      description: "Architecture guides, security walkthroughs, API reference, and production deployment patterns."
      url: "/getting-started/"

    - icon: "github"
      title: "Discussions"
      description: "Ask questions, share deployment patterns, and connect with other AgentWeave developers."
      url: "https://github.com/aj-geddes/agentweave/discussions"

    - icon: "github"
      title: "Report Issues"
      description: "Found a bug or have a feature request? Open an issue on GitHub."
      url: "https://github.com/aj-geddes/agentweave/issues"

market_stats:
  - icon: "trending-up"
    value: "$20.9B"
    label: "US agentic commerce market (2026)"
  - icon: "globe"
    value: "$1T+"
    label: "Projected US market by 2030"
  - icon: "zap"
    value: "693%"
    label: "AI traffic increase to retail sites"
  - icon: "shield"
    value: "40%"
    label: "Agentic AI projects cancelled due to risk"

use_cases:
  title: "Built for Real-World Agent Commerce"
  subtitle: "Security infrastructure for the scenarios that matter most"
  items:
    - icon: "trending-up"
      title: "Retail Agent Orchestration"
      description: "AI shopping agents are flooding retail platforms — 693% more AI traffic in the past year. AgentWeave gives retailers the infrastructure to verify which agents are legitimate, enforce purchasing policies, and maintain audit trails."
      capabilities:
        - "Cryptographic agent identity verification"
        - "Policy-enforced purchasing limits"
        - "Full transaction audit trail"
        - "Bot authentication and classification"
      link:
        text: "Explore retail use case"
        url: "/use-cases/agentic-commerce/"
    - icon: "globe"
      title: "B2B Agent Negotiation"
      description: "Gartner projects $15 trillion in B2B purchases will be AI-agent-intermediated by 2028. When agents negotiate contracts and authorize payments, trust infrastructure cannot be an afterthought."
      capabilities:
        - "Enterprise-grade mutual authentication"
        - "Contract negotiation authorization"
        - "Cross-organization trust federation"
        - "Auditable decision logging"
      link:
        text: "Explore B2B use case"
        url: "/use-cases/agentic-commerce/"
    - icon: "layers"
      title: "Cross-Platform Trust Federation"
      description: "The agent economy is multi-cloud and multi-vendor. A purchasing agent on AWS needs to securely transact with fulfillment on GCP and payments on Azure. SPIFFE-based federated identity makes this a configuration problem."
      capabilities:
        - "SPIFFE-based federated identity"
        - "Cross-cloud mesh networking"
        - "Vendor-neutral trust domains"
        - "Automatic certificate rotation"
      link:
        text: "Explore federation use case"
        url: "/use-cases/agentic-commerce/"

protocols:
  title: "Protocol Compatible"
  subtitle: "Works with the emerging agent communication ecosystem"
  items:
    - icon: "link"
      name: "A2A Protocol"
      status: "Native"
      description: "First-class support for the Linux Foundation Agent-to-Agent standard. Agent Cards, capability discovery, and JSON-RPC 2.0 messaging built in."
      link: "/core-concepts/communication/"
    - icon: "code"
      name: "ACP"
      status: "Compatible"
      description: "Compatible transport layer. AgentWeave's mTLS and identity infrastructure secures Agent Communication Protocol connections."
      link: "/core-concepts/communication/"
    - icon: "globe"
      name: "UCP"
      status: "Compatible"
      description: "Interoperable by design. AgentWeave provides the trust and authorization layer regardless of the wire protocol."
      link: "/core-concepts/communication/"
---

## The Agentic Commerce Security Gap

The AI agent economy is here. Every major platform — Google, OpenAI, Microsoft — has launched agentic shopping. Visa, Mastercard, and Cloudflare are building agent identity infrastructure. Gartner projects **$15 trillion in B2B purchases** will be AI-agent-intermediated by 2028.

But there is a critical gap. **40% of agentic AI projects are cancelled due to inadequate risk controls** (Gartner, 2025). AI bot traffic to retail sites is up **693%** (Adobe). Akamai reports a **300% increase** in AI bot traffic across the web. The commerce infrastructure that handles $20.9 billion in US transactions this year has no standardized trust layer.

AgentWeave fills that gap. It is the open-source security infrastructure that gives every AI agent a cryptographic identity, enforces mutual authentication on every transaction, and makes authorization decisions auditable and policy-driven.

**The secure path is the only path.** Developers using AgentWeave cannot accidentally ship an insecure agent. Security is not a feature you enable — it is the architecture itself.

---

## Why AgentWeave?

### Traditional Agent Security

- API keys and shared secrets passed in headers
- Plain HTTP or optional TLS with no peer verification
- Authorization logic scattered across application code
- No audit trail for agent-to-agent transactions
- Security added as an afterthought, easily bypassed
- Custom protocols that break across frameworks

### The AgentWeave Approach

- **Cryptographic identity** via SPIFFE — non-forgeable, automatically rotated
- **Mandatory mutual TLS** — every connection verified both ways, no downgrades
- **OPA policy enforcement** — default-deny authorization, policies as code
- **Every decision audited** — structured logs, distributed traces, Prometheus metrics
- **Security cannot be bypassed** — the SDK enforces it at the architecture level
- **A2A protocol standard** — framework-agnostic, Linux Foundation backed

---

## Built for the Agent Economy

### Retail & Commerce Orchestration

AI shopping agents are flooding retail platforms — **693% more AI traffic to retail sites** in the past year alone. AgentWeave gives retailers and platform operators the infrastructure to verify which agents are legitimate, enforce purchasing policies, and maintain audit trails for every automated transaction.

### B2B Agent Negotiation

Gartner projects **$15 trillion in B2B purchases** will be intermediated by AI agents by 2028. When agents negotiate contracts, place orders, and authorize payments on behalf of enterprises, the trust infrastructure cannot be an afterthought. AgentWeave provides the cryptographic identity and policy enforcement that B2B commerce demands.

### Cross-Platform Trust Federation

The agent economy is inherently multi-cloud and multi-vendor. A purchasing agent on AWS needs to securely transact with a fulfillment agent on GCP and a payment agent on Azure. AgentWeave's SPIFFE-based federated identity and optional Tailscale mesh networking make cross-boundary trust a configuration problem, not an engineering project.

---

## Protocol Compatible

AgentWeave is designed to work with the emerging agent protocol ecosystem:

- **A2A (Agent-to-Agent)** — Native support for the Linux Foundation standard. Agent Cards, capability discovery, and JSON-RPC 2.0 messaging built in.
- **ACP (Agent Communication Protocol)** — Compatible transport layer. AgentWeave's mTLS and identity infrastructure secures ACP connections.
- **UCP (Universal Communication Protocol)** — Interoperable by design. AgentWeave provides the trust and authorization layer regardless of the wire protocol.

The protocol landscape is evolving rapidly. AgentWeave's value is not in competing with communication protocols — it is in providing the **security and identity layer** that every protocol needs but none provide on their own.

---

## The Market Opportunity

The numbers tell a clear story:

| Metric | Value | Source |
|--------|-------|--------|
| US agentic commerce market (2026) | **$20.9 billion** | eMarketer |
| US agentic commerce market (2030) | **$1 trillion** | McKinsey |
| Global agentic commerce (2030) | **$3-5 trillion** | McKinsey |
| B2B purchases via AI agents (2028) | **$15 trillion** | Gartner |
| AI bot traffic increase | **300%** | Akamai |
| AI traffic to retail sites increase | **693%** | Adobe |
| Agentic AI projects cancelled (risk) | **40%** | Gartner |

Every one of these transactions needs verified identity, enforced authorization, and auditable trust. That is what AgentWeave provides.

---

## Ready to Secure Your Agents?

The agent economy will not wait for security to catch up. Start building with trust infrastructure that is already here.

<div class="cta-box">
  <a href="{{ '/getting-started/quickstart/' | relative_url }}" class="btn btn-primary btn-large">Get Started</a>
  <a href="{{ '/examples/' | relative_url }}" class="btn btn-secondary btn-large">View Examples</a>
</div>
