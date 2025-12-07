"""
Core agent classes for the AgentWeave SDK.

This module provides the base classes for building secure agents with
built-in identity verification, authorization, and A2A communication.
"""

import asyncio
import logging
import yaml
from abc import ABC, abstractmethod
from typing import Optional, Any, Type
from dataclasses import dataclass
from pathlib import Path

from agentweave.context import RequestContext, set_current_context
from agentweave.decorators import get_registered_capabilities


logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """
    Configuration for an agent.

    This is a simplified version. Full implementation would use
    Pydantic for validation as specified in the spec.
    """
    name: str
    trust_domain: str
    description: Optional[str] = None
    identity_provider: str = "spiffe"
    authz_provider: str = "opa"
    spiffe_endpoint: Optional[str] = None
    opa_endpoint: str = "http://localhost:8181"
    server_host: str = "0.0.0.0"
    server_port: int = 8443

    @classmethod
    def from_file(cls, path: str) -> "AgentConfig":
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        # Extract nested config (simplified)
        agent_data = data.get("agent", {})
        identity_data = data.get("identity", {})
        authz_data = data.get("authorization", {})
        server_data = data.get("server", {})

        return cls(
            name=agent_data.get("name"),
            trust_domain=agent_data.get("trust_domain"),
            description=agent_data.get("description"),
            identity_provider=identity_data.get("provider", "spiffe"),
            spiffe_endpoint=identity_data.get("spiffe_endpoint"),
            authz_provider=authz_data.get("provider", "opa"),
            opa_endpoint=authz_data.get("opa_endpoint", "http://localhost:8181"),
            server_host=server_data.get("host", "0.0.0.0"),
            server_port=server_data.get("port", 8443),
        )

    @classmethod
    def from_dict(cls, data: dict) -> "AgentConfig":
        """Create configuration from dictionary."""
        return cls(**data)


class BaseAgent(ABC):
    """
    Base class for all secure agents.

    This class provides core functionality:
    - Configuration loading and validation
    - Identity provider setup (SPIFFE or mTLS)
    - Authorization provider setup (OPA)
    - Transport layer with connection pool
    - Lifecycle management (start, stop, health checks)

    Subclasses must implement register_capabilities() to define
    their agent-specific capabilities.
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        identity: Optional[Any] = None,
        authz: Optional[Any] = None,
        transport: Optional[Any] = None
    ):
        """
        Initialize the base agent.

        Args:
            config: Agent configuration
            identity: Identity provider (for testing/DI)
            authz: Authorization enforcer (for testing/DI)
            transport: Transport layer (for testing/DI)
        """
        self._config = config
        self._identity = identity
        self._authz = authz
        self._transport = transport
        self._connection_pool = None
        self._server = None
        self._running = False

        if config:
            self._setup_from_config(config)

    def _setup_from_config(self, config: AgentConfig) -> None:
        """Setup agent from configuration."""
        logger.info(f"Initializing agent '{config.name}' in trust domain '{config.trust_domain}'")

        # Setup identity provider
        if self._identity is None:
            self._identity = self._create_identity_provider(config)

        # Setup authorization provider
        if self._authz is None:
            self._authz = self._create_authz_provider(config)

        # Setup transport layer
        if self._transport is None:
            self._transport = self._create_transport(config)

    def _create_identity_provider(self, config: AgentConfig) -> Any:
        """Create identity provider based on config."""
        if config.identity_provider == "spiffe":
            # Import and create SPIFFE provider
            # Note: In full implementation, would import from agentweave.identity.spiffe
            logger.info(f"Creating SPIFFE identity provider (endpoint: {config.spiffe_endpoint})")
            # Placeholder - would return actual SPIFFEIdentityProvider
            return None
        elif config.identity_provider == "mtls-static":
            logger.info("Creating static mTLS identity provider")
            # Placeholder - would return actual StaticMTLSProvider
            return None
        else:
            raise ValueError(f"Unknown identity provider: {config.identity_provider}")

    def _create_authz_provider(self, config: AgentConfig) -> Any:
        """Create authorization provider based on config."""
        if config.authz_provider == "opa":
            # Import and create OPA enforcer
            # Note: In full implementation, would import from agentweave.authz.opa
            logger.info(f"Creating OPA enforcer (endpoint: {config.opa_endpoint})")
            # Placeholder - would return actual OPAEnforcer
            return None
        elif config.authz_provider == "allow-all":
            logger.warning("Using allow-all authorization (DEVELOPMENT ONLY)")
            # Placeholder - would return AllowAllEnforcer
            return None
        else:
            raise ValueError(f"Unknown authorization provider: {config.authz_provider}")

    def _create_transport(self, config: AgentConfig) -> Any:
        """Create transport layer with connection pool."""
        logger.info("Creating secure transport layer")
        # Placeholder - would create SecureChannel with connection pool
        return None

    @classmethod
    def from_config(cls, config_path: str) -> "BaseAgent":
        """
        Create agent from configuration file.

        Args:
            config_path: Path to YAML configuration file

        Returns:
            Initialized agent instance
        """
        config = AgentConfig.from_file(config_path)
        return cls(config=config)

    @classmethod
    def from_dict(cls, config_dict: dict) -> "BaseAgent":
        """
        Create agent from configuration dictionary.

        Args:
            config_dict: Configuration dictionary

        Returns:
            Initialized agent instance
        """
        config = AgentConfig.from_dict(config_dict)
        return cls(config=config)

    def get_spiffe_id(self) -> str:
        """
        Get this agent's SPIFFE ID.

        Returns:
            The agent's SPIFFE ID
        """
        if self._identity and hasattr(self._identity, 'get_spiffe_id'):
            return self._identity.get_spiffe_id()

        # Fallback for testing/development
        if self._config:
            return f"spiffe://{self._config.trust_domain}/agent/{self._config.name}"

        return "spiffe://unknown/agent/unknown"

    async def start(self) -> None:
        """
        Start the agent.

        This method:
        1. Validates identity is available
        2. Starts the A2A server
        3. Registers capabilities
        4. Marks agent as running
        """
        if self._running:
            logger.warning("Agent already running")
            return

        logger.info(f"Starting agent {self.get_spiffe_id()}")

        # Verify identity provider is ready
        if self._identity and hasattr(self._identity, 'get_svid'):
            try:
                svid = await self._identity.get_svid()
                logger.info(f"Identity verified: {svid}")
            except Exception as e:
                logger.error(f"Failed to get SVID: {e}")
                raise RuntimeError("Cannot start agent without valid identity")

        # Register capabilities
        await self.register_capabilities()

        # Start A2A server (would be implemented with FastAPI)
        # self._server = A2AServer(self, config=self._config)
        # await self._server.start()

        self._running = True
        logger.info("Agent started successfully")

    async def stop(self) -> None:
        """
        Stop the agent gracefully.

        This method:
        1. Stops accepting new requests
        2. Waits for in-flight requests to complete
        3. Closes connection pool
        4. Shuts down server
        """
        if not self._running:
            logger.warning("Agent not running")
            return

        logger.info("Stopping agent...")

        # Stop server
        if self._server:
            await self._server.stop()

        # Close connection pool
        if self._connection_pool:
            await self._connection_pool.close()

        self._running = False
        logger.info("Agent stopped")

    async def health_check(self) -> dict[str, Any]:
        """
        Perform health check.

        Returns:
            Health status dictionary with component statuses
        """
        health = {
            "status": "healthy" if self._running else "stopped",
            "spiffe_id": self.get_spiffe_id(),
            "components": {}
        }

        # Check identity provider
        if self._identity:
            try:
                if hasattr(self._identity, 'get_svid'):
                    await self._identity.get_svid()
                health["components"]["identity"] = "healthy"
            except Exception as e:
                health["components"]["identity"] = f"unhealthy: {e}"
                health["status"] = "degraded"

        # Check authorization provider
        if self._authz:
            health["components"]["authorization"] = "healthy"

        # Check server
        if self._server and self._running:
            health["components"]["server"] = "running"
        elif self._running:
            health["components"]["server"] = "starting"

        return health

    @abstractmethod
    async def register_capabilities(self) -> None:
        """
        Register agent capabilities.

        Subclasses must implement this method to define their
        available capabilities. For SecureAgent, this is automatic.
        """
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    def run(self) -> None:
        """
        Run the agent (blocking).

        This is a convenience method for running the agent as a standalone
        application. It handles the async event loop and graceful shutdown.
        """
        async def _run():
            async with self:
                logger.info(f"Agent {self.get_spiffe_id()} is running")
                # Keep running until interrupted
                try:
                    while True:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Received shutdown signal")

        try:
            asyncio.run(_run())
        except KeyboardInterrupt:
            pass


class SecureAgent(BaseAgent):
    """
    Secure agent with automatic capability registration from decorated methods.

    This class extends BaseAgent to provide:
    - Automatic capability discovery from @capability decorated methods
    - Built-in A2A server for handling requests
    - Simplified agent-to-agent communication via call_agent()
    - Context manager support for easy lifecycle management

    Example:
        class DataSearchAgent(SecureAgent):
            @capability("search", description="Search the database")
            @requires_peer("spiffe://agentweave.io/agent/*")
            async def search(self, query: str) -> dict:
                return {"results": [...]}

        agent = DataSearchAgent.from_config("config.yaml")
        agent.run()
    """

    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        identity: Optional[Any] = None,
        authz: Optional[Any] = None,
        transport: Optional[Any] = None
    ):
        """Initialize the secure agent."""
        super().__init__(config, identity, authz, transport)
        self._capabilities = {}

    async def register_capabilities(self) -> None:
        """
        Automatically register capabilities from decorated methods.

        This method scans the instance for methods decorated with @capability
        and registers them as available capabilities.
        """
        logger.info("Auto-registering capabilities from decorated methods")

        # Scan instance methods for capability decorators
        for attr_name in dir(self):
            attr = getattr(self, attr_name)
            if hasattr(attr, '_capability_metadata'):
                metadata = attr._capability_metadata
                self._capabilities[metadata.name] = {
                    "name": metadata.name,
                    "description": metadata.description,
                    "handler": attr,
                    "requires_peer_patterns": metadata.requires_peer_patterns,
                    "audit_level": metadata.audit_level
                }
                logger.info(f"Registered capability: {metadata.name}")

        logger.info(f"Registered {len(self._capabilities)} capabilities")

    async def call_agent(
        self,
        target: str,
        task_type: str,
        payload: dict,
        timeout: float = 30.0
    ) -> Any:
        """
        Call another agent.

        This method handles the complete A2A call flow:
        1. Authorization check (outbound policy)
        2. Secure channel establishment
        3. Task submission via A2A protocol
        4. Result retrieval

        Args:
            target: Target agent's SPIFFE ID
            task_type: The capability/task type to invoke
            payload: Request payload
            timeout: Request timeout in seconds

        Returns:
            Task result from the target agent

        Raises:
            PermissionError: If authorization fails
            TimeoutError: If request times out
            ConnectionError: If unable to reach target
        """
        my_id = self.get_spiffe_id()

        logger.info(f"Calling agent {target} with task_type={task_type}")

        # Check authorization (outbound)
        if self._authz and hasattr(self._authz, 'check_outbound'):
            decision = await self._authz.check_outbound(
                caller_id=my_id,
                callee_id=target,
                action=task_type,
                context={"payload_size": len(str(payload))}
            )

            if not decision.allowed:
                logger.error(f"Outbound authorization denied: {decision.reason}")
                raise PermissionError(
                    f"Not authorized to call {target}: {decision.reason}"
                )

            logger.info(f"Outbound authorization granted (audit_id: {decision.audit_id})")

        # In full implementation, would use A2AClient to send task
        # For now, return a placeholder
        logger.info(f"Task submitted to {target} (would send via A2A protocol)")

        # Placeholder result
        return {
            "status": "completed",
            "target": target,
            "task_type": task_type,
            "payload": payload
        }

    async def handle_request(
        self,
        caller_id: str,
        task_type: str,
        payload: dict
    ) -> Any:
        """
        Handle an incoming A2A request.

        This method is called by the A2A server when a request arrives.
        It sets up the request context and dispatches to the appropriate
        capability handler.

        Args:
            caller_id: SPIFFE ID of the calling agent
            task_type: The capability being invoked
            payload: Request payload

        Returns:
            Result from the capability handler

        Raises:
            ValueError: If capability not found
            PermissionError: If authorization fails
        """
        # Create request context
        context = RequestContext.create(
            caller_id=caller_id,
            metadata={"task_type": task_type}
        )

        # Set context for this request
        set_current_context(context)

        try:
            # Look up capability
            if task_type not in self._capabilities:
                raise ValueError(f"Unknown capability: {task_type}")

            capability = self._capabilities[task_type]
            handler = capability["handler"]

            # Call the handler (decorators will handle authz checks)
            result = await handler(**payload)

            return result

        finally:
            # Clear context
            set_current_context(None)

    def get_capabilities(self) -> list[dict]:
        """
        Get list of registered capabilities.

        Returns:
            List of capability metadata dictionaries
        """
        return [
            {
                "name": cap["name"],
                "description": cap["description"],
                "requires_peer_patterns": cap["requires_peer_patterns"],
                "audit_level": cap["audit_level"]
            }
            for cap in self._capabilities.values()
        ]
