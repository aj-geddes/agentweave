---
layout: page
title: GCP Deployment
description: Deploy AgentWeave agents to Google Cloud Platform
nav_order: 5
parent: Deployment
---

# GCP Deployment Guide

This guide covers deploying AgentWeave agents to Google Cloud Platform using GKE with Workload Identity and native GCP integrations.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Prerequisites

- GCP Project with billing enabled
- gcloud CLI configured (`gcloud auth login`)
- kubectl 1.24+
- Helm 3.8+
- Appropriate IAM permissions

## Architecture on GCP

```
┌─────────────────────────────────────────────────────────────┐
│                    Google Cloud Platform                    │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  VPC Network                                         │   │
│  │                                                      │   │
│  │  ┌────────────────┐  ┌────────────────┐             │   │
│  │  │ Subnet (Zone-A)│  │ Subnet (Zone-B)│             │   │
│  │  │                │  │                │             │   │
│  │  │  ┌──────────┐  │  │  ┌──────────┐  │             │   │
│  │  │  │   GKE    │  │  │  │   GKE    │  │             │   │
│  │  │  │  Nodes   │  │  │  │  Nodes   │  │             │   │
│  │  │  │          │  │  │  │          │  │             │   │
│  │  │  │ ┌──────┐ │  │  │  │ ┌──────┐ │  │             │   │
│  │  │  │ │Agent │ │  │  │  │ │Agent │ │  │             │   │
│  │  │  │ │ Pods │ │  │  │  │ │ Pods │ │  │             │   │
│  │  │  │ └──┬───┘ │  │  │  │ └──┬───┘ │  │             │   │
│  │  │  └────┼─────┘  │  │  └────┼─────┘  │             │   │
│  │  └───────┼────────┘  └───────┼────────┘             │   │
│  │          │                   │                      │   │
│  │          └───────┬───────────┘                      │   │
│  │                  │                                  │   │
│  │        ┌─────────┴─────────┐                        │   │
│  │        │  Cloud Load Bal.  │                        │   │
│  │        └───────────────────┘                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Secret     │  │  Cloud       │  │  Workload    │     │
│  │   Manager    │  │  Logging     │  │  Identity    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## GKE Cluster Setup

### Create Cluster with gcloud

```bash
# Set project and region
export PROJECT_ID=my-gcp-project
export REGION=us-central1
export CLUSTER_NAME=agentweave-cluster

gcloud config set project $PROJECT_ID

# Create VPC
gcloud compute networks create agentweave-vpc \
  --subnet-mode=custom \
  --bgp-routing-mode=regional

gcloud compute networks subnets create agentweave-subnet \
  --network=agentweave-vpc \
  --region=$REGION \
  --range=10.0.0.0/20 \
  --secondary-range pods=10.4.0.0/14 \
  --secondary-range services=10.0.16.0/20

# Create GKE cluster with Workload Identity
gcloud container clusters create $CLUSTER_NAME \
  --region=$REGION \
  --network=agentweave-vpc \
  --subnetwork=agentweave-subnet \
  --cluster-secondary-range-name=pods \
  --services-secondary-range-name=services \
  --enable-ip-alias \
  --enable-stackdriver-kubernetes \
  --enable-cloud-logging \
  --enable-cloud-monitoring \
  --workload-pool=$PROJECT_ID.svc.id.goog \
  --enable-autoscaling \
  --min-nodes=2 \
  --max-nodes=10 \
  --num-nodes=3 \
  --machine-type=e2-standard-4 \
  --disk-size=100 \
  --disk-type=pd-standard \
  --enable-shielded-nodes \
  --shielded-secure-boot \
  --shielded-integrity-monitoring \
  --addons=HorizontalPodAutoscaling,HttpLoadBalancing,GcePersistentDiskCsiDriver \
  --release-channel=regular

# Get credentials
gcloud container clusters get-credentials $CLUSTER_NAME --region=$REGION
```

### Terraform Configuration

```hcl
# main.tf
module "gke" {
  source  = "terraform-google-modules/kubernetes-engine/google"
  version = "~> 29.0"

  project_id        = var.project_id
  name              = "agentweave-cluster"
  region            = var.region
  regional          = true
  kubernetes_version = "1.28"

  network           = module.vpc.network_name
  subnetwork        = module.vpc.subnets_names[0]
  ip_range_pods     = "pods"
  ip_range_services = "services"

  # Enable Workload Identity
  identity_namespace = "${var.project_id}.svc.id.goog"

  # Node pools
  node_pools = [
    {
      name               = "agentweave-pool"
      machine_type       = "e2-standard-4"
      min_count          = 2
      max_count          = 10
      initial_node_count = 3
      disk_size_gb       = 100
      disk_type          = "pd-standard"
      auto_repair        = true
      auto_upgrade       = true
      preemptible        = false

      node_metadata = "GKE_METADATA"
      workload_metadata_config = {
        mode = "GKE_METADATA"
      }
    }
  ]

  # Monitoring and logging
  monitoring_enable_managed_prometheus = true
  logging_enabled_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  monitoring_enabled_components = ["SYSTEM_COMPONENTS"]

  # Security
  enable_shielded_nodes = true
  master_authorized_networks = [
    {
      cidr_block   = "0.0.0.0/0"
      display_name = "All"
    }
  ]
}

# VPC Module
module "vpc" {
  source  = "terraform-google-modules/network/google"
  version = "~> 8.0"

  project_id   = var.project_id
  network_name = "agentweave-vpc"
  routing_mode = "REGIONAL"

  subnets = [
    {
      subnet_name           = "agentweave-subnet"
      subnet_ip             = "10.0.0.0/20"
      subnet_region         = var.region
      subnet_private_access = true
    }
  ]

  secondary_ranges = {
    agentweave-subnet = [
      {
        range_name    = "pods"
        ip_cidr_range = "10.4.0.0/14"
      },
      {
        range_name    = "services"
        ip_cidr_range = "10.0.16.0/20"
      }
    ]
  }
}
```

## Workload Identity Configuration

### Enable Workload Identity on Cluster

```bash
# Enable Workload Identity (if not done during cluster creation)
gcloud container clusters update $CLUSTER_NAME \
  --region=$REGION \
  --workload-pool=$PROJECT_ID.svc.id.goog
```

### Create Google Service Account

```bash
# Create GSA
gcloud iam service-accounts create agentweave-agent \
  --display-name="AgentWeave Agent Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:agentweave-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:agentweave-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:agentweave-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/monitoring.metricWriter"
```

### Bind KSA to GSA

```bash
# Create namespace
kubectl create namespace agentweave

# Create Kubernetes Service Account
kubectl create serviceaccount agentweave-agent -n agentweave

# Bind KSA to GSA
gcloud iam service-accounts add-iam-policy-binding \
  agentweave-agent@$PROJECT_ID.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:$PROJECT_ID.svc.id.goog[agentweave/agentweave-agent]"

# Annotate KSA
kubectl annotate serviceaccount agentweave-agent \
  -n agentweave \
  iam.gke.io/gcp-service-account=agentweave-agent@$PROJECT_ID.iam.gserviceaccount.com
```

### ServiceAccount YAML

```yaml
# serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agentweave-agent
  namespace: agentweave
  annotations:
    iam.gke.io/gcp-service-account: agentweave-agent@PROJECT_ID.iam.gserviceaccount.com
```

## Secret Manager Integration

### Create Secrets

```bash
# Create secret
echo -n "my-api-key-value" | gcloud secrets create agentweave-api-key \
  --data-file=- \
  --replication-policy=automatic

# Grant access to service account
gcloud secrets add-iam-policy-binding agentweave-api-key \
  --member="serviceAccount:agentweave-agent@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Using External Secrets Operator

Install External Secrets Operator:

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets \
  external-secrets/external-secrets \
  -n external-secrets-system \
  --create-namespace
```

Create SecretStore:

```yaml
# secret-store.yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: gcpsm-secret-store
  namespace: agentweave
spec:
  provider:
    gcpsm:
      projectID: "PROJECT_ID"
      auth:
        workloadIdentity:
          clusterLocation: us-central1
          clusterName: agentweave-cluster
          serviceAccountRef:
            name: agentweave-agent
```

Create ExternalSecret:

```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: agentweave-secrets
  namespace: agentweave
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: gcpsm-secret-store
    kind: SecretStore
  target:
    name: agentweave-secrets
    creationPolicy: Owner
  data:
    - secretKey: api-key
      remoteRef:
        key: agentweave-api-key
    - secretKey: database-url
      remoteRef:
        key: agentweave-database-url
```

## Cloud Logging Integration

### Configure Logging

Cloud Logging is enabled by default on GKE. Configure structured logging:

```yaml
# agent-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentweave-agent
  namespace: agentweave
spec:
  template:
    spec:
      containers:
        - name: agent
          env:
            # Enable structured JSON logging
            - name: AGENTWEAVE_LOG_FORMAT
              value: "json"
            # Set log level
            - name: AGENTWEAVE_LOG_LEVEL
              value: "INFO"
            # Add GCP metadata
            - name: GCP_PROJECT
              value: "PROJECT_ID"
            - name: GKE_CLUSTER
              value: "agentweave-cluster"
```

### Custom Log Filters

Create log-based metrics:

```bash
# Create log-based metric
gcloud logging metrics create agentweave_errors \
  --description="AgentWeave error count" \
  --log-filter='resource.type="k8s_container"
  resource.labels.namespace_name="agentweave"
  severity="ERROR"'
```

## Cloud Monitoring

### Enable Managed Prometheus

```bash
# Enable Managed Prometheus
gcloud container clusters update $CLUSTER_NAME \
  --region=$REGION \
  --enable-managed-prometheus
```

### PodMonitoring for Agents

```yaml
# pod-monitoring.yaml
apiVersion: monitoring.gke.io/v1
kind: PodMonitoring
metadata:
  name: agentweave-agent-monitoring
  namespace: agentweave
spec:
  selector:
    matchLabels:
      app: agentweave-agent
  endpoints:
    - port: metrics
      interval: 30s
      path: /metrics
```

### Create Alerting Policies

```bash
# Create alert policy for high CPU
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="AgentWeave High CPU" \
  --condition-display-name="CPU above 80%" \
  --condition-threshold-value=0.8 \
  --condition-threshold-duration=300s \
  --condition-filter='resource.type="k8s_pod"
    resource.labels.namespace_name="agentweave"
    metric.type="kubernetes.io/pod/cpu/core_usage_time"'
```

## SPIRE on GCP

### SPIRE with GCP Node Attestation

```yaml
# spire-server-config-gcp.yaml
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
    }

    plugins {
        DataStore "sql" {
            plugin_data {
                database_type = "postgres"
                connection_string = "postgresql://spire:password@postgres:5432/spire"
            }
        }

        NodeAttestor "gcp_iit" {
            plugin_data {
                projectid_allow_list = ["PROJECT_ID"]
                use_instance_metadata = true
            }
        }

        KeyManager "memory" {
            plugin_data {}
        }
    }
```

### Persistent Disk for SPIRE

```yaml
# spire-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: spire-server-data
  namespace: spire-system
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: standard-rwo
  resources:
    requests:
      storage: 10Gi
```

## Load Balancing

### Internal Load Balancer

```yaml
# ilb-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: agentweave-ilb
  namespace: agentweave
  annotations:
    cloud.google.com/load-balancer-type: "Internal"
    networking.gke.io/load-balancer-type: "Internal"
spec:
  type: LoadBalancer
  loadBalancerIP: 10.0.1.100  # Optional: Reserve internal IP
  selector:
    app: agentweave-agent
  ports:
    - name: https
      port: 8443
      targetPort: 8443
      protocol: TCP
```

### GKE Ingress with HTTPS

```yaml
# managed-cert.yaml
apiVersion: networking.gke.io/v1
kind: ManagedCertificate
metadata:
  name: agentweave-cert
  namespace: agentweave
spec:
  domains:
    - agents.agentweave.io

---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: agentweave-ingress
  namespace: agentweave
  annotations:
    kubernetes.io/ingress.class: "gce"
    kubernetes.io/ingress.global-static-ip-name: "agentweave-ip"
    networking.gke.io/managed-certificates: "agentweave-cert"
    kubernetes.io/ingress.allow-http: "false"
spec:
  rules:
    - host: agents.agentweave.io
      http:
        paths:
          - path: /*
            pathType: ImplementationSpecific
            backend:
              service:
                name: agentweave-agent
                port:
                  number: 8443
```

Reserve static IP:

```bash
gcloud compute addresses create agentweave-ip \
  --global \
  --ip-version IPV4
```

## Helm Deployment on GKE

Create values file for GKE:

```yaml
# gke-values.yaml
agent:
  name: "gke-agent"
  trustDomain: "agentweave.io"

# ServiceAccount with Workload Identity
serviceAccount:
  create: true
  annotations:
    iam.gke.io/gcp-service-account: agentweave-agent@PROJECT_ID.iam.gserviceaccount.com

# Use GCP Secret Manager
externalSecrets:
  enabled: true
  backend: gcpsm
  projectID: PROJECT_ID

# Cloud Logging
observability:
  logging:
    level: INFO
    format: json
    destination: stdout  # GKE forwards to Cloud Logging

# Monitoring
monitoring:
  enabled: true
  type: managed-prometheus

# Storage
persistence:
  enabled: true
  storageClass: standard-rwo
  size: 10Gi

# Networking
service:
  type: LoadBalancer
  annotations:
    cloud.google.com/load-balancer-type: "Internal"

# Node selector for specific node pool
nodeSelector:
  cloud.google.com/gke-nodepool: agentweave-pool

# Resources
resources:
  requests:
    cpu: 1000m
    memory: 1Gi
  limits:
    cpu: 4000m
    memory: 4Gi
```

Deploy:

```bash
helm install agentweave-agent agentweave/agentweave \
  -f gke-values.yaml \
  -n agentweave \
  --create-namespace
```

## Terraform Complete Example

```hcl
# terraform/main.tf

# GKE Cluster
module "gke" {
  source = "./modules/gke"
  # ... (as shown earlier)
}

# Workload Identity
resource "google_service_account" "agentweave" {
  account_id   = "agentweave-agent"
  display_name = "AgentWeave Agent"
  project      = var.project_id
}

resource "google_project_iam_member" "agentweave_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.agentweave.email}"
}

resource "google_service_account_iam_member" "workload_identity" {
  service_account_id = google_service_account.agentweave.name
  role               = "roles/iam.workloadIdentityUser"
  member             = "serviceAccount:${var.project_id}.svc.id.goog[agentweave/agentweave-agent]"
}

# Kubernetes Service Account
resource "kubernetes_service_account" "agentweave" {
  metadata {
    name      = "agentweave-agent"
    namespace = "agentweave"
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.agentweave.email
    }
  }

  depends_on = [module.gke]
}

# Secret Manager Secrets
resource "google_secret_manager_secret" "api_key" {
  secret_id = "agentweave-api-key"
  project   = var.project_id

  replication {
    automatic = true
  }
}

resource "google_secret_manager_secret_version" "api_key" {
  secret      = google_secret_manager_secret.api_key.id
  secret_data = var.api_key
}

# Helm Release
resource "helm_release" "agentweave" {
  name       = "agentweave-agent"
  repository = "https://charts.agentweave.io"
  chart      = "agentweave"
  namespace  = "agentweave"

  values = [
    templatefile("${path.module}/values.yaml.tpl", {
      project_id        = var.project_id
      service_account   = kubernetes_service_account.agentweave.metadata[0].name
      trust_domain      = var.trust_domain
    })
  ]

  depends_on = [
    module.gke,
    google_service_account_iam_member.workload_identity
  ]
}
```

## Monitoring Dashboards

### Create Custom Dashboard

```bash
# dashboard.json
{
  "displayName": "AgentWeave Agents",
  "mosaicLayout": {
    "columns": 12,
    "tiles": [
      {
        "width": 6,
        "height": 4,
        "widget": {
          "title": "CPU Usage",
          "xyChart": {
            "dataSets": [{
              "timeSeriesQuery": {
                "timeSeriesFilter": {
                  "filter": "resource.type=\"k8s_pod\" resource.labels.namespace_name=\"agentweave\"",
                  "aggregation": {
                    "alignmentPeriod": "60s",
                    "perSeriesAligner": "ALIGN_RATE"
                  }
                }
              }
            }]
          }
        }
      }
    ]
  }
}
```

Create dashboard:

```bash
gcloud monitoring dashboards create --config-from-file=dashboard.json
```

## Best Practices for GCP

1. **Use Workload Identity**: Always prefer Workload Identity over service account keys
2. **Enable Shielded Nodes**: Use shielded GKE nodes for additional security
3. **Regional Clusters**: Deploy regional clusters for high availability
4. **Managed Prometheus**: Use GKE's Managed Prometheus for monitoring
5. **Secret Manager**: Store all secrets in Secret Manager, not in code
6. **VPC-native Clusters**: Always use VPC-native clusters with IP aliasing
7. **Binary Authorization**: Enable for production workloads

## Troubleshooting

### Workload Identity Not Working

```bash
# Verify service account binding
gcloud iam service-accounts get-iam-policy \
  agentweave-agent@$PROJECT_ID.iam.gserviceaccount.com

# Check pod service account
kubectl describe pod -n agentweave -l app=agentweave-agent

# Test from pod
kubectl run -it --rm test --image=google/cloud-sdk:slim \
  --serviceaccount=agentweave-agent \
  -n agentweave \
  -- gcloud auth list
```

### Secret Manager Access Issues

```bash
# Test secret access
gcloud secrets versions access latest --secret=agentweave-api-key

# Check IAM permissions
gcloud secrets get-iam-policy agentweave-api-key
```

## Next Steps

- **[Azure Deployment](azure.md)** - Deploy to Microsoft Azure
- **[Hybrid Deployment](hybrid.md)** - Multi-cloud architecture
- **[Monitoring Guide](../guides/observability.md)** - Advanced monitoring

---

**Related Documentation**:
- [Kubernetes Deployment](kubernetes.md)
- [Helm Charts](helm.md)
- [Security Best Practices](../security.md)
