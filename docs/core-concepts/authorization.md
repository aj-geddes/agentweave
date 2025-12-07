---
layout: page
title: Authorization & OPA
description: Policy-based authorization with Open Policy Agent in AgentWeave
permalink: /core-concepts/authorization/
parent: Core Concepts
nav_order: 4
---

# Authorization & OPA

Authorization determines **what** a verified identity is allowed to do. This document explains how AgentWeave uses Open Policy Agent (OPA) for policy-based access control.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Why Policy-Based Authorization?

Identity tells us **who** is making a request. Authorization tells us **what** they can do.

### The Problem with Code-Based Authorization

Traditional authorization is embedded in application code:

```python
# ❌ Hard-coded authorization logic
def search(caller_id: str, query: str):
    # Authorization logic mixed with business logic
    if caller_id == "orchestrator" or caller_id == "admin":
        return perform_search(query)
    else:
        raise PermissionDenied("Not authorized")
```

**Problems:**
- **Coupled**: Authorization logic mixed with business logic
- **Inflexible**: Requires code changes to update policies
- **Error-prone**: Easy to forget checks or implement incorrectly
- **Unauditable**: No central view of who can do what

### Policy-Based Authorization

AgentWeave uses **declarative policies** in OPA:

```python
# ✅ Application code (no authorization logic)
@capability("search")
async def search(self, query: str) -> TaskResult:
    # SDK already checked authorization - just implement business logic
    return perform_search(query)
```

```rego
# ✅ Authorization policy (separate from code)
package agentweave.authz

allow {
    # Orchestrator can search
    input.caller_spiffe_id == "spiffe://company.com/agent/orchestrator"
    input.action == "search"
}

allow {
    # Admin can search
    input.caller_spiffe_id == "spiffe://company.com/admin"
    input.action == "search"
}
```

**Benefits:**
- **Separated**: Policy separated from business logic
- **Flexible**: Update policies without deploying code
- **Consistent**: Same policy engine across all agents
- **Auditable**: Policies version-controlled, reviewed, tested

---

## Open Policy Agent (OPA) Overview

**OPA** is a CNCF-graduated policy engine that evaluates policies written in **Rego**.

### Key Concepts

**Policy**: A set of rules defining what is allowed
**Rego**: The policy language (declarative, logic-based)
**Input**: Data about the request (caller, action, context)
**Output**: Decision (allow/deny) with optional metadata

### How OPA Works

```
┌──────────────────────────────────────────────────┐
│              AgentWeave Agent                    │
├──────────────────────────────────────────────────┤
│                                                  │
│  Incoming request:                               │
│  - Caller: spiffe://company.com/agent/orch       │
│  - Action: search                                │
│  - Context: {...}                                │
│                                                  │
│  ┌────────────────────────────────────────────┐ │
│  │  1. SDK builds authorization input         │ │
│  └─────────────────┬──────────────────────────┘ │
│                    │                             │
│                    ▼                             │
│  ┌────────────────────────────────────────────┐ │
│  │  2. POST to OPA                            │ │
│  │     /v1/data/agentweave/authz              │ │
│  │                                            │ │
│  │     {                                      │ │
│  │       "input": {                           │ │
│  │         "caller_spiffe_id": "...",         │ │
│  │         "action": "search"                 │ │
│  │       }                                    │ │
│  │     }                                      │ │
│  └─────────────────┬──────────────────────────┘ │
└────────────────────┼────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│              OPA Sidecar                       │
├────────────────────────────────────────────────┤
│                                                │
│  ┌──────────────────────────────────────────┐ │
│  │  3. Load policy (Rego)                   │ │
│  └─────────────────┬────────────────────────┘ │
│                    │                           │
│                    ▼                           │
│  ┌──────────────────────────────────────────┐ │
│  │  4. Evaluate policy against input        │ │
│  │                                          │ │
│  │     allow if {                           │ │
│  │       input.caller_spiffe_id == "..."    │ │
│  │       input.action == "search"           │ │
│  │     }                                    │ │
│  └─────────────────┬────────────────────────┘ │
│                    │                           │
│                    ▼                           │
│  ┌──────────────────────────────────────────┐ │
│  │  5. Return decision                      │ │
│  │                                          │ │
│  │     {                                    │ │
│  │       "result": {                        │ │
│  │         "allow": true,                   │ │
│  │         "reason": "Authorized"           │ │
│  │       }                                  │ │
│  │     }                                    │ │
│  └─────────────────┬────────────────────────┘ │
└────────────────────┼────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────┐
│              AgentWeave Agent                  │
├────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────┐ │
│  │  6. If allowed, execute capability       │ │
│  │     If denied, return error              │ │
│  └──────────────────────────────────────────┘ │
└────────────────────────────────────────────────┘
```

---

## Rego Policy Language Basics

Rego is a declarative language designed for expressing policies.

### Basic Syntax

```rego
package agentweave.authz

# Default deny - if no rule allows, deny
default allow := false

# Rule: Allow if condition is true
allow {
    input.caller_spiffe_id == "spiffe://company.com/agent/orchestrator"
    input.action == "search"
}
```

**Key points:**
- `package`: Namespace for the policy
- `default allow := false`: Explicit default deny
- `allow { ... }`: Rule that evaluates to true if all conditions match

### Multiple Rules

Rules with the same name are OR'd together:

```rego
# Allow orchestrator to search
allow {
    input.caller_spiffe_id == "spiffe://company.com/agent/orchestrator"
    input.action == "search"
}

# Also allow admin to search
allow {
    input.caller_spiffe_id == "spiffe://company.com/admin"
    input.action == "search"
}

# Result: allow is true if EITHER rule matches
```

### Pattern Matching

Match patterns instead of exact values:

```rego
# Allow any agent in the company.com trust domain
allow {
    startswith(input.caller_spiffe_id, "spiffe://company.com/agent/")
    input.action == "search"
}

# Allow specific actions
allow {
    input.caller_spiffe_id == "spiffe://company.com/agent/orchestrator"
    input.action in ["search", "index", "delete"]
}
```

### Variables and Iteration

```rego
# Define allowed callers
allowed_callers := [
    "spiffe://company.com/agent/orchestrator",
    "spiffe://company.com/agent/admin"
]

# Allow if caller is in the list
allow {
    input.caller_spiffe_id in allowed_callers
    input.action == "search"
}
```

### Functions

```rego
# Helper function to check trust domain
same_trust_domain(caller, callee) {
    caller_domain := split(caller, "/")[2]
    callee_domain := split(callee, "/")[2]
    caller_domain == callee_domain
}

# Use the function
allow {
    same_trust_domain(input.caller_spiffe_id, input.callee_spiffe_id)
    input.action == "search"
}
```

### Negation

```rego
# Allow unless caller is banned
allow {
    input.action == "search"
    not banned_caller
}

banned_caller {
    input.caller_spiffe_id in ["spiffe://company.com/agent/untrusted"]
}
```

{: .note }
Rego is a logic programming language. If you've used Prolog or Datalog, it will feel familiar. If not, the [OPA documentation](https://www.openpolicyagent.org/docs/latest/policy-language/) has excellent tutorials.

---

## How AgentWeave Integrates with OPA

### The OPAProvider Class

AgentWeave's `OPAProvider` handles all OPA interactions:

```python
from agentweave.authz import OPAProvider

provider = OPAProvider(
    endpoint="http://localhost:8181",
    policy_path="agentweave/authz"
)

# Check if a request is authorized
decision = await provider.check_inbound(
    caller_id="spiffe://company.com/agent/orchestrator",
    action="search",
    context={"query": "test"}
)

if decision.allowed:
    # Execute the request
    print(f"Authorized: {decision.reason}")
else:
    # Reject the request
    print(f"Denied: {decision.reason}")
```

### Authorization Decision

```python
@dataclass(frozen=True)
class AuthzDecision:
    allowed: bool          # True if authorized, False if denied
    reason: str            # Human-readable explanation
    audit_id: str          # Unique ID for audit trail
```

### Inbound vs Outbound Checks

**Inbound**: "Can this caller invoke me?"

```python
# Before executing a capability
decision = await authz.check_inbound(
    caller_id="spiffe://company.com/agent/orchestrator",
    action="search",
    context={"query": "test"}
)
```

**Outbound**: "Can I call this agent?"

```python
# Before calling another agent
decision = await authz.check_outbound(
    caller_id=self.spiffe_id,
    callee_id="spiffe://company.com/agent/search",
    action="search",
    context={"query": "test"}
)
```

{: .important }
Both checks happen automatically in the SDK. You don't need to call these methods manually—the SDK enforces authorization on every request.

---

## Default Policies

AgentWeave provides default policies for common scenarios.

### Allow All (Development Only)

```rego
package agentweave.authz

# WARNING: Development only - never use in production
default allow := true
```

{: .danger }
**Never use `allow := true` in production.** This disables authorization entirely. The SDK will refuse to start with this policy if `environment != "development"`.

### Same Trust Domain

Allow agents within the same trust domain:

```rego
package agentweave.authz

default allow := false

# Allow agents in same trust domain
allow {
    same_trust_domain
}

same_trust_domain {
    caller_domain := split(input.caller_spiffe_id, "/")[2]
    callee_domain := split(input.callee_spiffe_id, "/")[2]
    caller_domain == callee_domain
}
```

### Capability-Based

Allow specific capabilities to specific callers:

```rego
package agentweave.authz

default allow := false

# Define capability permissions
capabilities := {
    "spiffe://company.com/agent/orchestrator": ["search", "index"],
    "spiffe://company.com/agent/admin": ["search", "index", "delete"]
}

# Allow if caller has permission for this action
allow {
    allowed_actions := capabilities[input.caller_spiffe_id]
    input.action in allowed_actions
}
```

### Attribute-Based (ABAC)

Use attributes from context for fine-grained control:

```rego
package agentweave.authz

default allow := false

# Allow search with restrictions based on caller
allow {
    input.action == "search"
    input.caller_spiffe_id == "spiffe://company.com/agent/basic"

    # Basic agent can only search public data
    input.context.data_classification == "public"
}

allow {
    input.action == "search"
    input.caller_spiffe_id == "spiffe://company.com/agent/privileged"

    # Privileged agent can search all data
}
```

---

## Writing Custom Policies

### Step 1: Define Policy File

Create `policies/authz.rego`:

```rego
package agentweave.authz

import rego.v1

default allow := false

# Orchestrator can call search and processor agents
allow {
    input.caller_spiffe_id == "spiffe://company.com/agent/orchestrator"
    input.callee_spiffe_id in [
        "spiffe://company.com/agent/search",
        "spiffe://company.com/agent/processor"
    ]
    input.action in ["search", "process", "index"]
}

# Search agent can call processor agent
allow {
    input.caller_spiffe_id == "spiffe://company.com/agent/search"
    input.callee_spiffe_id == "spiffe://company.com/agent/processor"
    input.action == "process"
}

# Admin can call anything
allow {
    startswith(input.caller_spiffe_id, "spiffe://company.com/admin/")
}

# Audit all decisions
decision_metadata := {
    "timestamp": time.now_ns(),
    "caller": input.caller_spiffe_id,
    "callee": input.callee_spiffe_id,
    "action": input.action,
    "allowed": allow
}
```

### Step 2: Load Policy into OPA

```bash
# Start OPA with policy directory
opa run --server --addr :8181 /policies

# Or load policy via API
curl -X PUT http://localhost:8181/v1/policies/agentweave \
  --data-binary @policies/authz.rego
```

### Step 3: Configure Agent

```yaml
# config.yaml
authorization:
  provider: "opa"
  opa_endpoint: "http://localhost:8181"
  policy_path: "agentweave/authz"
  default_action: "deny"
```

### Step 4: Test Policy

```bash
# Test policy evaluation
curl -X POST http://localhost:8181/v1/data/agentweave/authz \
  -d '{
    "input": {
      "caller_spiffe_id": "spiffe://company.com/agent/orchestrator",
      "callee_spiffe_id": "spiffe://company.com/agent/search",
      "action": "search"
    }
  }'

# Response:
{
  "result": {
    "allow": true,
    "decision_metadata": {
      "timestamp": 1701234567890,
      "caller": "spiffe://company.com/agent/orchestrator",
      "callee": "spiffe://company.com/agent/search",
      "action": "search",
      "allowed": true
    }
  }
}
```

---

## Policy Testing

OPA supports **unit testing** for policies:

### Test File

Create `policies/authz_test.rego`:

```rego
package agentweave.authz

import rego.v1

# Test: Orchestrator can search
test_orchestrator_can_search {
    allow with input as {
        "caller_spiffe_id": "spiffe://company.com/agent/orchestrator",
        "callee_spiffe_id": "spiffe://company.com/agent/search",
        "action": "search"
    }
}

# Test: Unknown agent cannot search
test_unknown_cannot_search {
    not allow with input as {
        "caller_spiffe_id": "spiffe://evil.com/agent/attacker",
        "callee_spiffe_id": "spiffe://company.com/agent/search",
        "action": "search"
    }
}

# Test: Search agent cannot call orchestrator
test_search_cannot_call_orchestrator {
    not allow with input as {
        "caller_spiffe_id": "spiffe://company.com/agent/search",
        "callee_spiffe_id": "spiffe://company.com/agent/orchestrator",
        "action": "anything"
    }
}

# Test: Admin can do anything
test_admin_can_do_anything {
    allow with input as {
        "caller_spiffe_id": "spiffe://company.com/admin/alice",
        "callee_spiffe_id": "spiffe://company.com/agent/anything",
        "action": "anything"
    }
}
```

### Running Tests

```bash
# Run OPA tests
opa test policies/

# Output:
policies/authz_test.rego:
PASS: 4/4
```

{: .note }
**Test your policies!** Authorization bugs are security vulnerabilities. OPA's testing framework makes it easy to verify policies behave correctly.

---

## The @requires_peer Decorator

AgentWeave provides a decorator for inline authorization checks:

```python
from agentweave import SecureAgent, capability, requires_peer

class SearchAgent(SecureAgent):
    @capability("search")
    @requires_peer("spiffe://company.com/agent/orchestrator")
    async def search(self, query: str) -> TaskResult:
        """Only orchestrator can call this."""
        results = await self._db.search(query)
        return TaskResult(status="completed", artifacts=[results])

    @capability("index")
    @requires_peer("spiffe://company.com/agent/*")
    async def index(self, documents: list) -> TaskResult:
        """Any agent in company.com trust domain can call this."""
        await self._db.bulk_index(documents)
        return TaskResult(status="completed")

    @capability("admin_delete")
    @requires_peer("spiffe://company.com/admin/*")
    async def admin_delete(self, id: str) -> TaskResult:
        """Only admins can call this."""
        await self._db.delete(id)
        return TaskResult(status="completed")
```

**Pattern matching:**
- Exact match: `spiffe://company.com/agent/orchestrator`
- Wildcard: `spiffe://company.com/agent/*` (any agent in trust domain)
- Prefix: `spiffe://company.com/admin/*` (all admins)

{: .warning }
`@requires_peer` is a convenience for simple cases. For complex policies (attribute-based, time-based, context-dependent), use OPA policies.

---

## Advanced Policy Patterns

### Time-Based Authorization

Allow access only during business hours:

```rego
package agentweave.authz

import rego.v1

default allow := false

allow {
    input.action == "search"
    during_business_hours
}

during_business_hours {
    # Get current hour (UTC)
    now := time.now_ns()
    hour := time.clock([now])[0]

    # 9 AM to 5 PM UTC
    hour >= 9
    hour < 17
}
```

### Rate Limiting via Policy

Track request counts using external data:

```rego
package agentweave.authz

import rego.v1

default allow := false

# External data source with request counts
# (populated by agent or external system)
import data.request_counts

allow {
    input.action == "search"

    # Check rate limit
    count := request_counts[input.caller_spiffe_id]
    count < 100  # Max 100 requests per window
}
```

### Data Classification

Restrict access based on data sensitivity:

```rego
package agentweave.authz

import rego.v1

default allow := false

# Data classification levels
data_levels := {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3
}

# Agent clearance levels
agent_clearance := {
    "spiffe://company.com/agent/public": 0,
    "spiffe://company.com/agent/internal": 1,
    "spiffe://company.com/agent/confidential": 2,
    "spiffe://company.com/admin": 3
}

allow {
    # Get clearance level for caller
    clearance := agent_clearance[input.caller_spiffe_id]

    # Get data classification from context
    data_class := input.context.data_classification

    # Allow if clearance >= data classification
    clearance >= data_levels[data_class]
}
```

### Delegation Chains

Allow agents to act on behalf of others:

```rego
package agentweave.authz

import rego.v1

default allow := false

# Direct authorization
allow {
    input.caller_spiffe_id == "spiffe://company.com/agent/orchestrator"
    input.action == "search"
}

# Delegation: orchestrator delegates to proxy
allow {
    input.caller_spiffe_id == "spiffe://company.com/agent/proxy"
    input.context.delegated_by == "spiffe://company.com/agent/orchestrator"
    input.action == "search"

    # Verify delegation is valid (e.g., signed token)
    valid_delegation
}

valid_delegation {
    # Check delegation token signature
    # (implementation depends on token format)
    ...
}
```

---

## Audit Logging

Every authorization decision is logged for audit:

```json
{
  "timestamp": "2024-12-07T10:30:00Z",
  "audit_id": "550e8400-e29b-41d4-a716-446655440000",
  "caller_spiffe_id": "spiffe://company.com/agent/orchestrator",
  "callee_spiffe_id": "spiffe://company.com/agent/search",
  "action": "search",
  "decision": "allowed",
  "reason": "Authorized by policy agentweave.authz",
  "policy_version": "1.2.0",
  "context": {
    "query": "test",
    "max_results": 10
  }
}
```

**Audit logs include:**
- **timestamp**: When the decision was made
- **audit_id**: Unique ID for correlation
- **caller_spiffe_id**: Who made the request
- **callee_spiffe_id**: Who they're trying to call (or null for inbound)
- **action**: What capability they're trying to invoke
- **decision**: `allowed` or `denied`
- **reason**: Policy that made the decision
- **context**: Additional request metadata

### Audit Log Storage

Configure audit log destination:

```yaml
authorization:
  provider: "opa"
  audit:
    enabled: true
    destination: "file:///var/log/agentweave/audit.log"
    # Or:
    # destination: "syslog://localhost:514"
    # destination: "kafka://kafka:9092/audit-topic"
```

---

## Troubleshooting

### Policy Not Loading

**Error:**
```
OPAError: Failed to evaluate policy: package agentweave.authz not found
```

**Solution:**
1. Check policy is loaded in OPA:
   ```bash
   curl http://localhost:8181/v1/policies
   ```
2. Verify `policy_path` in config matches package in Rego:
   ```yaml
   policy_path: "agentweave/authz"  # Must match package name
   ```
   ```rego
   package agentweave.authz  # Must match policy_path
   ```

### Always Denied

**Error:**
```
AuthorizationError: Not authorized: default deny
```

**Solution:**
1. Check default policy:
   ```rego
   default allow := false  # ✅ Correct
   default allow := true   # ❌ Too permissive
   ```
2. Verify at least one `allow` rule matches:
   ```bash
   # Test policy manually
   curl -X POST http://localhost:8181/v1/data/agentweave/authz \
     -d '{"input": {...}}'
   ```

### OPA Not Reachable

**Error:**
```
ConnectionError: Cannot connect to OPA at http://localhost:8181
```

**Solution:**
1. Check OPA is running:
   ```bash
   curl http://localhost:8181/health
   ```
2. Verify endpoint in config:
   ```yaml
   opa_endpoint: "http://localhost:8181"  # Correct
   # NOT: http://localhost:8181/v1/data   # Wrong
   ```

---

## What's Next?

Now that you understand authorization, see how agents communicate:

- [A2A Protocol](communication/): Agent-to-agent communication with A2A
- [Security Model](security-model/): How authorization fits into the overall security architecture

{: .note }
OPA is incredibly powerful. This guide covers AgentWeave integration. For advanced Rego features (comprehensions, recursion, external data), see the [OPA documentation](https://www.openpolicyagent.org/docs/).
