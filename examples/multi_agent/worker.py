"""
Worker Agent Example

This agent performs actual work delegated by the orchestrator.
Demonstrates:
- Restricted peer requirements
- Business logic implementation
- Capability-specific processing
- Error handling and reporting
"""

from agentweave import SecureAgent, capability, requires_peer
from agentweave.types import TaskResult
import hashlib
import time


class WorkerAgent(SecureAgent):
    """Worker agent that processes individual items."""

    @capability("process_item")
    @requires_peer("spiffe://hvs.solutions/agent/orchestrator/*")
    async def process_item(self, item: dict) -> TaskResult:
        """
        Process a single item.

        Only the orchestrator agent can call this capability.

        Args:
            item: The item to process

        Returns:
            TaskResult with processed item
        """
        start_time = time.time()

        try:
            # Simulate processing
            processed = {
                "original": item,
                "checksum": self._compute_checksum(item),
                "processed_at": self.current_time(),
                "processor": self.config.agent.name
            }

            # Simulate some work
            await self._simulate_work(item.get("complexity", "medium"))

            elapsed = time.time() - start_time

            return TaskResult(
                status="completed",
                artifacts=[{
                    "type": "processed_item",
                    "data": processed
                }],
                metadata={
                    "processing_time_seconds": elapsed,
                    "worker_id": self.spiffe_id
                }
            )

        except Exception as e:
            self.logger.error(f"Failed to process item: {e}")
            return TaskResult(
                status="failed",
                error=str(e),
                metadata={
                    "worker_id": self.spiffe_id
                }
            )

    @capability("ping")
    @requires_peer("spiffe://hvs.solutions/agent/*")
    async def ping(self) -> TaskResult:
        """
        Health check endpoint.

        Returns:
            TaskResult confirming agent is healthy
        """
        return TaskResult(
            status="completed",
            artifacts=[{
                "type": "pong",
                "data": {
                    "agent": self.config.agent.name,
                    "spiffe_id": self.spiffe_id,
                    "status": "healthy"
                }
            }]
        )

    def _compute_checksum(self, data: dict) -> str:
        """Compute SHA256 checksum of data."""
        import json
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    async def _simulate_work(self, complexity: str):
        """Simulate processing work based on complexity."""
        import asyncio

        delays = {
            "low": 0.1,
            "medium": 0.5,
            "high": 1.0
        }

        await asyncio.sleep(delays.get(complexity, 0.5))


if __name__ == "__main__":
    agent = WorkerAgent.from_config("config/worker.yaml")
    agent.run()
