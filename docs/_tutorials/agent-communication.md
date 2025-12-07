---
layout: tutorial
title: Agent-to-Agent Communication
permalink: /tutorials/agent-communication/
nav_order: 3
parent: Tutorials
difficulty: Intermediate
duration: 45 minutes
---

# Agent-to-Agent Communication

In this tutorial, you'll build a two-agent system demonstrating secure agent-to-agent communication using the A2A (Agent-to-Agent) protocol. You'll create a worker agent that performs tasks and an orchestrator agent that delegates work to it.

## Learning Objectives

By completing this tutorial, you will:
- Understand multi-agent architecture patterns
- Use the `call_agent()` method for agent communication
- Handle responses and errors in agent calls
- Configure multiple agents to work together
- Debug and troubleshoot agent communication
- Implement request/response patterns

## Prerequisites

Before starting, ensure you have:
- **Completed** [Building Your First Agent](/tutorials/first-agent/)
- **SPIRE and OPA running** with proper configuration
- **Basic networking knowledge** (ports, hosts, protocols)
- **Two terminal windows** to run both agents simultaneously

**Time estimate:** 45 minutes

## What You'll Build

A document processing system with two agents:
1. **Document Worker Agent** - Analyzes documents (word count, sentiment, etc.)
2. **Document Orchestrator Agent** - Receives requests and delegates to workers

This demonstrates a common pattern: orchestration agents that coordinate specialized worker agents.

## Architecture Overview

```
User/Client
    |
    | (A2A Request)
    v
┌─────────────────────────┐
│ Orchestrator Agent      │
│ spiffe://example.org/   │
│   orchestrator          │
└───────────┬─────────────┘
            |
            | call_agent()
            | (A2A Request via mTLS)
            v
┌─────────────────────────┐
│ Worker Agent            │
│ spiffe://example.org/   │
│   document-worker       │
└─────────────────────────┘
```

Both agents:
- Have unique SPIFFE identities
- Communicate via mTLS
- Enforce OPA policies
- Run on different ports

## Step 1: Create Project Structure

Set up the project directory:

```bash
mkdir multi-agent-demo
cd multi-agent-demo
mkdir -p config policies worker orchestrator
```

Your structure:
```
multi-agent-demo/
├── worker/
│   └── agent.py              # Worker agent implementation
├── orchestrator/
│   └── agent.py              # Orchestrator agent implementation
├── config/
│   ├── worker.yaml           # Worker configuration
│   └── orchestrator.yaml     # Orchestrator configuration
└── policies/
    ├── worker_policy.rego    # Worker authorization policy
    └── orchestrator_policy.rego  # Orchestrator policy
```

## Step 2: Create the Worker Agent

The worker agent performs document analysis tasks.

### Worker Configuration (config/worker.yaml)

```yaml
identity:
  spiffe_id: "spiffe://example.org/document-worker"
  spire_socket: "/tmp/spire-agent/public/api.sock"
  trust_domain: "example.org"

authorization:
  engine: "opa"
  default_policy: "deny_all"  # Production setting
  policy_path: "./policies"
  policy_file: "worker_policy.rego"

server:
  host: "0.0.0.0"
  port: 8443  # Worker port
  mtls:
    enabled: true
    cert_source: "spire"

observability:
  logging:
    level: "INFO"
    format: "json"
  metrics:
    enabled: true
    port: 9090

metadata:
  name: "Document Worker Agent"
  version: "1.0.0"
  description: "Analyzes documents for the orchestrator"
```

### Worker Policy (policies/worker_policy.rego)

```rego
package agentweave.authz

# Default deny - explicit allow required
default allow = false

# Allow requests from the orchestrator
allow {
    # Get caller's SPIFFE ID
    caller_spiffe_id := input.caller.spiffe_id

    # Only allow our orchestrator
    caller_spiffe_id == "spiffe://example.org/orchestrator"

    # And only for these methods
    input.request.method in ["analyze_document", "count_words", "detect_sentiment"]
}

# Allow requests from the same trust domain for testing
allow {
    caller_spiffe_id := input.caller.spiffe_id
    caller_trust_domain := split(caller_spiffe_id, "/")[2]
    our_trust_domain := input.agent.trust_domain
    caller_trust_domain == our_trust_domain
}
```

{: .note }
> This policy only allows the orchestrator agent to call the worker. This is zero-trust security in action!

### Worker Implementation (worker/agent.py)

```python
"""
Document Worker Agent - Performs document analysis tasks
"""
from typing import Dict, Any, List
from agentweave import Agent, capability
from agentweave.context import AgentContext
import re


class DocumentWorkerAgent(Agent):
    """
    Worker agent that analyzes documents.

    Provides capabilities for:
    - Word counting
    - Sentiment detection (simple)
    - Document analysis
    """

    def __init__(self, config_path: str):
        super().__init__(config_path)
        self.logger.info("Document Worker Agent initialized")

    @capability(
        name="analyze_document",
        description="Analyze a document and return comprehensive statistics",
        input_schema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Document text to analyze"
                }
            },
            "required": ["text"]
        }
    )
    async def analyze_document(
        self,
        context: AgentContext,
        text: str
    ) -> Dict[str, Any]:
        """
        Perform comprehensive document analysis.

        Args:
            context: Request context
            text: Document text

        Returns:
            Analysis results including word count, sentences, sentiment
        """
        self.logger.info(
            "Analyzing document",
            extra={
                "caller": context.caller_spiffe_id,
                "text_length": len(text)
            }
        )

        # Count words
        words = text.split()
        word_count = len(words)

        # Count sentences (simple heuristic)
        sentences = re.split(r'[.!?]+', text)
        sentence_count = len([s for s in sentences if s.strip()])

        # Detect sentiment (very simple keyword-based)
        sentiment = self._detect_sentiment(text)

        # Calculate average word length
        avg_word_length = sum(len(w) for w in words) / word_count if word_count > 0 else 0

        return {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_word_length": round(avg_word_length, 2),
            "sentiment": sentiment,
            "character_count": len(text),
            "analyzed_by": self.config.metadata.name
        }

    @capability(
        name="count_words",
        description="Count words in a text",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"]
        }
    )
    async def count_words(
        self,
        context: AgentContext,
        text: str
    ) -> Dict[str, Any]:
        """Count words in the provided text."""
        words = text.split()
        count = len(words)

        self.logger.info(f"Counted {count} words")

        return {
            "word_count": count,
            "text_length": len(text)
        }

    @capability(
        name="detect_sentiment",
        description="Detect sentiment of text (positive, negative, neutral)",
        input_schema={
            "type": "object",
            "properties": {
                "text": {"type": "string"}
            },
            "required": ["text"]
        }
    )
    async def detect_sentiment(
        self,
        context: AgentContext,
        text: str
    ) -> Dict[str, Any]:
        """
        Detect sentiment using simple keyword matching.

        Note: This is a simplified implementation for demonstration.
        Production systems should use ML models.
        """
        sentiment = self._detect_sentiment(text)

        return {
            "sentiment": sentiment,
            "confidence": "demonstration"  # Not a real confidence score
        }

    def _detect_sentiment(self, text: str) -> str:
        """
        Simple sentiment detection based on keywords.

        Returns:
            "positive", "negative", or "neutral"
        """
        text_lower = text.lower()

        positive_words = ["good", "great", "excellent", "amazing", "wonderful", "fantastic", "love", "happy"]
        negative_words = ["bad", "terrible", "awful", "horrible", "hate", "sad", "angry", "disappointed"]

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"


def main():
    """Main entry point."""
    import asyncio
    import sys

    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/worker.yaml"
    agent = DocumentWorkerAgent(config_path)
    asyncio.run(agent.serve())


if __name__ == "__main__":
    main()
```

## Step 3: Create the Orchestrator Agent

The orchestrator receives user requests and delegates to workers.

### Orchestrator Configuration (config/orchestrator.yaml)

```yaml
identity:
  spiffe_id: "spiffe://example.org/orchestrator"
  spire_socket: "/tmp/spire-agent/public/api.sock"
  trust_domain: "example.org"

authorization:
  engine: "opa"
  default_policy: "allow_all"  # Orchestrator accepts user requests
  policy_path: "./policies"
  policy_file: "orchestrator_policy.rego"

server:
  host: "0.0.0.0"
  port: 8444  # Different port from worker
  mtls:
    enabled: true
    cert_source: "spire"

# Agent registry - known agents this orchestrator can call
agent_registry:
  document_worker:
    spiffe_id: "spiffe://example.org/document-worker"
    address: "https://localhost:8443"  # Worker's address

observability:
  logging:
    level: "INFO"
    format: "json"
  metrics:
    enabled: true
    port: 9091  # Different from worker

metadata:
  name: "Document Orchestrator Agent"
  version: "1.0.0"
  description: "Orchestrates document processing tasks"
```

### Orchestrator Policy (policies/orchestrator_policy.rego)

```rego
package agentweave.authz

# Orchestrator accepts requests from users/other agents
default allow = true

# In production, you'd have stricter policies here:
# - Rate limiting by caller
# - Time-based access
# - Specific method restrictions
```

### Orchestrator Implementation (orchestrator/agent.py)

```python
"""
Document Orchestrator Agent - Delegates work to specialized workers
"""
from typing import Dict, Any, List
from agentweave import Agent, capability
from agentweave.context import AgentContext


class DocumentOrchestratorAgent(Agent):
    """
    Orchestrator agent that delegates document processing to workers.

    Demonstrates:
    - Using call_agent() for A2A communication
    - Error handling in agent calls
    - Aggregating responses from multiple workers
    """

    def __init__(self, config_path: str):
        super().__init__(config_path)
        self.logger.info("Document Orchestrator Agent initialized")

    @capability(
        name="process_document",
        description="Process a document using worker agents",
        input_schema={
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "Document text to process"
                },
                "operations": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Operations to perform: analyze, count, sentiment"
                }
            },
            "required": ["text"]
        }
    )
    async def process_document(
        self,
        context: AgentContext,
        text: str,
        operations: List[str] = None
    ) -> Dict[str, Any]:
        """
        Process a document by delegating to worker agents.

        Args:
            context: Request context
            text: Document text
            operations: List of operations (default: all)

        Returns:
            Aggregated results from worker
        """
        if operations is None:
            operations = ["analyze"]  # Default operation

        self.logger.info(
            "Processing document",
            extra={
                "operations": operations,
                "text_length": len(text)
            }
        )

        results = {}

        # Get worker agent details from registry
        worker_spiffe_id = "spiffe://example.org/document-worker"
        worker_address = self.config.agent_registry.document_worker.address

        # Perform requested operations
        for operation in operations:
            try:
                if operation == "analyze":
                    # Call the worker's analyze_document capability
                    response = await self.call_agent(
                        agent_spiffe_id=worker_spiffe_id,
                        agent_address=worker_address,
                        capability="analyze_document",
                        params={"text": text},
                        timeout=30.0
                    )
                    results["analysis"] = response

                elif operation == "count":
                    # Call the worker's count_words capability
                    response = await self.call_agent(
                        agent_spiffe_id=worker_spiffe_id,
                        agent_address=worker_address,
                        capability="count_words",
                        params={"text": text},
                        timeout=30.0
                    )
                    results["word_count"] = response

                elif operation == "sentiment":
                    # Call the worker's detect_sentiment capability
                    response = await self.call_agent(
                        agent_spiffe_id=worker_spiffe_id,
                        agent_address=worker_address,
                        capability="detect_sentiment",
                        params={"text": text},
                        timeout=30.0
                    )
                    results["sentiment"] = response

                else:
                    self.logger.warning(f"Unknown operation: {operation}")
                    results[operation] = {"error": "Unknown operation"}

            except Exception as e:
                # Handle errors gracefully
                self.logger.error(
                    f"Error calling worker for {operation}",
                    extra={"error": str(e)}
                )
                results[operation] = {
                    "error": str(e),
                    "status": "failed"
                }

        return {
            "status": "completed",
            "operations_performed": operations,
            "results": results,
            "processed_by": self.config.metadata.name
        }

    @capability(
        name="batch_process",
        description="Process multiple documents in batch",
        input_schema={
            "type": "object",
            "properties": {
                "documents": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "text": {"type": "string"}
                        }
                    }
                }
            },
            "required": ["documents"]
        }
    )
    async def batch_process(
        self,
        context: AgentContext,
        documents: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Process multiple documents in batch.

        Demonstrates parallel agent calls using asyncio.gather()
        """
        import asyncio

        self.logger.info(f"Batch processing {len(documents)} documents")

        worker_spiffe_id = "spiffe://example.org/document-worker"
        worker_address = self.config.agent_registry.document_worker.address

        # Create tasks for parallel processing
        tasks = []
        for doc in documents:
            task = self.call_agent(
                agent_spiffe_id=worker_spiffe_id,
                agent_address=worker_address,
                capability="analyze_document",
                params={"text": doc["text"]},
                timeout=30.0
            )
            tasks.append(task)

        # Execute all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Combine results
        processed = []
        for doc, result in zip(documents, results):
            if isinstance(result, Exception):
                processed.append({
                    "id": doc["id"],
                    "status": "failed",
                    "error": str(result)
                })
            else:
                processed.append({
                    "id": doc["id"],
                    "status": "success",
                    "analysis": result
                })

        return {
            "total_documents": len(documents),
            "successful": sum(1 for p in processed if p["status"] == "success"),
            "failed": sum(1 for p in processed if p["status"] == "failed"),
            "results": processed
        }


def main():
    """Main entry point."""
    import asyncio
    import sys

    config_path = sys.argv[1] if len(sys.argv) > 1 else "config/orchestrator.yaml"
    agent = DocumentOrchestratorAgent(config_path)
    asyncio.run(agent.serve())


if __name__ == "__main__":
    main()
```

## Step 4: Run Both Agents

You need two terminal windows.

### Terminal 1: Start the Worker

```bash
cd multi-agent-demo
python worker/agent.py config/worker.yaml
```

Output:
```json
{"level": "INFO", "message": "Document Worker Agent initialized"}
{"level": "INFO", "message": "Loaded SPIFFE identity", "spiffe_id": "spiffe://example.org/document-worker"}
{"level": "INFO", "message": "Agent server started", "port": 8443}
```

### Terminal 2: Start the Orchestrator

```bash
cd multi-agent-demo
python orchestrator/agent.py config/orchestrator.yaml
```

Output:
```json
{"level": "INFO", "message": "Document Orchestrator Agent initialized"}
{"level": "INFO", "message": "Loaded SPIFFE identity", "spiffe_id": "spiffe://example.org/orchestrator"}
{"level": "INFO", "message": "Agent server started", "port": 8444}
```

Both agents are now running!

## Step 5: Test Agent Communication

### Terminal 3: Test the System

```bash
# Call the orchestrator (which will call the worker)
agentweave-cli call \
  --agent spiffe://example.org/orchestrator \
  --address https://localhost:8444 \
  --capability process_document \
  --params '{
    "text": "This is a wonderful document. It contains great information and amazing insights.",
    "operations": ["analyze", "sentiment"]
  }'
```

Response:
```json
{
  "status": "completed",
  "operations_performed": ["analyze", "sentiment"],
  "results": {
    "analysis": {
      "word_count": 12,
      "sentence_count": 2,
      "avg_word_length": 7.25,
      "sentiment": "positive",
      "character_count": 85,
      "analyzed_by": "Document Worker Agent"
    },
    "sentiment": {
      "sentiment": "positive",
      "confidence": "demonstration"
    }
  },
  "processed_by": "Document Orchestrator Agent"
}
```

### Test Batch Processing

```bash
agentweave-cli call \
  --agent spiffe://example.org/orchestrator \
  --address https://localhost:8444 \
  --capability batch_process \
  --params '{
    "documents": [
      {"id": "doc1", "text": "This is excellent!"},
      {"id": "doc2", "text": "This is terrible."},
      {"id": "doc3", "text": "This is okay."}
    ]
  }'
```

Response shows parallel processing:
```json
{
  "total_documents": 3,
  "successful": 3,
  "failed": 0,
  "results": [
    {
      "id": "doc1",
      "status": "success",
      "analysis": {
        "word_count": 3,
        "sentiment": "positive",
        ...
      }
    },
    ...
  ]
}
```

## Step 6: View the Communication Logs

Check the worker's logs (Terminal 1) to see the incoming requests:

```json
{"level": "INFO", "message": "Analyzing document", "caller": "spiffe://example.org/orchestrator", "text_length": 85}
{"level": "INFO", "message": "Request completed", "capability": "analyze_document", "duration_ms": 2.3}
```

The orchestrator's logs (Terminal 2):

```json
{"level": "INFO", "message": "Processing document", "operations": ["analyze", "sentiment"], "text_length": 85}
{"level": "INFO", "message": "Calling agent", "target": "spiffe://example.org/document-worker", "capability": "analyze_document"}
{"level": "INFO", "message": "Agent call completed", "duration_ms": 15.7}
```

## Understanding call_agent()

The `call_agent()` method is the core of A2A communication:

```python
response = await self.call_agent(
    agent_spiffe_id="spiffe://example.org/document-worker",  # Who to call
    agent_address="https://localhost:8443",                  # Where they are
    capability="analyze_document",                            # What capability
    params={"text": text},                                   # Parameters
    timeout=30.0                                             # Timeout in seconds
)
```

**What happens behind the scenes:**
1. **mTLS Handshake** - Agents verify each other's SPIFFE identities
2. **A2A Protocol** - Request formatted as JSON-RPC 2.0
3. **Authorization Check** - Worker checks OPA policy
4. **Capability Execution** - Worker runs the capability
5. **Response** - Worker returns result over mTLS
6. **Deserialization** - Orchestrator receives Python dict

## Error Handling Patterns

### Handle Network Errors

```python
from agentweave.exceptions import AgentCallError, AuthorizationError

try:
    response = await self.call_agent(...)
except AgentCallError as e:
    self.logger.error(f"Failed to call agent: {e}")
    return {"error": "Worker unavailable"}
except AuthorizationError as e:
    self.logger.error(f"Authorization denied: {e}")
    return {"error": "Access denied"}
except Exception as e:
    self.logger.error(f"Unexpected error: {e}")
    return {"error": "Internal error"}
```

### Set Appropriate Timeouts

```python
# Short timeout for quick operations
response = await self.call_agent(..., timeout=5.0)

# Longer timeout for heavy processing
response = await self.call_agent(..., timeout=300.0)

# Default timeout (30 seconds)
response = await self.call_agent(...)
```

## Summary

You've successfully built a multi-agent system! You've learned:

- How to structure multi-agent architectures
- Using `call_agent()` for secure A2A communication
- Configuring agents with different identities and ports
- Writing policies that allow specific agent-to-agent calls
- Error handling in distributed systems
- Parallel agent calls with `asyncio.gather()`
- Debugging agent communication

## Exercises

1. **Add a third agent:** Create a "summarizer" worker and call it from the orchestrator
2. **Implement retry logic:** Retry failed agent calls with exponential backoff
3. **Add circuit breaker:** Stop calling a worker if it fails multiple times
4. **Implement caching:** Cache worker responses to reduce redundant calls
5. **Add tracing:** Enable distributed tracing to visualize request flows

## What's Next?

Continue learning:

- **[Writing OPA Policies](/tutorials/opa-policies/)** - Master authorization
- **[Adding Observability](/tutorials/observability/)** - Monitor distributed systems
- **[How-To: Error Handling](/guides/error-handling/)** - Production error patterns
- **[Examples: Multi-Agent Chat](/examples/multi-agent-chat/)** - Complex orchestration

## Troubleshooting

### "Connection refused" errors
- Ensure both agents are running
- Verify addresses/ports in orchestrator config match worker
- Check firewall rules

### "Authorization denied"
- Verify worker policy allows orchestrator's SPIFFE ID
- Check SPIFFE IDs match exactly (case-sensitive)
- Review OPA logs for policy evaluation

### Slow responses
- Check network latency between agents
- Increase timeouts in `call_agent()`
- Review worker performance/resource usage

See [Troubleshooting: Connection Issues](/troubleshooting/connections/) for more help.
