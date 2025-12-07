# Federated Multi-Domain Agent Example

This example demonstrates cross-domain federation using SPIFFE trust bundles, enabling agents from different organizations or cloud environments to communicate securely.

## Overview

In this scenario:
- **Organization A** (`hvs.solutions`) operates agents in GCP
- **Organization B** (`partner.example.com`) operates agents in AWS
- Agents need to communicate across organizational boundaries
- Each organization maintains its own SPIRE server and trust domain

## Architecture

```
┌─────────────────────────────────┐     ┌─────────────────────────────────┐
│     Organization A (GCP)        │     │    Organization B (AWS)         │
│     Trust Domain: hvs.solutions │     │    Trust Domain: partner.ex...  │
├─────────────────────────────────┤     ├─────────────────────────────────┤
│                                 │     │                                 │
│  ┌──────────────────────┐       │     │  ┌──────────────────────┐       │
│  │  SPIRE Server A      │◄──────┼─────┼─►│  SPIRE Server B      │       │
│  │  (Trust Bundle       │       │     │  │  (Trust Bundle       │       │
│  │   Exchange)          │       │     │  │   Exchange)          │       │
│  └──────────┬───────────┘       │     │  └──────────┬───────────┘       │
│             │                   │     │             │                   │
│  ┌──────────▼───────────┐       │     │  ┌──────────▼───────────┐       │
│  │  SPIRE Agent A       │       │     │  │  SPIRE Agent B       │       │
│  └──────────┬───────────┘       │     │  └──────────┬───────────┘       │
│             │                   │     │             │                   │
│  ┌──────────▼───────────┐       │     │  ┌──────────▼───────────┐       │
│  │  Data Processor      │       │     │  │  Analytics Agent     │       │
│  │  SPIFFE ID:          │◄──────┼─────┼─►│  SPIFFE ID:          │       │
│  │  spiffe://hvs...     │       │     │  │  spiffe://partner... │       │
│  └──────────────────────┘       │     │  └──────────────────────┘       │
│                                 │     │                                 │
└─────────────────────────────────┘     └─────────────────────────────────┘
```

## Federation Setup

### 1. SPIRE Server Federation

Each SPIRE server must be configured to federate with the other:

**SPIRE Server A (hvs.solutions)**:
```hcl
server {
    trust_domain = "hvs.solutions"
    # ... other config ...
}

# Federation with partner.example.com
plugins {
    BundlePublisher "https_web" {
        plugin_data {
            address = "0.0.0.0:8443"
            acme {
                domain_name = "spire-server.hvs.solutions"
                email = "admin@hvs.solutions"
            }
        }
    }
}
```

**SPIRE Server B (partner.example.com)**:
```hcl
server {
    trust_domain = "partner.example.com"
    # ... other config ...
}

# Federation with hvs.solutions
plugins {
    BundlePublisher "https_web" {
        plugin_data {
            address = "0.0.0.0:8443"
            acme {
                domain_name = "spire-server.partner.example.com"
                email = "admin@partner.example.com"
            }
        }
    }
}
```

### 2. Establish Trust Bundle Exchange

On SPIRE Server A:
```bash
# Fetch partner's trust bundle
spire-server bundle show -format spiffe \
    -trustDomain partner.example.com \
    -endpointURL https://spire-server.partner.example.com:8443

# Set the federated bundle
spire-server bundle set \
    -format spiffe \
    -id spiffe://partner.example.com \
    -path partner-bundle.pem
```

On SPIRE Server B:
```bash
# Fetch HVS's trust bundle
spire-server bundle show -format spiffe \
    -trustDomain hvs.solutions \
    -endpointURL https://spire-server.hvs.solutions:8443

# Set the federated bundle
spire-server bundle set \
    -format spiffe \
    -id spiffe://hvs.solutions \
    -path hvs-bundle.pem
```

### 3. Agent Configuration

**Data Processor Agent (Organization A)**:
```yaml
# config/data-processor.yaml
agent:
  name: "data-processor"
  trust_domain: "hvs.solutions"
  description: "Processes data from federated sources"
  capabilities:
    - name: "process_data"
      description: "Process data and return results"
      input_modes: ["application/json"]
      output_modes: ["application/json"]

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"
  allowed_trust_domains:
    - "hvs.solutions"           # Own domain
    - "partner.example.com"     # Federated domain

authorization:
  provider: "opa"
  opa_endpoint: "http://localhost:8181"
  policy_path: "hvs/authz"
  default_action: "deny"
```

**Analytics Agent (Organization B)**:
```yaml
# config/analytics-agent.yaml
agent:
  name: "analytics-agent"
  trust_domain: "partner.example.com"
  description: "Performs analytics on data"
  capabilities:
    - name: "analyze"
      description: "Analyze data using ML models"
      input_modes: ["application/json"]
      output_modes: ["application/json"]

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"
  allowed_trust_domains:
    - "partner.example.com"     # Own domain
    - "hvs.solutions"           # Federated domain

authorization:
  provider: "opa"
  opa_endpoint: "http://localhost:8181"
  policy_path: "partner/authz"
  default_action: "deny"
```

### 4. OPA Authorization Policies

**Organization A Policy** (`hvs/authz.rego`):
```rego
package hvs.authz

import rego.v1

default allow := false

# Allow internal communication within hvs.solutions
allow if {
    startswith(input.caller_spiffe_id, "spiffe://hvs.solutions/")
    startswith(input.callee_spiffe_id, "spiffe://hvs.solutions/")
}

# Allow partner.example.com analytics agent to call our processor
allow if {
    input.caller_spiffe_id == "spiffe://partner.example.com/agent/analytics-agent/prod"
    input.callee_spiffe_id == "spiffe://hvs.solutions/agent/data-processor/prod"
    input.action == "process_data"
}

# Log all cross-domain requests
cross_domain_request if {
    caller_domain := split(input.caller_spiffe_id, "/")[2]
    callee_domain := split(input.callee_spiffe_id, "/")[2]
    caller_domain != callee_domain
}
```

**Organization B Policy** (`partner/authz.rego`):
```rego
package partner.authz

import rego.v1

default allow := false

# Allow internal communication within partner.example.com
allow if {
    startswith(input.caller_spiffe_id, "spiffe://partner.example.com/")
    startswith(input.callee_spiffe_id, "spiffe://partner.example.com/")
}

# Allow our analytics agent to call hvs.solutions processor
allow if {
    input.caller_spiffe_id == "spiffe://partner.example.com/agent/analytics-agent/prod"
    startswith(input.callee_spiffe_id, "spiffe://hvs.solutions/")
    input.action in ["process_data", "query_data"]
}
```

## Example Agent Code

**Data Processor Agent**:
```python
from agentweave import SecureAgent, capability, requires_peer
from agentweave.types import TaskResult

class DataProcessorAgent(SecureAgent):
    """Processes data from any trusted domain."""

    @capability("process_data")
    @requires_peer("spiffe://*/agent/*")  # Accept from any federated domain
    async def process_data(self, data: dict) -> TaskResult:
        """
        Process data from federated agent.

        Authorization is enforced by OPA policy, which restricts
        which specific agents can call this capability.
        """
        # Get caller's SPIFFE ID from request context
        caller_id = self.current_request_context.caller_spiffe_id
        caller_domain = caller_id.split("/")[2]

        self.logger.info(f"Processing data from federated domain: {caller_domain}")

        processed = {
            "original_data": data,
            "processed_by": self.spiffe_id,
            "caller": caller_id,
            "timestamp": self.current_time()
        }

        return TaskResult(
            status="completed",
            artifacts=[{
                "type": "processed_data",
                "data": processed
            }]
        )
```

**Analytics Agent**:
```python
from agentweave import SecureAgent, capability
from agentweave.types import TaskResult

class AnalyticsAgent(SecureAgent):
    """Performs analytics using federated data sources."""

    @capability("analyze")
    async def analyze(self, query: dict) -> TaskResult:
        """Run analysis across federated data sources."""

        # Call data processor in different trust domain
        processor_result = await self.call_agent(
            target="spiffe://hvs.solutions/agent/data-processor/prod",
            task_type="process_data",
            payload={
                "query": query,
                "requester": self.spiffe_id
            }
        )

        # Perform analytics on processed data
        processed_data = processor_result.artifacts[0]["data"]

        analytics = {
            "data_source": "hvs.solutions",
            "analysis": self._run_analytics(processed_data),
            "metadata": {
                "cross_domain": True,
                "trust_domains": ["hvs.solutions", "partner.example.com"]
            }
        }

        return TaskResult(
            status="completed",
            artifacts=[{
                "type": "analytics_report",
                "data": analytics
            }]
        )
```

## Deployment with Tailscale (Optional)

For simplified cross-cloud networking, combine SPIFFE identity with Tailscale connectivity:

```yaml
# Tailscale ACL (tailscale.com admin console)
{
  "acls": [
    {
      "action": "accept",
      "src": ["tag:hvs-agents"],
      "dst": ["tag:partner-agents:8443"]
    },
    {
      "action": "accept",
      "src": ["tag:partner-agents"],
      "dst": ["tag:hvs-agents:8443"]
    }
  ],
  "tagOwners": {
    "tag:hvs-agents": ["admin@hvs.solutions"],
    "tag:partner-agents": ["admin@partner.example.com"]
  }
}
```

Agents automatically discover each other via MagicDNS:
- `data-processor.hvs-agents.ts.net`
- `analytics-agent.partner-agents.ts.net`

**Important**: Tailscale provides network connectivity only. SPIFFE still provides cryptographic identity and mTLS encryption.

## Security Considerations

1. **Trust Bundle Rotation**: Automate trust bundle updates using SPIRE's federation API
2. **Policy Review**: Cross-domain policies should be reviewed by both organizations
3. **Audit Logging**: Enable audit logs for all federated calls
4. **Rate Limiting**: Implement rate limits for cross-domain requests
5. **Monitoring**: Set up alerts for unusual cross-domain traffic patterns

## Testing Federation

```bash
# Test from Organization A to Organization B
hvs-agent call \
  --from spiffe://hvs.solutions/agent/data-processor/prod \
  --to spiffe://partner.example.com/agent/analytics-agent/prod \
  --task analyze \
  --payload '{"query": "test"}'

# Verify trust bundle is valid
spire-server bundle show -trustDomain partner.example.com

# Check OPA policy evaluation
hvs-agent authz check \
  --caller spiffe://partner.example.com/agent/analytics-agent/prod \
  --callee spiffe://hvs.solutions/agent/data-processor/prod \
  --action process_data
```

## Troubleshooting

### Trust Bundle Issues
```bash
# Refresh trust bundle
spire-server bundle refresh -id spiffe://partner.example.com

# Verify bundle contents
openssl x509 -in partner-bundle.pem -text -noout
```

### mTLS Handshake Failures
- Check that both domains are in `allowed_trust_domains`
- Verify SPIRE agents can access updated trust bundles
- Ensure firewall rules allow traffic on port 8443

### Authorization Denials
- Review OPA policy logs: `docker logs opa`
- Test policy in OPA Playground
- Verify SPIFFE IDs match policy exactly

## References

- [SPIFFE Federation Spec](https://spiffe.io/docs/latest/federation/)
- [SPIRE Federation Guide](https://spiffe.io/docs/latest/spire/using/federation/)
- [OPA SPIFFE Integration](https://www.openpolicyagent.org/docs/latest/envoy-authorization/)
