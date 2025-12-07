---
layout: page
title: Configure Identity Providers
description: Set up SPIFFE/SPIRE or static mTLS for agent identity
parent: How-To Guides
nav_order: 1
---

# Configure Identity Providers

This guide shows you how to configure identity providers for your AgentWeave agents. Identity is the foundation of AgentWeave's security model - every agent must have a cryptographically verifiable identity.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Overview

AgentWeave supports two identity providers:

| Provider | Use Case | Production Ready? |
|----------|----------|-------------------|
| **SPIFFE/SPIRE** | Production deployments | Yes |
| **Static mTLS** | Development/testing only | No - insecure |

**Production Requirement:** You MUST use SPIFFE/SPIRE in production. Static mTLS certificates are only for local development and testing.

---

## SPIFFE/SPIRE Setup

SPIFFE (Secure Production Identity Framework For Everyone) provides cryptographic workload identities that automatically rotate. SPIRE is the reference implementation.

### Prerequisites

- Docker or Kubernetes (for running SPIRE)
- Basic understanding of trust domains
- Network connectivity between agents and SPIRE

### Architecture Overview

```
┌─────────────────┐
│  SPIRE Server   │  Issues SVIDs (identity certificates)
│  (Trust Root)   │  Manages trust bundles
└────────┬────────┘
         │
    ┌────┴────┬────────┬────────┐
    │         │        │        │
┌───▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐
│ SPIRE │ │SPIRE │ │SPIRE │ │SPIRE │
│ Agent │ │Agent │ │Agent │ │Agent │
└───┬───┘ └──┬───┘ └──┬───┘ └──┬───┘
    │        │        │        │
┌───▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐
│Agent  │ │Agent │ │Agent │ │Agent │
│  A    │ │  B   │ │  C   │ │  D   │
└───────┘ └──────┘ └──────┘ └──────┘
```

### Step 1: Install SPIRE Server

The SPIRE Server is the trust anchor that issues identities.

**Using Docker:**

```bash
# Create configuration directory
mkdir -p /opt/spire/server

# Create server configuration
cat > /opt/spire/server/server.conf <<EOF
server {
    bind_address = "0.0.0.0"
    bind_port = "8081"
    trust_domain = "yourdomain.com"
    data_dir = "/opt/spire/data/server"
    log_level = "INFO"

    ca_ttl = "24h"
    default_x509_svid_ttl = "1h"
}

plugins {
    DataStore "sql" {
        plugin_data {
            database_type = "sqlite3"
            connection_string = "/opt/spire/data/server/datastore.sqlite3"
        }
    }

    KeyManager "disk" {
        plugin_data {
            keys_path = "/opt/spire/data/server/keys.json"
        }
    }

    NodeAttestor "join_token" {
        plugin_data {}
    }
}
EOF

# Run SPIRE Server
docker run -d \
    --name spire-server \
    -p 8081:8081 \
    -v /opt/spire/server:/opt/spire \
    ghcr.io/spiffe/spire-server:1.8.5 \
    -config /opt/spire/server.conf
```

**Using Kubernetes:**

```yaml
# See: https://github.com/spiffe/spire-tutorials/tree/main/k8s/quickstart
# Or use the SPIRE Helm chart
helm repo add spiffe https://spiffe.github.io/helm-charts-hardened/
helm install spire-server spiffe/spire-server \
    --set global.spiffe.trustDomain=yourdomain.com
```

### Step 2: Install SPIRE Agent

The SPIRE Agent runs on each node and provides the Workload API to your agents.

**Using Docker:**

```bash
# Generate join token on server
docker exec spire-server \
    /opt/spire/bin/spire-server token generate \
    -spiffeID spiffe://yourdomain.com/agent/docker-host

# Save the token (shown as <TOKEN>)

# Create agent configuration
mkdir -p /opt/spire/agent
cat > /opt/spire/agent/agent.conf <<EOF
agent {
    data_dir = "/opt/spire/data/agent"
    log_level = "INFO"
    server_address = "spire-server"
    server_port = "8081"
    socket_path = "/tmp/spire-agent/public/api.sock"
    trust_domain = "yourdomain.com"
}

plugins {
    NodeAttestor "join_token" {
        plugin_data {
            token = "<TOKEN>"
        }
    }

    KeyManager "disk" {
        plugin_data {
            directory = "/opt/spire/data/agent"
        }
    }

    WorkloadAttestor "unix" {
        plugin_data {}
    }
}
EOF

# Run SPIRE Agent
docker run -d \
    --name spire-agent \
    --network container:spire-server \
    -v /opt/spire/agent:/opt/spire \
    -v /tmp/spire-agent:/tmp/spire-agent \
    ghcr.io/spiffe/spire-agent:1.8.5 \
    -config /opt/spire/agent.conf
```

**Using Kubernetes:**

```bash
helm install spire-agent spiffe/spire-agent \
    --set server.address=spire-server.spire.svc.cluster.local \
    --set global.spiffe.trustDomain=yourdomain.com
```

### Step 3: Register Your Agent

Create a registration entry that maps your workload to a SPIFFE ID.

```bash
# For Docker (Unix socket workload attestation)
docker exec spire-server \
    /opt/spire/bin/spire-server entry create \
    -spiffeID spiffe://yourdomain.com/agent/search \
    -parentID spiffe://yourdomain.com/agent/docker-host \
    -selector unix:uid:1000

# For Kubernetes (Pod workload attestation)
kubectl exec -n spire spire-server-0 -- \
    /opt/spire/bin/spire-server entry create \
    -spiffeID spiffe://yourdomain.com/agent/search \
    -parentID spiffe://yourdomain.com/spire/agent/k8s-node \
    -selector k8s:ns:default \
    -selector k8s:sa:search-agent \
    -selector k8s:pod-label:app:search
```

**Registration Entry Explained:**
- `spiffeID`: The identity assigned to this workload
- `parentID`: The SPIRE agent's identity
- `selector`: How to identify the workload (UID, K8s namespace, pod labels, etc.)

### Step 4: Configure AgentWeave to Use SPIRE

Update your agent configuration:

```yaml
# config.yaml
agent:
  name: search-agent
  trust_domain: yourdomain.com
  description: Search capability agent

identity:
  provider: spiffe
  spiffe_endpoint: unix:///tmp/spire-agent/public/api.sock
  allowed_trust_domains:
    - yourdomain.com
    - partner.example.com  # For federation

authorization:
  provider: opa
  # ... rest of config
```

Python code:

```python
from agentweave import SecureAgent, capability
from agentweave.config import AgentConfig

# Load configuration
config = AgentConfig.from_yaml("config.yaml")

class SearchAgent(SecureAgent):
    def __init__(self):
        super().__init__(config)

    @capability("search")
    async def search(self, query: str, limit: int = 10) -> dict:
        # Identity automatically verified via SPIRE
        results = await self._perform_search(query, limit)
        return {"results": results}

# Agent will fetch SVID from SPIRE on startup
agent = SearchAgent()
await agent.start()
```

### Step 5: Verify Identity

Check that your agent can fetch its identity:

```bash
# Check SPIRE Agent is running
docker exec spire-agent \
    /opt/spire/bin/spire-agent api fetch \
    -socketPath /tmp/spire-agent/public/api.sock

# You should see:
# SPIFFE ID: spiffe://yourdomain.com/agent/search
# SVID Valid: true
```

In your agent code:

```python
# Verify identity in agent startup
identity_provider = agent.identity_provider
svid = await identity_provider.get_svid()

print(f"Agent SPIFFE ID: {svid.spiffe_id}")
print(f"Certificate expires: {svid.expiry}")
print(f"Trust domain: {identity_provider.get_trust_domain()}")
```

---

## Static mTLS (Development Only)

For local development and testing, you can use static TLS certificates instead of SPIRE.

{: .warning }
**NEVER use static certificates in production.** They don't rotate, can be copied, and violate AgentWeave's security model.

### Generate Self-Signed Certificates

```bash
# Create certificates directory
mkdir -p certs/

# Generate CA
openssl req -x509 -newkey rsa:4096 -days 365 -nodes \
    -keyout certs/ca-key.pem \
    -out certs/ca-cert.pem \
    -subj "/CN=AgentWeave Dev CA"

# Generate agent certificate
openssl req -newkey rsa:4096 -nodes \
    -keyout certs/agent-key.pem \
    -out certs/agent-req.pem \
    -subj "/CN=spiffe://dev.local/agent/test"

# Sign agent certificate with CA
openssl x509 -req \
    -in certs/agent-req.pem \
    -CA certs/ca-cert.pem \
    -CAkey certs/ca-key.pem \
    -CAcreateserial \
    -out certs/agent-cert.pem \
    -days 365 \
    -extfile <(printf "subjectAltName=URI:spiffe://dev.local/agent/test")
```

### Configure AgentWeave with Static Certificates

```yaml
# config-dev.yaml
agent:
  name: dev-agent
  trust_domain: dev.local
  description: Development agent

identity:
  provider: mtls-static
  cert_path: ./certs/agent-cert.pem
  key_path: ./certs/agent-key.pem
  ca_path: ./certs/ca-cert.pem
  allowed_trust_domains:
    - dev.local

authorization:
  provider: allow-all  # For development
  default_action: log-only

transport:
  tls_min_version: "1.2"  # More permissive for dev
  peer_verification: log-only  # Warn but don't block

# WARNING: This configuration is NOT production-ready
```

### Security Warnings for Static mTLS

When using static certificates, AgentWeave will log warnings:

```
WARNING: Using static mTLS certificates - NOT SUITABLE FOR PRODUCTION
WARNING: Certificates do not auto-rotate - manual renewal required
WARNING: peer_verification set to 'log-only' - connections not verified
WARNING: authorization default_action is 'log-only' - requests not blocked
```

These warnings remind you that this configuration bypasses AgentWeave's security guarantees.

---

## Troubleshooting Identity Issues

### Problem: Cannot connect to SPIRE socket

**Symptoms:**
```
IdentityError: Cannot connect to SPIFFE Workload API at unix:///tmp/spire-agent/public/api.sock
```

**Solutions:**

1. Check SPIRE Agent is running:
   ```bash
   docker ps | grep spire-agent
   # or
   kubectl get pods -n spire
   ```

2. Verify socket exists and has correct permissions:
   ```bash
   ls -la /tmp/spire-agent/public/api.sock
   # Should be readable by your agent's user
   ```

3. Check socket path in configuration matches actual location:
   ```yaml
   identity:
     spiffe_endpoint: unix:///tmp/spire-agent/public/api.sock
   ```

### Problem: No registration entry found

**Symptoms:**
```
IdentityError: No SVID available for this workload
```

**Solutions:**

1. List all registration entries:
   ```bash
   docker exec spire-server \
       /opt/spire/bin/spire-server entry show
   ```

2. Verify your workload matches a selector:
   ```bash
   # Check your process UID
   id -u

   # Check Kubernetes pod labels
   kubectl get pod <pod-name> -o yaml | grep labels: -A 5
   ```

3. Create registration entry if missing (see Step 3 above)

### Problem: SVID expired

**Symptoms:**
```
SVIDError: SVID has expired and rotation failed
```

**Solutions:**

1. SPIRE Agent should auto-rotate. Check agent logs:
   ```bash
   docker logs spire-agent
   # Look for rotation errors
   ```

2. Verify SPIRE Server is reachable:
   ```bash
   docker exec spire-agent \
       nc -zv spire-server 8081
   ```

3. Manually fetch new SVID:
   ```bash
   docker exec spire-agent \
       /opt/spire/bin/spire-agent api fetch -socketPath /tmp/spire-agent/public/api.sock
   ```

### Problem: Trust bundle validation failed

**Symptoms:**
```
PeerVerificationError: Cannot verify peer certificate chain
```

**Solutions:**

1. Ensure both agents are in the same trust domain or have federation configured

2. Check trust bundle is current:
   ```bash
   docker exec spire-server \
       /opt/spire/bin/spire-server bundle show
   ```

3. For federation, verify bundle endpoint is reachable:
   ```yaml
   identity:
     federation:
       enabled: true
       bundle_endpoints:
         partner.example.com: https://spire.partner.example.com/bundle
   ```

---

## Related Guides

- [Common Authorization Patterns](policy-patterns.md) - Define who can call your agents
- [Production Checklist](production-checklist.md) - Security checklist including identity verification
- [Error Handling](error-handling.md) - Handle IdentityError and SVIDError exceptions

---

## External Resources

- [SPIFFE Documentation](https://spiffe.io/docs/)
- [SPIRE Quickstart](https://spiffe.io/docs/latest/spire/installing/)
- [SPIRE Kubernetes Tutorial](https://github.com/spiffe/spire-tutorials/tree/main/k8s/quickstart)
- [py-spiffe Library](https://github.com/HewlettPackard/py-spiffe)
