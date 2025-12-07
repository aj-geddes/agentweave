# AgentWeave SDK - Federation Authorization Policy
#
# This policy handles cross-domain trust and federated identity validation
# for agents communicating across different trust domains (organizations,
# cloud providers, partners, etc.)
#
# Policy Decision Path: agentweave/authz/federation/allow
#
# This policy should be used in conjunction with the default policy for
# comprehensive authorization coverage.

package agentweave.authz.federation

import rego.v1

# -----------------------------------------------------------------------------
# Federation Configuration
# -----------------------------------------------------------------------------
# Define trusted partner domains and their allowed interactions
# This configuration should be version controlled and reviewed

# List of allowed federated trust domains
# Add partner domains here after establishing SPIFFE federation
allowed_domains := {
    "agentweave.io",           # Primary trust domain
    "partner.example.com",     # Example partner domain
    "vendor.cloud.net",        # Example vendor domain
}

# Cross-domain capability mappings
# Define which external agents can call which capabilities
federation_rules := {
    # Partner domain can call our search service
    "partner.example.com": {
        "allowed_resources": {
            "spiffe://agentweave.io/agent/search": ["search", "query"],
            "spiffe://agentweave.io/agent/public-api": ["query"],
        },
    },
    # Vendor domain can only call specific data processor
    "vendor.cloud.net": {
        "allowed_resources": {
            "spiffe://agentweave.io/agent/data-processor": ["process"],
        },
    },
}

# -----------------------------------------------------------------------------
# Default Deny for Federation
# -----------------------------------------------------------------------------
default allow := false

# -----------------------------------------------------------------------------
# Federated Domain Validation
# -----------------------------------------------------------------------------
# Allow cross-domain calls only if explicitly configured

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

# -----------------------------------------------------------------------------
# Federated Identity Trust Chain Validation
# -----------------------------------------------------------------------------
# Verify that federated identities meet trust requirements

# Check if the caller's SPIFFE ID follows expected naming conventions
valid_federated_identity if {
    is_federated_call
    valid_spiffe_format(input.caller_spiffe_id)
    valid_spiffe_format(input.resource_spiffe_id)
}

# Helper to validate SPIFFE ID format
valid_spiffe_format(spiffe_id) if {
    startswith(spiffe_id, "spiffe://")
    parts := split(spiffe_id, "/")
    count(parts) >= 4  # Minimum: spiffe://domain/type/name
}

# -----------------------------------------------------------------------------
# Additional Security Constraints
# -----------------------------------------------------------------------------

# Require explicit context for federated calls
requires_context if {
    is_federated_call
    input.context
    input.context.request_id
}

# Example: Rate limiting context for federated calls
# This would be evaluated alongside the main policy
federated_rate_limit_ok if {
    is_federated_call
    input.context.rate_limit_quota_remaining > 0
}

# Example: Time-based access windows for federated partners
# Useful for maintenance windows or scheduled integrations
within_allowed_timeframe if {
    is_federated_call
    current_hour := time.clock([time.now_ns()])[0]
    # Example: Only allow federated calls during business hours (9-17 UTC)
    current_hour >= 9
    current_hour < 17
}

# -----------------------------------------------------------------------------
# Audit and Compliance
# -----------------------------------------------------------------------------

# Enhanced audit logging for federated calls
# Include additional metadata for compliance tracking
audit_metadata := metadata if {
    is_federated_call
    metadata := {
        "federated": true,
        "caller_domain": input.caller_trust_domain,
        "resource_domain": input.resource_trust_domain,
        "cross_boundary": true,
        "compliance_tag": "cross-org-access",
    }
}

audit_metadata := metadata if {
    not is_federated_call
    metadata := {
        "federated": false,
    }
}

# -----------------------------------------------------------------------------
# Response with Details
# -----------------------------------------------------------------------------

reason := r if {
    allow
    r := sprintf(
        "Federated access allowed: %s (%s) -> %s (%s) for action '%s'",
        [
            input.caller_spiffe_id,
            input.caller_trust_domain,
            input.resource_spiffe_id,
            input.resource_trust_domain,
            input.action,
        ]
    )
}

reason := r if {
    not allow
    is_federated_call
    not caller_domain_allowed
    r := sprintf(
        "Denied: Trust domain '%s' is not in allowed federation list",
        [input.caller_trust_domain]
    )
}

reason := r if {
    not allow
    is_federated_call
    caller_domain_allowed
    not resource_allowed_for_caller
    r := sprintf(
        "Denied: Resource '%s' not accessible to domain '%s'",
        [input.resource_spiffe_id, input.caller_trust_domain]
    )
}

reason := r if {
    not allow
    is_federated_call
    caller_domain_allowed
    resource_allowed_for_caller
    not action_allowed_for_resource
    r := sprintf(
        "Denied: Action '%s' not permitted for resource '%s' by domain '%s'",
        [input.action, input.resource_spiffe_id, input.caller_trust_domain]
    )
}

policy_id := "federation-v1"

decision := {
    "allow": allow,
    "reason": reason,
    "policy_id": policy_id,
    "audit": audit_metadata,
    "evaluated_at": time.now_ns(),
}
