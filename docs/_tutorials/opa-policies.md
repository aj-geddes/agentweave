---
layout: tutorial
title: Writing OPA Policies
permalink: /tutorials/opa-policies/
nav_order: 4
parent: Tutorials
difficulty: Intermediate
duration: 45 minutes
---

# Writing OPA Policies

In this tutorial, you'll master authorization by writing custom OPA (Open Policy Agent) policies in Rego. You'll learn to control who can call your agents, what capabilities they can access, and under what conditions.

## Learning Objectives

By completing this tutorial, you will:
- Understand OPA and Rego fundamentals
- Write policies that enforce security requirements
- Test policies using the OPA CLI
- Integrate policies with AgentWeave agents
- Implement common authorization patterns
- Follow policy testing best practices

## Prerequisites

Before starting, ensure you have:
- **Completed** [Building Your First Agent](/agentweave/tutorials/first-agent/)
- **OPA installed** - Download from [openpolicyagent.org](https://www.openpolicyagent.org/docs/latest/#running-opa)
- **Basic understanding** of authorization concepts (allow/deny, identity, permissions)
- **JSON knowledge** - Rego works with JSON data

**Time estimate:** 45 minutes

## What is OPA?

**Open Policy Agent (OPA)** is a general-purpose policy engine that decouples policy decision-making from policy enforcement.

**Key concepts:**
- **Policies** - Written in Rego language
- **Input** - JSON data to make decisions about (request context)
- **Output** - Boolean decision (allow/deny) or structured data
- **Evaluation** - OPA evaluates input against policies

## What is Rego?

**Rego** is OPA's declarative policy language. Key characteristics:

- **Declarative** - You state what should be true, not how to compute it
- **Logic-based** - Similar to Prolog or Datalog
- **JSON-native** - Works seamlessly with JSON data
- **Composable** - Build complex policies from simple rules

## AgentWeave Policy Input

When AgentWeave calls OPA to authorize a request, it provides this input structure:

```json
{
  "caller": {
    "spiffe_id": "spiffe://example.org/client-agent",
    "trust_domain": "example.org",
    "path": "/client-agent"
  },
  "agent": {
    "spiffe_id": "spiffe://example.org/my-agent",
    "trust_domain": "example.org",
    "name": "My Agent"
  },
  "request": {
    "method": "process_data",
    "params": {
      "data": "sensitive information"
    },
    "timestamp": "2025-12-07T10:30:00Z"
  },
  "context": {
    "remote_addr": "10.0.1.5",
    "request_id": "req-12345"
  }
}
```

Your policy evaluates this input and returns `allow: true` or `allow: false`.

## Step 1: Your First Policy

Let's start with the simplest possible policy.

Create `policies/hello_policy.rego`:

```rego
package agentweave.authz

# Default deny - security first
default allow = false

# Allow everything (for testing only!)
allow {
    true
}
```

This policy:
1. Sets the package name (must be `agentweave.authz`)
2. Defaults to deny
3. Has one rule that always allows

### Test with OPA CLI

Create test input in `test_input.json`:

```json
{
  "caller": {
    "spiffe_id": "spiffe://example.org/test-client"
  },
  "agent": {
    "spiffe_id": "spiffe://example.org/my-agent"
  },
  "request": {
    "method": "test"
  }
}
```

Test the policy:

```bash
opa eval --data policies/hello_policy.rego \
         --input test_input.json \
         --format pretty \
         'data.agentweave.authz.allow'
```

Output:
```
true
```

Great! The policy evaluated to `true` (allow).

## Step 2: Allow Specific Callers

Now let's write a realistic policy that only allows specific callers.

Create `policies/specific_caller_policy.rego`:

```rego
package agentweave.authz

# Default deny
default allow = false

# Allow requests from a specific agent
allow {
    # Get the caller's SPIFFE ID from input
    input.caller.spiffe_id == "spiffe://example.org/trusted-agent"
}

# Also allow requests from another specific agent
allow {
    input.caller.spiffe_id == "spiffe://example.org/admin-agent"
}
```

### Understanding the Rule

```rego
allow {
    input.caller.spiffe_id == "spiffe://example.org/trusted-agent"
}
```

This means:
- `allow` is true **if** the condition in braces is true
- `input.caller.spiffe_id` accesses the caller's identity from input
- `==` checks for exact equality
- If the condition is false, this rule doesn't apply (falls through to default)

### Test It

Create `test_trusted.json`:
```json
{
  "caller": {
    "spiffe_id": "spiffe://example.org/trusted-agent"
  },
  "request": {
    "method": "anything"
  }
}
```

```bash
opa eval --data policies/specific_caller_policy.rego \
         --input test_trusted.json \
         --format pretty \
         'data.agentweave.authz.allow'
```

Output: `true`

Now test with an untrusted caller in `test_untrusted.json`:
```json
{
  "caller": {
    "spiffe_id": "spiffe://example.org/random-agent"
  }
}
```

```bash
opa eval --data policies/specific_caller_policy.rego \
         --input test_untrusted.json \
         --format pretty \
         'data.agentweave.authz.allow'
```

Output: `false`

Perfect! The policy correctly denies unknown callers.

## Step 3: Allow by Trust Domain

Often you want to allow all agents in your organization (trust domain).

Create `policies/trust_domain_policy.rego`:

```rego
package agentweave.authz

default allow = false

# Allow requests from the same trust domain
allow {
    # Extract trust domain from caller's SPIFFE ID
    # SPIFFE ID format: spiffe://trust-domain/path
    caller_trust_domain := split(input.caller.spiffe_id, "/")[2]

    # Get our trust domain
    our_trust_domain := input.agent.trust_domain

    # Allow if they match
    caller_trust_domain == our_trust_domain
}
```

### Understanding split()

`split(input.caller.spiffe_id, "/")[2]` breaks down like this:

Given: `"spiffe://example.org/my-agent"`
1. `split(..., "/")` → `["spiffe:", "", "example.org", "my-agent"]`
2. `[2]` → `"example.org"` (zero-indexed array)

### Test Trust Domain Policy

```bash
# Create test input
cat > test_same_domain.json << 'EOF'
{
  "caller": {
    "spiffe_id": "spiffe://example.org/any-agent"
  },
  "agent": {
    "trust_domain": "example.org"
  }
}
EOF

# Test - should allow
opa eval --data policies/trust_domain_policy.rego \
         --input test_same_domain.json \
         --format pretty \
         'data.agentweave.authz.allow'
```

Output: `true`

Test with different trust domain:
```bash
cat > test_different_domain.json << 'EOF'
{
  "caller": {
    "spiffe_id": "spiffe://other-org.com/agent"
  },
  "agent": {
    "trust_domain": "example.org"
  }
}
EOF

opa eval --data policies/trust_domain_policy.rego \
         --input test_different_domain.json \
         --format pretty \
         'data.agentweave.authz.allow'
```

Output: `false`

## Step 4: Allow Specific Capabilities

Let's control access to specific capabilities (methods).

Create `policies/capability_policy.rego`:

```rego
package agentweave.authz

default allow = false

# Allow read operations for any authenticated caller
allow {
    # Caller must have a valid SPIFFE ID
    input.caller.spiffe_id != ""

    # Allow these read-only methods
    input.request.method in ["get_data", "list_items", "search"]
}

# Allow write operations only for admin agents
allow {
    # Must be from admin path
    startswith(input.caller.spiffe_id, "spiffe://example.org/admin/")

    # Allow these write methods
    input.request.method in ["create", "update", "delete"]
}

# Allow dangerous operations only for specific service
allow {
    input.caller.spiffe_id == "spiffe://example.org/system/backup-service"
    input.request.method == "delete_all"
}
```

### Understanding the Policy

This policy has three rules:

1. **Read operations** - Any authenticated agent can read
2. **Write operations** - Only admin agents can write
3. **Dangerous operations** - Only specific system service

The `in` operator checks if a value is in an array:
```rego
input.request.method in ["get_data", "list_items", "search"]
```

The `startswith()` function checks string prefixes:
```rego
startswith(input.caller.spiffe_id, "spiffe://example.org/admin/")
```

### Test It

```bash
# Test read operation - should allow
cat > test_read.json << 'EOF'
{
  "caller": {
    "spiffe_id": "spiffe://example.org/regular-agent"
  },
  "request": {
    "method": "get_data"
  }
}
EOF

opa eval --data policies/capability_policy.rego \
         --input test_read.json \
         --format pretty \
         'data.agentweave.authz.allow'
# Output: true

# Test write by non-admin - should deny
cat > test_write_nonadmin.json << 'EOF'
{
  "caller": {
    "spiffe_id": "spiffe://example.org/regular-agent"
  },
  "request": {
    "method": "delete"
  }
}
EOF

opa eval --data policies/capability_policy.rego \
         --input test_write_nonadmin.json \
         --format pretty \
         'data.agentweave.authz.allow'
# Output: false

# Test write by admin - should allow
cat > test_write_admin.json << 'EOF'
{
  "caller": {
    "spiffe_id": "spiffe://example.org/admin/admin-agent"
  },
  "request": {
    "method": "delete"
  }
}
EOF

opa eval --data policies/capability_policy.rego \
         --input test_write_admin.json \
         --format pretty \
         'data.agentweave.authz.allow'
# Output: true
```

## Step 5: Time-Based Access

Restrict access to certain time windows.

Create `policies/time_policy.rego`:

```rego
package agentweave.authz

import future.keywords.in

default allow = false

# Allow access only during business hours (9 AM - 5 PM UTC)
allow {
    # Parse timestamp from request
    timestamp := time.parse_rfc3339_ns(input.request.timestamp)

    # Get hour of day (UTC)
    hour := time.clock([timestamp])[0]

    # Allow between 9 AM and 5 PM
    hour >= 9
    hour < 17

    # Must be from same trust domain
    caller_trust_domain := split(input.caller.spiffe_id, "/")[2]
    our_trust_domain := input.agent.trust_domain
    caller_trust_domain == our_trust_domain
}

# System agents can always access
allow {
    startswith(input.caller.spiffe_id, "spiffe://example.org/system/")
}
```

### Understanding Time Functions

OPA provides time functions:
- `time.parse_rfc3339_ns()` - Parse ISO 8601 timestamp
- `time.clock([timestamp])` - Extract `[hour, minute, second]`

### Test It

```bash
# Test during business hours
cat > test_business_hours.json << 'EOF'
{
  "caller": {
    "spiffe_id": "spiffe://example.org/worker"
  },
  "agent": {
    "trust_domain": "example.org"
  },
  "request": {
    "method": "process",
    "timestamp": "2025-12-07T14:30:00Z"
  }
}
EOF

opa eval --data policies/time_policy.rego \
         --input test_business_hours.json \
         --format pretty \
         'data.agentweave.authz.allow'
# Output: true

# Test outside business hours
cat > test_after_hours.json << 'EOF'
{
  "caller": {
    "spiffe_id": "spiffe://example.org/worker"
  },
  "agent": {
    "trust_domain": "example.org"
  },
  "request": {
    "timestamp": "2025-12-07T22:30:00Z"
  }
}
EOF

opa eval --data policies/time_policy.rego \
         --input test_after_hours.json \
         --format pretty \
         'data.agentweave.authz.allow'
# Output: false

# Test system agent after hours - should allow
cat > test_system_after_hours.json << 'EOF'
{
  "caller": {
    "spiffe_id": "spiffe://example.org/system/monitor"
  },
  "request": {
    "timestamp": "2025-12-07T22:30:00Z"
  }
}
EOF

opa eval --data policies/time_policy.rego \
         --input test_system_after_hours.json \
         --format pretty \
         'data.agentweave.authz.allow'
# Output: true
```

## Step 6: Parameter-Based Authorization

Control access based on request parameters.

Create `policies/parameter_policy.rego`:

```rego
package agentweave.authz

default allow = false

# Allow agents to access their own data
allow {
    # Get user_id from request parameters
    user_id := input.request.params.user_id

    # Extract agent's user from SPIFFE ID
    # Format: spiffe://example.org/user/alice
    caller_path := split(input.caller.spiffe_id, "/")
    caller_user := caller_path[4]  # "alice"

    # Allow if accessing own data
    user_id == caller_user
}

# Allow admin agents to access anyone's data
allow {
    startswith(input.caller.spiffe_id, "spiffe://example.org/admin/")
}

# Deny access to sensitive data regardless of caller
deny {
    input.request.params.data_classification == "top-secret"
    not startswith(input.caller.spiffe_id, "spiffe://example.org/security/")
}

# Final decision: allow if allow rules pass and no deny rules trigger
default decision = false

decision {
    allow
    not deny
}
```

### Understanding Deny Rules

This policy introduces `deny` rules. The final decision is:
- `allow` rules must pass, AND
- `deny` rules must NOT trigger

This implements **deny overrides** - even if an allow rule matches, a deny rule can block access.

### Test It

```bash
# Test user accessing own data - should allow
cat > test_own_data.json << 'EOF'
{
  "caller": {
    "spiffe_id": "spiffe://example.org/user/alice"
  },
  "request": {
    "params": {
      "user_id": "alice"
    }
  }
}
EOF

opa eval --data policies/parameter_policy.rego \
         --input test_own_data.json \
         --format pretty \
         'data.agentweave.authz.decision'
# Output: true

# Test user accessing other's data - should deny
cat > test_other_data.json << 'EOF'
{
  "caller": {
    "spiffe_id": "spiffe://example.org/user/alice"
  },
  "request": {
    "params": {
      "user_id": "bob"
    }
  }
}
EOF

opa eval --data policies/parameter_policy.rego \
         --input test_other_data.json \
         --format pretty \
         'data.agentweave.authz.decision'
# Output: false

# Test accessing top-secret data - should deny even for admin
cat > test_topsecret.json << 'EOF'
{
  "caller": {
    "spiffe_id": "spiffe://example.org/admin/admin-agent"
  },
  "request": {
    "params": {
      "data_classification": "top-secret"
    }
  }
}
EOF

opa eval --data policies/parameter_policy.rego \
         --input test_topsecret.json \
         --format pretty \
         'data.agentweave.authz.decision'
# Output: false
```

## Step 7: Integrate with AgentWeave

Now let's use our policies with a real agent.

### Create Agent with Policy

```python
# agent_with_policy.py
from agentweave import Agent, capability
from agentweave.context import AgentContext

class SecureAgent(Agent):
    """Agent with comprehensive authorization policy."""

    @capability(name="get_data", description="Get data (read operation)")
    async def get_data(self, context: AgentContext, user_id: str):
        return {"user_id": user_id, "data": "some data"}

    @capability(name="delete", description="Delete data (write operation)")
    async def delete(self, context: AgentContext, user_id: str):
        return {"deleted": user_id}

    @capability(name="delete_all", description="Dangerous operation")
    async def delete_all(self, context: AgentContext):
        return {"deleted": "all"}
```

### Configuration

```yaml
# config.yaml
identity:
  spiffe_id: "spiffe://example.org/secure-agent"
  spire_socket: "/tmp/spire-agent/public/api.sock"
  trust_domain: "example.org"

authorization:
  engine: "opa"
  default_policy: "deny_all"  # Explicit policy required
  policy_path: "./policies"
  policy_file: "capability_policy.rego"  # Use the capability policy

server:
  host: "0.0.0.0"
  port: 8443
  mtls:
    enabled: true
    cert_source: "spire"

observability:
  logging:
    level: "INFO"
```

### Run and Test

```bash
# Run the agent
python agent_with_policy.py config.yaml

# Test read operation (should work for any authenticated caller)
agentweave-cli call \
  --agent spiffe://example.org/secure-agent \
  --capability get_data \
  --params '{"user_id": "test"}'
# Success!

# Test write operation (should fail for non-admin)
agentweave-cli call \
  --agent spiffe://example.org/secure-agent \
  --capability delete \
  --params '{"user_id": "test"}'
# Error: Authorization denied
```

## Common Policy Patterns

### Pattern 1: Allowlist by SPIFFE ID

```rego
package agentweave.authz

default allow = false

# Define allowed callers
allowed_callers := {
    "spiffe://example.org/agent-1",
    "spiffe://example.org/agent-2",
    "spiffe://example.org/agent-3"
}

allow {
    input.caller.spiffe_id in allowed_callers
}
```

### Pattern 2: Role-Based Access Control (RBAC)

```rego
package agentweave.authz

default allow = false

# Define roles by SPIFFE path
roles := {
    "admin": {"spiffe://example.org/admin/", "spiffe://example.org/root/"},
    "editor": {"spiffe://example.org/editor/"},
    "viewer": {"spiffe://example.org/viewer/"}
}

# Define permissions by role
permissions := {
    "admin": ["read", "write", "delete", "admin"],
    "editor": ["read", "write"],
    "viewer": ["read"]
}

# Helper to get caller's role
caller_role := role {
    some role
    prefix := roles[role][_]
    startswith(input.caller.spiffe_id, prefix)
}

# Allow if caller's role has permission for method
allow {
    required_permission := method_to_permission(input.request.method)
    required_permission in permissions[caller_role]
}

# Map methods to required permissions
method_to_permission(method) = "read" {
    method in ["get", "list", "search", "view"]
}

method_to_permission(method) = "write" {
    method in ["create", "update", "modify"]
}

method_to_permission(method) = "delete" {
    method in ["delete", "remove"]
}

method_to_permission(method) = "admin" {
    method in ["admin", "configure", "reset"]
}
```

### Pattern 3: Rate Limiting (Conceptual)

```rego
package agentweave.authz

default allow = false

# This is a conceptual example - actual rate limiting requires
# state tracking outside OPA (e.g., Redis)

allow {
    # Basic rate limit check
    # In practice, you'd query an external system
    caller_id := input.caller.spiffe_id
    current_rate := get_current_rate(caller_id)  # External data
    current_rate < 100  # requests per minute

    # Other authorization checks
    input.caller.trust_domain == input.agent.trust_domain
}

# External data would be provided via OPA's data API
get_current_rate(caller_id) = rate {
    rate := data.rate_limits[caller_id].current_rate
}
```

## Policy Testing Best Practices

### 1. Write Tests for All Rules

Create a test file `policy_test.rego`:

```rego
package agentweave.authz

test_allow_same_trust_domain {
    allow with input as {
        "caller": {"spiffe_id": "spiffe://example.org/agent"},
        "agent": {"trust_domain": "example.org"}
    }
}

test_deny_different_trust_domain {
    not allow with input as {
        "caller": {"spiffe_id": "spiffe://other.org/agent"},
        "agent": {"trust_domain": "example.org"}
    }
}

test_allow_admin_write {
    allow with input as {
        "caller": {"spiffe_id": "spiffe://example.org/admin/admin-agent"},
        "request": {"method": "delete"}
    }
}

test_deny_regular_write {
    not allow with input as {
        "caller": {"spiffe_id": "spiffe://example.org/regular-agent"},
        "request": {"method": "delete"}
    }
}
```

Run tests:
```bash
opa test policies/ -v
```

### 2. Test Edge Cases

- Empty strings
- Missing fields
- Invalid formats
- Boundary conditions (time limits, rate limits)

### 3. Use Descriptive Test Names

- `test_allow_...` for positive cases
- `test_deny_...` for negative cases
- Include the scenario in the name

### 4. Organize Tests by Rule

Group tests by the rule they test, making it easy to understand coverage.

## Summary

You've mastered OPA policy writing! You've learned:

- OPA and Rego fundamentals
- AgentWeave's policy input structure
- Writing policies for common patterns:
  - Specific callers
  - Trust domain filtering
  - Capability-based access
  - Time-based access
  - Parameter-based authorization
- Testing policies with OPA CLI
- Integrating policies with AgentWeave
- Policy testing best practices

## Exercises

1. **Write a policy** that allows access only on weekdays (Monday-Friday)
2. **Implement RBAC** with at least 3 roles and 5 permissions
3. **Create tests** for all your policy rules
4. **Write a policy** that requires multi-factor authentication for sensitive operations
5. **Implement** a policy that logs all authorization decisions

## What's Next?

Continue learning:

- **[Adding Observability](/agentweave/tutorials/observability/)** - Monitor policy decisions
- **[How-To: Policy Patterns](/agentweave/guides/policy-patterns/)** - Advanced patterns
- **[Security Best Practices](/agentweave/security/best-practices/)** - Production security
- **[OPA Documentation](https://www.openpolicyagent.org/docs/)** - Official OPA docs

## Troubleshooting

### Policy doesn't seem to apply
- Check package name is `agentweave.authz`
- Verify policy file path in agent config
- Check OPA logs for syntax errors
- Use `opa check` to validate syntax

### Always denied even with allow rules
- Check default_policy in config
- Verify input structure matches policy expectations
- Test policy in isolation with OPA CLI
- Add debug logging to policy

### Policy evaluation is slow
- Avoid complex loops in policies
- Use indexed lookups where possible
- Profile policies with `opa test --bench`
- Consider caching in external systems

See [Troubleshooting Guide](/agentweave/troubleshooting/) for more help.
