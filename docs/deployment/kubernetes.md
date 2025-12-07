---
layout: page
title: Kubernetes Deployment
description: Deploy AgentWeave agents to Kubernetes clusters
nav_order: 2
parent: Deployment
---

# Kubernetes Deployment Guide

This guide covers deploying AgentWeave agents to Kubernetes clusters with SPIRE and OPA integration.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Prerequisites

- Kubernetes cluster 1.24+ (kubectl configured)
- Cluster-admin access for initial setup
- Storage class for persistent volumes
- LoadBalancer support (cloud provider or MetalLB)
- At least 8GB RAM across cluster nodes

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│              Kubernetes Cluster                     │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  SPIRE Namespace (spire-system)              │   │
│  │                                              │   │
│  │  ┌─────────────┐      ┌─────────────┐       │   │
│  │  │ SPIRE       │      │ SPIRE Agent │       │   │
│  │  │ Server      │◄─────┤ (DaemonSet) │       │   │
│  │  │ (StatefulSet)      └─────────────┘       │   │
│  │  └─────────────┘                            │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │  Agent Namespace (agentweave)                │   │
│  │                                              │   │
│  │  ┌─────────────────────────────────────┐     │   │
│  │  │  Agent Pod                          │     │   │
│  │  │  ┌──────────┐  ┌────────────────┐   │     │   │
│  │  │  │  Agent   │  │  OPA Sidecar   │   │     │   │
│  │  │  │Container │  │                │   │     │   │
│  │  │  └─────┬────┘  └────────────────┘   │     │   │
│  │  │        │                             │     │   │
│  │  │        │  Shared SPIRE Socket        │     │   │
│  │  │        └─────────────────────────────│     │   │
│  │  └─────────────────────────────────────┘     │   │
│  └──────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```

## Namespace Setup

Create namespaces for infrastructure and agents:

```yaml
# namespaces.yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: spire-system
  labels:
    name: spire-system
    security: high

---
apiVersion: v1
kind: Namespace
metadata:
  name: agentweave
  labels:
    name: agentweave
    security: high
```

Apply namespaces:

```bash
kubectl apply -f namespaces.yaml
```

## SPIRE Deployment

### SPIRE Server

**ServiceAccount and RBAC**:

```yaml
# spire-server-rbac.yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spire-server
  namespace: spire-system

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: spire-server-cluster-role
rules:
  - apiGroups: [""]
    resources: ["pods", "nodes"]
    verbs: ["get", "list", "watch"]
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
    namespace: spire-system
```

**ConfigMap**:

```yaml
# spire-server-config.yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: spire-server
  namespace: spire-system
data:
  server.conf: |
    server {
        bind_address = "0.0.0.0"
        bind_port = "8081"
        trust_domain = "agentweave.io"
        data_dir = "/run/spire/data"
        log_level = "INFO"
        ca_ttl = "168h"
        default_x509_svid_ttl = "1h"
    }

    plugins {
        DataStore "sql" {
            plugin_data {
                database_type = "postgres"
                connection_string = "postgresql://spire:password@postgres:5432/spire?sslmode=disable"
            }
        }

        NodeAttestor "k8s_psat" {
            plugin_data {
                clusters = {
                    "agentweave-cluster" = {
                        service_account_allow_list = ["spire-system:spire-agent"]
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
            plugin_data {
                namespace = "spire-system"
            }
        }
    }

    health_checks {
        listener_enabled = true
        bind_address = "0.0.0.0"
        bind_port = "8080"
        live_path = "/live"
        ready_path = "/ready"
    }
```

**StatefulSet**:

```yaml
# spire-server-statefulset.yaml
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: spire-server
  namespace: spire-system
  labels:
    app: spire-server
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
          image: ghcr.io/spiffe/spire-server:1.9.0
          args:
            - -config
            - /run/spire/config/server.conf
          ports:
            - name: grpc
              containerPort: 8081
              protocol: TCP
            - name: health
              containerPort: 8080
              protocol: TCP
          livenessProbe:
            httpGet:
              path: /live
              port: 8080
            initialDelaySeconds: 30
            periodSeconds: 60
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 10
            periodSeconds: 10
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi
          volumeMounts:
            - name: spire-config
              mountPath: /run/spire/config
              readOnly: true
            - name: spire-data
              mountPath: /run/spire/data
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
            storage: 10Gi

---
apiVersion: v1
kind: Service
metadata:
  name: spire-server
  namespace: spire-system
spec:
  type: ClusterIP
  selector:
    app: spire-server
  ports:
    - name: grpc
      port: 8081
      targetPort: 8081
      protocol: TCP
```

### SPIRE Agent

**ServiceAccount and RBAC**:

```yaml
# spire-agent-rbac.yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: spire-agent
  namespace: spire-system

---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: spire-agent-cluster-role
rules:
  - apiGroups: [""]
    resources: ["pods", "nodes", "nodes/proxy"]
    verbs: ["get", "list"]

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
    namespace: spire-system
```

**ConfigMap**:

```yaml
# spire-agent-config.yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: spire-agent
  namespace: spire-system
data:
  agent.conf: |
    agent {
        data_dir = "/run/spire"
        log_level = "INFO"
        server_address = "spire-server"
        server_port = "8081"
        socket_path = "/run/spire/sockets/agent.sock"
        trust_domain = "agentweave.io"
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

        WorkloadAttestor "unix" {
            plugin_data {}
        }
    }

    health_checks {
        listener_enabled = true
        bind_address = "0.0.0.0"
        bind_port = "8080"
        live_path = "/live"
        ready_path = "/ready"
    }
```

**DaemonSet**:

```yaml
# spire-agent-daemonset.yaml
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: spire-agent
  namespace: spire-system
  labels:
    app: spire-agent
spec:
  selector:
    matchLabels:
      app: spire-agent
  template:
    metadata:
      labels:
        app: spire-agent
    spec:
      serviceAccountName: spire-agent
      hostPID: true
      hostNetwork: true
      dnsPolicy: ClusterFirstWithHostNet
      initContainers:
        - name: init
          image: ghcr.io/spiffe/spire-agent:1.9.0
          command:
            - /bin/sh
            - -c
            - |
              rm -rf /run/spire/sockets/*
          volumeMounts:
            - name: spire-agent-socket
              mountPath: /run/spire/sockets
      containers:
        - name: spire-agent
          image: ghcr.io/spiffe/spire-agent:1.9.0
          args:
            - -config
            - /run/spire/config/agent.conf
          livenessProbe:
            httpGet:
              path: /live
              port: 8080
            initialDelaySeconds: 15
            periodSeconds: 60
          readinessProbe:
            httpGet:
              path: /ready
              port: 8080
            initialDelaySeconds: 5
            periodSeconds: 5
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          securityContext:
            privileged: true
          volumeMounts:
            - name: spire-config
              mountPath: /run/spire/config
              readOnly: true
            - name: spire-agent-socket
              mountPath: /run/spire/sockets
            - name: spire-bundle
              mountPath: /run/spire/bundle
            - name: spire-token
              mountPath: /var/run/secrets/tokens
      volumes:
        - name: spire-config
          configMap:
            name: spire-agent
        - name: spire-agent-socket
          hostPath:
            path: /run/spire/sockets
            type: DirectoryOrCreate
        - name: spire-bundle
          configMap:
            name: spire-bundle
        - name: spire-token
          projected:
            sources:
              - serviceAccountToken:
                  path: spire-agent
                  expirationSeconds: 7200
                  audience: spire-server
```

## OPA Deployment

For centralized OPA, deploy as a service:

```yaml
# opa-deployment.yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: opa-policy
  namespace: agentweave
data:
  authz.rego: |
    package agentweave.authz

    import rego.v1

    default allow := false

    # Allow agents in same trust domain
    allow if {
        same_trust_domain
        valid_action
    }

    same_trust_domain if {
        caller_domain := split(input.caller_spiffe_id, "/")[2]
        callee_domain := split(input.callee_spiffe_id, "/")[2]
        caller_domain == callee_domain
        caller_domain == "agentweave.io"
    }

    valid_action if {
        input.action in ["search", "process", "orchestrate"]
    }

---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: opa
  namespace: agentweave
  labels:
    app: opa
spec:
  replicas: 3
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
          image: openpolicyagent/opa:0.62.0
          args:
            - "run"
            - "--server"
            - "--addr=0.0.0.0:8181"
            - "--log-level=info"
            - "--log-format=json"
            - "/policies"
          ports:
            - name: http
              containerPort: 8181
          livenessProbe:
            httpGet:
              path: /health
              port: 8181
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health?bundles
              port: 8181
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          volumeMounts:
            - name: opa-policy
              mountPath: /policies
              readOnly: true
      volumes:
        - name: opa-policy
          configMap:
            name: opa-policy

---
apiVersion: v1
kind: Service
metadata:
  name: opa
  namespace: agentweave
spec:
  type: ClusterIP
  selector:
    app: opa
  ports:
    - name: http
      port: 8181
      targetPort: 8181
```

## Agent Deployment

### ConfigMap for Agent Configuration

```yaml
# agent-config.yaml
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-agent-config
  namespace: agentweave
data:
  config.yaml: |
    agent:
      name: "my-agent"
      trust_domain: "agentweave.io"
      description: "Example agent"
      capabilities:
        - name: "process"
          description: "Process data"
          input_modes: ["application/json"]
          output_modes: ["application/json"]

    identity:
      provider: "spiffe"
      spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"
      allowed_trust_domains:
        - "agentweave.io"

    authorization:
      provider: "opa"
      opa_endpoint: "http://opa:8181"
      policy_path: "agentweave/authz"
      default_action: "deny"
      audit:
        enabled: true

    transport:
      tls_min_version: "1.3"
      peer_verification: "strict"
      connection_pool:
        max_connections: 100
        idle_timeout_seconds: 60

    server:
      host: "0.0.0.0"
      port: 8443

    observability:
      metrics:
        enabled: true
        port: 9090
      tracing:
        enabled: true
        exporter: "otlp"
        endpoint: "http://otel-collector:4317"
      logging:
        level: "INFO"
        format: "json"
```

### Secrets Management

Store sensitive data in Kubernetes Secrets:

```yaml
# agent-secrets.yaml
---
apiVersion: v1
kind: Secret
metadata:
  name: my-agent-secrets
  namespace: agentweave
type: Opaque
stringData:
  api-key: "your-api-key-here"
  database-url: "postgresql://user:pass@db:5432/mydb"
```

### ServiceAccount and RBAC

```yaml
# agent-rbac.yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: my-agent
  namespace: agentweave

---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: my-agent-role
  namespace: agentweave
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list"]

---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: my-agent-role-binding
  namespace: agentweave
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: Role
  name: my-agent-role
subjects:
  - kind: ServiceAccount
    name: my-agent
    namespace: agentweave
```

### Deployment Manifest

```yaml
# agent-deployment.yaml
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-agent
  namespace: agentweave
  labels:
    app: my-agent
    version: v1.0.0
spec:
  replicas: 3
  selector:
    matchLabels:
      app: my-agent
  template:
    metadata:
      labels:
        app: my-agent
        version: v1.0.0
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      serviceAccountName: my-agent
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        # Main agent container
        - name: agent
          image: my-org/my-agent:1.0.0
          imagePullPolicy: IfNotPresent
          ports:
            - name: https
              containerPort: 8443
              protocol: TCP
            - name: metrics
              containerPort: 9090
              protocol: TCP
          env:
            - name: SPIFFE_ENDPOINT_SOCKET
              value: "unix:///run/spire/sockets/agent.sock"
            - name: AGENTWEAVE_CONFIG_PATH
              value: "/etc/agentweave/config.yaml"
            - name: AGENTWEAVE_LOG_LEVEL
              value: "INFO"
          envFrom:
            - secretRef:
                name: my-agent-secrets
          livenessProbe:
            httpGet:
              path: /health/live
              port: 8443
              scheme: HTTPS
            initialDelaySeconds: 30
            periodSeconds: 30
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health/ready
              port: 8443
              scheme: HTTPS
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 2000m
              memory: 2Gi
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            runAsNonRoot: true
            runAsUser: 1000
            capabilities:
              drop:
                - ALL
          volumeMounts:
            - name: config
              mountPath: /etc/agentweave
              readOnly: true
            - name: spire-agent-socket
              mountPath: /run/spire/sockets
              readOnly: true
            - name: tmp
              mountPath: /tmp

        # OPA sidecar
        - name: opa
          image: openpolicyagent/opa:0.62.0
          args:
            - "run"
            - "--server"
            - "--addr=localhost:8181"
            - "--log-level=info"
            - "/policies"
          ports:
            - name: http
              containerPort: 8181
          livenessProbe:
            httpGet:
              path: /health
              port: 8181
            initialDelaySeconds: 5
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8181
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 512Mi
          volumeMounts:
            - name: opa-policy
              mountPath: /policies
              readOnly: true
      volumes:
        - name: config
          configMap:
            name: my-agent-config
        - name: spire-agent-socket
          hostPath:
            path: /run/spire/sockets
            type: Directory
        - name: opa-policy
          configMap:
            name: opa-policy
        - name: tmp
          emptyDir: {}
```

### Service Definition

```yaml
# agent-service.yaml
---
apiVersion: v1
kind: Service
metadata:
  name: my-agent
  namespace: agentweave
  labels:
    app: my-agent
spec:
  type: ClusterIP
  selector:
    app: my-agent
  ports:
    - name: https
      port: 8443
      targetPort: 8443
      protocol: TCP
    - name: metrics
      port: 9090
      targetPort: 9090
      protocol: TCP
```

## NetworkPolicy for Security

Restrict network access:

```yaml
# network-policy.yaml
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: my-agent-netpol
  namespace: agentweave
spec:
  podSelector:
    matchLabels:
      app: my-agent
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow from other agents
    - from:
        - namespaceSelector:
            matchLabels:
              name: agentweave
        - podSelector:
            matchLabels:
              app: agentweave-agent
      ports:
        - protocol: TCP
          port: 8443
    # Allow from monitoring
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
        - podSelector:
            matchLabels:
              app: spire-server
      ports:
        - protocol: TCP
          port: 8081
    # Allow to OPA
    - to:
        - podSelector:
            matchLabels:
              app: opa
      ports:
        - protocol: TCP
          port: 8181
    # Allow to other agents
    - to:
        - podSelector:
            matchLabels:
              app: agentweave-agent
      ports:
        - protocol: TCP
          port: 8443
    # Allow DNS
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53
```

## Kubectl Commands

### Deploying Components

```bash
# Deploy SPIRE
kubectl apply -f spire-server-rbac.yaml
kubectl apply -f spire-server-config.yaml
kubectl apply -f spire-server-statefulset.yaml
kubectl apply -f spire-agent-rbac.yaml
kubectl apply -f spire-agent-config.yaml
kubectl apply -f spire-agent-daemonset.yaml

# Wait for SPIRE to be ready
kubectl wait --for=condition=ready pod -l app=spire-server -n spire-system --timeout=300s
kubectl wait --for=condition=ready pod -l app=spire-agent -n spire-system --timeout=300s

# Deploy OPA
kubectl apply -f opa-deployment.yaml

# Deploy agent
kubectl apply -f agent-config.yaml
kubectl apply -f agent-secrets.yaml
kubectl apply -f agent-rbac.yaml
kubectl apply -f agent-deployment.yaml
kubectl apply -f agent-service.yaml
kubectl apply -f network-policy.yaml

# Wait for agent to be ready
kubectl wait --for=condition=ready pod -l app=my-agent -n agentweave --timeout=300s
```

### Registering Agents with SPIRE

```bash
# Create registration entry
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server entry create \
    -spiffeID spiffe://agentweave.io/agent/my-agent \
    -parentID spiffe://agentweave.io/spire/agent/k8s-node \
    -selector k8s:ns:agentweave \
    -selector k8s:sa:my-agent \
    -selector k8s:pod-label:app:my-agent \
    -dns my-agent \
    -dns my-agent.agentweave \
    -dns my-agent.agentweave.svc.cluster.local

# Verify registration
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server entry show
```

### Monitoring and Debugging

```bash
# View agent logs
kubectl logs -n agentweave -l app=my-agent -c agent -f

# View OPA sidecar logs
kubectl logs -n agentweave -l app=my-agent -c opa -f

# Check agent health
kubectl exec -n agentweave deploy/my-agent -c agent -- \
  agentweave validate /etc/agentweave/config.yaml

# View agent card
kubectl exec -n agentweave deploy/my-agent -c agent -- \
  agentweave card generate /etc/agentweave/config.yaml

# Test SPIRE connection
kubectl exec -n agentweave deploy/my-agent -c agent -- \
  ls -l /run/spire/sockets/

# Test OPA
kubectl exec -n agentweave deploy/my-agent -c agent -- \
  curl http://localhost:8181/health

# Port forward for local access
kubectl port-forward -n agentweave svc/my-agent 8443:8443

# View metrics
kubectl port-forward -n agentweave svc/my-agent 9090:9090
curl http://localhost:9090/metrics
```

### Scaling

```bash
# Scale up
kubectl scale deployment my-agent -n agentweave --replicas=5

# Scale down
kubectl scale deployment my-agent -n agentweave --replicas=2

# Autoscale based on CPU
kubectl autoscale deployment my-agent -n agentweave \
  --cpu-percent=70 \
  --min=2 \
  --max=10
```

### Updates and Rollbacks

```bash
# Update image
kubectl set image deployment/my-agent -n agentweave \
  agent=my-org/my-agent:1.1.0

# Check rollout status
kubectl rollout status deployment/my-agent -n agentweave

# View rollout history
kubectl rollout history deployment/my-agent -n agentweave

# Rollback to previous version
kubectl rollout undo deployment/my-agent -n agentweave

# Rollback to specific revision
kubectl rollout undo deployment/my-agent -n agentweave --to-revision=2
```

## Troubleshooting

### Pod Not Starting

```bash
# Check pod status
kubectl get pods -n agentweave -l app=my-agent

# Describe pod
kubectl describe pod -n agentweave -l app=my-agent

# Check events
kubectl get events -n agentweave --sort-by='.lastTimestamp'

# Check resource constraints
kubectl top pods -n agentweave
```

### SPIRE Issues

```bash
# Check SPIRE server logs
kubectl logs -n spire-system -l app=spire-server -f

# Check SPIRE agent logs on specific node
kubectl logs -n spire-system -l app=spire-agent --field-selector spec.nodeName=<node-name>

# Verify SPIRE socket exists
kubectl exec -n agentweave deploy/my-agent -c agent -- \
  ls -la /run/spire/sockets/

# Test SPIRE workload API
kubectl exec -n spire-system spire-agent-<pod-name> -- \
  /opt/spire/bin/spire-agent api fetch -socketPath /run/spire/sockets/agent.sock
```

### Network Issues

```bash
# Test connectivity between pods
kubectl exec -n agentweave deploy/my-agent -c agent -- \
  curl -k https://other-agent:8443/health/live

# Check NetworkPolicy
kubectl describe networkpolicy my-agent-netpol -n agentweave

# Temporarily disable NetworkPolicy for debugging
kubectl delete networkpolicy my-agent-netpol -n agentweave

# Re-enable NetworkPolicy
kubectl apply -f network-policy.yaml
```

## Next Steps

- **[Helm Deployment](helm.md)** - Use Helm charts for templated deployments
- **[Cloud-Specific Guides](aws.md)** - AWS, GCP, Azure deployments
- **[Monitoring Setup](../guides/observability.md)** - Full observability stack

---

**Related Documentation**:
- [Configuration Reference](../configuration.md)
- [Security Best Practices](../security.md)
- [High Availability Guide](../guides/ha.md)
