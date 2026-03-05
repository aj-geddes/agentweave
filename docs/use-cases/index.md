---
layout: page
title: "Use Cases - AgentWeave SDK"
description: "Explore AI agent security use cases for agentic commerce, multi-agent orchestration, B2B supply chains, compliance, and cross-platform trust. AgentWeave provides cryptographic identity and policy-based authorization for every scenario."
permalink: /use-cases/
nav_order: 4
has_children: true
---

# AI Agent Security Use Cases

AgentWeave provides the trust and security infrastructure for AI agents operating across industries, clouds, and organizational boundaries. Every use case shares the same foundation: cryptographic identity via SPIFFE, mandatory mTLS transport, OPA policy-based authorization, and full audit logging through OpenTelemetry.

The use cases below represent the highest-value scenarios where agent security is not optional -- it is the difference between a production deployment and a cancelled project.

---

## Agentic Commerce Security

**The fastest-growing use case for secure AI agents.**

The agentic commerce market will reach $20.9 billion in US transactions in 2026 (eMarketer) and is projected to hit $1 trillion by 2030 (McKinsey). AI shopping agents from Walmart, Amazon, Shopify, and independent developers are already executing purchases, comparing prices, and negotiating terms on behalf of consumers and businesses. But 40% of agentic AI projects are cancelled due to inadequate risk controls (Gartner), and AI bot traffic to retail sites has surged 693% (Adobe).

AgentWeave solves the trust problem at the infrastructure level. Every shopping agent gets a SPIFFE-based cryptographic identity that retailers can verify. Authorization policies control what each agent can do -- browse, add to cart, purchase, return -- with default-deny enforcement. Every transaction is logged with distributed tracing for dispute resolution and fraud investigation.

```python
from agentweave import SecureAgent, capability

class ShoppingAgent(SecureAgent):
    @capability("purchase", description="Execute a verified purchase")
    async def purchase(self, order: dict) -> dict:
        # Agent identity verified via SPIFFE SVID
        # Retailer authorization policy checked via OPA
        # mTLS ensures no MITM between agent and storefront
        return await self.execute_purchase(order)
```

[Read the full Agentic Commerce guide]({{ '/use-cases/agentic-commerce/' | relative_url }})

---

## Multi-Agent Retail Orchestration

**Coordinate specialized agents across the shopping journey with verifiable trust.**

Modern retail experiences involve multiple AI agents working together: a product discovery agent searches catalogs, a price comparison agent evaluates options, a negotiation agent secures discounts, and a fulfillment agent tracks delivery. Each agent may be built by a different vendor, deployed on a different cloud, and governed by different policies.

Without a trust layer, orchestration becomes a liability. An unauthorized agent could inject fraudulent product recommendations. A compromised fulfillment agent could redirect shipments. A rogue price agent could manipulate comparisons to favor a specific vendor. AgentWeave eliminates these risks by requiring every agent in the orchestration chain to present a verifiable cryptographic identity and pass authorization checks before participating.

```
┌──────────────┐     ┌───────────────┐     ┌──────────────┐
│  Discovery   │────>│  Comparison   │────>│ Negotiation  │
│    Agent     │     │    Agent      │     │    Agent     │
│  (Vendor A)  │     │  (Vendor B)   │     │  (Vendor C)  │
└──────────────┘     └───────────────┘     └──────┬───────┘
                                                  │
                                           ┌──────▼───────┐
                                           │ Fulfillment  │
                                           │    Agent     │
                                           │  (Vendor D)  │
                                           └──────────────┘

Every arrow = mTLS + SPIFFE identity + OPA authorization
```

AgentWeave's A2A protocol support means each agent publishes an Agent Card describing its capabilities, required permissions, and trust domain. The orchestrator discovers agents, verifies their identities, and enforces policies that govern which agents can interact -- all without custom integration code.

---

## B2B Supplier Networks

**Secure agent-to-agent negotiation across enterprise boundaries.**

Gartner projects $15 trillion in B2B purchases will be AI-agent-intermediated by 2028. In these scenarios, a buyer's procurement agent negotiates pricing and terms with multiple supplier agents, each operating within its own trust domain. Contracts are executed, purchase orders are placed, and payments are authorized -- all by agents acting on behalf of enterprises.

The security requirements are fundamentally different from consumer commerce. Agents must prove not just their own identity, but the identity and authority of the organization they represent. Authorization policies must enforce purchasing limits, approved vendor lists, and compliance requirements. Every negotiation step must produce an immutable audit trail that satisfies regulatory and internal governance requirements.

AgentWeave's SPIFFE federation enables cross-organization trust. A buyer's agent with identity `spiffe://acme.com/procurement/agent-7` can securely negotiate with a supplier's agent at `spiffe://supplier.io/sales/agent-12` across trust domain boundaries. OPA policies on both sides enforce their respective business rules.

```python
# Buyer-side OPA policy: enforce purchasing limits
package agentweave.authz

default allow = false

allow {
    input.caller_spiffe_id == "spiffe://acme.com/procurement/agent-7"
    input.action == "place_order"
    input.context.order_total <= 50000
    input.context.supplier_id in data.approved_suppliers
}
```

---

## Cross-Platform Commerce Security

**Verify agent identity across marketplaces, payment processors, and logistics platforms.**

AI agents now operate across Amazon, Shopify, Walmart, and independent storefronts simultaneously. Each platform has different authentication requirements, rate limits, and terms of service. Amazon has already sued Perplexity over unauthorized agent access and blocked 47 AI crawlers. Retailers are building walls -- but they also want legitimate agent traffic that drives sales.

AgentWeave provides a standardized trust layer that works across platforms. Instead of managing API keys for each marketplace, agents present a cryptographic SPIFFE identity that any platform can verify. Authorization policies define what each agent is permitted to do on each platform. When a retailer needs to distinguish a legitimate purchasing agent from a scraper or a fraud bot, AgentWeave's identity infrastructure provides the answer.

This approach aligns with the industry direction: Visa's Token Authentication Platform uses cryptographic signatures for agent transactions, Cloudflare's Web Bot Auth protocol provides machine-readable permissions, and Mastercard's Agent Pay framework requires verified agent identity. AgentWeave implements these patterns using CNCF-graduated open standards.

```yaml
# Agent configuration for cross-platform operation
agent:
  name: "cross-platform-shopper"
  spiffe_id: "spiffe://retailcorp.com/agents/shopper-v2"

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"

authz:
  default: "deny"
  policies:
    - path: "policies/amazon-marketplace.rego"
    - path: "policies/shopify-storefront.rego"
    - path: "policies/walmart-marketplace.rego"
```

---

## Omnichannel Agent Coordination

**Maintain consistent identity and authorization across web, mobile, voice, and in-store channels.**

Retailers increasingly deploy AI agents across every customer touchpoint: chatbots on the website, voice assistants in the call center, in-store kiosk agents, and mobile app concierges. Each channel agent needs to access the same customer data, inventory systems, and order management platforms -- but with channel-appropriate authorization levels.

An in-store kiosk agent should be able to check inventory and initiate a sale but not access a customer's purchase history without their presence. A call center voice agent may access account details after voice verification but should not process returns above a threshold without supervisor approval. A mobile agent may have broader self-service permissions but restricted access to loyalty program administration.

AgentWeave models these requirements as OPA policies tied to agent identity. Each channel agent has a distinct SPIFFE identity that encodes its channel and authorization level. Policies evaluate the agent's identity, the requested action, and contextual attributes like time of day, transaction value, and customer verification status.

```rego
# Channel-aware authorization policy
package agentweave.authz

default allow = false

# In-store kiosk: inventory and sales only
allow {
    startswith(input.caller_spiffe_id, "spiffe://retail.com/channel/kiosk/")
    input.action in ["check_inventory", "initiate_sale", "apply_discount"]
}

# Call center: account access after verification
allow {
    startswith(input.caller_spiffe_id, "spiffe://retail.com/channel/callcenter/")
    input.action in ["view_account", "process_return"]
    input.context.customer_verified == true
}

# Mobile app: self-service with limits
allow {
    startswith(input.caller_spiffe_id, "spiffe://retail.com/channel/mobile/")
    input.action == "process_return"
    input.context.return_value <= 500
}
```

---

## Returns and Refund Chain of Custody

**Cryptographic audit trails for every step of the returns process.**

Returns fraud costs US retailers over $100 billion annually. AI agents that process returns, authorize refunds, and manage reverse logistics need verifiable chain-of-custody records that prove which agent authorized each step, when, and under what policy.

AgentWeave's observability stack produces an immutable audit trail for every agent interaction. When a customer-facing agent initiates a return, the request passes through a verification agent, a refund authorization agent, and a logistics agent -- each with its own SPIFFE identity and authorization policy. OpenTelemetry distributed traces link every step with cryptographically verifiable agent identities.

```python
from agentweave import SecureAgent, capability
from agentweave.observability import audit_log

class RefundAgent(SecureAgent):
    @capability("authorize_refund", description="Authorize a customer refund")
    async def authorize_refund(self, request: dict) -> dict:
        # OPA policy checks: refund limit, reason code, customer history
        # All checked automatically before this method executes

        refund = await self.process_refund(request)

        # Audit log captures: agent SPIFFE ID, timestamp, policy decision,
        # refund amount, order ID -- all linked via trace context
        audit_log.record(
            action="refund_authorized",
            amount=refund["amount"],
            order_id=request["order_id"],
            reason=request["reason_code"]
        )
        return refund
```

The resulting audit trail satisfies both internal fraud investigation requirements and external regulatory inquiries. Every refund decision is traceable to a specific agent identity, a specific policy version, and a specific point in time.

---

## Compliance and Audit for Agentic Commerce

**Policy-as-code compliance that scales with your agent fleet.**

As AI agents take on more commercial authority, regulatory scrutiny is intensifying. Organizations deploying purchasing agents, pricing agents, or customer service agents need to demonstrate that their agents operate within defined boundaries, that authorization decisions are auditable, and that sensitive data is handled according to applicable regulations.

AgentWeave's architecture makes compliance a natural outcome of correct deployment rather than a separate workstream. OPA policies encode business rules, regulatory requirements, and internal governance standards as Rego code that is version-controlled, testable, and auditable. Every authorization decision is logged with the policy version that produced it. SPIFFE identities create a non-repudiable record of which agent performed each action.

For organizations subject to PCI-DSS, SOC 2, GDPR, or industry-specific regulations, AgentWeave provides the infrastructure to demonstrate that agent behavior is governed by explicit, auditable policies rather than opaque model outputs.

```rego
# PCI-DSS compliant payment agent policy
package agentweave.authz

default allow = false

# Only payment-authorized agents can process transactions
allow {
    input.caller_spiffe_id == "spiffe://corp.com/agents/payment-processor"
    input.action == "process_payment"
    input.context.payment_amount <= data.transaction_limits[input.context.merchant_category]
    input.context.cardholder_verified == true
}

# Audit trail: deny with reason for compliance reporting
deny_reason = "agent_not_authorized" {
    not startswith(input.caller_spiffe_id, "spiffe://corp.com/agents/payment-")
}

deny_reason = "transaction_limit_exceeded" {
    input.context.payment_amount > data.transaction_limits[input.context.merchant_category]
}
```

---

## Getting Started

Every use case above is built on the same AgentWeave foundation. To begin building secure AI agents for your scenario:

1. **Install AgentWeave**: `pip install agentweave`
2. **Follow the Quick Start**: [Getting Started Guide]({{ '/getting-started/quickstart/' | relative_url }})
3. **Review Security Architecture**: [Security Model]({{ '/core-concepts/security-model/' | relative_url }})
4. **Explore Examples**: [Code Examples]({{ '/examples/' | relative_url }})

---

**Related Documentation:**
- [Agentic Commerce Deep Dive]({{ '/use-cases/agentic-commerce/' | relative_url }})
- [Core Concepts]({{ '/core-concepts/' | relative_url }})
- [Security Best Practices]({{ '/security/best-practices/' | relative_url }})
- [API Reference]({{ '/api-reference/' | relative_url }})
