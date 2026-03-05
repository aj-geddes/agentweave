---
layout: page
title: "Agentic Commerce Security - AgentWeave SDK"
description: "Secure the agentic commerce ecosystem with cryptographic agent identity, mTLS, and policy-based authorization. AgentWeave provides the trust infrastructure for AI shopping agents."
permalink: /use-cases/agentic-commerce/
parent: "Use Cases - AgentWeave SDK"
nav_order: 1
---

# Agentic Commerce Security

AI agents are fundamentally reshaping how commerce works. They negotiate, purchase, compare, return, and manage transactions on behalf of consumers and enterprises across every major retail platform. AgentWeave provides the trust infrastructure that makes agentic commerce safe: cryptographic agent identity, mandatory mutual TLS, policy-based authorization, and full audit logging for every automated transaction.

---

## The Agentic Commerce Opportunity

The scale of agentic commerce is no longer speculative. eMarketer projects **$20.9 billion in US agentic commerce transactions in 2026**, with McKinsey forecasting the market will reach **$1 trillion by 2030** in the US alone and **$3-5 trillion globally**. Gartner projects that **$15 trillion in B2B purchases** will be AI-agent-intermediated by 2028.

Every major technology and commerce player is investing heavily:

- **Walmart** launched Sparky, an AI shopping agent that assists customers across its digital storefront
- **Amazon** deployed Rufus, an AI agent embedded directly in the shopping experience
- **Shopify** introduced Agentic Storefronts, enabling AI agents to browse, configure, and purchase products programmatically
- **Google, OpenAI, and Microsoft** have each launched agentic shopping capabilities within their respective platforms

The protocol ecosystem is maturing in parallel. The **Agent Communication Protocol (ACP)**, backed by OpenAI and Stripe, focuses on payment-aware agent interactions. Google and Shopify support the **Universal Communication Protocol (UCP)** for storefront interoperability. The Linux Foundation's **A2A (Agent-to-Agent) protocol** provides framework-agnostic communication with capability discovery via Agent Cards. AgentWeave implements A2A natively and provides the security layer that all these protocols need.

On the infrastructure side, major financial networks are building agent-specific trust systems. **Visa's Token Authentication Platform (TAP)** uses cryptographic signatures for agent-initiated transactions. **Cloudflare's Web Bot Auth** protocol creates machine-readable permission systems for agent access. **Mastercard's Agent Pay** framework requires verified agent identity before processing payments.

---

## The Trust Gap in Agentic Commerce

Despite the market momentum, a critical trust gap threatens the entire agentic commerce ecosystem.

### The Security Problem

**40% of agentic AI projects are cancelled due to inadequate risk controls** (Gartner, 2025). The cancellation rate is not driven by capability limitations -- agents are technically capable of executing commerce workflows. Projects fail because organizations cannot demonstrate that their agents operate within defined boundaries, that transactions are authorized, and that the agent's identity is verifiable.

The traffic numbers tell the same story from the retailer's perspective. **Akamai reports a 300% increase in AI bot traffic** across the web. **Adobe found a 693% increase in AI-driven traffic to retail sites** specifically. Retailers are being flooded with agent traffic and have limited ability to distinguish legitimate purchasing agents from scrapers, price manipulators, or fraud bots.

### The Unauthorized Access Problem

The tension between agent access and platform control is already producing legal conflicts. **Amazon sued Perplexity** over unauthorized agent access to its product data and has **blocked 47 AI crawlers** from its platforms. This is not an isolated incident -- it reflects a structural problem. Without a standardized mechanism for agents to prove their identity and obtain authorized access, platforms default to blocking all automated traffic.

This hurts everyone. Retailers lose legitimate agent-driven sales. Consumers lose the convenience of AI-assisted shopping. Agent developers face an unpredictable access landscape where their agents work today and get blocked tomorrow.

### The Compliance Problem

As agentic commerce scales, regulatory attention is increasing. Agents that process payments must satisfy PCI-DSS requirements. Agents that handle customer data must comply with GDPR and CCPA. Agents that make purchasing decisions on behalf of enterprises must produce audit trails that satisfy internal governance and external regulators. Most agent frameworks provide none of this infrastructure.

---

## How AgentWeave Solves the Agentic Commerce Trust Gap

AgentWeave addresses each dimension of the trust gap with production-proven, CNCF-graduated open standards.

### Cryptographic Agent Identity

Every AgentWeave agent receives a **SPIFFE-based cryptographic identity** -- a verifiable, non-forgeable credential like `spiffe://retailcorp.com/agents/shopper-v2`. Unlike API keys or bearer tokens, SPIFFE Verifiable Identity Documents (SVIDs) are X.509 certificates issued by SPIRE that are automatically rotated, cannot be shared or exfiltrated, and provide mutual authentication.

When a shopping agent connects to a retailer's storefront, both parties verify each other's identity through mutual TLS. The retailer knows exactly which organization, which agent, and which version is making the request. The agent knows it is talking to the legitimate storefront, not a phishing endpoint.

This is the same identity infrastructure pattern that **Netflix, Uber, Pinterest, and Square** use to secure their production workloads at scale.

### Mandatory mTLS for Every Transaction

AgentWeave enforces **mutual TLS on every agent interaction** -- no exceptions, no configuration flag to disable it, no downgrade path. TLS 1.3 is enforced. Peer verification is mandatory. The secure path is the only path.

This design eliminates entire classes of agentic commerce attacks:
- **Man-in-the-middle**: Cannot intercept agent-to-storefront communication
- **Agent impersonation**: Cannot forge a SPIFFE identity without the private key
- **Replay attacks**: mTLS session binding prevents credential reuse
- **Data exfiltration**: Encrypted transport with verified endpoints

### Policy-Based Authorization with Default Deny

AgentWeave uses **Open Policy Agent (OPA)** for fine-grained, policy-based authorization with **default-deny enforcement**. Every action an agent attempts -- browsing a catalog, adding to cart, executing a purchase, initiating a return -- is evaluated against Rego policies before execution.

Policies are decoupled from application code and version-controlled as infrastructure. A retailer can define policies that restrict which agents can purchase, set spending limits, enforce approved product categories, and require additional verification for high-value transactions -- all without modifying agent code.

### Audit Logging and Observability

Every authorization decision, every agent interaction, and every certificate rotation is captured through AgentWeave's **OpenTelemetry-native observability stack**. Prometheus metrics, distributed traces, and structured audit logs provide complete visibility into agent behavior.

For agentic commerce, this means every transaction has a verifiable record: which agent initiated it, what policy authorized it, when it occurred, and what the outcome was. This audit trail satisfies PCI-DSS, SOC 2, and internal governance requirements.

---

## Protocol Compatibility

The agentic commerce protocol landscape is evolving rapidly, with multiple standards emerging simultaneously. AgentWeave is designed to complement these protocols rather than compete with them -- providing the security and identity layer that every protocol needs.

### A2A Protocol (Linux Foundation)

AgentWeave provides **native A2A protocol support**. Agents publish Agent Cards that describe their capabilities, required permissions, and trust domain. Communication uses JSON-RPC 2.0 over authenticated connections. Capability discovery, task management, and streaming are built in.

### ACP (Agent Communication Protocol)

AgentWeave's mTLS transport and SPIFFE identity infrastructure can **secure ACP connections** between payment-aware agents. When agents use ACP for Stripe-integrated payment flows, AgentWeave ensures that both parties are cryptographically verified and that the transaction is authorized by policy.

### UCP (Universal Communication Protocol)

AgentWeave is **interoperable with UCP** by design. The trust and authorization layer operates independently of the wire protocol. Whether agents communicate via A2A, UCP, or a custom protocol, AgentWeave provides the identity verification and policy enforcement.

### Visa TAP, Cloudflare Web Bot Auth, Mastercard Agent Pay

These emerging financial infrastructure protocols all converge on the same principle: agents need **cryptographic proof of identity** to participate in commerce. AgentWeave implements this principle using CNCF-graduated SPIFFE, which provides the same type of cryptographic identity that Visa TAP and Mastercard Agent Pay are building toward -- but available today, as open source, with no vendor lock-in.

---

## Where AgentWeave Fits in the Agentic Commerce Stack

AgentWeave operates as the trust and security infrastructure layer between agent application logic and commerce platforms:

```
┌──────────────────────────────────────────────────────────────┐
│                    AI Agent Application                      │
│  (Shopping logic, price comparison, negotiation, checkout)   │
├──────────────────────────────────────────────────────────────┤
│                   AgentWeave SDK                             │
│  ┌─────────────┐ ┌────────────┐ ┌────────────┐ ┌─────────┐ │
│  │   SPIFFE     │ │  Mandatory │ │    OPA     │ │  Audit  │ │
│  │  Identity    │ │   mTLS     │ │   AuthZ    │ │ Logging │ │
│  │  (SVID)      │ │ Transport  │ │  (Rego)    │ │ (OTel)  │ │
│  └─────────────┘ └────────────┘ └────────────┘ └─────────┘ │
├──────────────────────────────────────────────────────────────┤
│                  Protocol Layer                              │
│         A2A  /  ACP  /  UCP  /  Custom APIs                 │
├──────────────────────────────────────────────────────────────┤
│               Commerce Platforms                             │
│  Amazon  /  Shopify  /  Walmart  /  B2B Marketplaces        │
└──────────────────────────────────────────────────────────────┘
```

AgentWeave does not replace commerce APIs or agent communication protocols. It provides the **missing security layer** that sits between agent logic and those protocols, ensuring that every interaction is authenticated, authorized, and auditable.

---

## Implementation Examples

### Retail Agent with Cryptographic Identity

A shopping agent that browses products and executes purchases with full SPIFFE identity verification and OPA authorization:

```python
from agentweave import SecureAgent, capability

class RetailShoppingAgent(SecureAgent):
    """AI shopping agent with cryptographic identity and
    policy-based authorization for agentic commerce."""

    @capability("browse_catalog", description="Search product catalogs")
    async def browse_catalog(self, query: dict) -> dict:
        # Agent identity verified via SPIFFE SVID
        # OPA policy confirms this agent can browse this retailer
        results = await self.search_products(
            retailer=query["retailer"],
            search_term=query["search_term"],
            filters=query.get("filters", {})
        )
        return {"products": results, "count": len(results)}

    @capability("execute_purchase", description="Complete a verified purchase")
    async def execute_purchase(self, order: dict) -> dict:
        # OPA policy checks: spending limit, approved retailer,
        # product category restrictions, time-of-day rules
        # All enforced automatically before this code runs
        confirmation = await self.submit_order(order)
        return {
            "status": "confirmed",
            "order_id": confirmation["id"],
            "total": confirmation["total"],
            "agent_id": self.spiffe_id  # Cryptographic proof of who placed the order
        }

# Configure with SPIFFE trust domain and OPA policies
agent = RetailShoppingAgent.from_config("config.yaml")
agent.run()
```

### Agent Configuration for Agentic Commerce

```yaml
agent:
  name: "retail-shopping-agent"
  version: "2.1.0"
  description: "AI shopping agent for multi-retailer purchasing"

identity:
  trust_domain: "retailcorp.com"
  spiffe_id: "spiffe://retailcorp.com/agents/shopper-v2"

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"
  # Certificate rotation is automatic via SPIRE

authz:
  provider: "opa"
  default: "deny"
  policies:
    - path: "policies/purchasing-limits.rego"
    - path: "policies/approved-retailers.rego"
    - path: "policies/product-restrictions.rego"

observability:
  metrics:
    enabled: true
    port: 9090
  tracing:
    enabled: true
    exporter: "otlp"
  audit:
    enabled: true
    include_request_body: false  # PCI-DSS: don't log payment details
```

### OPA Policy for Purchase Authorization

```rego
package agentweave.authz

default allow = false

# Allow browsing for all verified shopping agents
allow {
    startswith(input.caller_spiffe_id, "spiffe://retailcorp.com/agents/shopper-")
    input.action == "browse_catalog"
}

# Allow purchases within spending limits from approved retailers
allow {
    startswith(input.caller_spiffe_id, "spiffe://retailcorp.com/agents/shopper-")
    input.action == "execute_purchase"
    input.context.order_total <= data.spending_limits.per_transaction
    input.context.retailer_id in data.approved_retailers
    not input.context.product_category in data.restricted_categories
}

# Require additional verification for high-value purchases
allow {
    startswith(input.caller_spiffe_id, "spiffe://retailcorp.com/agents/shopper-")
    input.action == "execute_purchase"
    input.context.order_total > data.spending_limits.per_transaction
    input.context.order_total <= data.spending_limits.with_approval
    input.context.supervisor_approved == true
}
```

---

## Market Data Summary

| Metric | Value | Source |
|--------|-------|--------|
| US agentic commerce market (2026) | **$20.9 billion** | eMarketer |
| US agentic commerce market (2030) | **$1 trillion** | McKinsey |
| Global agentic commerce (2030) | **$3-5 trillion** | McKinsey |
| B2B purchases via AI agents (2028) | **$15 trillion** | Gartner |
| AI bot traffic increase (web-wide) | **300%** | Akamai |
| AI traffic to retail sites increase | **693%** | Adobe |
| Agentic AI projects cancelled due to risk | **40%** | Gartner |
| AI crawlers blocked by Amazon | **47** | Amazon/press reports |

---

## Getting Started with Agentic Commerce Security

The agentic commerce market is growing faster than the trust infrastructure to support it. AgentWeave provides that infrastructure today, using CNCF-graduated open standards, with no vendor lock-in.

### Step 1: Install AgentWeave

```bash
pip install agentweave
```

### Step 2: Configure Identity and Authorization

Define your agent's SPIFFE identity and OPA policies. The [Quick Start guide]({{ '/getting-started/quickstart/' | relative_url }}) walks through the complete setup in under 10 minutes.

### Step 3: Build Your Commerce Agent

Use the `SecureAgent` base class and `@capability` decorator. Identity verification, mTLS transport, and authorization enforcement are automatic -- you write business logic, AgentWeave handles trust.

### Step 4: Deploy and Monitor

Deploy to any cloud or Kubernetes environment with full observability. See the [Deployment guide]({{ '/deployment/' | relative_url }}) for production configurations.

<div class="cta-box">
  <a href="{{ '/getting-started/quickstart/' | relative_url }}" class="btn btn-primary btn-large">Get Started</a>
  <a href="{{ '/examples/' | relative_url }}" class="btn btn-secondary btn-large">View Examples</a>
</div>

---

**Related Documentation:**
- [Use Cases Overview]({{ '/use-cases/' | relative_url }})
- [Security Model]({{ '/core-concepts/security-model/' | relative_url }})
- [A2A Protocol Guide]({{ '/core-concepts/communication/' | relative_url }})
- [Authorization Guide]({{ '/core-concepts/authorization/' | relative_url }})
- [GitHub Repository](https://github.com/aj-geddes/agentweave)
