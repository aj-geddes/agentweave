---
layout: tutorial
title: Cross-Cloud Agent Mesh
permalink: /tutorials/multi-cloud/
nav_order: 7
parent: Tutorials
difficulty: Advanced
duration: 90 minutes
---

# Cross-Cloud Agent Mesh

In this tutorial, you'll build a multi-cloud agent mesh spanning AWS, GCP, and Azure. You'll configure SPIFFE federation, set up cross-cloud networking, and enable secure agent communication across cloud boundaries.

## Learning Objectives

By completing this tutorial, you will:
- Design multi-cloud agent architectures
- Configure SPIFFE trust domain federation
- Set up cross-cloud networking with Tailscale (optional)
- Deploy agents to multiple cloud providers
- Test and debug cross-cloud communication
- Implement production operational patterns

## Prerequisites

Before starting, ensure you have:
- **Completed** [Deploying to Kubernetes](/tutorials/kubernetes-deployment/)
- **Access to multiple cloud providers** (AWS, GCP, Azure)
- **Cloud CLI tools installed** (aws-cli, gcloud, az)
- **Advanced Kubernetes knowledge**
- **Understanding of cloud networking** (VPCs, peering, firewalls)

**Time estimate:** 90 minutes

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Trust Domain: example.org                 │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                │             │             │
        ┌───────▼──────┐  ┌──▼─────┐  ┌────▼──────┐
        │ AWS Region   │  │  GCP   │  │   Azure   │
        │ us-east-1    │  │ us-c1  │  │  eastus   │
        └───────┬──────┘  └──┬─────┘  └────┬──────┘
                │            │              │
        ┌───────▼──────┐  ┌──▼─────┐  ┌────▼──────┐
        │ SPIRE Server │  │ SPIRE  │  │   SPIRE   │
        │ (Primary)    │  │ Server │  │  Server   │
        └───────┬──────┘  └──┬─────┘  └────┬──────┘
                │            │              │
                │   Federation via mTLS    │
                └────────────┼──────────────┘
                             │
                ┌────────────┼────────────┐
                │            │            │
        ┌───────▼──────┐  ┌──▼─────┐  ┌──▼────────┐
        │ Agent Pods   │  │ Agent  │  │  Agent    │
        │ (AWS EKS)    │  │ (GKE)  │  │  (AKS)    │
        └──────────────┘  └────────┘  └───────────┘
```

## Step 1: Multi-Cloud Design Decisions

### Trust Domain Strategy

**Option A: Single Trust Domain (Recommended)**
- One trust domain: `example.org`
- All clouds share the same root of trust
- Simplifies authorization policies
- Easier to manage

**Option B: Multiple Trust Domains with Federation**
- Separate domains: `aws.example.org`, `gcp.example.org`, `azure.example.org`
- Explicit federation between domains
- Stronger isolation
- More complex policy management

For this tutorial, we'll use **Option A** (single trust domain).

### Networking Strategy

**Option A: Cloud VPN/Peering**
- AWS VPN ↔ GCP Cloud VPN ↔ Azure VPN Gateway
- Native cloud networking
- Higher cost, more complexity

**Option B: Service Mesh (Tailscale)**
- Overlay network across clouds
- Simpler setup
- Lower cost
- NAT traversal built-in

For this tutorial, we'll show **both options**.

### SPIRE Deployment Strategy

**Option A: Centralized SPIRE Server**
- Single SPIRE server in one cloud
- SPIRE agents in all clouds connect to it
- Simpler, single source of truth
- Single point of failure

**Option B: Federated SPIRE Servers**
- SPIRE server in each cloud
- Servers federate with each other
- Higher availability
- More complex

We'll use **Option B** (federated).

## Step 2: Set Up Cloud Infrastructure

### AWS - Create EKS Cluster

```bash
# Set region
export AWS_REGION=us-east-1

# Create EKS cluster
eksctl create cluster \
  --name agentweave-aws \
  --region $AWS_REGION \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --managed

# Configure kubectl context
aws eks update-kubeconfig --name agentweave-aws --region $AWS_REGION

# Rename context for clarity
kubectl config rename-context \
  arn:aws:eks:$AWS_REGION:$(aws sts get-caller-identity --query Account --output text):cluster/agentweave-aws \
  aws-cluster
```

### GCP - Create GKE Cluster

```bash
# Set project and zone
export GCP_PROJECT=your-project-id
export GCP_ZONE=us-central1-a

gcloud config set project $GCP_PROJECT

# Create GKE cluster
gcloud container clusters create agentweave-gcp \
  --zone $GCP_ZONE \
  --num-nodes 3 \
  --machine-type e2-medium \
  --enable-ip-alias

# Get credentials
gcloud container clusters get-credentials agentweave-gcp --zone $GCP_ZONE

# Rename context
kubectl config rename-context \
  gke_${GCP_PROJECT}_${GCP_ZONE}_agentweave-gcp \
  gcp-cluster
```

### Azure - Create AKS Cluster

```bash
# Set variables
export AZURE_RESOURCE_GROUP=agentweave-rg
export AZURE_LOCATION=eastus
export AZURE_CLUSTER_NAME=agentweave-azure

# Create resource group
az group create --name $AZURE_RESOURCE_GROUP --location $AZURE_LOCATION

# Create AKS cluster
az aks create \
  --resource-group $AZURE_RESOURCE_GROUP \
  --name $AZURE_CLUSTER_NAME \
  --node-count 3 \
  --node-vm-size Standard_B2s \
  --enable-managed-identity \
  --generate-ssh-keys

# Get credentials
az aks get-credentials \
  --resource-group $AZURE_RESOURCE_GROUP \
  --name $AZURE_CLUSTER_NAME

# Rename context
kubectl config rename-context $AZURE_CLUSTER_NAME azure-cluster
```

### Verify All Clusters

```bash
# List contexts
kubectl config get-contexts

# Should see:
# aws-cluster
# gcp-cluster
# azure-cluster

# Test each cluster
kubectl --context aws-cluster get nodes
kubectl --context gcp-cluster get nodes
kubectl --context azure-cluster get nodes
```

## Step 3: Deploy SPIRE with Federation

### Deploy SPIRE to AWS (Primary)

```bash
kubectl --context aws-cluster create namespace spire

# Create SPIRE server with federation enabled
cat <<EOF | kubectl --context aws-cluster apply -f -
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

      # Federation configuration
      federation {
        bundle_endpoint {
          address = "0.0.0.0"
          port = 8443
        }
      }
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
            "agentweave-aws" = {
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
    }
EOF

# Apply SPIRE server deployment (use manifests from Kubernetes tutorial)
# Then expose federation endpoint
cat <<EOF | kubectl --context aws-cluster apply -f -
apiVersion: v1
kind: Service
metadata:
  name: spire-server-federation
  namespace: spire
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
spec:
  type: LoadBalancer
  ports:
    - name: federation
      port: 8443
      targetPort: 8443
  selector:
    app: spire-server
EOF

# Get federation endpoint
AWS_FEDERATION_ENDPOINT=$(kubectl --context aws-cluster get svc -n spire spire-server-federation -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')
echo "AWS Federation Endpoint: https://$AWS_FEDERATION_ENDPOINT:8443"
```

### Deploy SPIRE to GCP

```bash
kubectl --context gcp-cluster create namespace spire

# Similar SPIRE deployment with federation
# Update trust_domain to example.org
# Expose federation endpoint via GCP Load Balancer

GCP_FEDERATION_ENDPOINT=$(kubectl --context gcp-cluster get svc -n spire spire-server-federation -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "GCP Federation Endpoint: https://$GCP_FEDERATION_ENDPOINT:8443"
```

### Deploy SPIRE to Azure

```bash
kubectl --context azure-cluster create namespace spire

# Similar SPIRE deployment
# Expose via Azure Load Balancer

AZURE_FEDERATION_ENDPOINT=$(kubectl --context azure-cluster get svc -n spire spire-server-federation -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Azure Federation Endpoint: https://$AZURE_FEDERATION_ENDPOINT:8443"
```

### Configure Federation Between SPIRE Servers

Get bundle from each SPIRE server and share with others:

```bash
# Get AWS bundle
AWS_SERVER_POD=$(kubectl --context aws-cluster get pod -n spire -l app=spire-server -o jsonpath='{.items[0].metadata.name}')
kubectl --context aws-cluster exec -n spire $AWS_SERVER_POD -- \
  /opt/spire/bin/spire-server bundle show -format spiffe > aws-bundle.json

# Get GCP bundle
GCP_SERVER_POD=$(kubectl --context gcp-cluster get pod -n spire -l app=spire-server -o jsonpath='{.items[0].metadata.name}')
kubectl --context gcp-cluster exec -n spire $GCP_SERVER_POD -- \
  /opt/spire/bin/spire-server bundle show -format spiffe > gcp-bundle.json

# Get Azure bundle
AZURE_SERVER_POD=$(kubectl --context azure-cluster get pod -n spire -l app=spire-server -o jsonpath='{.items[0].metadata.name}')
kubectl --context azure-cluster exec -n spire $AZURE_SERVER_POD -- \
  /opt/spire/bin/spire-server bundle show -format spiffe > azure-bundle.json

# Set federation relationships
# AWS trusts GCP and Azure
kubectl --context aws-cluster exec -n spire $AWS_SERVER_POD -- \
  /opt/spire/bin/spire-server bundle set -format spiffe -id spiffe://example.org < gcp-bundle.json

kubectl --context aws-cluster exec -n spire $AWS_SERVER_POD -- \
  /opt/spire/bin/spire-server bundle set -format spiffe -id spiffe://example.org < azure-bundle.json

# Repeat for GCP and Azure...
```

## Step 4: Cross-Cloud Networking with Tailscale

Tailscale provides a simple overlay network across clouds.

### Install Tailscale on All Clusters

```bash
# AWS
kubectl --context aws-cluster apply -f https://raw.githubusercontent.com/tailscale/tailscale/main/docs/k8s/tailscale.yaml

# GCP
kubectl --context gcp-cluster apply -f https://raw.githubusercontent.com/tailscale/tailscale/main/docs/k8s/tailscale.yaml

# Azure
kubectl --context azure-cluster apply -f https://raw.githubusercontent.com/tailscale/tailscale/main/docs/k8s/tailscale.yaml
```

### Configure Tailscale Subnet Routers

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tailscale-config
  namespace: tailscale
data:
  TS_ROUTES: "10.0.0.0/16"  # Your cluster pod CIDR
  TS_DEST_IP: "100.64.0.1"  # Tailscale IP to route to
---
apiVersion: apps/v1
kind: DaemonSet
metadata:
  name: tailscale-router
  namespace: tailscale
spec:
  selector:
    matchLabels:
      app: tailscale-router
  template:
    metadata:
      labels:
        app: tailscale-router
    spec:
      containers:
      - name: tailscale
        image: tailscale/tailscale:latest
        env:
        - name: TS_AUTHKEY
          valueFrom:
            secretKeyRef:
              name: tailscale-auth
              key: TS_AUTHKEY
        - name: TS_ROUTES
          valueFrom:
            configMapKeyRef:
              name: tailscale-config
              key: TS_ROUTES
        securityContext:
          privileged: true
```

Apply to all clusters and approve subnet routes in Tailscale admin console.

## Step 5: Deploy Agents to All Clouds

### AWS Agent Deployment

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentweave-config
  namespace: agentweave
data:
  config.yaml: |
    identity:
      spiffe_id: "spiffe://example.org/region/aws-us-east-1/agent"
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

      # Advertise address for cross-cloud communication
      advertise_address: "aws-agent.tailnet-name.ts.net:8443"

    # Registry of agents in other clouds
    agent_registry:
      gcp_agent:
        spiffe_id: "spiffe://example.org/region/gcp-us-central1/agent"
        address: "https://gcp-agent.tailnet-name.ts.net:8443"
      azure_agent:
        spiffe_id: "spiffe://example.org/region/azure-eastus/agent"
        address: "https://azure-agent.tailnet-name.ts.net:8443"

    observability:
      logging:
        level: "INFO"
        format: "json"
        default_fields:
          cloud: "aws"
          region: "us-east-1"
      metrics:
        enabled: true
        labels:
          cloud: "aws"
          region: "us-east-1"
      tracing:
        enabled: true
        service_name: "aws-agent"

    metadata:
      name: "AWS Agent"
      cloud: "aws"
      region: "us-east-1"
```

### GCP Agent Deployment

Similar configuration with GCP-specific values:

```yaml
# ... same structure ...
    identity:
      spiffe_id: "spiffe://example.org/region/gcp-us-central1/agent"
    server:
      advertise_address: "gcp-agent.tailnet-name.ts.net:8443"
    agent_registry:
      aws_agent:
        spiffe_id: "spiffe://example.org/region/aws-us-east-1/agent"
        address: "https://aws-agent.tailnet-name.ts.net:8443"
      azure_agent:
        spiffe_id: "spiffe://example.org/region/azure-eastus/agent"
        address: "https://azure-agent.tailnet-name.ts.net:8443"
    metadata:
      cloud: "gcp"
      region: "us-central1"
```

### Azure Agent Deployment

Similar configuration for Azure.

### Deploy All Agents

```bash
# AWS
kubectl --context aws-cluster apply -f aws-agent-deployment.yaml

# GCP
kubectl --context gcp-cluster apply -f gcp-agent-deployment.yaml

# Azure
kubectl --context azure-cluster apply -f azure-agent-deployment.yaml

# Verify all agents are running
kubectl --context aws-cluster get pods -n agentweave
kubectl --context gcp-cluster get pods -n agentweave
kubectl --context azure-cluster get pods -n agentweave
```

## Step 6: Test Cross-Cloud Communication

### Register MagicDNS Names in Tailscale

If using Tailscale, register DNS names for agents:
- `aws-agent.tailnet.ts.net` → AWS agent pod IP
- `gcp-agent.tailnet.ts.net` → GCP agent pod IP
- `azure-agent.tailnet.ts.net` → Azure agent pod IP

### Test AWS → GCP Communication

```bash
# Port forward to AWS agent
kubectl --context aws-cluster port-forward -n agentweave svc/agentweave-agent 8443:8443

# Call GCP agent from AWS agent
agentweave-cli call \
  --agent spiffe://example.org/region/aws-us-east-1/agent \
  --address https://localhost:8443 \
  --capability call_remote \
  --params '{
    "target_agent": "spiffe://example.org/region/gcp-us-central1/agent",
    "target_address": "https://gcp-agent.tailnet.ts.net:8443",
    "capability": "ping"
  }'
```

### Test GCP → Azure Communication

```bash
kubectl --context gcp-cluster port-forward -n agentweave svc/agentweave-agent 8444:8443

agentweave-cli call \
  --agent spiffe://example.org/region/gcp-us-central1/agent \
  --address https://localhost:8444 \
  --capability call_remote \
  --params '{
    "target_agent": "spiffe://example.org/region/azure-eastus/agent",
    "target_address": "https://azure-agent.tailnet.ts.net:8443",
    "capability": "ping"
  }'
```

### Test Round-Trip: AWS → GCP → Azure → AWS

Create a capability that chains calls across clouds:

```python
@capability(name="cross_cloud_test")
async def cross_cloud_test(self, context: AgentContext):
    """Test cross-cloud communication chain."""

    # AWS calls GCP
    gcp_response = await self.call_agent(
        agent_spiffe_id="spiffe://example.org/region/gcp-us-central1/agent",
        agent_address="https://gcp-agent.tailnet.ts.net:8443",
        capability="forward_to_azure",
        params={"message": "Hello from AWS"}
    )

    return {
        "cloud": "aws",
        "gcp_response": gcp_response
    }
```

## Step 7: Monitoring Cross-Cloud Agents

### Centralized Prometheus

Deploy Prometheus in one cloud and scrape all agents:

```yaml
# prometheus-config.yaml
scrape_configs:
  - job_name: 'aws-agents'
    kubernetes_sd_configs:
      - role: pod
        api_server: https://aws-eks-api-server
        tls_config:
          ca_file: /etc/prometheus/aws-ca.pem
        bearer_token_file: /etc/prometheus/aws-token
        namespaces:
          names:
            - agentweave

  - job_name: 'gcp-agents'
    kubernetes_sd_configs:
      - role: pod
        api_server: https://gcp-gke-api-server
        # ... similar config ...

  - job_name: 'azure-agents'
    kubernetes_sd_configs:
      - role: pod
        api_server: https://azure-aks-api-server
        # ... similar config ...
```

### Distributed Tracing Across Clouds

With OpenTelemetry, traces automatically propagate:

```
Trace: cross-cloud-request-xyz
├─ Span: aws-agent.process [200ms]
│  ├─ Span: call_agent(gcp-agent) [180ms]
│  │  ├─ Span: network.dial [20ms]
│  │  ├─ Span: mtls.handshake [15ms]
│  │  ├─ Span: gcp-agent.process [130ms]
│  │  │  ├─ Span: call_agent(azure-agent) [110ms]
│  │  │  │  ├─ Span: network.dial [18ms]
│  │  │  │  ├─ Span: azure-agent.process [80ms]
│  │  │  │  └─ Span: response [5ms]
│  │  │  └─ Span: aggregate [10ms]
│  │  └─ Span: deserialize [3ms]
│  └─ Span: build_response [5ms]
```

## Step 8: Operational Patterns

### Disaster Recovery

If one cloud region fails:

```yaml
# Configure fallback agents in agent_registry
agent_registry:
  primary_worker:
    spiffe_id: "spiffe://example.org/region/aws-us-east-1/worker"
    address: "https://aws-worker.tailnet.ts.net:8443"
  fallback_worker:
    spiffe_id: "spiffe://example.org/region/gcp-us-central1/worker"
    address: "https://gcp-worker.tailnet.ts.net:8443"
```

Implement failover logic:

```python
async def call_with_fallback(self, primary, fallback, capability, params):
    try:
        return await self.call_agent(
            agent_spiffe_id=primary['spiffe_id'],
            agent_address=primary['address'],
            capability=capability,
            params=params,
            timeout=10.0
        )
    except Exception as e:
        self.logger.warning(f"Primary failed, trying fallback: {e}")
        return await self.call_agent(
            agent_spiffe_id=fallback['spiffe_id'],
            agent_address=fallback['address'],
            capability=capability,
            params=params,
            timeout=10.0
        )
```

### Load Balancing Across Clouds

Use DNS-based load balancing or service mesh:

```yaml
# Tailscale load balancing
apiVersion: v1
kind: Service
metadata:
  name: agentweave-global
  annotations:
    tailscale.com/expose: "true"
    tailscale.com/hostname: "agentweave-global"
spec:
  type: LoadBalancer
  selector:
    app: agentweave-agent
  ports:
    - port: 8443
```

## Step 9: Security Best Practices

### Network Segmentation

Use network policies to restrict cross-cloud traffic:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-cross-cloud
  namespace: agentweave
spec:
  podSelector:
    matchLabels:
      app: agentweave-agent
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # Only allow from known SPIFFE IDs (enforced at mTLS layer)
  - from:
    - podSelector: {}  # Same namespace
    - ipBlock:
        cidr: 100.64.0.0/10  # Tailscale range
  egress:
  # Allow to other clouds
  - to:
    - ipBlock:
        cidr: 100.64.0.0/10  # Tailscale range
  # Allow to SPIRE and OPA
  - to:
    - namespaceSelector:
        matchLabels:
          name: spire
  - to:
    - namespaceSelector:
        matchLabels:
          name: opa
```

### Authorization Policies for Multi-Cloud

```rego
package agentweave.authz

default allow = false

# Allow from same cloud region
allow {
    caller_region := split(input.caller.spiffe_id, "/")[3]
    our_region := split(input.agent.spiffe_id, "/")[3]
    caller_region == our_region
}

# Allow specific cross-cloud calls
allow {
    # AWS orchestrator can call GCP workers
    input.caller.spiffe_id == "spiffe://example.org/region/aws-us-east-1/orchestrator"
    startswith(input.agent.spiffe_id, "spiffe://example.org/region/gcp-us-central1/worker")
}

# Allow cross-cloud for specific capabilities only
allow {
    input.request.method in ["ping", "health_check", "status"]
}
```

## Summary

You've built a cross-cloud agent mesh! You've learned:

- Multi-cloud architecture design
- SPIFFE trust domain federation
- Cross-cloud networking with Tailscale
- Deploying agents to AWS, GCP, and Azure
- Testing cross-cloud communication
- Distributed tracing across clouds
- Operational patterns for multi-cloud
- Security best practices

## Exercises

1. **Add a fourth cloud** (Oracle Cloud, IBM Cloud, etc.)
2. **Implement geo-routing** - route to nearest agent
3. **Create a global orchestrator** that load balances across clouds
4. **Set up cross-cloud backup** and disaster recovery
5. **Implement latency-based routing** using metrics

## What's Next?

- **[How-To: Multi-Cloud Operations](/guides/multi-cloud-ops/)** - Advanced patterns
- **[Security: Compliance](/security/compliance/)** - Multi-cloud compliance
- **[Examples: Global Data Pipeline](/examples/global-pipeline/)** - Real-world multi-cloud
- **[Troubleshooting: Connections](/troubleshooting/connections/)** - Debug cross-cloud issues

## Troubleshooting

### Cannot establish cross-cloud connection
- Verify Tailscale is running in all clusters
- Check DNS resolution for agent addresses
- Verify firewall rules allow egress/ingress
- Test connectivity with `kubectl exec ... -- curl`

### Federation not working
- Verify bundles are correctly shared between SPIRE servers
- Check SPIRE server logs for federation errors
- Ensure federation endpoints are accessible
- Test with `spire-server bundle show`

### High latency cross-cloud
- Use geo-routing to minimize round-trips
- Consider caching responses
- Deploy agents closer to users
- Use async patterns where possible

See [Troubleshooting Guide](/troubleshooting/) for more help.
