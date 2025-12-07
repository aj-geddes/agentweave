---
layout: page
title: FAQ
description: Frequently Asked Questions about AgentWeave
nav_order: 3
parent: Troubleshooting
---

# Frequently Asked Questions

Common questions about AgentWeave, organized by category.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## General Questions

### What is AgentWeave?

AgentWeave is a Python SDK for building secure, cross-cloud AI agents with cryptographic identity and automatic authorization. It's built on the principle that "the secure path is the only path" - developers cannot bypass security features.

Key features:
- **Cryptographic identity** via SPIFFE/SPIRE (no API keys or passwords)
- **Zero-trust architecture** with automatic mTLS and OPA-based authorization
- **A2A protocol** for standardized agent-to-agent communication
- **Cross-cloud ready** - works across AWS, GCP, Azure, on-premises

### Why use SPIFFE for identity?

SPIFFE (Secure Production Identity Framework For Everyone) provides several advantages over traditional authentication:

**vs. API Keys:**
- Automatic rotation (no manual key management)
- No secrets to leak or store
- Cryptographically strong identity

**vs. JWTs:**
- Automatic certificate rotation
- Mutual authentication built-in
- No shared secrets between services

**vs. Cloud IAM:**
- Cloud-agnostic (works across AWS, GCP, Azure)
- Standardized format
- Federation support for multi-org scenarios

### Why OPA for authorization?

Open Policy Agent (OPA) provides several benefits:

**Policy as Code:**
```rego
# Readable, testable, version-controlled
allow if {
    input.caller_spiffe_id in data.allowed_callers[input.callee_spiffe_id]
}
```

**Separation of Concerns:**
- Policies managed separately from application code
- Policy updates without code changes
- Centralized policy management

**Flexibility:**
- Fine-grained access control
- Context-aware decisions
- Dynamic policy updates

### Is AgentWeave production-ready?

Yes! AgentWeave is built on production-proven technologies:

- **SPIFFE/SPIRE** - Used by Netflix, Bloomberg, Pinterest
- **OPA** - CNCF graduated project, used by major cloud providers
- **mTLS** - Industry standard for service-to-service communication

AgentWeave enforces security by default:
- TLS 1.3 required in production
- Default deny authorization
- No security bypasses possible
- Comprehensive audit logging

See [Security Guide](../security.md) for production deployment guidelines.

### How does AgentWeave compare to other agent frameworks?

| Feature | AgentWeave | LangChain | AutoGen | CrewAI |
|---------|-----------|-----------|---------|--------|
| Cryptographic Identity | ✓ | ✗ | ✗ | ✗ |
| mTLS by Default | ✓ | ✗ | ✗ | ✗ |
| Policy-Based AuthZ | ✓ | ✗ | ✗ | ✗ |
| A2A Protocol | ✓ | ✗ | ✗ | ✗ |
| Cross-Cloud | ✓ | ✓ | ✓ | ✓ |
| LLM Integration | ✓ | ✓ | ✓ | ✓ |

AgentWeave focuses on **secure, production-grade** agent infrastructure. You can use it with LangChain, AutoGen, or other frameworks for LLM capabilities.

---

## Technical Questions

### Can I use AgentWeave without SPIRE?

No. SPIFFE/SPIRE is fundamental to AgentWeave's security model. However, for local development, you can run SPIRE easily with Docker:

```bash
# Download starter template
curl -O https://raw.githubusercontent.com/agentweave/agentweave-starter/main/docker-compose.yaml

# Start SPIRE
docker-compose up -d
```

**Why SPIRE is required:**
- Provides cryptographic identity for all agents
- Enables automatic mTLS authentication
- Supports federation for multi-org scenarios
- Industry-standard, production-proven

### Can I use AgentWeave without OPA?

No, but you can use a permissive policy for development:

```yaml
# Development only
authorization:
  provider: "opa"
  default_action: "log-only"  # Logs but doesn't block
```

**Why OPA is required:**
- Enforces authorization before your code runs
- Provides audit trail of all access decisions
- Enables fine-grained access control
- Separates policy from application logic

**Production requirement:**
```yaml
# Production
authorization:
  default_action: "deny"  # Required in production
```

### How do I test locally without full infrastructure?

Use the AgentWeave starter template:

```bash
# Download and start infrastructure
curl -O https://raw.githubusercontent.com/agentweave/agentweave-starter/main/docker-compose.yaml
docker-compose up -d

# This starts:
# - SPIRE Server
# - SPIRE Agent
# - OPA
# - Jaeger (optional, for tracing)
```

For testing without infrastructure, use the test utilities:

```python
from agentweave.testing import MockSecureAgent, MockIdentityProvider

# Create mock agent for testing
async def test_my_capability():
    agent = MockSecureAgent(
        spiffe_id="spiffe://test.local/agent/test"
    )

    result = await agent.process_data({"test": "data"})
    assert result["status"] == "success"
```

### What Python versions are supported?

**Supported:**
- Python 3.10+
- Python 3.11 (recommended)
- Python 3.12

**Not supported:**
- Python 3.9 and earlier (missing required async features)
- Python 2.x

**Check your version:**
```bash
python --version
```

### How does SVID rotation work?

SVID (SPIFFE Verifiable Identity Document) rotation is automatic:

**Rotation Timeline:**
```
SVID issued with 1h TTL
├─ 0min:  SVID valid
├─ 30min: SPIRE begins rotation (50% of TTL)
├─ 31min: New SVID fetched
├─ 31min: Agent updates mTLS with new cert
├─ 60min: Old SVID expires
└─ Agent continues with new SVID
```

**Your code doesn't need to do anything**, but you can monitor rotation:

```python
class MyAgent(SecureAgent):
    async def on_svid_update(self, new_svid):
        """Called when SVID rotates."""
        self.logger.info(
            "SVID rotated",
            extra={"expiry": new_svid.expiry.isoformat()}
        )
```

**Best practices:**
- Set TTL to 1 hour or less
- Monitor rotation failures
- Ensure SPIRE connectivity for rotation

### How do I debug policy decisions?

Several methods:

**1. Use CLI tool:**
```bash
agentweave authz check \
  --caller spiffe://example.com/agent/caller \
  --target spiffe://example.com/agent/target \
  --action process_data \
  --trace
```

**2. Enable debug logging:**
```yaml
observability:
  logging:
    loggers:
      "agentweave.authz": "DEBUG"
```

**3. Query OPA directly:**
```bash
curl -X POST http://localhost:8181/v1/data/agentweave/authz/allow \
  -d '{
    "input": {...},
    "explain": "full"
  }' | jq
```

**4. Check decision logs:**
```python
# View recent authorization decisions
import requests
response = requests.get("http://localhost:8181/v1/data/system/decisions")
decisions = response.json()["result"]
```

See [Debugging Guide](debugging.md#testing-opa-policies) for more details.

### Can I use custom authorization logic?

Yes, you can extend OPA policies or implement custom authorization:

**Option 1: Extend OPA policy (recommended):**
```rego
# authz.rego
package agentweave.authz

# Custom rule: Allow during business hours
allow if {
    time_in_business_hours
}

time_in_business_hours if {
    now := time.now_ns()
    hour := time.clock(now)[0]
    hour >= 9
    hour <= 17
}
```

**Option 2: Custom authorization provider:**
```python
from agentweave.authz import AuthorizationProvider

class CustomAuthZ(AuthorizationProvider):
    async def authorize(self, context: AuthzContext) -> AuthzDecision:
        # Your custom logic
        if context.caller in self.allowed_callers:
            return AuthzDecision(allow=True, reason="custom_allowlist")
        return AuthzDecision(allow=False, reason="not_in_allowlist")

# Use in config
agent = SecureAgent(
    config=config,
    authz_provider=CustomAuthZ()
)
```

### How do I handle multi-region deployments?

AgentWeave works across regions using SPIFFE federation:

**Architecture:**
```
Region 1 (us-east-1)          Region 2 (eu-west-1)
├─ SPIRE Server              ├─ SPIRE Server
├─ Trust Domain: us.example  ├─ Trust Domain: eu.example
└─ Agent: processor          └─ Agent: analyzer
   ↓                            ↑
   └──── Federated Trust ──────┘
```

**Setup federation:**
```bash
# On each SPIRE server, exchange trust bundles
spire-server bundle set \
  -format spiffe \
  -id spiffe://eu.example.com \
  -path eu-bundle.pem
```

**Allow federated domains:**
```yaml
# config.yaml
identity:
  allowed_trust_domains:
    - "us.example.com"   # Own domain
    - "eu.example.com"   # Federated region
```

---

## Security Questions

### Why can't I disable security in production?

AgentWeave enforces security by design to prevent accidental misconfigurations:

```yaml
# This will FAIL in production
authorization:
  default_action: "log-only"  # ❌ Not allowed

# Error:
# "Security violation: 'log-only' mode not allowed in production environment"
```

**Rationale:**
- Prevents accidental exposure of agents
- Enforces best practices
- Ensures compliance requirements are met
- Makes security violations obvious

**For development:**
```yaml
# config.dev.yaml
authorization:
  default_action: "log-only"  # OK for development

# Start with dev config
agentweave serve config.dev.yaml --env development
```

### How secure is the communication?

AgentWeave uses defense-in-depth security:

**Layer 1: Identity (SPIFFE)**
- Cryptographic identity (X.509 certificates)
- Automatic rotation
- No shared secrets

**Layer 2: Transport (mTLS)**
- TLS 1.3 only in production
- Mutual authentication (both sides verify)
- Perfect forward secrecy
- Strong cipher suites only

**Layer 3: Authorization (OPA)**
- Policy-based access control
- Default deny
- Audit logging
- Fine-grained permissions

**Security properties:**
- **Confidentiality**: All data encrypted in transit
- **Integrity**: Tampering detected via certificates
- **Authentication**: Both parties cryptographically verified
- **Authorization**: Policies enforced before execution
- **Non-repudiation**: Audit logs prove who did what

### What if OPA goes down?

AgentWeave handles OPA failures gracefully:

**Circuit Breaker Pattern:**
```yaml
authorization:
  circuit_breaker:
    failure_threshold: 5   # Open after 5 failures
    success_threshold: 2   # Close after 2 successes
    timeout: 30           # Retry after 30 seconds
```

**Behavior:**
1. OPA fails → Circuit breaker opens
2. Requests **fail closed** (denied) to maintain security
3. Circuit breaker periodically retries
4. When OPA recovers → Circuit closes

**Monitoring:**
```bash
# Check circuit breaker status
curl http://localhost:9090/metrics | grep circuit_breaker

# agentweave_authz_circuit_breaker_state{state="open"} 0
# agentweave_authz_circuit_breaker_state{state="closed"} 1
```

**High Availability:**
```yaml
# Run multiple OPA instances
authorization:
  opa_endpoints:
    - "http://opa-1:8181"
    - "http://opa-2:8181"
    - "http://opa-3:8181"
  failover_strategy: "round_robin"
```

### How do I handle key rotation?

**SVID rotation (automatic):**
- Handled automatically by SPIRE
- No code changes needed
- Configurable TTL (recommended: 1 hour)

**CA rotation (manual):**
```bash
# 1. Generate new CA
spire-server x509 rotate-ca

# 2. Old and new CAs valid during transition
# 3. After rotation period, old CA removed
```

**OPA policy rotation:**
```bash
# 1. Load new policy version
curl -X PUT http://localhost:8181/v1/policies/authz-v2 \
  --data-binary @authz-v2.rego

# 2. Switch agents to new policy
# config.yaml: policy_path: "agentweave/authz/v2/allow"

# 3. Remove old policy
curl -X DELETE http://localhost:8181/v1/policies/authz-v1
```

### What's the threat model?

See [Security Guide - Threat Model](../security/threat-model.md) for full details.

**Protected against:**
- Man-in-the-middle attacks (mTLS)
- Replay attacks (nonces, timestamps)
- Impersonation (cryptographic identity)
- Unauthorized access (OPA policies)
- Credential theft (no long-lived credentials)

**Out of scope:**
- Compromised SPIRE server (trusted component)
- Malicious admin with SPIRE access
- Physical access to nodes
- Supply chain attacks on dependencies

**Defense in depth:**
- Run SPIRE on dedicated infrastructure
- Restrict SPIRE admin access
- Use hardware security modules (HSMs) for SPIRE keys
- Regular security audits
- Dependency scanning

---

## Operations Questions

### How do I monitor agents?

AgentWeave exposes Prometheus metrics:

```yaml
# config.yaml
observability:
  metrics:
    enabled: true
    port: 9090
    path: "/metrics"
```

**Key metrics:**
```bash
# Request rate
agentweave_requests_total

# Request duration
agentweave_request_duration_seconds

# Authorization decisions
agentweave_authz_allowed_total
agentweave_authz_denied_total

# SVID rotation
agentweave_svid_rotation_total
agentweave_svid_rotation_errors_total

# OPA health
agentweave_opa_requests_total
agentweave_opa_errors_total
```

**Grafana dashboard:**
```bash
# Import official dashboard
https://grafana.com/grafana/dashboards/agentweave
```

See [Observability Tutorial](/tutorials/observability/) for details.

### How do I scale agents?

AgentWeave agents are stateless and scale horizontally:

**Kubernetes:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-agent
spec:
  replicas: 5  # Scale to 5 replicas
```

**Horizontal Pod Autoscaler:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: my-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: my-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

**Load balancing:**
- Each agent has same SPIFFE ID
- Clients can use DNS round-robin
- Or use Kubernetes Service
- Or use service mesh (Istio, Linkerd)

### What metrics should I watch?

**Critical metrics:**

**Request error rate:**
```promql
# Alert if error rate > 5%
rate(agentweave_requests_total{status="error"}[5m]) /
rate(agentweave_requests_total[5m]) > 0.05
```

**Authorization denial rate:**
```promql
# Alert if denials spike
rate(agentweave_authz_denied_total[5m]) > 10
```

**SVID rotation failures:**
```promql
# Alert on any rotation failure
agentweave_svid_rotation_errors_total > 0
```

**OPA availability:**
```promql
# Alert if OPA error rate high
rate(agentweave_opa_errors_total[5m]) > 5
```

**Request latency:**
```promql
# Alert if p99 latency > 1s
histogram_quantile(0.99,
  rate(agentweave_request_duration_seconds_bucket[5m])
) > 1
```

See [Observability Tutorial](/tutorials/observability/) for complete alert rules.

### How do I upgrade agents?

**Rolling upgrade (recommended):**

```bash
# Kubernetes
kubectl set image deployment/my-agent \
  agent=agentweave/my-agent:v2.0.0

# Deployment will:
# 1. Start new pod with v2.0.0
# 2. Wait for health checks
# 3. Terminate old pod
# 4. Repeat for all replicas
```

**Blue/Green deployment:**

```bash
# 1. Deploy new version alongside old
kubectl apply -f my-agent-v2.yaml

# 2. Test new version
agentweave ping spiffe://example.com/agent/my-agent-v2

# 3. Switch traffic (update Service selector)
kubectl patch service my-agent -p '{"spec":{"selector":{"version":"v2"}}}'

# 4. Monitor for issues
# 5. Remove old version
kubectl delete deployment my-agent-v1
```

**Breaking changes:**
- Update SPIFFE IDs if capability names change
- Update OPA policies if authorization changes
- Update client agents if A2A protocol changes

**Best practices:**
- Test in staging first
- Use canary deployments for risky changes
- Monitor metrics during rollout
- Have rollback plan ready

### How do I handle secrets?

AgentWeave doesn't use long-lived secrets, but you may need secrets for:
- External API keys
- Database credentials
- LLM API keys

**Kubernetes Secrets:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: agent-secrets
type: Opaque
data:
  openai_api_key: <base64-encoded>
```

```yaml
# Use in pod
env:
  - name: OPENAI_API_KEY
    valueFrom:
      secretKeyRef:
        name: agent-secrets
        key: openai_api_key
```

**External Secret Managers:**
```yaml
# AWS Secrets Manager
from agentweave.secrets import AWSSecretsProvider

secrets = AWSSecretsProvider(region="us-east-1")
api_key = await secrets.get_secret("openai-api-key")
```

See [Identity Providers Guide](/guides/identity-providers/) for details.

---

## Integration Questions

### Can I use AgentWeave with LangChain?

Yes! AgentWeave handles secure infrastructure, LangChain handles LLM workflows:

```python
from agentweave import SecureAgent, capability
from langchain.agents import create_openai_functions_agent
from langchain.chat_models import ChatOpenAI

class LLMAgent(SecureAgent):
    def __init__(self, config):
        super().__init__(config)
        self.llm = ChatOpenAI(model="gpt-4")
        self.agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.get_tools()
        )

    @capability("chat")
    async def chat(self, message: str) -> dict:
        """Chat with LLM agent."""
        # AgentWeave handles: identity, authz, mTLS
        # LangChain handles: LLM interaction
        response = await self.agent.ainvoke({"input": message})
        return {"response": response["output"]}
```

### Can I use AgentWeave with AutoGen?

Yes! Use AgentWeave for secure agent infrastructure, AutoGen for multi-agent conversations:

```python
from agentweave import SecureAgent, capability
import autogen

class AutoGenAgent(SecureAgent):
    @capability("collaborate")
    async def collaborate(self, task: str) -> dict:
        """Multi-agent collaboration using AutoGen."""
        # Create AutoGen agents
        assistant = autogen.AssistantAgent("assistant")
        user_proxy = autogen.UserProxyAgent("user")

        # Run conversation
        user_proxy.initiate_chat(assistant, message=task)

        return {"result": user_proxy.last_message()}
```

### How do I integrate with existing services?

**Option 1: Wrap existing service:**
```python
class LegacyServiceAgent(SecureAgent):
    @capability("process")
    async def process(self, data: dict) -> dict:
        """Call legacy service securely."""
        # AgentWeave provides secure wrapper
        result = await self.legacy_client.call(data)
        return result
```

**Option 2: Sidecar pattern:**
```yaml
# Kubernetes pod with sidecar
containers:
  - name: legacy-service
    image: legacy-service:latest
  - name: agentweave-sidecar
    image: agentweave/sidecar:latest
    # Sidecar handles mTLS, routes to legacy service
```

### Can I use AgentWeave with non-Python agents?

Yes! AgentWeave implements the A2A (Agent-to-Agent) protocol, which is language-agnostic.

**Call from any language:**
```bash
# HTTP/HTTPS request to A2A endpoint
curl -X POST https://agent:8443/a2a/v1/tasks \
  --cert client-cert.pem \
  --key client-key.pem \
  -H "Content-Type: application/json" \
  -d '{
    "task_type": "process_data",
    "payload": {"data": "..."}
  }'
```

**Implementations:**
- Python: AgentWeave SDK
- Go: Google ADK
- Java: AWS Bedrock AgentCore
- TypeScript: Community implementation

See [A2A Protocol](../a2a-protocol.md) for spec.

---

## Next Steps

- **[Common Issues](common-issues.md)** - Quick solutions
- **[Debugging Guide](debugging.md)** - Deep troubleshooting
- **[Support](support.md)** - Get help
- **[Security Guide](../security.md)** - Production security
