# Customer Support Triage System

A complete example demonstrating a multi-agent customer support system built with
AgentWeave. A triage agent classifies incoming tickets and routes them to specialist
agents based on content analysis.

## Architecture

```
                    +----------------+
[Customer Ticket] --> | Triage Agent   |
                    +-------+--------+
                            | classifies & routes
               +------------+------------+
               v            v            v
      +-----------+  +------------+  +-----------+
      | Billing   |  | Technical  |  | Account   |
      | Agent     |  | Agent      |  | Agent     |
      +-----------+  +------------+  +-----------+
```

## Agents

| Agent     | SPIFFE ID                                  | Role                                      |
|-----------|--------------------------------------------|--------------------------------------------|
| Triage    | `spiffe://support.example/agent/triage`    | Classifies tickets and routes to specialists |
| Billing   | `spiffe://support.example/agent/billing`   | Handles billing, invoices, refunds         |
| Technical | `spiffe://support.example/agent/technical`  | Handles errors, performance, certificates  |
| Account   | `spiffe://support.example/agent/account`   | Handles login, access, MFA issues          |

## Features Demonstrated

- **Dynamic routing via `call_agent`** -- the triage agent routes tickets to specialist agents based on keyword classification
- **Multiple specialist agents** -- each handles a focused domain with domain-specific processing logic
- **Observability** -- internal metrics tracking (total tickets, per-category counts)
- **RequestContext** -- ticket tracking across agent boundaries using `get_current_context()`
- **Classification logic** -- keyword-based content classification with confidence scoring
- **Error handling and fallback** -- graceful handling when specialist routing fails; unrecognized tickets go to a general queue
- **OPA authorization policies** -- only the triage agent can call specialists; specialists cannot call each other

## Files

| File                     | Description                                    |
|--------------------------|------------------------------------------------|
| `triage.py`              | Agent implementations and demo runner          |
| `config.yaml`            | Agent configuration for the triage system      |
| `policies/triage.rego`   | OPA authorization policy                       |
| `test_triage.py`         | Tests for classification, routing, and authz   |

## Running the Demo

```bash
# From the repository root
cd examples/support_triage
python triage.py
```

## Running Tests

```bash
# From the repository root
cd examples/support_triage
pytest test_triage.py -v
```

## Authorization Model

The OPA policy enforces the following rules:

1. **Triage agent can route to any specialist** -- only the triage agent is permitted to call `handle_ticket` on specialist agents
2. **Specialists cannot call each other** -- billing cannot call technical, etc.
3. **Any authorized agent can submit tickets** -- any agent within the `support.example` trust domain can call `submit_ticket` on the triage agent
4. **Any agent can check ticket status** -- `get_ticket_status` and `get_metrics` are open to all agents in the trust domain
5. **External agents are denied by default** -- agents outside `support.example` have no access
