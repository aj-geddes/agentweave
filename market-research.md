# AgentWeave Market Research: Agentic Commerce Opportunity

**Date:** March 2026
**Prepared for:** AgentWeave strategic planning
**Verdict:** Strong market fit with specific positioning required

---

## Executive Summary

Agentic commerce — where AI agents autonomously discover, negotiate, and complete purchases on behalf of consumers — has exploded from concept to production since late 2025. Every major tech platform (Google, OpenAI, Microsoft, Perplexity), every major retailer (Walmart, Amazon, Shopify, Target), and the payment networks (Visa, Mastercard, Stripe, PayPal) have launched agentic shopping products. The market is projected to reach $20.9 billion in US retail in 2026 alone (eMarketer), scaling to $1 trillion domestically and $3-5 trillion globally by 2030 (McKinsey).

**The critical gap in this ecosystem is trust and security infrastructure.** Fraud is surging (AI bot traffic up 300% — Akamai), agent identity is unsolved at the infrastructure layer, and retailers are simultaneously embracing and suing agentic platforms. AgentWeave's cryptographic identity (SPIFFE), mandatory mTLS, policy-based authorization (OPA), and A2A protocol support position it as infrastructure for the trust layer that agentic commerce requires but largely lacks today.

AgentWeave is **not** a consumer shopping agent. It is the **security and orchestration backbone** that retailers, payment processors, and platform operators need to run agentic commerce safely.

---

## 1. Market Landscape: Who Is Doing What

### 1.1 Tech Platform Shopping Agents

| Platform | Product | Status | Scale |
|----------|---------|--------|-------|
| **OpenAI** | ChatGPT Instant Checkout + Agentic Commerce Protocol (ACP) | Production (Sep 2025) | 900M weekly users; Etsy live, 1M+ Shopify merchants coming |
| **Google** | AI Mode Shopping + Universal Commerce Protocol (UCP) | Production (Jan 2026) | Etsy, Wayfair live; Walmart, Target, Shopify coming |
| **Microsoft** | Copilot Checkout + Brand Agents | Production (Jan 2026) | PayPal, Shopify, Stripe, Etsy integrations |
| **Perplexity** | Shopping Agent + Comet Browser | Production (Nov 2025) | 5,000+ merchants, PayPal integration, free tier |
| **Apple** | Siri (upgraded) | Delayed to late 2026 | Walmart grocery integration live; Gemini-powered |
| **Salesforce** | Agentforce Commerce | Production (2025) | Guided shopping GA; AI traffic up 119% YoY |

**Key observation:** These platforms are building the consumer-facing agent layer. They need backend infrastructure for secure agent-to-merchant and agent-to-agent communication.

### 1.2 Major Retailer Initiatives

| Retailer | Initiative | Key Detail |
|----------|-----------|------------|
| **Walmart** | Sparky AI Agent | 81% of shoppers used Sparky for product lookup; 35% higher avg order value; ads now embedded in agent responses; integrating with ChatGPT, Gemini, UCP |
| **Amazon** | Rufus auto-buy + defensive posture | Auto-buy at price thresholds for Prime; simultaneously blocked 47 AI crawlers; sued Perplexity over unauthorized agent access; removed 600M products from ChatGPT |
| **Shopify** | Agentic Storefronts + UCP co-development | Merchants auto-enrolled in Copilot Checkout; UCP co-developed with Google; single admin for ChatGPT, Perplexity, Copilot storefronts |
| **Target** | ChatGPT beta | In-app shopping via ChatGPT (Nov 2025 beta) |
| **Instacart** | ChatGPT Instant Checkout | First grocery partner with end-to-end checkout in ChatGPT, built on ACP |
| **DoorDash** | ChatGPT grocery integration | Recipe-to-grocery-list workflow; checkout redirects to DoorDash app |
| **Etsy** | Live on ChatGPT + Google AI Mode | First merchant live on both ACP and UCP |

**Key observation:** Amazon's defensive posture (blocking bots, suing competitors) while also building Rufus auto-buy highlights the core tension — **retailers want agent commerce but need to control which agents they trust and what those agents can do.** This is exactly AgentWeave's value proposition.

### 1.3 Agentic Commerce Startups

| Company | Focus | Traction |
|---------|-------|----------|
| **Envive** (fka Spiffy) | AI agents embedded in merchant e-commerce systems | $15M Series A; Spanx, Supergoop!, Wine Enthusiast |
| **Phia** | Browser-based price comparison agent | $8M raised; 500K installs in 5 months; 5,000 brand partnerships |
| **OneOff** | Celebrity/creator-look product recommendations | Early stage |
| **Capacity** | Enterprise commerce AI | 339% headcount growth YoY |
| **Constructor** | AI-powered product discovery | 98% headcount growth YoY |

**Key observation:** CB Insights mapped 90+ companies in agentic commerce. Orchestration platforms lead with 87% average headcount growth. Most startups focus on the consumer/merchant experience layer, not the security/trust infrastructure.

### 1.4 Commerce Protocols (The Standards War)

Three competing protocols have emerged:

| Protocol | Backers | Focus | Status |
|----------|---------|-------|--------|
| **ACP** (Agentic Commerce Protocol) | OpenAI + Stripe | Agent-to-merchant checkout | Production; Apache 2.0; PayPal, Etsy, Shopify live |
| **UCP** (Universal Commerce Protocol) | Google + Shopify | Full shopping journey (discovery through post-purchase) | Production; Walmart, Target, Etsy, Wayfair + 20 endorsers |
| **A2A** (Agent2Agent) | Google (Linux Foundation) | Agent-to-agent interoperability | Production v0.3; 50+ partners; gRPC support; signed Agent Cards |

Additionally:
- **MCP** (Model Context Protocol, Anthropic) — tool/context integration complementing A2A
- **Visa TAP** (Trusted Agent Protocol) — payment-specific agent identity
- **Mastercard Agent Pay** — payment-specific agent authentication

**Key observation:** AgentWeave already implements A2A protocol with Agent Cards, mTLS transport, and JSON-RPC 2.0. It is protocol-compatible with the emerging standards. UCP explicitly lists A2A compatibility. The convergence of ACP + UCP + A2A creates a multi-protocol world where AgentWeave's protocol-agnostic security layer adds value across all of them.

### 1.5 Payment & Security Infrastructure

| Company | Product | What It Does |
|---------|---------|--------------|
| **Visa** | Trusted Agent Protocol (TAP) | Cryptographic proof-of-identity for agent transactions; HTTP Message Signatures with public key crypto |
| **Mastercard** | Agent Pay | Agent authentication via Web Bot Auth |
| **Cloudflare** | Web Bot Auth | Cryptographically signed HTTP messages to verify agent identity; distinguishes good bots from bad |
| **Akamai** | Bot Management + TAP integration | Edge-based behavioral intelligence + agent identity verification |
| **Stripe** | ACP + Shared Payment Token | Delegated payment specification for agent-initiated payments |

**Key observation:** Visa TAP uses cryptographic identity (HTTP Message Signatures with public key crypto) — conceptually aligned with AgentWeave's SPIFFE-based approach. Cloudflare's Web Bot Auth uses cryptographic signatures for agent verification. The industry is converging on cryptographic identity as the solution. AgentWeave already implements this at the workload level.

---

## 2. The Security & Trust Crisis

### 2.1 The Problem Is Real and Growing

- **AI bot traffic surged 300%** year-over-year (Akamai 2025 Digital Fraud Report)
- **25 billion AI bot requests** hit the commerce industry in a two-month period (Akamai)
- **Amazon sued Perplexity** for Comet browser disguising automated transactions as human sessions (Nov 2025)
- **Amazon blocked 47 AI crawlers** via robots.txt, removing 600M+ product listings from ChatGPT
- **95% of AI agent projects are failing** (Aug 2025 data), with security/trust cited as a key factor
- **Gartner predicts 40% of agentic AI projects will be cancelled** by end of 2027 due to escalating costs, unclear value, or **inadequate risk controls**
- **Non-human identity compromise** is the fastest-growing attack vector in enterprise infrastructure
- **Deepfake fraud** (e.g., Arup $25M incident) shows compromised agents can initiate financial transactions

### 2.2 Specific Security Challenges in Agentic Commerce

From industry analysis and real incidents:

1. **Agent Identity**: "When a human isn't the transacting party, how do we establish identity certainty?" Distinguishing "good bots" from "bad bots" impersonating legitimate agents is the fundamental challenge.

2. **Credential Compromise**: Developers hardcode API keys; a single compromised agent credential can give attackers access for weeks or months. Session token theft enables agent impersonation.

3. **Counterfeit Merchant Agents**: Sophisticated fake merchants engineered specifically to exploit shopping agents that find "best deals."

4. **Authorization Scope Creep**: An agent authorized to browse and compare prices shouldn't be able to complete purchases without additional authorization gates.

5. **Cross-Platform Trust**: When a Walmart agent communicates with a logistics partner's agent, how is mutual identity established? Federation of trust across organizational boundaries.

6. **Audit & Compliance**: PCI DSS, SOX, and consumer protection regulations require clear audit trails. Who authorized this purchase? Which agent processed the refund? When did the price change?

7. **Data Privacy**: Agents accessing customer preferences, purchase history, and payment information must enforce field-level access controls based on role and context.

### 2.3 Industry Response

The industry is scrambling to build trust infrastructure:

- **Visa TAP**: Cryptographic signed HTTP messages (closest to AgentWeave's approach)
- **Cloudflare Web Bot Auth**: Public key crypto for agent identity verification
- **Akamai + Visa**: Behavioral intelligence + TAP integration
- **Google reCAPTCHA**: Attempting to distinguish legitimate agents from malicious ones
- **World Economic Forum**: Published "AI agents could be worth $236 billion by 2034 — if we ensure they are the good kind" (Jan 2026)

**The gap:** These solutions focus on the edge/payment layer. None provide end-to-end workload identity, mutual authentication, policy-based authorization, and audit across the full agent lifecycle. That's AgentWeave's position.

---

## 3. AgentWeave Fit Analysis

### 3.1 Capability Mapping to Market Needs

| Market Need | AgentWeave Capability | Fit |
|------------|----------------------|-----|
| Agent identity verification | SPIFFE/SPIRE cryptographic workload identity (X.509 SVIDs, auto-rotation, no hardcoded secrets) | **Direct match** |
| Mutual authentication | Mandatory mTLS with peer verification (cannot be disabled) | **Direct match** |
| Authorization & access control | OPA policies with default-deny, attribute-based, context-aware decisions | **Direct match** |
| Agent-to-agent communication | A2A protocol with Agent Cards, JSON-RPC 2.0, SSE streaming | **Direct match** |
| Cross-organization trust | SPIRE federation across trust domains | **Direct match** |
| Audit trail & compliance | Built-in audit logging (every auth decision, capability call, identity rotation) with pluggable backends | **Direct match** |
| Observability | Prometheus metrics, OpenTelemetry tracing, W3C Trace Context propagation | **Direct match** |
| Field-level data filtering | OPA policies can enforce per-field access based on caller identity and context | **Strong match** |
| Protocol compatibility | A2A native; compatible with UCP (which declares A2A compatibility) | **Strong match** |
| Anti-fraud infrastructure | Cryptographic identity eliminates API key theft vector; behavioral patterns via metrics | **Partial match** |
| Consumer-facing agent UX | Not in scope (AgentWeave is infrastructure, not UI) | **Not applicable** |

### 3.2 Where AgentWeave Fits in the Stack

```
┌──────────────────────────────────────────────────────┐
│  CONSUMER LAYER (not AgentWeave)                     │
│  ChatGPT / Gemini / Copilot / Perplexity / Siri     │
├──────────────────────────────────────────────────────┤
│  COMMERCE PROTOCOL LAYER                             │
│  ACP (OpenAI/Stripe) │ UCP (Google/Shopify) │ A2A    │
├──────────────────────────────────────────────────────┤
│  ★ AGENTWEAVE LAYER ★                               │
│  Identity (SPIFFE) │ AuthZ (OPA) │ mTLS │ Audit     │
│  Agent Cards │ Observability │ Policy Enforcement    │
├──────────────────────────────────────────────────────┤
│  PAYMENT LAYER                                       │
│  Visa TAP │ Mastercard Agent Pay │ Stripe │ PayPal   │
├──────────────────────────────────────────────────────┤
│  MERCHANT LAYER                                      │
│  Shopify │ Salesforce │ Envive │ Custom backends     │
├──────────────────────────────────────────────────────┤
│  INFRASTRUCTURE                                      │
│  Cloudflare │ Akamai │ AWS/GCP/Azure │ Kubernetes    │
└──────────────────────────────────────────────────────┘
```

AgentWeave occupies the **security and orchestration middleware** layer — below the consumer-facing agents and commerce protocols, above the payment and merchant platforms. It is the "trust fabric" that binds the stack together.

### 3.3 Competitive Positioning

| Solution | Identity | AuthZ | mTLS | A2A | Audit | Multi-Cloud |
|----------|---------|------|------|-----|-------|-------------|
| **AgentWeave** | SPIFFE (crypto) | OPA (policy) | Mandatory | Native | Built-in | Yes (SPIRE federation) |
| Visa TAP | HTTP Signatures | Payment-scoped | TLS | No | Payment logs | Via Cloudflare |
| Cloudflare Web Bot Auth | Public key | Edge rules | TLS | No | Edge logs | Cloudflare only |
| LangGraph | None built-in | None built-in | Optional | No | None | No |
| CrewAI | None built-in | Role-based (app) | Optional | No | None | No |
| Google ADK | Cloud IAM | Cloud IAM | GCP TLS | A2A | Cloud Logging | GCP-centric |

**AgentWeave's differentiator:** It is the only framework that provides cryptographic workload identity + policy-based authorization + mandatory mTLS + A2A protocol + audit logging as an integrated, cannot-be-bypassed stack. The "secure path is the only path" principle is unique and directly addresses the security crisis in agentic commerce.

---

## 4. Target Use Cases in Agentic Commerce

### 4.1 Tier 1: Immediate, High-Value Fit

#### Multi-Agent Retail Orchestration
**Scenario:** A retailer (Walmart, Target) runs multiple internal agents — product search, inventory, pricing, fulfillment, returns — that must communicate securely and with enforced authorization.

**AgentWeave value:**
- Each agent gets a SPIFFE ID: `spiffe://retail.example/agent/inventory/prod`
- OPA policies enforce: "only the order-processor can call fulfillment"
- mTLS ensures no eavesdropping between internal agents
- Audit trail tracks every inter-agent call for SOX/PCI compliance

**Market evidence:** Walmart Sparky coordinates product search, review synthesis, and ordering. These are separate capabilities that benefit from isolated agents with enforced boundaries.

#### B2B Supplier Networks (Agent-to-Agent Negotiation)
**Scenario:** A buyer's agent negotiates with supplier agents across organizations. Forrester predicts 1 in 5 sellers will respond to AI buyer agents with seller-controlled counter-agents in 2026.

**AgentWeave value:**
- SPIRE federation: `spiffe://buyer.com` trusts `spiffe://supplier-a.com`
- OPA policies enforce: "supplier agent can see quantity but not competitor pricing"
- A2A protocol with Agent Cards enables capability discovery
- Audit trail for dispute resolution

**Market evidence:** AgenticPay (academic benchmark) models multi-agent buyer-seller negotiation. Gartner predicts $15 trillion in B2B purchases AI-agent-intermediated by 2028.

#### Cross-Platform Commerce Security
**Scenario:** A merchant serves agents from ChatGPT (ACP), Google (UCP), Copilot, and Perplexity simultaneously. Each agent platform has different trust levels and should have different access.

**AgentWeave value:**
- Assign distinct SPIFFE identities per platform integration
- OPA policies: "ChatGPT agent can browse+checkout; Perplexity agent can browse-only"
- Observability: track conversion rates and latency per platform
- Audit: which platform agent authorized which transaction

**Market evidence:** Shopify Agentic Storefronts manage ChatGPT, Perplexity, and Copilot from one admin. The security/authorization granularity across platforms is currently basic.

### 4.2 Tier 2: Strong Fit with Integration Work

#### Payment Agent Trust Infrastructure
**Scenario:** Complementing Visa TAP / Mastercard Agent Pay with workload-level identity and authorization.

**AgentWeave value:** SPIFFE provides the workload identity that TAP's HTTP Signatures can reference. AgentWeave's OPA layer can enforce payment-specific policies ("this agent can initiate payments up to $500"). The mandatory audit trail satisfies PCI DSS requirements.

**Integration needed:** Bridge between SPIFFE SVIDs and TAP's HTTP Message Signatures.

#### Returns & Refund Chain of Custody
**Scenario:** Returns processing where each step (scan, inspect, authorize, refund, restock) is a separate agent with strict chain-of-custody.

**AgentWeave value:** Directly maps to the existing `data_pipeline` example pattern. OPA enforces "refund agent can only be called by approval agent." Audit trail shows who approved what amount.

**Market evidence:** Returns fraud is a major concern for retailers. Chain-of-custody auditing with cryptographic identity would be a significant improvement over current approaches.

#### Omnichannel Agent Coordination
**Scenario:** Web agent, mobile agent, in-store kiosk agent, and voice agent (Siri/Alexa) all access the same backend with different permission levels.

**AgentWeave value:** Each channel gets a distinct SPIFFE ID. OPA policies enforce channel-specific permissions (kiosk agent can check inventory but needs manager approval for returns over $100). Trace context tracks customer journey across channels.

### 4.3 Tier 3: Exploratory / Longer-Term

| Use Case | Fit | Notes |
|----------|-----|-------|
| Real-time price optimization agents | Moderate | OPA caching helps; main value is audit trail of price changes |
| AI-powered recommendation systems | Moderate | Multi-agent coordination helpful; security less critical |
| Fraud detection agent mesh | Strong | Agents detecting and reporting fraud to each other with verified identity |
| Supply chain visibility networks | Strong | Cross-org federation; chain-of-custody; regulatory compliance |
| Loyalty/rewards agent systems | Strong | Prevent reward fraud; enforce program rules via OPA policies |

---

## 5. Market Sizing & Opportunity

### 5.1 Total Addressable Market

| Metric | Value | Source |
|--------|-------|--------|
| US retail spending via AI platforms (2026) | $20.9B | eMarketer (Dec 2025) |
| US agentic commerce revenue (2030) | $1T | McKinsey |
| Global agentic commerce (2030) | $3-5T | McKinsey |
| B2B AI-agent-intermediated spend (2028) | $15T | Gartner |
| Global agentic AI market (2034) | $200B | Industry estimates |
| AI-driven traffic to retail YoY growth | 693% | Adobe 2025 Holiday Report |
| AI referral conversion premium | 31% higher | Adobe 2025 Holiday Report |
| AI shopping agents market headcount growth | 35% YoY | CB Insights |

### 5.2 AgentWeave's Addressable Slice

AgentWeave targets the **security infrastructure** layer, not the transaction layer. The relevant market is:

- **Agent identity & access management** for commerce: Analogous to IAM for cloud (estimated $20B+ market by 2028)
- **Commerce compliance/audit infrastructure**: Growing with regulatory attention to AI agent transactions
- **Multi-agent orchestration platforms**: CB Insights shows 87% headcount growth in orchestration category

Conservative estimate: If 5-10% of agentic commerce spending requires dedicated trust infrastructure (comparable to security spend as % of IT budgets), AgentWeave's addressable market is **$1-2B by 2028** in agentic commerce alone, with B2B significantly larger.

---

## 6. Risks & Challenges

### 6.1 Protocol Fragmentation
Three competing protocols (ACP, UCP, A2A) may consolidate or fragment. AgentWeave's A2A support and protocol-agnostic security layer mitigate this, but active tracking and adapter development is needed.

**Mitigation:** Build explicit ACP and UCP adapters. Position AgentWeave as the security layer that works *across* protocols.

### 6.2 Hyperscaler Competition
Google (ADK + A2A), Microsoft (Copilot), and Salesforce (Agentforce) could build comparable security into their platforms.

**Mitigation:** AgentWeave's value is multi-cloud and protocol-agnostic. A retailer using Google AI Mode, ChatGPT, and Copilot simultaneously needs a unified trust layer, not three vendor-specific ones. SPIFFE and OPA are CNCF/open-source foundations that resist vendor lock-in.

### 6.3 Adoption Friction
SPIRE + OPA infrastructure requires deployment expertise. Small merchants won't run this themselves.

**Mitigation:** Target platform operators (Shopify, Salesforce, large retailers) who manage infrastructure on behalf of merchants. Provide managed/hosted options and simplified Helm charts (v1.1 roadmap).

### 6.4 Market Timing
Gartner's prediction that 40% of agentic AI projects will be cancelled by 2027 suggests some market correction ahead.

**Mitigation:** AgentWeave helps prevent cancellation by solving the trust/security issues that lead to project failure. "Inadequate risk controls" is a cited cancellation reason — AgentWeave directly addresses this.

### 6.5 Visa TAP / Cloudflare Overlap
Visa TAP and Cloudflare Web Bot Auth use similar cryptographic identity concepts at the edge/payment layer.

**Mitigation:** Position as complementary, not competing. TAP/Web Bot Auth handle edge authentication; AgentWeave handles workload-to-workload trust, authorization policies, and audit across the full agent lifecycle. Explore TAP integration as an extension point.

---

## 7. Strategic Recommendations

### 7.1 Immediate Actions (Q1-Q2 2026)

1. **Build an agentic commerce example** — Create a reference implementation showing a multi-agent retail scenario (shopper agent, inventory agent, pricing agent, checkout agent) with AgentWeave securing all communication. Make it runnable, shareable, and compelling.

2. **Publish a position paper** — "Cryptographic Trust for Agentic Commerce: Why API Keys Won't Scale" targeting CTOs and security architects at mid-to-large retailers.

3. **Implement ACP/UCP adapters** — Build thin protocol adapters showing AgentWeave as the security layer under ACP (Stripe/OpenAI) and UCP (Google/Shopify) transactions.

4. **Engage with Visa TAP** — Explore integration between SPIFFE SVIDs and TAP's HTTP Message Signatures. A bridge between workload identity and payment identity is highly differentiating.

### 7.2 Medium-Term (Q3-Q4 2026)

5. **Target Shopify ecosystem** — Shopify's Agentic Storefronts manage multiple AI platform integrations from one admin. AgentWeave could provide the security layer for Shopify apps/partners that build agentic capabilities.

6. **Contribute to A2A protocol security specs** — AgentWeave's Agent Card + mTLS + SPIFFE model is more secure than the current A2A spec's authentication. Contributing security enhancements upstream builds credibility and adoption.

7. **Build a managed offering** — Reduce deployment friction with a hosted SPIRE + OPA + AgentWeave service. Target mid-market retailers who need agentic commerce security but lack infrastructure teams.

### 7.3 Long-Term (2027+)

8. **B2B agent commerce** — Position for the $15T B2B opportunity (Gartner 2028). Multi-organization federation with SPIRE is AgentWeave's strongest differentiator here.

9. **Regulatory compliance certifications** — As regulations catch up to agentic commerce, AgentWeave's audit trail and default-deny posture become compliance requirements rather than nice-to-haves.

10. **Agent marketplace trust** — As agent ecosystems grow, the ability to verify an agent's identity and enforce what it can do becomes infrastructure. AgentWeave could be the "certificate authority" of the agent economy.

---

## 8. Verdict

**AgentWeave is a strong fit for the agentic commerce market, with specific positioning required.**

It is **not** a shopping agent, recommendation engine, or consumer-facing product. It is the **trust and security infrastructure** that the agentic commerce ecosystem is actively building in fragmented, vendor-specific ways (Visa TAP, Cloudflare Web Bot Auth, Google Cloud IAM).

AgentWeave's advantages:
- **Already built:** Cryptographic identity, mTLS, OPA authorization, A2A protocol, audit logging — all production-ready
- **Already aligned:** A2A protocol compatibility, CNCF foundations (SPIFFE, OPA), open-source
- **Uniquely positioned:** Multi-cloud, multi-protocol, vendor-agnostic security — no existing solution covers this
- **Addresses the top failure reason:** Gartner says inadequate risk controls kill agentic projects. AgentWeave makes risk controls mandatory.

The market is real ($20.9B in 2026, $1T+ by 2030), the security gap is documented and growing, and AgentWeave's technology directly addresses it. The key execution risk is adoption friction and hyperscaler competition. The mitigation is positioning as the neutral, protocol-agnostic trust layer and targeting platform operators rather than individual merchants.

**Recommendation: Pursue aggressively. Build the commerce example, publish the position paper, and engage with the protocol communities (A2A, ACP, UCP, Visa TAP) in Q1-Q2 2026.**

---

## Sources

### Tech Platform Initiatives
- [Why the AI shopping agent wars will heat up in 2026 — Modern Retail](https://www.modernretail.co/technology/why-the-ai-shopping-agent-wars-will-heat-up-in-2026/)
- [Buy it in ChatGPT: Instant Checkout and ACP — OpenAI](https://openai.com/index/buy-it-in-chatgpt/)
- [Google launches agentic commerce suite — CXNetwork](https://www.cxnetwork.com/artificial-intelligence/news/google-agentic-commerce-ai-shopping)
- [Microsoft Copilot Checkout and Brand Agents — Microsoft Ads Blog](https://about.ads.microsoft.com/en/blog/post/january-2026/conversations-that-convert-copilot-checkout-and-brand-agents)
- [Shop like a Pro — Perplexity](https://www.perplexity.ai/hub/blog/shop-like-a-pro)
- [Salesforce Agentforce Commerce — Salesforce](https://www.salesforce.com/news/stories/agentforce-commerce-capabilities-announcement/)

### Retailer Initiatives
- [Walmart: The Future of Shopping Is Agentic. Meet Sparky — Walmart Corporate](https://corporate.walmart.com/news/2025/06/06/walmart-the-future-of-shopping-is-agentic-meet-sparky)
- [Amazon's Agent Dilemma: Block AI Bots or Join Them — TechBuzz](https://www.techbuzz.ai/articles/amazon-s-agent-dilemma-block-ai-bots-or-join-them)
- [Shopify: The Agentic Commerce Platform — Shopify](https://www.shopify.com/news/ai-commerce-at-scale)
- [Instacart App Launches in OpenAI ChatGPT — Instacart](https://investors.instacart.com/news-releases/news-release-details/instacart-app-launches-openai-chatgpt-first-company-offer-new)

### Commerce Protocols
- [Developing an open standard for agentic commerce — Stripe](https://stripe.com/blog/developing-an-open-standard-for-agentic-commerce)
- [Under the Hood: Universal Commerce Protocol (UCP) — Google Developers Blog](https://developers.googleblog.com/under-the-hood-universal-commerce-protocol-ucp/)
- [Announcing Agent2Agent Protocol (A2A) — Google Developers Blog](https://developers.googleblog.com/en/a2a-a-new-era-of-agent-interoperability/)
- [Agentic Commerce Protocol — OpenAI Developers](https://developers.openai.com/commerce/)
- [Shopify agentic commerce developer docs](https://shopify.dev/docs/agents)

### Security & Trust
- [Agentic Commerce: Threats and Risks — Visa](https://corporate.visa.com/en/sites/visa-perspectives/security-trust/the-threats-landscape-of-agentic-commerce.html)
- [Visa Trusted Agent Protocol — Visa Developer](https://developer.visa.com/capabilities/trusted-agent-protocol)
- [Securing agentic commerce with AI Agents — Cloudflare](https://blog.cloudflare.com/secure-agentic-commerce/)
- [The age of agents: cryptographically recognizing agent traffic — Cloudflare](https://blog.cloudflare.com/signed-agents/)
- [Akamai and Visa Join Forces — Akamai](https://www.akamai.com/newsroom/press-release/akamai-and-visa-join-forces-to-secure-the-next-era-of-agentic-commerce)
- [Trusting AI to buy: secure agentic commerce — Mastercard](https://www.mastercard.com/global/en/news-and-trends/stories/2026/agentic-commerce-standards.html)
- [Building Complete Agent Trust — Security Boulevard](https://securityboulevard.com/2026/02/building-complete-agent-trust-why-authentication-behavioral-intelligence-matters/)
- [AI agents could be worth $236B if we ensure they are the good kind — WEF](https://www.weforum.org/stories/2026/01/ai-agents-trust/)

### Analyst Forecasts
- [Gartner: AI agents will command $15T in B2B purchases by 2028 — Digital Commerce 360](https://www.digitalcommerce360.com/2025/11/28/gartner-ai-agents-15-trillion-in-b2b-purchases-by-2028/)
- [Gartner Predicts 40% of Agentic AI Projects Cancelled by 2027 — Gartner](https://www.gartner.com/en/newsroom/press-releases/2025-06-25-gartner-predicts-over-40-percent-of-agentic-ai-projects-will-be-canceled-by-end-of-2027)
- [Predictions 2026: The Agentic Commerce Race — Forrester](https://www.forrester.com/blogs/predictions-2026-the-agentic-commerce-race-and-some-potential-regrets-in-digital-commerce/)
- [The agentic commerce opportunity — McKinsey](https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-agentic-commerce-opportunity-how-ai-agents-are-ushering-in-a-new-era-for-consumers-and-merchants)
- [The agentic commerce market map — CB Insights](https://www.cbinsights.com/research/report/agentic-commerce-market-map/)

### Market Data
- [Adobe: Holiday Shopping Season Drove Record $257.8B — Adobe](https://news.adobe.com/news/2026/01/adobe-holiday-shopping-season)
- [AI's 693% Holiday Traffic Explosion — WebProNews](https://www.webpronews.com/ais-693-holiday-traffic-explosion-retails-new-commerce-frontier/)
- [2025 marked the birth of agentic commerce — Retail Brew](https://www.retailbrew.com/stories/2025/12/17/2025-the-birth-of-agentic-commerce)
- [A new era of agentic commerce is here — Google Cloud Blog](https://cloud.google.com/transform/a-new-era-agentic-commerce-retail-ai)

### Startups
- [Envive raises $15M to build AI agents for online retailers — GeekWire](https://www.geekwire.com/2025/commerce-is-entering-the-agentic-era-envive-raises-15m-to-build-ai-agents-for-online-retailers/)
- [Phia: The AI shopping agent — Kleiner Perkins](https://www.kleinerperkins.com/perspectives/phia-the-ai-shopping-agent-for-the-next-generation/)
- [Amazon sues Perplexity over AI shopping agents — Retail Dive](https://www.retaildive.com/news/amazon-sues-perplexity-ai-shopping-agents/804871/)
