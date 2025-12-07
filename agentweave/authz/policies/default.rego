# AgentWeave SDK - Default Authorization Policy
#
# This policy implements secure-by-default authorization for agent-to-agent
# communication using SPIFFE identities and capability-based access control.
#
# Policy Decision Path: agentweave/authz/allow
#
# Input Schema:
# {
#   "caller_spiffe_id": "spiffe://trust.domain/agent/name",
#   "resource_spiffe_id": "spiffe://trust.domain/agent/other",
#   "action": "capability_name",
#   "caller_trust_domain": "trust.domain",
#   "resource_trust_domain": "trust.domain",
#   "timestamp": "2025-12-06T12:00:00Z",
#   "context": {
#     "payload_size": 1024,
#     "request_id": "uuid",
#     ...
#   }
# }

package agentweave.authz

import rego.v1

# -----------------------------------------------------------------------------
# Default Deny
# -----------------------------------------------------------------------------
# Security principle: Deny by default, allow explicitly
# This ensures that any request without an explicit allow rule is rejected

default allow := false

# -----------------------------------------------------------------------------
# Same Trust Domain Communication
# -----------------------------------------------------------------------------
# Allow agents within the same trust domain to communicate
# This is the most basic form of authorization - agents in the same
# organizational trust boundary can call each other

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

# -----------------------------------------------------------------------------
# Capability-Based Access Control
# -----------------------------------------------------------------------------
# Define which agents can call which capabilities on other agents
# This section should be customized based on your agent architecture

# Example: Allow orchestrator to call any capability on worker agents
allow if {
    is_orchestrator
    is_worker_agent
}

is_orchestrator if {
    contains(input.caller_spiffe_id, "/agent/orchestrator")
}

is_worker_agent if {
    startswith(input.resource_spiffe_id, "spiffe://")
    contains(input.resource_spiffe_id, "/agent/worker")
}

# Example: Allow search agents to call index agents for specific actions
allow if {
    is_search_agent
    is_index_agent
    input.action in ["query", "search"]
}

is_search_agent if {
    contains(input.caller_spiffe_id, "/agent/search")
}

is_index_agent if {
    contains(input.resource_spiffe_id, "/agent/index")
}

# Example: Role-based capability matrix
# Define which agent roles can perform which actions
allow if {
    caller_role := agent_role(input.caller_spiffe_id)
    resource_role := agent_role(input.resource_spiffe_id)
    allowed_actions := role_capabilities[caller_role][resource_role]
    input.action in allowed_actions
}

# Helper function to extract agent role from SPIFFE ID
# Expected format: spiffe://domain/agent/<role>/<env>
agent_role(spiffe_id) := role if {
    parts := split(spiffe_id, "/")
    count(parts) >= 4
    role := parts[3]
}

# Role capability matrix
# Customize this based on your agent architecture
role_capabilities := {
    "orchestrator": {
        "search": ["search", "query"],
        "processor": ["process", "transform"],
        "storage": ["store", "retrieve"],
    },
    "search": {
        "index": ["query", "search"],
        "storage": ["retrieve"],
    },
    "processor": {
        "storage": ["store", "retrieve"],
        "validator": ["validate"],
    },
}

# -----------------------------------------------------------------------------
# Audit and Metadata
# -----------------------------------------------------------------------------
# Include additional context in the decision response

# Return detailed reason for allow decisions
reason := r if {
    allow
    same_trust_domain
    r := sprintf("Allowed: Same trust domain (%s)", [input.caller_trust_domain])
}

reason := r if {
    allow
    caller_role := agent_role(input.caller_spiffe_id)
    resource_role := agent_role(input.resource_spiffe_id)
    r := sprintf("Allowed: Role %s can %s on %s", [caller_role, input.action, resource_role])
}

# Return detailed reason for deny decisions
reason := r if {
    not allow
    not same_trust_domain
    r := sprintf(
        "Denied: Cross-domain access not permitted (%s -> %s)",
        [input.caller_trust_domain, input.resource_trust_domain]
    )
}

reason := r if {
    not allow
    same_trust_domain
    r := "Denied: No matching policy rule"
}

# Policy metadata
policy_id := "default-v1"

# Structured response
decision := {
    "allow": allow,
    "reason": reason,
    "policy_id": policy_id,
    "evaluated_at": time.now_ns(),
}
