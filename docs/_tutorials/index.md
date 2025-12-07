---
layout: tutorial
title: Tutorials Overview
permalink: /tutorials/
nav_order: 1
---

# Tutorials Overview

Welcome to the AgentWeave SDK tutorials! These hands-on guides will take you from building your first agent to deploying sophisticated multi-agent systems across cloud providers.

## How to Use These Tutorials

Each tutorial includes:
- **Clear learning objectives** - What you'll accomplish
- **Skill level indicator** - Beginner, Intermediate, or Advanced
- **Time estimate** - Plan your learning session
- **Prerequisites** - What you need before starting
- **Step-by-step instructions** - Detailed guidance with explanations
- **Complete code examples** - Working code you can copy and modify
- **Exercises** - Practice what you've learned

## Tutorial Path

We recommend following the tutorials in order, but you can jump to specific topics based on your needs.

### Beginner Tutorials

Start here if you're new to AgentWeave or building AI agents.

#### [Building Your First Agent](/tutorials/first-agent/)
**Time:** 30 minutes | **Level:** Beginner

Build a complete, secure agent from scratch. Learn the fundamentals of agent configuration, capability definition, and secure communication.

**Prerequisites:**
- AgentWeave SDK installed
- Basic Python knowledge
- SPIRE server running (see [Installation Guide](/getting-started/installation/))

**What you'll learn:**
- Project structure for agents
- Writing configuration files
- Defining agent capabilities
- Running and testing agents
- Basic security concepts

### Intermediate Tutorials

Once you've built your first agent, these tutorials explore key AgentWeave features.

#### [Agent-to-Agent Communication](/tutorials/agent-communication/)
**Time:** 45 minutes | **Level:** Intermediate

Build a two-agent system where agents communicate securely using the A2A protocol. Create an orchestrator agent that delegates work to a worker agent.

**Prerequisites:**
- Completed "Building Your First Agent"
- Understanding of basic networking concepts
- SPIRE and OPA running

**What you'll learn:**
- Multi-agent architecture patterns
- Using the `call_agent()` method
- Handling responses and errors
- Request/response patterns
- Debugging agent communication

#### [Writing OPA Policies](/tutorials/opa-policies/)
**Time:** 45 minutes | **Level:** Intermediate

Master authorization by writing custom OPA policies in Rego. Learn to control who can call your agents and what they can do.

**Prerequisites:**
- Completed "Building Your First Agent"
- Basic understanding of authorization concepts
- OPA installed

**What you'll learn:**
- OPA and Rego fundamentals
- Policy file structure
- Common authorization patterns
- Testing policies
- Integrating policies with agents
- Best practices for policy design

#### [Adding Observability](/tutorials/observability/)
**Time:** 30 minutes | **Level:** Intermediate

Instrument your agents with metrics, tracing, and structured logging. Set up a complete observability stack for monitoring production agents.

**Prerequisites:**
- Completed "Building Your First Agent"
- Docker or Kubernetes for running observability tools
- Basic understanding of monitoring concepts

**What you'll learn:**
- Configuring Prometheus metrics
- Setting up OpenTelemetry tracing
- Structured logging best practices
- Using Grafana dashboards
- Viewing traces in Jaeger
- Audit log patterns

### Advanced Tutorials

These tutorials cover production deployment scenarios and advanced architectures.

#### [Deploying to Kubernetes](/tutorials/kubernetes-deployment/)
**Time:** 60 minutes | **Level:** Advanced

Deploy agents to Kubernetes with SPIRE, OPA, and full observability. Learn production-ready configurations, health checks, and scaling strategies.

**Prerequisites:**
- Kubernetes cluster (local or cloud)
- kubectl and helm installed
- Completed intermediate tutorials
- Understanding of Kubernetes concepts

**What you'll learn:**
- Installing SPIRE on Kubernetes
- Deploying OPA for policy enforcement
- Creating agent deployments
- ConfigMaps and Secrets management
- Service mesh integration
- Health checks and liveness probes
- Horizontal scaling
- Production best practices

#### [Cross-Cloud Agent Mesh](/tutorials/multi-cloud/)
**Time:** 90 minutes | **Level:** Advanced

Build a multi-cloud agent mesh spanning AWS, GCP, and Azure. Configure SPIFFE federation and optional Tailscale integration for seamless cross-cloud communication.

**Prerequisites:**
- Access to multiple cloud providers
- Completed "Deploying to Kubernetes"
- Understanding of cloud networking
- Advanced Kubernetes knowledge

**What you'll learn:**
- Multi-cloud architecture design
- SPIFFE trust domain federation
- Cross-cloud networking strategies
- Tailscale mesh integration
- Cloud-specific deployment patterns
- Testing cross-cloud connectivity
- Troubleshooting federation issues
- Production operational patterns

## Learning Paths

### Path 1: Quick Start to Production
**Goal:** Get a basic agent running in production quickly

1. Building Your First Agent (30 min)
2. Adding Observability (30 min)
3. Deploying to Kubernetes (60 min)

**Total time:** 2 hours

### Path 2: Multi-Agent Systems
**Goal:** Build sophisticated agent collaboration patterns

1. Building Your First Agent (30 min)
2. Agent-to-Agent Communication (45 min)
3. Writing OPA Policies (45 min)
4. Adding Observability (30 min)

**Total time:** 2.5 hours

### Path 3: Enterprise Deployment
**Goal:** Production-ready, multi-cloud deployment

1. All Beginner and Intermediate tutorials (2.5 hours)
2. Deploying to Kubernetes (60 min)
3. Cross-Cloud Agent Mesh (90 min)

**Total time:** 5 hours

## Getting Help

If you get stuck:

1. **Check the documentation** - Review [Core Concepts](/core-concepts/) and [API Reference](/api-reference/)
2. **Review examples** - See working code in [Examples](/examples/)
3. **Read troubleshooting** - Common issues in [Troubleshooting](/troubleshooting/)
4. **Ask the community** - Post in [GitHub Discussions](https://github.com/aj-geddes/agentweave/discussions)
5. **Report bugs** - File issues at [GitHub Issues](https://github.com/aj-geddes/agentweave/issues)

## Additional Resources

- **[How-To Guides](/guides/)** - Task-oriented guides for specific features
- **[Examples Gallery](/examples/)** - Complete working examples
- **[API Reference](/api-reference/)** - Detailed API documentation
- **[Configuration Reference](/api-reference/config/)** - All configuration options

## What's Next?

Ready to start? Jump into [Building Your First Agent](/tutorials/first-agent/) and create your first secure AI agent in 30 minutes!

Already experienced? Explore advanced topics:
- [Multi-Agent Communication Patterns](/core-concepts/communication/)
- [Advanced Authorization Policies](/guides/policy-patterns/)
- [Production Operations](/guides/production-checklist/)
