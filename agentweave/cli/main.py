"""
AgentWeave SDK - CLI Main Entry Point
"""

import sys
import json
import time
import asyncio
from pathlib import Path
from typing import Optional

import click
import httpx
import yaml
from rich.console import Console

from agentweave.cli.utils import (
    load_config,
    success,
    error,
    warning,
    info,
    print_json,
    print_key_value,
    validate_spiffe_id,
    format_duration,
)


console = Console()


@click.group()
@click.version_option(version="0.1.0", prog_name="agentweave")
def cli():
    """
    AgentWeave SDK - Command Line Interface

    Manage and interact with secure agents with built-in
    SPIFFE identity, mTLS, and OPA authorization.
    """
    pass


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
def validate(config_file):
    """
    Validate agent configuration file.

    Checks:
    - YAML syntax
    - Required fields
    - SPIFFE endpoint connectivity
    - OPA endpoint connectivity
    - Security settings
    """
    info(f"Validating configuration: {config_file}")

    # Load configuration
    try:
        config = load_config(config_file)
    except Exception as e:
        error(f"Failed to load configuration: {e}")
        sys.exit(1)

    errors = []
    warnings = []

    # Validate required sections
    required_sections = ["agent", "identity", "authorization", "transport", "server"]
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: {section}")

    if errors:
        for err in errors:
            error(err)
        sys.exit(1)

    # Validate agent section
    agent_config = config.get("agent", {})
    if not agent_config.get("name"):
        errors.append("agent.name is required")
    if not agent_config.get("trust_domain"):
        errors.append("agent.trust_domain is required")

    # Validate identity section
    identity_config = config.get("identity", {})
    provider = identity_config.get("provider", "spiffe")

    if provider == "spiffe":
        spiffe_endpoint = identity_config.get(
            "spiffe_endpoint", "unix:///run/spire/sockets/agent.sock"
        )
        info(f"SPIFFE endpoint: {spiffe_endpoint}")

        # Check SPIFFE endpoint connectivity
        if spiffe_endpoint.startswith("unix://"):
            socket_path = spiffe_endpoint[7:]
            if not Path(socket_path).exists():
                warnings.append(f"SPIFFE socket not found: {socket_path}")
            else:
                success(f"SPIFFE socket found: {socket_path}")
        else:
            info("TCP SPIFFE endpoint configured (skipping connectivity check)")

    # Validate authorization section
    authz_config = config.get("authorization", {})
    authz_provider = authz_config.get("provider", "opa")

    if authz_provider == "opa":
        opa_endpoint = authz_config.get("opa_endpoint", "http://localhost:8181")
        info(f"OPA endpoint: {opa_endpoint}")

        # Check OPA endpoint connectivity
        try:
            response = httpx.get(f"{opa_endpoint}/health", timeout=5)
            if response.status_code == 200:
                success(f"OPA endpoint reachable: {opa_endpoint}")
            else:
                warnings.append(
                    f"OPA endpoint returned status {response.status_code}: {opa_endpoint}"
                )
        except httpx.ConnectError:
            warnings.append(f"OPA endpoint not reachable: {opa_endpoint}")
        except Exception as e:
            warnings.append(f"Error checking OPA endpoint: {e}")

    # Validate transport section
    transport_config = config.get("transport", {})
    peer_verification = transport_config.get("peer_verification", "strict")

    if peer_verification == "none":
        errors.append(
            "transport.peer_verification cannot be 'none' - security violation"
        )

    tls_min_version = transport_config.get("tls_min_version", "1.3")
    if tls_min_version not in ["1.2", "1.3"]:
        errors.append(
            f"transport.tls_min_version must be '1.2' or '1.3', got '{tls_min_version}'"
        )

    # Validate server section
    server_config = config.get("server", {})
    if not server_config.get("port"):
        warnings.append("server.port not specified, will use default")

    # Print warnings
    if warnings:
        console.print()
        for warn in warnings:
            warning(warn)

    # Print errors and exit if any
    if errors:
        console.print()
        for err in errors:
            error(err)
        console.print()
        error("Configuration validation failed")
        sys.exit(1)

    console.print()
    success("Configuration validation passed")

    # Display summary
    summary = {
        "Agent Name": agent_config.get("name"),
        "Trust Domain": agent_config.get("trust_domain"),
        "Identity Provider": provider,
        "Authorization Provider": authz_provider,
        "Server Port": server_config.get("port", 8443),
        "TLS Min Version": tls_min_version,
        "Peer Verification": peer_verification,
    }

    print_key_value(summary, title="Configuration Summary")


@cli.group(name="card")
def card_group():
    """Agent card operations."""
    pass


@card_group.command(name="generate")
@click.argument("config_file", type=click.Path(exists=True))
@click.option(
    "--output",
    "-o",
    type=click.Path(),
    help="Output file (default: stdout)",
)
def card_generate(config_file, output):
    """
    Generate Agent Card JSON from configuration.

    The Agent Card advertises the agent's capabilities,
    endpoints, and authentication requirements following
    the A2A protocol specification.
    """
    info(f"Generating agent card from: {config_file}")

    # Load configuration
    config = load_config(config_file)

    # Extract agent info
    agent_config = config.get("agent", {})
    server_config = config.get("server", {})
    identity_config = config.get("identity", {})

    # Build SPIFFE ID
    trust_domain = agent_config.get("trust_domain", "example.com")
    agent_name = agent_config.get("name", "unnamed-agent")
    spiffe_id = f"spiffe://{trust_domain}/agent/{agent_name}"

    # Build server URL
    host = server_config.get("host", "0.0.0.0")
    port = server_config.get("port", 8443)
    protocol = server_config.get("protocol", "a2a")

    # Use localhost for 0.0.0.0
    display_host = "localhost" if host == "0.0.0.0" else host
    url = f"https://{display_host}:{port}"

    # Build capabilities
    capabilities = []
    for cap in agent_config.get("capabilities", []):
        capability = {
            "name": cap.get("name"),
            "description": cap.get("description", ""),
            "input_modes": cap.get("input_modes", ["application/json"]),
            "output_modes": cap.get("output_modes", ["application/json"]),
        }
        capabilities.append(capability)

    # Build agent card
    agent_card = {
        "name": agent_name,
        "description": agent_config.get("description", ""),
        "url": url,
        "version": "1.0.0",
        "capabilities": capabilities,
        "authentication": {
            "schemes": [
                {
                    "type": "mtls",
                    "description": "Mutual TLS with SPIFFE identity",
                }
            ]
        },
        "extensions": {
            "spiffe_id": spiffe_id,
            "trust_domain": trust_domain,
            "protocol": protocol,
        },
    }

    # Output agent card
    if output:
        with open(output, "w") as f:
            json.dump(agent_card, f, indent=2)
        success(f"Agent card written to: {output}")
    else:
        print_json(agent_card)


@cli.command()
@click.argument("spiffe_id")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Agent configuration file (for identity)",
)
@click.option(
    "--timeout",
    "-t",
    type=float,
    default=5.0,
    help="Timeout in seconds (default: 5.0)",
)
def ping(spiffe_id, config, timeout):
    """
    Discover and ping a target agent.

    Verifies mTLS connectivity, retrieves the agent card,
    and displays latency information.

    Example:
        agentweave ping spiffe://agentweave.io/agent/search
    """
    if not validate_spiffe_id(spiffe_id):
        error(f"Invalid SPIFFE ID format: {spiffe_id}")
        sys.exit(1)

    info(f"Pinging agent: {spiffe_id}")

    # In a real implementation, this would:
    # 1. Use SPIFFE identity to establish mTLS
    # 2. Discover the agent's endpoint
    # 3. Fetch the agent card
    # 4. Measure latency

    # For now, provide a placeholder implementation
    warning("Note: This is a placeholder implementation")
    warning("Full implementation requires SPIFFE Workload API integration")

    info("Would perform:")
    info("  1. Fetch SVID from SPIRE agent")
    info("  2. Resolve agent endpoint from SPIFFE ID")
    info("  3. Establish mTLS connection")
    info("  4. Fetch /.well-known/agent.json")
    info("  5. Measure round-trip time")

    # Simulate ping
    console.print()
    info(f"Target: {spiffe_id}")
    info(f"Timeout: {timeout}s")


@cli.group(name="authz")
def authz_group():
    """Authorization policy operations."""
    pass


@authz_group.command(name="check")
@click.option(
    "--caller",
    required=True,
    help="Caller SPIFFE ID",
)
@click.option(
    "--callee",
    required=True,
    help="Callee SPIFFE ID",
)
@click.option(
    "--action",
    required=True,
    help="Action/capability being invoked",
)
@click.option(
    "--opa-endpoint",
    default="http://localhost:8181",
    help="OPA endpoint (default: http://localhost:8181)",
)
@click.option(
    "--policy-path",
    default="agentweave/authz",
    help="OPA policy path (default: agentweave/authz)",
)
def authz_check(caller, callee, action, opa_endpoint, policy_path):
    """
    Query OPA for authorization decision.

    Useful for debugging policies and understanding
    why certain agent-to-agent calls are allowed or denied.

    Example:
        agentweave authz check \\
          --caller spiffe://agentweave.io/agent/orchestrator \\
          --callee spiffe://agentweave.io/agent/search \\
          --action search
    """
    if not validate_spiffe_id(caller):
        error(f"Invalid caller SPIFFE ID: {caller}")
        sys.exit(1)

    if not validate_spiffe_id(callee):
        error(f"Invalid callee SPIFFE ID: {callee}")
        sys.exit(1)

    info("Querying OPA for authorization decision")

    # Build OPA input
    opa_input = {
        "input": {
            "caller_spiffe_id": caller,
            "callee_spiffe_id": callee,
            "action": action,
        }
    }

    # Query OPA
    try:
        url = f"{opa_endpoint}/v1/data/{policy_path.replace('.', '/')}"
        info(f"OPA URL: {url}")

        response = httpx.post(url, json=opa_input, timeout=5)
        response.raise_for_status()

        result = response.json()
        decision = result.get("result", {})

        console.print()

        # Display decision
        allowed = decision.get("allow", False)
        if allowed:
            success("ALLOWED")
        else:
            error("DENIED")

        # Display details
        if "reason" in decision:
            info(f"Reason: {decision['reason']}")

        console.print()
        print_json(decision, title="Full OPA Response")

    except httpx.ConnectError:
        error(f"Failed to connect to OPA at {opa_endpoint}")
        error("Is OPA running?")
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        error(f"OPA request failed: {e}")
        sys.exit(1)
    except Exception as e:
        error(f"Error querying OPA: {e}")
        sys.exit(1)


@cli.command()
@click.argument("config_file", type=click.Path(exists=True))
@click.option(
    "--host",
    help="Override server host from config",
)
@click.option(
    "--port",
    type=int,
    help="Override server port from config",
)
def serve(config_file, host, port):
    """
    Start the agent server.

    Loads configuration, initializes identity and authorization
    components, and runs the agent server until interrupted.

    Example:
        agentweave serve config.yaml
        agentweave serve config.yaml --port 9443
    """
    info(f"Starting agent from configuration: {config_file}")

    # Load configuration
    config = load_config(config_file)

    # Extract server settings
    server_config = config.get("server", {})
    agent_config = config.get("agent", {})

    server_host = host or server_config.get("host", "0.0.0.0")
    server_port = port or server_config.get("port", 8443)
    agent_name = agent_config.get("name", "unnamed-agent")

    console.print()
    info(f"Agent Name: {agent_name}")
    info(f"Server: {server_host}:{server_port}")
    console.print()

    # In a real implementation, this would:
    # 1. Initialize SPIFFEIdentityProvider
    # 2. Initialize OPAEnforcer
    # 3. Initialize SecureAgent
    # 4. Start FastAPI server
    # 5. Handle graceful shutdown

    warning("Note: This is a placeholder implementation")
    warning("Full implementation requires core SDK components")

    info("Would perform:")
    info("  1. Load configuration and validate")
    info("  2. Initialize SPIFFE identity provider")
    info("  3. Initialize OPA policy enforcer")
    info("  4. Initialize transport layer")
    info("  5. Start A2A server")
    info("  6. Register signal handlers for graceful shutdown")

    console.print()
    info("Press Ctrl+C to stop (in real implementation)")


@cli.command()
@click.argument("url")
@click.option(
    "--timeout",
    "-t",
    type=float,
    default=5.0,
    help="Timeout in seconds (default: 5.0)",
)
def health(url, timeout):
    """
    Check agent health endpoint.

    Queries the /health endpoint and displays the agent's
    health status, uptime, and other diagnostics.

    Example:
        agentweave health https://localhost:8443/health
    """
    info(f"Checking health: {url}")

    try:
        start_time = time.time()
        response = httpx.get(url, timeout=timeout, verify=False)  # Note: verify=False for dev
        elapsed = time.time() - start_time

        if response.status_code == 200:
            success(f"Health check passed ({format_duration(elapsed)})")

            try:
                health_data = response.json()
                console.print()
                print_json(health_data, title="Health Status")
            except json.JSONDecodeError:
                info("Response is not JSON")
                console.print(response.text)
        else:
            warning(f"Health check returned status {response.status_code}")
            console.print(response.text)

    except httpx.ConnectError:
        error(f"Failed to connect to {url}")
        error("Is the agent running?")
        sys.exit(1)
    except httpx.TimeoutException:
        error(f"Health check timed out after {timeout}s")
        sys.exit(1)
    except Exception as e:
        error(f"Error checking health: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli()
