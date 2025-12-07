---
layout: page
title: Azure Deployment
description: Deploy AgentWeave agents to Microsoft Azure
nav_order: 6
parent: Deployment
---

# Azure Deployment Guide

This guide covers deploying AgentWeave agents to Microsoft Azure using AKS with Azure AD Pod Identity and native Azure integrations.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Prerequisites

- Azure subscription
- Azure CLI configured (`az login`)
- kubectl 1.24+
- Helm 3.8+
- Appropriate Azure RBAC permissions

## Architecture on Azure

```
┌─────────────────────────────────────────────────────────────┐
│                    Microsoft Azure                          │
│                                                             │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Virtual Network (10.0.0.0/16)                       │   │
│  │                                                      │   │
│  │  ┌────────────────┐  ┌────────────────┐             │   │
│  │  │ Subnet (Zone-1)│  │ Subnet (Zone-2)│             │   │
│  │  │                │  │                │             │   │
│  │  │  ┌──────────┐  │  │  ┌──────────┐  │             │   │
│  │  │  │   AKS    │  │  │  │   AKS    │  │             │   │
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
│  │        │  Azure Load Bal.  │                        │   │
│  │        └───────────────────┘                        │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Key Vault  │  │    Azure     │  │   Managed    │     │
│  │              │  │   Monitor    │  │   Identity   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## AKS Cluster Setup

### Create Resource Group

```bash
# Set variables
export RESOURCE_GROUP=agentweave-rg
export LOCATION=eastus
export CLUSTER_NAME=agentweave-aks
export ACR_NAME=agentweaveacr

# Create resource group
az group create \
  --name $RESOURCE_GROUP \
  --location $LOCATION
```

### Create AKS Cluster

```bash
# Create VNet
az network vnet create \
  --resource-group $RESOURCE_GROUP \
  --name agentweave-vnet \
  --address-prefixes 10.0.0.0/16 \
  --subnet-name agentweave-subnet \
  --subnet-prefix 10.0.0.0/20

# Get subnet ID
SUBNET_ID=$(az network vnet subnet show \
  --resource-group $RESOURCE_GROUP \
  --vnet-name agentweave-vnet \
  --name agentweave-subnet \
  --query id -o tsv)

# Create AKS cluster with managed identity
az aks create \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME \
  --location $LOCATION \
  --kubernetes-version 1.28 \
  --node-count 3 \
  --node-vm-size Standard_D4s_v3 \
  --network-plugin azure \
  --vnet-subnet-id $SUBNET_ID \
  --enable-managed-identity \
  --enable-addons monitoring,azure-policy,azure-keyvault-secrets-provider \
  --enable-oidc-issuer \
  --enable-workload-identity \
  --enable-cluster-autoscaler \
  --min-count 2 \
  --max-count 10 \
  --zones 1 2 3 \
  --vm-set-type VirtualMachineScaleSets \
  --load-balancer-sku standard \
  --network-policy azure \
  --generate-ssh-keys

# Get credentials
az aks get-credentials \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME
```

### Terraform Configuration

```hcl
# main.tf
resource "azurerm_resource_group" "agentweave" {
  name     = "agentweave-rg"
  location = var.location
}

resource "azurerm_virtual_network" "agentweave" {
  name                = "agentweave-vnet"
  location            = azurerm_resource_group.agentweave.location
  resource_group_name = azurerm_resource_group.agentweave.name
  address_space       = ["10.0.0.0/16"]
}

resource "azurerm_subnet" "agentweave" {
  name                 = "agentweave-subnet"
  resource_group_name  = azurerm_resource_group.agentweave.name
  virtual_network_name = azurerm_virtual_network.agentweave.name
  address_prefixes     = ["10.0.0.0/20"]
}

resource "azurerm_kubernetes_cluster" "agentweave" {
  name                = "agentweave-aks"
  location            = azurerm_resource_group.agentweave.location
  resource_group_name = azurerm_resource_group.agentweave.name
  dns_prefix          = "agentweave"
  kubernetes_version  = "1.28"

  default_node_pool {
    name                = "agentweave"
    node_count          = 3
    vm_size             = "Standard_D4s_v3"
    vnet_subnet_id      = azurerm_subnet.agentweave.id
    enable_auto_scaling = true
    min_count           = 2
    max_count           = 10
    zones               = ["1", "2", "3"]

    tags = {
      Environment = "Production"
      Application = "AgentWeave"
    }
  }

  identity {
    type = "SystemAssigned"
  }

  network_profile {
    network_plugin    = "azure"
    network_policy    = "azure"
    load_balancer_sku = "standard"
    service_cidr      = "10.0.16.0/20"
    dns_service_ip    = "10.0.16.10"
  }

  oms_agent {
    log_analytics_workspace_id = azurerm_log_analytics_workspace.agentweave.id
  }

  azure_policy_enabled = true

  key_vault_secrets_provider {
    secret_rotation_enabled  = true
    secret_rotation_interval = "2m"
  }

  oidc_issuer_enabled       = true
  workload_identity_enabled = true
}

resource "azurerm_log_analytics_workspace" "agentweave" {
  name                = "agentweave-logs"
  location            = azurerm_resource_group.agentweave.location
  resource_group_name = azurerm_resource_group.agentweave.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
}
```

## Azure AD Workload Identity

### Create Managed Identity

```bash
# Create managed identity
az identity create \
  --name agentweave-agent-identity \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION

# Get identity details
export USER_ASSIGNED_CLIENT_ID=$(az identity show \
  --name agentweave-agent-identity \
  --resource-group $RESOURCE_GROUP \
  --query 'clientId' -o tsv)

export USER_ASSIGNED_PRINCIPAL_ID=$(az identity show \
  --name agentweave-agent-identity \
  --resource-group $RESOURCE_GROUP \
  --query 'principalId' -o tsv)
```

### Federate Identity with AKS

```bash
# Get OIDC issuer URL
export AKS_OIDC_ISSUER=$(az aks show \
  --name $CLUSTER_NAME \
  --resource-group $RESOURCE_GROUP \
  --query "oidcIssuerProfile.issuerUrl" -o tsv)

# Create federated identity credential
az identity federated-credential create \
  --name agentweave-agent-federated-identity \
  --identity-name agentweave-agent-identity \
  --resource-group $RESOURCE_GROUP \
  --issuer ${AKS_OIDC_ISSUER} \
  --subject system:serviceaccount:agentweave:agentweave-agent \
  --audience api://AzureADTokenExchange
```

### Create Kubernetes ServiceAccount

```yaml
# serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agentweave-agent
  namespace: agentweave
  annotations:
    azure.workload.identity/client-id: CLIENT_ID
  labels:
    azure.workload.identity/use: "true"
```

Apply:

```bash
kubectl create namespace agentweave

kubectl apply -f - <<EOF
apiVersion: v1
kind: ServiceAccount
metadata:
  name: agentweave-agent
  namespace: agentweave
  annotations:
    azure.workload.identity/client-id: ${USER_ASSIGNED_CLIENT_ID}
  labels:
    azure.workload.identity/use: "true"
EOF
```

## Azure Key Vault Integration

### Create Key Vault

```bash
# Create Key Vault
az keyvault create \
  --name agentweave-kv \
  --resource-group $RESOURCE_GROUP \
  --location $LOCATION \
  --enable-rbac-authorization

# Grant access to managed identity
az role assignment create \
  --role "Key Vault Secrets User" \
  --assignee $USER_ASSIGNED_PRINCIPAL_ID \
  --scope $(az keyvault show --name agentweave-kv --resource-group $RESOURCE_GROUP --query id -o tsv)
```

### Store Secrets

```bash
# Create secrets
az keyvault secret set \
  --vault-name agentweave-kv \
  --name agentweave-api-key \
  --value "your-api-key"

az keyvault secret set \
  --vault-name agentweave-kv \
  --name database-url \
  --value "postgresql://user:pass@host:5432/db"
```

### Using CSI Secret Store Driver

The CSI driver is already enabled via the addon. Create SecretProviderClass:

```yaml
# secret-provider-class.yaml
apiVersion: secrets-store.csi.x-k8s.io/v1
kind: SecretProviderClass
metadata:
  name: agentweave-secrets
  namespace: agentweave
spec:
  provider: azure
  parameters:
    usePodIdentity: "false"
    useVMManagedIdentity: "false"
    clientID: "CLIENT_ID"  # Managed identity client ID
    keyvaultName: "agentweave-kv"
    cloudName: ""
    objects: |
      array:
        - |
          objectName: agentweave-api-key
          objectType: secret
          objectVersion: ""
        - |
          objectName: database-url
          objectType: secret
          objectVersion: ""
    tenantId: "TENANT_ID"
  secretObjects:
    - secretName: agentweave-secrets
      type: Opaque
      data:
        - objectName: agentweave-api-key
          key: api-key
        - objectName: database-url
          key: database-url
```

Apply:

```bash
# Get tenant ID
export AZURE_TENANT_ID=$(az account show --query tenantId -o tsv)

# Apply with substitutions
envsubst < secret-provider-class.yaml | kubectl apply -f -
```

### Mount Secrets in Pod

```yaml
# deployment.yaml (excerpt)
spec:
  template:
    spec:
      serviceAccountName: agentweave-agent
      containers:
        - name: agent
          volumeMounts:
            - name: secrets-store
              mountPath: "/mnt/secrets-store"
              readOnly: true
          env:
            - name: API_KEY
              valueFrom:
                secretKeyRef:
                  name: agentweave-secrets
                  key: api-key
      volumes:
        - name: secrets-store
          csi:
            driver: secrets-store.csi.k8s.io
            readOnly: true
            volumeAttributes:
              secretProviderClass: "agentweave-secrets"
```

## Azure Monitor Integration

### Container Insights

Container Insights is enabled via the addon. View metrics:

```bash
# View live logs
az aks get-credentials \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME

kubectl logs -f deployment/agentweave-agent -n agentweave
```

### Custom Metrics

```yaml
# pod-monitoring.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: container-azm-ms-agentconfig
  namespace: kube-system
data:
  schema-version: v1
  config-version: ver1
  log-data-collection-settings: |-
    [log_collection_settings]
       [log_collection_settings.stdout]
          enabled = true
          exclude_namespaces = ["kube-system"]
       [log_collection_settings.stderr]
          enabled = true
          exclude_namespaces = ["kube-system"]
  prometheus-data-collection-settings: |-
    [prometheus_data_collection_settings.cluster]
        interval = "1m"
        monitor_kubernetes_pods = true
        [[prometheus_data_collection_settings.cluster.metric_filters]]
            namespace = "agentweave"
```

### Create Alert Rules

```bash
# Create metric alert
az monitor metrics alert create \
  --name agentweave-high-cpu \
  --resource-group $RESOURCE_GROUP \
  --scopes $(az aks show --name $CLUSTER_NAME --resource-group $RESOURCE_GROUP --query id -o tsv) \
  --condition "avg Percentage CPU > 80" \
  --description "Alert when CPU exceeds 80%" \
  --evaluation-frequency 5m \
  --window-size 15m \
  --severity 2
```

## SPIRE on Azure

### SPIRE with Azure Disk

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
  storageClassName: managed-premium
  resources:
    requests:
      storage: 10Gi
```

### SPIRE Server Configuration

```yaml
# spire-server-config-azure.yaml
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

        NodeAttestor "azure_msi" {
            plugin_data {
                tenants = {
                    "TENANT_ID" = {
                        subscription_id = "SUBSCRIPTION_ID"
                    }
                }
            }
        }

        KeyManager "memory" {
            plugin_data {}
        }
    }
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
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"
    service.beta.kubernetes.io/azure-load-balancer-internal-subnet: "agentweave-subnet"
spec:
  type: LoadBalancer
  loadBalancerIP: 10.0.1.100
  selector:
    app: agentweave-agent
  ports:
    - name: https
      port: 8443
      targetPort: 8443
      protocol: TCP
```

### Application Gateway Ingress

Install Application Gateway Ingress Controller:

```bash
# Create application gateway
az network application-gateway create \
  --name agentweave-appgw \
  --location $LOCATION \
  --resource-group $RESOURCE_GROUP \
  --vnet-name agentweave-vnet \
  --subnet appgw-subnet \
  --capacity 2 \
  --sku Standard_v2 \
  --http-settings-cookie-based-affinity Disabled \
  --frontend-port 443 \
  --http-settings-port 8443 \
  --http-settings-protocol Https

# Enable AGIC addon
az aks enable-addons \
  --resource-group $RESOURCE_GROUP \
  --name $CLUSTER_NAME \
  --addons ingress-appgw \
  --appgw-id $(az network application-gateway show --name agentweave-appgw --resource-group $RESOURCE_GROUP --query id -o tsv)
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
    kubernetes.io/ingress.class: azure/application-gateway
    appgw.ingress.kubernetes.io/ssl-redirect: "true"
    appgw.ingress.kubernetes.io/backend-protocol: "https"
spec:
  tls:
    - secretName: agentweave-tls
      hosts:
        - agents.agentweave.io
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

## Helm Deployment on AKS

```yaml
# aks-values.yaml
agent:
  name: "aks-agent"
  trustDomain: "agentweave.io"

# ServiceAccount with Workload Identity
serviceAccount:
  create: true
  annotations:
    azure.workload.identity/client-id: CLIENT_ID
  labels:
    azure.workload.identity/use: "true"

# Azure Key Vault integration
azureKeyVault:
  enabled: true
  secretProviderClass: agentweave-secrets
  keyvaultName: agentweave-kv
  tenantId: TENANT_ID
  clientId: CLIENT_ID

# Azure Monitor
observability:
  logging:
    level: INFO
    format: json
  monitoring:
    enabled: true
    type: azure-monitor

# Storage
persistence:
  enabled: true
  storageClass: managed-premium
  size: 10Gi

# Load Balancer
service:
  type: LoadBalancer
  annotations:
    service.beta.kubernetes.io/azure-load-balancer-internal: "true"

# Resources
resources:
  requests:
    cpu: 1000m
    memory: 1Gi
  limits:
    cpu: 4000m
    memory: 4Gi

# Node selector for specific node pool
nodeSelector:
  agentpool: agentweave
```

Deploy:

```bash
helm install agentweave-agent agentweave/agentweave \
  -f aks-values.yaml \
  -n agentweave \
  --create-namespace
```

## Complete Terraform Example

```hcl
# terraform/main.tf

# AKS Cluster
module "aks" {
  source = "./modules/aks"
  # ... (as shown earlier)
}

# Managed Identity
resource "azurerm_user_assigned_identity" "agentweave" {
  name                = "agentweave-agent-identity"
  resource_group_name = azurerm_resource_group.agentweave.name
  location            = azurerm_resource_group.agentweave.location
}

# Federated Identity Credential
resource "azurerm_federated_identity_credential" "agentweave" {
  name                = "agentweave-agent-federated"
  resource_group_name = azurerm_resource_group.agentweave.name
  parent_id           = azurerm_user_assigned_identity.agentweave.id
  audience            = ["api://AzureADTokenExchange"]
  issuer              = azurerm_kubernetes_cluster.agentweave.oidc_issuer_url
  subject             = "system:serviceaccount:agentweave:agentweave-agent"
}

# Key Vault
resource "azurerm_key_vault" "agentweave" {
  name                       = "agentweave-kv"
  location                   = azurerm_resource_group.agentweave.location
  resource_group_name        = azurerm_resource_group.agentweave.name
  tenant_id                  = data.azurerm_client_config.current.tenant_id
  sku_name                   = "standard"
  enable_rbac_authorization  = true
  purge_protection_enabled   = false
}

# Key Vault Access
resource "azurerm_role_assignment" "agentweave_kv" {
  scope                = azurerm_key_vault.agentweave.id
  role_definition_name = "Key Vault Secrets User"
  principal_id         = azurerm_user_assigned_identity.agentweave.principal_id
}

# Kubernetes Resources
resource "kubernetes_namespace" "agentweave" {
  metadata {
    name = "agentweave"
  }
  depends_on = [module.aks]
}

resource "kubernetes_service_account" "agentweave" {
  metadata {
    name      = "agentweave-agent"
    namespace = kubernetes_namespace.agentweave.metadata[0].name
    annotations = {
      "azure.workload.identity/client-id" = azurerm_user_assigned_identity.agentweave.client_id
    }
    labels = {
      "azure.workload.identity/use" = "true"
    }
  }
}

# Helm Release
resource "helm_release" "agentweave" {
  name       = "agentweave-agent"
  repository = "https://charts.agentweave.io"
  chart      = "agentweave"
  namespace  = kubernetes_namespace.agentweave.metadata[0].name

  values = [
    templatefile("${path.module}/values.yaml.tpl", {
      client_id       = azurerm_user_assigned_identity.agentweave.client_id
      tenant_id       = data.azurerm_client_config.current.tenant_id
      keyvault_name   = azurerm_key_vault.agentweave.name
      trust_domain    = var.trust_domain
    })
  ]

  depends_on = [
    kubernetes_service_account.agentweave,
    azurerm_federated_identity_credential.agentweave
  ]
}
```

## Best Practices for Azure

1. **Use Workload Identity**: Prefer Workload Identity over Pod Identity
2. **Enable RBAC**: Use Azure RBAC for Key Vault access
3. **Availability Zones**: Deploy across multiple zones for HA
4. **Managed Disks**: Use Premium SSD for SPIRE data
5. **Network Policies**: Enable Azure Network Policy
6. **Private Link**: Use Private Link for Key Vault access
7. **Azure Policy**: Enable for compliance and governance

## Troubleshooting

### Workload Identity Issues

```bash
# Check federated credential
az identity federated-credential show \
  --name agentweave-agent-federated-identity \
  --identity-name agentweave-agent-identity \
  --resource-group $RESOURCE_GROUP

# Verify service account
kubectl describe sa agentweave-agent -n agentweave

# Test from pod
kubectl run -it --rm test \
  --image=mcr.microsoft.com/azure-cli \
  --serviceaccount=agentweave-agent \
  -n agentweave \
  -- az login --identity
```

### Key Vault Access Problems

```bash
# Check RBAC assignments
az role assignment list \
  --assignee $USER_ASSIGNED_PRINCIPAL_ID \
  --all

# Test secret access
az keyvault secret show \
  --vault-name agentweave-kv \
  --name agentweave-api-key
```

## Next Steps

- **[Hybrid Deployment](hybrid.md)** - Multi-cloud architecture
- **[Monitoring Guide](../guides/observability.md)** - Advanced monitoring
- **[High Availability](../guides/ha.md)** - HA configuration

---

**Related Documentation**:
- [Kubernetes Deployment](kubernetes.md)
- [Helm Charts](helm.md)
- [Security Best Practices](../security.md)
