---
layout: page
title: Deployment
description: Deploy AgentWeave agents to production environments
nav_order: 6
has_children: true
---

# Deployment Overview

This section covers deploying AgentWeave agents to various production environments, from containers to cloud platforms.

## Deployment Options

AgentWeave supports multiple deployment strategies to fit your infrastructure:

| Deployment Target | Best For | Complexity | Documentation |
|------------------|----------|------------|---------------|
| **Docker** | Development, simple deployments | Low | [Docker Guide](docker.md) |
| **Kubernetes** | Production, scalable deployments | Medium | [Kubernetes Guide](kubernetes.md) |
| **Helm** | Kubernetes with templating | Medium | [Helm Guide](helm.md) |
| **AWS** | AWS-native deployments | Medium-High | [AWS Guide](aws.md) |
| **GCP** | GCP-native deployments | Medium-High | [GCP Guide](gcp.md) |
| **Azure** | Azure-native deployments | Medium-High | [Azure Guide](azure.md) |
| **Hybrid/Multi-Cloud** | Cross-cloud architectures | High | [Hybrid Guide](hybrid.md) |

## Prerequisites

Before deploying AgentWeave agents, ensure you have:

### Required Infrastructure

1. **SPIRE Infrastructure**
   - SPIRE Server (central identity authority)
   - SPIRE Agent (on each node/container)
   - Configured trust domain
   - Registration entries for workloads

2. **OPA Infrastructure**
   - OPA server or sidecar
   - Authorization policies loaded
   - Policy bundles (optional)

3. **Network Connectivity**
   - mTLS-capable network
   - DNS or service discovery
   - Firewall rules for agent communication

### Optional Components

- **Tailscale**: For simplified cross-cloud networking
- **Prometheus**: For metrics collection
- **Jaeger/Zipkin**: For distributed tracing
- **ELK/Loki**: For centralized logging

## Architecture Patterns

### Pattern 1: Sidecar Model (Recommended)

Each agent pod runs with SPIRE and OPA sidecars:

```
┌─────────────────────────────────┐
│         Agent Pod               │
│  ┌──────────────────────────┐   │
│  │  Agent Container         │   │
│  │  (Your Application)      │   │
│  └──────────┬───────────────┘   │
│             │                   │
│  ┌──────────┴───────────────┐   │
│  │  SPIRE Agent Sidecar     │   │
│  └──────────┬───────────────┘   │
│             │                   │
│  ┌──────────┴───────────────┐   │
│  │  OPA Sidecar             │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

**Pros**:
- Strong isolation between agents
- Independent scaling per agent
- Minimal shared infrastructure

**Cons**:
- Higher resource usage
- More complex configuration

### Pattern 2: DaemonSet Model

SPIRE Agent runs as DaemonSet, shared by all agents on node:

```
┌─────────────────────────────────┐
│           Node                  │
│  ┌──────────┐  ┌──────────┐     │
│  │ Agent 1  │  │ Agent 2  │     │
│  │  + OPA   │  │  + OPA   │     │
│  └────┬─────┘  └─────┬────┘     │
│       │              │          │
│       └──────┬───────┘          │
│              │                  │
│  ┌───────────┴──────────────┐   │
│  │  SPIRE Agent (DaemonSet) │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

**Pros**:
- Efficient resource usage
- Simplified SPIRE management
- Faster pod startup

**Cons**:
- SPIRE Agent is shared resource
- Node-level failure affects all agents

### Pattern 3: Centralized OPA

Central OPA cluster for all authorization decisions:

```
┌──────────┐  ┌──────────┐  ┌──────────┐
│ Agent 1  │  │ Agent 2  │  │ Agent 3  │
└────┬─────┘  └─────┬────┘  └─────┬────┘
     │              │              │
     └──────────────┼──────────────┘
                    │
         ┌──────────┴───────────┐
         │   OPA Cluster        │
         │  (HA, Load Balanced) │
         └──────────────────────┘
```

**Pros**:
- Centralized policy management
- Reduced per-agent overhead
- Easier policy updates

**Cons**:
- Network dependency for authz
- Potential bottleneck
- Higher latency

## Security Considerations

### Production Security Checklist

Before deploying to production, verify:

- [ ] SPIRE trust domain is properly configured
- [ ] SPIRE registration entries use restrictive selectors
- [ ] OPA policies default to deny
- [ ] TLS 1.3 is enforced (minimum 1.2)
- [ ] Peer verification is set to "strict"
- [ ] Audit logging is enabled
- [ ] Secrets are stored in vault/secret manager
- [ ] Network policies restrict agent communication
- [ ] Resource limits are set on containers
- [ ] Health checks are configured
- [ ] Monitoring and alerting are active

### Common Security Pitfalls

1. **Overly Permissive SPIRE Selectors**
   ```bash
   # BAD: Too broad
   spire-server entry create \
     -spiffeID spiffe://example.com/agent/my-agent \
     -selector k8s:ns:default

   # GOOD: Specific
   spire-server entry create \
     -spiffeID spiffe://example.com/agent/my-agent \
     -selector k8s:ns:production \
     -selector k8s:sa:my-agent \
     -selector k8s:pod-label:app:my-agent
   ```

2. **Weak OPA Policies**
   ```rego
   # BAD: Allows everything
   package agentweave.authz
   default allow = true

   # GOOD: Explicit allow rules
   package agentweave.authz
   default allow = false

   allow {
       input.caller_spiffe_id == "spiffe://example.com/agent/orchestrator"
       input.action == "search"
   }
   ```

3. **Disabling Peer Verification**
   ```yaml
   # BAD: Don't do this in production
   transport:
     peer_verification: "none"

   # GOOD: Always verify
   transport:
     peer_verification: "strict"
   ```

## Environment-Specific Guides

Choose your deployment target:

### Container Platforms

- **[Docker Deployment](docker.md)** - Containers, Docker Compose, local development
- **[Kubernetes Deployment](kubernetes.md)** - Production Kubernetes deployments
- **[Helm Charts](helm.md)** - Templated Kubernetes deployments

### Cloud Providers

- **[AWS Deployment](aws.md)** - EKS, ECS, IAM, Secrets Manager
- **[GCP Deployment](gcp.md)** - GKE, Workload Identity, Secret Manager
- **[Azure Deployment](azure.md)** - AKS, Pod Identity, Key Vault

### Advanced Scenarios

- **[Hybrid/Multi-Cloud](hybrid.md)** - Cross-cloud, SPIFFE federation, Tailscale

## Quick Start by Environment

### Local Development (5 minutes)

```bash
# Clone starter template
git clone https://github.com/aj-geddes/agentweave-starter.git
cd agentweave-starter

# Start infrastructure
docker-compose up -d

# Deploy your agent
docker-compose up agent-search
```

See [Docker Guide](docker.md) for details.

### Kubernetes Production (30 minutes)

```bash
# Install SPIRE
kubectl apply -f https://github.com/aj-geddes/agentweave/releases/latest/download/spire.yaml

# Install OPA
kubectl apply -f https://github.com/aj-geddes/agentweave/releases/latest/download/opa.yaml

# Deploy agent with Helm
helm install my-agent agentweave/agentweave \
  --set agent.name=my-agent \
  --set spiffe.trustDomain=example.com
```

See [Kubernetes Guide](kubernetes.md) for details.

### AWS EKS (1 hour)

```bash
# Create EKS cluster with Terraform
terraform apply

# Install SPIRE with OIDC federation
kubectl apply -f manifests/spire-aws.yaml

# Deploy agent with IAM roles
helm install my-agent agentweave/agentweave \
  --set cloud.provider=aws \
  --set aws.iamRole=arn:aws:iam::123456789012:role/my-agent
```

See [AWS Guide](aws.md) for details.

## Resource Requirements

### Minimum Requirements (Per Agent)

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| Agent Container | 100m | 128Mi | 1Gi |
| SPIRE Agent (sidecar) | 50m | 64Mi | 100Mi |
| OPA (sidecar) | 50m | 64Mi | 100Mi |
| **Total** | **200m** | **256Mi** | **~1.2Gi** |

### Recommended Production

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| Agent Container | 500m | 512Mi | 10Gi |
| SPIRE Agent (sidecar) | 100m | 128Mi | 1Gi |
| OPA (sidecar) | 100m | 128Mi | 1Gi |
| **Total** | **700m** | **768Mi** | **~12Gi** |

### Scaling Considerations

- **Horizontal Scaling**: Add more agent replicas for throughput
- **Vertical Scaling**: Increase resources for complex workloads
- **SPIRE Server**: 2-4 CPU, 4-8Gi memory for 1000+ workloads
- **OPA**: Consider centralized cluster for 50+ agents

## Monitoring and Observability

All deployment guides include setup for:

- **Metrics**: Prometheus endpoints on port 9090
- **Traces**: OpenTelemetry OTLP export
- **Logs**: Structured JSON to stdout
- **Health Checks**: Liveness and readiness probes

Example Prometheus scrape config:

```yaml
scrape_configs:
  - job_name: 'agentweave-agents'
    kubernetes_sd_configs:
      - role: pod
    relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        regex: agentweave-agent
        action: keep
      - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
        action: keep
        regex: true
```

## Troubleshooting

Common deployment issues and solutions:

### SPIRE Agent Connection Failed

```bash
# Check SPIRE Agent socket
kubectl exec -it my-agent-pod -c agent -- ls -l /run/spire/sockets/

# Verify SPIRE Agent is running
kubectl get pods -l app=spire-agent

# Check SPIRE Agent logs
kubectl logs -l app=spire-agent -f
```

### OPA Policy Denied

```bash
# Test policy locally
agentweave authz check \
  --caller spiffe://example.com/agent/caller \
  --callee spiffe://example.com/agent/callee \
  --action search

# Check OPA logs
kubectl logs -l app=opa -f

# Validate policy syntax
opa test policies/
```

### Agent Not Getting SVID

```bash
# Check SPIRE registration entry
spire-server entry show -spiffeID spiffe://example.com/agent/my-agent

# Verify selectors match pod
kubectl get pod my-agent-pod -o yaml | grep -A 10 metadata

# Check SPIRE Agent attestation
kubectl logs -l app=spire-agent | grep attestation
```

## Next Steps

1. Choose your deployment environment from the guides above
2. Review [Security Best Practices](../security.md)
3. Set up [Monitoring and Observability](../guides/observability.md)
4. Plan your [High Availability](../guides/ha.md) strategy

---

**Related Documentation**:
- [Configuration Reference](../configuration.md)
- [Security Guide](../security.md)
- [Operations Guide](../guides/operations.md)
