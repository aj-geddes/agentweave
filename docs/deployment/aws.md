---
layout: page
title: AWS Deployment
description: Deploy AgentWeave agents to Amazon Web Services
nav_order: 4
parent: Deployment
---

# AWS Deployment Guide

This guide covers deploying AgentWeave agents to AWS using EKS, with integration for AWS-native services.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured (`aws configure`)
- eksctl or Terraform for cluster management
- kubectl 1.24+
- Helm 3.8+

## Architecture on AWS

```
┌─────────────────────────────────────────────────────────────┐
│                      AWS Cloud                              │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  VPC (10.0.0.0/16)                                   │   │
│  │                                                      │   │
│  │  ┌────────────────┐  ┌────────────────┐             │   │
│  │  │ Private Subnet │  │ Private Subnet │             │   │
│  │  │ (AZ-A)         │  │ (AZ-B)         │             │   │
│  │  │                │  │                │             │   │
│  │  │  ┌──────────┐  │  │  ┌──────────┐  │             │   │
│  │  │  │   EKS    │  │  │  │   EKS    │  │             │   │
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
│  │        │  ALB / NLB        │                        │   │
│  │        └───────────────────┘                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Secrets    │  │  CloudWatch  │  │     IAM      │     │
│  │   Manager    │  │    Logs      │  │   Roles      │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## EKS Cluster Setup

### Option 1: Using eksctl

Create cluster configuration:

```yaml
# eks-cluster.yaml
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: agentweave-cluster
  region: us-west-2
  version: "1.28"

vpc:
  cidr: 10.0.0.0/16
  nat:
    gateway: HighlyAvailable

iam:
  withOIDC: true
  serviceAccounts:
    - metadata:
        name: agentweave-agent
        namespace: agentweave
      attachPolicyARNs:
        - arn:aws:iam::aws:policy/SecretsManagerReadWrite
        - arn:aws:iam::aws:policy/CloudWatchAgentServerPolicy
      roleName: agentweave-agent-role

managedNodeGroups:
  - name: agentweave-nodes
    instanceType: t3.large
    desiredCapacity: 3
    minSize: 2
    maxSize: 10
    volumeSize: 100
    ssh:
      allow: false
    labels:
      role: agentweave
    tags:
      Environment: production
      Application: agentweave
    iam:
      withAddonPolicies:
        ebs: true
        cloudWatch: true
        autoScaler: true

addons:
  - name: vpc-cni
    version: latest
  - name: coredns
    version: latest
  - name: kube-proxy
    version: latest
  - name: aws-ebs-csi-driver
    version: latest

cloudWatch:
  clusterLogging:
    enableTypes:
      - api
      - audit
      - authenticator
      - controllerManager
      - scheduler
```

Create cluster:

```bash
# Create cluster
eksctl create cluster -f eks-cluster.yaml

# Verify cluster
kubectl get nodes

# Configure kubectl context
aws eks update-kubeconfig \
  --region us-west-2 \
  --name agentweave-cluster
```

### Option 2: Using Terraform

```hcl
# main.tf
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = "agentweave-cluster"
  cluster_version = "1.28"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  # Enable IRSA
  enable_irsa = true

  # EKS Managed Node Group
  eks_managed_node_groups = {
    agentweave = {
      min_size     = 2
      max_size     = 10
      desired_size = 3

      instance_types = ["t3.large"]
      capacity_type  = "ON_DEMAND"

      labels = {
        role = "agentweave"
      }

      tags = {
        Environment = "production"
        Application = "agentweave"
      }
    }
  }

  # Cluster addons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
    aws-ebs-csi-driver = {
      most_recent = true
    }
  }

  # CloudWatch logging
  cluster_enabled_log_types = [
    "api",
    "audit",
    "authenticator",
    "controllerManager",
    "scheduler"
  ]
}

# VPC Module
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "agentweave-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["us-west-2a", "us-west-2b", "us-west-2c"]
  private_subnets = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  public_subnets  = ["10.0.101.0/24", "10.0.102.0/24", "10.0.103.0/24"]

  enable_nat_gateway   = true
  enable_dns_hostnames = true
  enable_dns_support   = true

  public_subnet_tags = {
    "kubernetes.io/role/elb" = "1"
  }

  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = "1"
  }
}
```

Apply Terraform:

```bash
terraform init
terraform plan
terraform apply
```

## IAM Roles for Service Accounts (IRSA)

### Creating IAM Policy

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue",
        "secretsmanager:DescribeSecret"
      ],
      "Resource": [
        "arn:aws:secretsmanager:us-west-2:123456789012:secret:agentweave/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ],
      "Resource": [
        "arn:aws:logs:us-west-2:123456789012:log-group:/aws/eks/agentweave/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*"
    }
  ]
}
```

Create policy:

```bash
aws iam create-policy \
  --policy-name AgentWeaveAgentPolicy \
  --policy-document file://agent-policy.json
```

### Associate IAM Role with ServiceAccount

```bash
# Using eksctl
eksctl create iamserviceaccount \
  --name agentweave-agent \
  --namespace agentweave \
  --cluster agentweave-cluster \
  --region us-west-2 \
  --attach-policy-arn arn:aws:iam::123456789012:policy/AgentWeaveAgentPolicy \
  --approve

# Verify
kubectl describe sa agentweave-agent -n agentweave
```

Or manually create:

```yaml
# serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agentweave-agent
  namespace: agentweave
  annotations:
    eks.amazonaws.com/role-arn: arn:aws:iam::123456789012:role/agentweave-agent-role
```

## SPIRE on AWS

### SPIRE Server with EBS

```yaml
# spire-server-aws.yaml
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: spire-server-data
  namespace: spire-system
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: gp3
  resources:
    requests:
      storage: 10Gi

---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: spire-server
  namespace: spire-system
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
            - containerPort: 8081
              name: grpc
          volumeMounts:
            - name: spire-config
              mountPath: /run/spire/config
              readOnly: true
            - name: spire-data
              mountPath: /run/spire/data
          resources:
            requests:
              cpu: 500m
              memory: 512Mi
            limits:
              cpu: 1000m
              memory: 1Gi
      volumes:
        - name: spire-config
          configMap:
            name: spire-server
        - name: spire-data
          persistentVolumeClaim:
            claimName: spire-server-data
```

### SPIRE with AWS Node Attestation

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

        NodeAttestor "aws_iid" {
            plugin_data {
                account_ids_for_local_validation = ["123456789012"]
                allowed_regions = ["us-west-2"]
            }
        }

        KeyManager "aws_kms" {
            plugin_data {
                region = "us-west-2"
                key_metadata_file = "/run/spire/data/keys.json"
                key_policy_file = "/run/spire/config/key-policy.json"
            }
        }
    }
```

## AWS Secrets Manager Integration

### External Secrets Operator

Install External Secrets Operator:

```bash
helm repo add external-secrets https://charts.external-secrets.io
helm repo update

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
  name: aws-secrets-manager
  namespace: agentweave
spec:
  provider:
    aws:
      service: SecretsManager
      region: us-west-2
      auth:
        jwt:
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
    name: aws-secrets-manager
    kind: SecretStore
  target:
    name: agentweave-secrets
    creationPolicy: Owner
  data:
    - secretKey: api-key
      remoteRef:
        key: agentweave/api-credentials
        property: api_key
    - secretKey: database-url
      remoteRef:
        key: agentweave/database
        property: connection_string
```

Create secrets in AWS:

```bash
# Create secret in AWS Secrets Manager
aws secretsmanager create-secret \
  --name agentweave/api-credentials \
  --secret-string '{"api_key":"your-api-key-here"}' \
  --region us-west-2

aws secretsmanager create-secret \
  --name agentweave/database \
  --secret-string '{"connection_string":"postgresql://user:pass@host:5432/db"}' \
  --region us-west-2
```

## CloudWatch Integration

### Container Insights

Enable Container Insights:

```bash
# Create CloudWatch namespace
kubectl create namespace amazon-cloudwatch

# Deploy CloudWatch agent
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cloudwatch-namespace.yaml

# Create ConfigMap
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cwagent/cwagent-configmap.yaml

# Deploy CloudWatch agent DaemonSet
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonset/container-insights-monitoring/cwagent/cwagent-daemonset.yaml
```

### Fluent Bit for Log Forwarding

```yaml
# fluent-bit-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: fluent-bit-config
  namespace: amazon-cloudwatch
data:
  fluent-bit.conf: |
    [SERVICE]
        Flush                     5
        Log_Level                 info
        Daemon                    off
        Parsers_File              parsers.conf

    [INPUT]
        Name                      tail
        Path                      /var/log/containers/agentweave-*.log
        Parser                    docker
        Tag                       agentweave.*
        Refresh_Interval          5
        Mem_Buf_Limit             5MB
        Skip_Long_Lines           On

    [FILTER]
        Name                      kubernetes
        Match                     agentweave.*
        Kube_URL                  https://kubernetes.default.svc:443
        Kube_CA_File              /var/run/secrets/kubernetes.io/serviceaccount/ca.crt
        Kube_Token_File           /var/run/secrets/kubernetes.io/serviceaccount/token
        Merge_Log                 On
        Keep_Log                  Off

    [OUTPUT]
        Name                      cloudwatch_logs
        Match                     agentweave.*
        region                    us-west-2
        log_group_name            /aws/eks/agentweave/application
        log_stream_prefix         from-fluent-bit-
        auto_create_group         true
```

## Load Balancing

### Network Load Balancer for Agents

```yaml
# nlb-service.yaml
apiVersion: v1
kind: Service
metadata:
  name: agentweave-nlb
  namespace: agentweave
  annotations:
    service.beta.kubernetes.io/aws-load-balancer-type: "nlb"
    service.beta.kubernetes.io/aws-load-balancer-internal: "true"
    service.beta.kubernetes.io/aws-load-balancer-scheme: "internal"
    service.beta.kubernetes.io/aws-load-balancer-cross-zone-load-balancing-enabled: "true"
spec:
  type: LoadBalancer
  selector:
    app: agentweave-agent
  ports:
    - name: https
      port: 8443
      targetPort: 8443
      protocol: TCP
```

### Application Load Balancer with Ingress

Install AWS Load Balancer Controller:

```bash
# Download IAM policy
curl -o iam-policy.json https://raw.githubusercontent.com/kubernetes-sigs/aws-load-balancer-controller/main/docs/install/iam_policy.json

# Create IAM policy
aws iam create-policy \
  --policy-name AWSLoadBalancerControllerIAMPolicy \
  --policy-document file://iam-policy.json

# Create service account
eksctl create iamserviceaccount \
  --cluster=agentweave-cluster \
  --namespace=kube-system \
  --name=aws-load-balancer-controller \
  --attach-policy-arn=arn:aws:iam::123456789012:policy/AWSLoadBalancerControllerIAMPolicy \
  --approve

# Install controller
helm repo add eks https://aws.github.io/eks-charts
helm repo update

helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=agentweave-cluster \
  --set serviceAccount.create=false \
  --set serviceAccount.name=aws-load-balancer-controller
```

Create Ingress:

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: agentweave-ingress
  namespace: agentweave
  annotations:
    kubernetes.io/ingress.class: alb
    alb.ingress.kubernetes.io/scheme: internal
    alb.ingress.kubernetes.io/target-type: ip
    alb.ingress.kubernetes.io/backend-protocol: HTTPS
    alb.ingress.kubernetes.io/certificate-arn: arn:aws:acm:us-west-2:123456789012:certificate/xxxxx
    alb.ingress.kubernetes.io/ssl-policy: ELBSecurityPolicy-TLS-1-2-2017-01
spec:
  rules:
    - host: agents.agentweave.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: agentweave-agent
                port:
                  number: 8443
```

## Cross-AZ Communication

### Pod Topology Spread

```yaml
# deployment-with-topology.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agentweave-agent
  namespace: agentweave
spec:
  replicas: 6
  selector:
    matchLabels:
      app: agentweave-agent
  template:
    metadata:
      labels:
        app: agentweave-agent
    spec:
      topologySpreadConstraints:
        - maxSkew: 1
          topologyKey: topology.kubernetes.io/zone
          whenUnsatisfiable: DoNotSchedule
          labelSelector:
            matchLabels:
              app: agentweave-agent
      containers:
        - name: agent
          image: my-org/agentweave-agent:1.0.0
```

## Terraform Example

Complete Terraform deployment:

```hcl
# terraform/main.tf

# EKS Module
module "eks" {
  source = "./modules/eks"

  cluster_name = var.cluster_name
  vpc_id       = module.vpc.vpc_id
  subnet_ids   = module.vpc.private_subnets
}

# AgentWeave Deployment
resource "helm_release" "agentweave" {
  name       = "agentweave-agent"
  repository = "https://charts.agentweave.io"
  chart      = "agentweave"
  namespace  = "agentweave"

  create_namespace = true

  values = [
    templatefile("${path.module}/values.yaml.tpl", {
      trust_domain      = var.trust_domain
      aws_region        = var.aws_region
      service_account   = kubernetes_service_account.agentweave.metadata[0].name
      secrets_arn       = aws_secretsmanager_secret.agentweave.arn
    })
  ]

  depends_on = [
    module.eks,
    kubernetes_namespace.agentweave
  ]
}

# Secrets Manager
resource "aws_secretsmanager_secret" "agentweave" {
  name = "agentweave/agent-credentials"

  tags = {
    Application = "agentweave"
    Environment = var.environment
  }
}

# Service Account with IRSA
resource "kubernetes_service_account" "agentweave" {
  metadata {
    name      = "agentweave-agent"
    namespace = "agentweave"
    annotations = {
      "eks.amazonaws.com/role-arn" = aws_iam_role.agentweave.arn
    }
  }
}

# IAM Role for Service Account
resource "aws_iam_role" "agentweave" {
  name = "agentweave-agent-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRoleWithWebIdentity"
      Effect = "Allow"
      Principal = {
        Federated = module.eks.oidc_provider_arn
      }
      Condition = {
        StringEquals = {
          "${module.eks.oidc_provider}:sub" = "system:serviceaccount:agentweave:agentweave-agent"
        }
      }
    }]
  })
}
```

## Monitoring and Alerting

### CloudWatch Alarms

```hcl
# cloudwatch-alarms.tf
resource "aws_cloudwatch_metric_alarm" "high_cpu" {
  alarm_name          = "agentweave-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "pod_cpu_utilization"
  namespace           = "ContainerInsights"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "This metric monitors agent CPU utilization"

  dimensions = {
    ClusterName = "agentweave-cluster"
    Namespace   = "agentweave"
  }

  alarm_actions = [aws_sns_topic.alerts.arn]
}
```

## Best Practices for AWS

1. **Use Multiple AZs**: Deploy across at least 3 availability zones
2. **Enable IRSA**: Use IAM Roles for Service Accounts instead of node IAM roles
3. **Use Secrets Manager**: Store sensitive data in AWS Secrets Manager
4. **Enable CloudWatch**: Forward all logs and metrics to CloudWatch
5. **Use NLB for Internal**: Use Network Load Balancer for agent-to-agent communication
6. **EBS Encryption**: Enable encryption for all EBS volumes
7. **VPC Endpoints**: Use VPC endpoints for AWS services to reduce data transfer costs

## Troubleshooting

### IRSA Not Working

```bash
# Check service account annotation
kubectl describe sa agentweave-agent -n agentweave

# Verify OIDC provider
aws eks describe-cluster --name agentweave-cluster --query "cluster.identity.oidc.issuer"

# Check pod environment
kubectl exec -it -n agentweave deploy/agentweave-agent -- env | grep AWS
```

### CloudWatch Logs Not Appearing

```bash
# Check Fluent Bit logs
kubectl logs -n amazon-cloudwatch -l k8s-app=fluent-bit

# Verify IAM permissions
aws iam get-role-policy --role-name agentweave-agent-role --policy-name logs-policy
```

## Next Steps

- **[GCP Deployment](gcp.md)** - Deploy to Google Cloud Platform
- **[Azure Deployment](azure.md)** - Deploy to Microsoft Azure
- **[Hybrid Deployment](hybrid.md)** - Multi-cloud setup

---

**Related Documentation**:
- [Kubernetes Deployment](kubernetes.md)
- [Helm Charts](helm.md)
- [Security Best Practices](../security.md)
