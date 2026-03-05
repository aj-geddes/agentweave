package agentweave.authz

import rego.v1

default allow := false

# Ingest accepts from authorized submitters within finance.example
allow if {
    input.action == "ingest"
    input.resource_spiffe_id == "spiffe://finance.example/agent/ingest"
    startswith(input.caller_spiffe_id, "spiffe://finance.example/")
}

# Validate only accepts from Ingest
allow if {
    input.action == "validate"
    input.caller_spiffe_id == "spiffe://finance.example/agent/ingest"
}

# Enrich only accepts from Validate
allow if {
    input.action == "enrich"
    input.caller_spiffe_id == "spiffe://finance.example/agent/validator"
}

# Store only accepts from Enrich
allow if {
    input.action == "store"
    input.caller_spiffe_id == "spiffe://finance.example/agent/enricher"
}

# Query is available to any finance.example agent
allow if {
    input.action == "query"
    startswith(input.caller_spiffe_id, "spiffe://finance.example/")
}
