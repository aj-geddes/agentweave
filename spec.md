# AgentWeave SDK Specification

**Version**: 1.0.0-DRAFT
**Author**: AgentWeave Team
**Date**: December 2025
**Classification**: Internal Technical Specification

---

## Executive Summary

This document specifies the architecture, design, and implementation guidelines for the **AgentWeave SDK** (`agentweave`)—a Python library for building cross-cloud AI agents with hardened security by default. The SDK is designed so that **the secure path is the only path**—developers cannot accidentally bypass identity verification, mutual authentication, or authorization checks.

The SDK combines:
- **SPIFFE/SPIRE** for cryptographic workload identity
- **A2A Protocol** for standardized agent-to-agent communication
- **OPA (Open Policy Agent)** for fine-grained authorization
- **Tailscale** (optional) for simplified cross-cloud networking

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Research Foundation](#2-research-foundation)
3. [Architecture Overview](#3-architecture-overview)
4. [Core Components](#4-core-components)
5. [Configuration Model](#5-configuration-model)
6. [Security Guarantees](#6-security-guarantees)
7. [Developer Experience](#7-developer-experience)
8. [Deployment Patterns](#8-deployment-patterns)
9. [Testing Strategy](#9-testing-strategy)
10. [Implementation Roadmap](#10-implementation-roadmap)
11. [Dependencies & Licensing](#11-dependencies--licensing)

---

## 1. Problem Statement

### Current State
AI agents proliferating across organizations face critical interoperability and security challenges:

- **Siloed Agents**: Agents built with different frameworks (LangGraph, CrewAI, ADK) cannot communicate
- **Ad-hoc Security**: Each agent implements its own authentication, often poorly
- **Cross-Cloud Complexity**: Connecting agents across AWS, GCP, Azure requires custom networking
- **No Identity Standard**: How does Agent-A prove it's really Agent-A to Agent-B?
- **Authorization Gaps**: Even if identity is proven, what can each agent actually do?

### Target State
A developer building an agent should:

```python
class DataProcessor(SecureAgent):
    @capability("process_data")
    async def process(self, data: dict) -> Result:
        return await self._process(data)

# That's it. Identity, mTLS, authorization handled automatically.
```

### Design Principle
**"Can't fuck it up unless the config is wrong."**

The SDK architecture ensures:
1. No agent can start without verified identity
2. No communication without mutual TLS authentication
3. No request without authorization check
4. All security decisions are SDK-internal, not developer-facing

---

## 2. Research Foundation

### 2.1 Identity Layer: SPIFFE/SPIRE

**Why SPIFFE?**
- CNCF-graduated project, production-proven at Netflix, Pinterest, Uber, Square
- Cryptographic workload identity (X.509 SVIDs, JWT SVIDs)
- Automatic certificate rotation (no manual renewal)
- Federation between trust domains (cross-org, cross-cloud)
- Native integration with Kubernetes, Envoy, OPA

**Key Specifications**:
- SPIFFE ID format: `spiffe://trust-domain/path` (e.g., `spiffe://hvs.solutions/agent/processor/prod`)
- SVIDs issued via Workload API (Unix socket or TCP)
- Trust bundles contain CA certificates for peer verification
- Federation allows cross-domain trust establishment

**Python Library**: `py-spiffe` (HPE maintained)
- PyPI: `spiffe` (v0.2.2+)
- Automatic SVID fetching and renewal
- Works with SPIRE or any SPIFFE Workload API implementation
- `spiffe-tls` for TLS context creation

**Relevant Documentation**:
- SPIFFE Specification: https://spiffe.io/docs/
- py-spiffe: https://github.com/HewlettPackard/py-spiffe
- SPIRE: https://github.com/spiffe/spire

### 2.2 Communication Layer: A2A Protocol

**Why A2A?**
- Open standard (Google → Linux Foundation)
- Framework-agnostic (works with ADK, LangGraph, CrewAI, etc.)
- Task-oriented communication model
- Built-in capability discovery via Agent Cards
- Supports OAuth 2.0, OpenID Connect for auth

**Key Concepts**:
| Concept | Description |
|---------|-------------|
| **Agent Card** | JSON metadata advertising capabilities, endpoints, auth requirements |
| **Task** | Unit of work with lifecycle (submitted → working → completed/failed) |
| **Message** | Single exchange containing parts (text, data, files) |
| **Artifact** | Output produced by task completion |

**Protocol Details**:
- Transport: HTTPS (JSON-RPC 2.0)
- Discovery: `/.well-known/agent.json` endpoint
- Auth: OAuth 2.0, OpenID Connect, API Keys
- Streaming: Server-Sent Events for long-running tasks

**Relevant Documentation**:
- A2A Spec: https://a2a-protocol.org/latest/
- GitHub: https://github.com/a2aproject/A2A

### 2.3 Authorization Layer: OPA

**Why OPA?**
- CNCF-graduated policy engine
- Decouples authorization from application logic
- Native Envoy integration (gRPC External Authorization)
- Documented integration with SPIFFE (identity-aware policies)
- Rego language for expressive policies

**Integration Pattern**:
```
Request → Envoy → OPA Sidecar → Allow/Deny → Application
                      ↑
              SPIFFE SVID for identity
```

**Policy Example** (Rego):
```rego
package hvs.authz

default allow = false

# Allow processors to call search agents
allow {
    input.caller_spiffe_id == "spiffe://hvs.solutions/agent/processor"
    input.callee_spiffe_id == "spiffe://hvs.solutions/agent/search"
    input.method == "search"
}
```

**Relevant Documentation**:
- OPA: https://www.openpolicyagent.org/
- OPA + SPIFFE + Envoy: https://spiffe.io/docs/latest/microservices/envoy-opa/

### 2.4 Networking Layer: Tailscale (Optional)

**Why Tailscale?**
- Zero-config encrypted mesh (WireGuard under hood)
- Cross-cloud connectivity without VPN complexity
- ACL-based access control
- MagicDNS for service discovery
- Kubernetes Operator (GA) for cluster integration

**Use Cases**:
- MVP deployments without full SPIRE setup
- Cross-cloud connectivity with simple ACLs
- Hybrid: Tailscale networking + SPIFFE identity

### 2.5 Existing Agent SDK Patterns

**AWS Bedrock AgentCore SDK**:
- Framework-agnostic (works with Strands, CrewAI, LangGraph)
- MCP support for tools
- A2A protocol support
- Identity via AWS IAM or OAuth

**Google ADK (Agent Development Kit)**:
- Code-first Python framework
- Native A2A support
- Multi-agent hierarchies
- Tool ecosystem with MCP integration
- Deploy to Vertex AI Agent Engine

**Common Patterns Observed**:
1. Declarative agent definition (decorators/classes)
2. Automatic infrastructure handling
3. Task/session-based communication
4. Built-in observability (tracing, metrics)
5. Testing utilities included

---

## 3. Architecture Overview

### 3.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     HVS Secure Agent SDK                        │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐ │
│  │   Agent     │  │   Agent     │  │        Agent            │ │
│  │   Code      │  │   Code      │  │        Code             │ │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘ │
│         │                │                      │               │
│  ┌──────┴────────────────┴──────────────────────┴─────────────┐│
│  │                  BaseAgent (SDK Core)                      ││
│  │  • Lifecycle management                                    ││
│  │  • Configuration loading                                   ││
│  │  • Health checks                                           ││
│  │  • Observability hooks                                     ││
│  └──────┬────────────────┬──────────────────────┬─────────────┘│
│         │                │                      │               │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌───────────┴─────────────┐ │
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
│  │  • Retry with backoff                                      ││
│  └────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │ SPIRE Agent       │ (sidecar or daemon)
                    │ OPA Agent         │ (sidecar)
                    │ Tailscale (opt)   │ (daemon)
                    └───────────────────┘
```

### 3.2 Data Flow: Agent-to-Agent Call

```
Agent-A (Caller)                                     Agent-B (Callee)
      │                                                    │
      ├─► SDK: call_agent("spiffe://...agent-b", task)    │
      │         │                                          │
      │         ├─► Identity Layer: Get SVID              │
      │         │         │                                │
      │         │         └─► SPIRE Agent (Unix socket)   │
      │         │                                          │
      │         ├─► AuthZ Layer: Check outbound policy    │
      │         │         │                                │
      │         │         └─► OPA: Can I call Agent-B?    │
      │         │                                          │
      │         ├─► Transport: Establish mTLS             │
      │         │         │                                │
      │         │         └─► Verify peer SVID            │
      │         │                                          │
      │         └─► Comms: Send A2A Task ─────────────────┼──►
      │                                                    │
      │                                   Transport: Verify caller SVID
      │                                                    │
      │                                   AuthZ: Check inbound policy
      │                                         │
      │                                         └─► OPA: Can Agent-A call me?
      │                                                    │
      │                                   Handler: Execute business logic
      │                                                    │
      │◄──────────────────────────────── Comms: Return A2A Result
      │                                                    │
      └─► SDK: Return Result to caller                    │
```

---

## 4. Core Components

### 4.1 Package Structure

```
agentweave/
├── __init__.py              # Public API exports
├── agent.py                 # BaseAgent, SecureAgent
├── config.py                # AgentConfig, validation
├── identity/
│   ├── __init__.py
│   ├── provider.py          # IdentityProvider interface
│   ├── spiffe.py            # SPIFFEIdentityProvider
│   └── mtls.py              # StaticMTLSProvider (fallback)
├── authz/
│   ├── __init__.py
│   ├── enforcer.py          # PolicyEnforcer interface
│   ├── opa.py               # OPAEnforcer
│   └── policies/            # Default policy templates
├── transport/
│   ├── __init__.py
│   ├── channel.py           # SecureChannel
│   ├── pool.py              # ConnectionPool
│   └── circuit.py           # CircuitBreaker
├── comms/
│   ├── __init__.py
│   ├── a2a/
│   │   ├── client.py        # A2AClient
│   │   ├── server.py        # A2AServer
│   │   ├── card.py          # AgentCard
│   │   └── task.py          # Task, TaskState
│   └── discovery.py         # Agent discovery
├── observability/
│   ├── __init__.py
│   ├── metrics.py           # Prometheus metrics
│   ├── tracing.py           # OpenTelemetry tracing
│   └── audit.py             # Audit logging
├── testing/
│   ├── __init__.py
│   ├── mocks.py             # MockSecureAgent, TestIdentityProvider
│   └── fixtures.py          # pytest fixtures
└── cli/
    ├── __init__.py
    └── main.py              # agentweave CLI
```

### 4.2 Identity Layer (`agentweave.identity`)

**Interface**:
```python
class IdentityProvider(Protocol):
    """Abstract interface for identity providers."""
    
    async def get_svid(self) -> SVID:
        """Get current SVID (X.509 or JWT)."""
        ...
    
    async def get_trust_bundle(self, trust_domain: str) -> TrustBundle:
        """Get trust bundle for verifying peers."""
        ...
    
    def get_spiffe_id(self) -> str:
        """Get this workload's SPIFFE ID."""
        ...
    
    async def watch_updates(self) -> AsyncIterator[SVIDUpdate]:
        """Stream SVID rotation events."""
        ...
```

**SPIFFE Implementation**:
```python
class SPIFFEIdentityProvider(IdentityProvider):
    """SPIFFE Workload API-based identity provider."""
    
    def __init__(self, endpoint: str = None):
        # Auto-detect from SPIFFE_ENDPOINT_SOCKET env var
        self._endpoint = endpoint or os.environ.get(
            "SPIFFE_ENDPOINT_SOCKET",
            "unix:///run/spire/sockets/agent.sock"
        )
        self._client = WorkloadApiClient(self._endpoint)
        self._svid_cache: X509Svid = None
        self._bundle_cache: dict[str, X509Bundle] = {}
    
    async def get_svid(self) -> X509Svid:
        if self._svid_cache is None or self._svid_cache.is_expired():
            self._svid_cache = await self._client.fetch_x509_svid()
        return self._svid_cache
    
    async def get_trust_bundle(self, trust_domain: str) -> X509Bundle:
        if trust_domain not in self._bundle_cache:
            bundles = await self._client.fetch_x509_bundles()
            self._bundle_cache.update(bundles)
        return self._bundle_cache.get(trust_domain)
```

### 4.3 Authorization Layer (`agentweave.authz`)

**Interface**:
```python
class PolicyEnforcer(Protocol):
    """Abstract interface for authorization."""
    
    async def check_outbound(
        self, 
        caller_id: str, 
        callee_id: str, 
        action: str,
        context: dict
    ) -> AuthzDecision:
        """Check if caller can invoke callee."""
        ...
    
    async def check_inbound(
        self,
        caller_id: str,
        action: str,
        context: dict
    ) -> AuthzDecision:
        """Check if incoming request is allowed."""
        ...

@dataclass(frozen=True)
class AuthzDecision:
    allowed: bool
    reason: str
    audit_id: str
```

**OPA Implementation**:
```python
class OPAEnforcer(PolicyEnforcer):
    """OPA-based policy enforcement."""
    
    def __init__(
        self,
        endpoint: str = "http://localhost:8181/v1/data",
        policy_path: str = "hvs/authz"
    ):
        self._endpoint = endpoint
        self._policy_path = policy_path
        self._http = httpx.AsyncClient()
    
    async def check_inbound(
        self,
        caller_id: str,
        action: str,
        context: dict
    ) -> AuthzDecision:
        input_doc = {
            "caller_spiffe_id": caller_id,
            "action": action,
            "context": context,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        response = await self._http.post(
            f"{self._endpoint}/{self._policy_path}",
            json={"input": input_doc}
        )
        result = response.json()
        
        return AuthzDecision(
            allowed=result.get("result", {}).get("allow", False),
            reason=result.get("result", {}).get("reason", ""),
            audit_id=str(uuid.uuid4())
        )
```

### 4.4 Transport Layer (`agentweave.transport`)

**Secure Channel** (mTLS enforced):
```python
class SecureChannel:
    """mTLS-only communication channel."""
    
    def __init__(
        self,
        identity: IdentityProvider,
        peer_spiffe_id: str,
        config: TransportConfig
    ):
        self._identity = identity
        self._peer_id = peer_spiffe_id
        self._config = config
        self._ssl_context: ssl.SSLContext = None
    
    async def _create_ssl_context(self) -> ssl.SSLContext:
        svid = await self._identity.get_svid()
        bundle = await self._identity.get_trust_bundle(
            self._get_trust_domain(self._peer_id)
        )
        
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = ssl.TLSVersion.TLSv1_3  # Enforced
        ctx.verify_mode = ssl.CERT_REQUIRED
        ctx.check_hostname = False  # SPIFFE uses SPIFFE ID, not hostname
        
        # Load our certificate
        ctx.load_cert_chain(
            certfile=svid.cert_chain_path,
            keyfile=svid.private_key_path
        )
        
        # Load trust bundle for peer verification
        ctx.load_verify_locations(cafile=bundle.ca_cert_path)
        
        return ctx
    
    async def verify_peer(self, cert: x509.Certificate) -> bool:
        """Verify peer's SPIFFE ID matches expected."""
        peer_id = self._extract_spiffe_id(cert)
        if peer_id != self._peer_id:
            raise PeerVerificationError(
                f"Expected {self._peer_id}, got {peer_id}"
            )
        return True
```

### 4.5 Communication Layer (`agentweave.comms`)

**A2A Client**:
```python
class A2AClient:
    """Client for A2A protocol communication."""
    
    def __init__(
        self,
        identity: IdentityProvider,
        authz: PolicyEnforcer,
        transport_config: TransportConfig
    ):
        self._identity = identity
        self._authz = authz
        self._transport_config = transport_config
        self._channel_pool: dict[str, SecureChannel] = {}
    
    async def send_task(
        self,
        target_agent: str,  # SPIFFE ID
        task_type: str,
        payload: dict,
        timeout: float = 30.0
    ) -> TaskResult:
        # 1. Check authorization
        my_id = self._identity.get_spiffe_id()
        decision = await self._authz.check_outbound(
            caller_id=my_id,
            callee_id=target_agent,
            action=task_type,
            context={"payload_size": len(json.dumps(payload))}
        )
        if not decision.allowed:
            raise AuthorizationError(
                f"Not authorized to call {target_agent}: {decision.reason}"
            )
        
        # 2. Get or create secure channel
        channel = await self._get_channel(target_agent)
        
        # 3. Build A2A task
        task = Task(
            id=str(uuid.uuid4()),
            type=task_type,
            state=TaskState.SUBMITTED,
            messages=[
                Message(
                    role="user",
                    parts=[DataPart(data=payload)]
                )
            ]
        )
        
        # 4. Send via JSON-RPC over HTTPS
        response = await channel.post(
            "/.well-known/a2a/tasks/send",
            json=task.to_jsonrpc(),
            timeout=timeout
        )
        
        return TaskResult.from_response(response)
```

**Agent Card**:
```python
@dataclass
class AgentCard:
    """A2A Agent Card for capability advertisement."""
    
    name: str
    description: str
    spiffe_id: str
    url: str
    version: str = "1.0.0"
    
    capabilities: list[Capability] = field(default_factory=list)
    auth_schemes: list[AuthScheme] = field(default_factory=list)
    
    def to_json(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "url": self.url,
            "version": self.version,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "authentication": {
                "schemes": [s.to_dict() for s in self.auth_schemes]
            },
            "extensions": {
                "spiffe_id": self.spiffe_id
            }
        }
```

---

## 5. Configuration Model

### 5.1 Configuration Schema

```yaml
# config.yaml - AgentWeave Configuration
agent:
  name: "data-processor"                    # Required, must be unique
  trust_domain: "agentweave.io"             # Required, valid SPIFFE trust domain
  description: "Processes incoming data"
  capabilities:
    - name: "process_data"
      description: "Process structured data"
      input_modes: ["application/json"]
      output_modes: ["application/json"]

identity:
  provider: "spiffe"                        # spiffe | mtls-static
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"
  allowed_trust_domains:
    - "agentweave.io"
    - "partner.example.com"                 # For federation

authorization:
  provider: "opa"                           # opa | allow-all (dev only)
  opa_endpoint: "http://localhost:8181"
  policy_path: "agentweave/authz"
  default_action: "deny"                    # deny | log-only (dev only)
  audit:
    enabled: true
    destination: "file:///var/log/agentweave/audit.log"

transport:
  tls_min_version: "1.3"                    # 1.2 | 1.3 (recommended)
  peer_verification: "strict"               # strict | log-only (never "none")
  connection_pool:
    max_connections: 100
    idle_timeout_seconds: 60
  circuit_breaker:
    failure_threshold: 5
    recovery_timeout_seconds: 30
  retry:
    max_attempts: 3
    backoff_base_seconds: 1.0
    backoff_max_seconds: 30.0

server:
  host: "0.0.0.0"
  port: 8443
  protocol: "a2a"                           # a2a | grpc

observability:
  metrics:
    enabled: true
    port: 9090
  tracing:
    enabled: true
    exporter: "otlp"
    endpoint: "http://collector:4317"
  logging:
    level: "INFO"
    format: "json"
```

### 5.2 Validation Rules (Enforced by SDK)

```python
class AgentConfig(BaseModel):
    """Agent configuration with strict validation."""
    
    model_config = ConfigDict(frozen=True)  # Immutable after creation
    
    agent: AgentSettings
    identity: IdentitySettings
    authorization: AuthorizationSettings
    transport: TransportSettings
    server: ServerSettings
    observability: ObservabilitySettings
    
    @model_validator(mode='after')
    def validate_security(self) -> Self:
        # RULE 1: Default deny in production
        if self._is_production() and self.authorization.default_action != "deny":
            raise ValueError(
                "authorization.default_action must be 'deny' in production"
            )
        
        # RULE 2: No peer verification bypass
        if self.transport.peer_verification == "none":
            raise ValueError(
                "transport.peer_verification cannot be 'none' - "
                "use 'strict' or 'log-only' for debugging"
            )
        
        # RULE 3: TLS 1.2 minimum (1.3 recommended)
        if self.transport.tls_min_version not in ("1.2", "1.3"):
            raise ValueError(
                "transport.tls_min_version must be '1.2' or '1.3'"
            )
        
        # RULE 4: Valid SPIFFE trust domain
        if not self._is_valid_trust_domain(self.agent.trust_domain):
            raise ValueError(
                f"Invalid trust domain: {self.agent.trust_domain}"
            )
        
        return self
    
    @classmethod
    def from_file(cls, path: str) -> "AgentConfig":
        """Load and validate configuration from file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)
    
    @classmethod  
    def from_env(cls) -> "AgentConfig":
        """Load configuration from environment variables."""
        # HVS_AGENT_NAME, HVS_TRUST_DOMAIN, etc.
        ...
```

---

## 6. Security Guarantees

### 6.1 Identity Guarantees

| Guarantee | Mechanism | Enforcement |
|-----------|-----------|-------------|
| Every agent has cryptographic identity | SPIFFE SVID | SDK refuses to start without valid SVID |
| Identity is verified on every connection | mTLS peer verification | Transport layer rejects unverified peers |
| Credentials rotate automatically | SPIRE agent handles rotation | SDK subscribes to SVID updates |
| No hardcoded secrets | SVID fetched at runtime | Config validation rejects static certs |

### 6.2 Communication Guarantees

| Guarantee | Mechanism | Enforcement |
|-----------|-----------|-------------|
| All traffic encrypted | TLS 1.3 | SDK refuses TLS < 1.2 |
| Mutual authentication | mTLS with SVID | Cannot send without peer verification |
| No downgrade attacks | TLS version pinning | Compile-time minimum |
| Tamper detection | TLS integrity | Built into protocol |

### 6.3 Authorization Guarantees

| Guarantee | Mechanism | Enforcement |
|-----------|-----------|-------------|
| Default deny | OPA policy | SDK checks before handler runs |
| Audit trail | Every decision logged | Cannot disable in production |
| Policy-as-code | Rego policies | Version controlled, reviewed |
| No bypass | SDK intercepts all calls | Handlers never see unauthorized requests |

### 6.4 What CAN Go Wrong (Config Errors)

These are the only ways security can be compromised:

1. **Misconfigured SPIRE entries**: Agent registered with wrong selectors
2. **Overly permissive OPA policies**: `allow = true` without conditions
3. **Wrong trust domain federation**: Trusting a malicious domain
4. **Weak network isolation**: SPIRE agent socket accessible to other pods

**Mitigation**: Policy review process, CI/CD validation, security scanning.

---

## 7. Developer Experience

### 7.1 Agent Definition (Declarative)

```python
from agentweave import SecureAgent, capability, requires_peer
from agentweave.types import TaskResult

class DataSearchAgent(SecureAgent):
    """Agent that searches data stores."""

    @capability("search")
    @requires_peer("spiffe://agentweave.io/agent/*")  # Any AgentWeave agent
    async def search(self, query: str, filters: dict = None) -> TaskResult:
        """
        Search for data matching query.
        
        The SDK has already:
        1. Verified caller's SPIFFE ID
        2. Checked OPA policy allows this call
        3. Logged the request for audit
        
        Developer just implements business logic.
        """
        results = await self._database.search(query, filters)
        return TaskResult(
            status="completed",
            artifacts=[{"type": "search_results", "data": results}]
        )
    
    @capability("index")
    @requires_peer("spiffe://agentweave.io/agent/orchestrator")  # Only orchestrator
    async def index(self, documents: list[dict]) -> TaskResult:
        """Index new documents. Restricted to orchestrator agent."""
        await self._database.bulk_index(documents)
        return TaskResult(status="completed")
```

### 7.2 Agent-to-Agent Calls (Type-Safe)

```python
class OrchestratorAgent(SecureAgent):
    """Coordinates other agents."""
    
    @capability("process_request")
    async def process(self, request: dict) -> TaskResult:
        # Call search agent - SDK handles all security
        search_result = await self.call_agent(
            target="spiffe://agentweave.io/agent/search",
            task_type="search",
            payload={"query": request["query"]}
        )

        # Call processor agent
        processed = await self.call_agent(
            target="spiffe://agentweave.io/agent/processor",
            task_type="process",
            payload={"data": search_result.artifacts[0]["data"]}
        )

        return processed
```

### 7.3 Application Startup

```python
# main.py
from agentweave import SecureAgent
from my_agents import DataSearchAgent

if __name__ == "__main__":
    # Load config, initialize identity, start server
    agent = DataSearchAgent.from_config("config.yaml")

    # Blocks and serves requests
    # Graceful shutdown on SIGTERM
    agent.run()
```

### 7.4 CLI Tools

```bash
# Validate configuration
agentweave validate config.yaml

# Generate agent card
agentweave card generate config.yaml > agent-card.json

# Test connectivity to another agent
agentweave ping spiffe://agentweave.io/agent/search

# Check OPA policy for a call
agentweave authz check \
  --caller spiffe://agentweave.io/agent/orchestrator \
  --callee spiffe://agentweave.io/agent/search \
  --action search
```

---

## 8. Deployment Patterns

### 8.1 Kubernetes (Primary)

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: data-search-agent
spec:
  template:
    spec:
      containers:
        # Application container
        - name: agent
          image: hvs/data-search-agent:1.0.0
          ports:
            - containerPort: 8443
          env:
            - name: SPIFFE_ENDPOINT_SOCKET
              value: "unix:///run/spire/sockets/agent.sock"
          volumeMounts:
            - name: spire-socket
              mountPath: /run/spire/sockets
              readOnly: true
            - name: config
              mountPath: /etc/agentweave
        
        # OPA sidecar
        - name: opa
          image: openpolicyagent/opa:latest-envoy
          args:
            - "run"
            - "--server"
            - "--config-file=/policies/config.yaml"
          ports:
            - containerPort: 8181
            - containerPort: 9191  # Envoy ext-authz
          volumeMounts:
            - name: opa-policies
              mountPath: /policies
      
      volumes:
        - name: spire-socket
          hostPath:
            path: /run/spire/sockets
            type: Directory
        - name: config
          configMap:
            name: data-search-agent-config
        - name: opa-policies
          configMap:
            name: opa-policies

---
# SPIRE registration entry
# spire-server entry create \
#   -spiffeID spiffe://agentweave.io/agent/search \
#   -parentID spiffe://agentweave.io/k8s-node \
#   -selector k8s:ns:agentweave \
#   -selector k8s:sa:data-search-agent
```

### 8.2 Docker Compose (Development)

```yaml
# docker-compose.yaml
version: '3.8'

services:
  spire-server:
    image: ghcr.io/spiffe/spire-server:1.9.0
    volumes:
      - ./spire/server:/opt/spire/conf
      - spire-data:/opt/spire/data
    command: ["-config", "/opt/spire/conf/server.conf"]
  
  spire-agent:
    image: ghcr.io/spiffe/spire-agent:1.9.0
    depends_on:
      - spire-server
    volumes:
      - ./spire/agent:/opt/spire/conf
      - /var/run/spire:/var/run/spire
    command: ["-config", "/opt/spire/conf/agent.conf"]
  
  opa:
    image: openpolicyagent/opa:latest
    volumes:
      - ./policies:/policies
    command: ["run", "--server", "/policies"]
  
  search-agent:
    build: ./agents/search
    depends_on:
      - spire-agent
      - opa
    environment:
      - SPIFFE_ENDPOINT_SOCKET=unix:///var/run/spire/agent.sock
      - AGENTWEAVE_OPA_ENDPOINT=http://opa:8181
    volumes:
      - /var/run/spire:/var/run/spire:ro
      - ./config/search-agent.yaml:/etc/agentweave/config.yaml:ro

volumes:
  spire-data:
```

### 8.3 Cross-Cloud with Tailscale

```yaml
# For agents that need to communicate across clouds
# Tailscale provides the network layer, SPIFFE still handles identity

agent:
  name: "cross-cloud-processor"
  trust_domain: "agentweave.io"

identity:
  provider: "spiffe"
  # SPIRE federation configured for cross-cloud trust domains
  allowed_trust_domains:
    - "agentweave.io"           # Primary (GCP)
    - "agentweave-aws.io"       # AWS region
    - "agentweave-azure.io"     # Azure region

transport:
  # Tailscale handles network connectivity
  # But we still do mTLS with SPIFFE on top
  peer_verification: "strict"
```

---

## 9. Testing Strategy

### 9.1 Unit Testing

```python
import pytest
from agentweave.testing import MockIdentityProvider, MockPolicyEnforcer

@pytest.fixture
def mock_identity():
    return MockIdentityProvider(
        spiffe_id="spiffe://test.local/agent/test"
    )

@pytest.fixture
def mock_authz():
    return MockPolicyEnforcer(default_allow=True)

async def test_search_capability(mock_identity, mock_authz):
    agent = DataSearchAgent(
        identity=mock_identity,
        authz=mock_authz
    )
    
    result = await agent.search(query="test")
    
    assert result.status == "completed"
    assert len(result.artifacts) > 0
```

### 9.2 Integration Testing

```python
from agentweave.testing import TestCluster

@pytest.fixture
async def test_cluster():
    """Spin up local SPIRE + OPA for integration tests."""
    async with TestCluster() as cluster:
        yield cluster

async def test_agent_to_agent_call(test_cluster):
    # Register both agents
    search_agent = await test_cluster.deploy_agent(DataSearchAgent)
    orchestrator = await test_cluster.deploy_agent(OrchestratorAgent)
    
    # Orchestrator calls search
    result = await orchestrator.call_agent(
        target=search_agent.spiffe_id,
        task_type="search",
        payload={"query": "test"}
    )
    
    assert result.status == "completed"
```

### 9.3 Policy Testing

```python
from agentweave.testing import PolicySimulator

def test_opa_policy():
    simulator = PolicySimulator("policies/authz.rego")
    
    # Should allow orchestrator to call search
    assert simulator.check(
        caller="spiffe://agentweave.io/agent/orchestrator",
        callee="spiffe://agentweave.io/agent/search",
        action="search"
    ).allowed

    # Should deny unknown agent
    assert not simulator.check(
        caller="spiffe://evil.com/agent/attacker",
        callee="spiffe://agentweave.io/agent/search",
        action="search"
    ).allowed
```

---

## 10. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-4)

**Week 1-2: Core Identity**
- [ ] `SPIFFEIdentityProvider` implementation
- [ ] SVID caching and rotation
- [ ] Trust bundle management
- [ ] Integration tests with SPIRE

**Week 3-4: Transport Layer**
- [ ] `SecureChannel` with mTLS
- [ ] Connection pooling
- [ ] Peer verification
- [ ] Circuit breaker

**Deliverable**: Agents can establish mTLS connections with SPIFFE identity.

### Phase 2: Authorization (Weeks 5-6)

**Week 5: OPA Integration**
- [ ] `OPAEnforcer` implementation
- [ ] Policy loading and caching
- [ ] Audit logging

**Week 6: Policy Framework**
- [ ] Default policy templates
- [ ] Policy testing utilities
- [ ] CLI for policy validation

**Deliverable**: All calls are authorized via OPA.

### Phase 3: A2A Protocol (Weeks 7-8)

**Week 7: A2A Core**
- [ ] Agent Card generation
- [ ] Task lifecycle management
- [ ] A2A client implementation

**Week 8: A2A Server**
- [ ] A2A server (FastAPI-based)
- [ ] Discovery endpoint
- [ ] Multi-agent testing

**Deliverable**: Agents communicate via A2A protocol.

### Phase 4: Developer Experience (Weeks 9-10)

**Week 9: Decorators & Base Classes**
- [ ] `@capability` decorator
- [ ] `@requires_peer` decorator
- [ ] `SecureAgent` base class
- [ ] Configuration loading

**Week 10: CLI & Docs**
- [ ] `hvs-agent` CLI
- [ ] Documentation site
- [ ] Example agents
- [ ] Tutorial

**Deliverable**: Complete SDK ready for beta.

### Phase 5: Production Hardening (Weeks 11-12)

- [ ] Performance optimization
- [ ] Load testing
- [ ] Security audit
- [ ] Helm chart for K8s deployment
- [ ] GitHub Actions for CI/CD

---

## 11. Dependencies & Licensing

### 11.1 Core Dependencies

| Package | Version | Purpose | License |
|---------|---------|---------|---------|
| `spiffe` | ≥0.2.2 | SPIFFE Workload API | Apache 2.0 |
| `spiffe-tls` | ≥0.1.0 | TLS utilities | Apache 2.0 |
| `httpx` | ≥0.27 | HTTP client | BSD-3 |
| `pydantic` | ≥2.0 | Config validation | MIT |
| `fastapi` | ≥0.110 | A2A server | MIT |
| `uvicorn` | ≥0.29 | ASGI server | BSD-3 |
| `opentelemetry-*` | ≥1.24 | Observability | Apache 2.0 |
| `prometheus-client` | ≥0.20 | Metrics | Apache 2.0 |

### 11.2 Infrastructure Dependencies

| Component | Version | Purpose |
|-----------|---------|---------|
| SPIRE Server | ≥1.9.0 | Identity provider |
| SPIRE Agent | ≥1.9.0 | Workload API |
| OPA | ≥0.62 | Policy engine |
| Tailscale | Latest | Optional networking |

### 11.3 SDK License

The AgentWeave SDK will be licensed under **Apache 2.0**, allowing:
- Commercial use
- Modification
- Distribution
- Patent use

With requirements for:
- License and copyright notice
- State changes documentation

---

## Appendix A: SPIFFE ID Naming Convention

```
spiffe://agentweave.io/agent/<agent-name>/<environment>

Examples:
- spiffe://agentweave.io/agent/orchestrator/prod
- spiffe://agentweave.io/agent/search/staging
- spiffe://agentweave.io/agent/processor/dev

For federated partners:
- spiffe://partner.example.com/agent/their-agent/prod
```

## Appendix B: Default OPA Policy Template

```rego
package agentweave.authz

import rego.v1

default allow := false

# Allow agents within same trust domain to communicate
allow if {
    same_trust_domain
    valid_action
}

# Allow federated domains (explicit list)
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
    input.action in data.allowed_actions[input.callee_spiffe_id]
}
```

## Appendix C: Glossary

| Term | Definition |
|------|------------|
| **SPIFFE** | Secure Production Identity Framework for Everyone |
| **SPIRE** | SPIFFE Runtime Environment |
| **SVID** | SPIFFE Verifiable Identity Document |
| **A2A** | Agent-to-Agent Protocol |
| **OPA** | Open Policy Agent |
| **mTLS** | Mutual TLS (both sides verify identity) |
| **Trust Domain** | Namespace for SPIFFE identities |
| **Agent Card** | A2A capability advertisement |

---

*Document Version: 1.0.0-DRAFT*
*Last Updated: December 2025*
*Author: AgentWeave Team*
