# AgentWeave SDK - Deployment Manifests Summary

## Overview

This deployment package provides production-ready Kubernetes manifests, Helm charts, and Docker Compose configurations for the AgentWeave SDK. All configurations follow security best practices with SPIFFE/SPIRE for identity and OPA for authorization.

## Files Created

### Kubernetes Base Manifests (`kubernetes/base/`)

#### 1. namespace.yaml
**Purpose**: Creates the AgentWeave agents namespace with security isolation

**Key Features**:
- Creates `agentweave` namespace with proper labels
- Default deny network policy for external traffic
- Allow agent-to-agent communication within namespace
- DNS access enabled for service discovery

**Usage**:
```bash
kubectl apply -f kubernetes/base/namespace.yaml
```

#### 2. spire-config.yaml
**Purpose**: Complete SPIRE server and agent deployment

**Components**:
- **SPIRE Server StatefulSet**: Manages workload identities (trust domain: hvs.solutions)
- **SPIRE Agent DaemonSet**: Runs on every node, provides Workload API via Unix socket
- **ConfigMaps**: Server and agent configuration with Kubernetes attestation
- **Services**: SPIRE server gRPC endpoint (port 8081)
- **RBAC**: ClusterRole and bindings for Kubernetes API access
- **ServiceAccounts**: For SPIRE server and agent pods

**Key Configuration**:
- Trust domain: `hvs.solutions` (customizable)
- Node attestation: Kubernetes PSAT (Projected Service Account Token)
- Workload attestation: Kubernetes pod metadata (namespace, service account, labels)
- Socket path: `/run/spire/sockets/agent.sock`
- SVID TTL: 1 hour (auto-rotates at 30 minutes)

**Usage**:
```bash
kubectl apply -f kubernetes/base/spire-config.yaml
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=spire-server -n agentweave
```

#### 3. opa-config.yaml
**Purpose**: OPA policy engine for authorization

**Components**:
- **Default Policies ConfigMap**: Rego policies for SPIFFE-based authorization
- **OPA Bundle Server**: Nginx-based policy distribution (port 8080)
- **Policy Configuration**: Runtime config for policy loading and decision logging
- **Network Policies**: Restrict OPA sidecar communication

**Policy Features**:
- Default deny with explicit allow rules
- Same trust domain validation
- Federated domain support
- Action-based authorization
- Detailed audit logging

**Usage**:
```bash
kubectl apply -f kubernetes/base/opa-config.yaml
```

#### 4. agent-template.yaml
**Purpose**: Complete reference template for deploying agents

**Components**:
- **ServiceAccount**: For Kubernetes RBAC and SPIRE attestation
- **ConfigMap**: Agent configuration (HVS SDK config.yaml)
- **Deployment**: Multi-container pod with agent + OPA sidecar
- **Service**: ClusterIP service for agent-to-agent communication
- **NetworkPolicy**: Restrict traffic to authorized services only
- **HorizontalPodAutoscaler**: Auto-scaling based on CPU/memory
- **PodDisruptionBudget**: High availability during maintenance

**Security Features**:
- Read-only root filesystem
- Non-root user (UID 1000)
- Dropped capabilities (ALL)
- No privilege escalation
- Seccomp profile enabled
- Init container waits for SPIRE socket
- mTLS enforced via SPIFFE

**Container Structure**:
1. Init: `wait-for-spire` - Ensures SPIRE agent socket is ready
2. Main: `agent` - Your HVS agent application
3. Sidecar: `opa` - Policy enforcement engine

**Usage**:
```bash
# Customize the template for your agent
cp kubernetes/base/agent-template.yaml my-search-agent.yaml
# Edit: change name, image, capabilities, etc.
kubectl apply -f my-search-agent.yaml
```

### Helm Chart (`helm/agentweave/`)

#### 5. Chart.yaml
**Purpose**: Helm chart metadata and dependencies

**Details**:
- Chart version: 1.0.0
- App version: 1.0.0
- Type: Application
- Maintainer: High Velocity Solutions
- License: Apache-2.0

**Keywords**: hvs, agent, spiffe, spire, opa, security, ai, multi-agent, a2a

#### 6. values.yaml
**Purpose**: Default configuration values for the Helm chart

**Key Sections**:

1. **Global Settings**:
   - Trust domain: `hvs.solutions`
   - Namespace: `agentweave`
   - Image pull secrets

2. **Agent Configuration**:
   - Name, environment, description
   - A2A capabilities definition
   - Custom labels and annotations

3. **Image Configuration**:
   - Repository, tag, pull policy
   - Defaults to chart appVersion

4. **SPIFFE/SPIRE**:
   - Socket path: `/run/spire/sockets/agent.sock`
   - Allowed trust domains
   - Registration selectors (namespace, service account, labels)

5. **OPA Configuration**:
   - Sidecar enabled by default
   - Bundle server integration
   - Resource limits (128Mi/256Mi, 50m/200m CPU)

6. **Transport/Security**:
   - TLS 1.3 minimum
   - Strict peer verification
   - Connection pooling, circuit breaker, retry logic

7. **Observability**:
   - Prometheus metrics (port 9090)
   - OpenTelemetry tracing
   - JSON logging

8. **Autoscaling**:
   - HPA: 2-10 replicas
   - Target: 70% CPU, 80% memory
   - Scale down stabilization: 5 minutes

9. **Security Contexts**:
   - Pod: non-root, fsGroup 1000
   - Container: read-only filesystem, dropped capabilities

**Customization Example**:
```yaml
# custom-values.yaml
agent:
  name: "search-agent"
  environment: "prod"

image:
  repository: myregistry/search-agent
  tag: "2.1.0"

resources:
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

#### 7. templates/deployment.yaml
**Purpose**: Kubernetes Deployment with templated values

**Features**:
- Checksum annotation for config changes (auto-restart)
- Conditional SPIRE init container
- OPA sidecar if enabled
- Environment variable injection (Pod IP, name, namespace)
- Extra volumes/mounts support
- Health checks (liveness/readiness)
- Resource limits from values
- Node selector, affinity, tolerations

#### 8. templates/service.yaml
**Purpose**: ClusterIP service for agent discovery

**Features**:
- SPIFFE ID in service annotation
- HTTPS port (8443) and metrics port (9090)
- Customizable labels and annotations

#### 9. templates/configmap.yaml
**Purpose**: Agent configuration from Helm values

**Generated Sections**:
- Agent identity and capabilities
- SPIFFE/OPA endpoints
- Transport settings (TLS, connection pool, circuit breaker)
- Server configuration
- Observability settings

**Template Logic**:
- Conditionally includes SPIFFE/OPA config based on enabled flags
- Merges custom config data from values

#### 10. templates/serviceaccount.yaml
**Purpose**: ServiceAccount for RBAC and SPIRE attestation

**Features**:
- Conditional creation
- Custom name or generated from chart name
- Annotations support

#### 11. templates/spire-registration.yaml
**Purpose**: Automatic SPIRE registration via Helm hook

**How It Works**:
1. Runs as post-install/post-upgrade Job
2. Connects to SPIRE server via socket
3. Checks if entry exists
4. Creates registration entry with selectors
5. Cleans up after 5 minutes

**Selectors**:
- Kubernetes namespace
- Service account
- Pod labels
- DNS names (optional)
- Federated domains (optional)

**ConfigMap**:
- Stores SPIFFE ID and registration info for reference

#### 12. templates/networkpolicy.yaml
**Purpose**: Restrict network access to authorized services

**Ingress Rules**:
- Allow from other agents (port 8443)
- Allow from monitoring namespace (port 9090)

**Egress Rules**:
- Allow to other agents
- Allow to SPIRE server (port 8081)
- Allow to OPA bundle server (port 8080)
- Allow to OpenTelemetry collector (port 4317)
- Allow DNS queries (port 53)

#### 13. templates/hpa.yaml
**Purpose**: Horizontal Pod Autoscaler for dynamic scaling

**Features**:
- CPU and memory-based scaling
- Configurable min/max replicas
- Scale down/up behavior policies
- Stabilization windows to prevent flapping

#### 14. templates/pdb.yaml
**Purpose**: Pod Disruption Budget for high availability

**Features**:
- Ensures minimum pods available during disruptions
- Supports minAvailable or maxUnavailable

#### 15. templates/_helpers.tpl
**Purpose**: Helm template helper functions

**Functions**:
- `agentweave.name`: Chart name
- `agentweave.fullname`: Full resource name
- `agentweave.chart`: Chart name and version
- `agentweave.labels`: Common labels
- `agentweave.selectorLabels`: Pod selector labels
- `agentweave.serviceAccountName`: ServiceAccount name resolution
- `agentweave.configMapName`: ConfigMap name resolution
- `agentweave.spiffeId`: Generate SPIFFE ID from values

### Docker Compose (`docker-compose.yaml`)

#### 16. docker-compose.yaml
**Purpose**: Complete local development stack

**Services**:

1. **spire-server** (172.28.0.10):
   - SPIRE server for identity management
   - Ports: 8081 (API), 8080 (health)
   - Volume: Persistent data storage

2. **spire-agent** (172.28.0.11):
   - SPIRE agent providing Workload API
   - Socket: `/run/spire/sockets/agent.sock`
   - Depends on: spire-server

3. **opa** (172.28.0.20):
   - OPA policy engine
   - Port: 8181
   - Volume: Policy files

4. **opa-bundle-server** (172.28.0.21):
   - Nginx serving policy bundles
   - Port: 8888 (external)

5. **agent-search** (172.28.0.100):
   - Example search agent
   - Ports: 8443 (HTTPS), 9090 (metrics)
   - SPIFFE ID: `spiffe://hvs.solutions/agent/search/dev`

6. **agent-processor** (172.28.0.101):
   - Example processor agent
   - Ports: 8444 (HTTPS), 9091 (metrics)
   - SPIFFE ID: `spiffe://hvs.solutions/agent/processor/dev`

7. **agent-orchestrator** (172.28.0.102):
   - Example orchestrator agent
   - Ports: 8445 (HTTPS), 9092 (metrics)
   - SPIFFE ID: `spiffe://hvs.solutions/agent/orchestrator/dev`
   - Connects to: agent-search, agent-processor

8. **prometheus** (172.28.0.30):
   - Metrics collection
   - Port: 9093

9. **grafana** (172.28.0.31):
   - Visualization dashboard
   - Port: 3000
   - Default credentials: admin/admin

10. **spire-registration**:
    - One-time registration job
    - Registers all agents with SPIRE server

**Network**:
- Custom bridge network: 172.28.0.0/16
- Static IPs for service discovery

**Volumes**:
- `spire-server-data`: Persistent SPIRE data
- `spire-agent-socket`: Shared Workload API socket
- `opa-data`: OPA cache

**Usage**:
```bash
docker-compose up -d
docker-compose logs -f agent-search
docker-compose exec spire-server spire-server entry show
docker-compose down
```

### Documentation (`README.md`)

#### 17. README.md
**Purpose**: Complete deployment guide

**Sections**:
1. Directory structure overview
2. Quick start guides (kubectl, Helm, Docker Compose)
3. Customization instructions
4. SPIRE registration procedures
5. OPA policy management
6. Network security configuration
7. Monitoring and observability setup
8. Troubleshooting guide
9. Production deployment checklist
10. Additional resources and support

## Deployment Patterns

### Pattern 1: Kubernetes with kubectl

**Use Case**: Direct control, no Helm required

**Steps**:
1. Deploy infrastructure (namespace, SPIRE, OPA)
2. Customize agent template for each agent
3. Apply manifests
4. Manually register with SPIRE

**Pros**:
- No Helm dependency
- Full control over resources
- Easy to understand and debug

**Cons**:
- Manual updates
- More repetitive configuration
- No built-in upgrade path

### Pattern 2: Helm Chart

**Use Case**: Production deployments, multiple agents

**Steps**:
1. Deploy infrastructure (namespace, SPIRE, OPA)
2. Install agents via Helm with custom values
3. Automatic SPIRE registration
4. Easy upgrades and rollbacks

**Pros**:
- Templated configuration
- Easy upgrades (`helm upgrade`)
- Automatic SPIRE registration
- Values file for environment-specific config

**Cons**:
- Requires Helm knowledge
- More abstraction layers

### Pattern 3: Docker Compose

**Use Case**: Local development and testing

**Steps**:
1. Create configuration files
2. Start stack with `docker-compose up`
3. Access agents via localhost

**Pros**:
- Complete local environment
- No Kubernetes required
- Fast iteration
- Includes monitoring stack

**Cons**:
- Not for production
- Different from production setup
- Limited scalability

## Security Architecture

### Defense in Depth

1. **Network Layer**:
   - Namespace isolation
   - NetworkPolicies (default deny)
   - Only authorized ingress/egress

2. **Identity Layer**:
   - SPIFFE cryptographic identity
   - Automatic certificate rotation
   - No static credentials

3. **Authentication Layer**:
   - Mutual TLS (mTLS) enforced
   - TLS 1.3 minimum
   - Peer verification required

4. **Authorization Layer**:
   - OPA policy enforcement
   - Default deny
   - Audit logging

5. **Container Layer**:
   - Read-only root filesystem
   - Non-root user
   - Dropped capabilities
   - Seccomp profile

6. **Pod Layer**:
   - Security contexts
   - Pod Security Standards
   - Resource limits

## Configuration Summary

### Key Customization Points

1. **Trust Domain**: Change `hvs.solutions` to your organization
2. **Namespace**: Modify `agentweave` if needed
3. **Agent Names**: Unique per agent deployment
4. **Resource Limits**: Adjust based on workload
5. **Autoscaling**: Configure min/max replicas
6. **OPA Policies**: Customize authorization rules
7. **Network Policies**: Adjust for your environment
8. **Monitoring**: Configure Prometheus, tracing endpoints

### Environment-Specific Values

**Development**:
```yaml
replicaCount: 1
autoscaling.enabled: false
debug.enabled: true
observability.logging.level: "DEBUG"
```

**Staging**:
```yaml
replicaCount: 2
autoscaling.enabled: true
autoscaling.minReplicas: 2
autoscaling.maxReplicas: 5
observability.logging.level: "INFO"
```

**Production**:
```yaml
replicaCount: 3
autoscaling.enabled: true
autoscaling.minReplicas: 3
autoscaling.maxReplicas: 20
podDisruptionBudget.enabled: true
observability.logging.level: "WARN"
resources.limits.memory: "1Gi"
```

## Integration Points

### With SPIRE
- Socket: `/run/spire/sockets/agent.sock`
- Registration: Automatic via Helm Job or manual via spire-server CLI
- Attestation: Kubernetes namespace + service account + labels

### With OPA
- Endpoint: `http://localhost:8181` (sidecar)
- Bundle Server: `http://opa-bundle-server:8080`
- Policy Path: `hvs/authz`
- Decision Logging: Enabled by default

### With Prometheus
- Port: 9090
- Path: `/metrics`
- Scrape Interval: Configured in Prometheus

### With OpenTelemetry
- Endpoint: Configurable (default: `http://otel-collector:4317`)
- Protocol: OTLP/gRPC
- Traces: Enabled by default

## Next Steps

1. **Deploy Infrastructure**:
   ```bash
   kubectl apply -f kubernetes/base/namespace.yaml
   kubectl apply -f kubernetes/base/spire-config.yaml
   kubectl apply -f kubernetes/base/opa-config.yaml
   ```

2. **Deploy Your First Agent**:
   ```bash
   helm install my-agent ./helm/agentweave \
     --namespace agentweave \
     --set agent.name=my-agent \
     --set image.repository=your-registry/your-agent
   ```

3. **Verify Deployment**:
   ```bash
   kubectl get all -n agentweave
   kubectl logs -n agentweave -l app.kubernetes.io/name=my-agent -f
   ```

4. **Test Agent Communication**:
   ```bash
   kubectl exec -n agentweave <pod> -- curl -k https://localhost:8443/health
   ```

## Production Readiness

Before going to production, ensure:

- [ ] Trust domain customized for your organization
- [ ] SPIRE using external database (PostgreSQL/MySQL)
- [ ] SPIRE using cloud KMS for key management
- [ ] OPA policies reviewed and tested
- [ ] Resource limits tuned for workload
- [ ] Monitoring and alerting configured
- [ ] Log aggregation set up
- [ ] Backup and disaster recovery planned
- [ ] Security scanning integrated in CI/CD
- [ ] Network policies validated
- [ ] Certificate management automated

## Support and Resources

- **Product Specification**: `/home/aj-geddes/dev/claude-projects/hvs-agent-pathfinder/spec.md`
- **Deployment Guide**: `/home/aj-geddes/dev/claude-projects/hvs-agent-pathfinder/deploy/README.md`
- **SPIRE Documentation**: https://spiffe.io/docs/
- **OPA Documentation**: https://www.openpolicyagent.org/docs/
- **A2A Protocol**: https://a2a-protocol.org/

---

**Generated**: 2025-12-06
**Version**: 1.0.0
**Author**: High Velocity Solutions LLC
