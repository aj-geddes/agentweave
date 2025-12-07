---
layout: tutorial
title: Deploying to Kubernetes
permalink: /tutorials/kubernetes-deployment/
nav_order: 6
parent: Tutorials
difficulty: Advanced
duration: 60 minutes
---

# Deploying to Kubernetes

In this tutorial, you'll deploy AgentWeave agents to Kubernetes with SPIRE, OPA, and full observability. You'll learn production-ready configurations, health checks, and scaling strategies.

## Learning Objectives

By completing this tutorial, you will:
- Install and configure SPIRE on Kubernetes
- Deploy OPA for policy enforcement
- Create production-ready agent deployments
- Configure ConfigMaps and Secrets
- Implement health checks and probes
- Set up horizontal pod autoscaling
- Use Helm charts for deployment

## Prerequisites

Before starting, ensure you have:
- **Kubernetes cluster** (local or cloud) - Minikube, Kind, GKE, EKS, or AKS
- **kubectl installed** and configured
- **Helm 3 installed**
- **Completed intermediate tutorials** - Understanding of agents and policies
- **Understanding of Kubernetes** - Pods, Deployments, Services, ConfigMaps

**Time estimate:** 60 minutes

## Architecture Overview

```
┌─────────────────────────────────────────────────┐
│              Kubernetes Cluster                  │
│                                                  │
│  ┌───────────────┐        ┌──────────────┐     │
│  │  SPIRE Server │        │     OPA      │     │
│  │  (StatefulSet)│        │  (Deployment)│     │
│  └───────┬───────┘        └──────┬───────┘     │
│          │                       │              │
│  ┌───────▼────────────────────────▼──────────┐ │
│  │        SPIRE Agent (DaemonSet)            │ │
│  └───────┬──────────────────────┬────────────┘ │
│          │                      │               │
│  ┌───────▼──────┐      ┌────────▼──────┐      │
│  │ Agent Pod 1  │      │ Agent Pod 2   │      │
│  │  - Agent     │      │  - Agent      │      │
│  │  - SPIRE     │      │  - SPIRE      │      │
│  └──────────────┘      └───────────────┘      │
│                                                 │
│  ┌─────────────────────────────────┐           │
│  │  Observability Stack             │           │
│  │  - Prometheus                    │           │
│  │  - Grafana                       │           │
│  │  - Jaeger                        │           │
│  └─────────────────────────────────┘           │
└─────────────────────────────────────────────────┘
```

## Step 1: Set Up Your Kubernetes Cluster

### Option A: Local Development (Minikube)

```bash
# Install minikube
# macOS
brew install minikube

# Linux
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Start cluster
minikube start --cpus=4 --memory=8192

# Verify
kubectl cluster-info
```

### Option B: Local Development (Kind)

```bash
# Install kind
brew install kind  # macOS
# Or: GO111MODULE=on go install sigs.k8s.io/kind@latest

# Create cluster
cat <<EOF | kind create cluster --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
- role: control-plane
- role: worker
- role: worker
EOF

# Verify
kubectl get nodes
```

### Option C: Cloud Provider

**Google GKE:**
```bash
gcloud container clusters create agentweave-cluster \
  --zone=us-central1-a \
  --num-nodes=3 \
  --machine-type=e2-standard-4
```

**AWS EKS:**
```bash
eksctl create cluster \
  --name agentweave-cluster \
  --region us-west-2 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3
```

**Azure AKS:**
```bash
az aks create \
  --resource-group agentweave-rg \
  --name agentweave-cluster \
  --node-count 3 \
  --node-vm-size Standard_D2s_v3
```

## Step 2: Install SPIRE on Kubernetes

SPIRE provides cryptographic identity for agents.

### Create Namespace

```bash
kubectl create namespace spire
```

### Install SPIRE Server

Create `spire-server.yaml`:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spire-server
  namespace: spire
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: spire-server-cluster-role
rules:
- apiGroups: [""]
  resources: ["nodes"]
  verbs: ["get"]
- apiGroups: ["authentication.k8s.io"]
  resources: ["tokenreviews"]
  verbs: ["create"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: spire-server-cluster-role-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: spire-server-cluster-role
subjects:
- kind: ServiceAccount
  name: spire-server
  namespace: spire
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: spire-server
  namespace: spire
data:
  server.conf: |
    server {
      bind_address = "0.0.0.0"
      bind_port = "8081"
      trust_domain = "example.org"
      data_dir = "/run/spire/data"
      log_level = "INFO"
      ca_ttl = "168h"
      default_svid_ttl = "1h"
    }

    plugins {
      DataStore "sql" {
        plugin_data {
          database_type = "sqlite3"
          connection_string = "/run/spire/data/datastore.sqlite3"
        }
      }

      NodeAttestor "k8s_psat" {
        plugin_data {
          clusters = {
            "agentweave-cluster" = {
              service_account_allow_list = ["spire:spire-agent"]
            }
          }
        }
      }

      KeyManager "disk" {
        plugin_data {
          keys_path = "/run/spire/data/keys.json"
        }
      }

      Notifier "k8sbundle" {
        plugin_data {}
      }
    }
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: spire-server
  namespace: spire
spec:
  serviceName: spire-server
  replicas: 1
  selector:
    matchLabels:
      app: spire-server
  template:
    metadata:
      labels:
        app: spire-server
    spec:
      serviceAccountName: spire-server
      containers:
      - name: spire-server
        image: ghcr.io/spiffe/spire-server:1.8.0
        args:
          - -config
          - /run/spire/config/server.conf
        ports:
        - containerPort: 8081
        volumeMounts:
        - name: spire-config
          mountPath: /run/spire/config
          readOnly: true
        - name: spire-data
          mountPath: /run/spire/data
        livenessProbe:
          exec:
            command:
              - /opt/spire/bin/spire-server
              - healthcheck
              - -shallow
          initialDelaySeconds: 15
          periodSeconds: 60
      volumes:
      - name: spire-config
        configMap:
          name: spire-server
  volumeClaimTemplates:
  - metadata:
      name: spire-data
    spec:
      accessModes:
        - ReadWriteOnce
      resources:
        requests:
          storage: 1Gi
---
apiVersion: v1
kind: Service
metadata:
  name: spire-server
  namespace: spire
spec:
  type: ClusterIP
  ports:
    - name: grpc
      port: 8081
      targetPort: 8081
      protocol: TCP
  selector:
    app: spire-server
```

Apply:
```bash
kubectl apply -f spire-server.yaml

# Wait for server to be ready
kubectl wait --for=condition=ready pod -l app=spire-server -n spire --timeout=300s
```

### Install SPIRE Agent

Create `spire-agent.yaml`:

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spire-agent
  namespace: spire
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: spire-agent-cluster-role
rules:
- apiGroups: [""]
  resources: ["pods", "nodes"]
  verbs: ["get"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: spire-agent-cluster-role-binding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: spire-agent-cluster-role
subjects:
- kind: ServiceAccount
  name: spire-agent
  namespace: spire
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: spire-agent
  namespace: spire
data:
  agent.conf: |
    agent {
      data_dir = "/run/spire"
      log_level = "INFO"
      server_address = "spire-server"
      server_port = "8081"
      socket_path = "/run/spire/sockets/agent.sock"
      trust_domain = "example.org"
    }

    plugins {
      NodeAttestor "k8s_psat" {
        plugin_data {
          cluster = "agentweave-cluster"
        }
      }

      KeyManager "memory" {
        plugin_data {}
      }

      WorkloadAttestor "k8s" {
        plugin_data {
          skip_kubelet_verification = true
        }
      }
    }
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: spire-agent
  namespace: spire
spec:
  selector:
    matchLabels:
      app: spire-agent
  template:
    metadata:
      labels:
        app: spire-agent
    spec:
      hostPID: true
      hostNetwork: true
      dnsPolicy: ClusterFirstWithHostNet
      serviceAccountName: spire-agent
      containers:
      - name: spire-agent
        image: ghcr.io/spiffe/spire-agent:1.8.0
        args:
          - -config
          - /run/spire/config/agent.conf
        volumeMounts:
        - name: spire-config
          mountPath: /run/spire/config
          readOnly: true
        - name: spire-bundle
          mountPath: /run/spire/bundle
        - name: spire-socket
          mountPath: /run/spire/sockets
        - name: spire-token
          mountPath: /var/run/secrets/tokens
        livenessProbe:
          exec:
            command:
              - /opt/spire/bin/spire-agent
              - healthcheck
              - -shallow
          initialDelaySeconds: 15
          periodSeconds: 60
      volumes:
      - name: spire-config
        configMap:
          name: spire-agent
      - name: spire-bundle
        emptyDir: {}
      - name: spire-socket
        hostPath:
          path: /run/spire/sockets
          type: DirectoryOrCreate
      - name: spire-token
        projected:
          sources:
          - serviceAccountToken:
              path: spire-agent
              expirationSeconds: 7200
              audience: spire-server
```

Apply:
```bash
kubectl apply -f spire-agent.yaml

# Verify agents are running on all nodes
kubectl get ds -n spire
kubectl get pods -n spire -l app=spire-agent
```

### Register Agent Workloads

Create SPIRE registration entries for your agents:

```bash
# Get SPIRE server pod
SERVER_POD=$(kubectl get pod -n spire -l app=spire-server -o jsonpath='{.items[0].metadata.name}')

# Register AgentWeave workloads
kubectl exec -n spire $SERVER_POD -- \
  /opt/spire/bin/spire-server entry create \
  -spiffeID spiffe://example.org/ns/agentweave/sa/agentweave-agent \
  -parentID spiffe://example.org/spire/agent/k8s_psat/agentweave-cluster \
  -selector k8s:ns:agentweave \
  -selector k8s:sa:agentweave-agent

# Verify registration
kubectl exec -n spire $SERVER_POD -- \
  /opt/spire/bin/spire-server entry show
```

## Step 3: Deploy OPA

Create `opa-deployment.yaml`:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: opa
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: opa-policies
  namespace: opa
data:
  policy.rego: |
    package agentweave.authz

    default allow = false

    allow {
      caller_trust_domain := split(input.caller.spiffe_id, "/")[2]
      our_trust_domain := input.agent.trust_domain
      caller_trust_domain == our_trust_domain
    }
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opa
  namespace: opa
spec:
  replicas: 2
  selector:
    matchLabels:
      app: opa
  template:
    metadata:
      labels:
        app: opa
    spec:
      containers:
      - name: opa
        image: openpolicyagent/opa:latest
        args:
          - "run"
          - "--server"
          - "--log-level=info"
          - "/policies"
        ports:
        - containerPort: 8181
        volumeMounts:
        - name: policies
          mountPath: /policies
          readOnly: true
        livenessProbe:
          httpGet:
            path: /health
            port: 8181
          initialDelaySeconds: 5
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health?bundle=true
            port: 8181
          initialDelaySeconds: 5
          periodSeconds: 10
      volumes:
      - name: policies
        configMap:
          name: opa-policies
---
apiVersion: v1
kind: Service
metadata:
  name: opa
  namespace: opa
spec:
  type: ClusterIP
  ports:
    - port: 8181
      targetPort: 8181
      protocol: TCP
  selector:
    app: opa
```

Apply:
```bash
kubectl apply -f opa-deployment.yaml

# Verify OPA is running
kubectl get pods -n opa
kubectl wait --for=condition=ready pod -l app=opa -n opa --timeout=300s
```

## Step 4: Deploy Your Agent

### Create Namespace

```bash
kubectl create namespace agentweave
```

### Create Service Account

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agentweave-agent
  namespace: agentweave
```

### Create ConfigMap for Agent Configuration

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentweave-config
  namespace: agentweave
data:
  config.yaml: |
    identity:
      spiffe_id: "spiffe://example.org/ns/agentweave/sa/agentweave-agent"
      spire_socket: "/run/spire/sockets/agent.sock"
      trust_domain: "example.org"

    authorization:
      engine: "opa"
      default_policy: "deny_all"
      opa:
        enabled: true
        url: "http://opa.opa.svc.cluster.local:8181"

    server:
      host: "0.0.0.0"
      port: 8443
      mtls:
        enabled: true
        cert_source: "spire"

    observability:
      logging:
        level: "INFO"
        format: "json"
      metrics:
        enabled: true
        port: 9090
      tracing:
        enabled: true
        exporter: "otlp"
        otlp_endpoint: "jaeger-collector.observability.svc.cluster.local:4317"

    metadata:
      name: "Production Agent"
      version: "1.0.0"
```

### Create Agent Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentweave-agent
  namespace: agentweave
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agentweave-agent
  template:
    metadata:
      labels:
        app: agentweave-agent
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: agentweave-agent
      containers:
      - name: agent
        image: your-registry/agentweave-agent:1.0.0
        imagePullPolicy: Always
        ports:
        - containerPort: 8443
          name: agent
          protocol: TCP
        - containerPort: 9090
          name: metrics
          protocol: TCP
        env:
        - name: POD_NAME
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: POD_NAMESPACE
          valueFrom:
            fieldRef:
              fieldPath: metadata.namespace
        volumeMounts:
        - name: config
          mountPath: /etc/agentweave
          readOnly: true
        - name: spire-socket
          mountPath: /run/spire/sockets
          readOnly: true
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health/live
            port: 8443
            scheme: HTTPS
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /health/ready
            port: 8443
            scheme: HTTPS
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
      volumes:
      - name: config
        configMap:
          name: agentweave-config
      - name: spire-socket
        hostPath:
          path: /run/spire/sockets
          type: Directory
---
apiVersion: v1
kind: Service
metadata:
  name: agentweave-agent
  namespace: agentweave
spec:
  type: ClusterIP
  ports:
    - port: 8443
      targetPort: 8443
      protocol: TCP
      name: agent
    - port: 9090
      targetPort: 9090
      protocol: TCP
      name: metrics
  selector:
    app: agentweave-agent
```

Save as `agent-deployment.yaml` and apply:

```bash
kubectl apply -f agent-deployment.yaml

# Watch deployment
kubectl get pods -n agentweave -w

# Check logs
kubectl logs -n agentweave -l app=agentweave-agent --tail=50
```

## Step 5: Configure Horizontal Pod Autoscaling

Scale based on CPU and custom metrics.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: agentweave-agent-hpa
  namespace: agentweave
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: agentweave-agent
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 2
        periodSeconds: 30
      selectPolicy: Max
```

Apply:
```bash
kubectl apply -f hpa.yaml

# Monitor HPA
kubectl get hpa -n agentweave -w
```

## Step 6: Network Policies

Restrict network access between components.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: agentweave-agent-netpol
  namespace: agentweave
spec:
  podSelector:
    matchLabels:
      app: agentweave-agent
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # Allow from other agents
  - from:
    - namespaceSelector:
        matchLabels:
          name: agentweave
      podSelector:
        matchLabels:
          app: agentweave-agent
    ports:
    - protocol: TCP
      port: 8443
  # Allow from Prometheus
  - from:
    - namespaceSelector:
        matchLabels:
          name: observability
      podSelector:
        matchLabels:
          app: prometheus
    ports:
    - protocol: TCP
      port: 9090
  egress:
  # Allow to OPA
  - to:
    - namespaceSelector:
        matchLabels:
          name: opa
      podSelector:
        matchLabels:
          app: opa
    ports:
    - protocol: TCP
      port: 8181
  # Allow to other agents
  - to:
    - namespaceSelector:
        matchLabels:
          name: agentweave
    ports:
    - protocol: TCP
      port: 8443
  # Allow to SPIRE
  - to:
    - namespaceSelector:
        matchLabels:
          name: spire
    ports:
    - protocol: TCP
      port: 8081
  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

## Step 7: Using Helm Chart

AgentWeave provides Helm charts for easier deployment.

### Install with Helm

```bash
# Add AgentWeave Helm repository
helm repo add agentweave https://aj-geddes.github.io/agentweave/helm-charts
helm repo update

# Install SPIRE
helm install spire agentweave/spire \
  --namespace spire \
  --create-namespace \
  --set trustDomain=example.org

# Install OPA
helm install opa agentweave/opa \
  --namespace opa \
  --create-namespace

# Install AgentWeave Agent
helm install my-agent agentweave/agentweave-agent \
  --namespace agentweave \
  --create-namespace \
  --values my-values.yaml
```

### Custom values.yaml

```yaml
# my-values.yaml
replicaCount: 3

image:
  repository: your-registry/agentweave-agent
  tag: "1.0.0"
  pullPolicy: Always

agent:
  spiffeId: "spiffe://example.org/my-agent"
  trustDomain: "example.org"

authorization:
  opa:
    enabled: true
    url: "http://opa.opa.svc.cluster.local:8181"

observability:
  metrics:
    enabled: true
    serviceMonitor: true
  tracing:
    enabled: true
    endpoint: "jaeger-collector.observability:4317"

resources:
  limits:
    cpu: 500m
    memory: 512Mi
  requests:
    cpu: 100m
    memory: 256Mi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

networkPolicy:
  enabled: true
```

## Step 8: Testing the Deployment

### Port Forward to Agent

```bash
kubectl port-forward -n agentweave svc/agentweave-agent 8443:8443
```

### Call the Agent

```bash
agentweave-cli call \
  --agent spiffe://example.org/ns/agentweave/sa/agentweave-agent \
  --address https://localhost:8443 \
  --capability test \
  --params '{}'
```

### Check Metrics

```bash
kubectl port-forward -n agentweave svc/agentweave-agent 9090:9090

curl http://localhost:9090/metrics
```

## Summary

You've deployed AgentWeave to Kubernetes! You've learned:

- Installing SPIRE for cryptographic identity
- Deploying OPA for authorization
- Creating production-ready agent deployments
- ConfigMaps and resource management
- Health checks and probes
- Horizontal pod autoscaling
- Network policies
- Using Helm charts

## Exercises

1. **Add Ingress** to expose agents externally
2. **Configure PodDisruptionBudget** for high availability
3. **Set up Prometheus** monitoring in-cluster
4. **Implement blue-green deployment** strategy
5. **Add init containers** for database migrations

## What's Next?

- **[Cross-Cloud Agent Mesh](/tutorials/multi-cloud/)** - Multi-cloud deployment
- **[How-To: Kubernetes Operations](/guides/k8s-operations/)** - Day 2 operations
- **[Security: Best Practices](/security/best-practices/)** - Production security
- **[Examples: K8s Operator](/examples/k8s-operator/)** - Build operators

## Troubleshooting

### Pods stuck in Pending
- Check resource availability: `kubectl describe pod <pod-name> -n agentweave`
- Review events: `kubectl get events -n agentweave`

### Cannot get SPIFFE identity
- Verify SPIRE agent is running on same node
- Check SPIRE socket is mounted correctly
- Review SPIRE registration entries

### Health checks failing
- Check agent logs: `kubectl logs -n agentweave <pod-name>`
- Verify certificates from SPIRE are valid
- Test health endpoint manually

See [Troubleshooting Guide](/troubleshooting/) for more help.
