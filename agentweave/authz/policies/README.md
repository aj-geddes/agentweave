# AgentWeave SDK - OPA Policy Templates

This directory contains Rego policy templates for the AgentWeave SDK authorization layer.

## Policy Files

### default.rego
The default authorization policy for agent-to-agent communication. Implements:

- **Default Deny**: All requests are denied unless explicitly allowed
- **Same Trust Domain**: Agents in the same trust domain can communicate
- **Capability-Based Access**: Role-based matrix for fine-grained control
- **Audit Metadata**: Detailed reasons for all decisions

**Policy Path**: `agentweave/authz/allow`

**Usage**:
```bash
# Load into OPA
opa run --server --bundle agentweave/authz/policies/default.rego

# Or via Docker
docker run -p 8181:8181 -v $(pwd)/agentweave/authz/policies:/policies \
  openpolicyagent/opa:latest run --server /policies/default.rego
```

### federation.rego
Federation policy for cross-domain trust and partner access. Implements:

- **Federated Domain Allowlist**: Only permitted partner domains can call
- **Cross-Domain Rules**: Specific resource and action mappings per partner
- **Identity Validation**: SPIFFE ID format and trust chain verification
- **Enhanced Audit**: Additional compliance metadata for federated calls

**Policy Path**: `agentweave/authz/federation/allow`

**Usage**:
```bash
# Load alongside default policy
opa run --server \
  --bundle agentweave/authz/policies/default.rego \
  --bundle agentweave/authz/policies/federation.rego
```

## Customizing Policies

### 1. Define Agent Roles

Edit `default.rego` to match your agent architecture:

```rego
role_capabilities := {
    "orchestrator": {
        "search": ["search", "query"],
        "processor": ["process", "transform"],
    },
    # Add your roles here
}
```

### 2. Configure Federation

Edit `federation.rego` to add trusted partners:

```rego
allowed_domains := {
    "agentweave.io",
    "partner.example.com",  # Add partner domain
}

federation_rules := {
    "partner.example.com": {
        "allowed_resources": {
            "spiffe://agentweave.io/agent/public-api": ["query"],
        },
    },
}
```

### 3. Test Policies

Use OPA's testing framework:

```rego
# test_default.rego
package agentweave.authz

test_same_domain_allowed {
    allow with input as {
        "caller_spiffe_id": "spiffe://agentweave.io/agent/orchestrator",
        "resource_spiffe_id": "spiffe://agentweave.io/agent/search",
        "action": "search",
        "caller_trust_domain": "agentweave.io",
        "resource_trust_domain": "agentweave.io",
    }
}

test_cross_domain_denied {
    not allow with input as {
        "caller_spiffe_id": "spiffe://evil.com/agent/attacker",
        "resource_spiffe_id": "spiffe://agentweave.io/agent/search",
        "action": "search",
        "caller_trust_domain": "evil.com",
        "resource_trust_domain": "agentweave.io",
    }
}
```

Run tests:
```bash
opa test agentweave/authz/policies/
```

## Policy Evaluation Flow

```
1. Request arrives with SPIFFE IDs and action
   ↓
2. OPAProvider builds input document
   ↓
3. OPA evaluates default.rego
   ↓
4. If cross-domain, also evaluates federation.rego
   ↓
5. Decision returned with reason and audit_id
   ↓
6. SDK enforces decision (deny = reject request)
```

## Integration with AgentWeave SDK

The SDK's `OPAProvider` class automatically:

1. Queries the policy at the configured path
2. Includes SPIFFE context (caller, resource, trust domains)
3. Caches decisions with TTL
4. Applies circuit breaker for OPA failures
5. Logs all decisions for audit trail

Example configuration:

```yaml
authorization:
  provider: "opa"
  opa_endpoint: "http://localhost:8181"
  policy_path: "agentweave/authz"  # Evaluates agentweave/authz/allow
  default_action: "deny"
```

## Best Practices

1. **Version Control**: Keep policies in Git alongside code
2. **Code Review**: Require review for policy changes
3. **Testing**: Write comprehensive policy tests
4. **Monitoring**: Alert on authorization failures
5. **Audit**: Retain decision logs for compliance
6. **Principle of Least Privilege**: Start restrictive, open as needed

## References

- [OPA Documentation](https://www.openpolicyagent.org/docs/)
- [SPIFFE Specification](https://spiffe.io/docs/)
- [AgentWeave SDK Specification](../../../spec.md)
