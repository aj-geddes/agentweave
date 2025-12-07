---
layout: page
title: Financial Services Use Case
permalink: /examples/real-world/financial-services/
parent: Real-World Scenarios
grand_parent: Examples Overview
nav_order: 1
---

# Financial Services: Compliant Trading System

**Industry**: Financial Services
**Scenario**: High-frequency trading platform with regulatory compliance
**Compliance**: SEC regulations, SOC 2, audit requirements
**Time to Complete**: 60 minutes

## Business Problem

**ACME Trading** operates a high-frequency trading platform that must:

1. **Execute trades** across multiple exchanges in milliseconds
2. **Perform risk checks** before every trade (capital requirements, position limits)
3. **Maintain compliance** with SEC regulations (Rule 15c3-5 - Market Access Rule)
4. **Provide audit trails** for all trades and risk decisions
5. **Implement maker-checker** for high-value trades (dual authorization)
6. **Generate reports** for regulatory filings

### Regulatory Requirements

| Requirement | Regulation | Implementation |
|-------------|-----------|----------------|
| Pre-trade risk checks | SEC 15c3-5 | Risk Agent validates before execution |
| Audit trail | SOC 2, SEC | Immutable logs of all decisions |
| Maker-checker | Internal policy | Approval workflow for large trades |
| Position limits | Exchange rules | Real-time position tracking |
| Capital requirements | SEC Net Capital Rule | Capital check before trade |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Trading Platform                          │
└─────────────────────────────────────────────────────────────┘

Client Order
    │
    ▼
┌─────────────────┐
│  Order Router   │  ← Routes orders, initial validation
│     Agent       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Risk Agent    │  ← Pre-trade risk checks (MANDATORY)
│                 │    • Capital requirements
│                 │    • Position limits
│                 │    • Concentration risk
│                 │    • Regulatory checks
└────────┬────────┘
         │
         ├─→ if high_value ──→ ┌──────────────────┐
         │                     │ Approval Agent   │
         │                     │ (Maker-Checker)  │
         │                     └──────────────────┘
         │                              │
         ▼                              │
┌─────────────────┐            ┌────────▼────────┐
│Execution Agent  │◄───────────│  Compliance     │
│                 │            │     Agent       │
│ • Send to       │            │                 │
│   exchange      │            │ • Log decision  │
│ • Get fills     │            │ • Generate      │
│ • Update        │            │   reports       │
│   positions     │            └─────────────────┘
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│Position Tracker │  ← Real-time position/P&L tracking
│     Agent       │
└─────────────────┘

All communication:
- mTLS with SPIFFE
- OPA policy enforcement
- Immutable audit logs
- Distributed tracing
```

## Compliance Architecture

```
                   ┌─────────────────────────┐
                   │   Audit Log Store       │
                   │   (Immutable, S3)       │
                   └─────────────────────────┘
                              ▲
                              │ All decisions logged
                              │
         ┌────────────────────┼────────────────────┐
         │                    │                    │
    ┌────▼────┐         ┌─────▼─────┐      ┌──────▼──────┐
    │  Risk   │         │ Execution │      │  Approval   │
    │  Check  │         │   Event   │      │   Event     │
    └─────────┘         └───────────┘      └─────────────┘

Each log entry contains:
- Timestamp (nanosecond precision)
- Agent SPIFFE ID (who made decision)
- Input data (trade parameters)
- Decision (allow/deny)
- Reasoning (why)
- Cryptographic signature
```

## Complete Code

### Order Router Agent

```python
# order_router_agent.py
"""
Order Router Agent - Entry point for all trade orders.

Responsibilities:
- Validate order format
- Route to risk agent for approval
- Track order lifecycle
"""

import asyncio
from typing import Dict, Any
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, validator

from agentweave import SecureAgent, capability
from agentweave.types import TaskResult, Message, DataPart
from agentweave.exceptions import AgentCallError


class Order(BaseModel):
    """Trade order."""
    order_id: str
    symbol: str
    side: str  # BUY, SELL
    quantity: int
    order_type: str  # MARKET, LIMIT
    price: Decimal = None
    account_id: str
    trader_id: str

    @validator('side')
    def validate_side(cls, v):
        if v not in ['BUY', 'SELL']:
            raise ValueError('side must be BUY or SELL')
        return v

    @validator('quantity')
    def validate_quantity(cls, v):
        if v <= 0:
            raise ValueError('quantity must be positive')
        return v


class OrderRouterAgent(SecureAgent):
    """Routes and tracks trade orders."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.risk_agent = "spiffe://agentweave.io/agent/risk"
        self.compliance_agent = "spiffe://agentweave.io/agent/compliance"

        self._orders: Dict[str, Order] = {}

    @capability("submit_order")
    async def submit_order(self, order_data: Dict[str, Any]) -> TaskResult:
        """
        Submit trade order.

        Workflow:
        1. Validate order
        2. Log to compliance
        3. Send to risk agent
        4. Return decision
        """
        try:
            # Validate order
            order = Order(**order_data)
            self._orders[order.order_id] = order

            # Log order submission to compliance
            await self._log_compliance_event(
                event_type="order_submitted",
                order=order
            )

            self.logger.info(
                "Order submitted",
                extra={
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "side": order.side,
                    "quantity": order.quantity,
                    "trader_id": order.trader_id
                }
            )

            # Send to risk agent for approval
            # This is where SEC 15c3-5 compliance is enforced
            risk_result = await self.call_agent(
                target=self.risk_agent,
                task_type="check_risk",
                payload={
                    "order": order.dict(),
                    "submitted_at": datetime.utcnow().isoformat(),
                    "submitter": str(self.spiffe_id)
                },
                timeout=1.0  # Risk checks must be fast (sub-second)
            )

            if risk_result.status != "completed":
                # Risk check failed - MUST NOT execute trade
                await self._log_compliance_event(
                    event_type="order_rejected_risk",
                    order=order,
                    reason=risk_result.error
                )

                return TaskResult(
                    status="failed",
                    error=f"Risk check failed: {risk_result.error}"
                )

            risk_data = risk_result.artifacts[0]["data"]

            if not risk_data["approved"]:
                await self._log_compliance_event(
                    event_type="order_rejected_risk",
                    order=order,
                    reason=risk_data["reason"]
                )

                return TaskResult(
                    status="failed",
                    error=f"Order rejected: {risk_data['reason']}"
                )

            # Risk approved - return success
            # Execution agent will pick up from here
            return TaskResult(
                status="completed",
                messages=[Message(
                    role="assistant",
                    parts=[DataPart(data={
                        "order_id": order.order_id,
                        "status": "risk_approved",
                        "risk_check_id": risk_data["check_id"]
                    })]
                )]
            )

        except Exception as e:
            self.logger.error(f"Order submission failed: {e}")
            return TaskResult(
                status="failed",
                error=f"Failed to submit order: {e}"
            )

    async def _log_compliance_event(
        self,
        event_type: str,
        order: Order,
        reason: str = None
    ):
        """Log event to compliance agent (fire and forget)."""
        try:
            await self.call_agent(
                target=self.compliance_agent,
                task_type="log_event",
                payload={
                    "event_type": event_type,
                    "order_id": order.order_id,
                    "symbol": order.symbol,
                    "trader_id": order.trader_id,
                    "reason": reason,
                    "timestamp": datetime.utcnow().isoformat()
                },
                timeout=5.0
            )
        except Exception as e:
            # Compliance logging must never fail the trade
            # But we must alert if it fails
            self.logger.critical(
                f"COMPLIANCE LOGGING FAILED: {e}",
                extra={"order_id": order.order_id}
            )


async def main():
    agent = OrderRouterAgent.from_config("config/order_router.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Risk Agent

```python
# risk_agent.py
"""
Risk Agent - Pre-trade risk checks (SEC 15c3-5 compliance).

CRITICAL: This agent implements Market Access Rule compliance.
All risk checks MUST complete before trade execution.
"""

import asyncio
from typing import Dict, Any
from decimal import Decimal
from datetime import datetime
import uuid

from agentweave import SecureAgent, capability, requires_peer
from agentweave.types import TaskResult, Message, DataPart


class RiskAgent(SecureAgent):
    """
    Performs pre-trade risk checks.

    SEC 15c3-5 (Market Access Rule) requires:
    - Credit limits
    - Capital thresholds
    - Regulatory requirements
    - Position concentration limits
    - Prohibited securities
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.approval_agent = "spiffe://agentweave.io/agent/approval"

        # Risk limits (in production, load from database)
        self.account_limits = {
            "ACC-001": {
                "max_position_value": Decimal("10000000"),  # $10M
                "max_order_value": Decimal("1000000"),      # $1M
                "max_concentration": 0.20  # 20% of portfolio
            }
        }

        # High-value threshold requiring approval
        self.high_value_threshold = Decimal("500000")  # $500K

    @capability("check_risk")
    @requires_peer("spiffe://agentweave.io/agent/order-router")
    async def check_risk(
        self,
        order: Dict[str, Any],
        submitted_at: str,
        submitter: str
    ) -> TaskResult:
        """
        Perform comprehensive pre-trade risk checks.

        SEC 15c3-5 Requirements:
        1. Financial/regulatory risk checks BEFORE order sent to market
        2. Must prevent erroneous orders
        3. Must enforce credit limits
        4. Must document all decisions
        """
        check_id = str(uuid.uuid4())

        self.logger.info(
            "Performing risk check",
            extra={
                "check_id": check_id,
                "order_id": order["order_id"],
                "symbol": order["symbol"],
                "quantity": order["quantity"]
            }
        )

        # Calculate order value
        order_value = await self._calculate_order_value(order)

        # Run all risk checks
        checks = {
            "capital": await self._check_capital(order, order_value),
            "position_limit": await self._check_position_limit(order, order_value),
            "concentration": await self._check_concentration(order),
            "prohibited": await self._check_prohibited_securities(order),
            "regulatory": await self._check_regulatory(order)
        }

        # All checks must pass
        all_passed = all(check["passed"] for check in checks.values())

        if not all_passed:
            failed_checks = [
                name for name, check in checks.items()
                if not check["passed"]
            ]

            reason = f"Failed checks: {', '.join(failed_checks)}"

            self.logger.warning(
                "Risk check FAILED",
                extra={
                    "check_id": check_id,
                    "order_id": order["order_id"],
                    "failed_checks": failed_checks,
                    "checks": checks
                }
            )

            return TaskResult(
                status="completed",
                messages=[Message(
                    role="assistant",
                    parts=[DataPart(data={
                        "check_id": check_id,
                        "approved": False,
                        "reason": reason,
                        "checks": checks
                    })]
                )],
                artifacts=[
                    {
                        "type": "risk_check",
                        "data": {
                            "check_id": check_id,
                            "approved": False,
                            "reason": reason,
                            "checks": checks
                        }
                    }
                ]
            )

        # High-value trades require approval
        if order_value > self.high_value_threshold:
            self.logger.info(
                "High-value trade requires approval",
                extra={
                    "check_id": check_id,
                    "order_value": str(order_value),
                    "threshold": str(self.high_value_threshold)
                }
            )

            # Request approval (maker-checker)
            approval_result = await self.call_agent(
                target=self.approval_agent,
                task_type="request_approval",
                payload={
                    "order": order,
                    "order_value": str(order_value),
                    "risk_check_id": check_id
                },
                timeout=300.0  # 5 minutes for human approval
            )

            if approval_result.status != "completed":
                return TaskResult(
                    status="completed",
                    messages=[Message(
                        role="assistant",
                        parts=[DataPart(data={
                            "check_id": check_id,
                            "approved": False,
                            "reason": "Approval required but not granted",
                            "checks": checks
                        })]
                    )],
                    artifacts=[...]
                )

        # All checks passed
        self.logger.info(
            "Risk check PASSED",
            extra={"check_id": check_id, "order_id": order["order_id"]}
        )

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data={
                    "check_id": check_id,
                    "approved": True,
                    "reason": "All risk checks passed",
                    "checks": checks
                })]
            )],
            artifacts=[
                {
                    "type": "risk_check",
                    "data": {
                        "check_id": check_id,
                        "approved": True,
                        "checks": checks
                    }
                }
            ]
        )

    async def _calculate_order_value(self, order: Dict[str, Any]) -> Decimal:
        """Calculate order value."""
        # In production, fetch real-time price
        if order["order_type"] == "LIMIT" and order["price"]:
            price = Decimal(str(order["price"]))
        else:
            # Get market price
            price = Decimal("100.00")  # Placeholder

        quantity = Decimal(str(order["quantity"]))
        return price * quantity

    async def _check_capital(
        self,
        order: Dict[str, Any],
        order_value: Decimal
    ) -> Dict[str, Any]:
        """Check capital requirements (SEC Net Capital Rule)."""
        # In production, check real capital
        available_capital = Decimal("50000000")  # $50M

        passed = order_value <= available_capital

        return {
            "passed": passed,
            "available_capital": str(available_capital),
            "required_capital": str(order_value)
        }

    async def _check_position_limit(
        self,
        order: Dict[str, Any],
        order_value: Decimal
    ) -> Dict[str, Any]:
        """Check position limits."""
        account_id = order["account_id"]
        limits = self.account_limits.get(
            account_id,
            {"max_order_value": Decimal("100000")}
        )

        max_order_value = limits["max_order_value"]
        passed = order_value <= max_order_value

        return {
            "passed": passed,
            "order_value": str(order_value),
            "max_order_value": str(max_order_value)
        }

    async def _check_concentration(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Check concentration limits."""
        # In production, calculate real portfolio concentration
        return {"passed": True, "concentration": "0.05"}

    async def _check_prohibited_securities(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Check if security is prohibited."""
        # In production, check prohibited list
        prohibited = []
        passed = order["symbol"] not in prohibited

        return {"passed": passed}

    async def _check_regulatory(self, order: Dict[str, Any]) -> Dict[str, Any]:
        """Check regulatory requirements."""
        # Check for short-sale rules, circuit breakers, etc.
        return {"passed": True}


async def main():
    agent = RiskAgent.from_config("config/risk.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Compliance Agent

```python
# compliance_agent.py
"""
Compliance Agent - Immutable audit logging and reporting.

Responsibilities:
- Log all trading decisions
- Generate regulatory reports
- Provide audit trail access
- Alert on compliance violations
"""

import asyncio
from typing import Dict, Any
from datetime import datetime
import json
import hashlib

from agentweave import SecureAgent, capability
from agentweave.types import TaskResult, Message, DataPart


class ComplianceAgent(SecureAgent):
    """
    Maintains immutable audit logs for compliance.

    All events are:
    - Cryptographically signed
    - Stored in append-only log
    - Replicated to S3 (in production)
    - Indexed for queries
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # In production, use S3 + DynamoDB
        self._audit_log = []

    @capability("log_event")
    async def log_event(
        self,
        event_type: str,
        order_id: str = None,
        **kwargs
    ) -> TaskResult:
        """
        Log compliance event (immutable).

        Events include:
        - order_submitted
        - order_rejected_risk
        - order_approved
        - trade_executed
        - trade_failed
        """
        timestamp = datetime.utcnow()

        # Create audit record
        record = {
            "event_id": self._generate_event_id(),
            "event_type": event_type,
            "timestamp": timestamp.isoformat(),
            "order_id": order_id,
            "caller": self.context.caller_spiffe_id,
            "data": kwargs,
            "sequence": len(self._audit_log)
        }

        # Add cryptographic signature
        record["signature"] = self._sign_record(record)

        # Append to immutable log
        self._audit_log.append(record)

        self.logger.info(
            "Compliance event logged",
            extra={
                "event_id": record["event_id"],
                "event_type": event_type
            }
        )

        # In production:
        # - Write to S3 (append-only bucket)
        # - Index in DynamoDB for queries
        # - Alert if compliance violation detected

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data={
                    "event_id": record["event_id"],
                    "sequence": record["sequence"]
                })]
            )]
        )

    @capability("query_audit_log")
    async def query_audit_log(
        self,
        order_id: str = None,
        start_time: str = None,
        end_time: str = None,
        event_type: str = None
    ) -> TaskResult:
        """
        Query audit log.

        Used for:
        - Regulatory inquiries
        - Internal audits
        - Incident investigation
        """
        # Filter records
        results = self._audit_log.copy()

        if order_id:
            results = [r for r in results if r.get("order_id") == order_id]

        if event_type:
            results = [r for r in results if r["event_type"] == event_type]

        # In production, query DynamoDB with proper indexes

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data={
                    "total_records": len(results),
                    "records": results[:100]  # Limit for demo
                })]
            )]
        )

    @capability("generate_report")
    async def generate_report(
        self,
        report_type: str,
        start_date: str,
        end_date: str
    ) -> TaskResult:
        """
        Generate regulatory report.

        Report types:
        - daily_trading_activity
        - risk_violations
        - rejected_orders
        - high_value_trades
        """
        # In production, aggregate data and generate report
        report = {
            "report_type": report_type,
            "start_date": start_date,
            "end_date": end_date,
            "generated_at": datetime.utcnow().isoformat(),
            "total_events": len(self._audit_log),
            "summary": {}
        }

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data=report)]
            )]
        )

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        import uuid
        return str(uuid.uuid4())

    def _sign_record(self, record: Dict[str, Any]) -> str:
        """
        Cryptographically sign record.

        In production:
        - Use HSM for signing
        - Include in blockchain/merkle tree
        - Verify chain integrity
        """
        # Simplified: hash the record
        record_json = json.dumps(record, sort_keys=True)
        return hashlib.sha256(record_json.encode()).hexdigest()


async def main():
    agent = ComplianceAgent.from_config("config/compliance.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

## OPA Policies for Compliance

```rego
# policies/trading_authz.rego
package trading.authz

import rego.v1

default allow := false

# Order router can submit to risk agent
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/order-router"
    input.callee_spiffe_id == "spiffe://agentweave.io/agent/risk"
    input.action == "check_risk"
}

# Risk agent can request approval
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/risk"
    input.callee_spiffe_id == "spiffe://agentweave.io/agent/approval"
    input.action == "request_approval"
}

# All agents can log to compliance
allow if {
    startswith(input.caller_spiffe_id, "spiffe://agentweave.io/agent/")
    input.callee_spiffe_id == "spiffe://agentweave.io/agent/compliance"
    input.action in ["log_event", "query_audit_log"]
}

# Only auditors can generate reports
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/auditor"
    input.callee_spiffe_id == "spiffe://agentweave.io/agent/compliance"
    input.action == "generate_report"
}

# CRITICAL: Execution agent can ONLY execute if risk approved
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/execution"
    input.callee_spiffe_id == "spiffe://agentweave.io/agent/exchange"
    has_risk_approval
}

has_risk_approval if {
    input.context.risk_check_id
    # In production, verify risk check in database
    true
}
```

## Running the Example

```bash
# Start infrastructure
docker-compose up -d

# Submit test order
agentweave call \
    --target spiffe://agentweave.io/agent/order-router \
    --capability submit_order \
    --data '{
        "order_data": {
            "order_id": "ORD-001",
            "symbol": "AAPL",
            "side": "BUY",
            "quantity": 1000,
            "order_type": "MARKET",
            "account_id": "ACC-001",
            "trader_id": "TRADER-123"
        }
    }'

# Query audit log
agentweave call \
    --target spiffe://agentweave.io/agent/compliance \
    --capability query_audit_log \
    --data '{"order_id": "ORD-001"}'
```

## Key Takeaways

### Compliance as Code

OPA policies enforce SEC 15c3-5:

```rego
# Execution ONLY if risk approved
allow if {
    input.action == "execute_trade"
    has_risk_approval
}
```

### Immutable Audit Trail

Every decision is logged:

```
[order_submitted] → [risk_check] → [approval_requested] → [approved] → [executed]
         ↓               ↓                  ↓                ↓             ↓
    Compliance      Compliance        Compliance       Compliance    Compliance
```

### Zero-Trust Trading

- **Every agent** has SPIFFE identity
- **Every call** requires mTLS
- **Every action** checked by OPA
- **Every decision** logged immutably

## Compliance Benefits

| Requirement | Traditional | AgentWeave |
|-------------|-------------|------------|
| **Audit Trail** | Manual logging, gaps possible | Automatic, immutable, complete |
| **Authorization** | Application code, scattered | OPA policies, centralized |
| **Identity** | API keys, easily compromised | SPIFFE, cryptographic |
| **Evidence** | Hard to prove compliance | Complete audit trail |

---

**Complete Code**: [GitHub Repository](https://github.com/agentweave/examples/tree/main/real-world/financial-services)
