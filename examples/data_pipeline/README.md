# Secure Multi-Stage Data Pipeline

A financial company processes transaction data through a secure pipeline with
cryptographic identity and chain-of-custody authorization at every stage.

## Architecture

```
[Client] --> [Ingest Agent] --> [Validate Agent] --> [Enrich Agent] --> [Store Agent]
                  |                   |                   |                  |
             Accepts raw         Validates schema     Adds metadata     Persists to
             transactions        & business rules     & enrichment      secure store
```

Each stage is a separate agent with its own SPIFFE identity and authorization
policy. Only the previous stage in the pipeline can call the next stage,
enforcing a strict chain-of-custody over transaction data.

## SPIFFE Identities

| Agent    | SPIFFE ID                                   | Port |
|----------|---------------------------------------------|------|
| Ingest   | `spiffe://finance.example/agent/ingest`     | 8443 |
| Validate | `spiffe://finance.example/agent/validator`  | 8444 |
| Enrich   | `spiffe://finance.example/agent/enricher`   | 8445 |
| Store    | `spiffe://finance.example/agent/store`      | 8446 |

## Features Demonstrated

- **Chain-of-custody authorization** -- Each stage can only call the next stage
  in the pipeline. The OPA policy and `@requires_peer` decorators both enforce
  this constraint independently.
- **`@requires_peer` for strict caller verification** -- The Validate agent
  only accepts calls from the Ingest agent, Enrich only from Validate, and
  Store only from Enrich.
- **`@audit_log` for compliance** -- Every capability invocation is
  audit-logged with caller identity, action, timing, and success/failure.
- **Error propagation through pipeline** -- Invalid transactions are rejected
  at the earliest stage; high-value transactions are flagged at validation.
- **Observability with metrics and tracing** -- All agents export Prometheus
  metrics and OpenTelemetry traces for end-to-end pipeline visibility.
- **OPA policies for pipeline flow control** -- The Rego policy in
  `policies/pipeline.rego` enforces the allowed caller/callee relationships.

## Files

```
data_pipeline/
  pipeline.py                  # Agent definitions for all four stages
  test_pipeline.py             # Tests for chain-of-custody and business logic
  config/
    ingest.yaml                # Ingest agent configuration
    validator.yaml             # Validator agent configuration
    enricher.yaml              # Enricher agent configuration
    store.yaml                 # Store agent configuration
  policies/
    pipeline.rego              # OPA policy enforcing pipeline flow
```

## Running the Example

### Prerequisites

- Python >= 3.11
- AgentWeave SDK installed (`pip install -e ".[dev]"` from repo root)
- SPIRE agent running (for production) or use `mtls-static` identity provider
  (for development)
- OPA server at `http://localhost:8181` with the pipeline policy loaded

### Development Mode

```bash
# From the repo root
python examples/data_pipeline/pipeline.py
```

### Running Tests

```bash
# From the repo root
pytest examples/data_pipeline/test_pipeline.py -v
```

### Loading the OPA Policy

```bash
# Upload the pipeline policy to OPA
curl -X PUT http://localhost:8181/v1/policies/pipeline \
  --data-binary @examples/data_pipeline/policies/pipeline.rego
```

## Authorization Flow

When a transaction batch arrives at the Ingest agent:

1. **Ingest** checks that the caller is within `spiffe://finance.example/`.
2. Ingest forwards accepted transactions to **Validate**.
3. Validate verifies the caller is `spiffe://finance.example/agent/ingest`
   (both via `@requires_peer` and OPA policy).
4. Validate forwards valid transactions to **Enrich**.
5. Enrich verifies the caller is `spiffe://finance.example/agent/validator`.
6. Enrich forwards enriched transactions to **Store**.
7. Store verifies the caller is `spiffe://finance.example/agent/enricher`.
8. Store persists the batch and returns a confirmation.

Any attempt to skip a stage (e.g., Ingest calling Store directly) is denied
by both the `@requires_peer` decorator and the OPA policy.

## Transaction Lifecycle

```
Raw transaction
  --> Ingest: adds batch_id, ingested_at, source
  --> Validate: checks amount > 0, flags high-value (> $1M)
  --> Enrich: adds account_name, account_tier, country
  --> Store: adds stored_at, storage_status = "persisted"
```
