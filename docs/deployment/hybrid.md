---
layout: page
title: Hybrid/Multi-Cloud Deployment
description: Deploy AgentWeave agents across multiple cloud providers and on-premises
nav_order: 7
parent: Deployment
---

# Hybrid and Multi-Cloud Deployment Guide

This guide covers deploying AgentWeave agents across multiple cloud providers and on-premises data centers using SPIFFE federation and Tailscale networking.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

Hybrid and multi-cloud deployments allow AgentWeave agents to communicate securely across:
- Multiple cloud providers (AWS, GCP, Azure)
- On-premises data centers
- Edge locations
- Different organizational boundaries

## Architecture Patterns

### Pattern 1: Federated SPIFFE Trust Domains

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Multi-Cloud Architecture                        │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │   AWS (EKS)      │  │   GCP (GKE)      │  │  Azure (AKS)     │  │
│  │                  │  │                  │  │                  │  │
│  │  Trust Domain:   │  │  Trust Domain:   │  │  Trust Domain:   │  │
│  │  aws.company.com │  │  gcp.company.com │  │  az.company.com  │  │
│  │                  │  │                  │  │                  │  │
│  │  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │  │
│  │  │SPIRE Server│  │  │  │SPIRE Server│  │  │  │SPIRE Server│  │  │
│  │  └─────┬──────┘  │  │  └─────┬──────┘  │  │  └─────┬──────┘  │  │
│  │        │         │  │        │         │  │        │         │  │
│  │  ┌─────┴──────┐  │  │  ┌─────┴──────┐  │  │  ┌─────┴──────┐  │  │
│  │  │  Agents    │  │  │  │  Agents    │  │  │  │  Agents    │  │  │
│  │  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│           │                     │                     │             │
│           └─────────────────────┼─────────────────────┘             │
│                                 │                                   │
│                    ┌────────────┴────────────┐                      │
│                    │  SPIFFE Federation      │                      │
│                    │  (Trust Bundle Exchange)│                      │
│                    └─────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────┘
```

### Pattern 2: Tailscale Mesh Network

```
┌─────────────────────────────────────────────────────────────────────┐
│                   Tailscale Mesh Network                            │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │   AWS            │  │   On-Premises    │  │   GCP            │  │
│  │                  │  │                  │  │                  │  │
│  │  ┌────────────┐  │  │  ┌────────────┐  │  │  ┌────────────┐  │  │
│  │  │  Agents    │──┼──┼──│  Agents    │──┼──┼──│  Agents    │  │  │
│  │  │ +Tailscale │  │  │  │ +Tailscale │  │  │  │ +Tailscale │  │  │
│  │  └────────────┘  │  │  └────────────┘  │  │  └────────────┘  │  │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘  │
│           │                     │                     │             │
│           └─────────────────────┼─────────────────────┘             │
│                                 │                                   │
│                    ┌────────────┴────────────┐                      │
│                    │  Tailscale Control      │                      │
│                    │  Plane (Coordination)   │                      │
│                    └─────────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────┘
```

## SPIFFE Federation Setup

### Overview

SPIFFE federation allows agents in different trust domains to verify each other's identities.

### Step 1: Configure Federation on Each SPIRE Server

**AWS SPIRE Server (aws.company.com)**:

```yaml
# spire-server-config-aws.yaml
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
        trust_domain = "aws.company.com"
        data_dir = "/run/spire/data"

        federation {
            bundle_endpoint {
                address = "0.0.0.0"
                port = 8443
                acme {
                    domain_name = "spire-aws.company.com"
                    email = "admin@company.com"
                }
            }
            federates_with "gcp.company.com" {
                bundle_endpoint_url = "https://spire-gcp.company.com:8443"
                bundle_endpoint_profile "https_web" {}
            }
            federates_with "azure.company.com" {
                bundle_endpoint_url = "https://spire-azure.company.com:8443"
                bundle_endpoint_profile "https_web" {}
            }
        }
    }

    plugins {
        DataStore "sql" {
            plugin_data {
                database_type = "postgres"
                connection_string = "postgresql://spire:password@postgres:5432/spire"
            }
        }

        NodeAttestor "aws_iid" {
            plugin_data {
                account_ids_for_local_validation = ["123456789012"]
            }
        }

        KeyManager "disk" {
            plugin_data {
                keys_path = "/run/spire/data/keys.json"
            }
        }
    }
```

**GCP SPIRE Server (gcp.company.com)**:

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
        trust_domain = "gcp.company.com"
        data_dir = "/run/spire/data"

        federation {
            bundle_endpoint {
                address = "0.0.0.0"
                port = 8443
                acme {
                    domain_name = "spire-gcp.company.com"
                    email = "admin@company.com"
                }
            }
            federates_with "aws.company.com" {
                bundle_endpoint_url = "https://spire-aws.company.com:8443"
                bundle_endpoint_profile "https_web" {}
            }
            federates_with "azure.company.com" {
                bundle_endpoint_url = "https://spire-azure.company.com:8443"
                bundle_endpoint_profile "https_web" {}
            }
        }
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
                projectid_allow_list = ["my-gcp-project"]
            }
        }

        KeyManager "disk" {
            plugin_data {
                keys_path = "/run/spire/data/keys.json"
            }
        }
    }
```

### Step 2: Expose Bundle Endpoints

**AWS - Expose via LoadBalancer**:

```yaml
# spire-bundle-service-aws.yaml
apiVersion: v1
kind: Service
metadata:
  name: spire-bundle-endpoint
  namespace: spire-system
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internet-facing"
    external-dns.alpha.kubernetes.io/hostname: spire-aws.company.com
spec:
  type: LoadBalancer
  selector:
    app: spire-server
  ports:
    - name: bundle-endpoint
      port: 8443
      targetPort: 8443
      protocol: TCP
```

**GCP - Expose via LoadBalancer**:

```yaml
# spire-bundle-service-gcp.yaml
apiVersion: v1
kind: Service
metadata:
  name: spire-bundle-endpoint
  namespace: spire-system
  annotations:
    cloud.google.com/load-balancer-type: "External"
    external-dns.alpha.kubernetes.io/hostname: spire-gcp.company.com
spec:
  type: LoadBalancer
  selector:
    app: spire-server
  ports:
    - name: bundle-endpoint
      port: 8443
      targetPort: 8443
      protocol: TCP
```

### Step 3: Configure Agent to Trust Multiple Domains

```yaml
# agent-config-federated.yaml
agent:
  name: "federated-agent"
  trust_domain: "aws.company.com"

identity:
  provider: "spiffe"
  allowed_trust_domains:
    - "aws.company.com"
    - "gcp.company.com"
    - "azure.company.com"

authorization:
  provider: "opa"
  policy_path: "agentweave/authz/federated"
```

### Step 4: OPA Policy for Federation

```rego
# federated-authz.rego
package agentweave.authz.federated

import rego.v1

default allow := false

# Allow calls within same trust domain
allow if {
    same_trust_domain
}

# Allow calls from federated trust domains
allow if {
    federated_trust_domain
    valid_action
}

same_trust_domain if {
    caller_domain := split(input.caller_spiffe_id, "/")[2]
    callee_domain := split(input.callee_spiffe_id, "/")[2]
    caller_domain == callee_domain
}

federated_trust_domain if {
    caller_domain := split(input.caller_spiffe_id, "/")[2]
    caller_domain in data.federation.allowed_domains
}

valid_action if {
    # Check action is allowed for the caller
    input.action in data.federation.allowed_actions[input.caller_spiffe_id]
}
```

### Step 5: Federation Data Configuration

```yaml
# federation-data.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: opa-federation-data
  namespace: agentweave
data:
  data.json: |
    {
      "federation": {
        "allowed_domains": [
          "aws.company.com",
          "gcp.company.com",
          "azure.company.com"
        ],
        "allowed_actions": {
          "spiffe://aws.company.com/agent/orchestrator": ["search", "process"],
          "spiffe://gcp.company.com/agent/search": ["search"],
          "spiffe://azure.company.com/agent/processor": ["process"]
        }
      }
    }
```

## Tailscale Integration

### Install Tailscale Operator

```bash
# Add Tailscale Helm repo
helm repo add tailscale https://pkgs.tailscale.com/helmcharts
helm repo update

# Create secret with Tailscale auth key
kubectl create secret generic tailscale-auth \
  -n tailscale \
  --from-literal=TS_AUTHKEY=tskey-auth-xxxxx

# Install operator
helm install tailscale-operator tailscale/tailscale-operator \
  -n tailscale \
  --create-namespace \
  --set-string oauth.clientId="<client-id>" \
  --set-string oauth.clientSecret="<client-secret>"
```

### Deploy Agent with Tailscale Sidecar

```yaml
# agent-with-tailscale.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentweave-agent
  namespace: agentweave
spec:
  template:
    metadata:
      annotations:
        tailscale.com/hostname: "agent-aws-prod"
        tailscale.com/tags: "tag:agentweave,tag:production"
    spec:
      serviceAccountName: agentweave-agent
      containers:
        # Main agent container
        - name: agent
          image: my-org/agentweave-agent:1.0.0
          env:
            - name: TAILSCALE_ENABLED
              value: "true"
            # Other agents reachable via Tailscale hostnames
            - name: SEARCH_AGENT_URL
              value: "https://agent-gcp-search:8443"
            - name: PROCESSOR_AGENT_URL
              value: "https://agent-azure-processor:8443"

        # Tailscale sidecar
        - name: tailscale
          image: tailscale/tailscale:latest
          env:
            - name: TS_AUTHKEY
              valueFrom:
                secretKeyRef:
                  name: tailscale-auth
                  key: TS_AUTHKEY
            - name: TS_KUBE_SECRET
              value: "tailscale-state"
            - name: TS_USERSPACE
              value: "true"
            - name: TS_HOSTNAME
              value: "agent-aws-prod"
            - name: TS_ACCEPT_DNS
              value: "true"
          securityContext:
            capabilities:
              add:
                - NET_ADMIN
```

### Tailscale ACLs

Configure Tailscale ACLs to control access:

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["tag:agentweave"],
      "dst": ["tag:agentweave:8443"]
    },
    {
      "action": "accept",
      "src": ["tag:agentweave"],
      "dst": ["tag:agentweave:9090"]
    }
  ],
  "tagOwners": {
    "tag:agentweave": ["admin@company.com"],
    "tag:production": ["admin@company.com"],
    "tag:staging": ["admin@company.com"]
  }
}
```

## Cross-Cloud Networking

### Option 1: VPN Peering

**AWS VPN to GCP**:

```bash
# Create Customer Gateway in AWS
aws ec2 create-customer-gateway \
  --type ipsec.1 \
  --public-ip <GCP_VPN_IP> \
  --bgp-asn 65000

# Create VPN Connection
aws ec2 create-vpn-connection \
  --type ipsec.1 \
  --customer-gateway-id <cgw-id> \
  --vpn-gateway-id <vgw-id>
```

**GCP VPN to AWS**:

```bash
# Create VPN gateway
gcloud compute vpn-gateways create aws-vpn-gateway \
  --network agentweave-vpc \
  --region us-central1

# Create VPN tunnel
gcloud compute vpn-tunnels create aws-tunnel-1 \
  --peer-address <AWS_VPN_IP> \
  --shared-secret <SHARED_SECRET> \
  --ike-version 2 \
  --vpn-gateway aws-vpn-gateway \
  --region us-central1
```

### Option 2: Cloud Interconnect

For high-bandwidth, low-latency requirements:

- **AWS Direct Connect** to on-premises
- **GCP Cloud Interconnect** to on-premises
- **Azure ExpressRoute** to on-premises

### Option 3: Service Mesh (Istio)

Deploy Istio multi-cluster for unified service mesh:

```yaml
# istio-multicluster-config.yaml
apiVersion: install.istio.io/v1alpha1
kind: IstioOperator
metadata:
  name: istio-controlplane
spec:
  values:
    global:
      meshID: agentweave-mesh
      multiCluster:
        clusterName: aws-cluster
      network: aws-network
```

## Disaster Recovery Patterns

### Active-Active Multi-Region

Deploy agents in multiple regions with load balancing:

```yaml
# global-load-balancer.yaml
apiVersion: v1
kind: Service
metadata:
  name: agentweave-global
  annotations:
    # AWS Route53
    external-dns.alpha.kubernetes.io/hostname: agents.company.com
    # Or GCP Global LB
    cloud.google.com/load-balancer-type: "External"
    networking.gke.io/load-balancer-type: "External"
spec:
  type: LoadBalancer
  selector:
    app: agentweave-agent
  ports:
    - port: 8443
      targetPort: 8443
```

### Failover Configuration

```yaml
# values-dr.yaml
replicaCount: 3

# Pod topology spread across zones and regions
topologySpreadConstraints:
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: DoNotSchedule
    labelSelector:
      matchLabels:
        app: agentweave-agent
  - maxSkew: 2
    topologyKey: topology.kubernetes.io/region
    whenUnsatisfiable: ScheduleAnyway
    labelSelector:
      matchLabels:
        app: agentweave-agent

# Pod disruption budget
podDisruptionBudget:
  enabled: true
  minAvailable: 2
```

## Latency Optimization

### Edge Caching with CDN

Deploy agents at edge locations:

```yaml
# edge-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentweave-edge
  namespace: agentweave
spec:
  replicas: 1
  selector:
    matchLabels:
      app: agentweave-edge
      tier: edge
  template:
    metadata:
      labels:
        app: agentweave-edge
        tier: edge
    spec:
      # Prefer edge nodes
      affinity:
        nodeAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              preference:
                matchExpressions:
                  - key: node.kubernetes.io/instance-type
                    operator: In
                    values:
                      - edge
                      - local
```

### Regional Routing

Use GeoDNS to route to nearest region:

```yaml
# geodns-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: geodns-config
data:
  Corefile: |
    .:53 {
        errors
        health
        ready

        geo {
            # Route US traffic to AWS us-east-1
            US {
                answer agents-aws-us-east.company.com
            }
            # Route EU traffic to GCP europe-west
            EU {
                answer agents-gcp-eu.company.com
            }
            # Default to Azure
            default {
                answer agents-azure-global.company.com
            }
        }

        forward . /etc/resolv.conf
        cache 30
    }
```

## Monitoring Multi-Cloud Deployments

### Centralized Monitoring with Prometheus Federation

```yaml
# prometheus-federation.yaml
global:
  scrape_interval: 15s

scrape_configs:
  # Federate from AWS cluster
  - job_name: 'federate-aws'
    scrape_interval: 30s
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job="agentweave-agent"}'
    static_configs:
      - targets:
          - 'prometheus-aws.company.com:9090'
        labels:
          cluster: 'aws'
          region: 'us-east-1'

  # Federate from GCP cluster
  - job_name: 'federate-gcp'
    scrape_interval: 30s
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job="agentweave-agent"}'
    static_configs:
      - targets:
          - 'prometheus-gcp.company.com:9090'
        labels:
          cluster: 'gcp'
          region: 'us-central1'

  # Federate from Azure cluster
  - job_name: 'federate-azure'
    scrape_interval: 30s
    honor_labels: true
    metrics_path: '/federate'
    params:
      'match[]':
        - '{job="agentweave-agent"}'
    static_configs:
      - targets:
          - 'prometheus-azure.company.com:9090'
        labels:
          cluster: 'azure'
          region: 'eastus'
```

### Distributed Tracing

Configure OpenTelemetry for multi-cloud tracing:

```yaml
# otel-collector-config.yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 10s

  # Add cloud and region metadata
  resource:
    attributes:
      - key: cloud.provider
        value: aws
        action: upsert
      - key: cloud.region
        value: us-east-1
        action: upsert

exporters:
  # Send to centralized Jaeger
  jaeger:
    endpoint: jaeger-collector.company.com:14250
    tls:
      insecure: false
      ca_file: /etc/ssl/certs/ca.crt

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [resource, batch]
      exporters: [jaeger]
```

## Security Considerations

### Cross-Cloud Network Security

1. **Encrypted Transit**: Always use mTLS with SPIFFE
2. **Network Segmentation**: Isolate agent traffic with VPCs
3. **Firewall Rules**: Whitelist only necessary ports (8443, 8081)
4. **DDoS Protection**: Use cloud-native DDoS protection
5. **WAF**: Deploy Web Application Firewall for ingress

### Identity Federation Security

1. **Trust Domain Validation**: Carefully validate federated domains
2. **Policy Review**: Regular review of cross-domain policies
3. **Audit Logging**: Enable comprehensive audit logging
4. **Certificate Rotation**: Automate SPIFFE certificate rotation
5. **Least Privilege**: Grant minimum necessary cross-domain access

## Cost Optimization

### Data Transfer Costs

```yaml
# Minimize cross-region traffic with affinity
affinity:
  podAffinity:
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector:
            matchLabels:
              app: agentweave-agent
          topologyKey: topology.kubernetes.io/region
```

### Spot Instances for Non-Critical Workloads

**AWS**:
```yaml
nodeSelector:
  eks.amazonaws.com/capacityType: SPOT
```

**GCP**:
```yaml
nodeSelector:
  cloud.google.com/gke-preemptible: "true"
```

**Azure**:
```yaml
nodeSelector:
  kubernetes.azure.com/scalesetpriority: spot
```

## Troubleshooting

### Federation Not Working

```bash
# Check bundle endpoint accessibility
curl -v https://spire-aws.company.com:8443

# Verify federation configuration
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server federation show

# Check trust bundles
kubectl exec -n spire-system spire-server-0 -- \
  /opt/spire/bin/spire-server bundle show -format spiffe
```

### Tailscale Connectivity Issues

```bash
# Check Tailscale status in pod
kubectl exec -it -n agentweave <pod-name> -c tailscale -- tailscale status

# Verify Tailscale routes
kubectl exec -it -n agentweave <pod-name> -c tailscale -- tailscale netcheck

# Test connectivity to other agents
kubectl exec -it -n agentweave <pod-name> -c agent -- \
  curl -k https://agent-gcp-search:8443/health
```

### Cross-Cloud Latency

```bash
# Measure latency between clusters
kubectl run -it --rm latency-test --image=nicolaka/netshoot -- \
  ping agent-gcp.company.com

# Trace route
kubectl run -it --rm traceroute-test --image=nicolaka/netshoot -- \
  traceroute agent-gcp.company.com
```

## Complete Multi-Cloud Example

```yaml
# multi-cloud-values.yaml
global:
  trustDomains:
    - aws.company.com
    - gcp.company.com
    - azure.company.com

aws:
  enabled: true
  trustDomain: aws.company.com
  region: us-east-1
  agents:
    - name: aws-orchestrator
      replicas: 3

gcp:
  enabled: true
  trustDomain: gcp.company.com
  region: us-central1
  agents:
    - name: gcp-search
      replicas: 5

azure:
  enabled: true
  trustDomain: azure.company.com
  region: eastus
  agents:
    - name: azure-processor
      replicas: 3

federation:
  enabled: true
  bundleEndpoints:
    aws: https://spire-aws.company.com:8443
    gcp: https://spire-gcp.company.com:8443
    azure: https://spire-azure.company.com:8443

networking:
  type: tailscale  # or vpn, istio
  tailscale:
    enabled: true
    authKeySecret: tailscale-auth
```

## Best Practices

1. **Start Simple**: Begin with 2 clouds before expanding
2. **Test Federation**: Thoroughly test SPIFFE federation
3. **Monitor Costs**: Track cross-cloud data transfer
4. **Automate**: Use IaC (Terraform) for all deployments
5. **DR Planning**: Regular disaster recovery drills
6. **Document**: Maintain network diagrams and runbooks
7. **Security**: Regular security audits of cross-cloud policies

## Next Steps

- **[Operations Guide](../guides/operations.md)** - Day-2 operations
- **[High Availability](../guides/ha.md)** - HA best practices
- **[Disaster Recovery](../guides/disaster-recovery.md)** - DR planning

---

**Related Documentation**:
- [AWS Deployment](aws.md)
- [GCP Deployment](gcp.md)
- [Azure Deployment](azure.md)
- [Security Best Practices](../security.md)
