"""
Customer Support Triage System

Demonstrates:
- Dynamic agent routing based on content classification
- Multiple specialist agents with focused capabilities
- Observability integration (metrics tracking)
- Error handling with fallback routing
- RequestContext for end-to-end ticket tracking
"""

import asyncio
import re
from datetime import datetime, timezone
from typing import Optional

from agentweave import (
    SecureAgent,
    AgentConfig,
    capability,
    audit_log,
    get_current_context,
)


# Specialist routing map
SPECIALIST_ROUTES = {
    "billing": "spiffe://support.example/agent/billing",
    "technical": "spiffe://support.example/agent/technical",
    "account": "spiffe://support.example/agent/account",
}

# Classification keywords
CLASSIFICATION_RULES = {
    "billing": [
        "invoice", "payment", "charge", "refund", "subscription",
        "pricing", "bill", "credit", "cost", "fee",
    ],
    "technical": [
        "error", "bug", "crash", "slow", "api", "integration",
        "timeout", "500", "connection", "deploy", "certificate",
    ],
    "account": [
        "password", "login", "access", "permission", "role",
        "user", "profile", "settings", "mfa", "locked",
    ],
}


class TriageAgent(SecureAgent):
    """
    Routes customer support tickets to the appropriate specialist agent.

    Capabilities:
    - submit_ticket: Accept and classify a support ticket
    - get_ticket_status: Check status of a submitted ticket
    - get_metrics: Retrieve triage metrics
    """

    def __init__(self, config: AgentConfig, **kwargs):
        super().__init__(config=config, **kwargs)
        self._tickets: dict[str, dict] = {}
        self._metrics = {
            "total_tickets": 0,
            "by_category": {"billing": 0, "technical": 0, "account": 0, "general": 0},
            "avg_classification_confidence": 0.0,
        }

    def _classify(self, subject: str, description: str) -> tuple[str, float]:
        """
        Classify a ticket into a category.
        Returns (category, confidence_score).
        """
        text = f"{subject} {description}".lower()
        scores = {}

        for category, keywords in CLASSIFICATION_RULES.items():
            score = sum(1 for kw in keywords if kw in text)
            scores[category] = score

        if not any(scores.values()):
            return "general", 0.0

        best_category = max(scores, key=scores.get)
        total_matches = sum(scores.values())
        confidence = scores[best_category] / total_matches if total_matches > 0 else 0.0

        return best_category, round(confidence, 2)

    @capability("submit_ticket")
    @audit_log()
    async def submit_ticket(
        self,
        subject: str,
        description: str,
        customer_id: str,
        priority: str = "normal",
    ) -> dict:
        """
        Accept a support ticket, classify it, and route to specialist.
        """
        ctx = get_current_context()
        ticket_id = f"TKT-{self._metrics['total_tickets'] + 1:05d}"

        # Classify the ticket
        category, confidence = self._classify(subject, description)

        # Create ticket record
        ticket = {
            "ticket_id": ticket_id,
            "subject": subject,
            "description": description,
            "customer_id": customer_id,
            "priority": priority,
            "category": category,
            "confidence": confidence,
            "status": "classifying",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "submitted_by": ctx.caller_id if ctx else "direct",
        }
        self._tickets[ticket_id] = ticket

        # Update metrics
        self._metrics["total_tickets"] += 1
        self._metrics["by_category"][category] = (
            self._metrics["by_category"].get(category, 0) + 1
        )

        # Route to specialist if we have one
        specialist_result = None
        if category in SPECIALIST_ROUTES:
            try:
                specialist_result = await self.call_agent(
                    target=SPECIALIST_ROUTES[category],
                    task_type="handle_ticket",
                    payload={
                        "ticket_id": ticket_id,
                        "subject": subject,
                        "description": description,
                        "customer_id": customer_id,
                        "priority": priority,
                        "category": category,
                    },
                )
                ticket["status"] = "routed"
                ticket["routed_to"] = category
            except Exception as e:
                ticket["status"] = "routing_failed"
                ticket["routing_error"] = str(e)
                specialist_result = {"error": f"Failed to route: {e}"}
        else:
            ticket["status"] = "unrouted"
            ticket["routed_to"] = "general_queue"

        return {
            "ticket_id": ticket_id,
            "category": category,
            "confidence": confidence,
            "status": ticket["status"],
            "specialist_response": specialist_result,
        }

    @capability("get_ticket_status")
    async def get_ticket_status(self, ticket_id: str) -> dict:
        """Get the current status of a ticket."""
        ticket = self._tickets.get(ticket_id)
        if not ticket:
            return {"error": "Ticket not found", "ticket_id": ticket_id}
        return ticket

    @capability("get_metrics")
    async def get_metrics(self) -> dict:
        """Get triage metrics."""
        return self._metrics


class BillingAgent(SecureAgent):
    """Handles billing-related support tickets."""

    @capability("handle_ticket")
    @audit_log()
    async def handle_ticket(
        self,
        ticket_id: str,
        subject: str,
        description: str,
        customer_id: str,
        priority: str = "normal",
        category: str = "billing",
    ) -> dict:
        """Process a billing support ticket."""
        # Simulate billing-specific processing
        actions = []
        desc_lower = description.lower()

        if "refund" in desc_lower:
            actions.append({
                "type": "refund_review",
                "status": "initiated",
                "note": "Refund request queued for review",
            })
        if "invoice" in desc_lower:
            actions.append({
                "type": "invoice_lookup",
                "status": "completed",
                "note": f"Retrieved invoice history for customer {customer_id}",
            })
        if not actions:
            actions.append({
                "type": "general_billing",
                "status": "assigned",
                "note": "Assigned to billing team for review",
            })

        return {
            "ticket_id": ticket_id,
            "handler": "billing_agent",
            "status": "processing",
            "actions": actions,
            "estimated_resolution": "24 hours" if priority == "normal" else "4 hours",
        }


class TechnicalAgent(SecureAgent):
    """Handles technical support tickets."""

    @capability("handle_ticket")
    @audit_log()
    async def handle_ticket(
        self,
        ticket_id: str,
        subject: str,
        description: str,
        customer_id: str,
        priority: str = "normal",
        category: str = "technical",
    ) -> dict:
        """Process a technical support ticket."""
        # Simulate technical diagnosis
        diagnostics = []
        desc_lower = description.lower()

        if "error" in desc_lower or "500" in desc_lower:
            diagnostics.append({
                "check": "error_logs",
                "result": "Reviewing recent error logs",
            })
        if "slow" in desc_lower or "timeout" in desc_lower:
            diagnostics.append({
                "check": "performance",
                "result": "Running performance diagnostics",
            })
        if "certificate" in desc_lower or "tls" in desc_lower:
            diagnostics.append({
                "check": "certificates",
                "result": "Checking certificate validity and chain",
            })
        if not diagnostics:
            diagnostics.append({
                "check": "general",
                "result": "Assigned to engineering for investigation",
            })

        return {
            "ticket_id": ticket_id,
            "handler": "technical_agent",
            "status": "investigating",
            "diagnostics": diagnostics,
            "severity": "high" if priority == "urgent" else "medium",
        }


class AccountAgent(SecureAgent):
    """Handles account-related support tickets."""

    @capability("handle_ticket")
    @audit_log()
    async def handle_ticket(
        self,
        ticket_id: str,
        subject: str,
        description: str,
        customer_id: str,
        priority: str = "normal",
        category: str = "account",
    ) -> dict:
        """Process an account support ticket."""
        actions = []
        desc_lower = description.lower()

        if "locked" in desc_lower or "password" in desc_lower:
            actions.append({
                "type": "account_unlock",
                "status": "pending_verification",
                "note": "Identity verification required before unlock",
            })
        if "permission" in desc_lower or "access" in desc_lower:
            actions.append({
                "type": "access_review",
                "status": "in_progress",
                "note": f"Reviewing access permissions for {customer_id}",
            })
        if "mfa" in desc_lower:
            actions.append({
                "type": "mfa_reset",
                "status": "pending_verification",
                "note": "MFA reset requires manager approval",
            })
        if not actions:
            actions.append({
                "type": "general_account",
                "status": "assigned",
                "note": "Assigned to account management team",
            })

        return {
            "ticket_id": ticket_id,
            "handler": "account_agent",
            "status": "processing",
            "actions": actions,
            "security_review_required": any(
                kw in desc_lower for kw in ["password", "mfa", "locked", "access"]
            ),
        }


async def demo():
    """Demonstrate the triage system with sample tickets."""
    print("Customer Support Triage System")
    print("=" * 50)
    print()

    # Create triage agent using mock providers so the demo runs
    # without SPIFFE/SPIRE infrastructure.
    from agentweave.testing import MockIdentityProvider, MockAuthorizationProvider

    config = AgentConfig(
        name="triage",
        trust_domain="support.example",
        identity_provider="mtls-static",
        authz_provider="allow-all",
    )
    identity = MockIdentityProvider(
        spiffe_id="spiffe://support.example/agent/triage"
    )
    authz = MockAuthorizationProvider(default_allow=True)
    triage = TriageAgent(config, identity=identity, authz=authz)

    # Demonstrate classification
    test_tickets = [
        (
            "Invoice discrepancy",
            "I was charged twice on my last invoice for the premium plan",
            "billing",
        ),
        (
            "API returning 500 errors",
            "Our integration is getting 500 errors on the /api/v2/agents endpoint",
            "technical",
        ),
        (
            "Account locked out",
            "I can't login to my account after too many password attempts",
            "account",
        ),
        (
            "General inquiry",
            "What features does the enterprise plan include?",
            "general",
        ),
    ]

    for subject, description, expected in test_tickets:
        category, confidence = triage._classify(subject, description)
        status = "CORRECT" if category == expected else f"MISMATCH (expected {expected})"
        print(f"  Ticket: {subject}")
        print(f"  -> Category: {category} (confidence: {confidence}) [{status}]")
        print()


if __name__ == "__main__":
    asyncio.run(demo())
