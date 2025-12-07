---
layout: page
title: Best Practices
description: Security best practices for deploying and operating AgentWeave SDK agents
permalink: /security/best-practices/
parent: Security
nav_order: 2
---

# Security Best Practices

This guide provides operational security recommendations for building, deploying, and running production AgentWeave agents securely.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Identity Management

### Use SPIFFE/SPIRE in Production

**Never use mock identity in production.**

```yaml
# ❌ BAD - Mock identity for production
identity:
  provider: "mock"
  spiffe_id: "spiffe://example.com/agent/my-agent"

# ✅ GOOD - SPIRE for production
identity:
  provider: "spire"
  socket_path: "/run/spire/sockets/agent.sock"
  allowed_trust_domains:
    - "example.com"
```

Mock identity should only be used for:
- Local development
- Unit testing
- Integration testing in CI

### Register Unique SPIFFE IDs per Agent

Each agent instance should have a unique, descriptive SPIFFE ID:

```bash
# ✅ GOOD - Specific IDs
spiffe://example.com/agent/data-processor/production
spiffe://example.com/agent/api-gateway/staging
spiffe://example.com/agent/orchestrator/dev

# ❌ BAD - Generic IDs
spiffe://example.com/agent
spiffe://example.com/service
```

**SPIFFE ID Best Practices:**
- Include environment (production, staging, dev)
- Include functional role (data-processor, orchestrator)
- Use hierarchical structure: `/agent/<role>/<env>`
- Document your SPIFFE ID naming convention

### Rotate SVIDs Regularly

Configure short TTL for SVIDs:

```bash
# ✅ GOOD - 1 hour TTL
spire-server entry create \
  -spiffeID spiffe://example.com/agent/data-processor/prod \
  -parentID spiffe://example.com/k8s-node \
  -selector k8s:ns:agentweave \
  -selector k8s:sa:data-processor \
  -ttl 3600  # 1 hour

# ⚠️ ACCEPTABLE - 4 hours for testing
-ttl 14400

# ❌ BAD - 1 day
-ttl 86400
```

**SVID TTL Recommendations:**
- **Production**: 1 hour (3600 seconds)
- **Staging**: 2-4 hours
- **Development**: 4-8 hours
- **Testing**: Can be longer for convenience

SPIRE automatically rotates at 50% of TTL (30 minutes for 1-hour TTL).

### Validate Trust Domains

Explicitly configure allowed trust domains:

```yaml
# ✅ GOOD - Explicit allowlist
identity:
  allowed_trust_domains:
    - "example.com"                    # Own domain
    - "partner.trusted-org.com"        # Federated partner
    - "vendor.external-service.io"     # Trusted vendor

# ❌ BAD - Wildcard trust
identity:
  allowed_trust_domains:
    - "*"  # Never do this!
```

### Monitor SVID Health

Set up monitoring for SVID rotation:

```python
class MyAgent(SecureAgent):
    async def on_svid_update(self, new_svid):
        """Called when SVID rotates."""
        self.logger.info(
            "SVID rotated successfully",
            extra={
                "spiffe_id": new_svid.spiffe_id,
                "expiry": new_svid.expiry,
                "ttl_seconds": new_svid.ttl,
            }
        )

        # Alert if TTL is shorter than expected
        if new_svid.ttl < 3600:
            self.logger.warning(
                "SVID TTL is shorter than expected",
                extra={"ttl": new_svid.ttl}
            )
```

**Prometheus Metrics:**
```yaml
# Alert on rotation failures
- alert: SVIDRotationFailed
  expr: agentweave_svid_rotation_errors_total > 0
  annotations:
    summary: "SVID rotation failed for {{ $labels.agent }}"

# Alert on expiring SVIDs
- alert: SVIDNearExpiry
  expr: agentweave_svid_ttl_seconds < 300
  annotations:
    summary: "SVID expires in less than 5 minutes"
```

---

## Authorization Policies

### Default Deny

Always use default deny authorization:

```rego
# ✅ GOOD - Default deny
package agentweave.authz

import rego.v1

default allow := false

# Explicit rules required for access
allow if {
    # ... specific allow conditions
}
```

```rego
# ❌ BAD - Default allow
default allow := true

# This is dangerous!
```

**In agent configuration:**

```yaml
# ✅ GOOD
authorization:
  default_action: "deny"

# ❌ BAD
authorization:
  default_action: "allow"
```

### Principle of Least Privilege

Grant minimal permissions necessary:

```rego
# ✅ GOOD - Specific capabilities
allow if {
    input.caller_spiffe_id == "spiffe://example.com/agent/api-gateway"
    input.callee_spiffe_id == "spiffe://example.com/agent/data-processor"
    input.action in ["query", "health_check"]  # Only what's needed
}

# ❌ BAD - Overly permissive
allow if {
    input.caller_spiffe_id == "spiffe://example.com/agent/api-gateway"
    # Grants access to ALL capabilities
}
```

### Regular Policy Audits

Schedule policy reviews:

```bash
# Export current policies
curl -X GET http://localhost:8181/v1/policies > policies-$(date +%Y%m%d).json

# Review who can call what
curl -X POST http://localhost:8181/v1/data/agentweave/authz/allow \
  -d @test-cases.json

# Use OPA test framework
opa test policies/ -v
```

**Quarterly Review Checklist:**
- [ ] Review all allowlist entries
- [ ] Check for overly broad permissions
- [ ] Remove stale/unused entries
- [ ] Verify federated trust is still needed
- [ ] Test deny cases still work
- [ ] Update documentation

### Test Policies Thoroughly

Use OPA's test framework:

```rego
# policies/authz_test.rego
package agentweave.authz

# Test allowed access
test_api_gateway_can_query {
    allow with input as {
        "caller_spiffe_id": "spiffe://example.com/agent/api-gateway",
        "callee_spiffe_id": "spiffe://example.com/agent/data-processor",
        "action": "query"
    }
}

# Test denied access
test_unknown_caller_denied {
    not allow with input as {
        "caller_spiffe_id": "spiffe://example.com/agent/unknown",
        "callee_spiffe_id": "spiffe://example.com/agent/data-processor",
        "action": "query"
    }
}

# Test default deny
test_no_policy_denies {
    not allow with input as {
        "caller_spiffe_id": "spiffe://example.com/agent/new-agent",
        "callee_spiffe_id": "spiffe://example.com/agent/new-service",
        "action": "new_action"
    }
}
```

Run tests in CI/CD:

```bash
# Run all policy tests
opa test policies/ -v

# Check coverage (aim for 100%)
opa test policies/ --coverage

# Fail CI if tests fail
opa test policies/ || exit 1
```

### Separate Policy from Code

Store policies in version control separately:

```
project/
├── agents/
│   ├── data-processor/
│   └── orchestrator/
└── policies/
    ├── authz.rego
    ├── authz_test.rego
    └── data.json
```

Use OPA bundles for distribution:

```yaml
# OPA config
services:
  bundle-server:
    url: https://policy-server.example.com

bundles:
  authz:
    service: bundle-server
    resource: bundles/agentweave-authz.tar.gz
    polling:
      min_delay_seconds: 30
      max_delay_seconds: 60
```

---

## Transport Security

### Enforce TLS 1.3 Minimum

```yaml
# ✅ GOOD - TLS 1.3 only
transport:
  tls_min_version: "1.3"

# ⚠️ ACCEPTABLE for legacy compatibility
transport:
  tls_min_version: "1.2"

# ❌ BAD - TLS 1.1 is deprecated
transport:
  tls_min_version: "1.1"
```

### Enable Strict Peer Verification

```yaml
# ✅ GOOD - Verify peer identity
transport:
  verify_peer: true
  require_client_cert: true

# ❌ BAD - Skip verification
transport:
  verify_peer: false  # Never do this!
```

### Configure Proper Cipher Suites

For TLS 1.3 (recommended):

```yaml
transport:
  tls_min_version: "1.3"
  # TLS 1.3 cipher suites are secure by default
  cipher_suites:
    - "TLS_AES_256_GCM_SHA384"
    - "TLS_AES_128_GCM_SHA256"
    - "TLS_CHACHA20_POLY1305_SHA256"
```

For TLS 1.2 (if required):

```yaml
transport:
  tls_min_version: "1.2"
  cipher_suites:
    - "TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384"
    - "TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256"
    - "TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384"
    - "TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256"
```

### Certificate Pinning Considerations

For high-security environments, consider trust bundle pinning:

```python
class MyAgent(SecureAgent):
    async def validate_peer_svid(self, peer_svid):
        """Additional validation beyond standard checks."""
        # Validate trust bundle fingerprint
        expected_bundle_hash = "sha256:abcd1234..."
        if peer_svid.bundle_hash != expected_bundle_hash:
            raise SecurityError("Trust bundle mismatch")

        # Validate SPIFFE ID matches expected pattern
        if not peer_svid.spiffe_id.startswith("spiffe://example.com/"):
            raise SecurityError("Unexpected trust domain")
```

---

## Configuration Security

### Never Disable Security Checks

AgentWeave does not allow disabling security:

```yaml
# ❌ These options don't exist (by design)
security:
  enabled: false  # Not possible
  skip_authz: true  # Not possible
  disable_tls: true  # Not possible
```

If you need to test without full security, use mock mode:

```yaml
# ✅ GOOD - Explicit mock mode for testing
identity:
  provider: "mock"  # Clearly mock, not "disabled security"
```

### Environment-Specific Configurations

Separate configs by environment:

```
configs/
├── base.yaml           # Shared settings
├── development.yaml    # Dev overrides
├── staging.yaml        # Staging overrides
└── production.yaml     # Production settings
```

```yaml
# production.yaml
identity:
  provider: "spire"
  socket_path: "/run/spire/sockets/agent.sock"

authorization:
  default_action: "deny"
  opa_url: "http://localhost:8181"

observability:
  audit_log:
    enabled: true
    destination: "syslog"
    syslog_address: "logs.example.com:514"
```

### Secrets Management

**Never commit secrets to configuration files:**

```yaml
# ❌ BAD - Secrets in config
database:
  password: "super-secret-password"  # Never!

# ✅ GOOD - Reference to secret
database:
  password_env: "DB_PASSWORD"  # From environment variable
```

**Use secret management systems:**

```yaml
# Kubernetes Secret
apiVersion: v1
kind: Secret
metadata:
  name: agent-secrets
type: Opaque
data:
  db-password: <base64-encoded>
```

```yaml
# Agent deployment references secret
env:
  - name: DB_PASSWORD
    valueFrom:
      secretKeyRef:
        name: agent-secrets
        key: db-password
```

**For sensitive API keys:**

```python
import os
from agentweave import SecureAgent

class MyAgent(SecureAgent):
    def __init__(self, config_path: str):
        super().__init__(config_path)

        # Load secrets from environment, not config
        self.api_key = os.environ.get("EXTERNAL_API_KEY")
        if not self.api_key:
            raise ValueError("EXTERNAL_API_KEY environment variable required")
```

### Validate Configurations

Always validate before deploying:

```bash
# Validate configuration
agentweave validate config/production.yaml

# Run validation in CI/CD
agentweave validate config/*.yaml || exit 1
```

---

## Operational Security

### Enable Audit Logging

**Always enable audit logging in production:**

```yaml
# ✅ GOOD - Comprehensive audit logging
observability:
  audit_log:
    enabled: true
    destination: "syslog"
    syslog_address: "logs.example.com:514"
    syslog_protocol: "tcp"
    level: "info"
    include_payloads: false  # Don't log sensitive data
    fields:
      - "timestamp"
      - "caller_spiffe_id"
      - "callee_spiffe_id"
      - "capability"
      - "action"
      - "decision"
      - "trace_id"
```

See [Audit Logging](audit-logging/) for complete guide.

### Monitor for Anomalies

Set up security monitoring:

```yaml
# Prometheus alert rules
groups:
  - name: agentweave-security
    rules:
      # High rate of denials
      - alert: HighAuthzDenialRate
        expr: rate(agentweave_authz_denied_total[5m]) > 10
        for: 5m
        annotations:
          summary: "Unusually high authorization denial rate"

      # Unknown callers
      - alert: UnknownCallerAttempt
        expr: agentweave_authz_denied_total{reason="unknown_caller"} > 0
        annotations:
          summary: "Unknown agent attempted access"

      # SVID issues
      - alert: SVIDRotationFailure
        expr: agentweave_svid_rotation_errors_total > 0
        annotations:
          summary: "SVID rotation failed"

      # Unusual capability usage
      - alert: UnusualCapabilityUsage
        expr: rate(agentweave_capability_calls_total{capability="admin"}[1h]) > 1
        annotations:
          summary: "Unusual admin capability usage pattern"
```

### Incident Response Plan

Have a documented incident response plan:

1. **Detection**: How do you detect security incidents?
   - Alerts from monitoring
   - Audit log analysis
   - User reports

2. **Containment**: How do you limit damage?
   - Revoke compromised SVIDs
   - Update OPA policies to deny access
   - Isolate affected agents

3. **Investigation**: How do you determine what happened?
   - Review audit logs
   - Check distributed traces
   - Analyze authorization decisions

4. **Recovery**: How do you restore normal operations?
   - Issue new SVIDs
   - Update policies
   - Restart agents

5. **Post-Incident**: How do you prevent recurrence?
   - Root cause analysis
   - Update policies
   - Improve monitoring

**Example: Revoking Compromised Agent**

```bash
# Step 1: Delete SPIRE entry
spire-server entry delete \
  -spiffeID spiffe://example.com/agent/compromised

# Step 2: Ban in OPA
curl -X PUT http://localhost:8181/v1/data/banned_agents \
  -d '["spiffe://example.com/agent/compromised"]'

# Step 3: Update policy to deny
cat <<EOF | curl -X PUT http://localhost:8181/v1/policies/authz --data-binary @-
package agentweave.authz
import rego.v1

default allow := false

# Deny banned agents
allow if {
    not input.caller_spiffe_id in data.banned_agents
    # ... other rules
}
EOF

# Step 4: Verify access denied
agentweave authz check \
  --caller spiffe://example.com/agent/compromised \
  --callee spiffe://example.com/agent/target
```

---

## Code Security

### Input Validation

Validate all inputs at capability boundaries:

```python
from pydantic import BaseModel, Field, validator

class ProcessRequest(BaseModel):
    """Validated input for process capability."""
    user_id: str = Field(..., min_length=1, max_length=100)
    data: str = Field(..., max_length=10000)

    @validator('user_id')
    def validate_user_id(cls, v):
        # Only allow alphanumeric and hyphens
        if not re.match(r'^[a-zA-Z0-9-]+$', v):
            raise ValueError("Invalid user_id format")
        return v

class DataProcessor(SecureAgent):
    @capability(
        name="process",
        description="Process user data"
    )
    async def process(self, request: ProcessRequest) -> dict:
        # Input is validated by Pydantic
        return await self._process_internal(request)
```

### Error Handling Without Info Leakage

Don't expose internal details in errors:

```python
# ❌ BAD - Leaks internal info
@capability(name="query")
async def query(self, sql: str):
    try:
        return await self.db.execute(sql)
    except DatabaseError as e:
        # Exposes database schema, credentials, etc.
        raise CapabilityError(f"Database error: {e}")

# ✅ GOOD - Generic error, log details internally
@capability(name="query")
async def query(self, query_id: str):
    try:
        return await self.execute_safe_query(query_id)
    except DatabaseError as e:
        # Log full error internally
        self.logger.error(
            "Database error during query",
            extra={
                "query_id": query_id,
                "error": str(e),
                "trace_id": self.context.trace_id
            }
        )
        # Return generic error to caller
        raise CapabilityError("Query failed. Check logs for details.")
```

### Dependency Scanning

Scan dependencies regularly:

```bash
# Install safety
pip install safety

# Scan for known vulnerabilities
safety check --json

# Use in CI/CD
safety check || exit 1
```

```yaml
# GitHub Actions
- name: Dependency Security Scan
  run: |
    pip install safety
    safety check --json --output safety-report.json
```

### Secure Coding Checklist

- [ ] All inputs validated
- [ ] No SQL injection possible (use parameterized queries)
- [ ] No command injection (don't use `shell=True`)
- [ ] No path traversal (validate file paths)
- [ ] Secrets not in code or logs
- [ ] Error messages don't leak info
- [ ] Dependencies scanned for vulnerabilities
- [ ] Code reviewed for security issues

---

## Kubernetes Security

### Pod Security Standards

Use restricted Pod Security Standard:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: agentweave
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### Security Context

```yaml
securityContext:
  # Pod-level
  runAsNonRoot: true
  runAsUser: 10001
  fsGroup: 10001
  seccompProfile:
    type: RuntimeDefault

containers:
  - name: agent
    securityContext:
      # Container-level
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      runAsNonRoot: true
      runAsUser: 10001
      capabilities:
        drop:
          - ALL
```

### Network Policies

Restrict network access:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agent-netpol
spec:
  podSelector:
    matchLabels:
      app: my-agent
  policyTypes:
    - Ingress
    - Egress

  ingress:
    # Only from other agents
    - from:
        - podSelector:
            matchLabels:
              app.kubernetes.io/part-of: agentweave

  egress:
    # To SPIRE
    - to:
        - namespaceSelector:
            matchLabels:
              name: spire-system
      ports:
        - protocol: TCP
          port: 8081

    # To other agents
    - to:
        - podSelector:
            matchLabels:
              app.kubernetes.io/part-of: agentweave
      ports:
        - protocol: TCP
          port: 8443

    # DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53
```

### Resource Limits

Prevent resource exhaustion:

```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

---

## Summary

**Critical Security Practices:**

1. ✅ Use SPIRE identity in production (never mock)
2. ✅ Default deny authorization
3. ✅ TLS 1.3 minimum
4. ✅ Enable audit logging
5. ✅ Short SVID TTL (1 hour)
6. ✅ Regular policy reviews
7. ✅ Monitor for anomalies
8. ✅ Validate all inputs
9. ✅ Never commit secrets
10. ✅ Run as non-root with restricted permissions

**Next Steps:**

- Review [Threat Model](threat-model/) to understand what you're protecting against
- Set up [Audit Logging](audit-logging/) for security monitoring
- Check [Compliance](compliance/) for regulatory requirements
- See main [Security Guide](/agentweave/security/) for deployment details
