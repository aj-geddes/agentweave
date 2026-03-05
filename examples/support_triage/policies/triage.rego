package agentweave.authz

import rego.v1

# Default deny - secure by default
default allow := false

# -------------------------------------------------------------------
# Rule 1: Triage agent can route to any specialist
# Only the triage agent is permitted to call handle_ticket on
# billing, technical, or account specialist agents.
# -------------------------------------------------------------------
allow if {
	input.action == "handle_ticket"
	input.caller_spiffe_id == "spiffe://support.example/agent/triage"
	specialist_agents[input.resource_spiffe_id]
}

specialist_agents contains agent if {
	some agent in {
		"spiffe://support.example/agent/billing",
		"spiffe://support.example/agent/technical",
		"spiffe://support.example/agent/account",
	}
}

# -------------------------------------------------------------------
# Rule 2: Specialists can only be called by the triage agent
# This is enforced implicitly by Rule 1 being the only rule that
# grants handle_ticket access to specialist agents. Explicitly
# deny any non-triage caller attempting handle_ticket on a
# specialist, even if another rule might inadvertently allow it.
# -------------------------------------------------------------------
deny if {
	input.action == "handle_ticket"
	specialist_agents[input.resource_spiffe_id]
	input.caller_spiffe_id != "spiffe://support.example/agent/triage"
}

# -------------------------------------------------------------------
# Rule 3: Any authorized agent in the trust domain can submit tickets
# -------------------------------------------------------------------
allow if {
	input.action == "submit_ticket"
	startswith(input.caller_spiffe_id, "spiffe://support.example/")
}

# -------------------------------------------------------------------
# Rule 4: Any agent in the trust domain can check ticket status
# and retrieve metrics
# -------------------------------------------------------------------
allow if {
	input.action in ["get_ticket_status", "get_metrics"]
	startswith(input.caller_spiffe_id, "spiffe://support.example/")
}

# -------------------------------------------------------------------
# Deny cross-domain access by default
# -------------------------------------------------------------------
deny if {
	caller_domain := split(input.caller_spiffe_id, "/")[2]
	caller_domain != "support.example"
}
