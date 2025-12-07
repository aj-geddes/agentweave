"""
Example agent demonstrating the AgentWeave SDK usage.

This example shows how to create a DataSearchAgent with secure capabilities.
"""

import asyncio
from agentweave import SecureAgent, capability, requires_peer, audit_log


class DataSearchAgent(SecureAgent):
    """Example agent that searches data stores."""

    @capability("search", description="Search the database")
    @requires_peer("spiffe://hvs.solutions/agent/*")
    async def search(self, query: str, filters: dict = None) -> dict:
        """
        Search for data matching query.

        Args:
            query: Search query string
            filters: Optional filters to apply

        Returns:
            Search results
        """
        # Simulate database search
        await asyncio.sleep(0.1)  # Simulate I/O

        return {
            "results": [
                {"id": 1, "title": f"Result for {query}", "score": 0.95},
                {"id": 2, "title": f"Another result for {query}", "score": 0.87}
            ],
            "total": 2,
            "query": query,
            "filters": filters or {}
        }

    @capability("index", description="Index new documents")
    @requires_peer("spiffe://hvs.solutions/agent/orchestrator")
    @audit_log(level="warning")
    async def index(self, documents: list) -> dict:
        """
        Index new documents (restricted to orchestrator).

        Args:
            documents: List of documents to index

        Returns:
            Indexing result
        """
        # Simulate indexing
        await asyncio.sleep(0.2)

        return {
            "indexed": len(documents),
            "status": "success"
        }


async def main():
    """Example usage of the DataSearchAgent."""

    # Create agent configuration
    config = {
        "name": "data-search",
        "trust_domain": "hvs.solutions",
        "description": "Search agent for data stores"
    }

    # Create agent from config
    agent = DataSearchAgent.from_dict(config)

    print(f"Agent SPIFFE ID: {agent.get_spiffe_id()}")

    # Start the agent
    await agent.start()

    # Get registered capabilities
    capabilities = agent.get_capabilities()
    print(f"\nRegistered capabilities: {len(capabilities)}")
    for cap in capabilities:
        print(f"  - {cap['name']}: {cap['description']}")

    # Health check
    health = await agent.health_check()
    print(f"\nHealth status: {health}")

    # Stop the agent
    await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
