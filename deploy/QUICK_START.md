# AgentWeave SDK - Quick Start Guide

This guide gets you up and running with AgentWeave agents in under 10 minutes.

## Prerequisites

Choose your deployment method:

### Option A: Kubernetes
- Kubernetes cluster (1.24+)
- kubectl configured
- Cluster admin permissions

### Option B: Helm
- Kubernetes cluster (1.24+)
- Helm 3.x installed
- kubectl configured

### Option C: Docker Compose
- Docker 20.10+
- Docker Compose 2.0+
- 4GB RAM available

## 5-Minute Quick Start

### Kubernetes (kubectl)

```bash
# 1. Deploy infrastructure
cd /home/aj-geddes/dev/claude-projects/hvs-agent-pathfinder/deploy
kubectl apply -f kubernetes/base/namespace.yaml
kubectl apply -f kubernetes/base/spire-config.yaml
kubectl apply -f kubernetes/base/opa-config.yaml

# 2. Wait for SPIRE to be ready (30-60 seconds)
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=spire-server -n agentweave --timeout=120s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=spire-agent -n agentweave --timeout=120s

# 3. Deploy your first agent
cp kubernetes/base/agent-template.yaml my-agent.yaml

# Edit my-agent.yaml:
# - Change "agentweave-example" to "my-agent" (all occurrences)
# - Update image to your agent image
# - Customize capabilities in ConfigMap

kubectl apply -f my-agent.yaml

# 4. Verify deployment
kubectl get pods -n agentweave
kubectl logs -n agentweave -l app.kubernetes.io/name=my-agent -f
```

### Helm

```bash
# 1. Deploy infrastructure
cd /home/aj-geddes/dev/claude-projects/hvs-agent-pathfinder/deploy
kubectl apply -f kubernetes/base/namespace.yaml
kubectl apply -f kubernetes/base/spire-config.yaml
kubectl apply -f kubernetes/base/opa-config.yaml

# 2. Wait for SPIRE
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=spire-server -n agentweave --timeout=120s

# 3. Install agent via Helm
helm install my-agent ./helm/agentweave \
  --namespace agentweave \
  --set agent.name=my-agent \
  --set agent.environment=dev \
  --set image.repository=agentweave/my-agent \
  --set image.tag=1.0.0

# 4. Verify
kubectl get pods -n agentweave -l app.kubernetes.io/instance=my-agent
helm status my-agent -n agentweave
```

### Docker Compose

```bash
# 1. Create config directories
cd /home/aj-geddes/dev/claude-projects/hvs-agent-pathfinder/deploy
mkdir -p config/{spire,opa/policies,agents}

# 2. Create minimal SPIRE server config
cat > config/spire/server.conf << 'EOF'
server {
  bind_address = "0.0.0.0"
  bind_port = "8081"
  trust_domain = "hvs.solutions"
  data_dir = "/opt/spire/data"
  log_level = "INFO"
  ca_subject {
    country = ["US"]
    organization = ["HVS"]
    common_name = "hvs.solutions"
  }
}

plugins {
  DataStore "sql" {
    plugin_data {
      database_type = "sqlite3"
      connection_string = "/opt/spire/data/datastore.sqlite3"
    }
  }
  KeyManager "disk" {
    plugin_data {
      keys_path = "/opt/spire/data/keys.json"
    }
  }
  NodeAttestor "join_token" {
    plugin_data {}
  }
}
EOF

# 3. Create minimal SPIRE agent config
cat > config/spire/agent.conf << 'EOF'
agent {
  data_dir = "/opt/spire/data"
  log_level = "INFO"
  server_address = "spire-server"
  server_port = "8081"
  socket_path = "/run/spire/sockets/agent.sock"
  trust_domain = "hvs.solutions"
  insecure_bootstrap = true
}

plugins {
  KeyManager "disk" {
    plugin_data {
      directory = "/opt/spire/data"
    }
  }
  NodeAttestor "join_token" {
    plugin_data {}
  }
  WorkloadAttestor "docker" {
    plugin_data {}
  }
}
EOF

# 4. Create OPA config
cat > config/opa/config.yaml << 'EOF'
services: []
bundles: {}
decision_logs:
  console: true
EOF

# 5. Create basic OPA policy
cat > config/opa/policies/authz.rego << 'EOF'
package hvs.authz

default allow = true  # Permissive for dev

allow {
  true
}
EOF

# 6. Create agent configs (examples)
cat > config/agents/search-agent.yaml << 'EOF'
agent:
  name: "search-agent"
  trust_domain: "hvs.solutions"
  description: "Search agent"
  capabilities:
    - name: "search"
      description: "Search capability"
      input_modes: ["application/json"]
      output_modes: ["application/json"]

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"

authorization:
  provider: "opa"
  opa_endpoint: "http://opa:8181"
  default_action: "deny"

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"

server:
  host: "0.0.0.0"
  port: 8443

observability:
  metrics:
    enabled: true
    port: 9090
  logging:
    level: "INFO"
    format: "json"
EOF

# Copy for other agents
cp config/agents/search-agent.yaml config/agents/processor-agent.yaml
cp config/agents/search-agent.yaml config/agents/orchestrator-agent.yaml

# 7. Create registration script
cat > scripts/register-agents.sh << 'EOF'
#!/bin/sh
set -e

echo "Waiting for SPIRE server..."
sleep 10

# Generate join token and register agents
TOKEN=$(spire-server token generate -spiffeID spiffe://hvs.solutions/agent/workload)

echo "Agents can use token: $TOKEN"
echo "Registration complete"
EOF

chmod +x scripts/register-agents.sh

# 8. Start the stack
docker-compose up -d

# 9. View logs
docker-compose logs -f

# 10. Access services
# - Agent Search: https://localhost:8443
# - OPA: http://localhost:8181
# - Prometheus: http://localhost:9093
# - Grafana: http://localhost:3000 (admin/admin)
```

## Common First Tasks

### Register Agent with SPIRE (Kubernetes)

```bash
# Get SPIRE server pod
SPIRE_POD=$(kubectl get pod -n agentweave -l app.kubernetes.io/name=spire-server -o jsonpath='{.items[0].metadata.name}')

# Create entry
kubectl exec -n agentweave $SPIRE_POD -- \
  spire-server entry create \
  -spiffeID spiffe://hvs.solutions/agent/my-agent/dev \
  -parentID spiffe://hvs.solutions/k8s-node \
  -selector k8s:ns:agentweave \
  -selector k8s:sa:my-agent

# Verify
kubectl exec -n agentweave $SPIRE_POD -- \
  spire-server entry show -spiffeID spiffe://hvs.solutions/agent/my-agent/dev
```

### Test Agent Health

```bash
# Kubernetes
kubectl port-forward -n agentweave svc/my-agent 8443:8443
curl -k https://localhost:8443/health/live

# Docker Compose
curl -k https://localhost:8443/health/live
```

### View Agent Logs

```bash
# Kubernetes
kubectl logs -n agentweave -l app.kubernetes.io/name=my-agent -f

# Docker Compose
docker-compose logs -f agent-search
```

### Check OPA Policies

```bash
# Kubernetes
kubectl port-forward -n agentweave svc/opa-bundle-server 8888:8080
curl http://localhost:8888/bundles/

# Docker Compose
curl http://localhost:8181/v1/data/hvs/authz
```

### View Metrics

```bash
# Kubernetes
kubectl port-forward -n agentweave svc/my-agent 9090:9090
curl http://localhost:9090/metrics

# Docker Compose (via Prometheus)
open http://localhost:9093
```

## Next Steps

1. **Customize Your Agent**:
   - Edit agent configuration
   - Add capabilities
   - Implement business logic

2. **Configure Security**:
   - Review OPA policies
   - Adjust network policies
   - Set resource limits

3. **Enable Monitoring**:
   - Configure Prometheus
   - Set up dashboards
   - Create alerts

4. **Deploy to Production**:
   - Use production trust domain
   - Enable external database for SPIRE
   - Configure backups
   - Set up CI/CD

## Troubleshooting

### Agent won't start

**Check SPIRE socket**:
```bash
kubectl exec -n agentweave <pod> -- ls -la /run/spire/sockets/
```

**Check SPIRE agent logs**:
```bash
kubectl logs -n agentweave -l app.kubernetes.io/name=spire-agent
```

### Can't communicate between agents

**Check network policy**:
```bash
kubectl get networkpolicy -n agentweave
```

**Test DNS resolution**:
```bash
kubectl exec -n agentweave <pod> -- nslookup other-agent
```

### OPA denying requests

**Check OPA logs**:
```bash
kubectl logs -n agentweave <pod> -c opa
```

**Test policy**:
```bash
kubectl port-forward -n agentweave svc/opa-bundle-server 8181:8080
curl -X POST http://localhost:8181/v1/data/hvs/authz/allow \
  -d '{"input": {"caller_spiffe_id": "spiffe://hvs.solutions/agent/test"}}'
```

## Support

- **Full Documentation**: See `/home/aj-geddes/dev/claude-projects/hvs-agent-pathfinder/deploy/README.md`
- **Detailed Summary**: See `/home/aj-geddes/dev/claude-projects/hvs-agent-pathfinder/deploy/DEPLOYMENT_SUMMARY.md`
- **Product Spec**: See `/home/aj-geddes/dev/claude-projects/hvs-agent-pathfinder/spec.md`

---

**Happy Building!**
