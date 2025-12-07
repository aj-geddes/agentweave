---
layout: page
title: Installation
description: Install the AgentWeave SDK and set up your development environment
nav_order: 1
parent: Getting Started
---

# Installation Guide

This guide covers installing AgentWeave and setting up the required infrastructure for development.

## Installing AgentWeave

### Basic Installation

Install AgentWeave using pip:

```bash
pip install agentweave
```

This installs the core SDK with all required dependencies.

### Installing with Extras

AgentWeave provides optional extras for development, testing, and documentation:

```bash
# Development tools (linting, formatting, type checking)
pip install agentweave[dev]

# Testing utilities and fixtures
pip install agentweave[test]

# Documentation tools
pip install agentweave[docs]

# Install everything
pip install agentweave[dev,test,docs]
```

### Installing from Source

For the latest development version or to contribute:

```bash
# Clone the repository
git clone https://github.com/agentweave/agentweave.git
cd agentweave

# Install in editable mode with dev dependencies
pip install -e ".[dev,test]"

# Verify installation
agentweave --version
```

## Verifying Installation

Check that AgentWeave is installed correctly:

```bash
# Check version
python -c "import agentweave; print(agentweave.__version__)"

# Verify CLI is available
agentweave --help
```

You should see output like:

```
AgentWeave SDK v1.0.0

Usage: agentweave [OPTIONS] COMMAND [ARGS]...

Commands:
  validate     Validate agent configuration
  serve        Run an agent server
  card         Generate agent card
  authz        Test authorization policies
  ping         Test connectivity to another agent
```

## Docker Image

AgentWeave provides official Docker images:

```bash
# Pull the latest image
docker pull agentweave/agentweave:latest

# Pull a specific version
docker pull agentweave/agentweave:1.0.0

# Run a container
docker run -it agentweave/agentweave:latest agentweave --help
```

### Building the Docker Image

To build your own image:

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Install AgentWeave
RUN pip install agentweave

# Copy your agent code
COPY my_agent.py /app/
COPY config.yaml /app/

WORKDIR /app

CMD ["python", "my_agent.py"]
```

```bash
docker build -t my-agent:latest .
```

## Infrastructure Setup (Development)

AgentWeave requires supporting infrastructure for identity (SPIRE) and authorization (OPA). For development, we provide a Docker Compose setup.

### Quick Start with Docker Compose

Clone the starter template:

```bash
# Clone the starter repository
git clone https://github.com/agentweave/agentweave-starter.git
cd agentweave-starter

# Start all services
docker-compose up -d

# Verify services are running
docker-compose ps
```

This starts:
- **SPIRE Server** - Central identity authority
- **SPIRE Agent** - Local workload API
- **OPA** - Policy engine for authorization
- **Prometheus** - Metrics collection (optional)
- **Jaeger** - Distributed tracing (optional)

### Manual Infrastructure Setup

If you prefer to run services separately:

#### 1. SPIRE Setup

**Install SPIRE**:

```bash
# Download SPIRE
SPIRE_VERSION=1.9.0
wget https://github.com/spiffe/spire/releases/download/v${SPIRE_VERSION}/spire-${SPIRE_VERSION}-linux-amd64-musl.tar.gz

# Extract
tar xzf spire-${SPIRE_VERSION}-linux-amd64-musl.tar.gz
cd spire-${SPIRE_VERSION}
```

**Configure SPIRE Server** (`conf/server/server.conf`):

```hcl
server {
    bind_address = "0.0.0.0"
    bind_port = "8081"
    trust_domain = "agentweave.local"
    data_dir = "/opt/spire/data/server"
}

plugins {
    DataStore "sql" {
        plugin_data {
            database_type = "sqlite3"
            connection_string = "/opt/spire/data/server/datastore.sqlite3"
        }
    }
    NodeAttestor "join_token" {
        plugin_data {}
    }
    KeyManager "disk" {
        plugin_data {
            keys_path = "/opt/spire/data/server/keys.json"
        }
    }
}
```

**Start SPIRE Server**:

```bash
./bin/spire-server run -config conf/server/server.conf &
```

**Configure SPIRE Agent** (`conf/agent/agent.conf`):

```hcl
agent {
    data_dir = "/opt/spire/data/agent"
    trust_domain = "agentweave.local"
    server_address = "localhost"
    server_port = "8081"
}

plugins {
    NodeAttestor "join_token" {
        plugin_data {}
    }
    KeyManager "disk" {
        plugin_data {
            directory = "/opt/spire/data/agent"
        }
    }
    WorkloadAttestor "unix" {
        plugin_data {}
    }
}
```

**Start SPIRE Agent**:

```bash
# Generate join token
TOKEN=$(./bin/spire-server token generate -spiffeID spiffe://agentweave.local/agent)

# Start agent with token
./bin/spire-agent run -config conf/agent/agent.conf -joinToken $TOKEN &
```

#### 2. OPA Setup

**Install OPA**:

```bash
# Download OPA
curl -L -o opa https://openpolicyagent.org/downloads/latest/opa_linux_amd64

# Make executable
chmod +x opa

# Move to PATH
sudo mv opa /usr/local/bin/
```

**Start OPA**:

```bash
# Create policy directory
mkdir -p policies

# Start OPA server
opa run --server --addr :8181 policies/ &
```

## Environment Configuration

Set up environment variables for AgentWeave:

```bash
# SPIFFE endpoint (where SPIRE Agent listens)
export SPIFFE_ENDPOINT_SOCKET="unix:///run/spire/sockets/agent.sock"

# OPA endpoint
export AGENTWEAVE_OPA_ENDPOINT="http://localhost:8181"

# Trust domain
export AGENTWEAVE_TRUST_DOMAIN="agentweave.local"

# Log level
export AGENTWEAVE_LOG_LEVEL="INFO"
```

Add these to your `~/.bashrc` or `~/.zshrc` for persistence.

## Troubleshooting

### Permission Denied: SPIRE Socket

If you see "Permission denied" when accessing the SPIRE socket:

```bash
# Check socket permissions
ls -l /run/spire/sockets/agent.sock

# Fix permissions (development only!)
sudo chmod 666 /run/spire/sockets/agent.sock
```

For production, use proper Unix user/group configuration.

### Module Not Found: agentweave

If Python can't find the agentweave module:

```bash
# Verify installation
pip list | grep agentweave

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"

# Reinstall if needed
pip uninstall agentweave
pip install agentweave
```

### Docker Compose Services Not Starting

Check service logs:

```bash
# View all logs
docker-compose logs

# View specific service
docker-compose logs spire-server
docker-compose logs opa

# Follow logs in real-time
docker-compose logs -f
```

Common issues:
- Port conflicts (8081, 8181, 8443 already in use)
- Insufficient Docker resources (increase memory limit)
- Volume mount permissions

### SPIRE Server Connection Failed

Verify SPIRE Server is accessible:

```bash
# Check if server is listening
netstat -tlnp | grep 8081

# Test connection
curl -k https://localhost:8081/healthz

# Check server logs
docker-compose logs spire-server
```

### OPA Not Responding

Test OPA connectivity:

```bash
# Health check
curl http://localhost:8181/health

# Test policy evaluation
curl -X POST http://localhost:8181/v1/data \
  -H "Content-Type: application/json" \
  -d '{"input": {}}'
```

## Platform-Specific Notes

### macOS

On macOS, use `host.docker.internal` to access host services from Docker containers:

```yaml
# config.yaml
authorization:
  opa_endpoint: "http://host.docker.internal:8181"
```

### Windows (WSL2)

Run AgentWeave inside WSL2 for best compatibility:

```powershell
# In PowerShell, start WSL
wsl

# Inside WSL, follow Linux installation steps
```

For native Windows support, use the Windows Docker Compose setup from the starter template.

### Linux

On Linux, you may need to adjust socket paths:

```bash
# SPIRE Agent socket typically at:
/run/spire/sockets/agent.sock

# Or for user-local installation:
/tmp/spire/sockets/agent.sock
```

## Next Steps

Now that AgentWeave is installed, you're ready to:

1. **[Run the 5-Minute Quickstart](quickstart.md)** - Get your first agent running
2. **[Learn Core Concepts](concepts.md)** - Understand the architecture
3. **[Build Hello World](hello-world.md)** - Detailed tutorial

---

**Previous**: [← Getting Started Overview](index.md) | **Next**: [5-Minute Quickstart →](quickstart.md)
