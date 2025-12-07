---
layout: page
title: Production Readiness Checklist
description: Comprehensive checklist for deploying AgentWeave agents to production
parent: How-To Guides
nav_order: 6
---

# Production Readiness Checklist

This comprehensive checklist ensures your AgentWeave agents are production-ready. Review each section before deploying to production.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Security Checklist

### Identity & Authentication

- [ ] **SPIFFE/SPIRE configured** - Using SPIRE for identity (NOT static mTLS certificates)
- [ ] **SVID rotation enabled** - Automatic certificate rotation working
- [ ] **Trust domain validated** - Using appropriate trust domain (e.g., `yourdomain.com`)
- [ ] **Registration entries created** - All agents have SPIRE registration entries
- [ ] **Workload attestation configured** - Proper selectors (K8s, Unix, etc.) in place
- [ ] **Trust bundles configured** - Local and federated trust bundles loaded
- [ ] **Identity verified at startup** - Agents verify SVID before accepting requests

**Verification:**
```bash
# Verify SPIRE agent is running
docker exec spire-agent /opt/spire/bin/spire-agent api fetch -socketPath /tmp/spire-agent/public/api.sock

# Check registration entries
docker exec spire-server /opt/spire/bin/spire-server entry show
```

### Authorization

- [ ] **Default deny configured** - `default_action: deny` in production
- [ ] **OPA policies reviewed** - Policies implement least-privilege access
- [ ] **OPA policies tested** - Unit tests for all policy rules
- [ ] **Audit logging enabled** - All authorization decisions logged
- [ ] **Audit logs secured** - Logs written to tamper-proof storage
- [ ] **Policy version controlled** - Rego policies in Git with review process
- [ ] **Emergency access documented** - Break-glass procedures documented

**Verification:**
```yaml
# config.yaml must have:
authorization:
  default_action: deny  # NOT 'allow' or 'log-only'
  audit:
    enabled: true
    destination: "file:///var/log/agentweave/audit.log"
```

### Transport & TLS

- [ ] **TLS 1.3 enforced** - `tls_min_version: "1.3"` configured
- [ ] **Peer verification strict** - `peer_verification: strict` (NOT 'log-only' or 'none')
- [ ] **Strong cipher suites** - Only secure ciphers enabled
- [ ] **Certificate validation** - Peer certificates validated against trust bundle
- [ ] **mTLS required** - All agent-to-agent communication uses mTLS
- [ ] **No plaintext connections** - HTTP disabled, HTTPS only

**Verification:**
```yaml
# config.yaml must have:
transport:
  tls_min_version: "1.3"
  peer_verification: strict
```

### Secrets Management

- [ ] **No secrets in code** - API keys, passwords not in source code
- [ ] **No secrets in config files** - Secrets loaded from environment or vault
- [ ] **Environment variables secured** - Secrets in K8s secrets or AWS Secrets Manager
- [ ] **Secrets rotated regularly** - Rotation schedule documented and implemented
- [ ] **Access to secrets logged** - Secret access audited

**Best practices:**
```python
# BAD: Hardcoded secret
api_key = "sk-1234567890abcdef"

# GOOD: From environment
import os
api_key = os.environ.get("API_KEY")
if not api_key:
    raise ConfigurationError("API_KEY not set")
```

---

## Reliability Checklist

### Health Checks

- [ ] **Liveness probe configured** - K8s/Docker liveness probe responds
- [ ] **Readiness probe configured** - Agent doesn't accept traffic until ready
- [ ] **Health check endpoint** - `/health` endpoint returns status
- [ ] **Dependency checks** - Health check verifies SPIRE, OPA, database connectivity
- [ ] **Startup probe configured** - Separate startup check for slow-starting agents

**Kubernetes example:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8443
    scheme: HTTPS
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /ready
    port: 8443
    scheme: HTTPS
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 2
```

### Circuit Breakers

- [ ] **Circuit breakers enabled** - Prevents cascading failures
- [ ] **Failure threshold tuned** - Appropriate threshold for your traffic
- [ ] **Recovery timeout configured** - Allows time for downstream recovery
- [ ] **Circuit breaker metrics exposed** - State changes monitored

**Configuration:**
```yaml
transport:
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout_seconds: 30
    success_threshold: 2
```

### Retry Policies

- [ ] **Retry configuration tuned** - Appropriate max attempts and backoff
- [ ] **Exponential backoff** - Prevents thundering herd
- [ ] **Jitter enabled** - Random delay to spread retries
- [ ] **Non-retryable errors identified** - Don't retry AuthorizationError, etc.
- [ ] **Retry budget configured** - Limit total retry overhead

**Configuration:**
```yaml
transport:
  retry:
    max_attempts: 3
    backoff_base_seconds: 1.0
    backoff_max_seconds: 30.0
    jitter: true
```

### Graceful Shutdown

- [ ] **SIGTERM handler** - Gracefully shut down on SIGTERM
- [ ] **Active requests drained** - Wait for in-flight requests to complete
- [ ] **Shutdown timeout** - Force shutdown after timeout (e.g., 30s)
- [ ] **No new requests accepted** - Stop accepting traffic during shutdown

**Implementation:**
```python
import signal
import asyncio

class GracefulAgent(SecureAgent):
    async def start(self):
        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        signal.signal(signal.SIGINT, self._handle_sigterm)
        await super().start()

    def _handle_sigterm(self, signum, frame):
        """Handle SIGTERM gracefully."""
        asyncio.create_task(self._graceful_shutdown())

    async def _graceful_shutdown(self):
        """Gracefully shut down."""
        self.logger.info("Received SIGTERM, shutting down gracefully")

        # Stop accepting new requests
        self.accepting_requests = False

        # Wait for active requests to complete (max 30s)
        timeout = 30
        while self.active_requests > 0 and timeout > 0:
            await asyncio.sleep(1)
            timeout -= 1

        # Stop the agent
        await self.stop()
```

---

## Observability Checklist

### Metrics

- [ ] **Metrics enabled** - Prometheus metrics exposed
- [ ] **Metrics endpoint secured** - /metrics protected or on separate port
- [ ] **Core metrics exported** - Request count, duration, errors
- [ ] **Business metrics exported** - Domain-specific metrics
- [ ] **Resource metrics exported** - CPU, memory, connection pool stats
- [ ] **SLO/SLI metrics defined** - Service level objectives measurable

**Must-have metrics:**
```
# Request metrics
agentweave_requests_total{capability="search",status="success"}
agentweave_request_duration_seconds{capability="search",quantile="0.95"}

# Authorization metrics
agentweave_authz_decisions_total{result="allowed"}
agentweave_authz_check_duration_seconds

# System metrics
agentweave_connection_pool_active
agentweave_circuit_breaker_state{callee="search-agent"}
```

### Tracing

- [ ] **Distributed tracing enabled** - OpenTelemetry or Jaeger configured
- [ ] **Trace sampling configured** - Sample rate appropriate for volume
- [ ] **Traces include SPIFFE IDs** - Agent identities in trace context
- [ ] **Traces exported** - Sent to collector (Jaeger, Tempo, etc.)
- [ ] **Trace retention configured** - Appropriate retention period

**Configuration:**
```yaml
observability:
  tracing:
    enabled: true
    exporter: otlp
    endpoint: http://tempo:4317
    sampling_rate: 0.1  # 10% of requests
```

### Logging

- [ ] **Structured logging** - JSON format for machine parsing
- [ ] **Log levels appropriate** - INFO in prod (DEBUG only for troubleshooting)
- [ ] **Sensitive data redacted** - No PII, credentials in logs
- [ ] **Request ID in logs** - Every log has correlation ID
- [ ] **Logs centralized** - Sent to Elasticsearch, Loki, or CloudWatch
- [ ] **Log retention configured** - Appropriate retention policy

**Log format:**
```json
{
  "timestamp": "2025-12-07T12:34:56.789Z",
  "level": "INFO",
  "message": "Request processed successfully",
  "request_id": "req-123",
  "spiffe_id": "spiffe://yourdomain.com/agent/search",
  "duration_ms": 123,
  "caller_id": "spiffe://yourdomain.com/agent/orchestrator"
}
```

### Alerts

- [ ] **Critical alerts configured** - Page on-call for critical issues
- [ ] **Warning alerts configured** - Notify team for degraded performance
- [ ] **Alert thresholds tuned** - Based on actual traffic patterns
- [ ] **Alert runbooks created** - Response procedures documented
- [ ] **Alerts tested** - Fire test alerts to verify routing

**Critical alerts:**
- SVID rotation failing
- Authorization service unreachable
- Error rate > 5%
- p95 latency > SLO
- Circuit breaker opened
- Memory/CPU > 90%

---

## Deployment Checklist

### Resource Limits

- [ ] **CPU requests set** - Guaranteed CPU allocation
- [ ] **CPU limits set** - Maximum CPU usage
- [ ] **Memory requests set** - Guaranteed memory allocation
- [ ] **Memory limits set** - Maximum memory usage (OOM protection)
- [ ] **Ephemeral storage limits** - Disk usage bounded

**Kubernetes example:**
```yaml
resources:
  requests:
    cpu: 500m
    memory: 512Mi
    ephemeral-storage: 1Gi
  limits:
    cpu: 2000m
    memory: 2Gi
    ephemeral-storage: 5Gi
```

### Network Policies

- [ ] **Network policies defined** - K8s NetworkPolicy or equivalent
- [ ] **Ingress rules configured** - Only required ports open
- [ ] **Egress rules configured** - Only required destinations allowed
- [ ] **Default deny** - Deny all traffic by default
- [ ] **Policies tested** - Verified in staging environment

**Example NetworkPolicy:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: search-agent-netpol
spec:
  podSelector:
    matchLabels:
      app: search-agent
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: orchestrator-agent
    ports:
    - protocol: TCP
      port: 8443
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: spire-agent
  - to:
    - podSelector:
        matchLabels:
          app: opa
```

### Secrets Management

- [ ] **K8s Secrets used** - Or AWS Secrets Manager, Vault, etc.
- [ ] **Secrets encrypted at rest** - K8s encryption enabled
- [ ] **Secrets mounted securely** - File-based secrets, not environment vars
- [ ] **RBAC configured** - Only agent pods can read secrets
- [ ] **Secret rotation automated** - Automatic rotation scheduled

### Container Image

- [ ] **Base image minimal** - Use distroless or alpine
- [ ] **No root user** - Run as non-root user
- [ ] **Image scanned** - Trivy/Snyk scan passed
- [ ] **No vulnerabilities** - Critical/high vulns resolved
- [ ] **Image signed** - Cosign or equivalent used
- [ ] **SBOM generated** - Software bill of materials available

**Dockerfile example:**
```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 agentweave

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=agentweave:agentweave . /app
WORKDIR /app

# Switch to non-root user
USER agentweave

CMD ["python", "agent.py"]
```

### Rollback Plan

- [ ] **Rollback procedure documented** - Step-by-step instructions
- [ ] **Previous version tagged** - Git tag for last known good version
- [ ] **Rollback tested** - Procedure tested in staging
- [ ] **Rollback automation** - One-command rollback if possible
- [ ] **Data migration reversible** - Database changes can be undone

---

## Testing Checklist

### Unit Tests

- [ ] **Unit tests written** - All capabilities have tests
- [ ] **Test coverage > 80%** - Measured with pytest-cov
- [ ] **Mocks used** - Tests don't require external services
- [ ] **Tests run in CI** - Automated on every commit
- [ ] **Tests pass** - All tests passing before deploy

### Integration Tests

- [ ] **Integration tests written** - Multi-agent scenarios tested
- [ ] **OPA policies tested** - Policy unit tests pass
- [ ] **Authorization flows tested** - Allow and deny cases tested
- [ ] **Error handling tested** - Failure scenarios covered
- [ ] **Tests run in CI** - Automated integration tests

### Load Tests

- [ ] **Load tests performed** - Locust or similar used
- [ ] **Peak load tested** - 2x expected peak traffic
- [ ] **Sustained load tested** - 24-hour soak test
- [ ] **Spike load tested** - Sudden traffic increase handled
- [ ] **Performance SLOs met** - p95 latency within target

**Load test results to verify:**
```
Requests/sec:     > 100 (your target)
Error rate:       < 0.1%
p50 latency:      < 50ms
p95 latency:      < 200ms
p99 latency:      < 500ms
Connection pool:  < 80% utilized
```

### Security Tests

- [ ] **Penetration testing** - Security review completed
- [ ] **SAST performed** - Static analysis (Bandit, etc.)
- [ ] **Dependency scan** - Known vulnerabilities checked
- [ ] **Secret scanning** - No secrets in Git history
- [ ] **TLS configuration tested** - sslyze or testssl.sh

---

## Documentation Checklist

### Operational Documentation

- [ ] **Architecture diagram** - System design documented
- [ ] **Dependencies documented** - All external services listed
- [ ] **Configuration documented** - All config options explained
- [ ] **Runbooks created** - Common operations documented
- [ ] **Troubleshooting guide** - Common issues and solutions
- [ ] **Disaster recovery plan** - Recovery procedures documented

### Developer Documentation

- [ ] **API documentation** - All capabilities documented
- [ ] **Setup instructions** - Local development guide
- [ ] **Testing guide** - How to run tests
- [ ] **Contribution guide** - How to contribute
- [ ] **Code comments** - Complex logic explained

### Compliance Documentation

- [ ] **Data flow diagram** - Data flows mapped
- [ ] **Access control matrix** - Who can access what
- [ ] **Audit log format** - Log schema documented
- [ ] **Compliance controls** - SOC2/HIPAA controls mapped
- [ ] **Privacy policy** - Data handling documented

---

## Pre-Deploy Verification

Run these checks immediately before deploying:

### Configuration Validation

```bash
# Validate configuration file
agentweave validate config.yaml

# Expected output:
# ✓ Configuration is valid
# ✓ Security settings: production-ready
# ✓ TLS version: 1.3
# ✓ Peer verification: strict
# ✓ Default action: deny
```

### SPIRE Connectivity

```bash
# Test SPIRE connection
docker exec spire-agent /opt/spire/bin/spire-agent api fetch

# Verify SVID is issued
# Expected: SPIFFE ID, valid certificate, not expired
```

### OPA Connectivity

```bash
# Test OPA connection
curl http://localhost:8181/v1/data/agentweave/authz

# Verify policy is loaded
```

### Smoke Test

```bash
# Deploy to staging
kubectl apply -f deployment-staging.yaml

# Run smoke tests
pytest tests/smoke/ --env=staging

# Verify:
# - Agent starts successfully
# - Health check passes
# - Can fetch SVID
# - Authorization works
# - Can call other agents
```

---

## Post-Deploy Verification

After deploying to production:

### Immediate Checks (0-15 minutes)

- [ ] **Pods running** - All replicas healthy
  ```bash
  kubectl get pods -l app=search-agent
  # All pods should be Running
  ```

- [ ] **Health checks passing** - Liveness/readiness probes OK
  ```bash
  kubectl describe pod <pod-name>
  # Events should show successful health checks
  ```

- [ ] **Logs normal** - No errors in startup logs
  ```bash
  kubectl logs <pod-name> --tail=100
  # Check for errors, warnings
  ```

- [ ] **Metrics available** - Prometheus scraping successfully
  ```bash
  curl http://<pod-ip>:9090/metrics
  # Should return Prometheus metrics
  ```

### Short-term Checks (15 minutes - 1 hour)

- [ ] **Traffic routing correctly** - Requests reaching new pods
- [ ] **Error rate normal** - No spike in errors
- [ ] **Latency normal** - p95 latency within SLO
- [ ] **Authorization working** - No unusual denials
- [ ] **No circuit breakers open** - All dependencies healthy

### Long-term Monitoring (1+ hours)

- [ ] **Memory stable** - No memory leaks
- [ ] **CPU stable** - No unexpected CPU spikes
- [ ] **Connection pool healthy** - No exhaustion
- [ ] **SVID rotation working** - Certificates rotating
- [ ] **No OPA errors** - Policy evaluation working

---

## Production-Ready Criteria

Your agent is production-ready when:

1. **Security**: All security checklist items completed
2. **Reliability**: Circuit breakers, retries, health checks configured
3. **Observability**: Metrics, logs, traces configured and monitored
4. **Testing**: Unit, integration, and load tests passing
5. **Documentation**: Runbooks and troubleshooting guides complete
6. **Deployment**: Rollback plan tested, resources configured
7. **Verification**: All pre-deploy checks passed
8. **Monitoring**: Alerts configured and tested

---

## Related Guides

- [Configure Identity Providers](identity-providers.md) - SPIFFE/SPIRE setup
- [Common Authorization Patterns](policy-patterns.md) - Production policies
- [Error Handling](error-handling.md) - Graceful error handling
- [Performance Tuning](performance.md) - Optimize for production
- [Testing Your Agents](testing.md) - Test before deploy

---

## Templates

### Deployment Checklist Template

Use this template for each deployment:

```markdown
# Deployment Checklist: [Agent Name] v[Version]

**Date**: YYYY-MM-DD
**Engineer**: Name
**Environment**: Production

## Pre-Deploy
- [ ] All tests passing (unit, integration, load)
- [ ] Configuration validated
- [ ] Security review completed
- [ ] Rollback plan documented
- [ ] Change approved by [Approver]

## Deploy
- [ ] Deployed to staging (timestamp: ____)
- [ ] Smoke tests passed in staging
- [ ] Deployed to production (timestamp: ____)
- [ ] Health checks passing

## Post-Deploy
- [ ] Metrics normal (15 min)
- [ ] Logs normal (15 min)
- [ ] Error rate normal (1 hour)
- [ ] Memory/CPU stable (1 hour)
- [ ] No alerts fired

## Rollback (if needed)
- [ ] Rollback decision made by: ____
- [ ] Rollback executed (timestamp: ____)
- [ ] Previous version healthy
- [ ] Incident report filed

**Status**: [ ] Success / [ ] Rolled back / [ ] In progress
**Notes**: ____
```

---

**Remember**: Production readiness is not a one-time checklist. Review regularly and update as your system evolves.
