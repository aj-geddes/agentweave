---
layout: page
title: Troubleshooting
description: Diagnose and resolve common AgentWeave issues
nav_order: 9
has_children: true
---

# Troubleshooting AgentWeave

This section helps you diagnose and resolve issues when working with AgentWeave. Whether you're encountering identity problems, authorization failures, or connectivity issues, we'll guide you through systematic troubleshooting.

## How to Approach Troubleshooting

AgentWeave's security architecture has multiple layers, so issues can occur at different levels. Follow this systematic approach:

### 1. Identify the Layer

Determine which layer is failing:

```
┌─────────────────────────────────────┐
│ Application Logic                   │  ← Your code
├─────────────────────────────────────┤
│ Authorization (OPA)                 │  ← Policy enforcement
├─────────────────────────────────────┤
│ Transport (mTLS)                    │  ← Network communication
├─────────────────────────────────────┤
│ Identity (SPIFFE)                   │  ← Cryptographic identity
└─────────────────────────────────────┘
```

**Common symptoms by layer:**
- **Identity**: "Cannot connect to SPIRE", "SVID expired"
- **Transport**: "Connection timeout", "TLS handshake failed"
- **Authorization**: "Policy denied request", "OPA connection refused"
- **Application**: Task errors, invalid payloads, business logic issues

### 2. Gather Information

Collect diagnostic data before attempting fixes:

```bash
# Check agent health
curl https://localhost:8443/health

# View agent configuration
agentweave validate config.yaml

# Check identity status
agentweave identity show

# Test authorization
agentweave authz check --caller CALLER_ID --target TARGET_ID --action ACTION

# View logs with timestamps
agentweave logs --follow --timestamps
```

### 3. Check the Basics

Before diving deep, verify fundamentals:

- [ ] Infrastructure running (SPIRE, OPA)
- [ ] Network connectivity
- [ ] Configuration file valid
- [ ] SPIRE registration exists
- [ ] Correct SPIFFE socket path
- [ ] Sufficient permissions

### 4. Enable Debug Logging

Get more detailed information:

```yaml
# config.yaml
observability:
  logging:
    level: "DEBUG"
    format: "json"  # Structured logs for easier parsing
```

### 5. Isolate the Problem

Test components individually:

```bash
# Test SPIRE connectivity
agentweave spire check

# Test OPA connectivity
agentweave opa check

# Test mTLS to target agent
agentweave ping TARGET_SPIFFE_ID

# Validate configuration
agentweave validate config.yaml
```

## Quick Diagnostic Commands

### Check Infrastructure Status

```bash
# SPIRE Server health
docker exec spire-server spire-server healthcheck

# SPIRE Agent health
docker exec spire-agent spire-agent healthcheck

# OPA health
curl http://localhost:8181/health

# List SPIRE entries
docker exec spire-server spire-server entry show
```

### Test Connectivity

```bash
# Test local agent health
curl https://localhost:8443/health

# Test agent-to-agent connectivity
agentweave ping spiffe://example.com/agent/target

# Check agent card discovery
curl https://target-agent:8443/.well-known/agent.json
```

### View Logs

```bash
# Agent logs
agentweave logs --level DEBUG

# SPIRE Server logs
docker logs spire-server --tail 100 --follow

# SPIRE Agent logs
docker logs spire-agent --tail 100 --follow

# OPA logs
docker logs opa --tail 100 --follow
```

## Diagnostic Tools

AgentWeave provides several CLI tools for troubleshooting:

### agentweave validate

Validates configuration files:

```bash
# Validate config
agentweave validate config.yaml

# Validate with environment substitution
agentweave validate config.yaml --env production

# Strict validation (enforce all security requirements)
agentweave validate config.yaml --strict
```

### agentweave identity

Check identity status:

```bash
# Show current identity
agentweave identity show

# Show SVID details
agentweave identity show --verbose

# Test SPIRE connection
agentweave identity test
```

### agentweave authz

Test authorization policies:

```bash
# Check if caller can perform action
agentweave authz check \
  --caller spiffe://example.com/agent/caller \
  --target spiffe://example.com/agent/target \
  --action process_data

# Test with custom input
agentweave authz check --input input.json

# Show policy decision trace
agentweave authz check --trace
```

### agentweave ping

Test connectivity to other agents:

```bash
# Ping an agent
agentweave ping spiffe://example.com/agent/target

# Ping with timeout
agentweave ping spiffe://example.com/agent/target --timeout 5s

# Verbose output
agentweave ping spiffe://example.com/agent/target --verbose
```

### agentweave health

Check overall agent health:

```bash
# Health check
agentweave health

# Detailed health report
agentweave health --verbose

# JSON output for monitoring
agentweave health --format json
```

## Common Issue Categories

### [Identity Issues](identity.md)

Problems with SPIFFE/SPIRE and cryptographic identity:
- Cannot connect to SPIRE agent
- SVID expired or invalid
- Trust domain mismatch
- Registration entry not found

### [Authorization Issues](authorization.md)

Problems with OPA and policy enforcement:
- OPA connection refused
- Policy denied request
- Circuit breaker open
- Policy compilation errors

### [Transport Issues](connections.md)

Problems with mTLS and network connectivity:
- Connection timeout
- TLS handshake failed
- Peer verification failed
- Certificate verification errors

### [Configuration Issues](common-issues.md#configuration-issues)

Problems with configuration files and validation:
- Configuration validation failed
- Required field missing
- Security violations in production
- Invalid YAML syntax

### [A2A Protocol Issues](common-issues.md#a2a-protocol-issues)

Problems with Agent-to-Agent communication:
- Agent not discovered
- Invalid task state
- Malformed requests
- Protocol version mismatch

## Getting Help

If you can't resolve your issue:

### 1. Search Existing Issues

Check if others have encountered the same problem:
- [GitHub Issues](https://github.com/agentweave/agentweave/issues)
- [GitHub Discussions](https://github.com/agentweave/agentweave/discussions)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/agentweave)

### 2. Ask the Community

For questions and discussions:
- [GitHub Discussions](https://github.com/agentweave/agentweave/discussions)
- [Discord Community](https://discord.gg/agentweave)

### 3. Report a Bug

If you've found a bug, please [create an issue](https://github.com/agentweave/agentweave/issues/new) with:
- AgentWeave version (`agentweave --version`)
- Python version
- Operating system
- Configuration (sanitized)
- Full error message and stack trace
- Steps to reproduce
- Expected vs actual behavior

See [Getting Help](support.md) for detailed guidance on reporting issues.

## Troubleshooting Resources

- **[Common Issues](common-issues.md)** - Quick solutions to frequent problems
- **[Debugging Guide](debugging.md)** - Deep-dive debugging techniques
- **[FAQ](faq.md)** - Frequently asked questions
- **[Support](support.md)** - How to get help

## Prevention Best Practices

Avoid common issues by following these practices:

### Development

- **Always validate configs**: Run `agentweave validate` before deploying
- **Use debug logging**: Start with `DEBUG` level logging during development
- **Test policies locally**: Use `agentweave authz check` before deploying policies
- **Monitor SVID expiry**: Set TTL appropriately and monitor rotation

### Production

- **Health checks**: Implement readiness and liveness probes
- **Monitoring**: Set up metrics and alerts (see [Monitoring Guide](../guides/monitoring.md))
- **Log aggregation**: Send logs to centralized logging system
- **Audit trails**: Enable audit logging for security events
- **Graceful degradation**: Handle SPIRE/OPA failures appropriately

### Security

- **Default deny**: Always use `default_action: deny` in production
- **Least privilege**: Grant minimal required permissions
- **Regular rotation**: Use short SVID TTLs (1 hour or less)
- **Trust domain validation**: Verify allowed trust domains
- **TLS 1.3 only**: Enforce modern TLS versions

---

**Next Steps:**
- [Common Issues](common-issues.md) - Quick solutions
- [Debugging Guide](debugging.md) - Deep troubleshooting
- [FAQ](faq.md) - Common questions
