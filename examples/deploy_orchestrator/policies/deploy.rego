package agentweave.authz

import rego.v1

default allow := false

# The CI/CD pipeline can trigger deployments on the orchestrator
allow if {
	input.action in ["deploy", "deploy_with_rollback", "list_deployments", "get_deployment"]
	startswith(input.caller_spiffe_id, "spiffe://devops.example/")
}

# Only the orchestrator can deploy to or rollback environment agents
allow if {
	input.action in ["apply_deployment", "verify_deployment", "rollback"]
	input.caller_spiffe_id == "spiffe://devops.example/agent/orchestrator"
}

# Any devops agent can check health and deployment history
allow if {
	input.action in ["health_check", "get_deploy_history"]
	startswith(input.caller_spiffe_id, "spiffe://devops.example/")
}
