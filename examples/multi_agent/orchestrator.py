"""
Orchestrator Agent Example

This agent coordinates multiple worker agents to complete complex tasks.
Demonstrates:
- Agent-to-agent communication
- Task decomposition
- Error handling
- Result aggregation
"""

from agentweave import SecureAgent, capability, requires_peer
from agentweave.types import TaskResult
import asyncio


class OrchestratorAgent(SecureAgent):
    """Orchestrates work across multiple worker agents."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Define worker agents this orchestrator can call
        self.worker_agents = [
            "spiffe://hvs.solutions/agent/worker-1/dev",
            "spiffe://hvs.solutions/agent/worker-2/dev",
            "spiffe://hvs.solutions/agent/worker-3/dev"
        ]

    @capability("process_batch")
    @requires_peer("spiffe://hvs.solutions/agent/*")
    async def process_batch(self, items: list[dict]) -> TaskResult:
        """
        Process a batch of items by distributing work to workers.

        Args:
            items: List of items to process

        Returns:
            TaskResult with aggregated results from all workers
        """
        self.logger.info(f"Processing batch of {len(items)} items")

        # Distribute items across workers using round-robin
        tasks = []
        for idx, item in enumerate(items):
            worker_idx = idx % len(self.worker_agents)
            worker_id = self.worker_agents[worker_idx]

            # Call worker asynchronously
            # SDK handles all security: mTLS, authz, retry
            task = self.call_agent(
                target=worker_id,
                task_type="process_item",
                payload={"item": item}
            )
            tasks.append(task)

        # Wait for all workers to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Aggregate results
        successful = []
        failed = []

        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Worker task {idx} failed: {result}")
                failed.append({"index": idx, "error": str(result)})
            else:
                successful.append(result.artifacts[0]["data"])

        return TaskResult(
            status="completed" if not failed else "partial",
            artifacts=[{
                "type": "batch_results",
                "data": {
                    "successful": successful,
                    "failed": failed,
                    "total": len(items),
                    "success_rate": len(successful) / len(items)
                }
            }]
        )

    @capability("health_check")
    async def health_check(self) -> TaskResult:
        """
        Check health of all worker agents.

        Returns:
            TaskResult with health status of each worker
        """
        health_statuses = {}

        for worker_id in self.worker_agents:
            try:
                result = await self.call_agent(
                    target=worker_id,
                    task_type="ping",
                    payload={},
                    timeout=5.0
                )
                health_statuses[worker_id] = {
                    "status": "healthy",
                    "latency_ms": result.metadata.get("latency_ms", 0)
                }
            except Exception as e:
                health_statuses[worker_id] = {
                    "status": "unhealthy",
                    "error": str(e)
                }

        all_healthy = all(
            status["status"] == "healthy"
            for status in health_statuses.values()
        )

        return TaskResult(
            status="completed",
            artifacts=[{
                "type": "health_report",
                "data": {
                    "workers": health_statuses,
                    "all_healthy": all_healthy
                }
            }]
        )


if __name__ == "__main__":
    agent = OrchestratorAgent.from_config("config/orchestrator.yaml")
    agent.run()
