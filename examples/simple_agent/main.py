"""
Simple Echo Agent Example

This demonstrates the most basic AgentWeave agent:
- Single capability (echo)
- Automatic SPIFFE identity
- Built-in mTLS and authorization
- Configuration-driven setup
"""

from agentweave import SecureAgent, capability


class EchoAgent(SecureAgent):
    """A simple agent that echoes messages back."""

    @capability("echo")
    async def echo(self, message: str) -> dict:
        """
        Echo a message back to the caller.

        Args:
            message: The message to echo

        Returns:
            Dictionary containing the echoed message
        """
        return {"echo": message, "timestamp": self.current_time()}


if __name__ == "__main__":
    # Load configuration from config.yaml
    # This handles:
    # - SPIFFE identity initialization
    # - OPA authorization setup
    # - A2A server startup
    # - Health check endpoints
    agent = EchoAgent.from_config("config.yaml")

    # Start the agent server
    # Blocks until SIGTERM/SIGINT
    agent.run()
