"""
Secure Multi-Stage Data Pipeline

Demonstrates:
- Chain-of-custody: each stage can only call the next stage
- @requires_peer for strict caller verification
- @audit_log for financial compliance
- Error handling and propagation
- RequestContext for tracing data lineage
"""
import asyncio
from datetime import datetime, timezone
from typing import Optional
from agentweave import (
    SecureAgent, AgentConfig,
    capability, requires_peer, audit_log,
    get_current_context,
)


class IngestAgent(SecureAgent):
    """
    Stage 1: Accepts raw transaction data from authorized clients.

    Validates basic structure and forwards to the validation stage.
    Only accepts data from authorized submitters within the
    finance.example trust domain.
    """

    @capability("ingest", description="Accept raw transactions and forward to validation")
    @audit_log(level="info")
    async def ingest(self, transactions: list[dict],
                     source: str = "unknown") -> dict:
        """Accept raw transactions and forward to validation."""
        ctx = get_current_context()
        batch_id = f"batch_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        # Basic structural validation
        accepted = []
        rejected = []
        for i, txn in enumerate(transactions):
            if "amount" in txn and "account" in txn:
                txn["batch_id"] = batch_id
                txn["ingested_at"] = datetime.now(timezone.utc).isoformat()
                txn["source"] = source
                accepted.append(txn)
            else:
                rejected.append({
                    "index": i,
                    "reason": "Missing required fields: amount, account",
                })

        # Forward accepted transactions to validation stage
        if accepted:
            validation_result = await self.call_agent(
                target="spiffe://finance.example/agent/validator",
                task_type="validate",
                payload={
                    "batch_id": batch_id,
                    "transactions": accepted,
                },
            )
        else:
            validation_result = {"status": "skipped", "reason": "No valid transactions"}

        return {
            "batch_id": batch_id,
            "total_received": len(transactions),
            "accepted": len(accepted),
            "rejected": len(rejected),
            "rejections": rejected,
            "validation": validation_result,
        }


class ValidateAgent(SecureAgent):
    """
    Stage 2: Validates transactions against business rules.

    Only accepts calls from the Ingest Agent (chain-of-custody).
    """

    AMOUNT_LIMIT = 1_000_000  # Flag transactions over $1M

    @capability("validate", description="Validate transactions against business rules")
    @requires_peer("spiffe://finance.example/agent/ingest*")
    @audit_log(level="info")
    async def validate(self, batch_id: str,
                       transactions: list[dict]) -> dict:
        """Validate transactions against business rules."""
        valid = []
        flagged = []
        invalid = []

        for txn in transactions:
            amount = txn.get("amount", 0)

            # Business rule: amount must be positive
            if amount <= 0:
                invalid.append({**txn, "validation_error": "Amount must be positive"})
                continue

            # Business rule: flag high-value transactions
            if amount > self.AMOUNT_LIMIT:
                flagged.append({**txn, "flag": "HIGH_VALUE", "requires_review": True})
                continue

            txn["validated_at"] = datetime.now(timezone.utc).isoformat()
            txn["validation_status"] = "passed"
            valid.append(txn)

        # Forward valid transactions to enrichment stage
        if valid:
            enrichment_result = await self.call_agent(
                target="spiffe://finance.example/agent/enricher",
                task_type="enrich",
                payload={
                    "batch_id": batch_id,
                    "transactions": valid,
                },
            )
        else:
            enrichment_result = {"status": "skipped", "reason": "No valid transactions"}

        return {
            "batch_id": batch_id,
            "valid": len(valid),
            "flagged": len(flagged),
            "invalid": len(invalid),
            "flagged_transactions": flagged,
            "enrichment": enrichment_result,
        }


class EnrichAgent(SecureAgent):
    """
    Stage 3: Enriches transactions with additional metadata.

    Only accepts calls from the Validate Agent.
    """

    # Simulated account metadata
    ACCOUNT_DATA = {
        "ACC001": {"name": "Acme Corp", "tier": "enterprise", "country": "US"},
        "ACC002": {"name": "Global Trade Ltd", "tier": "standard", "country": "UK"},
        "ACC003": {"name": "Tech Startup Inc", "tier": "startup", "country": "US"},
    }

    @capability("enrich", description="Enrich transactions with account metadata")
    @requires_peer("spiffe://finance.example/agent/validator")
    @audit_log(level="info")
    async def enrich(self, batch_id: str,
                     transactions: list[dict]) -> dict:
        """Enrich transactions with account metadata."""
        enriched = []
        for txn in transactions:
            account = txn.get("account", "")
            account_info = self.ACCOUNT_DATA.get(account, {
                "name": "Unknown", "tier": "unknown", "country": "unknown",
            })

            txn["enrichment"] = {
                "account_name": account_info["name"],
                "account_tier": account_info["tier"],
                "country": account_info["country"],
                "enriched_at": datetime.now(timezone.utc).isoformat(),
            }
            enriched.append(txn)

        # Forward enriched transactions to storage
        store_result = await self.call_agent(
            target="spiffe://finance.example/agent/store",
            task_type="store",
            payload={
                "batch_id": batch_id,
                "transactions": enriched,
            },
        )

        return {
            "batch_id": batch_id,
            "enriched": len(enriched),
            "storage": store_result,
        }


class StoreAgent(SecureAgent):
    """
    Stage 4: Persists transactions to secure storage.

    Only accepts calls from the Enrich Agent.
    Terminal stage in the pipeline.
    """

    def __init__(self, config=None, identity=None, authz=None, transport=None):
        super().__init__(config=config, identity=identity, authz=authz, transport=transport)
        self._stored_batches: dict[str, list] = {}

    @capability("store", description="Persist enriched transactions to storage")
    @requires_peer("spiffe://finance.example/agent/enricher")
    @audit_log(level="info")
    async def store(self, batch_id: str,
                    transactions: list[dict]) -> dict:
        """Persist enriched transactions to storage."""
        # Add storage metadata
        for txn in transactions:
            txn["stored_at"] = datetime.now(timezone.utc).isoformat()
            txn["storage_status"] = "persisted"

        # Store the batch (in production, write to database)
        self._stored_batches[batch_id] = transactions

        return {
            "batch_id": batch_id,
            "stored_count": len(transactions),
            "status": "persisted",
        }

    @capability("query", description="Query stored transactions")
    @audit_log(level="info")
    async def query(self, batch_id: Optional[str] = None) -> dict:
        """Query stored transactions."""
        if batch_id:
            transactions = self._stored_batches.get(batch_id, [])
            return {
                "batch_id": batch_id,
                "transactions": transactions,
                "count": len(transactions),
            }
        return {
            "batches": list(self._stored_batches.keys()),
            "total_batches": len(self._stored_batches),
            "total_transactions": sum(
                len(txns) for txns in self._stored_batches.values()
            ),
        }


async def main():
    """Start the pipeline (would normally be separate processes)."""
    print("Data Pipeline Example")
    print("=" * 50)
    print("In production, each agent runs as a separate service.")
    print("This example shows the agent definitions.")
    print()
    print("Pipeline flow:")
    print("  Client -> Ingest -> Validate -> Enrich -> Store")
    print()
    print("Chain-of-custody enforcement:")
    print("  - Ingest: accepts from authorized clients")
    print("  - Validate: only accepts from Ingest agent")
    print("  - Enrich: only accepts from Validate agent")
    print("  - Store: only accepts from Enrich agent")


if __name__ == "__main__":
    asyncio.run(main())
