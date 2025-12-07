---
layout: page
title: Real-World Scenarios
permalink: /examples/real-world/
parent: Examples Overview
nav_order: 6
has_children: true
---

# Real-World Scenarios

These examples demonstrate how AgentWeave solves real-world problems in specific industries. Each example includes production-grade patterns, compliance considerations, and security best practices.

## Industry Examples

### [Financial Services](financial-services/)

**Scenario**: Trading system with compliance and audit requirements

A high-frequency trading platform where multiple agents process trades, perform risk checks, and maintain audit trails for regulatory compliance. Demonstrates:

- Multi-agent trading workflow
- Compliance as code (OPA policies)
- Immutable audit logs
- Real-time risk assessment
- Regulatory reporting

**Key Technologies**:
- AgentWeave for secure agent communication
- OPA for compliance policies
- Distributed tracing for audit
- Event sourcing for trade history

**Compliance**: SOC 2, SEC regulations, audit requirements

---

### [Healthcare](healthcare/)

**Scenario**: Patient data processing with HIPAA compliance

A healthcare analytics platform where agents process patient data across organizational boundaries while maintaining HIPAA compliance. Demonstrates:

- Data minimization
- Consent-based access control
- PHI (Protected Health Information) handling
- Cross-organization data sharing (federated)
- Audit logging for HIPAA compliance
- De-identification workflows

**Key Technologies**:
- SPIFFE federation for hospital networks
- Fine-grained OPA policies for PHI access
- Encryption at rest and in transit
- Comprehensive audit trails

**Compliance**: HIPAA, HITECH, state privacy laws

---

### [IoT/Edge Computing](iot-edge/)

**Scenario**: Edge devices communicating securely with cloud

A smart building system where IoT devices (sensors, controllers) run lightweight agents that communicate with cloud agents for analytics and control. Demonstrates:

- Constrained resource environments
- Intermittent connectivity handling
- Edge-to-cloud secure communication
- Device attestation
- OTA updates
- Offline operation with sync

**Key Technologies**:
- Lightweight SPIFFE agent for edge
- mTLS over constrained networks
- Store-and-forward messaging
- Certificate rotation with limited resources

**Use Cases**: Smart buildings, industrial IoT, fleet management

---

## Common Patterns Across Examples

### Security

All examples demonstrate:
- **Zero-trust architecture**: Every communication verified
- **Least privilege access**: OPA policies grant minimum necessary permissions
- **Audit everything**: Complete audit trail of all operations
- **Encryption everywhere**: mTLS for transport, encryption at rest

### Compliance

Each example shows how to:
- **Policy as code**: Compliance rules in Rego
- **Immutable audit logs**: Cannot be tampered with
- **Access control**: Fine-grained, attribute-based
- **Data governance**: Who accessed what, when, and why

### Production Readiness

All examples include:
- **Error handling**: Graceful degradation, retries
- **Monitoring**: Metrics, traces, logs
- **Testing**: Unit, integration, policy tests
- **Documentation**: Runbooks, incident response

## How to Use These Examples

1. **Understand the scenario**: Read the business problem and requirements
2. **Review the architecture**: See how agents are structured
3. **Examine the policies**: Study OPA policies for compliance
4. **Run the example**: Follow setup instructions
5. **Adapt for your use case**: Modify for your specific needs

## Prerequisites

All examples require:
- **AgentWeave SDK**: `pip install agentweave`
- **SPIRE**: For identity
- **OPA**: For authorization
- **Docker**: For running examples

Some examples have additional requirements (databases, message queues, etc.) documented in each example.

## Getting Help

- **Example-specific questions**: Each example has a GitHub Discussions thread
- **General AgentWeave questions**: [Main documentation](/agentweave/getting-started/)
- **Security concerns**: [Security guide](/agentweave/security/)
- **Compliance questions**: Consult with your compliance team

---

**Next**: Start with an example that matches your industry, or review all three to see different patterns.
