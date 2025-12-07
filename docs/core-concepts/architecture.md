---
layout: page
title: System Architecture
description: High-level architecture and component interactions in AgentWeave
permalink: /core-concepts/architecture/
parent: Core Concepts
nav_order: 1
---

# System Architecture

This document provides a comprehensive view of AgentWeave's architecture, explaining how components interact to provide secure, scalable agent-to-agent communication.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## High-Level Architecture

AgentWeave consists of multiple layers, each with a specific security responsibility:

```
┌─────────────────────────────────────────────────────────────────┐
│                     AgentWeave SDK                              │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Agent     │  │   Agent     │  │        Agent            │ │
│  │   Code      │  │   Code      │  │        Code             │ │
│  │  (Custom)   │  │  (Custom)   │  │      (Custom)           │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                      │               │
│  ┌──────┴────────────────┴──────────────────────┴─────────────┐│
│  │                  SecureAgent (SDK Core)                    ││
│  │  • Lifecycle management (start/stop)                       ││
│  │  • Configuration loading & validation                      ││
│  │  • Capability registration & routing                       ││
│  │  • Health checks & metrics                                 ││
│  └──────┬────────────────┬──────────────────────┬─────────────┘│
│         │                │                      │               │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌───────────▼─────────────┐ │
│  │  Identity   │  │   AuthZ     │  │      Communication      │ │
│  │   Layer     │  │   Layer     │  │         Layer           │ │
│  │             │  │             │  │                         │ │
│  │ • SPIFFE    │  │ • OPA       │  │ • A2A Protocol          │ │
│  │ • SVIDs     │  │ • Policies  │  │ • Agent Cards           │ │
│  │ • Rotation  │  │ • Audit     │  │ • Task Management       │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                      │               │
│  ┌──────┴────────────────┴──────────────────────┴─────────────┐│
│  │                   Transport Layer                          ││
│  │  • mTLS (mandatory)                                        ││
│  │  • Connection pooling                                      ││
│  │  • Circuit breakers                                        ││
│  │  • Retry with exponential backoff                          ││
│  └────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │ Infrastructure    │
                    │ • SPIRE Agent     │ (sidecar or DaemonSet)
                    │ • OPA Agent       │ (sidecar)
                    │ • Tailscale (opt) │ (daemon)
                    └───────────────────┘
```

## Core Components

### 1. Agent Layer

The **Agent Layer** is where your business logic lives. This is the code you write.

**Components:**
- **BaseAgent**: Minimal agent with lifecycle management, no security
- **SecureAgent**: Production agent class with automatic security enforcement
- **Custom Agents**: Your agent implementations extending SecureAgent

**Responsibilities:**
- Define capabilities using the `@capability` decorator
- Implement business logic in capability handlers
- Call other agents using `call_agent()` method
- Handle errors and return structured results

**Example:**
```python
from agentweave import SecureAgent, capability

class SearchAgent(SecureAgent):
    """Searches data stores for information."""

    @capability("search")
    async def search(self, query: str, filters: dict = None) -> TaskResult:
        results = await self._database.search(query, filters)
        return TaskResult(
            status="completed",
            artifacts=[{"type": "results", "data": results}]
        )
```

### 2. Identity Layer

The **Identity Layer** provides cryptographic workload identity using SPIFFE/SPIRE.

**Components:**
- **IdentityProvider** (interface): Abstract identity provider
- **SPIFFEIdentityProvider**: Production implementation using SPIRE Workload API
- **StaticMTLSProvider**: Development/testing fallback with static certificates

**Responsibilities:**
- Fetch X.509 SVIDs (certificates) from SPIRE Agent
- Automatically rotate SVIDs before expiration
- Manage trust bundles for peer verification
- Provide SPIFFE ID for local workload

**Key Classes:**
```python
class SPIFFEIdentityProvider:
    async def get_svid(self) -> X509Svid:
        """Get current SVID (auto-rotates)."""

    async def get_trust_bundle(self, trust_domain: str) -> X509Bundle:
        """Get CA bundle for verifying peers."""

    def get_spiffe_id(self) -> str:
        """Get this agent's SPIFFE ID."""
```

**SPIFFE ID Format:**
```
spiffe://trust-domain/agent/agent-name/environment

Examples:
- spiffe://mycompany.com/agent/search/prod
- spiffe://mycompany.com/agent/orchestrator/staging
```

See [Identity & SPIFFE](/core-concepts/identity/) for details.

### 3. Authorization Layer

The **Authorization Layer** enforces policy-based access control using Open Policy Agent (OPA).

**Components:**
- **PolicyEnforcer** (interface): Abstract authorization provider
- **OPAEnforcer**: Production implementation using OPA
- **AllowAllProvider**: Development-only (never use in production)

**Responsibilities:**
- Check if caller is authorized before executing capabilities
- Enforce outbound policies (can I call this agent?)
- Enforce inbound policies (can this caller invoke me?)
- Log all authorization decisions for audit

**Key Classes:**
```python
class OPAEnforcer:
    async def check_inbound(
        self,
        caller_id: str,
        action: str,
        context: dict
    ) -> AuthzDecision:
        """Check if incoming request is allowed."""

    async def check_outbound(
        self,
        caller_id: str,
        callee_id: str,
        action: str,
        context: dict
    ) -> AuthzDecision:
        """Check if outbound call is allowed."""
```

**Authorization Decision:**
```python
@dataclass(frozen=True)
class AuthzDecision:
    allowed: bool          # True if authorized
    reason: str            # Human-readable explanation
    audit_id: str          # Unique ID for audit trail
```

See [Authorization & OPA](/core-concepts/authorization/) for details.

### 4. Communication Layer

The **Communication Layer** implements the A2A (Agent-to-Agent) protocol for standardized communication.

**Components:**
- **A2AClient**: Sends tasks to other agents
- **A2AServer**: Receives and routes incoming tasks
- **AgentCard**: Advertises capabilities and metadata
- **Task**: Represents a unit of work

**Responsibilities:**
- Serialize/deserialize A2A messages (JSON-RPC 2.0)
- Manage task lifecycle (submitted → working → completed)
- Publish Agent Cards for discovery
- Handle streaming responses for long-running tasks

**Key Classes:**
```python
class A2AClient:
    async def send_task(
        self,
        target_agent: str,     # SPIFFE ID
        task_type: str,        # Capability name
        payload: dict,         # Task input
        timeout: float = 30.0
    ) -> TaskResult:
        """Send task to another agent."""

class AgentCard:
    name: str
    description: str
    spiffe_id: str
    capabilities: list[Capability]

    def to_json(self) -> dict:
        """Serialize to A2A Agent Card format."""
```

See [A2A Protocol](/core-concepts/communication/) for details.

### 5. Transport Layer

The **Transport Layer** handles secure networking with mandatory mTLS.

**Components:**
- **SecureChannel**: mTLS connection to a single peer
- **ConnectionPool**: Manages reusable connections
- **CircuitBreaker**: Prevents cascading failures
- **RetryPolicy**: Handles transient failures

**Responsibilities:**
- Establish mTLS connections using SVIDs
- Verify peer SPIFFE IDs match expected values
- Pool connections for performance
- Implement circuit breaker pattern for resilience
- Retry failed requests with exponential backoff

**Key Classes:**
```python
class SecureChannel:
    async def post(
        self,
        path: str,
        json: dict,
        timeout: float
    ) -> httpx.Response:
        """Make authenticated POST request."""

    async def verify_peer(self, cert: x509.Certificate) -> bool:
        """Verify peer's SPIFFE ID."""
```

**Security Features:**
- TLS 1.3 minimum (1.2 allowed but warned)
- Mutual authentication (both sides verify)
- Certificate pinning via SPIFFE ID
- No hostname verification (SPIFFE ID is the identity)

---

## Request Flow: Agent-to-Agent Call

Here's what happens when Agent A calls Agent B:

```
Agent-A (Caller)                                     Agent-B (Callee)
      │                                                    │
      ├─► 1. call_agent("spiffe://...agent-b", task)     │
      │         │                                          │
      │         ├─► 2. Identity: Get my SVID              │
      │         │         │                                │
      │         │         └─► SPIRE Agent (Unix socket)   │
      │         │             Returns X.509 cert          │
      │         │                                          │
      │         ├─► 3. AuthZ: Check outbound policy       │
      │         │         │                                │
      │         │         └─► OPA: Can I call Agent-B?    │
      │         │             Evaluates Rego policy        │
      │         │             Returns allow/deny           │
      │         │                                          │
      │         ├─► 4. Transport: Establish mTLS          │
      │         │         │                                │
      │         │         ├─► Create SSL context          │
      │         │         ├─► Load my SVID as client cert │
      │         │         ├─► Load trust bundle for CA    │
      │         │         └─► Verify peer SVID            │
      │         │                                          │
      │         └─► 5. Comms: Send A2A Task ──────────────┼──►
      │                 (JSON-RPC over HTTPS)              │
      │                                                    │
      │                                   6. Transport: Verify caller SVID
      │                                         │
      │                                         ├─► Extract peer cert
      │                                         ├─► Verify SPIFFE ID
      │                                         └─► Matches Agent-A
      │                                                    │
      │                                   7. AuthZ: Check inbound policy
      │                                         │
      │                                         └─► OPA: Can Agent-A call me?
      │                                             Evaluates policy
      │                                             Returns allow/deny
      │                                                    │
      │                                   8. Route to capability handler
      │                                         │
      │                                         └─► Execute business logic
      │                                             Return TaskResult
      │                                                    │
      │◄──────────────────────────────── 9. Return result │
      │                 (JSON-RPC response)                │
      │                                                    │
      └─► 10. Return TaskResult to caller                 │
```

### Step-by-Step Breakdown

**Steps 1-2: Identity Acquisition**
- Agent A's SDK fetches its current SVID from the local SPIRE Agent
- The SVID is cached and automatically rotated before expiration
- The SPIFFE ID identifies Agent A (e.g., `spiffe://company.com/agent/orchestrator`)

**Step 3: Outbound Authorization**
- Before making the call, Agent A checks if it's allowed to call Agent B
- OPA evaluates the policy using Agent A's SPIFFE ID, Agent B's SPIFFE ID, and the action
- If denied, the call fails immediately without network traffic

**Step 4: Secure Channel Establishment**
- Agent A creates an mTLS connection to Agent B
- Client certificate: Agent A's SVID
- Server certificate: Agent B's SVID (verified against expected SPIFFE ID)
- Trust bundle: CA certificates for the trust domain

**Step 5: Send A2A Task**
- The task is serialized to JSON-RPC 2.0 format
- Sent over the mTLS channel (encrypted, authenticated)
- Agent B's endpoint receives the request

**Steps 6-7: Inbound Verification**
- Agent B verifies Agent A's SPIFFE ID from the client certificate
- Agent B checks authorization: "Is Agent A allowed to call this capability?"
- If denied, Agent B returns an authorization error

**Step 8: Execute Business Logic**
- Only if all security checks pass does Agent B execute the capability handler
- Your code runs in the handler—security is already enforced
- Business logic returns a TaskResult

**Steps 9-10: Return Response**
- Result is serialized and sent back over the mTLS channel
- Agent A receives the TaskResult
- The `call_agent()` method returns the result to your code

---

## Component Interactions

### Identity + Transport

The identity layer provides certificates that the transport layer uses for mTLS:

```python
# Identity provides the SVID
svid = await identity_provider.get_svid()

# Transport uses it to create SSL context
ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ssl_context.load_cert_chain(
    certfile=svid.cert_chain_path,
    keyfile=svid.private_key_path
)
```

### Identity + Authorization

The authorization layer uses SPIFFE IDs from the identity layer:

```python
# Identity provides SPIFFE ID
my_spiffe_id = identity_provider.get_spiffe_id()

# Authorization uses it in policy evaluation
decision = await authz.check_outbound(
    caller_id=my_spiffe_id,  # From identity
    callee_id="spiffe://company.com/agent/target",
    action="search"
)
```

### Transport + Communication

The communication layer uses the transport layer for all network calls:

```python
# Communication layer builds A2A task
task = Task(type="search", payload={"query": "..."})

# Transport layer sends it over mTLS
response = await secure_channel.post(
    "/.well-known/a2a/tasks/send",
    json=task.to_jsonrpc()
)
```

### Authorization + Communication

Every A2A request is authorized before execution:

```python
# A2A server receives task
task = parse_a2a_task(request.json())

# Authorization checks before routing
decision = await authz.check_inbound(
    caller_id=peer_spiffe_id,
    action=task.type,
    context={"task_id": task.id}
)

if not decision.allowed:
    raise AuthorizationError(decision.reason)

# Only then route to handler
result = await route_to_capability(task)
```

---

## Design Principles

### 1. Separation of Concerns

Each layer has a single, well-defined responsibility:
- **Identity**: Who am I? Who are you?
- **Transport**: How do we communicate securely?
- **Authorization**: What are you allowed to do?
- **Communication**: What message are we exchanging?

This separation makes the system easier to understand, test, and secure.

### 2. Defense in Depth

Multiple security layers provide overlapping protection:

| Attack Scenario | Layer 1: Identity | Layer 2: Transport | Layer 3: AuthZ |
|-----------------|-------------------|-------------------|----------------|
| Impersonation | ✅ SPIFFE prevents | ✅ mTLS verifies cert | ✅ Policy checks ID |
| MITM Attack | ✅ Cert signed by CA | ✅ TLS encryption | ⚪ N/A |
| Privilege Escalation | ⚪ Identity is fixed | ⚪ N/A | ✅ Policy enforces limits |
| Data Tampering | ✅ Cert proves sender | ✅ TLS integrity | ⚪ N/A |

Even if one layer has a misconfiguration, others provide protection.

### 3. Secure by Default

The SDK is designed so you **cannot accidentally** build an insecure agent:

**✅ Enforced at Compile Time:**
- Type system prevents calling agents without identity
- Abstract classes require security components

**✅ Enforced at Runtime:**
- Agent refuses to start without valid SVID
- Requests fail if authorization check denies
- TLS version < 1.2 is rejected

**✅ Enforced by Configuration Validation:**
- Cannot set `peer_verification: none`
- Cannot use `default_action: allow` in production
- Invalid SPIFFE IDs rejected at config load

### 4. Configuration Over Code

Security policies are declared in configuration, not implemented in code:

```yaml
# Developers don't write security code
authorization:
  provider: "opa"
  policy_path: "company/authz"
  default_action: "deny"
```

```rego
# Security team writes policies
package company.authz

allow {
    input.caller_spiffe_id == "spiffe://company.com/agent/orchestrator"
    input.action in ["search", "index"]
}
```

This separation allows security teams to manage policies independently of application code.

### 5. Observable by Default

Every security decision is logged and traceable:

- **Metrics**: Authorization decisions, mTLS handshakes, task durations
- **Traces**: Distributed tracing across agent calls (OpenTelemetry)
- **Logs**: Structured JSON logs with correlation IDs
- **Audit**: Every authorization decision logged with context

---

## Deployment Architecture

### Kubernetes (Recommended)

```
┌─────────────────────────────────────────────────────┐
│                   Kubernetes Cluster                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │             Namespace: agents                 │ │
│  │                                               │ │
│  │  ┌─────────────────────────────────────────┐ │ │
│  │  │         Pod: search-agent              │ │ │
│  │  │                                         │ │ │
│  │  │  ┌──────────┐  ┌──────────────────┐   │ │ │
│  │  │  │  Agent   │  │  OPA Sidecar     │   │ │ │
│  │  │  │Container │  │  (port 8181)     │   │ │ │
│  │  │  └──────────┘  └──────────────────┘   │ │ │
│  │  │       │                                 │ │ │
│  │  │       └────┐                            │ │ │
│  │  │            ▼                            │ │ │
│  │  │  /run/spire/sockets/agent.sock         │ │ │
│  │  │  (volume from host)                    │ │ │
│  │  └─────────────────────────────────────────┘ │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │       DaemonSet: spire-agent                  │ │
│  │  Runs on each node, provides Workload API    │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │     Deployment: spire-server                  │ │
│  │  Issues SVIDs to workloads                    │ │
│  └───────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

### Docker Compose (Development)

```
┌─────────────────────────────────────────────────┐
│              Docker Network: agents             │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌──────────────┐  ┌──────────────┐            │
│  │ spire-server │  │ spire-agent  │            │
│  │              │  │              │            │
│  └──────────────┘  └──────┬───────┘            │
│                           │                    │
│                    ┌──────▼──────┐             │
│                    │ /var/run/   │             │
│                    │ spire/      │             │
│                    │ agent.sock  │             │
│                    └──────┬──────┘             │
│                           │                    │
│  ┌──────────────┐  ┌──────▼──────┐            │
│  │     OPA      │  │ search-agent│            │
│  │              │  │             │            │
│  └──────────────┘  └─────────────┘            │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## What's Next?

Now that you understand the overall architecture, dive into each component:

- [Understanding Agents](/core-concepts/agents/): Learn about SecureAgent, capabilities, and lifecycle
- [Identity & SPIFFE](/core-concepts/identity/): Deep dive into cryptographic identity
- [Authorization & OPA](/core-concepts/authorization/): Master policy-based access control
- [A2A Protocol](/core-concepts/communication/): Understand agent-to-agent communication
- [Security Model](/core-concepts/security-model/): See how all layers work together for zero-trust

{: .important }
The architecture is designed to be **tamper-proof**. Even with full access to the agent code, an attacker cannot bypass identity verification, authorization, or encryption without also compromising SPIRE, OPA, or TLS—which are hardened, production-grade systems.
