---
layout: page
title: Examples Overview
permalink: /examples/
nav_order: 6
has_children: true
---

# AgentWeave Examples

This section provides comprehensive, runnable examples demonstrating how to build secure AI agents with AgentWeave. Each example includes complete code, configuration files, deployment manifests, and detailed explanations.

## Example Categories

### Getting Started Examples

Perfect for developers new to AgentWeave:

- **[Simple Agent](simple-agent/)** - Single agent with one capability, complete walkthrough
- **[Multi-Agent Orchestration](multi-agent/)** - Orchestrator pattern with multiple workers

### Architectural Patterns

Common patterns for building agent systems:

- **[Federated Agents](federated/)** - Agents across trust domains with cross-domain communication
- **[Microservices Pattern](microservices/)** - Converting traditional microservices to secure agents

### Real-World Use Cases

Production-ready examples for specific industries:

- **[Data Processing Pipeline](data-pipeline/)** - ETL pipeline with ingestion, processing, and storage agents
- **[Financial Services](real-world/financial-services/)** - Trading system with compliance and audit
- **[Healthcare](real-world/healthcare/)** - Patient data processing with HIPAA compliance
- **[IoT/Edge Computing](real-world/iot-edge/)** - Edge devices communicating securely with cloud

## Complexity Levels

Examples are marked with complexity levels to help you choose:

| Level | Description | Best For |
|-------|-------------|----------|
| **Beginner** | Single agent, minimal configuration | Learning AgentWeave basics |
| **Intermediate** | Multi-agent systems, basic policies | Building practical applications |
| **Advanced** | Federation, complex policies, production patterns | Enterprise deployments |

## How to Run Examples

### Prerequisites

All examples require:

1. **Python 3.11+**
   ```bash
   python --version  # Should be 3.11 or higher
   ```

2. **Docker and Docker Compose**
   ```bash
   docker --version
   docker-compose --version
   ```

3. **AgentWeave SDK**
   ```bash
   pip install agentweave
   ```

### Quick Start

Each example includes a complete setup. The general pattern is:

```bash
# 1. Clone the examples repository
git clone https://github.com/aj-geddes/agentweave.git
cd agentweave/examples/<example-name>

# 2. Review the configuration
cat config/agent.yaml

# 3. Start infrastructure (SPIRE, OPA)
docker-compose up -d

# 4. Run the agent
python agent.py
```

### Example Structure

Each example follows this structure:

```
example-name/
├── README.md                    # Overview and instructions
├── agent.py                     # Agent implementation
├── config/
│   ├── agent.yaml              # Agent configuration
│   └── policies/               # OPA policies
│       └── authz.rego
├── docker-compose.yaml         # Infrastructure setup
├── spire/                      # SPIRE configuration
│   ├── server.conf
│   └── agent.conf
├── tests/                      # Unit and integration tests
└── requirements.txt            # Python dependencies
```

## Example Code Repository

All examples are available in the [AgentWeave Repository](https://github.com/aj-geddes/agentweave):

```bash
git clone https://github.com/aj-geddes/agentweave.git
cd agentweave/examples
```

The repository includes:

- Complete, runnable code for each example
- Docker Compose files for infrastructure
- SPIRE and OPA configurations
- Integration tests
- Deployment manifests for Kubernetes
- Helm charts for production deployment

## Learning Path

We recommend following examples in this order:

1. **[Simple Agent](simple-agent/)** - Understand the basics
2. **[Multi-Agent Orchestration](multi-agent/)** - Learn inter-agent communication
3. **[Data Pipeline](data-pipeline/)** - Apply patterns to a real use case
4. **[Federated Agents](federated/)** - Understand cross-domain security
5. **Industry-Specific Examples** - Adapt patterns to your domain

## Getting Help

- **Documentation Issues**: [Open an issue](https://github.com/aj-geddes/agentweave/issues)
- **Example Questions**: [GitHub Discussions](https://github.com/aj-geddes/agentweave/discussions)
- **Community**: [Discord Server](https://discord.gg/agentweave)

## Contributing Examples

Have a useful pattern or use case? We welcome contributions!

See [Contributing Guide](https://github.com/aj-geddes/agentweave/blob/main/CONTRIBUTING.md) for:
- Example submission guidelines
- Code quality standards
- Documentation requirements

---

**Next Steps:**
- Start with [Simple Agent](simple-agent/) to learn the basics
- Review [Core Concepts](/agentweave/core-concepts/) for deeper understanding
- Check out [Real-World Examples](real-world/) for production patterns
