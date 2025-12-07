---
layout: page
title: Identity & SPIFFE
description: Cryptographic workload identity with SPIFFE/SPIRE in AgentWeave
permalink: /core-concepts/identity/
parent: Core Concepts
nav_order: 3
---

# Identity & SPIFFE

Identity is the foundation of AgentWeave's security model. This document explains how agents get cryptographic identity using SPIFFE/SPIRE.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## What is SPIFFE?

**SPIFFE** (Secure Production Identity Framework for Everyone) is an open standard for cryptographic workload identity.

Think of SPIFFE as a universal ID card for services and agents. Just as your driver's license proves your identity to humans, a SPIFFE ID proves a workload's identity to other workloads.

### Why SPIFFE Matters

Traditional authentication has problems:

| Problem | Traditional Approach | SPIFFE Approach |
|---------|---------------------|-----------------|
| **Secret Management** | API keys in environment variables | No shared secrets, cryptographic proof |
| **Rotation** | Manual rotation, downtime | Automatic rotation, zero downtime |
| **Cross-Cloud** | Different auth per cloud provider | Universal identity standard |
| **Impersonation** | Secrets can be stolen | Cryptographic identity, hardware-attested |

{: .important }
**SPIFFE eliminates shared secrets.** There are no API keys, passwords, or tokens to leak. Identity is cryptographically proven using X.509 certificates.

### SPIFFE vs Traditional Auth

**Traditional API Key Auth:**
```python
# ❌ Shared secret in environment
api_key = os.environ["API_KEY"]
response = requests.post(
    "https://api.example.com/data",
    headers={"Authorization": f"Bearer {api_key}"}
)
```

Problems:
- Secret can be stolen from environment
- Manual rotation required
- No proof of caller identity (anyone with key can impersonate)

**SPIFFE Identity:**
```python
# ✅ Cryptographic identity, no shared secrets
# SDK handles everything automatically
result = await self.call_agent(
    target="spiffe://company.com/agent/search",
    task_type="search",
    payload={"query": "data"}
)
```

Benefits:
- No secrets in environment or config
- Automatic rotation before expiration
- Cryptographic proof of identity (can't be impersonated without private key)
- Works across cloud providers

---

## SPIFFE IDs Explained

A **SPIFFE ID** is a URI that uniquely identifies a workload.

### Format

```
spiffe://trust-domain/path

Examples:
spiffe://mycompany.com/agent/search/prod
spiffe://mycompany.com/agent/orchestrator/staging
spiffe://partner.example.com/agent/data-processor
```

### Components

**Trust Domain** (`mycompany.com`):
- The root of trust for your organization
- Like a DNS domain, but for identity
- Typically matches your company domain
- All agents within a trust domain trust the same CA

**Path** (`/agent/search/prod`):
- Hierarchical identifier for the workload
- Convention: `/agent/<agent-name>/<environment>`
- Can include arbitrary path segments
- Path is just an identifier—no inherent authorization

### Naming Conventions

AgentWeave recommends this structure:

```
spiffe://trust-domain/agent/<agent-name>/<environment>

Examples:
spiffe://mycompany.com/agent/search/prod
spiffe://mycompany.com/agent/search/staging
spiffe://mycompany.com/agent/orchestrator/prod
```

For shared infrastructure:

```
spiffe://mycompany.com/infra/spire-agent
spiffe://mycompany.com/infra/opa
spiffe://mycompany.com/k8s-node/worker-01
```

{: .note }
**SPIFFE IDs are case-sensitive.** `spiffe://MyCompany.com` and `spiffe://mycompany.com` are different trust domains.

---

## X.509 SVIDs (Certificates)

An **SVID** (SPIFFE Verifiable Identity Document) is a cryptographic proof of identity. The most common type is an X.509 SVID (a short-lived certificate).

### What's in an SVID?

An X.509 SVID is a standard X.509 certificate with extensions:

```
┌──────────────────────────────────────────────────────┐
│                X.509 Certificate                     │
├──────────────────────────────────────────────────────┤
│ Subject: (empty or workload-specific)                │
│ Issuer: CN=mycompany.com SPIRE CA                    │
│ Validity: Not Before / Not After (short-lived)       │
│ Public Key: RSA 2048 or ECDSA P-256                  │
│                                                       │
│ Extensions:                                          │
│   ┌────────────────────────────────────────────────┐ │
│   │ URI SAN: spiffe://mycompany.com/agent/search   │ │
│   └────────────────────────────────────────────────┘ │
│   (This is the SPIFFE ID)                            │
│                                                       │
│ Signature: (signed by SPIRE CA)                      │
└──────────────────────────────────────────────────────┘
```

**Key points:**
- **Subject**: Usually empty (SPIFFE ID is in URI SAN instead)
- **Issuer**: The SPIRE CA that signed the certificate
- **Validity**: Short-lived (default: 1 hour)
- **URI SAN**: Contains the SPIFFE ID
- **Signature**: Proves the certificate was issued by the trusted CA

### SVID Lifecycle

```
┌──────────────┐
│  SPIRE CA    │  Issues SVIDs
│  (Server)    │
└──────┬───────┘
       │
       ▼
┌──────────────┐
│ SPIRE Agent  │  Delivers SVIDs to workloads
│  (Daemon)    │
└──────┬───────┘
       │ Unix socket or TCP
       │ (Workload API)
       ▼
┌──────────────┐
│   Agent      │  Fetches and uses SVID
│  (Your code) │
└──────────────┘
```

1. **Issuance**: SPIRE Server issues SVID to SPIRE Agent
2. **Delivery**: SPIRE Agent delivers SVID to workload via Workload API
3. **Usage**: Workload uses SVID for mTLS authentication
4. **Rotation**: SVID expires, SPIRE Agent fetches new one
5. **Repeat**: Continuous rotation without downtime

### SVID Rotation

SVIDs are short-lived (typically 1 hour) and **automatically rotated**:

```
Time: 0:00      0:30      0:45      1:00      1:30
      │         │         │         │         │
SVID1 ├─────────┴─────────┴─────────┤
      │                   │         │
      │                   ├─────────┴─────────┤
      │                   SVID2 fetched       │
      │                   (15 min before exp)  │
      │                             │         │
      │                             ├─────────┴───────
      │                             SVID3 fetched
      │
```

**Rotation timeline:**
- **T+0**: SVID1 issued, valid for 1 hour
- **T+45min**: SDK fetches SVID2 (15 minutes before SVID1 expires)
- **T+60min**: SVID1 expires, SDK uses SVID2
- **T+105min**: SDK fetches SVID3
- **Continues indefinitely**

{: .note }
**No downtime during rotation.** The SDK holds both the current SVID and the next SVID during the overlap period, ensuring seamless transitions.

---

## SPIRE Overview

**SPIRE** (SPIFFE Runtime Environment) is the production implementation of SPIFFE. It consists of two components:

### SPIRE Server

**Purpose**: Issues SVIDs to workloads

**Responsibilities:**
- Manages the root CA (signing SVIDs)
- Stores registration entries (which workloads get which SPIFFE IDs)
- Attests SPIRE Agents (proves they're legitimate)
- Federates with other SPIRE Servers (cross-org trust)

**Deployment:**
- Usually 1-3 replicas for HA
- Runs in a secure, central location
- Does **not** run on the same node as workloads

### SPIRE Agent

**Purpose**: Delivers SVIDs to workloads on the local node

**Responsibilities:**
- Attests the node to SPIRE Server (proves node identity)
- Fetches SVIDs for workloads running on the node
- Provides Workload API (Unix socket or TCP) for workloads to fetch SVIDs
- Rotates SVIDs before expiration

**Deployment:**
- One per node (DaemonSet in Kubernetes)
- Runs on every machine hosting workloads
- Exposes Unix socket at `/run/spire/sockets/agent.sock`

### How SPIRE Works

```
┌─────────────────────────────────────────────────────┐
│                 Kubernetes Cluster                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │         SPIRE Server (Deployment)             │ │
│  │                                               │ │
│  │  • Root CA: mycompany.com                     │ │
│  │  • Registration DB: Which workloads get       │ │
│  │    which SPIFFE IDs                           │ │
│  └───────────────────┬───────────────────────────┘ │
│                      │                             │
│                      │ gRPC                        │
│                      │                             │
│  ┌───────────────────▼──────────┐                  │
│  │  SPIRE Agent (DaemonSet)     │                  │
│  │  Runs on each node           │                  │
│  │                              │                  │
│  │  /run/spire/sockets/         │                  │
│  │    agent.sock                │                  │
│  └────────┬─────────────────────┘                  │
│           │                                         │
│           │ Workload API (Unix socket)             │
│           │                                         │
│  ┌────────▼──────────┐                             │
│  │  AgentWeave Agent │                             │
│  │  (Your workload)  │                             │
│  │                   │                             │
│  │  Fetches SVID via │                             │
│  │  Workload API     │                             │
│  └───────────────────┘                             │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## Trust Domains and Federation

### Trust Domains

A **trust domain** is a boundary of trust. All workloads within a trust domain trust the same root CA.

**Example:**
- Trust domain: `mycompany.com`
- Root CA: SPIRE Server for `mycompany.com`
- All agents with SPIFFE IDs under `spiffe://mycompany.com/*` trust this CA

### Federation

**Federation** allows workloads in different trust domains to trust each other.

**Use cases:**
- Multi-organization collaboration
- Mergers and acquisitions
- Cross-cloud deployments with separate SPIRE Servers

**Example:**

Company A (`companyA.com`) and Company B (`companyB.com`) want their agents to communicate:

```
┌───────────────────────┐         ┌───────────────────────┐
│   Company A           │         │   Company B           │
│   Trust Domain:       │         │   Trust Domain:       │
│   companyA.com        │         │   companyB.com        │
│                       │         │                       │
│  ┌─────────────────┐  │         │  ┌─────────────────┐  │
│  │ SPIRE Server A  │◄─┼─────────┼─►│ SPIRE Server B  │  │
│  │                 │  │Federation│  │                 │  │
│  └─────────────────┘  │         │  └─────────────────┘  │
│                       │         │                       │
│  Agent A can now      │         │  Agent B can now      │
│  verify Agent B's     │         │  verify Agent A's     │
│  SVID                 │         │  SVID                 │
└───────────────────────┘         └───────────────────────┘
```

**Configuration:**

Company A trusts Company B's SPIRE Server:

```yaml
# Company A's AgentWeave config
identity:
  provider: "spiffe"
  allowed_trust_domains:
    - "companyA.com"      # Own trust domain
    - "companyB.com"      # Federated trust domain
```

Now Agent A can call Agent B:

```python
# Agent A calling Agent B (different trust domain)
result = await self.call_agent(
    target="spiffe://companyB.com/agent/data-processor",
    task_type="process",
    payload={...}
)
```

{: .warning }
**Federation requires explicit configuration.** You must configure SPIRE federation on both SPIRE Servers and add the federated trust domain to `allowed_trust_domains` in your AgentWeave config.

---

## The SPIFFEIdentityProvider Class

AgentWeave's `SPIFFEIdentityProvider` handles all SPIFFE/SPIRE interactions.

### Initialization

```python
from agentweave.identity import SPIFFEIdentityProvider

# Auto-detect SPIRE Agent from environment variable
provider = SPIFFEIdentityProvider()

# Or specify endpoint explicitly
provider = SPIFFEIdentityProvider(
    endpoint="unix:///run/spire/sockets/agent.sock"
)
```

**Environment variable:**
```bash
export SPIFFE_ENDPOINT_SOCKET="unix:///run/spire/sockets/agent.sock"
```

### Getting an SVID

```python
# Fetch current SVID
svid = await provider.get_svid()

print(f"SPIFFE ID: {svid.spiffe_id}")
print(f"Expires: {svid.expiry}")
print(f"Certificate: {svid.cert_chain_path}")
print(f"Private Key: {svid.private_key_path}")
```

**SVID Object:**
```python
@dataclass
class X509Svid:
    spiffe_id: str              # spiffe://company.com/agent/search
    cert_chain_path: str        # Path to certificate file
    private_key_path: str       # Path to private key file
    expiry: datetime            # When SVID expires
    cert_chain: list[x509.Certificate]  # Parsed certificates
```

### Getting Trust Bundles

Trust bundles contain CA certificates for verifying peers:

```python
# Get trust bundle for a trust domain
bundle = await provider.get_trust_bundle("companyB.com")

print(f"Trust Domain: {bundle.trust_domain}")
print(f"CA Certificates: {len(bundle.ca_certs)}")
```

### Watching for Updates

The provider streams SVID rotation events:

```python
# Watch for SVID rotation
async for update in provider.watch_updates():
    print(f"SVID rotated: {update.svid.spiffe_id}")
    print(f"New expiry: {update.svid.expiry}")

    # SDK automatically updates mTLS contexts
```

{: .note }
**You don't need to watch updates manually.** The SDK handles SVID rotation automatically in the background.

---

## Creating mTLS Contexts

The identity provider creates SSL contexts for mTLS:

```python
# Get SVID and trust bundle
svid = await provider.get_svid()
bundle = await provider.get_trust_bundle("company.com")

# Create SSL context for mTLS
import ssl

ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.minimum_version = ssl.TLSVersion.TLSv1_3

# Load our certificate (proves our identity)
ctx.load_cert_chain(
    certfile=svid.cert_chain_path,
    keyfile=svid.private_key_path
)

# Load CA bundle (for verifying peer)
ctx.load_verify_locations(cafile=bundle.ca_cert_path)

# Require peer verification
ctx.verify_mode = ssl.CERT_REQUIRED
ctx.check_hostname = False  # SPIFFE uses SPIFFE ID, not hostname

# Use context for HTTPS
import httpx
async with httpx.AsyncClient(verify=ctx) as client:
    response = await client.post("https://peer-agent:8443/api", ...)
```

{: .note }
**The SDK handles mTLS setup.** You don't need to create SSL contexts manually—the transport layer does this automatically.

---

## SPIRE Registration

Before a workload can get an SVID, it must be **registered** in SPIRE.

### Registration Entry

A registration entry tells SPIRE:
- **Which workload** gets an SVID (identified by selectors)
- **What SPIFFE ID** to issue

**Example (Kubernetes):**

```bash
# Register search-agent in Kubernetes
spire-server entry create \
  -spiffeID spiffe://mycompany.com/agent/search/prod \
  -parentID spiffe://mycompany.com/k8s-node \
  -selector k8s:ns:agents \
  -selector k8s:sa:search-agent \
  -selector k8s:pod-label:app:search-agent
```

**Explanation:**
- **spiffeID**: The SPIFFE ID to issue to this workload
- **parentID**: The SPIRE Agent's SPIFFE ID (proves agent is legitimate)
- **Selectors**: How to identify the workload
  - `k8s:ns:agents`: Pod in `agents` namespace
  - `k8s:sa:search-agent`: Uses `search-agent` ServiceAccount
  - `k8s:pod-label:app:search-agent`: Has label `app=search-agent`

When all selectors match, SPIRE issues the SVID with the specified SPIFFE ID.

### Selectors

Selectors are key-value pairs that identify workloads. Common selectors:

**Kubernetes:**
- `k8s:ns:<namespace>`: Namespace
- `k8s:sa:<service-account>`: ServiceAccount
- `k8s:pod-label:<key>:<value>`: Pod label
- `k8s:container-name:<name>`: Container name

**Unix:**
- `unix:uid:<uid>`: User ID
- `unix:gid:<gid>`: Group ID
- `unix:path:<path>`: Executable path

**Docker:**
- `docker:label:<key>:<value>`: Container label
- `docker:env:<key>:<value>`: Environment variable

{: .important }
**Selectors must be specific.** Overly broad selectors (e.g., just `k8s:ns:default`) can issue SVIDs to unintended workloads.

---

## Security Considerations

### SPIRE Agent Socket Security

The SPIRE Agent Unix socket is the **most sensitive component**. Anyone who can access the socket can fetch SVIDs for workloads on that node.

**Protection:**
- **File permissions**: Socket should be readable only by root or a specific group
- **Kubernetes**: Mount socket as `readOnly: true` in agent containers
- **Namespace isolation**: SPIRE Agent runs in dedicated namespace

**Example (Kubernetes):**

```yaml
volumes:
  - name: spire-socket
    hostPath:
      path: /run/spire/sockets
      type: Directory

volumeMounts:
  - name: spire-socket
    mountPath: /run/spire/sockets
    readOnly: true  # ✅ Read-only mount
```

### SVID Expiration

SVIDs are short-lived to limit the damage from a compromised SVID:

- **Default TTL**: 1 hour
- **Rotation**: 15 minutes before expiration
- **Impact of compromise**: Attacker has at most 1 hour of access

If an SVID is compromised, the attacker can impersonate the workload until expiration. Short TTLs limit this window.

### Trust Domain Isolation

Each trust domain is independent. Workloads in different trust domains **cannot** communicate unless:
- Trust domains are federated
- The federated trust domain is in `allowed_trust_domains`

This isolation prevents lateral movement across organizational boundaries.

---

## Troubleshooting

### SVID Fetch Failed

**Error:**
```
IdentityError: Failed to fetch SVID from Workload API
```

**Causes:**
- SPIRE Agent not running
- Socket path incorrect
- No registration entry for this workload
- Selectors don't match

**Solution:**

```bash
# Check SPIRE Agent is running
kubectl get pods -n spire-system -l app=spire-agent

# Check socket exists
ls -la /run/spire/sockets/agent.sock

# Check registration entries
spire-server entry show

# Test Workload API manually
spire-agent api fetch x509
```

### SPIFFE ID Mismatch

**Error:**
```
PeerVerificationError: Expected spiffe://company.com/agent/search, got spiffe://company.com/agent/processor
```

**Cause:** You specified the wrong target SPIFFE ID in `call_agent()`

**Solution:** Verify the target agent's SPIFFE ID (check their Agent Card or SPIRE registration)

### Trust Bundle Not Found

**Error:**
```
IdentityError: Trust bundle for trust domain 'partner.com' not found
```

**Cause:** Trying to call an agent in a trust domain that isn't federated

**Solution:**

1. Configure SPIRE federation between trust domains
2. Add `partner.com` to `allowed_trust_domains` in config

---

## What's Next?

Now that you understand identity, learn how it's used for authorization:

- [Authorization & OPA](/agentweave/core-concepts/authorization/): Policy-based access control using SPIFFE IDs
- [A2A Protocol](/agentweave/core-concepts/communication/): How agents use mTLS with SPIFFE for secure communication
- [Security Model](/agentweave/core-concepts/security-model/): How identity fits into the overall security architecture

{: .note }
SPIFFE/SPIRE is a deep topic. This guide covers what you need to build agents. For SPIRE administration (setup, federation, policy), see the [SPIRE documentation](https://spiffe.io/docs/).
