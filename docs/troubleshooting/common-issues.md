---
layout: page
title: Common Issues
description: Quick solutions to frequently encountered problems
nav_order: 1
parent: Troubleshooting
---

# Common Issues and Solutions

This page provides quick solutions to the most frequently encountered AgentWeave issues, organized by category.

## Identity Issues

### Cannot connect to SPIRE agent

**Symptoms:**
```
ERROR: Failed to connect to SPIRE agent
ConnectionRefusedError: [Errno 111] Connection refused
```

**Causes:**
1. SPIRE agent not running
2. Incorrect socket path
3. Permission issues

**Solutions:**

**Check if SPIRE agent is running:**
```bash
# Docker
docker ps | grep spire-agent

# Kubernetes
kubectl get pods -n spire-system -l app=spire-agent

# Systemd
systemctl status spire-agent
```

**Verify socket path:**
```bash
# Check socket exists
ls -l /run/spire/sockets/agent.sock

# Check environment variable
echo $SPIFFE_ENDPOINT_SOCKET

# Should be: unix:///run/spire/sockets/agent.sock
```

**Fix permissions:**
```bash
# Socket should be accessible by your user
sudo chmod 666 /run/spire/sockets/agent.sock

# Or run agent with correct user
docker run --user $(id -u):$(id -g) ...
```

**Configuration fix:**
```yaml
# config.yaml
identity:
  provider: "spiffe"
  spiffe_socket: "unix:///run/spire/sockets/agent.sock"  # Correct path
```

---

### SVID expired

**Symptoms:**
```
ERROR: SVID has expired
ERROR: Certificate expired at 2025-12-07T09:00:00Z
```

**Why it happens:**
- SVID TTL elapsed without rotation
- Agent couldn't reach SPIRE for renewal
- Network issues during rotation

**Solutions:**

**Immediate fix (restart agent):**
```bash
# Agent will fetch fresh SVID on startup
agentweave serve config.yaml
```

**Check SVID status:**
```bash
# View current SVID expiry
agentweave identity show --verbose

# Check SPIRE registration TTL
docker exec spire-server spire-server entry show \
  -spiffeID spiffe://example.com/agent/my-agent
```

**Adjust TTL for more frequent rotation:**
```bash
# Update registration with shorter TTL (1 hour)
docker exec spire-server spire-server entry update \
  -spiffeID spiffe://example.com/agent/my-agent \
  -ttl 3600
```

**Monitor rotation:**
```python
# Add rotation monitoring
class MyAgent(SecureAgent):
    async def on_svid_update(self, new_svid):
        self.logger.info(
            f"SVID rotated successfully",
            extra={
                "expiry": new_svid.expiry.isoformat(),
                "time_until_expiry": (new_svid.expiry - datetime.now()).total_seconds()
            }
        )
```

---

### Trust domain not found

**Symptoms:**
```
ERROR: Trust domain 'partner.example.com' not in allowed list
ERROR: No trust bundle found for domain
```

**Causes:**
1. Missing federation configuration
2. Trust domain not in allowed list
3. Trust bundle not loaded

**Solutions:**

**Add to allowed trust domains:**
```yaml
# config.yaml
identity:
  allowed_trust_domains:
    - "example.com"           # Your domain
    - "partner.example.com"   # Federated domain
```

**Set up federation (SPIRE Server):**
```bash
# Fetch partner's trust bundle
spire-server bundle show \
  -format spiffe \
  -trustDomain partner.example.com \
  -endpointURL https://spire.partner.example.com:8443

# Set federated bundle
spire-server bundle set \
  -format spiffe \
  -id spiffe://partner.example.com \
  -path partner-bundle.pem

# Verify
spire-server bundle list
```

**Check federation status:**
```bash
# List all trust bundles
docker exec spire-server spire-server bundle list

# Should show both domains:
# - spiffe://example.com
# - spiffe://partner.example.com
```

---

### Certificate verification failed

**Symptoms:**
```
ERROR: Certificate verification failed
ERROR: x509: certificate signed by unknown authority
```

**Causes:**
1. mTLS configuration issue
2. Trust bundle mismatch
3. Self-signed certificates not trusted

**Solutions:**

**Check trust bundle:**
```bash
# Verify agent has correct trust bundle
agentweave identity show --verbose

# Check SPIRE bundle
docker exec spire-server spire-server bundle show
```

**For development (self-signed certs):**
```yaml
# config.yaml - DEVELOPMENT ONLY
transport:
  tls_verify: false  # NEVER use in production
```

**For production:**
```yaml
# config.yaml
transport:
  tls_verify: true
  ca_cert_path: "/etc/ssl/certs/ca-bundle.crt"
```

**Verify certificate chain:**
```bash
# Check certificate
openssl s_client -connect target-agent:8443 -showcerts

# Verify against CA
openssl verify -CAfile ca-bundle.crt agent-cert.pem
```

---

## Authorization Issues

### OPA connection refused

**Symptoms:**
```
ERROR: Failed to connect to OPA
ConnectionError: http://localhost:8181: Connection refused
```

**Causes:**
1. OPA not running
2. Wrong endpoint
3. Network policy blocking access

**Solutions:**

**Check OPA status:**
```bash
# Docker
docker ps | grep opa

# Kubernetes
kubectl get pods -l app=opa

# Health check
curl http://localhost:8181/health
```

**Start OPA:**
```bash
# Docker
docker run -d -p 8181:8181 openpolicyagent/opa:latest \
  run --server --addr :8181

# Kubernetes
kubectl apply -f opa-deployment.yaml
```

**Fix endpoint:**
```yaml
# config.yaml
authorization:
  provider: "opa"
  opa_endpoint: "http://localhost:8181"  # Correct endpoint

  # For Kubernetes sidecar:
  # opa_endpoint: "http://localhost:8181"

  # For remote OPA:
  # opa_endpoint: "http://opa.example.com:8181"
```

**Test connectivity:**
```bash
# Test OPA endpoint
agentweave opa check

# Manual test
curl http://localhost:8181/v1/data/agentweave/authz/allow \
  -H "Content-Type: application/json" \
  -d '{"input": {}}'
```

---

### Policy denied request

**Symptoms:**
```
ERROR: Authorization denied
INFO: OPA decision: {"allow": false, "reason": "no_matching_rule"}
```

**Causes:**
1. No policy rule matches
2. Default deny in effect
3. Incorrect policy data

**How to debug:**

**Check policy decision:**
```bash
# Test specific authorization
agentweave authz check \
  --caller spiffe://example.com/agent/caller \
  --target spiffe://example.com/agent/target \
  --action process_data \
  --trace
```

**View policy trace:**
```bash
# Get detailed trace
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

**Common fixes:**

**Add allowlist entry:**
```json
// data.json
{
  "allowed_callers": {
    "spiffe://example.com/agent/target": [
      "spiffe://example.com/agent/caller"
    ]
  }
}
```

**Grant capability:**
```json
// data.json
{
  "capabilities": {
    "spiffe://example.com/agent/caller": [
      "process_data",
      "query"
    ]
  }
}
```

**Update and reload policy:**
```bash
# Load updated data
curl -X PUT http://localhost:8181/v1/data \
  -H "Content-Type: application/json" \
  -d @data.json

# Verify
curl http://localhost:8181/v1/data/allowed_callers | jq
```

---

### Circuit breaker open

**Symptoms:**
```
ERROR: Authorization circuit breaker open
INFO: Too many OPA failures, circuit breaker activated
```

**Causes:**
1. OPA overloaded
2. OPA repeatedly failing
3. Network issues to OPA

**Solutions:**

**Check OPA health:**
```bash
# OPA status
curl http://localhost:8181/health

# OPA metrics
curl http://localhost:8181/metrics
```

**Adjust circuit breaker settings:**
```yaml
# config.yaml
authorization:
  circuit_breaker:
    failure_threshold: 5      # Open after 5 failures
    success_threshold: 2      # Close after 2 successes
    timeout: 30              # Try again after 30s
```

**Scale OPA (Kubernetes):**
```bash
# Increase replicas
kubectl scale deployment opa --replicas=3

# Or use HPA
kubectl autoscale deployment opa --min=2 --max=10 --cpu-percent=80
```

**Temporary workaround (development only):**
```yaml
# config.yaml - DEVELOPMENT ONLY
authorization:
  default_action: "log-only"  # Don't block on OPA failure
```

---

## Transport Issues

### Connection timeout

**Symptoms:**
```
ERROR: Connection timeout to target agent
TimeoutError: Request timed out after 30s
```

**Causes:**
1. Network unreachable
2. Firewall blocking traffic
3. Target agent not running
4. DNS resolution failure

**Solutions:**

**Check target agent:**
```bash
# Test connectivity
agentweave ping spiffe://example.com/agent/target

# Check if agent is running
curl https://target-agent:8443/health
```

**Test network connectivity:**
```bash
# DNS resolution
nslookup target-agent

# Port reachable
nc -zv target-agent 8443

# Or using telnet
telnet target-agent 8443
```

**Check firewall rules:**
```bash
# Kubernetes Network Policy
kubectl get networkpolicy

# Cloud firewall (example: AWS)
aws ec2 describe-security-groups --group-ids sg-xxx
```

**Adjust timeout:**
```yaml
# config.yaml
transport:
  timeout: 60  # Increase to 60 seconds
  connect_timeout: 10
```

---

### TLS handshake failed

**Symptoms:**
```
ERROR: TLS handshake failed
ssl.SSLError: [SSL: TLSV1_ALERT_UNKNOWN_CA] tlsv1 alert unknown ca
```

**Causes:**
1. TLS version mismatch
2. Cipher suite incompatibility
3. Certificate issues

**Solutions:**

**Check TLS configuration:**
```yaml
# config.yaml
transport:
  tls_min_version: "1.3"       # Both agents must match
  tls_max_version: "1.3"
  cipher_suites:                # Compatible suites
    - "TLS_AES_256_GCM_SHA384"
    - "TLS_AES_128_GCM_SHA256"
```

**Debug TLS connection:**
```bash
# Test TLS handshake
openssl s_client -connect target-agent:8443 \
  -tls1_3 \
  -showcerts

# Check supported ciphers
nmap --script ssl-enum-ciphers -p 8443 target-agent
```

**Verify certificates:**
```bash
# Check certificate validity
echo | openssl s_client -connect target-agent:8443 2>&1 | \
  openssl x509 -noout -dates

# Check certificate details
agentweave identity show --verbose
```

---

### Peer verification failed

**Symptoms:**
```
ERROR: Peer verification failed
ERROR: SPIFFE ID mismatch: expected 'spiffe://example.com/agent/target', got 'spiffe://example.com/agent/other'
```

**Causes:**
1. SPIFFE ID mismatch
2. Wrong agent responding
3. Load balancer routing issue

**Solutions:**

**Check target SPIFFE ID:**
```bash
# Get agent's actual SPIFFE ID
curl https://target-agent:8443/.well-known/agent.json | jq '.extensions.spiffe_id'
```

**Use correct SPIFFE ID:**
```python
# Call with correct ID
result = await agent.call_agent(
    target="spiffe://example.com/agent/actual-id",  # Use actual ID
    task_type="process",
    payload={"data": "..."}
)
```

**Check DNS/Load Balancer:**
```bash
# Ensure DNS points to correct agent
nslookup target-agent

# Check if load balancer is routing correctly
# (multiple calls should hit same agent for SPIFFE consistency)
for i in {1..5}; do
  curl https://target-agent:8443/.well-known/agent.json | jq '.extensions.spiffe_id'
done
```

---

## Configuration Issues

### Configuration validation failed

**Symptoms:**
```
ERROR: Configuration validation failed
ERROR: Missing required field: agent.name
```

**Common validation errors:**

**Missing required fields:**
```yaml
# WRONG
agent:
  description: "My agent"

# CORRECT
agent:
  name: "my-agent"           # Required
  trust_domain: "example.com" # Required
  description: "My agent"
```

**Invalid values:**
```yaml
# WRONG
server:
  port: "8443"  # String instead of int

# CORRECT
server:
  port: 8443  # Integer
```

**Validate before running:**
```bash
# Validate configuration
agentweave validate config.yaml

# Strict validation (production rules)
agentweave validate config.yaml --strict

# With environment substitution
agentweave validate config.yaml --env production
```

---

### Required field missing

**Symptoms:**
```
ERROR: Missing required configuration field
ERROR: 'agent.name' is required
```

**Required fields:**

```yaml
# Minimum required configuration
agent:
  name: "my-agent"                    # Required
  trust_domain: "example.com"         # Required
  capabilities: []                    # Required (can be empty)

identity:
  provider: "spiffe"                  # Required

authorization:
  provider: "opa"                     # Required
  opa_endpoint: "http://localhost:8181"  # Required

server:
  port: 8443                          # Required
```

**Check what's required:**
```bash
# Generate sample config with all required fields
agentweave init --template minimal > config.yaml

# Or full config with all options
agentweave init --template full > config.yaml
```

---

### Security violation in production

**Symptoms:**
```
ERROR: Security violation: 'log-only' mode not allowed in production
ERROR: Configuration not secure for production environment
```

**Production requirements:**

```yaml
# DEVELOPMENT config (NOT allowed in production)
authorization:
  default_action: "log-only"  # ❌ Not allowed

transport:
  tls_verify: false           # ❌ Not allowed

# PRODUCTION config (required)
authorization:
  default_action: "deny"      # ✓ Required

transport:
  tls_verify: true           # ✓ Required
  tls_min_version: "1.3"     # ✓ Required
```

**Environment detection:**
```yaml
# Use environment variable
authorization:
  default_action: "${AUTHZ_DEFAULT_ACTION:-deny}"

# Or separate configs
# config.dev.yaml - for development
# config.prod.yaml - for production
```

**Enforce production mode:**
```bash
# Set environment
export AGENTWEAVE_ENV=production

# Or use flag
agentweave serve config.yaml --env production
```

---

## A2A Protocol Issues

### Agent not discovered

**Symptoms:**
```
ERROR: Agent not found
ERROR: Failed to discover agent at spiffe://example.com/agent/target
```

**Causes:**
1. Agent not running
2. Agent card not accessible
3. Network/DNS issue
4. SPIFFE ID incorrect

**Solutions:**

**Check agent is running:**
```bash
# Health check
curl https://target-agent:8443/health

# Agent card (discovery endpoint)
curl https://target-agent:8443/.well-known/agent.json
```

**Verify SPIFFE ID:**
```bash
# Get agent's actual SPIFFE ID
curl https://target-agent:8443/.well-known/agent.json | \
  jq '.extensions.spiffe_id'
```

**Check DNS resolution:**
```bash
# Resolve hostname
nslookup target-agent

# Or use SPIFFE ID directly
# The SDK can resolve SPIFFE IDs via SPIRE
```

**Use discovery:**
```python
# Automatic discovery
agent = await agent.discover_agent("spiffe://example.com/agent/target")

# Manual endpoint
result = await agent.call_agent(
    target="spiffe://example.com/agent/target",
    endpoint="https://target-agent:8443",  # Explicit endpoint
    task_type="process"
)
```

---

### Invalid task state

**Symptoms:**
```
ERROR: Invalid task state transition
ERROR: Cannot transition from 'completed' to 'running'
```

**Causes:**
1. Task already completed
2. Concurrent task updates
3. Client retry on completed task

**Solution:**

**Check task status before retrying:**
```python
# Get task status
task_id = "task-123"
status = await agent.get_task_status(task_id)

if status.state == "completed":
    # Don't retry, get result
    result = status.artifacts
elif status.state == "failed":
    # Can retry failed task
    result = await agent.retry_task(task_id)
```

**Use idempotency:**
```python
# Use idempotency key
result = await agent.call_agent(
    target="spiffe://example.com/agent/target",
    task_type="process",
    payload={"data": "..."},
    idempotency_key="unique-key-123"  # Same key = same task
)
```

---

## Performance Issues

### Slow agent responses

**Check:**
1. OPA policy complexity
2. SVID rotation during request
3. Network latency
4. Target agent overloaded

**Solutions:**

**Profile OPA policies:**
```bash
# Benchmark policy
curl -X POST http://localhost:8181/v1/data/agentweave/authz/allow \
  -H "Content-Type: application/json" \
  -d @input.json \
  --write-out '\nTime: %{time_total}s\n'
```

**Add timeouts:**
```yaml
transport:
  timeout: 30
  connect_timeout: 5
```

**Monitor metrics:**
```python
# Check agent metrics
curl http://localhost:9090/metrics | grep agentweave_
```

---

## Next Steps

- **[Debugging Guide](debugging.md)** - Deep troubleshooting techniques
- **[FAQ](faq.md)** - Common questions
- **[Getting Help](support.md)** - Report issues
