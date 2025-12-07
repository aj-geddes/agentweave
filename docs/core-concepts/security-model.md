---
layout: page
title: Security Model
description: Zero-trust security architecture and defense-in-depth in AgentWeave
permalink: /core-concepts/security-model/
parent: Core Concepts
nav_order: 6
---

# Security Model

AgentWeave's security model is built on **zero-trust principles** and **defense in depth**. This document explains the philosophy, guarantees, and protections built into the SDK.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Zero-Trust Architecture Explained

**Zero-trust** means **never trust, always verify**. Every request is authenticated, authorized, and audited—regardless of where it comes from.

### Traditional Perimeter Security

Traditional security assumes a **trusted internal network**:

```
┌────────────────────────────────────────┐
│        Internal Network (Trusted)      │
│                                        │
│  Agent A ─────► Agent B                │
│    │                                   │
│    └─────► Agent C                     │
│                                        │
│  No authentication, no authorization   │
│  "Inside the firewall = trusted"       │
└────────────────────────────────────────┘
              │
         Firewall
              │
      External Threats
```

**Problems:**
- **Lateral movement**: If one agent is compromised, attacker can access everything inside
- **Insider threats**: Malicious insiders have unrestricted access
- **Misconfiguration**: One firewall rule mistake exposes everything
- **Cloud-native doesn't fit**: "Inside the firewall" is meaningless in multi-cloud

### Zero-Trust Model

AgentWeave assumes **no implicit trust**:

```
┌──────────────────────────────────────────────┐
│           Every Connection Verified          │
│                                              │
│  Agent A ─────mTLS + authz────► Agent B      │
│    │      (always verified)                  │
│    └───────mTLS + authz────► Agent C         │
│                                              │
│  Every request:                              │
│  1. Identity verified (SPIFFE)               │
│  2. Connection encrypted (mTLS)              │
│  3. Authorization checked (OPA)              │
│  4. Decision audited                         │
└──────────────────────────────────────────────┘
```

**Benefits:**
- **No lateral movement**: Each connection is independently verified
- **Insider threat mitigation**: Even internal agents must be authorized
- **Cloud-native**: Works across networks, clouds, and trust boundaries
- **Audit trail**: Every access is logged

{: .important }
**In AgentWeave, there is no "trusted network."** Every single agent-to-agent call is verified, encrypted, and authorized—even if both agents are in the same Kubernetes pod.

---

## "The Secure Path is the Only Path" Philosophy

AgentWeave is designed so **you cannot accidentally build an insecure agent**.

### Design Principle

Traditional frameworks make security **optional**:

```python
# ❌ Traditional framework - security is opt-in
class MyAgent:
    def __init__(self, use_mtls=False, check_auth=False):
        self.use_mtls = use_mtls        # Optional
        self.check_auth = check_auth    # Optional

    def call_agent(self, target, action):
        if self.use_mtls:
            # Use mTLS (if developer remembered)
            ...
        else:
            # Plain HTTP (insecure)
            ...

        if self.check_auth:
            # Check authorization (if developer remembered)
            ...

        # Do the call
        ...
```

This is dangerous because:
- Developers can forget to enable security
- Security can be disabled "temporarily" and never re-enabled
- Misconfiguration can silently bypass security

### AgentWeave Approach

AgentWeave makes security **mandatory and automatic**:

```python
# ✅ AgentWeave - security is always enforced
class MyAgent(SecureAgent):
    @capability("process")
    async def process(self, data: dict) -> TaskResult:
        # SDK automatically:
        # - Verified caller identity (SPIFFE)
        # - Established mTLS connection
        # - Checked authorization (OPA)
        # - Logged the request

        # You just write business logic
        result = await process_data(data)
        return TaskResult(status="completed", artifacts=[result])
```

**How it works:**
- No configuration option to disable mTLS
- No way to bypass identity verification
- No code path that skips authorization
- Config validation rejects insecure settings

{: .note }
**The SDK is designed to make insecure agents impossible.** Even with full access to the code, you cannot bypass security without also breaking the agent entirely.

---

## Defense in Depth Layers

AgentWeave implements **four overlapping security layers**. Even if one layer fails, others provide protection.

### Layer 1: Identity Verification (SPIFFE)

**Purpose**: Prove **who** is making the request

**Mechanism**: X.509 certificates (SVIDs) issued by SPIRE

**Guarantees:**
- Every agent has a cryptographic identity
- Identity cannot be forged without the private key
- SVIDs are short-lived (1 hour) and automatically rotated
- No shared secrets to leak

**What it prevents:**
- **Impersonation**: Attacker cannot pretend to be another agent
- **Replay attacks**: Expired SVIDs are rejected
- **Credential theft**: SVIDs are in-memory, not in environment variables

**Example attack scenario:**

```
Attacker tries to impersonate Agent A:

1. Attacker sends request claiming to be Agent A
2. Agent B requests mTLS client certificate
3. Attacker cannot provide valid certificate
   (requires Agent A's private key, which is in SPIRE)
4. Connection rejected
```

### Layer 2: Transport Security (mTLS)

**Purpose**: Encrypt data and authenticate both parties

**Mechanism**: Mutual TLS with SPIFFE SVIDs

**Guarantees:**
- All traffic encrypted with TLS 1.3 (or 1.2 minimum)
- Both client and server verify each other's identity
- Perfect forward secrecy (even if key is compromised later, past traffic stays encrypted)
- SPIFFE ID is verified against expected value

**What it prevents:**
- **Eavesdropping**: Attacker cannot read traffic
- **Man-in-the-middle**: Attacker cannot intercept or modify traffic
- **Downgrade attacks**: TLS version is pinned

**Example attack scenario:**

```
Attacker intercepts network traffic:

1. Agent A sends encrypted request to Agent B
2. Attacker captures the traffic
3. Traffic is encrypted with TLS 1.3
4. Without Agent A's or Agent B's private key, attacker cannot decrypt
5. Even if attacker replays the traffic, timestamp prevents replay
```

### Layer 3: Authorization (OPA)

**Purpose**: Determine **what** the verified caller can do

**Mechanism**: Policy-based access control with OPA

**Guarantees:**
- Default deny (nothing is allowed unless explicitly permitted)
- Policies are evaluated before handler executes
- Every decision is logged
- Policies are external to application code

**What it prevents:**
- **Privilege escalation**: Even legitimate agents can only do what's allowed
- **Lateral movement**: Compromised agent cannot access other agents
- **Unauthorized actions**: Policies enforce least-privilege

**Example attack scenario:**

```
Attacker compromises Agent A and tries to access Agent B:

1. Attacker has valid credentials for Agent A
2. Attacker uses Agent A's identity to call Agent B
3. Agent B verifies Agent A's identity (✓ passes)
4. Agent B checks OPA policy: "Can Agent A call this capability?"
5. Policy says "No" (Agent A should never call Agent B)
6. Request rejected, attack logged
```

### Layer 4: Audit Logging

**Purpose**: Detect and investigate security incidents

**Mechanism**: Structured logging of all security decisions

**Guarantees:**
- Every authorization decision is logged
- Logs are tamper-evident (signed or sent to external SIEM)
- Correlation IDs connect related requests
- Logs include caller, action, decision, and context

**What it prevents:**
- **Undetected breaches**: Anomalous access patterns are visible
- **Forensics gaps**: Full audit trail for investigation
- **Insider threats**: All actions are logged

**Example attack scenario:**

```
Attacker gains access and tries to stay hidden:

1. Attacker successfully compromises Agent A
2. Attacker makes authorized calls (passes all security checks)
3. But every call is logged:
   - Agent A calling Agent B at 2 AM (unusual time)
   - Agent A suddenly accessing new agents (unusual pattern)
4. Security team sees anomalous logs
5. Incident response team investigates
6. Attacker's actions are fully visible in audit trail
```

---

## How Layers Work Together

Each layer complements the others:

| Attack Vector | Layer 1 (Identity) | Layer 2 (mTLS) | Layer 3 (AuthZ) | Layer 4 (Audit) |
|---------------|-------------------|----------------|-----------------|-----------------|
| **Fake Agent** | ✅ Blocks (no SVID) | ✅ Blocks (no cert) | ⚪ N/A | ✅ Logs attempt |
| **MITM Attack** | ✅ Detects (wrong ID) | ✅ Blocks (cert mismatch) | ⚪ N/A | ✅ Logs attempt |
| **Compromised Agent** | ⚪ Bypassed (valid ID) | ⚪ Bypassed (valid cert) | ✅ Blocks (policy denies) | ✅ Logs activity |
| **Privilege Escalation** | ⚪ N/A | ⚪ N/A | ✅ Blocks (policy limits) | ✅ Logs attempt |
| **Data Exfiltration** | ⚪ N/A | ✅ Encrypts data | ✅ Limits access | ✅ Logs transfers |
| **Insider Threat** | ✅ Identifies user | ⚪ N/A | ✅ Limits actions | ✅ Full audit trail |

**Key insight**: Layered security means **multiple failures must occur** for an attack to succeed:

```
Attacker must bypass ALL of:
1. SPIFFE identity verification
2. mTLS encryption and authentication
3. OPA authorization policies
4. Audit logging detection

If ANY layer holds, the attack fails or is detected.
```

---

## Security Guarantees

### What AgentWeave Guarantees

AgentWeave **guarantees** these security properties:

1. **Identity Guarantee**
   - Every agent has a cryptographic identity (SPIFFE ID)
   - Identity is verified on every connection
   - SVIDs rotate automatically (no manual renewal)

2. **Confidentiality Guarantee**
   - All agent communication is encrypted (TLS 1.2 minimum, 1.3 recommended)
   - No plaintext credentials (SVIDs are cryptographic proof)

3. **Integrity Guarantee**
   - TLS prevents tampering with messages in transit
   - Certificate signatures prevent forged identities

4. **Authorization Guarantee**
   - Every request is authorized before execution
   - Default deny (nothing allowed unless policy permits)
   - Policies are enforced by SDK, not application code

5. **Auditability Guarantee**
   - Every security decision is logged
   - Logs include caller, action, decision, and timestamp
   - Audit IDs correlate requests across agents

### What AgentWeave Does NOT Guarantee

AgentWeave **cannot** protect against:

1. **Compromised Infrastructure**
   - If SPIRE Server is compromised, attacker can issue arbitrary SVIDs
   - If OPA is compromised, attacker can change policies
   - Mitigation: Harden SPIRE/OPA with access controls, monitoring

2. **Application Logic Bugs**
   - If your capability handler has a bug (e.g., SQL injection), SDK cannot prevent it
   - Mitigation: Input validation, secure coding practices

3. **Social Engineering**
   - If an attacker tricks an operator into changing policies, SDK will enforce the malicious policy
   - Mitigation: Policy review process, change control

4. **Side-Channel Attacks**
   - Timing attacks, power analysis, etc.
   - Mitigation: Use constant-time crypto operations, harden infrastructure

5. **Supply Chain Attacks**
   - If a dependency is malicious, SDK cannot detect it
   - Mitigation: Dependency scanning, software bill of materials (SBOM)

{: .important }
**AgentWeave secures agent-to-agent communication.** You must still harden infrastructure, validate inputs, and follow secure development practices.

---

## Security Configuration Validation

The SDK validates security configuration at startup to prevent misconfigurations.

### Validation Rules

**Rule 1: No Security Bypasses**

```yaml
# ❌ This is rejected
transport:
  peer_verification: "none"  # Not allowed
```

```python
ValidationError: transport.peer_verification cannot be 'none'.
Use 'strict' for production or 'log-only' for debugging.
```

**Rule 2: Default Deny in Production**

```yaml
# ❌ This is rejected in production
authorization:
  default_action: "allow"  # Only allowed in development
```

```python
ValidationError: authorization.default_action must be 'deny' in production.
Set environment to 'development' to use 'allow'.
```

**Rule 3: TLS Version Minimum**

```yaml
# ❌ This is rejected
transport:
  tls_min_version: "1.0"  # Too old
```

```python
ValidationError: transport.tls_min_version must be '1.2' or '1.3'.
TLS 1.0 and 1.1 are deprecated and insecure.
```

**Rule 4: Valid SPIFFE Trust Domain**

```yaml
# ❌ This is rejected
agent:
  trust_domain: "not-a-valid-domain!"
```

```python
ValidationError: Invalid trust domain: 'not-a-valid-domain!'
Trust domain must be a valid DNS name (e.g., 'company.com').
```

### Environment Detection

AgentWeave detects the environment and adjusts validation:

**Production** (default):
- `default_action: "deny"` required
- `peer_verification: "strict"` required
- Audit logging required

**Development** (opt-in):
- `default_action: "allow"` allowed (with warning)
- `peer_verification: "log-only"` allowed (with warning)
- Audit logging optional

```yaml
# Explicitly set environment
agent:
  environment: "development"  # or "production"
```

```bash
# Or via environment variable
export AGENTWEAVE_ENVIRONMENT="development"
```

{: .danger }
**Never run production agents with `environment: "development"`.** Development mode disables critical security checks.

---

## Production vs Development Modes

### Production Mode (Default)

**Security:**
- Full enforcement of all security layers
- Default deny authorization
- Strict peer verification
- Audit logging required
- TLS 1.3 recommended

**Use when:**
- Deploying to production environments
- Handling real user data
- Cross-organization communication

**Configuration:**

```yaml
agent:
  environment: "production"  # Default if not specified

identity:
  provider: "spiffe"

authorization:
  provider: "opa"
  default_action: "deny"

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"

observability:
  audit:
    enabled: true
    destination: "syslog://logs.company.com:514"
```

### Development Mode

**Security:**
- Warnings instead of errors for some violations
- `default_action: "allow"` permitted (with warning)
- `peer_verification: "log-only"` permitted (logs but doesn't block)
- Audit logging optional

**Use when:**
- Local development and testing
- Prototyping new agents
- Integration testing

**Configuration:**

```yaml
agent:
  environment: "development"  # Explicitly enable dev mode

identity:
  provider: "spiffe"  # Still required (use local SPIRE)

authorization:
  provider: "opa"
  default_action: "allow"  # ⚠️ WARNING: Development only

transport:
  tls_min_version: "1.2"
  peer_verification: "log-only"  # ⚠️ WARNING: Logs but doesn't block

observability:
  logging:
    level: "DEBUG"  # More verbose logging
```

{: .warning }
**Development mode is for local testing only.** Do not deploy to shared environments (staging, production) with development mode enabled.

---

## What AgentWeave Protects Against

### Attack Scenarios

**Scenario 1: Impersonation Attack**

```
Attacker creates a fake agent claiming to be Agent A:

1. Attacker deploys rogue pod in Kubernetes
2. Rogue pod tries to call Agent B, claiming to be Agent A
3. Agent B requests mTLS client certificate
4. Rogue pod cannot provide valid SVID
   (SPIRE won't issue SVID without valid registration)
5. mTLS handshake fails
6. Connection rejected

Result: ✅ Attack blocked at Layer 1 (Identity)
```

**Scenario 2: Man-in-the-Middle Attack**

```
Attacker intercepts traffic between Agent A and Agent B:

1. Agent A initiates mTLS connection to Agent B
2. Attacker intercepts and tries to proxy the connection
3. Agent B verifies Agent A's SPIFFE ID from certificate
4. Attacker cannot forge certificate (no SPIRE CA private key)
5. Certificate verification fails
6. Connection rejected

Result: ✅ Attack blocked at Layer 2 (mTLS)
```

**Scenario 3: Compromised Agent Lateral Movement**

```
Attacker compromises Agent A and tries to access Agent B:

1. Attacker gains control of Agent A (valid SVID)
2. Attacker uses Agent A's identity to call Agent B
3. mTLS handshake succeeds (Agent A is legitimate)
4. Agent B checks OPA policy: "Can Agent A call me?"
5. Policy denies (Agent A should never call Agent B)
6. Request rejected
7. Attempt logged to SIEM

Result: ✅ Attack blocked at Layer 3 (Authorization)
```

**Scenario 4: Insider Privilege Escalation**

```
Insider with access to Agent A tries to escalate privileges:

1. Insider deploys modified Agent A with extra capabilities
2. Modified Agent A calls protected Agent C (admin-only)
3. Identity verification succeeds (valid SVID for Agent A)
4. mTLS succeeds (valid certificate)
5. Authorization check: "Can Agent A call Agent C?"
6. Policy denies (Agent A not authorized for Agent C)
7. Request rejected
8. Attempt logged with full context

Result: ✅ Attack blocked at Layer 3 (Authorization)
```

**Scenario 5: Data Exfiltration**

```
Attacker tries to steal data by calling storage agent:

1. Attacker compromises low-privilege Agent D
2. Agent D calls Storage Agent to retrieve all data
3. Identity verification succeeds (Agent D is legitimate)
4. mTLS succeeds
5. Authorization check: "Can Agent D access all data?"
6. Policy allows limited read-only access
7. Agent D gets public data only (not sensitive data)
8. Access logged with data classification level

Result: ✅ Attack limited at Layer 3 (Authorization), detected at Layer 4 (Audit)
```

---

## Threat Model Summary

### In Scope (Protected)

AgentWeave protects against:

- **Network-based attacks**: MITM, eavesdropping, replay
- **Identity attacks**: Impersonation, credential theft
- **Access control violations**: Unauthorized agent calls, privilege escalation
- **Lateral movement**: Compromised agent accessing other agents
- **Insider threats**: Malicious or compromised internal agents

### Out of Scope (Requires Additional Hardening)

AgentWeave does **not** protect against:

- **Infrastructure compromise**: Kubernetes cluster admin, SPIRE server compromise
- **Application vulnerabilities**: SQL injection, XSS, etc. in your code
- **Supply chain attacks**: Malicious dependencies
- **Physical security**: Hardware tampering
- **Denial of Service**: Network flooding (use rate limiting, Kubernetes resource limits)

### Shared Responsibility Model

| Component | AgentWeave Responsibility | Your Responsibility |
|-----------|--------------------------|---------------------|
| **Identity** | Fetch and rotate SVIDs | Configure SPIRE registrations |
| **Transport** | Enforce mTLS, verify peers | Deploy agents in secure networks |
| **Authorization** | Enforce policies | Write correct policies |
| **Audit** | Log all decisions | Monitor and respond to logs |
| **Application Logic** | ⚪ Not covered | Validate inputs, secure code |
| **Infrastructure** | ⚪ Not covered | Harden Kubernetes, SPIRE, OPA |

---

## Security Best Practices

### 1. Principle of Least Privilege

Grant only the minimum permissions needed:

```rego
# ✅ Good: Specific permissions
allow {
    input.caller_spiffe_id == "spiffe://company.com/agent/orchestrator"
    input.callee_spiffe_id == "spiffe://company.com/agent/search"
    input.action == "search"
}

# ❌ Bad: Overly permissive
allow {
    startswith(input.caller_spiffe_id, "spiffe://company.com/")
}
```

### 2. Review Policies Regularly

Treat policies like code:
- Version control in Git
- Code review before merging
- CI/CD tests for policies
- Regular audits of active policies

### 3. Monitor Audit Logs

Set up alerts for anomalous behavior:
- Authorization failures (potential attack)
- Unusual access patterns (compromised agent)
- Access outside business hours
- High-volume requests (DoS or data exfiltration)

### 4. Rotate Trust Material

Even though SVIDs auto-rotate, rotate trust material periodically:
- SPIRE CA certificate: Annually
- OPA policies: On every release
- Agent configurations: On security updates

### 5. Harden Infrastructure

Secure the underlying infrastructure:
- SPIRE Server: Restrict access, enable encryption at rest
- OPA: Restrict policy upload, require authentication
- Kubernetes: Network policies, pod security standards
- Secrets: Use external secret managers (Vault, AWS Secrets Manager)

---

## What's Next?

You now understand AgentWeave's security model. To see it in action:

- [System Architecture](/agentweave/core-concepts/architecture/): See how security layers fit into the overall architecture
- [Identity & SPIFFE](/agentweave/core-concepts/identity/): Deep dive into Layer 1 (Identity)
- [Authorization & OPA](/agentweave/core-concepts/authorization/): Deep dive into Layer 3 (Authorization)
- [A2A Protocol](/agentweave/core-concepts/communication/): How security is enforced during agent calls

{: .note }
Security is a journey, not a destination. AgentWeave provides a strong foundation, but security requires ongoing vigilance, monitoring, and updates. Stay informed about security advisories and keep your dependencies updated.
