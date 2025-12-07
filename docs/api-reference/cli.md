---
layout: page
title: CLI Reference
description: Complete reference for the agentweave command-line interface
parent: API Reference
nav_order: 1
---

# CLI Reference

Complete reference for the `agentweave` command-line interface.

The AgentWeave CLI provides tools for configuring, validating, running, and debugging secure agents. All commands support `--help` for detailed usage information.

## Installation

The CLI is automatically installed with the AgentWeave SDK:

```bash
pip install agentweave
```

Verify installation:

```bash
agentweave --version
```

## Global Options

All commands support these global options:

- `--help` - Show help message and exit
- `--version` - Show version and exit

## Commands

### `agentweave validate`

Validate an agent configuration file.

**Usage:**
```bash
agentweave validate <config_file>
```

**Arguments:**
- `config_file` - Path to agent configuration YAML file (required)

**Checks Performed:**
1. **YAML Syntax** - Verifies file is valid YAML
2. **Required Fields** - Ensures all mandatory configuration sections exist
3. **SPIFFE Endpoint** - Checks connectivity to SPIFFE Workload API socket
4. **OPA Endpoint** - Verifies OPA policy engine is reachable
5. **Security Settings** - Validates security configuration meets requirements

**Exit Codes:**
- `0` - Configuration is valid
- `1` - Validation failed (errors displayed)

**Example Output:**

```bash
$ agentweave validate config.yaml
ℹ Validating configuration: config.yaml
ℹ SPIFFE endpoint: unix:///run/spire/sockets/agent.sock
✓ SPIFFE socket found: /run/spire/sockets/agent.sock
ℹ OPA endpoint: http://localhost:8181
✓ OPA endpoint reachable: http://localhost:8181

✓ Configuration validation passed

Configuration Summary
──────────────────────────────────
Agent Name:              search-agent
Trust Domain:            agentweave.io
Identity Provider:       spiffe
Authorization Provider:  opa
Server Port:             8443
TLS Min Version:         1.3
Peer Verification:       strict
```

**Common Errors:**

```bash
✗ Missing required section: identity
✗ agent.name is required
✗ transport.peer_verification cannot be 'none' - security violation
⚠ OPA endpoint not reachable: http://localhost:8181
```

---

### `agentweave serve`

Start the agent server.

**Usage:**
```bash
agentweave serve <config_file> [OPTIONS]
```

**Arguments:**
- `config_file` - Path to agent configuration YAML file (required)

**Options:**
- `--host HOST` - Override server host from configuration
- `--port PORT` - Override server port from configuration

**Behavior:**

When you run `serve`, the following happens:

1. **Load Configuration** - Parses and validates the config file
2. **Initialize Identity** - Connects to SPIFFE Workload API and fetches SVID
3. **Initialize Authorization** - Connects to OPA policy engine
4. **Initialize Transport** - Sets up mTLS server with SPIFFE credentials
5. **Start Server** - Begins listening for A2A protocol requests
6. **Register Signal Handlers** - Handles SIGTERM/SIGINT for graceful shutdown

**Signal Handling:**

- `SIGTERM`, `SIGINT` (Ctrl+C) - Graceful shutdown
- `SIGHUP` - Reload configuration (if supported)

**Examples:**

```bash
# Start with default config settings
agentweave serve config.yaml

# Override port
agentweave serve config.yaml --port 9443

# Override host and port
agentweave serve config.yaml --host 127.0.0.1 --port 9443
```

**Output:**

```bash
$ agentweave serve config.yaml
ℹ Starting agent from configuration: config.yaml

ℹ Agent Name: search-agent
ℹ Server: 0.0.0.0:8443

{"timestamp": "2025-12-07T10:30:00Z", "level": "INFO", "message": "Agent starting", "agent": "search-agent"}
{"level": "INFO", "message": "SVID acquired", "spiffe_id": "spiffe://agentweave.io/agent/search"}
{"level": "INFO", "message": "Server listening", "host": "0.0.0.0", "port": 8443}
```

---

### `agentweave card generate`

Generate an A2A-compliant Agent Card JSON from configuration.

**Usage:**
```bash
agentweave card generate <config_file> [OPTIONS]
```

**Arguments:**
- `config_file` - Path to agent configuration YAML file (required)

**Options:**
- `-o, --output FILE` - Write output to file instead of stdout

**Output Format:**

The command generates a JSON document following the A2A Agent Card specification:

```json
{
  "name": "search-agent",
  "description": "Semantic search and retrieval agent",
  "url": "https://localhost:8443",
  "version": "1.0.0",
  "capabilities": [
    {
      "name": "search",
      "description": "Perform semantic search over document corpus",
      "input_modes": ["application/json"],
      "output_modes": ["application/json"]
    }
  ],
  "authentication": {
    "schemes": [
      {
        "type": "mtls",
        "description": "Mutual TLS with SPIFFE identity"
      }
    ]
  },
  "extensions": {
    "spiffe_id": "spiffe://agentweave.io/agent/search",
    "trust_domain": "agentweave.io",
    "protocol": "a2a"
  }
}
```

**Examples:**

```bash
# Print to stdout
agentweave card generate config.yaml

# Save to file
agentweave card generate config.yaml -o agent-card.json
agentweave card generate config.yaml --output agent-card.json
```

**Use Cases:**

- Register agent with discovery service
- Share capabilities with other teams
- Debug agent configuration
- Generate documentation

---

### `agentweave ping`

Discover and ping a target agent to verify connectivity.

**Usage:**
```bash
agentweave ping <spiffe_id> [OPTIONS]
```

**Arguments:**
- `spiffe_id` - Target agent's SPIFFE ID (required)

**Options:**
- `-c, --config FILE` - Agent configuration file for identity credentials
- `-t, --timeout SECONDS` - Timeout in seconds (default: 5.0)

**What It Checks:**

1. Validates SPIFFE ID format
2. Fetches SVID from local SPIRE agent (if config provided)
3. Resolves agent endpoint from SPIFFE ID
4. Establishes mTLS connection
5. Fetches `/.well-known/agent.json` (Agent Card)
6. Measures round-trip latency

**Examples:**

```bash
# Basic ping
agentweave ping spiffe://agentweave.io/agent/search

# With identity config
agentweave ping spiffe://agentweave.io/agent/search -c config.yaml

# Custom timeout
agentweave ping spiffe://agentweave.io/agent/search -t 10.0
```

**Output:**

```bash
$ agentweave ping spiffe://agentweave.io/agent/search
ℹ Pinging agent: spiffe://agentweave.io/agent/search

ℹ Target: spiffe://agentweave.io/agent/search
ℹ Timeout: 5.0s
✓ Agent reachable
✓ mTLS handshake successful
✓ Peer identity verified: spiffe://agentweave.io/agent/search
ℹ Round-trip time: 23.45ms
```

**Error Output:**

```bash
✗ Invalid SPIFFE ID format: spiffe//bad-id
✗ Connection timeout after 5.0s
✗ Peer identity verification failed
```

---

### `agentweave authz check`

Query OPA for an authorization decision.

**Usage:**
```bash
agentweave authz check [OPTIONS]
```

**Options (all required):**
- `--caller SPIFFE_ID` - Caller's SPIFFE ID
- `--callee SPIFFE_ID` - Callee's SPIFFE ID
- `--action ACTION` - Action/capability being invoked

**Additional Options:**
- `--opa-endpoint URL` - OPA endpoint (default: `http://localhost:8181`)
- `--policy-path PATH` - OPA policy path (default: `agentweave/authz`)

**Use Cases:**

- Debug authorization policies
- Understand why calls are denied
- Test policy changes before deployment
- Audit authorization decisions

**Examples:**

```bash
# Basic authorization check
agentweave authz check \
  --caller spiffe://agentweave.io/agent/orchestrator \
  --callee spiffe://agentweave.io/agent/search \
  --action search

# Custom OPA endpoint
agentweave authz check \
  --caller spiffe://agentweave.io/agent/orchestrator \
  --callee spiffe://agentweave.io/agent/search \
  --action search \
  --opa-endpoint http://opa:8181

# Custom policy path
agentweave authz check \
  --caller spiffe://agentweave.io/agent/orchestrator \
  --callee spiffe://agentweave.io/agent/search \
  --action search \
  --policy-path my_org/policies/authz
```

**Output (Allowed):**

```bash
$ agentweave authz check --caller spiffe://agentweave.io/agent/orchestrator \
    --callee spiffe://agentweave.io/agent/search --action search

ℹ Querying OPA for authorization decision
ℹ OPA URL: http://localhost:8181/v1/data/agentweave/authz

✓ ALLOWED
ℹ Reason: Caller in allowed_agents list for search capability

Full OPA Response
──────────────────────────────────
{
  "allow": true,
  "reason": "Caller in allowed_agents list for search capability",
  "matched_rule": "allow_specific_capabilities"
}
```

**Output (Denied):**

```bash
✗ DENIED
ℹ Reason: Caller not in allowed_agents list

Full OPA Response
──────────────────────────────────
{
  "allow": false,
  "reason": "Caller not in allowed_agents list"
}
```

**Errors:**

```bash
✗ Invalid caller SPIFFE ID: bad-id
✗ Failed to connect to OPA at http://localhost:8181
✗ Is OPA running?
```

---

### `agentweave health`

Check an agent's health endpoint.

**Usage:**
```bash
agentweave health <url> [OPTIONS]
```

**Arguments:**
- `url` - Health endpoint URL (required, e.g., `https://localhost:8443/health`)

**Options:**
- `-t, --timeout SECONDS` - Timeout in seconds (default: 5.0)

**Response:**

The health endpoint returns JSON with agent status:

```json
{
  "status": "healthy",
  "agent": "search-agent",
  "spiffe_id": "spiffe://agentweave.io/agent/search",
  "uptime_seconds": 3600,
  "svid_expires_at": "2025-12-07T12:00:00Z",
  "checks": {
    "identity": "ok",
    "authorization": "ok",
    "transport": "ok"
  }
}
```

**Examples:**

```bash
# Check local agent
agentweave health https://localhost:8443/health

# With custom timeout
agentweave health https://localhost:8443/health -t 10.0
```

**Output:**

```bash
$ agentweave health https://localhost:8443/health
ℹ Checking health: https://localhost:8443/health
✓ Health check passed (234.56ms)

Health Status
──────────────────────────────────
{
  "status": "healthy",
  "agent": "search-agent",
  "uptime_seconds": 3600
}
```

**Error Output:**

```bash
✗ Failed to connect to https://localhost:8443/health
✗ Is the agent running?

⚠ Health check returned status 503
{
  "status": "unhealthy",
  "error": "OPA connection failed"
}

✗ Health check timed out after 5.0s
```

---

## Environment Variables

The CLI respects these environment variables:

### Identity Configuration

- `SPIFFE_ENDPOINT_SOCKET` - Override SPIFFE Workload API socket path
  - Example: `unix:///run/spire/sockets/agent.sock`
  - Default: Uses value from configuration file

### Authorization Configuration

- `AGENTWEAVE_OPA_ENDPOINT` - Override OPA endpoint URL
  - Example: `http://opa-server:8181`
  - Default: `http://localhost:8181`

- `AGENTWEAVE_POLICY_PATH` - Override OPA policy path
  - Example: `myorg/policies/authz`
  - Default: `agentweave/authz`

### Server Configuration

- `AGENTWEAVE_SERVER_HOST` - Override server host
  - Example: `127.0.0.1`
  - Default: Uses value from configuration file

- `AGENTWEAVE_SERVER_PORT` - Override server port
  - Example: `9443`
  - Default: Uses value from configuration file

### Logging

- `AGENTWEAVE_LOG_LEVEL` - Set log level
  - Values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
  - Default: `INFO`

- `AGENTWEAVE_LOG_FORMAT` - Set log format
  - Values: `json`, `text`
  - Default: `json`

**Example with Environment Variables:**

```bash
export SPIFFE_ENDPOINT_SOCKET=unix:///var/run/spire/sockets/agent.sock
export AGENTWEAVE_OPA_ENDPOINT=http://opa-prod:8181
export AGENTWEAVE_LOG_LEVEL=DEBUG

agentweave serve config.yaml
```

---

## Configuration File Location

The CLI looks for configuration files in these locations (in order):

1. Explicit path provided as argument
2. `./config.yaml` (current directory)
3. `~/.agentweave/config.yaml` (user home)
4. `/etc/agentweave/config.yaml` (system)

---

## Exit Codes

The CLI uses standard exit codes:

- `0` - Success
- `1` - General error (validation failed, connection failed, etc.)
- `2` - Command-line usage error
- `130` - Interrupted by Ctrl+C (SIGINT)

---

## Shell Completion

The CLI supports shell completion for Bash, Zsh, and Fish.

**Bash:**
```bash
# Add to ~/.bashrc
eval "$(_AGENTWEAVE_COMPLETE=bash_source agentweave)"
```

**Zsh:**
```bash
# Add to ~/.zshrc
eval "$(_AGENTWEAVE_COMPLETE=zsh_source agentweave)"
```

**Fish:**
```bash
# Add to ~/.config/fish/completions/agentweave.fish
eval (env _AGENTWEAVE_COMPLETE=fish_source agentweave)
```

---

## Debugging

### Enable Debug Logging

```bash
export AGENTWEAVE_LOG_LEVEL=DEBUG
agentweave serve config.yaml
```

### Validate Configuration Before Running

```bash
# Always validate first
agentweave validate config.yaml && agentweave serve config.yaml
```

### Test Individual Components

```bash
# Test SPIFFE connectivity
agentweave validate config.yaml  # Checks SPIFFE socket

# Test OPA connectivity and policies
agentweave authz check \
  --caller spiffe://test.local/agent/caller \
  --callee spiffe://test.local/agent/callee \
  --action test

# Test agent health
agentweave health https://localhost:8443/health
```

---

## Examples

### Complete Development Workflow

```bash
# 1. Validate configuration
agentweave validate config.yaml

# 2. Generate agent card
agentweave card generate config.yaml -o agent-card.json

# 3. Start agent
agentweave serve config.yaml

# In another terminal:
# 4. Check health
agentweave health https://localhost:8443/health

# 5. Test authorization
agentweave authz check \
  --caller spiffe://agentweave.io/agent/orchestrator \
  --callee spiffe://agentweave.io/agent/search \
  --action search

# 6. Ping agent
agentweave ping spiffe://agentweave.io/agent/search
```

### Production Deployment

```bash
# Set production environment variables
export AGENTWEAVE_LOG_LEVEL=INFO
export AGENTWEAVE_LOG_FORMAT=json
export SPIFFE_ENDPOINT_SOCKET=unix:///run/spire/sockets/agent.sock

# Validate config (CI/CD pipeline)
agentweave validate /etc/agentweave/prod-config.yaml || exit 1

# Start agent with systemd or supervisor
agentweave serve /etc/agentweave/prod-config.yaml
```

---

## See Also

- [Configuration Reference](../configuration.md) - Detailed configuration options
- [Security Guide](../security.md) - Production security hardening
- [A2A Protocol](../a2a-protocol.md) - Protocol specification
