# AgentWeave SDK - Deployment Guide

This directory contains deployment manifests and Helm charts for the AgentWeave SDK.

## Directory Structure

```
deploy/
├── kubernetes/
│   └── base/
│       ├── namespace.yaml           # AgentWeave namespace and network policies
│       ├── spire-config.yaml        # SPIRE server and agent deployment
│       ├── opa-config.yaml          # OPA policy engine configuration
│       └── agent-template.yaml      # Agent deployment template
├── helm/
│   └── agentweave/
│       ├── Chart.yaml               # Helm chart metadata
│       ├── values.yaml              # Default configuration values
│       └── templates/               # Kubernetes resource templates
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── configmap.yaml
│           ├── serviceaccount.yaml
│           ├── spire-registration.yaml
│           ├── networkpolicy.yaml
│           ├── hpa.yaml
│           ├── pdb.yaml
│           └── _helpers.tpl
├── docker-compose.yaml              # Local development stack
└── README.md                        # This file
```

## Quick Start

### Option 1: Kubernetes with kubectl

1. **Deploy infrastructure (SPIRE + OPA)**:
   ```bash
   kubectl apply -f kubernetes/base/namespace.yaml
   kubectl apply -f kubernetes/base/spire-config.yaml
   kubectl apply -f kubernetes/base/opa-config.yaml
   ```

2. **Wait for SPIRE to be ready**:
   ```bash
   kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=spire-server -n agentweave --timeout=120s
   kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=spire-agent -n agentweave --timeout=120s
   ```

3. **Deploy an agent** (customize the template):
   ```bash
   # Copy and customize the agent template
   cp kubernetes/base/agent-template.yaml my-agent.yaml
   # Edit my-agent.yaml to set your agent name, image, etc.
   kubectl apply -f my-agent.yaml
   ```

### Option 2: Helm Chart

1. **Install infrastructure** (SPIRE + OPA):
   ```bash
   kubectl apply -f kubernetes/base/namespace.yaml
   kubectl apply -f kubernetes/base/spire-config.yaml
   kubectl apply -f kubernetes/base/opa-config.yaml
   ```

2. **Install an agent using Helm**:
   ```bash
   helm install my-agent ./helm/agentweave \
     --namespace agentweave \
     --set agent.name=my-agent \
     --set image.repository=your-registry/your-agent \
     --set image.tag=1.0.0
   ```

3. **Customize with values file**:
   ```bash
   # Create custom-values.yaml with your configuration
   helm install my-agent ./helm/agentweave \
     --namespace agentweave \
     --values custom-values.yaml
   ```

### Option 3: Docker Compose (Development)

1. **Create configuration files**:
   ```bash
   # Create required directories
   mkdir -p config/{spire,opa/policies,agents}

   # Copy example configs (create these based on kubernetes/base/ examples)
   # See the inline comments in docker-compose.yaml for required files
   ```

2. **Start the development stack**:
   ```bash
   docker-compose up -d
   ```

3. **View logs**:
   ```bash
   docker-compose logs -f
   ```

4. **Access services**:
   - SPIRE Server: http://localhost:8080
   - OPA: http://localhost:8181
   - Agent Search: https://localhost:8443
   - Prometheus: http://localhost:9093
   - Grafana: http://localhost:3000

## Customization Guide

### Kubernetes Agent Template

The `kubernetes/base/agent-template.yaml` file is a reference template. To customize:

1. **Change the agent name**:
   - Update all instances of `agentweave-example` to your agent name
   - Update the SPIFFE ID in service annotations

2. **Update the container image**:
   - Change `image: hvs/example-agent:1.0.0` to your agent image

3. **Modify capabilities**:
   - Edit the `config.yaml` section in the ConfigMap
   - Update agent capabilities, ports, and other settings

4. **Adjust resource limits**:
   - Modify `resources.requests` and `resources.limits` based on your needs

5. **Configure autoscaling**:
   - Adjust HorizontalPodAutoscaler min/max replicas
   - Modify CPU/memory thresholds

### Helm Chart Values

Key configuration options in `values.yaml`:

```yaml
# Agent identity
agent:
  name: "my-agent"
  environment: "prod"

# Container image
image:
  repository: your-registry/your-agent
  tag: 1.0.0

# Scaling
replicaCount: 2
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10

# Resources
resources:
  requests:
    memory: "256Mi"
    cpu: "100m"
  limits:
    memory: "512Mi"
    cpu: "500m"

# SPIFFE trust domain
global:
  trustDomain: "hvs.solutions"
  namespace: "agentweave"
```

## SPIRE Registration

Agents must be registered with SPIRE server to receive SVIDs. There are two approaches:

### Automatic (Helm Chart)

The Helm chart includes a registration Job that automatically creates SPIRE entries:

```bash
helm install my-agent ./helm/agentweave \
  --set spireRegistration.enabled=true
```

### Manual (kubectl)

Register agents manually with SPIRE server:

```bash
# Get SPIRE server pod
SPIRE_SERVER_POD=$(kubectl get pod -n agentweave -l app.kubernetes.io/name=spire-server -o jsonpath='{.items[0].metadata.name}')

# Create registration entry
kubectl exec -n agentweave $SPIRE_SERVER_POD -- \
  spire-server entry create \
  -spiffeID spiffe://hvs.solutions/agent/my-agent/prod \
  -parentID spiffe://hvs.solutions/k8s-node \
  -selector k8s:ns:agentweave \
  -selector k8s:sa:my-agent \
  -ttl 3600
```

## OPA Policy Configuration

Policies are stored in the `opa-default-policies` ConfigMap. To update:

1. **Edit the policy**:
   ```bash
   kubectl edit configmap opa-default-policies -n agentweave
   ```

2. **Or update from file**:
   ```bash
   kubectl create configmap opa-default-policies \
     --from-file=authz.rego=my-policy.rego \
     --dry-run=client -o yaml | kubectl apply -f -
   ```

3. **OPA sidecars will automatically reload** the policy.

## Network Security

All agents are protected by:

1. **Namespace isolation**: Agents run in `agentweave` namespace
2. **Network policies**: Restrict ingress/egress to authorized services
3. **mTLS**: All agent-to-agent communication uses mutual TLS with SPIFFE
4. **OPA authorization**: Every request is authorized before processing

To customize network policies:

```yaml
# In Helm values.yaml
networkPolicy:
  enabled: true
  ingress:
    fromAgents: true
    fromMonitoring: true
  egress:
    toAgents: true
    toSpireServer: true
```

## Monitoring and Observability

### Metrics

Agents expose Prometheus metrics on port 9090:

```yaml
# Prometheus scrape config
- job_name: 'agentweave-agents'
  kubernetes_sd_configs:
    - role: pod
      namespaces:
        names:
          - agentweave
  relabel_configs:
    - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
      action: keep
      regex: true
```

### Tracing

Configure OpenTelemetry endpoint:

```yaml
observability:
  tracing:
    enabled: true
    exporter: "otlp"
    endpoint: "http://otel-collector:4317"
```

### Logs

Agents log in JSON format. Use your preferred log aggregation:

```bash
# View agent logs
kubectl logs -n agentweave -l app.kubernetes.io/component=agent -f

# With stern (recommended)
stern -n agentweave agent
```

## Troubleshooting

### Agent can't get SVID

**Symptoms**: Agent logs show "failed to fetch SVID" errors

**Solutions**:
1. Check SPIRE agent is running:
   ```bash
   kubectl get pods -n agentweave -l app.kubernetes.io/name=spire-agent
   ```

2. Verify socket mount:
   ```bash
   kubectl exec -n agentweave <agent-pod> -- ls -la /run/spire/sockets/
   ```

3. Check SPIRE registration:
   ```bash
   kubectl exec -n agentweave <spire-server-pod> -- \
     spire-server entry show -spiffeID spiffe://hvs.solutions/agent/<your-agent>/prod
   ```

### Agent denied by OPA

**Symptoms**: Agent-to-agent calls fail with "authorization denied"

**Solutions**:
1. Check OPA logs:
   ```bash
   kubectl logs -n agentweave <agent-pod> -c opa
   ```

2. Test policy manually:
   ```bash
   curl -X POST http://localhost:8181/v1/data/hvs/authz/allow \
     -d '{"input": {"caller_spiffe_id": "...", "action": "..."}}'
   ```

3. Review policy ConfigMap:
   ```bash
   kubectl get configmap opa-default-policies -n agentweave -o yaml
   ```

### Network connectivity issues

**Symptoms**: Agents can't reach each other

**Solutions**:
1. Check NetworkPolicy:
   ```bash
   kubectl get networkpolicy -n agentweave
   ```

2. Verify service DNS:
   ```bash
   kubectl exec -n agentweave <agent-pod> -- nslookup <other-agent-service>
   ```

3. Test mTLS connection:
   ```bash
   kubectl exec -n agentweave <agent-pod> -- \
     curl -v --cacert /run/spire/certs/bundle.crt \
     https://<other-agent>:8443/health
   ```

## Production Checklist

Before deploying to production:

- [ ] Change default trust domain in `global.trustDomain`
- [ ] Use external database for SPIRE (not SQLite)
- [ ] Configure SPIRE key management (AWS KMS, GCP KMS, Vault)
- [ ] Review and customize OPA policies
- [ ] Set up persistent volumes for SPIRE server
- [ ] Configure TLS certificates for ingress
- [ ] Enable audit logging
- [ ] Set up monitoring and alerting
- [ ] Configure backup and disaster recovery
- [ ] Review resource limits and autoscaling settings
- [ ] Enable Pod Security Standards/Policies
- [ ] Configure network policies for your environment
- [ ] Set up log aggregation
- [ ] Document SPIFFE ID naming convention for your org

## Additional Resources

- [SPIRE Documentation](https://spiffe.io/docs/latest/spire/)
- [OPA Documentation](https://www.openpolicyagent.org/docs/)
- [A2A Protocol Specification](https://a2a-protocol.org/)
- [AgentWeave SDK Specification](../spec.md)

## Support

For issues and questions:
- GitHub Issues: https://github.com/hvs-solutions/hvs-agent-pathfinder/issues
- Documentation: https://hvs.solutions/docs
- Email: support@hvs.solutions
