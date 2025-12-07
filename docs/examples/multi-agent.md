---
layout: page
title: Multi-Agent Orchestration
permalink: /examples/multi-agent/
parent: Examples Overview
nav_order: 2
---

# Multi-Agent Orchestration Example

**Complexity:** Intermediate
**Time to Complete:** 30 minutes
**Prerequisites:** Complete [Simple Agent](simple-agent/) example first

This example demonstrates the orchestrator pattern: a coordinator agent that delegates work to multiple specialized worker agents. This is one of the most common multi-agent patterns.

## What You'll Learn

- How to make agent-to-agent calls using `call_agent()`
- Orchestrator pattern with worker agents
- Different authorization policies for different agents
- Running multiple agents in a system
- Error handling and fault tolerance

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         Client                               │
└───────────────────────┬──────────────────────────────────────┘
                        │
                        │ "Process this document"
                        ▼
          ┌─────────────────────────────┐
          │   Orchestrator Agent        │
          │                             │
          │  Coordinates workflow:      │
          │  1. Call Analyzer           │
          │  2. Call Summarizer         │
          │  3. Combine results         │
          └──────┬────────────┬─────────┘
                 │            │
        ┌────────┘            └────────┐
        │                              │
        ▼                              ▼
┌──────────────────┐          ┌──────────────────┐
│ Analyzer Agent   │          │ Summarizer Agent │
│                  │          │                  │
│ Analyzes:        │          │ Summarizes:      │
│ - Sentiment      │          │ - Key points     │
│ - Topics         │          │ - Action items   │
│ - Entities       │          │ - Summary        │
└──────────────────┘          └──────────────────┘

All communication uses:
- mTLS with SPIFFE identity
- OPA policy enforcement
- Audit logging
```

## Sequence Diagram

```
Client                Orchestrator           Analyzer        Summarizer
  │                        │                     │               │
  │──Process Document────► │                     │               │
  │                        │                     │               │
  │                        │──Analyze────────────►│               │
  │                        │                     │               │
  │                        │  (mTLS + OPA check) │               │
  │                        │                     │               │
  │                        │◄─Analysis Results───│               │
  │                        │                     │               │
  │                        │──Summarize──────────┼──────────────►│
  │                        │                     │               │
  │                        │          (mTLS + OPA check)         │
  │                        │                     │               │
  │                        │◄─Summary────────────┼───────────────│
  │                        │                     │               │
  │                        │ (Combine results)   │               │
  │                        │                     │               │
  │◄─Combined Report───────│                     │               │
  │                        │                     │               │
```

## Complete Code

### Orchestrator Agent

```python
# orchestrator_agent.py
"""
Orchestrator Agent - Coordinates document processing workflow.

This agent demonstrates:
- Making calls to other agents
- Error handling and retries
- Combining results from multiple agents
- Workflow orchestration
"""

import asyncio
from typing import Dict, Any, List

from agentweave import SecureAgent, capability
from agentweave.types import TaskResult, Message, TextPart, DataPart
from agentweave.exceptions import AgentCallError, AuthorizationError


class OrchestratorAgent(SecureAgent):
    """
    Orchestrates document processing across multiple agents.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Configuration: SPIFFE IDs of worker agents
        self.analyzer_id = "spiffe://agentweave.io/agent/analyzer"
        self.summarizer_id = "spiffe://agentweave.io/agent/summarizer"

    @capability("process_document")
    async def process_document(
        self,
        document: str,
        options: Dict[str, Any] = None
    ) -> TaskResult:
        """
        Process a document through analysis and summarization.

        Workflow:
        1. Call Analyzer agent to extract insights
        2. Call Summarizer agent to create summary
        3. Combine results into comprehensive report

        Args:
            document: The document text to process
            options: Processing options (analyze_sentiment, etc.)

        Returns:
            TaskResult with combined analysis and summary
        """
        options = options or {}

        self.logger.info(
            "Starting document processing workflow",
            extra={
                "document_length": len(document),
                "options": options
            }
        )

        try:
            # Step 1: Analyze document
            analysis = await self._analyze_document(document, options)

            # Step 2: Summarize document
            summary = await self._summarize_document(document, options)

            # Step 3: Combine results
            report = self._create_report(document, analysis, summary)

            self.logger.info("Document processing completed successfully")

            return TaskResult(
                status="completed",
                messages=[
                    Message(
                        role="assistant",
                        parts=[
                            TextPart(text=report["text"]),
                            DataPart(data=report["data"])
                        ]
                    )
                ],
                artifacts=[
                    {
                        "type": "analysis",
                        "data": analysis
                    },
                    {
                        "type": "summary",
                        "data": summary
                    }
                ]
            )

        except AuthorizationError as e:
            self.logger.error(f"Authorization failed: {e}")
            return TaskResult(
                status="failed",
                error=f"Not authorized to call required agents: {e}"
            )

        except AgentCallError as e:
            self.logger.error(f"Agent call failed: {e}")
            return TaskResult(
                status="failed",
                error=f"Failed to process document: {e}"
            )

    async def _analyze_document(
        self,
        document: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call Analyzer agent to analyze document.

        The SDK automatically:
        - Verifies our identity with SPIRE
        - Establishes mTLS with analyzer
        - Checks OPA policy allows this call
        - Logs the request
        """
        self.logger.debug(f"Calling analyzer: {self.analyzer_id}")

        result = await self.call_agent(
            target=self.analyzer_id,
            task_type="analyze",
            payload={
                "text": document,
                "analyze_sentiment": options.get("analyze_sentiment", True),
                "extract_topics": options.get("extract_topics", True),
                "extract_entities": options.get("extract_entities", True)
            },
            timeout=30.0
        )

        if result.status != "completed":
            raise AgentCallError(f"Analyzer failed: {result.error}")

        return result.artifacts[0]["data"]

    async def _summarize_document(
        self,
        document: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Call Summarizer agent to create summary."""
        self.logger.debug(f"Calling summarizer: {self.summarizer_id}")

        result = await self.call_agent(
            target=self.summarizer_id,
            task_type="summarize",
            payload={
                "text": document,
                "max_length": options.get("summary_length", 200),
                "include_key_points": True,
                "include_action_items": True
            },
            timeout=30.0
        )

        if result.status != "completed":
            raise AgentCallError(f"Summarizer failed: {result.error}")

        return result.artifacts[0]["data"]

    def _create_report(
        self,
        document: str,
        analysis: Dict[str, Any],
        summary: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Combine analysis and summary into final report."""

        report_text = f"""
Document Processing Report
==========================

Summary
-------
{summary['summary']}

Key Points
----------
{self._format_list(summary['key_points'])}

Sentiment Analysis
------------------
Overall: {analysis['sentiment']['overall']} ({analysis['sentiment']['score']:.2f})

Topics Identified
-----------------
{self._format_list(analysis['topics'])}

Entities Extracted
------------------
{self._format_entities(analysis['entities'])}

Action Items
------------
{self._format_list(summary.get('action_items', []))}
"""

        return {
            "text": report_text.strip(),
            "data": {
                "document_length": len(document),
                "analysis": analysis,
                "summary": summary,
                "processed_at": self.context.request_time.isoformat()
            }
        }

    @staticmethod
    def _format_list(items: List[str]) -> str:
        """Format list items with bullets."""
        return "\n".join(f"• {item}" for item in items)

    @staticmethod
    def _format_entities(entities: Dict[str, List[str]]) -> str:
        """Format entity dictionary."""
        lines = []
        for entity_type, items in entities.items():
            lines.append(f"\n{entity_type.title()}:")
            lines.extend(f"  • {item}" for item in items)
        return "\n".join(lines)


async def main():
    agent = OrchestratorAgent.from_config("config/orchestrator.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Analyzer Agent

```python
# analyzer_agent.py
"""
Analyzer Agent - Analyzes document content.

This worker agent performs:
- Sentiment analysis
- Topic extraction
- Named entity recognition
"""

import asyncio
from typing import Dict, Any, List

from agentweave import SecureAgent, capability, requires_peer
from agentweave.types import TaskResult, Message, DataPart


class AnalyzerAgent(SecureAgent):
    """Analyzes document content for insights."""

    @capability("analyze")
    @requires_peer("spiffe://agentweave.io/agent/orchestrator")
    async def analyze(
        self,
        text: str,
        analyze_sentiment: bool = True,
        extract_topics: bool = True,
        extract_entities: bool = True
    ) -> TaskResult:
        """
        Analyze document content.

        Note: @requires_peer decorator ensures only orchestrator can call this.
        SDK enforces this before method runs.
        """
        self.logger.info(
            "Analyzing document",
            extra={"text_length": len(text)}
        )

        result = {}

        if analyze_sentiment:
            result["sentiment"] = await self._analyze_sentiment(text)

        if extract_topics:
            result["topics"] = await self._extract_topics(text)

        if extract_entities:
            result["entities"] = await self._extract_entities(text)

        return TaskResult(
            status="completed",
            messages=[
                Message(
                    role="assistant",
                    parts=[
                        DataPart(data={
                            "analysis": result,
                            "analyzer_version": "1.0.0"
                        })
                    ]
                )
            ],
            artifacts=[
                {
                    "type": "analysis_results",
                    "data": result
                }
            ]
        )

    async def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment.

        In production, this would use an LLM or ML model.
        For demo, we'll use a simple heuristic.
        """
        # Simple keyword-based sentiment (replace with real model)
        positive_words = ["good", "great", "excellent", "positive", "success"]
        negative_words = ["bad", "poor", "negative", "fail", "problem"]

        text_lower = text.lower()
        pos_count = sum(word in text_lower for word in positive_words)
        neg_count = sum(word in text_lower for word in negative_words)

        total = pos_count + neg_count
        if total == 0:
            return {"overall": "neutral", "score": 0.0}

        score = (pos_count - neg_count) / total

        if score > 0.2:
            overall = "positive"
        elif score < -0.2:
            overall = "negative"
        else:
            overall = "neutral"

        return {
            "overall": overall,
            "score": score,
            "positive_indicators": pos_count,
            "negative_indicators": neg_count
        }

    async def _extract_topics(self, text: str) -> List[str]:
        """Extract main topics (simplified for demo)."""
        # In production, use topic modeling (LDA, etc.)
        topics = []

        keywords = {
            "technology": ["software", "hardware", "computer", "digital"],
            "business": ["revenue", "profit", "market", "customer"],
            "science": ["research", "study", "experiment", "data"],
        }

        text_lower = text.lower()
        for topic, words in keywords.items():
            if any(word in text_lower for word in words):
                topics.append(topic)

        return topics or ["general"]

    async def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities (simplified for demo)."""
        # In production, use NER model (spaCy, transformers, etc.)
        return {
            "organizations": ["AgentWeave", "ACME Corp"],  # Placeholder
            "locations": ["San Francisco", "New York"],
            "technologies": ["Python", "Kubernetes"]
        }


async def main():
    agent = AnalyzerAgent.from_config("config/analyzer.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Summarizer Agent

```python
# summarizer_agent.py
"""
Summarizer Agent - Creates document summaries.
"""

import asyncio
from typing import Dict, Any, List

from agentweave import SecureAgent, capability, requires_peer
from agentweave.types import TaskResult, Message, TextPart, DataPart


class SummarizerAgent(SecureAgent):
    """Creates concise document summaries."""

    @capability("summarize")
    @requires_peer("spiffe://agentweave.io/agent/orchestrator")
    async def summarize(
        self,
        text: str,
        max_length: int = 200,
        include_key_points: bool = True,
        include_action_items: bool = True
    ) -> TaskResult:
        """Create document summary."""
        self.logger.info(
            "Summarizing document",
            extra={
                "text_length": len(text),
                "max_length": max_length
            }
        )

        # Generate summary (simplified for demo)
        summary_text = await self._generate_summary(text, max_length)

        result = {
            "summary": summary_text
        }

        if include_key_points:
            result["key_points"] = await self._extract_key_points(text)

        if include_action_items:
            result["action_items"] = await self._extract_action_items(text)

        return TaskResult(
            status="completed",
            messages=[
                Message(
                    role="assistant",
                    parts=[
                        TextPart(text=summary_text),
                        DataPart(data=result)
                    ]
                )
            ],
            artifacts=[
                {
                    "type": "summary_results",
                    "data": result
                }
            ]
        )

    async def _generate_summary(self, text: str, max_length: int) -> str:
        """
        Generate summary.

        In production, use LLM for summarization.
        """
        # Simple extractive summary (first sentences)
        sentences = text.split(". ")
        summary = sentences[0]

        for sentence in sentences[1:]:
            if len(summary) + len(sentence) > max_length:
                break
            summary += ". " + sentence

        return summary.strip()

    async def _extract_key_points(self, text: str) -> List[str]:
        """Extract key points (simplified)."""
        # In production, use LLM to identify key points
        sentences = text.split(". ")
        return sentences[:3] if len(sentences) >= 3 else sentences

    async def _extract_action_items(self, text: str) -> List[str]:
        """Extract action items (simplified)."""
        # In production, use LLM to identify action items
        action_verbs = ["implement", "create", "develop", "deploy", "test"]

        action_items = []
        for sentence in text.split(". "):
            if any(verb in sentence.lower() for verb in action_verbs):
                action_items.append(sentence.strip())

        return action_items


async def main():
    agent = SummarizerAgent.from_config("config/summarizer.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

## Configuration Files

### Orchestrator Configuration

```yaml
# config/orchestrator.yaml
agent:
  name: "orchestrator"
  trust_domain: "agentweave.io"
  description: "Orchestrates document processing workflow"

  capabilities:
    - name: "process_document"
      description: "Process document through analysis and summarization"
      input_modes: ["text/plain", "application/json"]
      output_modes: ["text/plain", "application/json"]

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"
  allowed_trust_domains:
    - "agentweave.io"

authorization:
  provider: "opa"
  opa_endpoint: "http://opa:8181"
  policy_path: "agentweave/authz/orchestrator"
  default_action: "deny"
  audit:
    enabled: true
    destination: "stdout"

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"
  connection_pool:
    max_connections: 20
    idle_timeout_seconds: 60

server:
  host: "0.0.0.0"
  port: 8443
  protocol: "a2a"

observability:
  metrics:
    enabled: true
    port: 9090
  logging:
    level: "INFO"
    format: "json"
```

### Analyzer Configuration

```yaml
# config/analyzer.yaml
agent:
  name: "analyzer"
  trust_domain: "agentweave.io"
  description: "Analyzes document content for insights"

  capabilities:
    - name: "analyze"
      description: "Perform sentiment, topic, and entity analysis"
      input_modes: ["text/plain"]
      output_modes: ["application/json"]

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"
  allowed_trust_domains:
    - "agentweave.io"

authorization:
  provider: "opa"
  opa_endpoint: "http://opa:8181"
  policy_path: "agentweave/authz/analyzer"
  default_action: "deny"

server:
  host: "0.0.0.0"
  port: 8444
  protocol: "a2a"
```

### Summarizer Configuration

```yaml
# config/summarizer.yaml
agent:
  name: "summarizer"
  trust_domain: "agentweave.io"
  description: "Creates document summaries"

  capabilities:
    - name: "summarize"
      description: "Generate summary with key points and action items"
      input_modes: ["text/plain"]
      output_modes: ["text/plain", "application/json"]

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"
  allowed_trust_domains:
    - "agentweave.io"

authorization:
  provider: "opa"
  opa_endpoint: "http://opa:8181"
  policy_path: "agentweave/authz/summarizer"
  default_action: "deny"

server:
  host: "0.0.0.0"
  port: 8445
  protocol: "a2a"
```

## Authorization Policies

```rego
# config/policies/orchestrator_authz.rego
package agentweave.authz.orchestrator

import rego.v1

default allow := false

# Orchestrator can call analyzer
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/orchestrator"
    input.callee_spiffe_id == "spiffe://agentweave.io/agent/analyzer"
    input.action == "analyze"
}

# Orchestrator can call summarizer
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/orchestrator"
    input.callee_spiffe_id == "spiffe://agentweave.io/agent/summarizer"
    input.action == "summarize"
}

# Clients can call orchestrator
allow if {
    startswith(input.caller_spiffe_id, "spiffe://agentweave.io/client/")
    input.action == "process_document"
}
```

```rego
# config/policies/analyzer_authz.rego
package agentweave.authz.analyzer

import rego.v1

default allow := false

# Only orchestrator can call analyzer
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/orchestrator"
    input.action == "analyze"
}
```

```rego
# config/policies/summarizer_authz.rego
package agentweave.authz.summarizer

import rego.v1

default allow := false

# Only orchestrator can call summarizer
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/orchestrator"
    input.action == "summarize"
}
```

## Docker Compose Setup

```yaml
# docker-compose.yaml
version: '3.8'

services:
  spire-server:
    image: ghcr.io/spiffe/spire-server:1.9.0
    hostname: spire-server
    volumes:
      - ./spire/server.conf:/opt/spire/conf/server/server.conf:ro
      - spire-server-data:/opt/spire/data
    command: ["-config", "/opt/spire/conf/server/server.conf"]
    networks:
      - agentweave

  spire-agent:
    image: ghcr.io/spiffe/spire-agent:1.9.0
    hostname: spire-agent
    depends_on:
      - spire-server
    volumes:
      - ./spire/agent.conf:/opt/spire/conf/agent/agent.conf:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - spire-agent-socket:/run/spire/sockets
    command: ["-config", "/opt/spire/conf/agent/agent.conf"]
    networks:
      - agentweave

  opa:
    image: openpolicyagent/opa:0.62.0
    hostname: opa
    volumes:
      - ./config/policies:/policies:ro
    command:
      - "run"
      - "--server"
      - "--addr=0.0.0.0:8181"
      - "/policies"
    ports:
      - "8181:8181"
    networks:
      - agentweave

  orchestrator:
    build:
      context: .
      dockerfile: Dockerfile.orchestrator
    depends_on:
      - spire-agent
      - opa
      - analyzer
      - summarizer
    volumes:
      - spire-agent-socket:/run/spire/sockets:ro
      - ./config:/etc/agentweave:ro
    ports:
      - "8443:8443"
      - "9090:9090"
    networks:
      - agentweave

  analyzer:
    build:
      context: .
      dockerfile: Dockerfile.analyzer
    depends_on:
      - spire-agent
      - opa
    volumes:
      - spire-agent-socket:/run/spire/sockets:ro
      - ./config:/etc/agentweave:ro
    ports:
      - "8444:8444"
    networks:
      - agentweave

  summarizer:
    build:
      context: .
      dockerfile: Dockerfile.summarizer
    depends_on:
      - spire-agent
      - opa
    volumes:
      - spire-agent-socket:/run/spire/sockets:ro
      - ./config:/etc/agentweave:ro
    ports:
      - "8445:8445"
    networks:
      - agentweave

volumes:
  spire-server-data:
  spire-agent-socket:

networks:
  agentweave:
    driver: bridge
```

## Running the Example

### Step 1: Register Workloads with SPIRE

```bash
# Start infrastructure
docker-compose up -d spire-server spire-agent opa

# Register orchestrator
docker-compose exec spire-server \
    /opt/spire/bin/spire-server entry create \
    -spiffeID spiffe://agentweave.io/agent/orchestrator \
    -parentID spiffe://agentweave.io/agent/spire-agent \
    -selector docker:label:com.docker.compose.service:orchestrator

# Register analyzer
docker-compose exec spire-server \
    /opt/spire/bin/spire-server entry create \
    -spiffeID spiffe://agentweave.io/agent/analyzer \
    -parentID spiffe://agentweave.io/agent/spire-agent \
    -selector docker:label:com.docker.compose.service:analyzer

# Register summarizer
docker-compose exec spire-server \
    /opt/spire/bin/spire-server entry create \
    -spiffeID spiffe://agentweave.io/agent/summarizer \
    -parentID spiffe://agentweave.io/agent/spire-agent \
    -selector docker:label:com.docker.compose.service:summarizer
```

### Step 2: Start All Agents

```bash
docker-compose up -d
```

### Step 3: Test the System

```bash
# Process a document
agentweave call \
    --target spiffe://agentweave.io/agent/orchestrator \
    --capability process_document \
    --data '{
        "document": "Our latest software release has been excellent. Customers report positive experiences with the new features. We need to implement additional security measures and develop the mobile app. The team should deploy to production next week.",
        "options": {
            "analyze_sentiment": true,
            "extract_topics": true,
            "summary_length": 150
        }
    }'
```

## Expected Output

```json
{
  "status": "completed",
  "messages": [
    {
      "role": "assistant",
      "parts": [
        {
          "type": "text",
          "text": "Document Processing Report\n==========================\n\nSummary\n-------\nOur latest software release has been excellent. Customers report positive experiences with the new features.\n\nKey Points\n----------\n• Our latest software release has been excellent\n• Customers report positive experiences with the new features\n• We need to implement additional security measures and develop the mobile app\n\nSentiment Analysis\n------------------\nOverall: positive (0.67)\n\nTopics Identified\n-----------------\n• technology\n• business\n\nEntities Extracted\n------------------\nOrganizations:\n  • AgentWeave\n  • ACME Corp\n\nAction Items\n------------\n• implement additional security measures\n• develop the mobile app\n• deploy to production next week"
        }
      ]
    }
  ]
}
```

## Key Takeaways

### Inter-Agent Communication

The orchestrator calls workers with `call_agent()`:

```python
result = await self.call_agent(
    target="spiffe://agentweave.io/agent/analyzer",
    task_type="analyze",
    payload={...}
)
```

SDK automatically handles:
- mTLS connection establishment
- OPA policy check (can orchestrator call analyzer?)
- Request serialization (A2A protocol)
- Response deserialization
- Error propagation

### Access Control

Each agent has different policies:

- **Orchestrator**: Can call analyzer and summarizer
- **Analyzer**: Only orchestrator can call
- **Summarizer**: Only orchestrator can call
- **Clients**: Can call orchestrator

This is enforced by OPA before any code runs.

### Error Handling

```python
try:
    result = await self.call_agent(...)
except AuthorizationError:
    # Caller not allowed
except AgentCallError:
    # Call failed or timed out
```

## Next Steps

- **Add More Workers**: Create specialized agents for different tasks
- **Parallel Execution**: Call multiple agents concurrently with `asyncio.gather()`
- **Workflow Engine**: See [Data Pipeline Example](data-pipeline/) for complex workflows
- **Federation**: See [Federated Example](federated/) for cross-domain orchestration

---

**Complete Code**: [GitHub Repository](https://github.com/agentweave/examples/tree/main/multi-agent)
