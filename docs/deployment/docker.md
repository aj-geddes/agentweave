---
layout: page
title: Docker Deployment
description: Deploy AgentWeave agents using Docker and Docker Compose
nav_order: 1
parent: Deployment
---

# Docker Deployment Guide

This guide covers deploying AgentWeave agents using Docker containers and Docker Compose for local development and simple production deployments.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Prerequisites

- Docker Engine 20.10+ or Docker Desktop
- Docker Compose 2.0+ (included with Docker Desktop)
- Basic understanding of Docker concepts
- At least 4GB RAM available for Docker

## Building Agent Docker Images

### Dockerfile Best Practices

Create a production-ready Dockerfile for your agent:

```dockerfile
# Use official Python slim image
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Create non-root user
RUN groupadd -r agentweave && \
    useradd -r -g agentweave -u 1000 agentweave && \
    mkdir -p /app /etc/agentweave /var/log/agentweave && \
    chown -R agentweave:agentweave /app /etc/agentweave /var/log/agentweave

WORKDIR /app

# Install dependencies stage
FROM base as builder

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc \
        g++ \
        make \
        libffi-dev \
        libssl-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --user --no-warn-script-location -r requirements.txt

# Final stage
FROM base

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/agentweave/.local

# Copy application code
COPY --chown=agentweave:agentweave . /app/

# Make sure scripts are executable
RUN chmod +x /app/entrypoint.sh

# Switch to non-root user
USER agentweave

# Update PATH to include user-installed packages
ENV PATH=/home/agentweave/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import requests; requests.get('https://localhost:8443/health/live', verify=False)" || exit 1

# Expose ports
EXPOSE 8443 9090

# Set entrypoint
ENTRYPOINT ["/app/entrypoint.sh"]

# Default command
CMD ["agentweave", "serve", "/etc/agentweave/config.yaml"]
```

### Entrypoint Script

Create `entrypoint.sh` for initialization:

```bash
#!/bin/bash
set -e

# Wait for SPIRE socket to be available
echo "Waiting for SPIRE socket..."
while [ ! -S "${SPIFFE_ENDPOINT_SOCKET#unix://}" ]; do
    sleep 1
done
echo "SPIRE socket available"

# Wait for OPA to be ready
if [ -n "$OPA_ENDPOINT" ]; then
    echo "Waiting for OPA..."
    until curl -f "${OPA_ENDPOINT}/health" >/dev/null 2>&1; do
        sleep 1
    done
    echo "OPA ready"
fi

# Validate configuration
echo "Validating configuration..."
agentweave validate /etc/agentweave/config.yaml

# Generate agent card
echo "Generating agent card..."
agentweave card generate /etc/agentweave/config.yaml > /app/agent-card.json

# Execute main command
echo "Starting agent..."
exec "$@"
```

### Building the Image

```bash
# Build with tag
docker build -t my-agent:1.0.0 .

# Build with build args
docker build \
    --build-arg AGENTWEAVE_VERSION=1.0.0 \
    --build-arg PYTHON_VERSION=3.11 \
    -t my-agent:1.0.0 .

# Multi-platform build
docker buildx build \
    --platform linux/amd64,linux/arm64 \
    -t my-agent:1.0.0 \
    --push .
```

## Running with docker run

### Basic Container

Run a single agent container:

```bash
docker run -d \
    --name my-agent \
    -p 8443:8443 \
    -p 9090:9090 \
    -v /run/spire/sockets:/run/spire/sockets:ro \
    -v $(pwd)/config.yaml:/etc/agentweave/config.yaml:ro \
    -e SPIFFE_ENDPOINT_SOCKET=unix:///run/spire/sockets/agent.sock \
    -e OPA_ENDPOINT=http://opa:8181 \
    my-agent:1.0.0
```

### Environment Variables

Configure agent via environment variables:

```bash
docker run -d \
    --name my-agent \
    -e SPIFFE_ENDPOINT_SOCKET=unix:///run/spire/sockets/agent.sock \
    -e AGENTWEAVE_TRUST_DOMAIN=example.com \
    -e AGENTWEAVE_LOG_LEVEL=INFO \
    -e AGENTWEAVE_LOG_FORMAT=json \
    -e OPA_ENDPOINT=http://opa:8181 \
    -e AGENTWEAVE_METRICS_PORT=9090 \
    -e AGENTWEAVE_SERVER_PORT=8443 \
    my-agent:1.0.0
```

### Volume Mounts

Mount necessary volumes:

```bash
docker run -d \
    --name my-agent \
    # SPIRE socket (read-only)
    -v /run/spire/sockets:/run/spire/sockets:ro \
    # Agent configuration (read-only)
    -v $(pwd)/config:/etc/agentweave:ro \
    # Application data (read-write)
    -v $(pwd)/data:/app/data \
    # Logs (read-write)
    -v $(pwd)/logs:/var/log/agentweave \
    my-agent:1.0.0
```

### Networking

Connect to custom network:

```bash
# Create network
docker network create agentweave-net

# Run agent on network
docker run -d \
    --name my-agent \
    --network agentweave-net \
    -e OPA_ENDPOINT=http://opa:8181 \
    my-agent:1.0.0
```

## Docker Compose for Development

### Complete Development Stack

Create `docker-compose.yml`:

```yaml
version: '3.8'

networks:
  agentweave:
    driver: bridge

volumes:
  spire-server-data:
  spire-agent-socket:
  opa-data:

services:
  # SPIRE Server
  spire-server:
    image: ghcr.io/spiffe/spire-server:1.9.0
    hostname: spire-server
    networks:
      - agentweave
    ports:
      - "8081:8081"
    volumes:
      - spire-server-data:/opt/spire/data
      - ./config/spire/server.conf:/opt/spire/conf/server.conf:ro
    command: ["-config", "/opt/spire/conf/server.conf"]
    healthcheck:
      test: ["CMD", "/opt/spire/bin/spire-server", "healthcheck"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s

  # SPIRE Agent
  spire-agent:
    image: ghcr.io/spiffe/spire-agent:1.9.0
    hostname: spire-agent
    networks:
      - agentweave
    depends_on:
      spire-server:
        condition: service_healthy
    volumes:
      - spire-agent-socket:/run/spire/sockets
      - ./config/spire/agent.conf:/opt/spire/conf/agent.conf:ro
      # For Unix workload attestation
      - /var/run/docker.sock:/var/run/docker.sock:ro
    command: ["-config", "/opt/spire/conf/agent.conf"]
    healthcheck:
      test: ["CMD", "/opt/spire/bin/spire-agent", "healthcheck"]
      interval: 10s
      timeout: 5s
      retries: 5

  # OPA
  opa:
    image: openpolicyagent/opa:0.62.0
    hostname: opa
    networks:
      - agentweave
    ports:
      - "8181:8181"
    volumes:
      - opa-data:/data
      - ./config/opa/policies:/policies:ro
    command:
      - "run"
      - "--server"
      - "--addr=0.0.0.0:8181"
      - "--log-level=info"
      - "/policies"
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:8181/health"]
      interval: 5s
      timeout: 3s
      retries: 3

  # Your Agent
  my-agent:
    build:
      context: .
      dockerfile: Dockerfile
    hostname: my-agent
    networks:
      - agentweave
    depends_on:
      spire-agent:
        condition: service_healthy
      opa:
        condition: service_healthy
    ports:
      - "8443:8443"
      - "9090:9090"
    environment:
      - SPIFFE_ENDPOINT_SOCKET=unix:///run/spire/sockets/agent.sock
      - OPA_ENDPOINT=http://opa:8181
      - AGENTWEAVE_LOG_LEVEL=DEBUG
    volumes:
      - spire-agent-socket:/run/spire/sockets:ro
      - ./config/agent.yaml:/etc/agentweave/config.yaml:ro
      - ./data:/app/data
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "--no-check-certificate", "https://localhost:8443/health/live"]
      interval: 10s
      timeout: 5s
      retries: 3
```

### SPIRE Configuration Files

**`config/spire/server.conf`**:

```hcl
server {
    bind_address = "0.0.0.0"
    bind_port = "8081"
    trust_domain = "agentweave.local"
    data_dir = "/opt/spire/data/server"
    log_level = "INFO"
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

    KeyManager "memory" {
        plugin_data {}
    }
}
```

**`config/spire/agent.conf`**:

```hcl
agent {
    data_dir = "/opt/spire/data/agent"
    log_level = "INFO"
    server_address = "spire-server"
    server_port = "8081"
    socket_path = "/run/spire/sockets/agent.sock"
    trust_domain = "agentweave.local"
}

plugins {
    NodeAttestor "join_token" {
        plugin_data {}
    }

    KeyManager "memory" {
        plugin_data {}
    }

    WorkloadAttestor "docker" {
        plugin_data {
            docker_socket_path = "/var/run/docker.sock"
        }
    }

    WorkloadAttestor "unix" {
        plugin_data {}
    }
}
```

### OPA Policy Files

**`config/opa/policies/authz.rego`**:

```rego
package agentweave.authz

import rego.v1

default allow := false

# Allow agents in same trust domain
allow if {
    same_trust_domain
}

same_trust_domain if {
    caller_domain := split(input.caller_spiffe_id, "/")[2]
    callee_domain := split(input.callee_spiffe_id, "/")[2]
    caller_domain == callee_domain
    caller_domain == "agentweave.local"
}

# Audit all decisions
audit_entry := {
    "timestamp": time.now_ns(),
    "caller": input.caller_spiffe_id,
    "action": input.action,
    "allowed": allow,
    "reason": reason
}

reason := "same trust domain" if same_trust_domain
reason := "denied" if not allow
```

### Agent Configuration

**`config/agent.yaml`**:

```yaml
agent:
  name: "my-agent"
  trust_domain: "agentweave.local"
  description: "Example agent"
  capabilities:
    - name: "process"
      description: "Process data"

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"
  allowed_trust_domains:
    - "agentweave.local"

authorization:
  provider: "opa"
  opa_endpoint: "http://opa:8181"
  policy_path: "agentweave/authz"
  default_action: "deny"

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"

server:
  host: "0.0.0.0"
  port: 8443

observability:
  metrics:
    enabled: true
    port: 9090
  logging:
    level: "INFO"
    format: "json"
```

## Multi-Container Setup

### Multiple Agents

Deploy orchestrated multi-agent system:

```yaml
version: '3.8'

services:
  # Infrastructure services (spire-server, spire-agent, opa)
  # ... (as shown above)

  # Search Agent
  agent-search:
    build: ./agents/search
    environment:
      - AGENTWEAVE_SPIFFE_ID=spiffe://agentweave.local/agent/search
    volumes:
      - spire-agent-socket:/run/spire/sockets:ro
      - ./config/search-agent.yaml:/etc/agentweave/config.yaml:ro
    ports:
      - "8443:8443"

  # Processor Agent
  agent-processor:
    build: ./agents/processor
    environment:
      - AGENTWEAVE_SPIFFE_ID=spiffe://agentweave.local/agent/processor
    volumes:
      - spire-agent-socket:/run/spire/sockets:ro
      - ./config/processor-agent.yaml:/etc/agentweave/config.yaml:ro
    ports:
      - "8444:8443"

  # Orchestrator Agent
  agent-orchestrator:
    build: ./agents/orchestrator
    depends_on:
      - agent-search
      - agent-processor
    environment:
      - AGENTWEAVE_SPIFFE_ID=spiffe://agentweave.local/agent/orchestrator
      - SEARCH_AGENT_URL=https://agent-search:8443
      - PROCESSOR_AGENT_URL=https://agent-processor:8443
    volumes:
      - spire-agent-socket:/run/spire/sockets:ro
      - ./config/orchestrator-agent.yaml:/etc/agentweave/config.yaml:ro
    ports:
      - "8445:8443"
```

### Registering Workloads with SPIRE

Create `scripts/register-agents.sh`:

```bash
#!/bin/bash

# Wait for SPIRE server to be ready
echo "Waiting for SPIRE server..."
until /opt/spire/bin/spire-server healthcheck -socketPath /opt/spire/data/server/private/api.sock; do
    sleep 1
done

echo "SPIRE server ready, registering agents..."

# Register search agent
/opt/spire/bin/spire-server entry create \
    -socketPath /opt/spire/data/server/private/api.sock \
    -spiffeID spiffe://agentweave.local/agent/search \
    -parentID spiffe://agentweave.local/spire/agent/docker \
    -selector docker:label:com.docker.compose.service:agent-search \
    -dns agent-search

# Register processor agent
/opt/spire/bin/spire-server entry create \
    -socketPath /opt/spire/data/server/private/api.sock \
    -spiffeID spiffe://agentweave.local/agent/processor \
    -parentID spiffe://agentweave.local/spire/agent/docker \
    -selector docker:label:com.docker.compose.service:agent-processor \
    -dns agent-processor

# Register orchestrator agent
/opt/spire/bin/spire-server entry create \
    -socketPath /opt/spire/data/server/private/api.sock \
    -spiffeID spiffe://agentweave.local/agent/orchestrator \
    -parentID spiffe://agentweave.local/spire/agent/docker \
    -selector docker:label:com.docker.compose.service:agent-orchestrator \
    -dns agent-orchestrator

echo "Agent registration complete"
```

Add registration service to compose:

```yaml
  spire-registration:
    image: ghcr.io/spiffe/spire-server:1.9.0
    depends_on:
      spire-server:
        condition: service_healthy
    volumes:
      - spire-server-data:/opt/spire/data
      - ./scripts/register-agents.sh:/scripts/register-agents.sh:ro
    command: ["/bin/sh", "/scripts/register-agents.sh"]
    restart: "no"
```

## Common Operations

### Starting the Stack

```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose up -d spire-server spire-agent opa

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f my-agent
```

### Stopping the Stack

```bash
# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Stop without removing containers
docker-compose stop
```

### Updating Agents

```bash
# Rebuild and restart agent
docker-compose up -d --build my-agent

# Pull latest images and restart
docker-compose pull
docker-compose up -d
```

### Debugging

```bash
# Execute command in running container
docker-compose exec my-agent bash

# Check agent health
docker-compose exec my-agent agentweave validate /etc/agentweave/config.yaml

# View SPIRE registration entries
docker-compose exec spire-server /opt/spire/bin/spire-server entry show

# Test OPA policy
docker-compose exec opa opa test /policies

# View agent card
docker-compose exec my-agent cat /app/agent-card.json
```

## Production Considerations

### Resource Limits

Add resource constraints:

```yaml
services:
  my-agent:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M
```

### Restart Policies

Configure restart behavior:

```yaml
services:
  my-agent:
    restart: unless-stopped
    # or
    restart: on-failure:3
```

### Logging

Configure logging driver:

```yaml
services:
  my-agent:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service,env"
```

### Security

Run as non-root user:

```yaml
services:
  my-agent:
    user: "1000:1000"
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    read_only: true
    tmpfs:
      - /tmp
```

## Troubleshooting

### Container Fails to Start

Check logs and health:

```bash
# View container logs
docker-compose logs my-agent

# Check container status
docker-compose ps

# Inspect container
docker inspect agentweave_my-agent_1

# View health check logs
docker inspect --format='{{json .State.Health}}' agentweave_my-agent_1
```

### SPIRE Socket Not Available

Verify SPIRE Agent is running and socket is mounted:

```bash
# Check SPIRE Agent status
docker-compose ps spire-agent

# Verify socket exists in agent container
docker-compose exec my-agent ls -l /run/spire/sockets/

# Check socket permissions
docker-compose exec spire-agent ls -l /run/spire/sockets/

# Test SPIRE connection
docker-compose exec my-agent sh -c 'test -S /run/spire/sockets/agent.sock && echo "Socket exists" || echo "Socket not found"'
```

### OPA Connection Failed

Test OPA connectivity:

```bash
# Check OPA status
docker-compose ps opa

# Test OPA from agent container
docker-compose exec my-agent curl http://opa:8181/health

# Test policy evaluation
docker-compose exec my-agent curl -X POST http://opa:8181/v1/data/agentweave/authz \
  -H "Content-Type: application/json" \
  -d '{"input": {"caller_spiffe_id": "spiffe://agentweave.local/agent/test"}}'
```

### Network Issues Between Containers

Debug networking:

```bash
# Check network
docker network inspect agentweave_agentweave

# Test connectivity between containers
docker-compose exec my-agent ping opa
docker-compose exec my-agent ping spire-server

# Check DNS resolution
docker-compose exec my-agent nslookup opa
```

### Permission Denied Errors

Fix volume mount permissions:

```bash
# Check ownership
docker-compose exec my-agent ls -la /run/spire/sockets/

# Fix permissions on host (development only)
sudo chmod 666 /run/spire/sockets/agent.sock

# Use correct user in Dockerfile
# USER agentweave
```

## Next Steps

- **[Kubernetes Deployment](kubernetes.md)** - Scale to production with Kubernetes
- **[Helm Charts](helm.md)** - Template-based deployments
- **[Security Best Practices](/agentweave/security/)** - Harden your deployment

---

**Related Documentation**:
- [Configuration Reference](/agentweave/configuration/)
- [Observability Guide](/agentweave/guides/observability/)
- [Development Workflow](/agentweave/guides/development/)
