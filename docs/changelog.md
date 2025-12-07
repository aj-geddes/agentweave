---
layout: page
title: Changelog
description: Version history and release notes for AgentWeave SDK
nav_order: 11
---

# Changelog

All notable changes to the AgentWeave SDK will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Versioning Policy

AgentWeave follows [Semantic Versioning](https://semver.org/):

- **MAJOR version** (X.0.0) - Incompatible API changes
- **MINOR version** (0.X.0) - New functionality in a backward-compatible manner
- **PATCH version** (0.0.X) - Backward-compatible bug fixes

### Pre-1.0.0 Development

During pre-1.0.0 development, we follow these conventions:
- **0.X.0** - May include breaking changes
- **0.0.X** - Bug fixes and minor features

---

## [Unreleased]

### Planned Features

Features planned for future releases:

- Support for additional identity providers (AWS IAM, GCP Service Accounts)
- Built-in rate limiting and circuit breaker patterns
- Agent discovery and service mesh integration
- Performance optimizations for high-throughput scenarios
- Enhanced observability with OpenTelemetry auto-instrumentation
- GraphQL transport in addition to gRPC
- WebSocket transport for browser-based agents

---

## [1.0.0] - 2025-01-15

Initial release of AgentWeave SDK - Production ready!

### Added

#### Core Agent Framework
- **SecureAgent class** - Base class for building secure agents with cryptographic identity
- **@capability decorator** - Define agent capabilities with automatic authorization
- **@tool decorator** - Define tools that agents can use
- **AgentContext** - Rich context propagation throughout agent lifecycle
- **Agent lifecycle management** - Startup, shutdown, and health check handling
- **Async-first architecture** - Full async/await support throughout the SDK

#### Identity & Authentication (SPIFFE)
- **SPIFFE identity provider** - Integration with SPIRE for cryptographic workload identity
- **X.509-SVID support** - X.509 certificate-based identity verification
- **JWT-SVID support** - JWT-based identity tokens for certain scenarios
- **Automatic certificate rotation** - Seamless handling of certificate expiration
- **Multiple identity backends** - Support for SPIRE, file-based, and environment-based identities
- **Identity validation** - Comprehensive SPIFFE ID validation and verification

#### Authorization (OPA)
- **OPA authorization provider** - Integration with Open Policy Agent for policy-based authorization
- **Rego policy evaluation** - Execute Rego policies for authorization decisions
- **Built-in authorization policies** - Pre-defined policies for common scenarios
- **Policy bundling** - Package and distribute authorization policies
- **Authorization caching** - Cache authorization decisions for improved performance
- **Default-deny enforcement** - Secure by default with explicit allow policies required in production

#### A2A Protocol
- **JSON-RPC 2.0 implementation** - Standards-compliant A2A protocol
- **Request/response messaging** - Synchronous communication patterns
- **Streaming support** - Server-streaming and bidirectional streaming
- **Error handling** - Comprehensive error codes and error propagation
- **Protocol versioning** - Version negotiation for protocol compatibility
- **Agent Card support** - Discover and validate agent capabilities

#### Transport Layer
- **mTLS transport** - Mutual TLS authentication for all agent-to-agent communication
- **gRPC transport** - High-performance gRPC-based communication
- **HTTP/2 support** - Efficient binary protocol with multiplexing
- **Connection pooling** - Reuse connections for improved performance
- **Automatic retry logic** - Configurable retry strategies with exponential backoff
- **Timeout handling** - Request and connection timeout management
- **Load balancing** - Client-side load balancing across multiple agent instances

#### Configuration
- **YAML-based configuration** - Human-readable configuration files
- **Environment variable support** - Override config values via environment variables
- **Configuration validation** - Comprehensive validation with helpful error messages
- **Schema documentation** - Auto-generated configuration schema
- **Hierarchical configuration** - Support for configuration inheritance and overrides
- **Secret management** - Integration with secret stores (environment, files, external stores)

#### Observability
- **Structured logging** - JSON-structured logs with rich context
- **Prometheus metrics** - Request rates, latencies, error rates, and custom metrics
- **OpenTelemetry tracing** - Distributed tracing across agent interactions
- **Health checks** - Liveness and readiness endpoints
- **Debug endpoints** - Runtime introspection and diagnostics
- **Correlation IDs** - Request tracking across agent boundaries

#### CLI Tools
- **hvs-agent validate** - Validate configuration files
- **hvs-agent serve** - Start an agent server
- **hvs-agent card generate** - Generate Agent Card from configuration
- **hvs-agent card validate** - Validate Agent Card format and signatures
- **hvs-agent authz check** - Test authorization policies
- **hvs-agent identity show** - Display agent's SPIFFE identity
- **hvs-agent call** - Make A2A calls from the command line for testing

#### Testing Utilities
- **MockIdentityProvider** - Mock SPIFFE identity for testing
- **MockAuthzProvider** - Mock OPA authorization for testing
- **TestAgent** - Simplified agent for unit tests
- **Integration test helpers** - Utilities for integration testing with real infrastructure
- **Assertion helpers** - Test assertions for agent behaviors
- **Fixture management** - Test data and configuration fixtures

#### Documentation
- **Comprehensive user guide** - Complete documentation for all features
- **API reference** - Full API documentation with examples
- **Quickstart guide** - Get started in 5 minutes
- **Tutorial series** - Step-by-step tutorials for common scenarios
- **Security guide** - Security best practices and threat model
- **Architecture documentation** - Design principles and architecture decisions
- **Example applications** - Real-world example agents
- **Troubleshooting guide** - Common issues and solutions

#### Deployment
- **Docker support** - Dockerfile and Docker Compose configurations
- **Kubernetes manifests** - YAML manifests for Kubernetes deployment
- **Helm chart** - Production-ready Helm chart with customization options
- **SPIRE integration guides** - Deploy SPIRE alongside agents
- **Multi-cloud deployment guides** - AWS ECS, GCP Cloud Run, Azure Container Apps
- **Security hardening guides** - Production security configurations

### Changed

N/A - Initial release

### Deprecated

N/A - Initial release

### Removed

N/A - Initial release

### Fixed

N/A - Initial release

### Security

- **Mandatory mTLS** - All agent-to-agent communication uses mutual TLS
- **Cryptographic identity** - SPIFFE-based identity cannot be spoofed
- **Policy-based authorization** - OPA policies enforce fine-grained access control
- **No security bypasses** - Security cannot be accidentally or intentionally disabled
- **Secure defaults** - Default-deny authorization in production environments
- **Certificate validation** - Comprehensive X.509 certificate validation
- **Input validation** - All inputs validated before processing
- **Dependency scanning** - Automated vulnerability scanning of dependencies

---

## Upgrade Notes

### Upgrading to 1.0.0

This is the initial release, so there are no upgrade considerations yet.

For future upgrades, this section will include:
- Breaking changes that require code modifications
- Deprecated features that will be removed in future versions
- Configuration changes required
- Data migration steps (if applicable)
- Behavioral changes that may affect your application

### Migration Guides

Migration guides for major version upgrades will be provided here.

---

## Release Process

### Release Schedule

- **Major releases** (X.0.0) - Planned annually, announced 3 months in advance
- **Minor releases** (0.X.0) - Released quarterly with new features
- **Patch releases** (0.0.X) - Released as needed for bug fixes

### Pre-release Versions

We use these pre-release identifiers:
- **alpha** (X.Y.Z-alpha.N) - Early testing, may have bugs and incomplete features
- **beta** (X.Y.Z-beta.N) - Feature complete, undergoing testing
- **rc** (X.Y.Z-rc.N) - Release candidate, ready for production testing

### Support Policy

- **Current major version** - Full support with new features, bug fixes, and security patches
- **Previous major version** - Security patches and critical bug fixes for 12 months
- **Older versions** - No support; please upgrade

### Deprecation Policy

When we deprecate a feature:
1. Mark it as deprecated in the release notes
2. Add deprecation warnings in the code
3. Maintain the feature for at least 2 minor versions
4. Remove in the next major version
5. Provide migration guide for alternatives

---

## How to Read This Changelog

### Change Categories

Changes are grouped into categories:

- **Added** - New features and capabilities
- **Changed** - Changes to existing functionality
- **Deprecated** - Features that will be removed in future versions
- **Removed** - Features that have been removed
- **Fixed** - Bug fixes
- **Security** - Security-related changes and fixes

### Version Links

Each version number links to the GitHub release page with:
- Full release notes
- Binary downloads
- Source code archive
- Docker images

### Issue References

Changes reference GitHub issues where applicable:
- `#123` - Links to issue or pull request
- `@username` - Credits contributor

---

## Contributing

Found a bug? Want to request a feature? Here's how:

1. **Check existing issues** - Search [GitHub Issues](https://github.com/aj-geddes/agentweave/issues)
2. **Create an issue** - Use our issue templates for bugs or features
3. **Submit a PR** - See our [Contributing Guide](contributing/index.md)

### Changelog Contributions

When submitting a PR:
1. Add an entry to the `[Unreleased]` section
2. Use the appropriate category (Added, Changed, etc.)
3. Describe the change from a user's perspective
4. Reference the issue or PR number

Example:
```markdown
### Added
- Support for custom identity providers (#123) @contributor-name
```

---

## Stay Updated

- **Watch releases** - Click "Watch" → "Releases only" on [GitHub](https://github.com/aj-geddes/agentweave)
- **Subscribe to announcements** - Join our [mailing list](https://agentweave.io/newsletter)
- **Follow on Twitter** - [@agentweave](https://twitter.com/agentweave)
- **RSS feed** - Subscribe to our [release feed](https://github.com/aj-geddes/agentweave/releases.atom)

---

## Archive

For a complete list of all releases, see the [Releases page](https://github.com/aj-geddes/agentweave/releases) on GitHub.

---

**Questions?** See our [Contributing Guide](contributing/index.md) or ask in [GitHub Discussions](https://github.com/aj-geddes/agentweave/discussions).
