# Security Guide

This guide covers security architecture, deployment best practices, and hardening guidelines for the AgentWeave SDK.

## Security Architecture

The SDK enforces a layered security model where every component is security-critical:

```
┌─────────────────────────────────────────────────────────────┐
│                      Security Layers                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Layer 1: Identity (SPIFFE/SPIRE)                   │   │
│  │  • Cryptographic workload identity                  │   │
│  │  • Automatic certificate rotation                   │   │
│  │  • No shared secrets                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │  Layer 2: Transport (mTLS)                          │   │
│  │  • TLS 1.3 mandatory                                │   │
│  │  • Mutual authentication                            │   │
│  │  • Perfect forward secrecy                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │  Layer 3: Authorization (OPA)                       │   │
│  │  • Policy-based access control                      │   │
│  │  • Default deny                                     │   │
│  │  • Audit logging                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│  ┌─────────────────────────▼───────────────────────────┐   │
│  │  Layer 4: Application Logic                         │   │
│  │  • Input validation                                 │   │
│  │  • Business logic isolation                         │   │
│  │  • Rate limiting                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## SPIFFE/SPIRE Setup

### Architecture Overview

SPIFFE provides cryptographic identity for workloads. SPIRE is the production implementation.

**Components**:
- **SPIRE Server**: Issues identities (SVIDs) to agents
- **SPIRE Agent**: Runs on each node, provides Workload API
- **Workload**: Your agent, which fetches SVIDs from local SPIRE Agent

### Installation

#### Kubernetes

```bash
# Install SPIRE using Helm
helm repo add spiffe https://spiffe.github.io/helm-charts-hardened/
helm repo update

# Install SPIRE Server
helm install spire-server spiffe/spire \
  --namespace spire-system \
  --create-namespace \
  --set global.spire.trustDomain=agentweave.io

# Install SPIRE Agent (DaemonSet)
helm install spire-agent spiffe/spire \
  --namespace spire-system \
  --set agent.enabled=true \
  --set server.enabled=false
```

#### Docker Compose

See [examples/multi_agent/docker-compose.yaml](../examples/multi_agent/docker-compose.yaml) for full setup.

### SPIRE Server Configuration

**server.conf**:
```hcl
server {
    bind_address = "0.0.0.0"
    bind_port = "8081"
    trust_domain = "agentweave.io"
    data_dir = "/opt/spire/data"
    log_level = "INFO"

    # CA for signing SVIDs
    ca_subject {
        country = ["US"]
        organization = ["HVS"]
        common_name = "agentweave.io"
    }
}

plugins {
    DataStore "sql" {
        plugin_data {
            database_type = "postgres"
            connection_string = "postgresql://user:pass@postgres:5432/spire"
        }
    }

    KeyManager "disk" {
        plugin_data {
            keys_path = "/opt/spire/data/keys.json"
        }
    }

    NodeAttestor "k8s_psat" {
        plugin_data {
            clusters = {
                "production" = {
                    service_account_allow_list = ["spire-system:spire-agent"]
                }
            }
        }
    }

    # Enable federation
    BundlePublisher "https_web" {
        plugin_data {
            address = "0.0.0.0:8443"
            acme {
                domain_name = "spire.agentweave.io"
                email = "admin@agentweave.io"
            }
        }
    }
}
```

### SPIRE Agent Configuration

**agent.conf**:
```hcl
agent {
    data_dir = "/opt/spire/data"
    log_level = "INFO"
    server_address = "spire-server"
    server_port = "8081"
    socket_path = "/run/spire/sockets/agent.sock"
    trust_domain = "agentweave.io"
}

plugins {
    NodeAttestor "k8s_psat" {
        plugin_data {
            cluster = "production"
        }
    }

    KeyManager "disk" {
        plugin_data {
            directory = "/opt/spire/data"
        }
    }

    WorkloadAttestor "k8s" {
        plugin_data {
            skip_kubelet_verification = false
        }
    }

    WorkloadAttestor "unix" {
        plugin_data {}
    }
}
```

### Registration Entries

Register your agent with SPIRE:

```bash
# Create registration entry for agent
spire-server entry create \
  -spiffeID spiffe://agentweave.io/agent/data-processor/prod \
  -parentID spiffe://agentweave.io/k8s-node \
  -selector k8s:ns:agentweave \
  -selector k8s:sa:data-processor \
  -selector k8s:pod-label:app:data-processor \
  -dns data-processor.agentweave.svc.cluster.local \
  -ttl 3600

# Verify entry was created
spire-server entry show -spiffeID spiffe://agentweave.io/agent/data-processor/prod
```

**Selectors**:
- `k8s:ns:NAMESPACE` - Kubernetes namespace
- `k8s:sa:SERVICE_ACCOUNT` - Service account name
- `k8s:pod-label:KEY:VALUE` - Pod label
- `unix:uid:UID` - Unix user ID (non-K8s)
- `unix:gid:GID` - Unix group ID

### SVID Rotation

SVIDs automatically rotate based on TTL:

```python
# SDK handles rotation automatically
# Your code doesn't need to do anything

# But you can subscribe to rotation events:
class MyAgent(SecureAgent):
    async def on_svid_update(self, new_svid):
        """Called when SVID rotates."""
        self.logger.info(
            f"SVID rotated. New expiry: {new_svid.expiry}"
        )
```

**Best Practices**:
- Set TTL to 1 hour or less
- SPIRE rotates at 50% of TTL (30 min for 1h TTL)
- Monitor rotation events for failures

### Federation Setup

To trust agents from another organization:

```bash
# On SPIRE Server A (agentweave.io)
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

# Verify federation
spire-server bundle list
```

Agent configuration:
```yaml
identity:
  allowed_trust_domains:
    - "agentweave.io"        # Own domain
    - "partner.example.com"  # Federated domain
```

## OPA Policy Configuration

### Policy Structure

```rego
package agentweave.authz

import rego.v1

# Default deny - explicit allow required
default allow := false

# Decision includes reason for audit
decision := {
    "allow": allow,
    "reason": reason
}

# Rule 1: Same trust domain
allow if {
    same_trust_domain
}

reason := "same_trust_domain" if {
    same_trust_domain
}

same_trust_domain if {
    caller_domain := split(input.caller_spiffe_id, "/")[2]
    callee_domain := split(input.callee_spiffe_id, "/")[2]
    caller_domain == callee_domain
}

# Rule 2: Specific agent allowlist
allow if {
    input.caller_spiffe_id in data.allowed_callers[input.callee_spiffe_id]
}

reason := "allowlist" if {
    input.caller_spiffe_id in data.allowed_callers[input.callee_spiffe_id]
}

# Rule 3: Capability-specific permissions
allow if {
    input.action in data.capabilities[input.caller_spiffe_id]
}

reason := "capability_grant" if {
    input.action in data.capabilities[input.caller_spiffe_id]
}
```

### Policy Data

**data.json**:
```json
{
  "allowed_callers": {
    "spiffe://agentweave.io/agent/data-processor/prod": [
      "spiffe://agentweave.io/agent/orchestrator/prod",
      "spiffe://agentweave.io/agent/api-gateway/prod"
    ]
  },
  "capabilities": {
    "spiffe://agentweave.io/agent/orchestrator/prod": [
      "process",
      "query",
      "health_check"
    ],
    "spiffe://agentweave.io/agent/api-gateway/prod": [
      "query",
      "health_check"
    ]
  }
}
```

### Loading Policies

```bash
# Load policy
curl -X PUT http://localhost:8181/v1/policies/authz \
  --data-binary @authz.rego

# Load data
curl -X PUT http://localhost:8181/v1/data/allowed_callers \
  -H "Content-Type: application/json" \
  -d @data.json

# Test policy
curl -X POST http://localhost:8181/v1/data/agentweave/authz/allow \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "caller_spiffe_id": "spiffe://agentweave.io/agent/orchestrator/prod",
      "callee_spiffe_id": "spiffe://agentweave.io/agent/data-processor/prod",
      "action": "process"
    }
  }'
```

### OPA Bundle Service

For production, use OPA bundles:

**OPA config**:
```yaml
services:
  bundle-server:
    url: https://bundle-server.agentweave.io

bundles:
  authz:
    service: bundle-server
    resource: bundles/authz.tar.gz
    polling:
      min_delay_seconds: 10
      max_delay_seconds: 30
```

**Bundle structure**:
```
authz.tar.gz
├── .manifest
├── authz.rego
└── data.json
```

### Policy Testing

Use OPA's testing framework:

**authz_test.rego**:
```rego
package agentweave.authz

test_same_trust_domain_allowed {
    allow with input as {
        "caller_spiffe_id": "spiffe://agentweave.io/agent/a",
        "callee_spiffe_id": "spiffe://agentweave.io/agent/b",
        "action": "test"
    }
}

test_different_trust_domain_denied {
    not allow with input as {
        "caller_spiffe_id": "spiffe://evil.com/agent/attacker",
        "callee_spiffe_id": "spiffe://agentweave.io/agent/b",
        "action": "test"
    }
}
```

Run tests:
```bash
opa test . -v
```

## Kubernetes Deployment Security

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

### Service Account

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: data-processor
  namespace: agentweave
automountServiceAccountToken: false  # Don't mount unless needed
```

### Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-processor
  namespace: agentweave
spec:
  replicas: 3
  selector:
    matchLabels:
      app: data-processor
  template:
    metadata:
      labels:
        app: data-processor
    spec:
      serviceAccountName: data-processor

      # Security context (pod-level)
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
        fsGroup: 10001
        seccompProfile:
          type: RuntimeDefault

      containers:
        - name: agent
          image: hvs/data-processor:v1.0.0

          # Security context (container-level)
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            runAsUser: 10001
            capabilities:
              drop:
                - ALL

          # Resources
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"

          # Probes
          livenessProbe:
            httpGet:
              path: /health
              port: 8443
              scheme: HTTPS
            initialDelaySeconds: 10
            periodSeconds: 10

          readinessProbe:
            httpGet:
              path: /ready
              port: 8443
              scheme: HTTPS
            initialDelaySeconds: 5
            periodSeconds: 5

          # Environment
          env:
            - name: SPIFFE_ENDPOINT_SOCKET
              value: "unix:///run/spire/sockets/agent.sock"

          # Volume mounts
          volumeMounts:
            - name: spire-socket
              mountPath: /run/spire/sockets
              readOnly: true
            - name: config
              mountPath: /etc/agentweave
              readOnly: true
            - name: tmp
              mountPath: /tmp

        # OPA sidecar
        - name: opa
          image: openpolicyagent/opa:latest
          args:
            - "run"
            - "--server"
            - "--addr=localhost:8181"
            - "/policies"
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            runAsUser: 10001
            capabilities:
              drop:
                - ALL
          volumeMounts:
            - name: opa-policies
              mountPath: /policies
              readOnly: true

      volumes:
        - name: spire-socket
          hostPath:
            path: /run/spire/sockets
            type: Directory
        - name: config
          configMap:
            name: data-processor-config
        - name: opa-policies
          configMap:
            name: opa-policies
        - name: tmp
          emptyDir: {}
```

### Network Policies

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: data-processor-netpol
  namespace: agentweave
spec:
  podSelector:
    matchLabels:
      app: data-processor
  policyTypes:
    - Ingress
    - Egress

  ingress:
    # Allow from other agents in same namespace
    - from:
        - namespaceSelector:
            matchLabels:
              name: agentweave
      ports:
        - protocol: TCP
          port: 8443

    # Allow Prometheus scraping
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
      ports:
        - protocol: TCP
          port: 9090

  egress:
    # Allow to SPIRE server
    - to:
        - namespaceSelector:
            matchLabels:
              name: spire-system
      ports:
        - protocol: TCP
          port: 8081

    # Allow to other agents
    - to:
        - namespaceSelector:
            matchLabels:
              name: agentweave
      ports:
        - protocol: TCP
          port: 8443

    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53
```

## Security Best Practices

### Configuration Security

1. **Never commit secrets**: Use Kubernetes secrets or secret managers
2. **Validate configurations**: Run `agentweave validate` in CI/CD
3. **Use default deny**: `authorization.default_action: deny`
4. **Enable audit logging**: Required for security monitoring
5. **TLS 1.3 only**: `transport.tls_min_version: "1.3"`

### Runtime Security

1. **Read-only root filesystem**: Prevents tampering
2. **Non-root user**: Run as UID > 10000
3. **Drop all capabilities**: Minimal privileges
4. **Resource limits**: Prevent resource exhaustion
5. **Network policies**: Restrict network access

### Monitoring and Alerting

```yaml
# Prometheus alert rules
groups:
  - name: agentweave-security
    rules:
      - alert: AuthorizationDenied
        expr: rate(agentweave_authz_denied_total[5m]) > 10
        annotations:
          summary: "High rate of authorization denials"

      - alert: SVIDRotationFailed
        expr: agentweave_svid_rotation_errors_total > 0
        annotations:
          summary: "SVID rotation failed"

      - alert: UnauthorizedCaller
        expr: agentweave_authz_denied_total{reason="unknown_caller"} > 0
        annotations:
          summary: "Unknown caller attempted access"
```

### Incident Response

1. **Log aggregation**: Send logs to SIEM (Splunk, ELK, etc.)
2. **Audit trail**: Enable audit logging for all requests
3. **Trace requests**: Use OpenTelemetry trace IDs
4. **Revoke identities**: Use SPIRE to revoke compromised SVIDs

```bash
# Revoke compromised agent
spire-server entry delete \
  -spiffeID spiffe://agentweave.io/agent/compromised/prod

# Ban SPIFFE ID in OPA
curl -X PUT http://localhost:8181/v1/data/banned_agents \
  -d '["spiffe://agentweave.io/agent/compromised/prod"]'
```

## Compliance

### SOC 2 Requirements

- **Authentication**: mTLS with SPIFFE
- **Authorization**: OPA policy enforcement
- **Encryption**: TLS 1.3 in transit
- **Audit logging**: All requests logged
- **Access control**: Default deny, explicit allow

### HIPAA/PCI DSS

- Enable audit logging with retention
- Use TLS 1.3 only
- Implement rate limiting
- Monitor for anomalies
- Encrypt at rest (application layer)

## Security Checklist

Pre-deployment:
- [ ] SPIRE Server deployed with HA
- [ ] SPIRE Agent on all nodes
- [ ] OPA policies reviewed and tested
- [ ] Network policies configured
- [ ] Audit logging enabled
- [ ] Monitoring and alerting configured
- [ ] Secrets managed securely
- [ ] Configuration validated

Post-deployment:
- [ ] SVID rotation working
- [ ] Audit logs flowing to SIEM
- [ ] Metrics scraped by Prometheus
- [ ] Alerts firing correctly
- [ ] Network policies enforced
- [ ] No privilege escalation possible

## Further Reading

- [SPIFFE Security Best Practices](https://spiffe.io/docs/latest/spiffe-about/security/)
- [SPIRE Production Guide](https://spiffe.io/docs/latest/spire/installing/install-server/)
- [OPA Security](https://www.openpolicyagent.org/docs/latest/security/)
- [Kubernetes Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
