package agentweave.authz

import rego.v1

# Default deny - secure by default
default allow := false

# Allow any agent in research.example domain to search and summarize
allow if {
	input.action in ["search", "summarize", "stats"]
	startswith(input.caller_spiffe_id, "spiffe://research.example/")
}

# Only admin agents can index documents
allow if {
	input.action == "index"
	startswith(input.caller_spiffe_id, "spiffe://research.example/agent/admin")
}

# Deny cross-domain access by default
deny if {
	caller_domain := split(input.caller_spiffe_id, "/")[2]
	resource_domain := split(input.resource_spiffe_id, "/")[2]
	caller_domain != resource_domain
}
