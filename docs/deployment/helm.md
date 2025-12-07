---
layout: page
title: Helm Deployment
description: Deploy AgentWeave agents using Helm charts
nav_order: 3
parent: Deployment
---

# Helm Deployment Guide

This guide covers deploying AgentWeave agents using Helm charts for templated, reproducible Kubernetes deployments.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Prerequisites

- Kubernetes cluster 1.24+
- Helm 3.8+
- kubectl configured
- Cluster-admin access for initial setup

## Installing Helm

If you don't have Helm installed:

```bash
# macOS
brew install helm

# Linux
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify installation
helm version
```

## Adding the AgentWeave Helm Repository

```bash
# Add the official AgentWeave Helm repository
helm repo add agentweave https://charts.agentweave.io

# Update repository index
helm repo update

# Search for available charts
helm search repo agentweave
```

Expected output:
```
NAME                            CHART VERSION   APP VERSION     DESCRIPTION
agentweave/agentweave           1.0.0           1.0.0           AgentWeave secure agent SDK
agentweave/spire                1.9.0           1.9.0           SPIRE identity infrastructure
agentweave/agentweave-stack     1.0.0           1.0.0           Complete AgentWeave stack
```

## Chart Structure

The AgentWeave Helm chart has the following structure:

```
agentweave/
├── Chart.yaml              # Chart metadata
├── values.yaml             # Default configuration values
├── templates/
│   ├── NOTES.txt           # Post-installation notes
│   ├── _helpers.tpl        # Template helpers
│   ├── configmap.yaml      # Agent configuration
│   ├── deployment.yaml     # Agent deployment
│   ├── service.yaml        # Service definition
│   ├── serviceaccount.yaml # RBAC resources
│   ├── networkpolicy.yaml  # Network policies
│   ├── hpa.yaml            # Horizontal pod autoscaler
│   ├── pdb.yaml            # Pod disruption budget
│   └── spire/              # SPIRE-specific resources
│       ├── entries.yaml    # Registration entries
│       └── configmap.yaml  # SPIRE configuration
└── values.schema.json      # Values validation schema
```

## values.yaml Reference

### Complete values.yaml

```yaml
# AgentWeave Helm Chart Values
# This file contains all configurable parameters

# Agent configuration
agent:
  # Agent name (required)
  name: "my-agent"

  # SPIFFE trust domain
  trustDomain: "agentweave.io"

  # Agent description
  description: "Example AgentWeave agent"

  # Agent capabilities
  capabilities:
    - name: "process"
      description: "Process data"
      inputModes:
        - "application/json"
      outputModes:
        - "application/json"

# Container image configuration
image:
  # Image repository
  repository: agentweave/agent

  # Image pull policy
  pullPolicy: IfNotPresent

  # Image tag (defaults to chart appVersion)
  tag: ""

# Image pull secrets
imagePullSecrets: []

# Number of replicas
replicaCount: 3

# ServiceAccount configuration
serviceAccount:
  # Create service account
  create: true

  # Service account annotations
  annotations: {}

  # Service account name
  name: ""

# Pod annotations
podAnnotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "9090"
  prometheus.io/path: "/metrics"

# Pod security context
podSecurityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault

# Container security context
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  runAsNonRoot: true
  runAsUser: 1000
  capabilities:
    drop:
      - ALL

# SPIFFE/SPIRE configuration
spiffe:
  # Enable SPIFFE identity
  enabled: true

  # SPIRE agent socket path
  socketPath: "/run/spire/sockets/agent.sock"

  # Allowed trust domains
  allowedTrustDomains:
    - "agentweave.io"

  # SPIRE registration entry
  registration:
    # Create registration entry
    create: true

    # Parent SPIFFE ID
    parentID: "spiffe://agentweave.io/spire/agent/k8s-node"

    # Selectors
    selectors:
      - "k8s:ns:{{ .Release.Namespace }}"
      - "k8s:sa:{{ include \"agentweave.serviceAccountName\" . }}"
      - "k8s:pod-label:app.kubernetes.io/name:{{ include \"agentweave.name\" . }}"

    # DNS names
    dnsNames:
      - "{{ include \"agentweave.fullname\" . }}"
      - "{{ include \"agentweave.fullname\" . }}.{{ .Release.Namespace }}"
      - "{{ include \"agentweave.fullname\" . }}.{{ .Release.Namespace }}.svc.cluster.local"

# Authorization configuration
authorization:
  # OPA provider
  provider: "opa"

  # OPA endpoint
  opaEndpoint: "http://opa:8181"

  # OPA policy path
  policyPath: "agentweave/authz"

  # Default action
  defaultAction: "deny"

  # Audit logging
  audit:
    enabled: true
    destination: "stdout"

  # OPA sidecar configuration
  sidecar:
    # Enable OPA sidecar
    enabled: true

    # OPA image
    image: "openpolicyagent/opa:0.62.0"

    # Resources
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 512Mi

# Transport configuration
transport:
  # Minimum TLS version
  tlsMinVersion: "1.3"

  # Peer verification
  peerVerification: "strict"

  # Connection pool
  connectionPool:
    maxConnections: 100
    idleTimeoutSeconds: 60

  # Circuit breaker
  circuitBreaker:
    failureThreshold: 5
    recoveryTimeoutSeconds: 30

# Server configuration
server:
  # Listen host
  host: "0.0.0.0"

  # Listen port
  port: 8443

  # Protocol
  protocol: "a2a"

# Observability configuration
observability:
  # Metrics
  metrics:
    enabled: true
    port: 9090

  # Tracing
  tracing:
    enabled: true
    exporter: "otlp"
    endpoint: "http://otel-collector:4317"

  # Logging
  logging:
    level: "INFO"
    format: "json"

# Service configuration
service:
  # Service type
  type: ClusterIP

  # HTTPS port
  port: 8443

  # Metrics port
  metricsPort: 9090

  # Annotations
  annotations: {}

# Ingress configuration
ingress:
  # Enable ingress
  enabled: false

  # Ingress class
  className: "nginx"

  # Annotations
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/backend-protocol: "HTTPS"

  # Hosts
  hosts:
    - host: my-agent.example.com
      paths:
        - path: /
          pathType: Prefix

  # TLS
  tls:
    - secretName: my-agent-tls
      hosts:
        - my-agent.example.com

# Resource limits and requests
resources:
  requests:
    cpu: 500m
    memory: 512Mi
  limits:
    cpu: 2000m
    memory: 2Gi

# Autoscaling
autoscaling:
  # Enable HPA
  enabled: true

  # Minimum replicas
  minReplicas: 2

  # Maximum replicas
  maxReplicas: 10

  # Target CPU utilization
  targetCPUUtilizationPercentage: 70

  # Target memory utilization
  targetMemoryUtilizationPercentage: 80

# Pod disruption budget
podDisruptionBudget:
  # Enable PDB
  enabled: true

  # Minimum available pods
  minAvailable: 1

# Node selector
nodeSelector: {}

# Tolerations
tolerations: []

# Affinity rules
affinity:
  podAntiAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app.kubernetes.io/name: agentweave
          topologyKey: kubernetes.io/hostname

# Network policy
networkPolicy:
  # Enable network policy
  enabled: true

  # Ingress rules
  ingress:
    # Allow from same namespace
    - from:
        - namespaceSelector:
            matchLabels:
              name: "{{ .Release.Namespace }}"

  # Egress rules
  egress:
    # Allow to SPIRE
    - to:
        - namespaceSelector:
            matchLabels:
              name: spire-system
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
    # Allow DNS
    - to:
        - namespaceSelector: {}
          podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53

# Extra environment variables
extraEnv: []

# Extra volumes
extraVolumes: []

# Extra volume mounts
extraVolumeMounts: []

# Config overrides
configOverrides: {}
```

## Installing the Chart

### Basic Installation

Install with default values:

```bash
helm install my-agent agentweave/agentweave \
  --namespace agentweave \
  --create-namespace
```

### Custom values.yaml

Create a custom `values.yaml`:

```yaml
# my-values.yaml
agent:
  name: "search-agent"
  trustDomain: "company.com"
  capabilities:
    - name: "search"
      description: "Search documents"

replicaCount: 5

resources:
  requests:
    cpu: 1000m
    memory: 1Gi
  limits:
    cpu: 4000m
    memory: 4Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
```

Install with custom values:

```bash
helm install search-agent agentweave/agentweave \
  --namespace agentweave \
  --create-namespace \
  --values my-values.yaml
```

### Command-Line Overrides

Override specific values via command line:

```bash
helm install my-agent agentweave/agentweave \
  --namespace agentweave \
  --create-namespace \
  --set agent.name=my-agent \
  --set agent.trustDomain=example.com \
  --set replicaCount=5 \
  --set resources.requests.cpu=1000m \
  --set resources.requests.memory=1Gi
```

## Common Configurations

### Configuration 1: Single Agent (Development)

```yaml
# dev-values.yaml
agent:
  name: "dev-agent"
  trustDomain: "dev.local"

replicaCount: 1

resources:
  requests:
    cpu: 100m
    memory: 128Mi
  limits:
    cpu: 500m
    memory: 512Mi

autoscaling:
  enabled: false

podDisruptionBudget:
  enabled: false

observability:
  logging:
    level: "DEBUG"
```

Deploy:

```bash
helm install dev-agent agentweave/agentweave \
  -f dev-values.yaml \
  -n dev
```

### Configuration 2: Production Multi-Agent

```yaml
# prod-values.yaml
agent:
  name: "prod-agent"
  trustDomain: "company.com"

replicaCount: 3

resources:
  requests:
    cpu: 1000m
    memory: 1Gi
  limits:
    cpu: 4000m
    memory: 4Gi

autoscaling:
  enabled: true
  minReplicas: 3
  maxReplicas: 20
  targetCPUUtilizationPercentage: 70

podDisruptionBudget:
  enabled: true
  minAvailable: 2

affinity:
  podAntiAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector:
          matchLabels:
            app.kubernetes.io/name: agentweave
        topologyKey: kubernetes.io/hostname

observability:
  logging:
    level: "INFO"
  tracing:
    enabled: true
    endpoint: "http://jaeger-collector:4317"
```

Deploy:

```bash
helm install prod-agent agentweave/agentweave \
  -f prod-values.yaml \
  -n production
```

### Configuration 3: With SPIRE Stack

Install complete SPIRE + Agent stack:

```yaml
# spire-stack-values.yaml
# Install SPIRE dependencies
spire:
  enabled: true
  server:
    enabled: true
    trustDomain: "company.com"
  agent:
    enabled: true
    daemonset: true

# Agent configuration
agent:
  name: "my-agent"
  trustDomain: "company.com"

spiffe:
  enabled: true
  registration:
    create: true
```

Deploy:

```bash
helm install agentweave-stack agentweave/agentweave-stack \
  -f spire-stack-values.yaml \
  -n agentweave
```

### Configuration 4: With OPA Sidecar

```yaml
# opa-sidecar-values.yaml
agent:
  name: "secure-agent"
  trustDomain: "company.com"

authorization:
  provider: "opa"
  sidecar:
    enabled: true
    policies:
      authz.rego: |
        package agentweave.authz

        import rego.v1

        default allow := false

        allow if {
            input.caller_spiffe_id == "spiffe://company.com/agent/orchestrator"
            input.action in ["search", "process"]
        }
```

Deploy:

```bash
helm install secure-agent agentweave/agentweave \
  -f opa-sidecar-values.yaml \
  -n agentweave
```

## Managing Releases

### Viewing Releases

```bash
# List all releases
helm list -A

# List releases in specific namespace
helm list -n agentweave

# Get release status
helm status my-agent -n agentweave

# Get release values
helm get values my-agent -n agentweave

# Get all release information
helm get all my-agent -n agentweave
```

### Upgrading Releases

```bash
# Upgrade with new values
helm upgrade my-agent agentweave/agentweave \
  -f new-values.yaml \
  -n agentweave

# Upgrade to specific chart version
helm upgrade my-agent agentweave/agentweave \
  --version 1.1.0 \
  -n agentweave

# Upgrade with reuse of existing values
helm upgrade my-agent agentweave/agentweave \
  --reuse-values \
  --set image.tag=1.1.0 \
  -n agentweave

# Dry-run upgrade
helm upgrade my-agent agentweave/agentweave \
  -f new-values.yaml \
  --dry-run \
  -n agentweave
```

### Rollback Procedures

```bash
# View release history
helm history my-agent -n agentweave

# Rollback to previous revision
helm rollback my-agent -n agentweave

# Rollback to specific revision
helm rollback my-agent 3 -n agentweave

# Dry-run rollback
helm rollback my-agent 3 --dry-run -n agentweave
```

### Uninstalling Releases

```bash
# Uninstall release
helm uninstall my-agent -n agentweave

# Keep history
helm uninstall my-agent -n agentweave --keep-history

# Delete namespace too
helm uninstall my-agent -n agentweave
kubectl delete namespace agentweave
```

## Customizing Templates

### Adding Custom Annotations

```yaml
# values.yaml
podAnnotations:
  custom.io/annotation: "value"
  prometheus.io/scrape: "true"

deployment:
  annotations:
    deployment.custom.io/annotation: "value"
```

### Adding Sidecars

```yaml
# values.yaml
sidecars:
  - name: log-forwarder
    image: fluent/fluent-bit:latest
    volumeMounts:
      - name: logs
        mountPath: /var/log

extraVolumes:
  - name: logs
    emptyDir: {}
```

### Custom Init Containers

```yaml
# values.yaml
initContainers:
  - name: wait-for-spire
    image: busybox:latest
    command:
      - sh
      - -c
      - |
        until [ -S /run/spire/sockets/agent.sock ]; do
          echo "Waiting for SPIRE socket..."
          sleep 1
        done
    volumeMounts:
      - name: spire-agent-socket
        mountPath: /run/spire/sockets
        readOnly: true
```

## Testing Chart Changes

### Linting

```bash
# Lint chart
helm lint agentweave/

# Lint with custom values
helm lint agentweave/ -f my-values.yaml
```

### Template Rendering

```bash
# Render templates
helm template my-agent agentweave/agentweave \
  -f my-values.yaml \
  -n agentweave

# Render specific template
helm template my-agent agentweave/agentweave \
  -s templates/deployment.yaml \
  -f my-values.yaml

# Debug template rendering
helm template my-agent agentweave/agentweave \
  -f my-values.yaml \
  --debug
```

### Dry-Run Installation

```bash
# Dry-run install
helm install my-agent agentweave/agentweave \
  -f my-values.yaml \
  -n agentweave \
  --dry-run \
  --debug

# Diff against running release (requires helm-diff plugin)
helm diff upgrade my-agent agentweave/agentweave \
  -f new-values.yaml \
  -n agentweave
```

## Chart Development

### Creating Custom Chart

```bash
# Create new chart based on AgentWeave
helm create my-custom-agent

# Or fork the official chart
git clone https://github.com/aj-geddes/helm-charts.git
cd helm-charts/charts/agentweave
```

### Testing Locally

```bash
# Install from local directory
helm install my-agent ./agentweave \
  -f values.yaml \
  -n agentweave

# Package chart
helm package agentweave/

# Install from package
helm install my-agent agentweave-1.0.0.tgz \
  -n agentweave
```

### Chart Dependencies

```yaml
# Chart.yaml
dependencies:
  - name: spire
    version: "1.9.0"
    repository: "https://charts.agentweave.io"
    condition: spire.enabled
  - name: opa
    version: "0.62.0"
    repository: "https://charts.agentweave.io"
    condition: opa.enabled
```

Update dependencies:

```bash
helm dependency update agentweave/
helm dependency list agentweave/
```

## Troubleshooting

### Chart Installation Fails

```bash
# Check chart validity
helm lint agentweave/ -f values.yaml

# Render templates to check for errors
helm template my-agent agentweave/agentweave -f values.yaml --debug

# Check Kubernetes events
kubectl get events -n agentweave --sort-by='.lastTimestamp'
```

### Values Not Being Applied

```bash
# Verify applied values
helm get values my-agent -n agentweave

# Compare with all values (including defaults)
helm get values my-agent -n agentweave --all

# Re-apply with debug
helm upgrade my-agent agentweave/agentweave \
  -f values.yaml \
  --debug \
  -n agentweave
```

### Template Rendering Issues

```bash
# Render specific template
helm template my-agent agentweave/agentweave \
  -s templates/deployment.yaml \
  --debug

# Check for syntax errors in values
helm template my-agent agentweave/agentweave \
  -f values.yaml \
  --validate
```

## Best Practices

### Version Pinning

Always pin chart versions in production:

```bash
# Install specific version
helm install my-agent agentweave/agentweave \
  --version 1.0.0 \
  -n agentweave

# Lock versions in requirements
helm dependency update --skip-refresh
```

### Values Organization

Organize values by environment:

```
values/
├── values.yaml          # Common values
├── dev-values.yaml      # Development overrides
├── staging-values.yaml  # Staging overrides
└── prod-values.yaml     # Production overrides
```

Deploy with merged values:

```bash
helm install my-agent agentweave/agentweave \
  -f values/values.yaml \
  -f values/prod-values.yaml \
  -n production
```

### Secrets Management

Never commit secrets to values files:

```bash
# Use sealed-secrets
kubectl create secret generic my-agent-secrets \
  --from-literal=api-key=secret-value \
  -n agentweave

# Or use external secrets operator
# Reference in values.yaml
externalSecrets:
  enabled: true
  backend: aws-secrets-manager
  secretName: my-agent-secrets
```

## Next Steps

- **[AWS Deployment](aws.md)** - Deploy to AWS EKS
- **[GCP Deployment](gcp.md)** - Deploy to Google GKE
- **[Azure Deployment](azure.md)** - Deploy to Azure AKS

---

**Related Documentation**:
- [Kubernetes Deployment](kubernetes.md)
- [Configuration Reference](/agentweave/configuration/)
- [Operations Guide](/agentweave/guides/operations/)
