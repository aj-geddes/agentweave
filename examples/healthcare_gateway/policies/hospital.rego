package agentweave.authz

import rego.v1

default allow := false

# Hospital internal agents can lookup and get full records
allow if {
	input.action in ["lookup_patient", "get_records"]
	startswith(input.caller_spiffe_id, "spiffe://hospital.health/")
}

# Insurance agents can ONLY get filtered claim data
allow if {
	input.action == "get_claim_data"
	startswith(input.caller_spiffe_id, "spiffe://insurance.health/agent/claims")
}

# Compliance officers can access audit reports
allow if {
	input.action == "audit_report"
	startswith(input.caller_spiffe_id, "spiffe://hospital.health/agent/compliance")
}

# Explicitly deny insurance agents from full records
deny if {
	input.action in ["lookup_patient", "get_records"]
	startswith(input.caller_spiffe_id, "spiffe://insurance.health/")
}
