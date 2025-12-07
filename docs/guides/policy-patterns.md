---
layout: page
title: Common Authorization Patterns
description: Real-world OPA policy patterns for agent authorization
parent: How-To Guides
nav_order: 2
---

# Common Authorization Patterns

This guide provides complete, copy-paste-ready OPA (Rego) policy patterns for common authorization scenarios in AgentWeave.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Understanding Authorization in AgentWeave

AgentWeave uses Open Policy Agent (OPA) to make authorization decisions. Every agent-to-agent call goes through authorization:

```
┌─────────┐         ┌─────┐         ┌─────────┐
│ Caller  │───────▶ │ OPA │───────▶ │ Callee  │
│ Agent   │  Allow? │     │  Yes!   │ Agent   │
└─────────┘         └─────┘         └─────────┘
                       │
                       │ No!
                       ▼
                  [Denied]
```

### Input Schema

OPA receives this input for each request:

```json
{
  "caller_spiffe_id": "spiffe://yourdomain.com/agent/orchestrator",
  "resource_spiffe_id": "spiffe://yourdomain.com/agent/search",
  "action": "search",
  "caller_trust_domain": "yourdomain.com",
  "resource_trust_domain": "yourdomain.com",
  "timestamp": "2025-12-07T12:00:00Z",
  "context": {
    "payload_size": 1024,
    "request_id": "uuid-here"
  }
}
```

### Decision Path

Your policy must set: `agentweave.authz.allow` to `true` or `false`

---

## Pattern 1: Allow by Trust Domain

**Use Case:** Allow all agents within the same trust domain to communicate

**Security Level:** Medium (suitable for small teams/orgs)

```rego
package agentweave.authz

import rego.v1

# Default deny
default allow := false

# Allow same trust domain
allow if {
    same_trust_domain
    valid_spiffe_ids
}

same_trust_domain if {
    input.caller_trust_domain == input.resource_trust_domain
}

valid_spiffe_ids if {
    startswith(input.caller_spiffe_id, "spiffe://")
    startswith(input.resource_spiffe_id, "spiffe://")
}

# Provide reason for audit
reason := "Allowed: Same trust domain" if allow
reason := "Denied: Different trust domains" if not allow
```

**When to use:**
- Small organizations with trusted internal teams
- All agents in the same deployment environment
- Rapid prototyping before implementing fine-grained policies

**When NOT to use:**
- Multi-tenant environments
- Different security levels within same trust domain
- Production systems requiring least-privilege access

---

## Pattern 2: Allow Specific Agents

**Use Case:** Explicitly allow specific agent pairs to communicate

**Security Level:** High (explicit allowlist)

```rego
package agentweave.authz

import rego.v1

default allow := false

# Define allowed agent pairs
allowed_calls := [
    {
        "caller": "spiffe://yourdomain.com/agent/orchestrator",
        "callee": "spiffe://yourdomain.com/agent/search",
        "actions": ["search", "query"]
    },
    {
        "caller": "spiffe://yourdomain.com/agent/orchestrator",
        "callee": "spiffe://yourdomain.com/agent/processor",
        "actions": ["process", "transform"]
    },
    {
        "caller": "spiffe://yourdomain.com/agent/search",
        "callee": "spiffe://yourdomain.com/agent/indexer",
        "actions": ["query"]
    },
]

# Check if call is explicitly allowed
allow if {
    some call in allowed_calls
    call.caller == input.caller_spiffe_id
    call.callee == input.resource_spiffe_id
    input.action in call.actions
}

reason := r if {
    allow
    r := sprintf("Allowed: Explicit policy for %s -> %s:%s",
        [input.caller_spiffe_id, input.resource_spiffe_id, input.action])
}

reason := "Denied: No explicit allow rule" if not allow
```

**When to use:**
- Production environments requiring strict access control
- Compliance requirements (SOC2, HIPAA, etc.)
- Multi-tenant systems
- High-security applications

**Advantages:**
- Least privilege by default
- Easy to audit (all allowed paths are explicit)
- Clear security boundaries

**Disadvantages:**
- Requires maintenance as agents are added/removed
- More verbose policy files

---

## Pattern 3: Allow Specific Capabilities

**Use Case:** Grant permissions based on capability/action, not caller identity

**Security Level:** Medium-High

```rego
package agentweave.authz

import rego.v1

default allow := false

# Define capabilities and their required permissions
capability_requirements := {
    "search": {
        "public": true,
        "requires_trust_domain": true
    },
    "process": {
        "public": false,
        "allowed_callers": [
            "spiffe://yourdomain.com/agent/orchestrator",
            "spiffe://yourdomain.com/agent/search"
        ]
    },
    "admin": {
        "public": false,
        "allowed_callers": [
            "spiffe://yourdomain.com/agent/admin-console"
        ]
    },
}

# Allow public capabilities from same trust domain
allow if {
    requirements := capability_requirements[input.action]
    requirements.public == true
    requirements.requires_trust_domain == true
    input.caller_trust_domain == input.resource_trust_domain
}

# Allow restricted capabilities from specific callers
allow if {
    requirements := capability_requirements[input.action]
    requirements.public == false
    input.caller_spiffe_id in requirements.allowed_callers
}

reason := r if {
    allow
    requirements := capability_requirements[input.action]
    requirements.public == true
    r := sprintf("Allowed: Public capability '%s' from same trust domain", [input.action])
}

reason := r if {
    allow
    requirements := capability_requirements[input.action]
    requirements.public == false
    r := sprintf("Allowed: Restricted capability '%s' from authorized caller", [input.action])
}

reason := "Denied: Capability not allowed for this caller" if not allow
```

**When to use:**
- APIs with public and private capabilities
- Role-based access where capabilities define roles
- Services with mixed security levels

---

## Pattern 4: Deny by Default with Exceptions

**Use Case:** Block all access except for specific allowed patterns

**Security Level:** Very High (zero-trust model)

```rego
package agentweave.authz

import rego.v1

# Explicit default deny
default allow := false

# Exception 1: Health checks always allowed
allow if {
    input.action == "health_check"
    valid_spiffe_id(input.caller_spiffe_id)
}

# Exception 2: Metrics scraping from monitoring agents
allow if {
    input.action in ["metrics", "status"]
    is_monitoring_agent
}

is_monitoring_agent if {
    contains(input.caller_spiffe_id, "/agent/prometheus")
}

# Exception 3: Emergency admin access
allow if {
    is_admin_agent
    is_emergency_window
}

is_admin_agent if {
    contains(input.caller_spiffe_id, "/agent/admin")
}

is_emergency_window if {
    # Allow admin access only during defined emergency window
    # This would typically be set via OPA data updates
    data.emergency_mode.enabled == true
}

# Exception 4: Specific production agent pairs
allow if {
    is_production_pair
}

is_production_pair if {
    input.caller_spiffe_id == "spiffe://yourdomain.com/agent/api-gateway"
    input.resource_spiffe_id == "spiffe://yourdomain.com/agent/backend"
    input.action in ["query", "process"]
}

# Helper function
valid_spiffe_id(id) if {
    startswith(id, "spiffe://yourdomain.com/")
}

reason := r if {
    allow
    input.action == "health_check"
    r := "Allowed: Health check from valid agent"
}

reason := r if {
    allow
    is_monitoring_agent
    r := "Allowed: Metrics access for monitoring"
}

reason := r if {
    allow
    is_admin_agent
    r := "Allowed: Emergency admin access"
}

reason := "Denied: No exception applies" if not allow
```

**When to use:**
- Maximum security environments
- After a security incident
- Regulated industries
- Systems handling sensitive data

---

## Pattern 5: Time-Based Access

**Use Case:** Allow access only during specific time windows

**Security Level:** High (adds temporal constraint)

```rego
package agentweave.authz

import rego.v1

default allow := false

# Allow calls during business hours
allow if {
    is_business_hours
    same_trust_domain
    valid_action
}

is_business_hours if {
    # Get current hour in UTC
    current_hour := time.clock([time.now_ns()])[0]

    # Business hours: 9 AM - 5 PM UTC
    current_hour >= 9
    current_hour < 17
}

same_trust_domain if {
    input.caller_trust_domain == input.resource_trust_domain
}

valid_action if {
    input.action in ["search", "query", "process"]
}

# Allow maintenance operations during maintenance window
allow if {
    is_maintenance_window
    is_maintenance_agent
    is_maintenance_action
}

is_maintenance_window if {
    current_hour := time.clock([time.now_ns()])[0]
    # Maintenance window: 2 AM - 4 AM UTC
    current_hour >= 2
    current_hour < 4
}

is_maintenance_agent if {
    contains(input.caller_spiffe_id, "/agent/maintenance")
}

is_maintenance_action if {
    input.action in ["update", "restart", "backup"]
}

# 24/7 access for critical operations
allow if {
    input.action in ["health_check", "alert", "emergency"]
    same_trust_domain
}

reason := r if {
    allow
    is_business_hours
    r := "Allowed: Business hours operation"
}

reason := r if {
    allow
    is_maintenance_window
    r := "Allowed: Maintenance window"
}

reason := r if {
    allow
    input.action in ["health_check", "alert", "emergency"]
    r := "Allowed: Critical operation (24/7)"
}

reason := r if {
    not allow
    not is_business_hours
    r := "Denied: Outside business hours"
}

reason := "Denied: Time constraint not met" if not allow
```

**When to use:**
- Batch processing systems (only during off-hours)
- Maintenance operations
- Cost optimization (limit expensive calls to business hours)
- Compliance requirements (e.g., data access only during audited hours)

---

## Pattern 6: Attribute-Based Access Control (ABAC)

**Use Case:** Make decisions based on request attributes, not just identity

**Security Level:** Very High (fine-grained control)

```rego
package agentweave.authz

import rego.v1

default allow := false

# Allow based on multiple attributes
allow if {
    # Basic identity check
    valid_identities

    # Environment matching
    caller_env == resource_env

    # Payload size limit
    within_size_limit

    # Rate limit check
    within_rate_limit
}

valid_identities if {
    startswith(input.caller_spiffe_id, "spiffe://yourdomain.com/")
    startswith(input.resource_spiffe_id, "spiffe://yourdomain.com/")
}

caller_env := env if {
    # Extract environment from SPIFFE ID
    # Format: spiffe://domain/agent/<name>/<env>
    parts := split(input.caller_spiffe_id, "/")
    count(parts) >= 5
    env := parts[4]
}

resource_env := env if {
    parts := split(input.resource_spiffe_id, "/")
    count(parts) >= 5
    env := parts[4]
}

within_size_limit if {
    # Limit payload size based on action
    size_limits := {
        "search": 10240,      # 10KB
        "process": 1048576,   # 1MB
        "upload": 10485760,   # 10MB
    }

    max_size := size_limits[input.action]
    input.context.payload_size <= max_size
}

within_rate_limit if {
    # Check rate limit from context
    # (Rate limit tracking would be external to OPA)
    input.context.rate_limit_remaining > 0
}

# Special case: Admin agents bypass size limits
allow if {
    is_admin
    valid_identities
    within_rate_limit
}

is_admin if {
    contains(input.caller_spiffe_id, "/agent/admin")
}

reason := r if {
    allow
    is_admin
    r := "Allowed: Admin agent (size limit bypassed)"
}

reason := r if {
    allow
    not is_admin
    r := sprintf("Allowed: Valid request (env=%s, size=%d, rate_ok=%v)",
        [caller_env, input.context.payload_size, within_rate_limit])
}

reason := r if {
    not allow
    not within_size_limit
    r := "Denied: Payload size exceeds limit"
}

reason := r if {
    not allow
    not within_rate_limit
    r := "Denied: Rate limit exceeded"
}

reason := r if {
    not allow
    caller_env != resource_env
    r := sprintf("Denied: Environment mismatch (%s != %s)", [caller_env, resource_env])
}
```

**When to use:**
- Complex authorization requirements
- Multi-environment deployments (dev/staging/prod isolation)
- Rate limiting enforcement
- Payload validation
- Fine-grained security controls

**Attributes you can use:**
- SPIFFE ID components (trust domain, path, environment)
- Timestamps (time-based access)
- Payload size
- Rate limit quotas
- Custom context fields
- External data (OPA data documents)

---

## Pattern 7: Cross-Domain Federation Policies

**Use Case:** Allow agents from different trust domains (organizations) to communicate

**Security Level:** High (requires SPIFFE federation)

```rego
package agentweave.authz.federation

import rego.v1

default allow := false

# Allowed federated domains
allowed_domains := {
    "yourdomain.com",
    "partner.example.com",
    "vendor.cloud.net",
}

# Cross-domain rules
federation_rules := {
    "partner.example.com": {
        "allowed_resources": {
            "spiffe://yourdomain.com/agent/public-api": ["query", "search"],
            "spiffe://yourdomain.com/agent/search": ["search"],
        },
    },
    "vendor.cloud.net": {
        "allowed_resources": {
            "spiffe://yourdomain.com/agent/data-processor": ["process"],
        },
    },
}

# Allow federated calls with explicit rules
allow if {
    is_federated_call
    caller_domain_allowed
    resource_allowed_for_caller
    action_allowed_for_resource
}

is_federated_call if {
    input.caller_trust_domain != input.resource_trust_domain
}

caller_domain_allowed if {
    input.caller_trust_domain in allowed_domains
}

resource_allowed_for_caller if {
    rules := federation_rules[input.caller_trust_domain]
    input.resource_spiffe_id in object.keys(rules.allowed_resources)
}

action_allowed_for_resource if {
    rules := federation_rules[input.caller_trust_domain]
    allowed_actions := rules.allowed_resources[input.resource_spiffe_id]
    input.action in allowed_actions
}

# Additional security: Require audit context for federated calls
allow if {
    is_federated_call
    # ... other checks ...
    has_audit_context
}

has_audit_context if {
    input.context.request_id != ""
    input.context.caller_org != ""
}

reason := r if {
    allow
    is_federated_call
    r := sprintf("Allowed: Federated access from %s -> %s:%s",
        [input.caller_trust_domain, input.resource_spiffe_id, input.action])
}

reason := r if {
    not allow
    is_federated_call
    not caller_domain_allowed
    r := sprintf("Denied: Trust domain '%s' not in federation allowlist",
        [input.caller_trust_domain])
}

reason := r if {
    not allow
    is_federated_call
    caller_domain_allowed
    not resource_allowed_for_caller
    r := sprintf("Denied: Resource '%s' not accessible to '%s'",
        [input.resource_spiffe_id, input.caller_trust_domain])
}
```

**When to use:**
- Partner integrations
- Multi-cloud deployments
- Vendor access to your agents
- B2B agent communication
- Cross-organization collaboration

**Prerequisites:**
- SPIFFE federation configured between trust domains
- Trust bundle exchange established
- Legal/compliance approval for data sharing

---

## Testing Your Policies

### Using OPA REPL

```bash
# Start OPA with your policy
opa run policy.rego

# Test in REPL
> input := {
    "caller_spiffe_id": "spiffe://yourdomain.com/agent/orchestrator",
    "resource_spiffe_id": "spiffe://yourdomain.com/agent/search",
    "action": "search",
    "caller_trust_domain": "yourdomain.com",
    "resource_trust_domain": "yourdomain.com"
  }
> data.agentweave.authz.allow
true
```

### Using AgentWeave Test Fixtures

```python
from agentweave.testing import MockAuthorizationProvider

# Configure mock with your policy rules
authz = MockAuthorizationProvider(
    default_allow=False,
    policy_rules={
        "spiffe://test.local/agent/caller:spiffe://test.local/agent/callee:search": True,
    }
)

# Test authorization
decision = await authz.check_outbound(
    caller_id="spiffe://test.local/agent/caller",
    callee_id="spiffe://test.local/agent/callee",
    action="search"
)

assert decision.allowed == True
```

### Integration Testing with OPA

```python
import pytest
from agentweave.authz import OPAAuthzProvider

@pytest.mark.asyncio
async def test_policy_allows_orchestrator():
    # Start OPA with your policy
    authz = OPAAuthzProvider(
        opa_endpoint="http://localhost:8181",
        policy_path="agentweave/authz"
    )

    decision = await authz.check_outbound(
        caller_id="spiffe://yourdomain.com/agent/orchestrator",
        callee_id="spiffe://yourdomain.com/agent/search",
        action="search",
        context={"request_id": "test-123"}
    )

    assert decision.allowed == True
    assert "orchestrator" in decision.reason
```

---

## Policy Development Workflow

1. **Start with Default Deny**
   ```rego
   default allow := false
   ```

2. **Add Specific Allow Rules**
   - Start narrow (specific agent pairs)
   - Expand as needed (trust domain, capabilities)

3. **Test with Real Identities**
   - Use actual SPIFFE IDs from your environment
   - Test both allow and deny cases

4. **Add Audit Reasons**
   ```rego
   reason := "Allowed: <specific reason>"
   ```

5. **Monitor in Production**
   - Check OPA decision logs
   - Look for unexpected denials
   - Adjust policies based on usage

---

## Related Guides

- [Configure Identity Providers](identity-providers.md) - Set up SPIFFE IDs for your agents
- [Testing Your Agents](testing.md) - Test authorization policies
- [Production Checklist](production-checklist.md) - Security review for policies
- [Error Handling](error-handling.md) - Handle AuthorizationError exceptions

---

## External Resources

- [OPA Documentation](https://www.openpolicyagent.org/docs/)
- [Rego Language Guide](https://www.openpolicyagent.org/docs/latest/policy-language/)
- [OPA Policy Testing](https://www.openpolicyagent.org/docs/latest/policy-testing/)
- [SPIFFE Federation](https://spiffe.io/docs/latest/spiffe-about/federation/)
