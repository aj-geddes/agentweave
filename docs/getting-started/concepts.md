---
layout: page
title: Core Concepts
description: Understanding AgentWeave's architecture and security model
nav_order: 3
parent: Getting Started
---

# Core Concepts

This guide introduces the fundamental concepts behind AgentWeave. Understanding these concepts will help you build secure, scalable agent systems.

## What is AgentWeave?

**AgentWeave** is a Python SDK for building secure, cross-cloud AI agents. It combines industry-standard security technologies (SPIFFE, mTLS, OPA) with the A2A (Agent-to-Agent) protocol to provide a developer-friendly framework where **security is automatic and mandatory**.

In a traditional agent framework, you write code like:

```python
# Traditional approach - security is manual
def handle_request(request):
    # Developer must remember to:
    cert = verify_certificate(request.cert)     # 1. Verify identity
    if not check_permissions(cert, request):     # 2. Check authorization
        raise Forbidden()
    # Finally, business logic
    return process(request.data)
```

With AgentWeave, security is handled by the SDK:

```python
# AgentWeave approach - security is automatic
from agentweave import SecureAgent, capability

class MyAgent(SecureAgent):
    @capability("process")
    async def process(self, data: dict) -> dict:
        # Identity verified ✓
        # Authorization checked ✓
        # Just implement your logic
        return await self._process(data)
```

## The "Secure Path is the Only Path" Principle

AgentWeave's architecture ensures that **developers cannot bypass security**, even accidentally. This principle is enforced through:

1. **No agent starts without identity** - The SDK refuses to start if it can't obtain a valid SPIFFE identity
2. **No communication without mTLS** - All agent-to-agent calls use mutual TLS with certificate verification
3. **No request without authorization** - OPA policies are checked before your handler code runs
4. **No configuration bypasses** - Security-critical settings are validated at startup

The only way security can fail is through **configuration errors** (wrong policies, misconfigured SPIRE entries), which are preventable through CI/CD validation and policy review.

## Key Components

AgentWeave's architecture consists of five layers:

```
┌─────────────────────────────────────────┐
│         Your Agent Code                 │  ← Business logic only
├─────────────────────────────────────────┤
│         AgentWeave SDK                  │  ← Security & communication
│  ┌──────────┬──────────┬──────────────┐ │
│  │ Identity │   AuthZ  │ Communication│ │
│  │  Layer   │   Layer  │    Layer     │ │
│  └────┬─────┴─────┬────┴──────┬───────┘ │
├───────┴───────────┴───────────┴─────────┤
│         Transport Layer (mTLS)          │  ← Encrypted connections
└─────────────────────────────────────────┘
           │            │            │
    ┌──────┴────┐  ┌────┴─────┐  ┌──┴──────┐
    │   SPIRE   │  │   OPA    │  │  A2A    │  ← External systems
    └───────────┘  └──────────┘  └─────────┘
```

### 1. Identity Layer (SPIFFE/SPIRE)

Every agent has a **cryptographic identity** in the form of a SPIFFE ID.

**SPIFFE ID Format**: `spiffe://trust-domain/path/to/workload`

Example: `spiffe://myorg.com/agent/data-processor/production`

**Key Concepts**:

- **SPIFFE**: Specification for workload identity (like a passport for software)
- **SVID**: SPIFFE Verifiable Identity Document (an X.509 certificate)
- **SPIRE**: Implementation that issues and manages SVIDs
- **Trust Domain**: Namespace for identities (like `myorg.com`)

**How it Works**:

```
1. Agent starts → Requests SVID from SPIRE Agent (via Unix socket)
2. SPIRE Agent → Checks agent's selectors (user ID, k8s pod, etc.)
3. SPIRE Server → Issues short-lived X.509 certificate (SVID)
4. Agent → Uses SVID for mTLS connections
5. SVID expires → SPIRE automatically rotates (no downtime)
```

{: .note }
> **No Secrets Required**: Unlike API keys or passwords, SVIDs are issued based on platform attestation (process UID, Kubernetes service account, etc.). Nothing to leak!

### 2. Authorization Layer (OPA)

Authorization is handled by **Open Policy Agent** (OPA), a policy engine that makes decisions based on **Rego** policies.

**How it Works**:

```
1. Request arrives → SDK extracts caller's SPIFFE ID from mTLS cert
2. SDK → Asks OPA: "Can spiffe://caller call this capability?"
3. OPA → Evaluates Rego policy, returns allow/deny
4. SDK → Only calls your handler if allowed
```

**Example Policy** (Rego):

```rego
package agentweave.authz

default allow = false

# Allow agents in the same trust domain
allow {
    caller_domain := split(input.caller_spiffe_id, "/")[2]
    callee_domain := split(input.callee_spiffe_id, "/")[2]
    caller_domain == callee_domain
}

# Allow specific cross-agent calls
allow {
    input.caller_spiffe_id == "spiffe://myorg.com/agent/orchestrator"
    input.callee_spiffe_id == "spiffe://myorg.com/agent/worker"
    input.action == "process_task"
}
```

{: .warning }
> **Production Default**: Always use `default allow = false` (default deny). Explicitly list what's allowed, not what's forbidden.

### 3. Communication Layer (A2A Protocol)

Agents communicate using the **A2A (Agent-to-Agent) Protocol**, an open standard originally from Google.

**Key Concepts**:

- **Agent Card**: JSON metadata advertising capabilities (like an API schema)
- **Task**: Unit of work with a lifecycle (submitted → working → completed)
- **Capability**: A method an agent exposes (like `"search"`, `"process"`)
- **Artifact**: Output produced by a task

**Agent Card Example**:

```json
{
  "name": "search-agent",
  "description": "Searches documents",
  "capabilities": [
    {
      "name": "search",
      "description": "Search for documents",
      "input_modes": ["application/json"],
      "output_modes": ["application/json"]
    }
  ],
  "extensions": {
    "spiffe_id": "spiffe://myorg.com/agent/search"
  }
}
```

**Task Lifecycle**:

```
submitted → working → completed
                  ↘ failed
```

{: .note }
> **Framework Agnostic**: A2A is an open protocol. Your AgentWeave agents can talk to agents built with Google ADK, AWS Bedrock AgentCore, or any A2A-compatible framework.

### 4. Transport Layer (mTLS)

All communication uses **mutual TLS** (mTLS), where both parties authenticate each other:

```
Agent A                                Agent B
   |                                      |
   |  ClientHello (+ client cert) -----→ |
   |                                      |
   | ←----- ServerHello (+ server cert)  |
   |                                      |
   |  Verify: Is this really Agent B?    |
   |         (Check SPIFFE ID in cert)   |
   |                                      |
   |                         Verify: Is this really Agent A?
   |                         (Check SPIFFE ID in cert)
   |                                      |
   | ←-→ Encrypted data exchange ←-→ |
```

**Security Guarantees**:

- **Encryption**: All data encrypted with TLS 1.3
- **Authentication**: Both sides verify each other's identity
- **Integrity**: Tampering detected automatically
- **No Downgrade**: SDK enforces minimum TLS version

## Agent Lifecycle

Understanding the lifecycle helps you debug issues and write robust agents.

### Startup Sequence

```
1. Load Configuration
   ↓ (validates security settings)
2. Acquire Identity
   ↓ (connect to SPIRE, fetch SVID)
3. Connect to OPA
   ↓ (verify policies are loaded)
4. Initialize Transport
   ↓ (create mTLS server)
5. Register Capabilities
   ↓ (generate Agent Card)
6. Start Server
   ↓ (listen for incoming requests)
7. Ready to Serve
```

If any step fails, the agent **refuses to start**. This fail-fast behavior prevents running in an insecure state.

### Request Handling

When a request arrives:

```
1. mTLS Handshake
   ↓ (verify peer's SPIFFE ID)
2. Authorization Check
   ↓ (ask OPA: is this allowed?)
3. Parse A2A Task
   ↓ (extract capability and payload)
4. Route to Handler
   ↓ (@capability decorated method)
5. Execute Business Logic
   ↓ (your code runs here)
6. Return Result
   ↓ (wrap in A2A response)
7. Audit Log
   ↓ (record for compliance)
```

Your code only runs at step 5 - security is handled in steps 1-4.

### Graceful Shutdown

```
1. Receive SIGTERM
   ↓
2. Stop Accepting New Requests
   ↓
3. Wait for In-Flight Requests (max 30s)
   ↓
4. Close Connections
   ↓
5. Exit
```

## Security Model Overview

AgentWeave implements a **zero-trust security model**:

### Defense in Depth

Multiple layers of security:

1. **Network**: Encrypted with TLS 1.3
2. **Identity**: Cryptographic verification via SPIFFE
3. **Authentication**: Mutual TLS with certificate validation
4. **Authorization**: Policy-based enforcement via OPA
5. **Audit**: All requests logged for forensics

### Trust Boundaries

```
┌─────────────────────────────────────┐
│      Trust Domain: myorg.com        │
│                                     │
│  ┌────────┐  ┌────────┐  ┌────────┐│
│  │Agent A │←→│Agent B │←→│Agent C ││
│  └────────┘  └────────┘  └────────┘│
│      ↓           ↓           ↓      │
│    SPIFFE     SPIFFE     SPIFFE    │
└─────────────────────────────────────┘
         ↓ (federation)
┌─────────────────────────────────────┐
│   Trust Domain: partner.example.com │
│                                     │
│  ┌────────┐                         │
│  │Agent D │ (requires federation)   │
│  └────────┘                         │
└─────────────────────────────────────┘
```

Agents within the same trust domain can communicate by default (if policies allow). Cross-domain communication requires **SPIRE federation** and explicit policies.

### What Can Go Wrong?

Since the SDK enforces security, the only attack vectors are:

1. **Misconfigured Policies**: Overly permissive OPA rules (e.g., `allow = true` without conditions)
2. **Wrong SPIRE Registration**: Agent registered with incorrect selectors
3. **Compromised Infrastructure**: SPIRE Server or OPA compromised
4. **Policy Bypass**: OPA not running (prevented by SDK refusing to start)

**Mitigation**: CI/CD validation, policy review, infrastructure hardening, and monitoring.

## Glossary of Terms

| Term | Definition | Example |
|------|------------|---------|
| **SPIFFE** | Secure Production Identity Framework for Everyone | Standard for workload identity |
| **SPIRE** | SPIFFE Runtime Environment | Implementation that issues SVIDs |
| **SVID** | SPIFFE Verifiable Identity Document | X.509 certificate with SPIFFE ID |
| **Trust Domain** | Namespace for SPIFFE identities | `myorg.com`, `production.cloud` |
| **OPA** | Open Policy Agent | Policy engine for authorization |
| **Rego** | Policy language used by OPA | `allow { input.role == "admin" }` |
| **A2A** | Agent-to-Agent Protocol | Standard for agent communication |
| **Agent Card** | Metadata describing agent capabilities | JSON document at `/.well-known/agent.json` |
| **Capability** | A method/function an agent exposes | `"search"`, `"process"`, `"analyze"` |
| **mTLS** | Mutual TLS | Both client and server authenticate |
| **Task** | Unit of work in A2A protocol | Request with lifecycle tracking |
| **Artifact** | Output produced by a task | Data, files, or results |

## Architecture Patterns

### Single Agent

The simplest pattern - one agent serving requests:

```
Client → Agent (with SPIFFE ID, OPA policies)
```

Use case: Standalone service, API endpoint, function-as-a-service

### Multi-Agent Orchestration

An orchestrator coordinates multiple worker agents:

```
Orchestrator Agent
   ├→ Search Agent
   ├→ Analysis Agent
   └→ Storage Agent
```

Use case: Complex workflows, multi-step processes

### Agent Mesh

Peer-to-peer agent network:

```
    Agent A ←→ Agent B
       ↓   ×     ↓
    Agent C ←→ Agent D
```

Use case: Distributed systems, microservices, event-driven architectures

### Cross-Cloud Federation

Agents across different clouds/organizations:

```
┌─────────────────────┐         ┌─────────────────────┐
│   AWS (myorg.com)   │         │ GCP (partner.com)   │
│  ┌────────┐         │         │         ┌────────┐  │
│  │Agent A │─────────┼─────────┼────────→│Agent B │  │
│  └────────┘         │ (mTLS + │         └────────┘  │
│   SPIRE + OPA       │  federated trust) │ SPIRE + OPA│
└─────────────────────┘         └─────────────────────┘
```

Use case: Multi-cloud, B2B integration, hybrid deployments

## Next Steps

Now that you understand the core concepts:

- **[Hello World Tutorial](hello-world.md)** - Build a complete agent with explanations
- **[Configuration Reference](/agentweave/configuration/)** - Deep dive into config options
- **[Security Guide](/agentweave/security/)** - Production hardening best practices
- **[A2A Protocol](/agentweave/a2a-protocol/)** - Detailed protocol specification

---

**Previous**: [← 5-Minute Quickstart](quickstart.md) | **Next**: [Hello World Tutorial →](hello-world.md)
