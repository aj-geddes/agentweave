"""
Test cluster management for integration testing.

This module provides utilities for spinning up local SPIRE and OPA servers
for integration testing with real identity and authorization.
"""

import asyncio
import os
import tempfile
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
import docker
import yaml


@dataclass
class ClusterConfig:
    """Configuration for test cluster."""

    spire_server_image: str = "ghcr.io/spiffe/spire-server:1.9.0"
    spire_agent_image: str = "ghcr.io/spiffe/spire-agent:1.9.0"
    opa_image: str = "openpolicyagent/opa:latest"
    trust_domain: str = "test.local"
    cleanup_on_exit: bool = True
    network_name: str = "hvs-test-network"


@dataclass
class AgentRegistration:
    """Registration for a test agent."""

    spiffe_id: str
    selectors: List[str]
    parent_id: str = "spiffe://test.local/spire-agent"


class TestCluster:
    """
    Test cluster for integration testing.

    Spins up local SPIRE server, SPIRE agent, and OPA server using Docker.
    Provides utilities for registering test agents and managing the lifecycle.

    Example:
        async with TestCluster() as cluster:
            # Register an agent
            await cluster.register_agent(
                spiffe_id="spiffe://test.local/agent/search",
                selectors=["unix:uid:1000"]
            )

            # Deploy and test your agent
            agent = await cluster.deploy_agent(MySearchAgent)
            result = await agent.search("test query")

            # Cluster automatically cleans up on exit
    """

    def __init__(self, config: Optional[ClusterConfig] = None):
        """
        Initialize test cluster.

        Args:
            config: Cluster configuration (uses defaults if not provided)
        """
        self.config = config or ClusterConfig()
        self._docker_client: Optional[docker.DockerClient] = None
        self._containers: Dict[str, Any] = {}
        self._network: Optional[Any] = None
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None
        self._agent_registrations: List[AgentRegistration] = []
        self._deployed_agents: List[Any] = []

    async def start(self):
        """Start the test cluster."""
        print("Starting HVS test cluster...")

        # Initialize Docker client
        self._docker_client = docker.from_env()

        # Create temporary directory for configs
        self._temp_dir = tempfile.TemporaryDirectory()
        self._config_path = Path(self._temp_dir.name)

        # Create Docker network
        await self._create_network()

        # Start SPIRE server
        await self._start_spire_server()

        # Wait for SPIRE server to be ready
        await self._wait_for_spire_server()

        # Start SPIRE agent
        await self._start_spire_agent()

        # Wait for SPIRE agent to be ready
        await self._wait_for_spire_agent()

        # Start OPA
        await self._start_opa()

        print("Test cluster started successfully")

    async def stop(self):
        """Stop the test cluster and clean up resources."""
        print("Stopping HVS test cluster...")

        # Stop deployed agents
        for agent in self._deployed_agents:
            try:
                await agent.stop()
            except Exception as e:
                print(f"Error stopping agent: {e}")

        # Stop containers
        if self.config.cleanup_on_exit:
            for name, container in self._containers.items():
                try:
                    print(f"Stopping container: {name}")
                    container.stop(timeout=10)
                    container.remove()
                except Exception as e:
                    print(f"Error stopping container {name}: {e}")

            # Remove network
            if self._network:
                try:
                    self._network.remove()
                except Exception as e:
                    print(f"Error removing network: {e}")

        # Clean up temp directory
        if self._temp_dir:
            self._temp_dir.cleanup()

        # Close Docker client
        if self._docker_client:
            self._docker_client.close()

        print("Test cluster stopped")

    async def __aenter__(self):
        """Context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.stop()

    def _create_network(self):
        """Create Docker network for cluster."""
        print(f"Creating network: {self.config.network_name}")
        try:
            self._network = self._docker_client.networks.get(self.config.network_name)
        except docker.errors.NotFound:
            self._network = self._docker_client.networks.create(
                self.config.network_name,
                driver="bridge"
            )

    def _start_spire_server(self):
        """Start SPIRE server container."""
        print("Starting SPIRE server...")

        # Create server config
        server_config = {
            "server": {
                "trust_domain": self.config.trust_domain,
                "bind_address": "0.0.0.0",
                "bind_port": "8081",
                "data_dir": "/opt/spire/data/server",
                "log_level": "DEBUG",
                "ca_ttl": "24h",
                "default_x509_svid_ttl": "1h",
            },
            "plugins": {
                "DataStore": [
                    {"sql": {"plugin_data": {"database_type": "sqlite3", "connection_string": "/opt/spire/data/server/datastore.sqlite3"}}}
                ],
                "NodeAttestor": [
                    {"join_token": {"plugin_data": {}}}
                ],
                "KeyManager": [
                    {"disk": {"plugin_data": {"keys_path": "/opt/spire/data/server/keys.json"}}}
                ],
            },
        }

        # Write config file
        server_config_path = self._config_path / "server.conf"
        with open(server_config_path, "w") as f:
            f.write(self._hcl_encode(server_config))

        # Start container
        self._containers["spire-server"] = self._docker_client.containers.run(
            self.config.spire_server_image,
            command=["-config", "/opt/spire/conf/server.conf"],
            name="hvs-test-spire-server",
            network=self.config.network_name,
            volumes={
                str(server_config_path): {"bind": "/opt/spire/conf/server.conf", "mode": "ro"}
            },
            detach=True,
            remove=False,
        )

    def _start_spire_agent(self):
        """Start SPIRE agent container."""
        print("Starting SPIRE agent...")

        # Create agent config
        agent_config = {
            "agent": {
                "trust_domain": self.config.trust_domain,
                "server_address": "hvs-test-spire-server",
                "server_port": "8081",
                "socket_path": "/run/spire/sockets/agent.sock",
                "data_dir": "/opt/spire/data/agent",
                "log_level": "DEBUG",
            },
            "plugins": {
                "NodeAttestor": [
                    {"join_token": {"plugin_data": {}}}
                ],
                "KeyManager": [
                    {"disk": {"plugin_data": {"directory": "/opt/spire/data/agent"}}}
                ],
                "WorkloadAttestor": [
                    {"unix": {"plugin_data": {}}}
                ],
            },
        }

        # Write config file
        agent_config_path = self._config_path / "agent.conf"
        with open(agent_config_path, "w") as f:
            f.write(self._hcl_encode(agent_config))

        # Start container
        self._containers["spire-agent"] = self._docker_client.containers.run(
            self.config.spire_agent_image,
            command=["-config", "/opt/spire/conf/agent.conf"],
            name="hvs-test-spire-agent",
            network=self.config.network_name,
            volumes={
                str(agent_config_path): {"bind": "/opt/spire/conf/agent.conf", "mode": "ro"}
            },
            detach=True,
            remove=False,
        )

    def _start_opa(self):
        """Start OPA container."""
        print("Starting OPA...")

        # Create default policy
        default_policy = """
package agentweave.authz

import rego.v1

default allow := false

# Allow all for testing
allow if {
    input.caller_spiffe_id
}
"""

        # Write policy file
        policy_path = self._config_path / "policy.rego"
        with open(policy_path, "w") as f:
            f.write(default_policy)

        # Start container
        self._containers["opa"] = self._docker_client.containers.run(
            self.config.opa_image,
            command=["run", "--server", "--addr", "0.0.0.0:8181", "/policies"],
            name="hvs-test-opa",
            network=self.config.network_name,
            ports={"8181/tcp": 8181},
            volumes={
                str(self._config_path): {"bind": "/policies", "mode": "ro"}
            },
            detach=True,
            remove=False,
        )

    async def _wait_for_spire_server(self, timeout: int = 30):
        """Wait for SPIRE server to be ready."""
        print("Waiting for SPIRE server to be ready...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                result = self._containers["spire-server"].exec_run(
                    "spire-server healthcheck"
                )
                if result.exit_code == 0:
                    print("SPIRE server is ready")
                    return
            except Exception:
                pass

            await asyncio.sleep(1)

        raise TimeoutError("SPIRE server failed to start")

    async def _wait_for_spire_agent(self, timeout: int = 30):
        """Wait for SPIRE agent to be ready."""
        print("Waiting for SPIRE agent to be ready...")
        start_time = time.time()

        # First, generate a join token
        result = self._containers["spire-server"].exec_run(
            ["spire-server", "token", "generate", "-spiffeID", "spiffe://test.local/spire-agent"]
        )
        token = result.output.decode().strip()
        print(f"Generated join token: {token}")

        # Bootstrap agent with token
        self._containers["spire-agent"].exec_run(
            ["spire-agent", "run", "-joinToken", token],
            detach=True
        )

        while time.time() - start_time < timeout:
            try:
                result = self._containers["spire-agent"].exec_run(
                    "spire-agent healthcheck -socketPath /run/spire/sockets/agent.sock"
                )
                if result.exit_code == 0:
                    print("SPIRE agent is ready")
                    return
            except Exception:
                pass

            await asyncio.sleep(1)

        raise TimeoutError("SPIRE agent failed to start")

    async def register_agent(
        self,
        spiffe_id: str,
        selectors: List[str],
        parent_id: str = "spiffe://test.local/spire-agent",
    ):
        """
        Register an agent with SPIRE.

        Args:
            spiffe_id: SPIFFE ID to assign to the agent
            selectors: List of selectors (e.g., ["unix:uid:1000"])
            parent_id: Parent SPIFFE ID

        Example:
            await cluster.register_agent(
                spiffe_id="spiffe://test.local/agent/search",
                selectors=["unix:uid:1000"]
            )
        """
        print(f"Registering agent: {spiffe_id}")

        # Build command
        cmd = [
            "spire-server", "entry", "create",
            "-spiffeID", spiffe_id,
            "-parentID", parent_id,
        ]

        for selector in selectors:
            cmd.extend(["-selector", selector])

        # Execute registration
        result = self._containers["spire-server"].exec_run(cmd)

        if result.exit_code != 0:
            raise RuntimeError(f"Failed to register agent: {result.output.decode()}")

        self._agent_registrations.append(
            AgentRegistration(
                spiffe_id=spiffe_id,
                selectors=selectors,
                parent_id=parent_id,
            )
        )

        print(f"Agent registered: {spiffe_id}")

    async def deploy_agent(self, agent_class: Type, config: Optional[Dict[str, Any]] = None):
        """
        Deploy an agent in the test cluster.

        Args:
            agent_class: Agent class to instantiate
            config: Optional configuration override

        Returns:
            Deployed agent instance

        Example:
            agent = await cluster.deploy_agent(MySearchAgent)
            result = await agent.search("test")
        """
        # This would create an actual agent instance
        # For now, return a placeholder
        print(f"Deploying agent: {agent_class.__name__}")

        # In a real implementation, this would:
        # 1. Create agent configuration
        # 2. Register with SPIRE
        # 3. Start the agent
        # 4. Return the running instance

        class DeployedAgent:
            def __init__(self, agent_class, cluster):
                self.agent_class = agent_class
                self.cluster = cluster
                self.spiffe_id = f"spiffe://{cluster.config.trust_domain}/agent/{agent_class.__name__.lower()}"

            async def stop(self):
                pass

        agent = DeployedAgent(agent_class, self)
        self._deployed_agents.append(agent)
        return agent

    def get_spire_socket_path(self) -> str:
        """Get path to SPIRE agent socket."""
        return "/run/spire/sockets/agent.sock"

    def get_opa_endpoint(self) -> str:
        """Get OPA endpoint URL."""
        return "http://localhost:8181"

    def _hcl_encode(self, data: Dict) -> str:
        """
        Encode dict as HCL (simplified).

        This is a simple encoder for basic SPIRE configs.
        For production use, consider using python-hcl2.
        """
        lines = []

        def encode_value(value, indent=0):
            if isinstance(value, dict):
                result = "{\n"
                for k, v in value.items():
                    result += "  " * (indent + 1) + f"{k} = "
                    result += encode_value(v, indent + 1)
                    result += "\n"
                result += "  " * indent + "}"
                return result
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    # List of dicts (plugins)
                    result = ""
                    for item in value:
                        result += encode_value(item, indent)
                    return result
                else:
                    # Simple list
                    return "[" + ", ".join(f'"{v}"' for v in value) + "]"
            elif isinstance(value, str):
                return f'"{value}"'
            elif isinstance(value, bool):
                return str(value).lower()
            else:
                return str(value)

        for key, value in data.items():
            lines.append(f"{key} " + encode_value(value))

        return "\n".join(lines)


# Context manager decorator for async with support
@asynccontextmanager
async def test_cluster(config: Optional[ClusterConfig] = None):
    """
    Async context manager for test cluster.

    Example:
        async with test_cluster() as cluster:
            await cluster.register_agent(...)
            # Use cluster
    """
    cluster = TestCluster(config)
    await cluster.start()
    try:
        yield cluster
    finally:
        await cluster.stop()
