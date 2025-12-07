---
layout: page
title: Federated Agents Example
permalink: /examples/federated/
parent: Examples Overview
nav_order: 3
---

# Federated Agents Example

**Complexity:** Advanced
**Time to Complete:** 45 minutes
**Prerequisites:** Understanding of SPIFFE federation, PKI basics

This example demonstrates cross-trust-domain agent communication using SPIFFE federation. This pattern enables secure agent collaboration across organizational boundaries, cloud providers, or regulatory domains.

## What You'll Learn

- SPIFFE trust domain federation
- Cross-domain authorization policies
- Trust bundle management
- Federated identity verification
- Security considerations for multi-tenancy

## Use Cases

- **Multi-Organization Collaboration**: Company A's agents call Company B's agents
- **Multi-Cloud Deployment**: AWS agents calling GCP agents
- **Regulatory Boundaries**: Production domain calling compliance audit domain
- **Partner Integration**: Secure API between partner organizations

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    Trust Domain A                              │
│                  (acme-corp.io)                                │
│                                                                │
│  ┌──────────────────┐         ┌─────────────────┐            │
│  │ SPIRE Server A   │         │  Billing Agent  │            │
│  │                  │         │                 │            │
│  │ CA: A            │─────────│ ID: spiffe://   │            │
│  │                  │  Issues │  acme-corp.io/  │            │
│  │ Trust Bundle:    │  SVID   │  agent/billing  │            │
│  │  - CA A (own)    │         │                 │            │
│  │  - CA B (federated)│       │                 │            │
│  └────────┬─────────┘         └────────┬────────┘            │
│           │ Federation                 │                      │
└───────────┼────────────────────────────┼──────────────────────┘
            │ Bundle Exchange            │
            │                            │ Cross-domain call
            │                            │ (mTLS with SVID)
            │                            ▼
┌───────────┼────────────────────────────┼──────────────────────┐
│           │                            │                      │
│  ┌────────▼─────────┐         ┌───────▼─────────┐            │
│  │ SPIRE Server B   │         │  Payment Agent  │            │
│  │                  │         │                 │            │
│  │ CA: B            │─────────│ ID: spiffe://   │            │
│  │                  │  Issues │  partner.com/   │            │
│  │ Trust Bundle:    │  SVID   │  agent/payment  │            │
│  │  - CA B (own)    │         │                 │            │
│  │  - CA A (federated)│       │                 │            │
│  └──────────────────┘         └─────────────────┘            │
│                                                                │
│                    Trust Domain B                              │
│                    (partner.com)                               │
└────────────────────────────────────────────────────────────────┘
```

## Scenario

**ACME Corp** needs to integrate with **Partner Payments Inc** to process customer payments:

- **ACME Corp** operates in trust domain `acme-corp.io`
- **Partner Payments** operates in trust domain `partner.com`
- ACME's Billing Agent needs to call Partner's Payment Agent
- Both organizations maintain independent SPIRE infrastructure
- Trust is established through federation

## Complete Code

### Billing Agent (ACME Corp)

```python
# billing_agent.py
"""
Billing Agent - Processes billing and initiates payments.

Trust Domain: acme-corp.io
Calls: partner.com/agent/payment (federated)
"""

import asyncio
from decimal import Decimal
from typing import Dict, Any

from agentweave import SecureAgent, capability
from agentweave.types import TaskResult, Message, DataPart
from agentweave.exceptions import AgentCallError, FederationError


class BillingAgent(SecureAgent):
    """
    Processes billing and initiates payments via federated partner.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Federated partner agent
        self.payment_agent_id = "spiffe://partner.com/agent/payment"

    @capability("process_billing")
    async def process_billing(
        self,
        customer_id: str,
        amount: Decimal,
        description: str
    ) -> TaskResult:
        """
        Process customer billing and initiate payment.

        This demonstrates:
        - Calling an agent in a different trust domain
        - SDK verifies federated trust bundle
        - Cross-domain authorization
        """
        self.logger.info(
            "Processing billing",
            extra={
                "customer_id": customer_id,
                "amount": str(amount),
                "payment_agent": self.payment_agent_id
            }
        )

        # Create billing record
        billing_record = await self._create_billing_record(
            customer_id, amount, description
        )

        try:
            # Call federated payment agent
            # SDK will:
            # 1. Get our SVID from SPIRE (trust domain A)
            # 2. Get trust bundle for partner.com (trust domain B)
            # 3. Establish mTLS using federated trust
            # 4. Verify payment agent's SVID against trust bundle B
            # 5. Check OPA policy (cross-domain call allowed?)
            payment_result = await self.call_agent(
                target=self.payment_agent_id,
                task_type="process_payment",
                payload={
                    "billing_id": billing_record["id"],
                    "customer_id": customer_id,
                    "amount": str(amount),
                    "currency": "USD",
                    "description": description,
                    "metadata": {
                        "source_domain": "acme-corp.io",
                        "billing_agent": str(self.spiffe_id)
                    }
                },
                timeout=60.0
            )

            if payment_result.status != "completed":
                await self._mark_billing_failed(billing_record["id"])
                raise AgentCallError(
                    f"Payment failed: {payment_result.error}"
                )

            # Extract payment data
            payment_data = payment_result.artifacts[0]["data"]

            # Update billing record
            await self._mark_billing_completed(
                billing_record["id"],
                payment_data["transaction_id"]
            )

            return TaskResult(
                status="completed",
                messages=[
                    Message(
                        role="assistant",
                        parts=[
                            DataPart(data={
                                "billing_id": billing_record["id"],
                                "payment_status": "completed",
                                "transaction_id": payment_data["transaction_id"],
                                "amount": str(amount),
                                "processed_by": self.payment_agent_id
                            })
                        ]
                    )
                ],
                artifacts=[
                    {
                        "type": "billing_result",
                        "data": {
                            "billing_record": billing_record,
                            "payment_data": payment_data
                        }
                    }
                ]
            )

        except FederationError as e:
            # Federation not configured or trust bundle unavailable
            self.logger.error(
                f"Federation error: {e}",
                extra={"target_domain": "partner.com"}
            )
            await self._mark_billing_failed(billing_record["id"])
            return TaskResult(
                status="failed",
                error=f"Cannot establish trust with partner.com: {e}"
            )

        except AgentCallError as e:
            self.logger.error(f"Payment call failed: {e}")
            await self._mark_billing_failed(billing_record["id"])
            return TaskResult(
                status="failed",
                error=f"Payment processing failed: {e}"
            )

    async def _create_billing_record(
        self,
        customer_id: str,
        amount: Decimal,
        description: str
    ) -> Dict[str, Any]:
        """Create billing record in database."""
        # In production, write to database
        import uuid
        return {
            "id": str(uuid.uuid4()),
            "customer_id": customer_id,
            "amount": str(amount),
            "description": description,
            "status": "pending",
            "created_at": self.context.request_time.isoformat()
        }

    async def _mark_billing_completed(
        self,
        billing_id: str,
        transaction_id: str
    ):
        """Mark billing as completed."""
        self.logger.info(
            "Billing completed",
            extra={
                "billing_id": billing_id,
                "transaction_id": transaction_id
            }
        )

    async def _mark_billing_failed(self, billing_id: str):
        """Mark billing as failed."""
        self.logger.warning(
            "Billing failed",
            extra={"billing_id": billing_id}
        )


async def main():
    agent = BillingAgent.from_config("config/billing.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Payment Agent (Partner Payments Inc)

```python
# payment_agent.py
"""
Payment Agent - Processes payments for federated partners.

Trust Domain: partner.com
Called by: Various federated partners
"""

import asyncio
from decimal import Decimal
from typing import Dict, Any

from agentweave import SecureAgent, capability, requires_federated_peer
from agentweave.types import TaskResult, Message, DataPart


class PaymentAgent(SecureAgent):
    """
    Processes payments for federated partners.
    """

    @capability("process_payment")
    @requires_federated_peer(
        trust_domains=["acme-corp.io", "other-partner.io"]
    )
    async def process_payment(
        self,
        billing_id: str,
        customer_id: str,
        amount: str,
        currency: str,
        description: str,
        metadata: Dict[str, Any] = None
    ) -> TaskResult:
        """
        Process payment from federated partner.

        Security:
        - @requires_federated_peer ensures caller is from allowed domain
        - SDK verifies caller's SVID using federated trust bundle
        - Additional OPA policy checks applied
        """
        amount_decimal = Decimal(amount)
        metadata = metadata or {}

        # Get caller's trust domain
        caller_domain = self._extract_trust_domain(
            self.context.caller_spiffe_id
        )

        self.logger.info(
            "Processing federated payment request",
            extra={
                "caller_domain": caller_domain,
                "caller_id": self.context.caller_spiffe_id,
                "amount": amount,
                "currency": currency,
                "billing_id": billing_id
            }
        )

        # Verify caller is authorized for this customer
        if not await self._verify_partner_authorization(
            caller_domain, customer_id
        ):
            return TaskResult(
                status="failed",
                error=f"Partner {caller_domain} not authorized for customer {customer_id}"
            )

        # Process payment
        transaction = await self._process_payment_transaction(
            billing_id=billing_id,
            customer_id=customer_id,
            amount=amount_decimal,
            currency=currency,
            description=description,
            source_domain=caller_domain,
            source_agent=self.context.caller_spiffe_id
        )

        return TaskResult(
            status="completed",
            messages=[
                Message(
                    role="assistant",
                    parts=[
                        DataPart(data={
                            "transaction_id": transaction["id"],
                            "status": transaction["status"],
                            "amount": str(amount_decimal),
                            "currency": currency,
                            "processed_at": transaction["processed_at"]
                        })
                    ]
                )
            ],
            artifacts=[
                {
                    "type": "payment_transaction",
                    "data": transaction
                }
            ]
        )

    async def _verify_partner_authorization(
        self,
        partner_domain: str,
        customer_id: str
    ) -> bool:
        """
        Verify partner is authorized to process payments for customer.

        In production, check:
        - Partner registration database
        - Customer consent records
        - Partner rate limits
        """
        # Simplified for demo
        authorized_partners = ["acme-corp.io", "other-partner.io"]
        return partner_domain in authorized_partners

    async def _process_payment_transaction(
        self,
        billing_id: str,
        customer_id: str,
        amount: Decimal,
        currency: str,
        description: str,
        source_domain: str,
        source_agent: str
    ) -> Dict[str, Any]:
        """Process payment through payment gateway."""
        import uuid
        from datetime import datetime

        # In production, call payment gateway API
        transaction_id = str(uuid.uuid4())

        self.logger.info(
            "Payment processed",
            extra={
                "transaction_id": transaction_id,
                "source_domain": source_domain,
                "amount": str(amount)
            }
        )

        return {
            "id": transaction_id,
            "billing_id": billing_id,
            "customer_id": customer_id,
            "amount": str(amount),
            "currency": currency,
            "description": description,
            "status": "completed",
            "source_domain": source_domain,
            "source_agent": source_agent,
            "processed_at": datetime.utcnow().isoformat()
        }

    @staticmethod
    def _extract_trust_domain(spiffe_id: str) -> str:
        """Extract trust domain from SPIFFE ID."""
        # spiffe://trust-domain/path -> trust-domain
        parts = spiffe_id.split("/")
        return parts[2] if len(parts) > 2 else ""


async def main():
    agent = PaymentAgent.from_config("config/payment.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration

### Billing Agent Configuration

```yaml
# config/billing.yaml (ACME Corp)
agent:
  name: "billing"
  trust_domain: "acme-corp.io"
  description: "Billing agent with federated payment integration"

  capabilities:
    - name: "process_billing"
      description: "Process billing and initiate payment"
      input_modes: ["application/json"]
      output_modes: ["application/json"]

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"

  # Allow our own domain and federated partner
  allowed_trust_domains:
    - "acme-corp.io"      # Own domain
    - "partner.com"        # Federated partner

authorization:
  provider: "opa"
  opa_endpoint: "http://opa-acme:8181"
  policy_path: "acme/authz"
  default_action: "deny"

  audit:
    enabled: true
    destination: "file:///var/log/agentweave/billing-audit.log"

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"

server:
  host: "0.0.0.0"
  port: 8443
  protocol: "a2a"
```

### Payment Agent Configuration

```yaml
# config/payment.yaml (Partner Payments Inc)
agent:
  name: "payment"
  trust_domain: "partner.com"
  description: "Payment processing agent for federated partners"

  capabilities:
    - name: "process_payment"
      description: "Process payment from federated partner"
      input_modes: ["application/json"]
      output_modes: ["application/json"]

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"

  # Allow our domain and federated partners
  allowed_trust_domains:
    - "partner.com"        # Own domain
    - "acme-corp.io"       # Federated partner
    - "other-partner.io"   # Another partner

authorization:
  provider: "opa"
  opa_endpoint: "http://opa-partner:8181"
  policy_path: "partner/authz"
  default_action: "deny"

  audit:
    enabled: true
    destination: "file:///var/log/agentweave/payment-audit.log"
    # Log all federated calls
    log_federated: true

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"

server:
  host: "0.0.0.0"
  port: 8443
  protocol: "a2a"
```

## SPIRE Federation Setup

### SPIRE Server Configuration (ACME Corp)

```hcl
# spire/acme/server.conf
server {
    bind_address = "0.0.0.0"
    bind_port = "8081"
    trust_domain = "acme-corp.io"
    data_dir = "/opt/spire/data"
    log_level = "INFO"
}

plugins {
    DataStore "sql" {
        plugin_data {
            database_type = "postgres"
            connection_string = "postgresql://spire:password@postgres:5432/spire"
        }
    }

    KeyManager "disk" {
        plugin_data {
            keys_path = "/opt/spire/data/keys"
        }
    }

    NodeAttestor "join_token" {
        plugin_data {}
    }

    # Configure federation with partner.com
    BundlePublisher "https" {
        plugin_data {
            # Publish our trust bundle for partner to fetch
            bind_address = "0.0.0.0"
            bind_port = "8443"
            cert_path = "/opt/spire/conf/federation/cert.pem"
            key_path = "/opt/spire/conf/federation/key.pem"
        }
    }
}

# Federation configuration
federation {
    # Define federated trust domain
    bundle_endpoint {
        address = "0.0.0.0"
        port = 8443
    }

    # Configure trust with partner.com
    federates_with "partner.com" {
        bundle_endpoint_url = "https://spire.partner.com:8443"
        bundle_endpoint_profile "https_spiffe" {
            endpoint_spiffe_id = "spiffe://partner.com/spire/server"
        }
    }
}
```

### SPIRE Server Configuration (Partner Payments)

```hcl
# spire/partner/server.conf
server {
    bind_address = "0.0.0.0"
    bind_port = "8081"
    trust_domain = "partner.com"
    data_dir = "/opt/spire/data"
    log_level = "INFO"
}

plugins {
    DataStore "sql" {
        plugin_data {
            database_type = "postgres"
            connection_string = "postgresql://spire:password@postgres:5432/spire"
        }
    }

    KeyManager "disk" {
        plugin_data {
            keys_path = "/opt/spire/data/keys"
        }
    }

    NodeAttestor "join_token" {
        plugin_data {}
    }

    BundlePublisher "https" {
        plugin_data {
            bind_address = "0.0.0.0"
            bind_port = "8443"
            cert_path = "/opt/spire/conf/federation/cert.pem"
            key_path = "/opt/spire/conf/federation/key.pem"
        }
    }
}

federation {
    bundle_endpoint {
        address = "0.0.0.0"
        port = 8443
    }

    # Configure trust with acme-corp.io
    federates_with "acme-corp.io" {
        bundle_endpoint_url = "https://spire.acme-corp.io:8443"
        bundle_endpoint_profile "https_spiffe" {
            endpoint_spiffe_id = "spiffe://acme-corp.io/spire/server"
        }
    }

    # Configure trust with other-partner.io
    federates_with "other-partner.io" {
        bundle_endpoint_url = "https://spire.other-partner.io:8443"
        bundle_endpoint_profile "https_spiffe" {
            endpoint_spiffe_id = "spiffe://other-partner.io/spire/server"
        }
    }
}
```

## Authorization Policies

### ACME Corp Policy (Outbound Calls)

```rego
# policies/acme_authz.rego
package acme.authz

import rego.v1

default allow := false

# Allow billing agent to call federated payment agent
allow if {
    input.caller_spiffe_id == "spiffe://acme-corp.io/agent/billing"
    input.callee_spiffe_id == "spiffe://partner.com/agent/payment"
    input.action == "process_payment"

    # Additional checks
    is_valid_amount
    has_billing_id
}

# Verify amount is reasonable
is_valid_amount if {
    amount := to_number(input.context.payload.amount)
    amount > 0
    amount < 1000000  # Max $1M per transaction
}

# Require billing ID for audit trail
has_billing_id if {
    input.context.payload.billing_id != ""
}
```

### Partner Payments Policy (Inbound Calls)

```rego
# policies/partner_authz.rego
package partner.authz

import rego.v1

default allow := false

# Allow registered partners to call process_payment
allow if {
    input.action == "process_payment"
    is_registered_partner
    is_valid_request
}

# Check if caller is from registered federated domain
is_registered_partner if {
    caller_domain := extract_trust_domain(input.caller_spiffe_id)
    caller_domain in data.partner.registered_domains
}

# Validate request structure
is_valid_request if {
    input.context.payload.billing_id
    input.context.payload.customer_id
    input.context.payload.amount
    to_number(input.context.payload.amount) > 0
}

# Helper: Extract trust domain from SPIFFE ID
extract_trust_domain(spiffe_id) := domain if {
    parts := split(spiffe_id, "/")
    domain := parts[2]
}
```

### Policy Data (Partner Registration)

```json
{
  "partner": {
    "registered_domains": [
      "acme-corp.io",
      "other-partner.io"
    ],
    "partner_limits": {
      "acme-corp.io": {
        "max_transaction": 1000000,
        "daily_limit": 10000000,
        "rate_limit_per_minute": 100
      },
      "other-partner.io": {
        "max_transaction": 500000,
        "daily_limit": 5000000,
        "rate_limit_per_minute": 50
      }
    }
  }
}
```

## Running the Example

### Step 1: Set Up SPIRE Federation

```bash
# Start SPIRE servers for both domains
docker-compose -f docker-compose-acme.yaml up -d spire-server
docker-compose -f docker-compose-partner.yaml up -d spire-server

# Verify federation is established
docker-compose -f docker-compose-acme.yaml exec spire-server \
    /opt/spire/bin/spire-server bundle show -format spiffe

# Should show bundles for both acme-corp.io and partner.com
```

### Step 2: Register Workloads

```bash
# Register billing agent (ACME)
docker-compose -f docker-compose-acme.yaml exec spire-server \
    /opt/spire/bin/spire-server entry create \
    -spiffeID spiffe://acme-corp.io/agent/billing \
    -parentID spiffe://acme-corp.io/agent/spire-agent \
    -selector docker:label:com.docker.compose.service:billing

# Register payment agent (Partner)
docker-compose -f docker-compose-partner.yaml exec spire-server \
    /opt/spire/bin/spire-server entry create \
    -spiffeID spiffe://partner.com/agent/payment \
    -parentID spiffe://partner.com/agent/spire-agent \
    -selector docker:label:com.docker.compose.service:payment
```

### Step 3: Start Agents

```bash
# Start ACME agents
docker-compose -f docker-compose-acme.yaml up -d billing

# Start Partner agents
docker-compose -f docker-compose-partner.yaml up -d payment
```

### Step 4: Test Federated Call

```bash
# Call billing agent (which calls payment agent across trust domains)
agentweave call \
    --target spiffe://acme-corp.io/agent/billing \
    --capability process_billing \
    --data '{
        "customer_id": "cust-123",
        "amount": "99.99",
        "description": "Monthly subscription"
    }'
```

## Expected Output

### Successful Cross-Domain Call

```json
{
  "status": "completed",
  "messages": [
    {
      "role": "assistant",
      "parts": [
        {
          "type": "data",
          "data": {
            "billing_id": "bill-456",
            "payment_status": "completed",
            "transaction_id": "txn-789",
            "amount": "99.99",
            "processed_by": "spiffe://partner.com/agent/payment"
          }
        }
      ]
    }
  ]
}
```

### Audit Logs (ACME)

```json
{
  "timestamp": "2025-12-07T10:45:00Z",
  "level": "INFO",
  "message": "Processing billing",
  "customer_id": "cust-123",
  "amount": "99.99",
  "payment_agent": "spiffe://partner.com/agent/payment",
  "caller_domain": "acme-corp.io"
}
```

### Audit Logs (Partner)

```json
{
  "timestamp": "2025-12-07T10:45:01Z",
  "level": "INFO",
  "message": "Processing federated payment request",
  "caller_domain": "acme-corp.io",
  "caller_id": "spiffe://acme-corp.io/agent/billing",
  "amount": "99.99",
  "currency": "USD",
  "billing_id": "bill-456"
}
```

## Security Considerations

### Trust Establishment

Federation requires **explicit configuration**:

1. **Both SPIRE servers** must configure each other
2. **Trust bundles** must be exchanged (automatic via bundle endpoint)
3. **OPA policies** must explicitly allow cross-domain calls
4. **Audit logging** captures all federated interactions

### Defense in Depth

Multiple security layers:

- **SPIFFE Federation**: Cryptographic trust between domains
- **mTLS**: Encrypted, mutually authenticated transport
- **OPA Policies**: Fine-grained authorization (per-partner limits)
- **Audit Logs**: Complete audit trail of cross-domain calls
- **Rate Limiting**: Prevent abuse (policy-enforced)

### What Can Go Wrong

| Issue | Impact | Mitigation |
|-------|--------|------------|
| Trust bundle out of sync | Calls fail with verification error | Automatic bundle refresh (SPIRE) |
| Partner compromised | Malicious calls to your agents | Revoke federation, update policy |
| Policy misconfiguration | Unintended access | Policy review process, testing |
| Certificate expiry | Federation breaks | Monitor cert expiry, auto-rotation |

## Key Takeaways

### Federation is Explicit

Unlike same-domain calls, federation requires:

```yaml
allowed_trust_domains:
  - "acme-corp.io"    # Own domain
  - "partner.com"      # Federated partner (explicit!)
```

### SDK Handles Complexity

When you call a federated agent:

```python
await self.call_agent(
    target="spiffe://partner.com/agent/payment",
    ...
)
```

SDK automatically:
1. Detects cross-domain call
2. Fetches trust bundle for `partner.com`
3. Verifies peer SVID using federated trust
4. Enforces cross-domain OPA policies

### Audit Everything

Federated calls have **enhanced audit logging**:

- Source trust domain
- Target trust domain
- Caller SPIFFE ID
- All request parameters
- Authorization decision

## Next Steps

- **Multi-Cloud**: Deploy across AWS/GCP with federation
- **Compliance**: See [Healthcare Example](real-world/healthcare/) for HIPAA
- **Revocation**: Learn to revoke federation if partner compromised
- **Monitoring**: Set up alerts for federated call failures

---

**Complete Code**: [GitHub Repository](https://github.com/agentweave/examples/tree/main/federated)
