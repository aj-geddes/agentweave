---
layout: page
title: How-To Guides
description: Task-oriented guides for solving specific problems with AgentWeave
nav_order: 5
has_children: true
---

# How-To Guides

How-To Guides are **task-oriented** documentation that help you solve specific problems. Unlike tutorials (which teach concepts step-by-step), these guides assume you have basic AgentWeave knowledge and want to accomplish a particular goal.

## What's the Difference?

| Tutorials | How-To Guides |
|-----------|---------------|
| Learning-oriented | Task-oriented |
| Take you by the hand | Assume basic knowledge |
| Get you started | Solve a specific problem |
| "Learn how to build agents" | "Configure SPIRE identity" |

## Categories

### Identity & Security

- **[Configure Identity Providers](identity-providers.md)** - Set up SPIFFE/SPIRE or static mTLS certificates for agent identity
- **[Common Authorization Patterns](policy-patterns.md)** - Real-world OPA policy patterns with complete Rego examples

### Development & Testing

- **[Testing Your Agents](testing.md)** - Unit testing, mocking, integration tests, and CI/CD integration
- **[Error Handling Best Practices](error-handling.md)** - Handle exceptions gracefully and implement retry strategies

### Operations & Production

- **[Performance Tuning](performance.md)** - Optimize connection pools, caching, and async operations
- **[Production Readiness Checklist](production-checklist.md)** - Comprehensive checklist for deploying agents to production

## Quick Links by Use Case

### "I need to..."

**Set up identity for development**
- See: [Identity Providers - Static mTLS (Development)](identity-providers.md#static-mtls-development-only)

**Deploy to production with SPIRE**
- See: [Identity Providers - SPIFFE/SPIRE Setup](identity-providers.md#spiffespire-setup)

**Allow specific agents to call my capabilities**
- See: [Policy Patterns - Allow Specific Agents](policy-patterns.md#pattern-allow-specific-agents)

**Test my agent with mocked dependencies**
- See: [Testing - Using Mock Providers](testing.md#using-mock-providers)

**Handle authorization failures gracefully**
- See: [Error Handling - Handling AuthorizationError](error-handling.md#handling-authorizationerror)

**Improve agent performance**
- See: [Performance Tuning - Connection Pool Configuration](performance.md#connection-pool-configuration)

**Prepare for production deployment**
- See: [Production Readiness Checklist](production-checklist.md)

## Before You Start

Make sure you've completed:
1. [Installation](/agentweave/getting-started/installation/) - AgentWeave SDK installed
2. [5-Minute Quickstart](/agentweave/getting-started/quickstart/) - Built your first agent
3. [Core Concepts](/agentweave/core-concepts/) - Understand identity, authorization, and A2A protocol

## Contributing

Found a problem not covered here? Want to add a guide? We welcome contributions:

1. Check existing [GitHub Issues](https://github.com/aj-geddes/agentweave/issues)
2. Open a new issue describing the problem you want to solve
3. Submit a pull request with your guide following our [documentation template](https://github.com/aj-geddes/agentweave/blob/main/docs/TEMPLATE.md)

## Related Documentation

- [Tutorials](/agentweave/tutorials/) - Step-by-step learning guides
- [API Reference](/agentweave/api-reference/) - Detailed API documentation
- [Examples](/agentweave/examples/) - Complete example applications
- [Core Concepts](/agentweave/core-concepts/) - Conceptual explanations

---

**Next Steps:**
- Browse guides by category above
- Jump to a specific problem using Quick Links
- Check the [Production Checklist](production-checklist.md) before deploying
