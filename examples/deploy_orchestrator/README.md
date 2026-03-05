# CI/CD Deployment Orchestrator

A deployment system where an orchestrator agent coordinates deployments across
multiple environment agents (staging, production). The orchestrator runs health
checks, manages rollbacks, and uses circuit breakers. Production deployments
require extra authorization.

## Architecture

```
                   +--------------------+
[CI/CD Pipeline] > | Deploy Orchestrator |
                   +----------+---------+
                              |
               +--------------+--------------+
               v              v              v
      +---------------+ +-----------+ +---------------+
      |  Staging Env  | | Prod Env  | | Monitor       |
      |  Agent        | | Agent     | | Agent         |
      +---------------+ +-----------+ +---------------+
                         requires       health checks
                         extra authz    & rollback
```

## SPIFFE Identities

| Agent        | SPIFFE ID                                        | Port |
|--------------|--------------------------------------------------|------|
| Orchestrator | `spiffe://devops.example/agent/orchestrator`      | 8443 |
| Staging      | `spiffe://devops.example/agent/env-staging`       | 8444 |
| Production   | `spiffe://devops.example/agent/env-production`    | 8445 |
| Monitor      | `spiffe://devops.example/agent/monitor`           | 8446 |

## Features Demonstrated

- **Multi-environment deployment orchestration** -- A single orchestrator
  coordinates deployments across staging and production environments.
- **Strict authorization for production deployments** -- Only the orchestrator
  can deploy to environment agents, and production requires a successful
  staging deployment first.
- **Health checks before and after deploy** -- The orchestrator runs pre-deploy
  and post-deploy health checks against environment agents.
- **Rollback capability with state tracking** -- If post-deploy verification
  fails, the orchestrator automatically rolls back. Manual rollback is also
  supported.
- **Circuit breaker for unreachable environments** -- Transport-level circuit
  breakers protect against cascading failures when an environment is down.
- **Retry policies for transient failures** -- Configurable retry with
  exponential backoff for transient network issues.
- **Deployment state machine** -- Each deployment tracks its state through
  `pending -> deploying -> verifying -> complete/rolled_back/failed`.

## Files

```
deploy_orchestrator/
  orchestrator.py              # Agent definitions for orchestrator and environments
  test_orchestrator.py         # Tests for deployment logic and authorization
  config/
    orchestrator.yaml          # Orchestrator agent configuration
    environment.yaml           # Template for environment agent configuration
  policies/
    deploy.rego                # OPA policy enforcing deployment authorization
```

## Running the Example

### Prerequisites

- Python >= 3.11
- AgentWeave SDK installed (`pip install -e ".[dev]"` from repo root)
- SPIRE agent running (for production) or use `mtls-static` identity provider
  (for development)
- OPA server at `http://localhost:8181` with the deploy policy loaded

### Development Mode

```bash
# From the repo root
python examples/deploy_orchestrator/orchestrator.py
```

### Running Tests

```bash
# From the repo root
pytest examples/deploy_orchestrator/test_orchestrator.py -v
```

### Loading the OPA Policy

```bash
# Upload the deploy policy to OPA
curl -X PUT http://localhost:8181/v1/policies/deploy \
  --data-binary @examples/deploy_orchestrator/policies/deploy.rego
```

## Deployment Pipeline

When a deployment is triggered:

1. **Orchestrator** receives a deploy request with service name, version, and
   target environment.
2. If the target is production, the orchestrator verifies that the same service
   and version have been successfully deployed to staging first.
3. **Pre-deploy health check** -- The orchestrator calls the environment agent's
   `health_check` capability to verify the environment is healthy.
4. **Apply deployment** -- The orchestrator calls `apply_deployment` on the
   environment agent. Only the orchestrator's SPIFFE ID is authorized to do this
   (enforced by `@requires_peer` and OPA policy).
5. **Post-deploy verification** -- The orchestrator calls `verify_deployment` to
   confirm the new version is healthy.
6. If verification fails, the orchestrator **automatically rolls back** to the
   previous version.
7. All steps are audit-logged with caller identity and timing.

## Deployment State Machine

```
pending -> deploying -> verifying -> complete
                  |          |
                  v          v
               failed   rolling_back -> rolled_back
                              |
                              v
                           failed
```

## Authorization Flow

The OPA policy in `policies/deploy.rego` enforces:

- The CI/CD pipeline can call the orchestrator to trigger deployments
- Only the orchestrator can deploy to or roll back environment agents
- Any devops agent can check health and deployment status
- Production deployments require an additional `prod_approved` claim
