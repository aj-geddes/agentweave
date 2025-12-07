---
layout: page
title: About
description: About the AgentWeave SDK project - history, philosophy, team, and acknowledgments
nav_order: 12
---

# About AgentWeave

AgentWeave is an open-source Python SDK for building secure, cross-cloud AI agents with cryptographic identity and automatic authorization. Built on industry-standard technologies like SPIFFE, OPA, and the A2A protocol, AgentWeave makes security the default path - not an afterthought.

---

## Project History

### Origins

AgentWeave was born from a simple observation: **AI agents are getting more powerful, but agent security hasn't kept pace.**

Traditional agent frameworks focus on capabilities - what agents can do - but largely ignore security fundamentals like identity verification, authorization, and secure communication. Developers are left to implement security themselves, leading to inconsistent implementations, subtle vulnerabilities, and security bypasses.

The founding team asked: **What if security was built into the framework, not bolted on afterward?**

### Timeline

- **Q4 2024** - Initial concept and design
- **Q1 2025** - Core architecture and SPIFFE integration
- **Q2 2025** - A2A protocol implementation
- **Q3 2025** - Beta release and community feedback
- **January 2025** - Version 1.0.0 released

### Evolution

AgentWeave started as an internal project at a security-focused AI company dealing with multi-cloud agent deployments. After realizing the broader industry faced the same challenges, we open-sourced the project to benefit the entire AI agent ecosystem.

---

## Design Philosophy

AgentWeave is built on several core principles:

### 1. The Secure Path is the Only Path

**Principle:** Security should be impossible to bypass, even accidentally.

Unlike traditional frameworks where security is optional or easy to misconfigure, AgentWeave enforces security at the framework level. There's no way to "turn off" identity verification or authorization - if you're using AgentWeave, you're using a secure agent.

**Why?** Because the easiest way to prevent security bugs is to make them impossible.

### 2. Identity Over Credentials

**Principle:** Use cryptographic identity instead of shared secrets.

AgentWeave uses SPIFFE for workload identity. Every agent has a cryptographically verifiable identity (like `spiffe://yourorg.com/agent/processor`). No API keys, no passwords, no secrets to rotate or leak.

**Why?** Shared secrets are the root cause of most security breaches. Cryptographic identity eliminates entire classes of vulnerabilities.

### 3. Zero-Trust by Default

**Principle:** Trust nothing, verify everything.

All agent-to-agent communication uses mutual TLS. Both parties verify each other's identity before exchanging data. Authorization policies are evaluated on every request. Default deny in production.

**Why?** Perimeter security is dead. Modern systems need defense in depth with per-request authorization.

### 4. Standards Over Proprietary

**Principle:** Build on open standards, not vendor lock-in.

AgentWeave uses industry standards:
- **SPIFFE** for identity (CNCF standard)
- **OPA** for authorization (CNCF standard)
- **A2A protocol** for communication (open standard)
- **OpenTelemetry** for observability (CNCF standard)

**Why?** Open standards ensure interoperability, prevent vendor lock-in, and leverage community expertise.

### 5. Developer Experience Matters

**Principle:** Security should be transparent and developer-friendly.

While security is enforced, developers shouldn't have to think about it constantly. AgentWeave uses decorators, type hints, and sensible defaults to make secure development feel natural.

**Why?** If security is painful, developers will fight it. Make it easy, and they'll embrace it.

### 6. Production-Ready from Day One

**Principle:** Every feature should be production-ready before release.

AgentWeave includes comprehensive testing, observability, error handling, and documentation. Features aren't released as "experimental" - they're ready for production use.

**Why?** Developers need tools they can rely on. Half-baked features erode trust.

---

## Core Team

AgentWeave is developed and maintained by a team of security and distributed systems engineers:

### Project Maintainers

**AJ Geddes** - Project Lead & Chief Architect
GitHub: [@aj-geddes](https://github.com/aj-geddes)
Focus: Architecture, security model, identity systems

**[Name]** - Core Developer
GitHub: [@username]
Focus: A2A protocol, transport layer, gRPC implementation

**[Name]** - Core Developer
GitHub: [@username]
Focus: Authorization, OPA integration, policy framework

### Emeritus Maintainers

Contributors who have stepped back from active maintenance but made significant contributions to the project.

### Contributors

AgentWeave is made possible by contributions from developers around the world. See our [CONTRIBUTORS.md](https://github.com/aj-geddes/agentweave/blob/main/CONTRIBUTORS.md) for a full list.

### How to Join

Interested in becoming a maintainer?
1. Start by contributing (see [Contributing Guide](contributing/index.md))
2. Demonstrate expertise in specific areas
3. Actively participate in reviews and discussions
4. Existing maintainers will invite you to join

---

## Acknowledgments

AgentWeave builds on the shoulders of giants. We're grateful to:

### Organizations

- **SPIFFE/SPIRE Project** - For creating a robust workload identity standard
- **Open Policy Agent (OPA)** - For flexible, powerful policy-based authorization
- **Cloud Native Computing Foundation (CNCF)** - For fostering open standards
- **Python Software Foundation** - For the Python language and ecosystem

### Inspiration

AgentWeave was inspired by:
- **Istio** - Service mesh and zero-trust networking patterns
- **HashiCorp Vault** - Secrets management and identity-based security
- **Kubernetes** - Declarative configuration and operator patterns
- **gRPC** - High-performance RPC framework
- **FastAPI** - Developer-friendly Python framework design

### Technologies

Core technologies that power AgentWeave:
- **SPIFFE/SPIRE** - Workload identity framework
- **Open Policy Agent** - Policy engine
- **gRPC** - Communication protocol
- **Python asyncio** - Async runtime
- **Pydantic** - Data validation
- **Prometheus** - Metrics
- **OpenTelemetry** - Distributed tracing

---

## Related Projects

AgentWeave is part of the broader AI agent ecosystem:

### SPIFFE/SPIRE

**Website:** [spiffe.io](https://spiffe.io)
**Why it matters:** SPIFFE provides the identity foundation for AgentWeave. Every agent's cryptographic identity comes from SPIRE.

### Open Policy Agent (OPA)

**Website:** [openpolicyagent.org](https://www.openpolicyagent.org)
**Why it matters:** OPA enables flexible, policy-based authorization. AgentWeave evaluates Rego policies for every agent interaction.

### A2A Protocol

**Specification:** [a2a-protocol.org](https://a2a-protocol.org)
**Why it matters:** The A2A (Agent-to-Agent) protocol is an open standard for agent communication. AgentWeave agents can interoperate with agents built using other A2A-compatible frameworks.

### Related AI Agent Frameworks

- **Google ADK (Agent Development Kit)** - Google's agent framework with A2A support
- **AWS Bedrock AgentCore** - AWS agent framework
- **LangChain** - Popular agent orchestration framework
- **AutoGen** - Microsoft's multi-agent framework
- **CrewAI** - Role-based multi-agent framework

### Complementary Tools

- **Tailscale** - Mesh networking for cross-cloud connectivity
- **Consul** - Service discovery and configuration
- **Vault** - Secrets management
- **cert-manager** - Kubernetes certificate management

---

## License

AgentWeave is licensed under the **Apache License 2.0**.

### What This Means

The Apache 2.0 license is:
- **Permissive** - Use AgentWeave in commercial and non-commercial projects
- **Patent-safe** - Includes explicit patent grant
- **Attribution required** - Include copyright and license notice
- **Modification friendly** - Modify and distribute modified versions

### Full License Text

See the [LICENSE](https://github.com/aj-geddes/agentweave/blob/main/LICENSE) file in the repository.

### Why Apache 2.0?

We chose Apache 2.0 because:
1. It's widely understood and accepted in the enterprise
2. It's compatible with most other open-source licenses
3. It includes patent protection for users
4. It allows both open-source and commercial use

---

## Governance

AgentWeave follows an open governance model:

### Decision Making

- **Technical decisions** - Made by consensus among maintainers
- **Security issues** - Handled privately until patches are available
- **Breaking changes** - Require RFC and community discussion
- **Feature requests** - Prioritized based on community needs

### RFC Process

For significant changes:
1. Author writes an RFC (Request for Comments)
2. RFC is posted for community feedback
3. Discussion and iteration period (typically 2 weeks)
4. Maintainers make final decision
5. Accepted RFCs are implemented

### Release Process

See our [Changelog](changelog.md) for details on:
- Release schedule
- Versioning policy
- Support policy
- Deprecation process

---

## Community

Join the AgentWeave community:

### Communication Channels

- **GitHub Discussions** - [Discussions](https://github.com/aj-geddes/agentweave/discussions)
- **GitHub Issues** - [Issues](https://github.com/aj-geddes/agentweave/issues)
- **Discord** - [Join our Discord](https://discord.gg/agentweave)
- **Twitter** - [@agentweave](https://twitter.com/agentweave)
- **Mailing List** - [Subscribe](https://agentweave.io/newsletter)

### Events

- **Monthly Community Calls** - First Tuesday of each month
- **Office Hours** - Thursdays 2-3pm UTC
- **Contributor Summits** - Quarterly virtual meetups
- **Conference Talks** - Find us at KubeCon, PyCon, and security conferences

### Resources

- **Blog** - [blog.agentweave.io](https://blog.agentweave.io)
- **YouTube** - [AgentWeave Channel](https://youtube.com/@agentweave)
- **Examples Repository** - [agentweave/examples](https://github.com/agentweave/examples)

---

## Roadmap

Want to see where AgentWeave is headed?

### Short-term (Next 6 months)

- Enhanced observability with auto-instrumentation
- Additional identity provider integrations
- Performance optimizations for high-throughput scenarios
- WebSocket transport for browser-based agents

### Medium-term (6-12 months)

- Service mesh integration (Istio, Linkerd)
- Advanced routing and load balancing
- Agent orchestration patterns
- Multi-tenant isolation improvements

### Long-term (12+ months)

- Formal verification of security properties
- Language SDKs beyond Python (Go, TypeScript, Rust)
- Edge deployment optimizations
- Enhanced developer tooling and IDE integrations

See our [GitHub Projects](https://github.com/aj-geddes/agentweave/projects) for detailed roadmap and progress.

---

## Support

### Free Support

- **Documentation** - Comprehensive docs at [docs.agentweave.io](https://aj-geddes.github.io/agentweave/)
- **Community** - Get help from the community in [Discussions](https://github.com/aj-geddes/agentweave/discussions)
- **Bug Reports** - Report issues on [GitHub](https://github.com/aj-geddes/agentweave/issues)

### Commercial Support

Commercial support, training, and consulting available through our partners:
- **Email** - support@agentweave.io
- **Enterprise Plans** - Custom SLAs and priority support
- **Training** - On-site or virtual training sessions
- **Consulting** - Architecture reviews and implementation assistance

---

## Contact

Questions about AgentWeave?

- **General Inquiries** - hello@agentweave.io
- **Security Issues** - security@agentweave.io
- **Commercial Support** - support@agentweave.io
- **Code of Conduct** - conduct@agentweave.io
- **Media/Press** - press@agentweave.io

---

## Sponsor the Project

AgentWeave is free and open source, but development takes time and resources. Support the project:

- **GitHub Sponsors** - [Sponsor on GitHub](https://github.com/sponsors/agentweave)
- **Corporate Sponsorship** - Contact sponsor@agentweave.io
- **Contribute** - Code, documentation, and testing are always welcome

### Sponsors

We're grateful to our sponsors who make AgentWeave possible:

**Platinum Sponsors**
- [Your Company Here]

**Gold Sponsors**
- [Your Company Here]

**Silver Sponsors**
- [Your Company Here]

Interested in sponsoring? Email sponsor@agentweave.io

---

## FAQ

### Who is AgentWeave for?

AgentWeave is for developers building AI agents that need:
- Strong security guarantees
- Cross-cloud deployment
- Identity verification
- Authorization policies
- Interoperability with other agent frameworks

### Is AgentWeave production-ready?

Yes! Version 1.0.0 is production-ready and used in production by multiple organizations.

### What cloud providers does AgentWeave support?

AgentWeave is cloud-agnostic and runs on:
- AWS (ECS, EKS, EC2)
- Google Cloud (Cloud Run, GKE, Compute Engine)
- Azure (Container Apps, AKS, VMs)
- On-premises Kubernetes
- Any environment with SPIRE support

### Can AgentWeave integrate with LangChain/AutoGen/etc?

Yes! AgentWeave agents can be wrapped in LangChain tools or integrated with other frameworks. The A2A protocol also enables interoperability with other A2A-compatible frameworks.

### What programming languages does AgentWeave support?

Currently Python 3.10+. Additional language SDKs (Go, TypeScript, Rust) are on the roadmap.

### Is AgentWeave suitable for hobbyist projects?

Absolutely! While AgentWeave excels in enterprise environments, it's also great for learning about secure agent architectures and distributed systems.

---

Thank you for using AgentWeave! Together, we're making AI agents more secure.

---

**Learn More:**
- [Getting Started Guide](getting-started/index.md)
- [Contributing Guide](contributing/index.md)
- [Changelog](changelog.md)
- [GitHub Repository](https://github.com/aj-geddes/agentweave)
