---
layout: page
title: Data Processing Pipeline
permalink: /examples/data-pipeline/
parent: Examples Overview
nav_order: 4
---

# Data Processing Pipeline Example

**Complexity:** Intermediate
**Time to Complete:** 40 minutes
**Prerequisites:** Understanding of ETL patterns, basic data processing

This example demonstrates a real-world data processing pipeline using the agent pattern. Three specialized agents (Ingester, Processor, Storage) work together to process streaming data with security and observability built-in.

## What You'll Learn

- Pipeline pattern with agent orchestration
- Stream processing with agents
- Error handling and retry logic
- Data validation and transformation
- Monitoring pipeline health
- Backpressure handling

## Use Case

**Scenario**: Process customer event data from various sources

- **Ingester Agent**: Receives events from external sources, validates, normalizes
- **Processor Agent**: Enriches data, applies business rules, filters
- **Storage Agent**: Persists to database, sends to data warehouse

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Data Sources                            │
│                  (APIs, Webhooks, Message Queues)               │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         │ Raw Events
                         │
                         ▼
              ┌──────────────────────┐
              │   Ingester Agent     │
              │                      │
              │  • Validate schema   │
              │  • Normalize format  │
              │  • Rate limiting     │
              │  • Deduplication     │
              └──────────┬───────────┘
                         │
                         │ Validated Events
                         │
                         ▼
              ┌──────────────────────┐
              │  Processor Agent     │
              │                      │
              │  • Enrich data       │
              │  • Apply rules       │
              │  • Filter/transform  │
              │  • Aggregate         │
              └──────────┬───────────┘
                         │
                         │ Processed Events
                         │
                         ▼
              ┌──────────────────────┐
              │   Storage Agent      │
              │                      │
              │  • Save to DB        │
              │  • Send to warehouse │
              │  • Update indexes    │
              │  • Trigger analytics │
              └──────────────────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │  Data Stores         │
              │  • PostgreSQL        │
              │  • S3/Data Lake      │
              │  • Search Index      │
              └──────────────────────┘

All communication secured with:
- SPIFFE identity
- mTLS transport
- OPA authorization
- Full audit trail
```

## Data Flow Diagram

```
External Event → Ingester → Processor → Storage → Database
                     │           │           │
                     │           │           └─→ Data Warehouse
                     │           └─→ Metrics
                     └─→ Dead Letter Queue (if invalid)

Each arrow represents:
- A2A protocol message
- mTLS connection
- OPA policy check
- Distributed trace span
```

## Complete Code

### Ingester Agent

```python
# ingester_agent.py
"""
Ingester Agent - Receives and validates incoming events.

Responsibilities:
- Accept events from external sources
- Validate schema and format
- Normalize data structure
- Rate limiting
- Send to processor
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, ValidationError

from agentweave import SecureAgent, capability
from agentweave.types import TaskResult, Message, DataPart
from agentweave.exceptions import AgentCallError


class Event(BaseModel):
    """Event schema."""
    event_id: str
    event_type: str
    timestamp: datetime
    user_id: str
    properties: Dict[str, Any]
    source: str


class IngesterAgent(SecureAgent):
    """Ingests and validates events from external sources."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.processor_id = "spiffe://agentweave.io/agent/processor"

        # Metrics
        self._events_received = 0
        self._events_validated = 0
        self._events_rejected = 0

    @capability("ingest_event")
    async def ingest_event(self, event_data: Dict[str, Any]) -> TaskResult:
        """
        Ingest a single event.

        Process:
        1. Validate event schema
        2. Normalize format
        3. Check for duplicates
        4. Send to processor
        """
        self._events_received += 1

        try:
            # Validate event schema
            event = Event(**event_data)

            # Check for duplicates (simplified)
            if await self._is_duplicate(event.event_id):
                self.logger.warning(
                    "Duplicate event detected",
                    extra={"event_id": event.event_id}
                )
                return TaskResult(
                    status="completed",
                    messages=[Message(
                        role="assistant",
                        parts=[DataPart(data={
                            "status": "duplicate",
                            "event_id": event.event_id
                        })]
                    )]
                )

            # Normalize event
            normalized = await self._normalize_event(event)

            # Send to processor
            result = await self.call_agent(
                target=self.processor_id,
                task_type="process_event",
                payload={
                    "event": normalized,
                    "ingested_at": datetime.utcnow().isoformat(),
                    "ingester_id": str(self.spiffe_id)
                },
                timeout=30.0
            )

            if result.status == "completed":
                self._events_validated += 1
                self.logger.info(
                    "Event ingested successfully",
                    extra={
                        "event_id": event.event_id,
                        "event_type": event.event_type
                    }
                )
            else:
                raise AgentCallError(f"Processor failed: {result.error}")

            return TaskResult(
                status="completed",
                messages=[Message(
                    role="assistant",
                    parts=[DataPart(data={
                        "status": "ingested",
                        "event_id": event.event_id,
                        "processed": True
                    })]
                )]
            )

        except ValidationError as e:
            self._events_rejected += 1
            self.logger.error(
                "Event validation failed",
                extra={"errors": str(e), "event_data": event_data}
            )

            # Send to dead letter queue
            await self._send_to_dlq(event_data, str(e))

            return TaskResult(
                status="failed",
                error=f"Invalid event schema: {e}"
            )

        except AgentCallError as e:
            self.logger.error(f"Failed to send to processor: {e}")
            # Could implement retry logic here
            return TaskResult(
                status="failed",
                error=f"Processing failed: {e}"
            )

    @capability("ingest_batch")
    async def ingest_batch(
        self,
        events: List[Dict[str, Any]]
    ) -> TaskResult:
        """
        Ingest a batch of events.

        Processes events in parallel with backpressure control.
        """
        self.logger.info(f"Ingesting batch of {len(events)} events")

        # Process events with concurrency limit
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent

        async def process_one(event_data):
            async with semaphore:
                return await self.ingest_event(event_data)

        results = await asyncio.gather(
            *[process_one(e) for e in events],
            return_exceptions=True
        )

        # Aggregate results
        succeeded = sum(1 for r in results if isinstance(r, TaskResult) and r.status == "completed")
        failed = len(results) - succeeded

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data={
                    "total": len(events),
                    "succeeded": succeeded,
                    "failed": failed
                })]
            )]
        )

    @capability("health")
    async def health(self) -> TaskResult:
        """Get ingester health metrics."""
        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data={
                    "agent": "ingester",
                    "status": "healthy",
                    "metrics": {
                        "events_received": self._events_received,
                        "events_validated": self._events_validated,
                        "events_rejected": self._events_rejected,
                        "rejection_rate": self._events_rejected / max(self._events_received, 1)
                    }
                })]
            )]
        )

    async def _is_duplicate(self, event_id: str) -> bool:
        """Check if event was already processed."""
        # In production, check Redis or database
        return False

    async def _normalize_event(self, event: Event) -> Dict[str, Any]:
        """Normalize event format."""
        return {
            "event_id": event.event_id,
            "event_type": event.event_type,
            "timestamp": event.timestamp.isoformat(),
            "user_id": event.user_id,
            "properties": event.properties,
            "source": event.source,
            "version": "1.0"
        }

    async def _send_to_dlq(self, event_data: Dict[str, Any], error: str):
        """Send invalid event to dead letter queue."""
        self.logger.warning(
            "Sending to DLQ",
            extra={"event": event_data, "error": error}
        )
        # In production, send to SQS, Kafka, etc.


async def main():
    agent = IngesterAgent.from_config("config/ingester.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Processor Agent

```python
# processor_agent.py
"""
Processor Agent - Enriches and transforms events.

Responsibilities:
- Enrich event data (lookup user info, etc.)
- Apply business rules
- Filter and transform
- Send to storage
"""

import asyncio
from typing import Dict, Any
from datetime import datetime

from agentweave import SecureAgent, capability, requires_peer
from agentweave.types import TaskResult, Message, DataPart
from agentweave.exceptions import AgentCallError


class ProcessorAgent(SecureAgent):
    """Processes and enriches events."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.storage_id = "spiffe://agentweave.io/agent/storage"

        # Metrics
        self._events_processed = 0
        self._events_filtered = 0

    @capability("process_event")
    @requires_peer("spiffe://agentweave.io/agent/ingester")
    async def process_event(
        self,
        event: Dict[str, Any],
        ingested_at: str,
        ingester_id: str
    ) -> TaskResult:
        """
        Process an event.

        Processing pipeline:
        1. Enrich with additional data
        2. Apply business rules
        3. Transform format
        4. Send to storage
        """
        self.logger.info(
            "Processing event",
            extra={
                "event_id": event["event_id"],
                "event_type": event["event_type"]
            }
        )

        # Step 1: Enrich event
        enriched = await self._enrich_event(event)

        # Step 2: Apply business rules
        if not await self._should_process(enriched):
            self._events_filtered += 1
            self.logger.debug(
                "Event filtered by business rules",
                extra={"event_id": event["event_id"]}
            )
            return TaskResult(
                status="completed",
                messages=[Message(
                    role="assistant",
                    parts=[DataPart(data={"status": "filtered"})]
                )]
            )

        # Step 3: Transform
        transformed = await self._transform_event(enriched)

        # Step 4: Send to storage
        try:
            result = await self.call_agent(
                target=self.storage_id,
                task_type="store_event",
                payload={
                    "event": transformed,
                    "processed_at": datetime.utcnow().isoformat(),
                    "processor_id": str(self.spiffe_id)
                },
                timeout=30.0
            )

            if result.status != "completed":
                raise AgentCallError(f"Storage failed: {result.error}")

            self._events_processed += 1

            return TaskResult(
                status="completed",
                messages=[Message(
                    role="assistant",
                    parts=[DataPart(data={
                        "status": "processed",
                        "event_id": event["event_id"]
                    })]
                )]
            )

        except AgentCallError as e:
            self.logger.error(f"Failed to store event: {e}")
            return TaskResult(
                status="failed",
                error=f"Storage failed: {e}"
            )

    async def _enrich_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrich event with additional data.

        In production:
        - Lookup user profile
        - Geo-location from IP
        - Product catalog data
        """
        enriched = event.copy()

        # Simulate user lookup
        user_data = await self._lookup_user(event["user_id"])
        enriched["user"] = user_data

        # Add computed fields
        enriched["computed"] = {
            "day_of_week": datetime.fromisoformat(event["timestamp"]).strftime("%A"),
            "hour": datetime.fromisoformat(event["timestamp"]).hour
        }

        return enriched

    async def _should_process(self, event: Dict[str, Any]) -> bool:
        """
        Apply business rules to determine if event should be processed.

        Examples:
        - Filter test users
        - Skip certain event types
        - Apply sampling
        """
        # Skip test users
        if event.get("user", {}).get("is_test", False):
            return False

        # Skip certain event types
        skip_types = ["heartbeat", "debug"]
        if event["event_type"] in skip_types:
            return False

        return True

    async def _transform_event(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform event to storage format.

        - Flatten nested structures
        - Convert types
        - Add metadata
        """
        return {
            "id": event["event_id"],
            "type": event["event_type"],
            "timestamp": event["timestamp"],
            "user_id": event["user_id"],
            "user_name": event.get("user", {}).get("name"),
            "user_tier": event.get("user", {}).get("tier", "free"),
            "properties": event["properties"],
            "source": event["source"],
            "day_of_week": event["computed"]["day_of_week"],
            "hour": event["computed"]["hour"],
            "version": event["version"]
        }

    async def _lookup_user(self, user_id: str) -> Dict[str, Any]:
        """Lookup user data (mock)."""
        # In production, query user service or database
        return {
            "id": user_id,
            "name": f"User {user_id}",
            "tier": "premium",
            "is_test": False
        }


async def main():
    agent = ProcessorAgent.from_config("config/processor.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Storage Agent

```python
# storage_agent.py
"""
Storage Agent - Persists events to data stores.

Responsibilities:
- Save to database
- Send to data warehouse
- Update search indexes
- Trigger downstream analytics
"""

import asyncio
from typing import Dict, Any
from datetime import datetime

from agentweave import SecureAgent, capability, requires_peer
from agentweave.types import TaskResult, Message, DataPart


class StorageAgent(SecureAgent):
    """Stores events in multiple data stores."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Metrics
        self._events_stored = 0
        self._storage_errors = 0

    @capability("store_event")
    @requires_peer("spiffe://agentweave.io/agent/processor")
    async def store_event(
        self,
        event: Dict[str, Any],
        processed_at: str,
        processor_id: str
    ) -> TaskResult:
        """
        Store event in multiple destinations.

        Destinations:
        1. Primary database (PostgreSQL)
        2. Data warehouse (S3/Parquet)
        3. Search index (Elasticsearch)
        """
        self.logger.info(
            "Storing event",
            extra={"event_id": event["id"], "event_type": event["type"]}
        )

        results = {}

        try:
            # Store in parallel
            db_task = self._store_in_database(event)
            warehouse_task = self._store_in_warehouse(event)
            search_task = self._update_search_index(event)

            db_result, warehouse_result, search_result = await asyncio.gather(
                db_task, warehouse_task, search_task,
                return_exceptions=True
            )

            results["database"] = "success" if not isinstance(db_result, Exception) else str(db_result)
            results["warehouse"] = "success" if not isinstance(warehouse_result, Exception) else str(warehouse_result)
            results["search"] = "success" if not isinstance(search_result, Exception) else str(search_result)

            # Check if critical storage (database) succeeded
            if isinstance(db_result, Exception):
                self._storage_errors += 1
                raise db_result

            self._events_stored += 1

            # Trigger downstream (async, don't wait)
            asyncio.create_task(self._trigger_analytics(event))

            return TaskResult(
                status="completed",
                messages=[Message(
                    role="assistant",
                    parts=[DataPart(data={
                        "status": "stored",
                        "event_id": event["id"],
                        "destinations": results
                    })]
                )]
            )

        except Exception as e:
            self.logger.error(
                f"Storage failed: {e}",
                extra={"event_id": event["id"]}
            )
            return TaskResult(
                status="failed",
                error=f"Storage failed: {e}"
            )

    async def _store_in_database(self, event: Dict[str, Any]):
        """Store in primary database."""
        self.logger.debug(f"Storing event {event['id']} in database")

        # In production, use async database client
        # await db.events.insert_one(event)

        # Simulate database write
        await asyncio.sleep(0.01)

    async def _store_in_warehouse(self, event: Dict[str, Any]):
        """Store in data warehouse."""
        self.logger.debug(f"Storing event {event['id']} in warehouse")

        # In production:
        # - Buffer events
        # - Write to S3 as Parquet
        # - Partition by date
        # await s3_client.write_parquet(event)

        await asyncio.sleep(0.005)

    async def _update_search_index(self, event: Dict[str, Any]):
        """Update search index."""
        self.logger.debug(f"Indexing event {event['id']} in search")

        # In production, use Elasticsearch client
        # await es_client.index(index="events", document=event)

        await asyncio.sleep(0.005)

    async def _trigger_analytics(self, event: Dict[str, Any]):
        """Trigger downstream analytics (fire and forget)."""
        self.logger.debug(f"Triggering analytics for event {event['id']}")

        # In production:
        # - Send to Kafka topic
        # - Trigger Lambda function
        # - Update real-time dashboards

        await asyncio.sleep(0.01)


async def main():
    agent = StorageAgent.from_config("config/storage.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration Files

### Ingester Configuration

```yaml
# config/ingester.yaml
agent:
  name: "ingester"
  trust_domain: "agentweave.io"
  description: "Event ingestion and validation"

  capabilities:
    - name: "ingest_event"
      description: "Ingest single event"
    - name: "ingest_batch"
      description: "Ingest batch of events"
    - name: "health"
      description: "Health check"

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"
  allowed_trust_domains:
    - "agentweave.io"

authorization:
  provider: "opa"
  opa_endpoint: "http://opa:8181"
  policy_path: "pipeline/authz/ingester"
  default_action: "deny"

server:
  host: "0.0.0.0"
  port: 8443

observability:
  metrics:
    enabled: true
    port: 9090
  tracing:
    enabled: true
    exporter: "otlp"
    endpoint: "http://jaeger:4317"
  logging:
    level: "INFO"
```

## Docker Compose

```yaml
# docker-compose.yaml
version: '3.8'

services:
  spire-server:
    image: ghcr.io/spiffe/spire-server:1.9.0
    # ... (same as other examples)

  spire-agent:
    image: ghcr.io/spiffe/spire-agent:1.9.0
    # ... (same as other examples)

  opa:
    image: openpolicyagent/opa:0.62.0
    # ... (same as other examples)

  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: events
      POSTGRES_USER: pipeline
      POSTGRES_PASSWORD: pipeline
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data

  jaeger:
    image: jaegertracing/all-in-one:latest
    ports:
      - "16686:16686"  # UI
      - "4317:4317"    # OTLP gRPC

  ingester:
    build:
      context: .
      dockerfile: Dockerfile.ingester
    depends_on:
      - spire-agent
      - opa
    ports:
      - "8443:8443"
      - "9090:9090"

  processor:
    build:
      context: .
      dockerfile: Dockerfile.processor
    depends_on:
      - spire-agent
      - opa
      - ingester
    ports:
      - "8444:8443"
      - "9091:9090"

  storage:
    build:
      context: .
      dockerfile: Dockerfile.storage
    depends_on:
      - spire-agent
      - opa
      - processor
      - postgres
    ports:
      - "8445:8443"
      - "9092:9090"

volumes:
  postgres-data:
```

## Running the Pipeline

### Step 1: Start Infrastructure

```bash
docker-compose up -d spire-server spire-agent opa postgres jaeger
```

### Step 2: Register Agents

```bash
# Register all three agents
for agent in ingester processor storage; do
    docker-compose exec spire-server \
        /opt/spire/bin/spire-server entry create \
        -spiffeID spiffe://agentweave.io/agent/$agent \
        -parentID spiffe://agentweave.io/agent/spire-agent \
        -selector docker:label:com.docker.compose.service:$agent
done
```

### Step 3: Start Pipeline

```bash
docker-compose up -d ingester processor storage
```

### Step 4: Send Test Event

```bash
# Single event
agentweave call \
    --target spiffe://agentweave.io/agent/ingester \
    --capability ingest_event \
    --data '{
        "event_data": {
            "event_id": "evt-001",
            "event_type": "user_signup",
            "timestamp": "2025-12-07T10:00:00Z",
            "user_id": "user-123",
            "source": "web",
            "properties": {
                "plan": "premium",
                "referral_code": "FRIEND20"
            }
        }
    }'

# Batch
agentweave call \
    --target spiffe://agentweave.io/agent/ingester \
    --capability ingest_batch \
    --data @sample_events.json
```

## Monitoring

### View Traces in Jaeger

```bash
# Open Jaeger UI
open http://localhost:16686

# Search for traces:
# Service: ingester, processor, storage
# See complete pipeline flow
```

### Check Metrics

```bash
# Ingester metrics
curl http://localhost:9090/metrics

# Processor metrics
curl http://localhost:9091/metrics

# Storage metrics
curl http://localhost:9092/metrics
```

### Pipeline Health

```bash
# Check ingester health
agentweave call \
    --target spiffe://agentweave.io/agent/ingester \
    --capability health
```

## Key Takeaways

### Pipeline as Agents

Traditional pipeline services become secure agents:

- **Each stage** is an independent agent
- **Communication** is secured (mTLS, OPA)
- **Observability** is built-in (traces, metrics)
- **Resilience** through retries, circuit breakers

### Backpressure Handling

```python
# Ingester uses semaphore for concurrency control
semaphore = asyncio.Semaphore(10)

async def process_one(event):
    async with semaphore:
        return await self.ingest_event(event)
```

### Distributed Tracing

Every agent call creates a trace span:

```
Trace: process-event-evt-001
├── Span: ingester.ingest_event (2ms)
├── Span: processor.process_event (15ms)
│   ├── Span: enrich_event (8ms)
│   └── Span: transform_event (2ms)
└── Span: storage.store_event (25ms)
    ├── Span: database_write (10ms)
    ├── Span: warehouse_write (8ms)
    └── Span: search_index (7ms)
```

## Next Steps

- **Stream Processing**: Integrate with Kafka for high-volume events
- **Advanced Patterns**: See [Microservices Example](microservices/)
- **Production**: Add retries, dead letter queues, monitoring alerts
- **Scaling**: Deploy on Kubernetes with horizontal pod autoscaling

---

**Complete Code**: [GitHub Repository](https://github.com/agentweave/examples/tree/main/data-pipeline)
