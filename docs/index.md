---
layout: home
title: AgentWeave SDK
description: Build secure, cross-cloud AI agents with cryptographic identity and zero-trust authorization
permalink: /

hero:
  title: "AgentWeave SDK"
  tagline: "The secure path is the only path"
  description: "Build production-ready AI agents with built-in cryptographic identity, mutual TLS, and policy-based authorization. Security isn't optional—it's automatic."
  code_example: |
    from agentweave import SecureAgent, capability

    class DataProcessor(SecureAgent):
        @capability("process", description="Process incoming data")
        async def process(self, data: dict) -> dict:
            return {"status": "processed", "id": data["id"]}

    # Identity, mTLS, and authorization are automatic
    agent = DataProcessor.from_config("config.yaml")
    agent.run()

features:
  title: "Built for Security, Designed for Simplicity"
  subtitle: "Everything you need to build production-grade AI agents"
  items:
    - icon: "shield"
      title: "Zero-Trust Security"
      description: "Every request is authenticated and authorized. Default-deny policies ensure no accidental access. Security cannot be bypassed—it's baked into the SDK."
      link:
        text: "Learn about security"
        url: "/security/"

    - icon: "lock"
      title: "SPIFFE Identity"
      description: "Cryptographic workload identity via SPIRE. Automatic certificate rotation. No hardcoded secrets. Trust established through verifiable credentials."
      link:
        text: "Identity concepts"
        url: "/concepts/identity/"

    - icon: "code"
      title: "A2A Protocol"
      description: "Standardized agent-to-agent communication. Framework-agnostic. Built-in capability discovery via Agent Cards. Works with any A2A-compatible system."
      link:
        text: "A2A protocol guide"
        url: "/concepts/a2a-protocol/"

    - icon: "zap"
      title: "OPA Authorization"
      description: "Fine-grained policy-based access control. Policies as code with Rego. Audit every decision. Decouple authorization from business logic."
      link:
        text: "Authorization guide"
        url: "/concepts/authorization/"

    - icon: "layers"
      title: "mTLS Transport"
      description: "Mutual TLS for all communication. TLS 1.3 enforced. Peer verification mandatory. Encrypted end-to-end with zero downgrade attacks."
      link:
        text: "Transport layer"
        url: "/concepts/mtls/"

    - icon: "cloud"
      title: "Observability"
      description: "Built-in metrics, tracing, and audit logging. OpenTelemetry integration. Prometheus-compatible metrics. Debug and monitor production agents."
      link:
        text: "Observability guide"
        url: "/concepts/observability/"

technologies:
  title: "Built on Production-Proven Technologies"
  items:
    - name: "SPIFFE/SPIRE"
      description: "CNCF-graduated cryptographic identity framework. Used by Netflix, Pinterest, Uber, and Square in production."
      link: "https://spiffe.io"

    - name: "Open Policy Agent"
      description: "CNCF-graduated policy engine for cloud-native environments. Decoupled authorization at scale."
      link: "https://www.openpolicyagent.org"

    - name: "A2A Protocol"
      description: "Linux Foundation standard for agent-to-agent communication. Framework-agnostic interoperability."
      link: "https://a2a-protocol.org"

    - name: "OpenTelemetry"
      description: "CNCF standard for observability. Unified metrics, traces, and logs across your agent infrastructure."
      link: "https://opentelemetry.io"

getting_started:
  title: "Get Started in Minutes"
  steps:
    - title: "Install AgentWeave"
      description: "Install the SDK using pip. Requires Python 3.10 or higher."
      code: "pip install agentweave"

    - title: "Create Your Agent"
      description: "Define your agent with the @capability decorator. Security is automatic."
      code: |
        from agentweave import SecureAgent, capability

        class MyAgent(SecureAgent):
            @capability("greet")
            async def greet(self, name: str) -> dict:
                return {"message": f"Hello, {name}!"}

    - title: "Configure & Run"
      description: "Set up identity, authorization, and transport in config.yaml, then start your agent."
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
      description: "Comprehensive guides, tutorials, and API reference for every feature of AgentWeave."
      url: "/getting-started/"

    - icon: "github"
      title: "Discussions"
      description: "Ask questions, share projects, and connect with other AgentWeave developers."
      url: "https://github.com/aj-geddes/agentweave/discussions"

    - icon: "github"
      title: "Report Issues"
      description: "Found a bug or have a feature request? Let us know on GitHub Issues."
      url: "https://github.com/aj-geddes/agentweave/issues"
---

## Why AgentWeave?

### Security by Design, Not Afterthought

Building secure AI agents shouldn't require security expertise. AgentWeave makes the secure path the only path.

#### Traditional Approach

- API keys in environment variables
- Plain HTTP or self-signed TLS
- Authorization logic scattered in code
- No audit trail
- Security bolted on later
- Custom protocols per framework

#### AgentWeave Approach

- Cryptographic identity via SPIFFE
- Mutual TLS with automatic rotation
- OPA policy enforcement (default-deny)
- Every decision audited and logged
- Security cannot be bypassed
- Standard A2A protocol (framework-agnostic)

### Production-Ready from Day One

AgentWeave is built on CNCF-graduated technologies trusted by industry leaders:

- **SPIFFE/SPIRE** - Used by Netflix, Pinterest, Uber, Square
- **Open Policy Agent** - Proven at scale in cloud-native environments
- **A2A Protocol** - Linux Foundation standard for agent interoperability
- **mTLS** - Industry-standard encrypted communication

### Cross-Cloud by Default

Deploy agents anywhere—AWS, GCP, Azure, on-premises—and they can securely communicate:

- **Federated Identity** - Trust across organizational boundaries
- **Optional Tailscale Integration** - Zero-config mesh networking
- **Kubernetes Native** - First-class Helm charts and operators
- **Cloud Agnostic** - No vendor lock-in

## Ready to Build?

Get your first secure agent running in 5 minutes.

<div class="cta-box">
  <a href="/getting-started/quickstart/" class="btn btn-primary btn-large">Get Started</a>
  <a href="/examples/" class="btn btn-secondary btn-large">View Examples</a>
</div>
