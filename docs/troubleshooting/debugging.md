---
layout: page
title: Debugging Guide
description: Deep-dive debugging techniques for AgentWeave
nav_order: 2
parent: Troubleshooting
---

# Debugging Guide

This guide covers advanced debugging techniques for diagnosing complex AgentWeave issues. Use these methods when common troubleshooting steps haven't resolved your problem.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Enabling Debug Logging

Debug logging provides detailed information about agent operations.

### Configuration

```yaml
# config.yaml
observability:
  logging:
    level: "DEBUG"              # DEBUG, INFO, WARNING, ERROR
    format: "json"              # json or text
    include_caller: true        # Include file:line
    include_stacktrace: true    # Include stack traces on errors
```

### Environment Variable

```bash
# Override config
export AGENTWEAVE_LOG_LEVEL=DEBUG

# Run agent
agentweave serve config.yaml
```

### Programmatic

```python
import logging
from agentweave import SecureAgent

# Set log level
logging.basicConfig(level=logging.DEBUG)

# Or for specific logger
logging.getLogger("agentweave").setLevel(logging.DEBUG)
```

### Selective Debug Logging

Enable debug only for specific components:

```yaml
observability:
  logging:
    level: "INFO"  # Default level
    loggers:
      "agentweave.identity": "DEBUG"      # Debug identity issues
      "agentweave.authz": "DEBUG"         # Debug authorization
      "agentweave.transport": "INFO"      # Normal transport logging
      "agentweave.a2a": "WARNING"         # Minimal A2A logging
```

---

## Log Analysis

### Understanding Log Structure

JSON logs include structured metadata:

```json
{
  "timestamp": "2025-12-07T10:30:00.123Z",
  "level": "INFO",
  "logger": "agentweave.agent",
  "message": "Request received",
  "agent": "my-agent",
  "caller_spiffe_id": "spiffe://example.com/agent/caller",
  "task_id": "task-123",
  "task_type": "process_data",
  "trace_id": "abc123",
  "span_id": "def456"
}
```

### Filtering Logs

**By level:**
```bash
# Show only errors
agentweave logs --level ERROR

# Show errors and warnings
agentweave logs --level WARNING
```

**By component:**
```bash
# Show only identity logs
agentweave logs --logger agentweave.identity

# Show authorization decisions
agentweave logs --logger agentweave.authz
```

**By trace ID:**
```bash
# Follow a specific request
agentweave logs --trace-id abc123

# Or with jq
agentweave logs --format json | jq 'select(.trace_id == "abc123")'
```

### Common Log Patterns

**Successful request:**
```json
{"level": "INFO", "message": "Request received", "task_id": "task-123"}
{"level": "DEBUG", "message": "Identity verified", "caller": "spiffe://..."}
{"level": "DEBUG", "message": "Authorization allowed", "decision": {"allow": true}}
{"level": "DEBUG", "message": "Executing capability", "capability": "process_data"}
{"level": "INFO", "message": "Request completed", "task_id": "task-123", "duration_ms": 150}
```

**Authorization denied:**
```json
{"level": "INFO", "message": "Request received", "task_id": "task-124"}
{"level": "DEBUG", "message": "Identity verified", "caller": "spiffe://..."}
{"level": "WARNING", "message": "Authorization denied", "decision": {"allow": false, "reason": "no_matching_rule"}}
{"level": "INFO", "message": "Request rejected", "task_id": "task-124", "status": 403}
```

**Identity failure:**
```json
{"level": "ERROR", "message": "Failed to fetch SVID", "error": "Connection refused"}
{"level": "DEBUG", "message": "SPIRE socket path", "path": "/run/spire/sockets/agent.sock"}
{"level": "ERROR", "message": "Identity unavailable", "retry_in_seconds": 5}
```

---

## Using the CLI for Debugging

### agentweave validate

Comprehensive configuration validation:

```bash
# Basic validation
agentweave validate config.yaml

# Strict validation (production rules)
agentweave validate config.yaml --strict

# Show warnings as errors
agentweave validate config.yaml --strict --warnings-as-errors

# Validate with environment substitution
agentweave validate config.yaml --env production

# JSON output for CI/CD
agentweave validate config.yaml --format json
```

**Example output:**
```json
{
  "valid": false,
  "errors": [
    {
      "field": "authorization.default_action",
      "value": "log-only",
      "error": "Production environment requires 'deny'"
    }
  ],
  "warnings": [
    {
      "field": "server.port",
      "value": 8080,
      "warning": "Non-standard port, recommended: 8443"
    }
  ]
}
```

### agentweave authz check

Test authorization policies:

```bash
# Basic check
agentweave authz check \
  --caller spiffe://example.com/agent/caller \
  --target spiffe://example.com/agent/target \
  --action process_data

# With trace output
agentweave authz check \
  --caller spiffe://example.com/agent/caller \
  --target spiffe://example.com/agent/target \
  --action process_data \
  --trace

# With custom input file
agentweave authz check --input input.json --trace

# JSON output
agentweave authz check \
  --caller spiffe://example.com/agent/caller \
  --target spiffe://example.com/agent/target \
  --action process_data \
  --format json
```

**Example trace output:**
```json
{
  "decision": {
    "allow": true,
    "reason": "same_trust_domain"
  },
  "trace": {
    "rules_evaluated": [
      "same_trust_domain",
      "allowlist",
      "capability_grant"
    ],
    "rule_matched": "same_trust_domain",
    "evaluation_time_ms": 5,
    "input": {
      "caller_spiffe_id": "spiffe://example.com/agent/caller",
      "callee_spiffe_id": "spiffe://example.com/agent/target",
      "action": "process_data"
    }
  }
}
```

### agentweave ping

Test connectivity to other agents:

```bash
# Basic ping
agentweave ping spiffe://example.com/agent/target

# With timeout
agentweave ping spiffe://example.com/agent/target --timeout 5s

# Verbose output (shows TLS details)
agentweave ping spiffe://example.com/agent/target --verbose

# Continuous ping
agentweave ping spiffe://example.com/agent/target --count 10 --interval 1s

# JSON output
agentweave ping spiffe://example.com/agent/target --format json
```

**Example verbose output:**
```
PING spiffe://example.com/agent/target
Connected to: https://target-agent.example.com:8443
TLS Version: TLSv1.3
Cipher Suite: TLS_AES_256_GCM_SHA384
Peer SPIFFE ID: spiffe://example.com/agent/target
Peer Certificate Expiry: 2025-12-07T11:30:00Z

Response time: 45ms
Status: 200 OK
```

### agentweave health

Check overall agent health:

```bash
# Basic health check
agentweave health

# Verbose (all subsystems)
agentweave health --verbose

# JSON output
agentweave health --format json

# Specific subsystem
agentweave health --subsystem identity
agentweave health --subsystem authorization
agentweave health --subsystem transport
```

**Example verbose output:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-07T10:30:00Z",
  "subsystems": {
    "identity": {
      "status": "healthy",
      "spiffe_id": "spiffe://example.com/agent/my-agent",
      "svid_expiry": "2025-12-07T11:30:00Z",
      "time_until_expiry_seconds": 3600
    },
    "authorization": {
      "status": "healthy",
      "opa_endpoint": "http://localhost:8181",
      "policy_loaded": true,
      "circuit_breaker": "closed"
    },
    "transport": {
      "status": "healthy",
      "server_running": true,
      "port": 8443,
      "tls_enabled": true
    },
    "server": {
      "status": "healthy",
      "uptime_seconds": 3600,
      "active_tasks": 5
    }
  }
}
```

---

## Inspecting mTLS Connections

### Using OpenSSL

**Connect and view certificate:**
```bash
# Basic connection
openssl s_client -connect target-agent:8443

# Show full certificate chain
openssl s_client -connect target-agent:8443 -showcerts

# Specific TLS version
openssl s_client -connect target-agent:8443 -tls1_3

# With SNI
openssl s_client -connect target-agent:8443 -servername target-agent.example.com
```

**Extract and examine certificate:**
```bash
# Get certificate
echo | openssl s_client -connect target-agent:8443 2>/dev/null | \
  openssl x509 -outform PEM > target-cert.pem

# View certificate details
openssl x509 -in target-cert.pem -text -noout

# Check expiry
openssl x509 -in target-cert.pem -noout -dates

# Extract SPIFFE ID from SAN
openssl x509 -in target-cert.pem -noout -ext subjectAltName
```

### Using cURL

**Test HTTPS endpoint:**
```bash
# Basic request
curl -v https://target-agent:8443/health

# With client certificate (mTLS)
curl -v https://target-agent:8443/health \
  --cert client-cert.pem \
  --key client-key.pem \
  --cacert ca-bundle.pem

# Show TLS handshake details
curl -v https://target-agent:8443/health 2>&1 | grep -E "(TLS|SSL|certificate)"
```

### Debugging TLS Issues

**Common TLS errors:**

**Error: "certificate signed by unknown authority"**
```bash
# Check CA bundle
openssl verify -CAfile ca-bundle.pem agent-cert.pem

# Add SPIRE's CA to bundle
cat /path/to/spire-ca.pem >> ca-bundle.pem
```

**Error: "tls: protocol version not supported"**
```yaml
# Check both agents support same TLS version
transport:
  tls_min_version: "1.3"  # Must match on both sides
  tls_max_version: "1.3"
```

**Error: "tls: no cipher suites supported"**
```bash
# Check supported ciphers
nmap --script ssl-enum-ciphers -p 8443 target-agent

# Ensure compatible cipher suites
```

---

## Testing OPA Policies

### Interactive Policy Testing

**Using OPA CLI:**
```bash
# Test policy with input
opa eval -d authz.rego \
  -i input.json \
  'data.agentweave.authz.allow'

# With explanation
opa eval -d authz.rego \
  -i input.json \
  --explain full \
  'data.agentweave.authz.allow'
```

**Using OPA Server:**
```bash
# Load policy
curl -X PUT http://localhost:8181/v1/policies/authz \
  --data-binary @authz.rego

# Test decision
curl -X POST http://localhost:8181/v1/data/agentweave/authz/allow \
  -H "Content-Type: application/json" \
  -d @input.json | jq

# With explanation
curl -X POST http://localhost:8181/v1/data/agentweave/authz/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "caller_spiffe_id": "spiffe://example.com/agent/caller",
      "callee_spiffe_id": "spiffe://example.com/agent/target",
      "action": "process_data"
    },
    "explain": "full"
  }' | jq
```

### Policy Unit Tests

**Create test file (authz_test.rego):**
```rego
package agentweave.authz

import rego.v1

# Test same trust domain allows
test_same_trust_domain_allowed if {
    allow with input as {
        "caller_spiffe_id": "spiffe://example.com/agent/a",
        "callee_spiffe_id": "spiffe://example.com/agent/b",
        "action": "test"
    }
}

# Test different trust domain denies
test_different_trust_domain_denied if {
    not allow with input as {
        "caller_spiffe_id": "spiffe://evil.com/agent/attacker",
        "callee_spiffe_id": "spiffe://example.com/agent/b",
        "action": "test"
    }
}

# Test allowlist works
test_allowlist_allowed if {
    allow with input as {
        "caller_spiffe_id": "spiffe://example.com/agent/allowed",
        "callee_spiffe_id": "spiffe://example.com/agent/target",
        "action": "test"
    } with data.allowed_callers as {
        "spiffe://example.com/agent/target": [
            "spiffe://example.com/agent/allowed"
        ]
    }
}
```

**Run tests:**
```bash
# Run all tests
opa test . -v

# Run specific test
opa test . -v -r test_same_trust_domain_allowed

# With coverage
opa test . -v --coverage
```

### Debugging Policy Decisions

**Enable OPA decision logging:**
```yaml
# opa-config.yaml
decision_logs:
  console: true

services:
  console_logger:
    url: http://logger:8080

plugins:
  decision_logs:
    service: console_logger
```

**Query decision logs:**
```bash
# View recent decisions
curl http://localhost:8181/v1/data/system/decisions | jq

# Filter by input
curl http://localhost:8181/v1/data/system/decisions | \
  jq '.result[] | select(.input.caller_spiffe_id == "spiffe://example.com/agent/caller")'
```

---

## Network Debugging

### DNS Resolution

```bash
# Check DNS
nslookup target-agent

# Using dig
dig target-agent

# Using host
host target-agent

# Check all DNS records
dig target-agent ANY
```

### Port Connectivity

```bash
# Check port is open
nc -zv target-agent 8443

# Or using telnet
telnet target-agent 8443

# Check with timeout
timeout 5 bash -c '</dev/tcp/target-agent/8443' && echo "Port open" || echo "Port closed"
```

### Network Path

```bash
# Trace route
traceroute target-agent

# TCP trace route
tcptraceroute target-agent 8443

# MTU path discovery
ping -M do -s 1472 target-agent
```

### Packet Capture

**Using tcpdump:**
```bash
# Capture traffic to/from agent
sudo tcpdump -i any -w capture.pcap port 8443

# Capture with filter
sudo tcpdump -i any -w capture.pcap \
  'host target-agent and port 8443'

# Real-time view
sudo tcpdump -i any -A port 8443
```

**Analyze with Wireshark:**
```bash
# Install Wireshark
# Open capture.pcap
# Filter: tcp.port == 8443 && ssl

# Look for:
# - TLS handshake completion
# - Certificate exchange
# - Application data
```

### Firewall Rules

**Kubernetes Network Policies:**
```bash
# List network policies
kubectl get networkpolicy

# Describe policy
kubectl describe networkpolicy agent-netpol

# Test connectivity from pod
kubectl run -it --rm debug \
  --image=nicolaka/netshoot \
  --restart=Never \
  -- curl https://target-agent:8443/health
```

**Cloud Firewalls:**
```bash
# AWS Security Groups
aws ec2 describe-security-groups --group-ids sg-xxx

# GCP Firewall Rules
gcloud compute firewall-rules list

# Azure Network Security Groups
az network nsg rule list --resource-group rg --nsg-name nsg
```

---

## Common Debugging Patterns

### Pattern 1: Identity Issues

**Step-by-step debugging:**

```bash
# 1. Check SPIRE agent is running
docker ps | grep spire-agent
# OR
systemctl status spire-agent

# 2. Verify socket exists and is accessible
ls -l /run/spire/sockets/agent.sock

# 3. Test SPIRE Workload API
agentweave identity show --verbose

# 4. Check SPIRE registration
docker exec spire-server spire-server entry show \
  -spiffeID spiffe://example.com/agent/my-agent

# 5. View SPIRE agent logs
docker logs spire-agent --tail 50

# 6. Test SVID fetch
agentweave identity test
```

### Pattern 2: Authorization Issues

**Step-by-step debugging:**

```bash
# 1. Check OPA is running
curl http://localhost:8181/health

# 2. Verify policy is loaded
curl http://localhost:8181/v1/policies

# 3. Check policy data
curl http://localhost:8181/v1/data

# 4. Test specific decision
agentweave authz check \
  --caller spiffe://example.com/agent/caller \
  --target spiffe://example.com/agent/target \
  --action process_data \
  --trace

# 5. View OPA logs
docker logs opa --tail 50

# 6. Test policy directly
curl -X POST http://localhost:8181/v1/data/agentweave/authz/allow \
  -d @input.json \
  --write-out '\n%{http_code}\n'
```

### Pattern 3: Connectivity Issues

**Step-by-step debugging:**

```bash
# 1. Verify target agent is running
curl https://target-agent:8443/health

# 2. Check DNS resolution
nslookup target-agent

# 3. Test port connectivity
nc -zv target-agent 8443

# 4. Test TLS handshake
openssl s_client -connect target-agent:8443

# 5. Ping agent (mTLS)
agentweave ping spiffe://example.com/agent/target --verbose

# 6. Check network policies
kubectl get networkpolicy
```

---

## When to Check What

### Agent Won't Start

1. Check configuration validity: `agentweave validate config.yaml`
2. Verify SPIRE connectivity: `agentweave identity test`
3. Check port availability: `nc -zv localhost 8443`
4. Review startup logs: `agentweave serve config.yaml --log-level DEBUG`

### Agent Can't Call Another Agent

1. Verify target agent is running: `curl https://target:8443/health`
2. Test connectivity: `agentweave ping spiffe://example.com/agent/target`
3. Check authorization: `agentweave authz check ...`
4. Inspect mTLS: `openssl s_client -connect target:8443`

### Authorization Always Denies

1. Check OPA is running: `curl http://localhost:8181/health`
2. Verify policy loaded: `curl http://localhost:8181/v1/policies`
3. Test policy: `agentweave authz check --trace`
4. Review policy data: `curl http://localhost:8181/v1/data`

### SVID Issues

1. Check SPIRE agent: `agentweave identity show`
2. Verify registration: `docker exec spire-server spire-server entry show`
3. Check expiry: `agentweave identity show --verbose`
4. Test SPIRE connection: `agentweave identity test`

---

## Advanced Debugging

### Distributed Tracing

Enable OpenTelemetry tracing:

```yaml
observability:
  tracing:
    enabled: true
    exporter: "otlp"
    endpoint: "http://jaeger:4317"
```

View traces in Jaeger:
```bash
# Open Jaeger UI
open http://localhost:16686

# Search for traces by:
# - Service: my-agent
# - Operation: process_data
# - Tags: caller_spiffe_id
```

### Memory Profiling

```python
# Add to agent
import tracemalloc

class MyAgent(SecureAgent):
    async def on_start(self):
        tracemalloc.start()

    async def on_stop(self):
        snapshot = tracemalloc.take_snapshot()
        top_stats = snapshot.statistics('lineno')
        for stat in top_stats[:10]:
            print(stat)
```

### CPU Profiling

```bash
# Install py-spy
pip install py-spy

# Profile running agent
py-spy top --pid $(pgrep -f agentweave)

# Record profile
py-spy record -o profile.svg --pid $(pgrep -f agentweave)
```

---

## Next Steps

- **[Common Issues](common-issues.md)** - Quick solutions
- **[FAQ](faq.md)** - Common questions
- **[Support](support.md)** - Get help
