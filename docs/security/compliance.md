---
layout: page
title: Compliance
description: How AgentWeave SDK supports compliance with SOC 2, HIPAA, PCI DSS, GDPR, and FedRAMP
permalink: /security/compliance/
parent: Security
nav_order: 3
---

# Compliance Considerations

AgentWeave SDK provides security controls and features that help organizations meet various compliance requirements. This guide explains how AgentWeave addresses common compliance frameworks.

**Important:** AgentWeave provides technical controls, but compliance requires organizational policies, procedures, and audits. Consult with compliance experts for your specific requirements.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## How AgentWeave Helps with Compliance

AgentWeave provides several security controls that map to common compliance requirements:

| Control | AgentWeave Feature |
|---------|-------------------|
| **Authentication** | SPIFFE/SPIRE cryptographic identity |
| **Authorization** | OPA policy-based access control |
| **Encryption in Transit** | TLS 1.3 with mTLS |
| **Audit Logging** | Comprehensive request/decision logging |
| **Access Control** | Default deny, least privilege |
| **Identity Management** | Automatic credential rotation |
| **Monitoring** | Metrics, traces, logs (observability) |
| **Integrity** | Cryptographic signatures, immutable logs |

---

## SOC 2 (System and Organization Controls)

### Overview

SOC 2 focuses on controls relevant to security, availability, processing integrity, confidentiality, and privacy of customer data.

### Relevant Trust Service Criteria

#### CC6.1 - Logical and Physical Access Controls

**Requirement:** The entity implements logical access security controls to protect system resources from unauthorized access.

**AgentWeave Controls:**

1. **Cryptographic Identity** (CC6.1)
   - Every agent has SPIFFE identity (cannot be forged)
   - No shared credentials or API keys
   - Automatic rotation prevents credential compromise

```yaml
# Configuration evidence
identity:
  provider: "spire"
  socket_path: "/run/spire/sockets/agent.sock"
```

2. **Mutual Authentication** (CC6.1)
   - mTLS required for all agent communication
   - Both parties verify each other's identity
   - Cannot bypass authentication

3. **Default Deny Authorization** (CC6.1)
   - All requests denied unless explicitly allowed
   - Policy-based access control
   - Centralized policy management

```rego
# Policy evidence
default allow := false  # Must explicitly grant access
```

#### CC6.2 - System Access is Removed When Access is No Longer Required

**AgentWeave Controls:**

1. **Short-lived Credentials** (CC6.2)
   - SVIDs expire after 1 hour by default
   - Automatic rotation at 50% TTL
   - Revocation supported via SPIRE

```bash
# Registration with 1-hour TTL
spire-server entry create \
  -spiffeID spiffe://example.com/agent/my-agent \
  -ttl 3600
```

2. **SPIRE Entry Deletion** (CC6.2)
   - Remove SPIRE registration to revoke access permanently

```bash
# Revoke access
spire-server entry delete -spiffeID spiffe://example.com/agent/old-agent
```

#### CC7.2 - System Monitoring

**Requirement:** The entity monitors system components and the operation of those components for anomalies.

**AgentWeave Controls:**

1. **Audit Logging** (CC7.2)
   - All requests logged with caller/callee identity
   - Authorization decisions logged
   - Failed access attempts logged

```yaml
observability:
  audit_log:
    enabled: true
    destination: "syslog"
```

2. **Metrics** (CC7.2)
   - Authorization success/failure rates
   - SVID rotation events
   - Capability invocation counts

3. **Alerting** (CC7.2)
   - Alert on high denial rates
   - Alert on SVID rotation failures
   - Alert on unknown caller attempts

#### CC8.1 - Change Management

**Requirement:** The entity authorizes, designs, develops or acquires, configures, documents, tests, approves, and implements changes to infrastructure and software.

**AgentWeave Controls:**

1. **Configuration Validation** (CC8.1)
   ```bash
   # Validate before deployment
   agentweave validate config/production.yaml
   ```

2. **Version Control** (CC8.1)
   - Policies stored in Git
   - Agent configurations in version control
   - Audit trail of changes

3. **Policy Testing** (CC8.1)
   ```bash
   # Test policies before deployment
   opa test policies/ -v
   ```

### SOC 2 Evidence Collection

**What to Collect:**

1. **Configuration Files**
   - Agent YAML configurations showing security settings
   - OPA policy files
   - SPIRE registration entries

2. **Audit Logs**
   - Sample of authorization decisions
   - Access denied events
   - SVID rotation events

3. **Monitoring Dashboards**
   - Screenshots showing security metrics
   - Alert configurations
   - Incident response logs

4. **Procedures**
   - SVID rotation policy (document TTL settings)
   - Access revocation process
   - Policy review schedule

---

## HIPAA (Health Insurance Portability and Accountability Act)

### Overview

HIPAA requires protecting Protected Health Information (PHI) with administrative, physical, and technical safeguards.

### Relevant Safeguards

#### 164.312(a)(1) - Access Control

**Requirement:** Implement technical policies and procedures for electronic information systems that maintain ePHI to allow access only to those persons or software programs that have been granted access rights.

**AgentWeave Controls:**

1. **Unique User Identification** (164.312(a)(2)(i))
   - Each agent has unique SPIFFE ID
   - Cannot share credentials (cryptographic identity)

2. **Automatic Logoff** (164.312(a)(2)(iii))
   - SVIDs expire automatically (1 hour TTL)
   - Must re-authenticate after expiry

3. **Encryption and Decryption** (164.312(a)(2)(iv))
   - All communication encrypted with TLS 1.3
   - Perfect forward secrecy

#### 164.312(b) - Audit Controls

**Requirement:** Implement hardware, software, and/or procedural mechanisms that record and examine activity in information systems that contain or use ePHI.

**AgentWeave Controls:**

1. **Comprehensive Audit Logging**
   - All PHI access logged
   - Who accessed what, when
   - Authorization decisions logged

```yaml
observability:
  audit_log:
    enabled: true
    level: "info"
    fields:
      - "timestamp"
      - "caller_spiffe_id"
      - "callee_spiffe_id"
      - "capability"
      - "action"
      - "decision"
      - "trace_id"
```

2. **Log Retention**
   - Logs sent to SIEM for retention
   - Configure retention per HIPAA requirements (6 years)

#### 164.312(c) - Integrity Controls

**Requirement:** Implement policies and procedures to protect ePHI from improper alteration or destruction.

**AgentWeave Controls:**

1. **Data Integrity** (164.312(c)(1))
   - TLS provides message integrity (MAC)
   - Tampering detected and rejected

2. **Digital Signatures** (164.312(c)(2))
   - SVID is cryptographically signed
   - Cannot forge identity

#### 164.312(d) - Person or Entity Authentication

**Requirement:** Implement procedures to verify that a person or entity seeking access to ePHI is the one claimed.

**AgentWeave Controls:**

1. **Strong Authentication**
   - Mutual TLS authentication
   - Cryptographic proof of identity
   - Cannot impersonate without private key

#### 164.312(e) - Transmission Security

**Requirement:** Implement technical security measures to guard against unauthorized access to ePHI that is being transmitted over an electronic communications network.

**AgentWeave Controls:**

1. **Encryption** (164.312(e)(2)(i))
   - TLS 1.3 encryption for all transmissions
   - No plaintext communication possible

2. **Integrity Controls** (164.312(e)(2)(ii))
   - Message authentication codes
   - Detect tampering in transit

### HIPAA Implementation Recommendations

**For PHI-Handling Agents:**

1. **Enable payload redaction in logs:**
```yaml
observability:
  audit_log:
    include_payloads: false  # Don't log PHI
    redact_fields:
      - "ssn"
      - "patient_id"
      - "diagnosis"
```

2. **Encrypt PHI at rest (application layer):**
```python
class PHIProcessor(SecureAgent):
    @capability(name="process_phi")
    async def process(self, encrypted_phi: str):
        # Decrypt only in memory
        phi = self.decrypt(encrypted_phi)
        # Process...
        # Never log PHI
```

3. **Implement access controls:**
```rego
# Only allow healthcare providers to access PHI
allow if {
    input.caller_spiffe_id in data.healthcare_providers
    input.action in ["read_phi", "write_phi"]
}
```

---

## PCI DSS (Payment Card Industry Data Security Standard)

### Overview

PCI DSS protects cardholder data with requirements for network security, access control, and monitoring.

### Relevant Requirements

#### Requirement 1: Install and Maintain Network Security Controls

**AgentWeave Controls:**

1. **Network Segmentation** (1.2.1)
   - Use Kubernetes NetworkPolicies
   - Isolate agents handling card data

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: payment-agent-netpol
spec:
  podSelector:
    matchLabels:
      app: payment-processor
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Only from authenticated agents
    - from:
        - podSelector:
            matchLabels:
              pci-zone: "true"
```

#### Requirement 2: Apply Secure Configurations

**AgentWeave Controls:**

1. **Secure Defaults** (2.2)
   - Security cannot be disabled
   - TLS 1.3 enforced
   - Default deny authorization

#### Requirement 4: Protect Cardholder Data with Strong Cryptography

**AgentWeave Controls:**

1. **Encryption in Transit** (4.2)
   - TLS 1.3 for all communication
   - Strong cipher suites only

```yaml
transport:
  tls_min_version: "1.3"
  cipher_suites:
    - "TLS_AES_256_GCM_SHA384"
    - "TLS_AES_128_GCM_SHA256"
```

#### Requirement 7: Restrict Access to System Components

**AgentWeave Controls:**

1. **Need-to-Know Access** (7.1)
   - Default deny authorization
   - Grant minimal permissions

```rego
# Only payment gateway can call payment processor
allow if {
    input.caller_spiffe_id == "spiffe://example.com/agent/payment-gateway"
    input.callee_spiffe_id == "spiffe://example.com/agent/payment-processor"
    input.action in ["authorize", "capture"]
}
```

#### Requirement 8: Identify Users and Authenticate Access

**AgentWeave Controls:**

1. **Unique IDs** (8.1)
   - Each agent has unique SPIFFE ID

2. **Strong Authentication** (8.3)
   - Cryptographic authentication (mTLS)
   - Cannot share credentials

#### Requirement 10: Log and Monitor All Access

**AgentWeave Controls:**

1. **Audit Trail** (10.2)
   - All access to cardholder data logged
   - Failed access attempts logged
   - Authorization decisions logged

2. **Log Details** (10.3)
   - User identification (SPIFFE ID)
   - Type of event (capability called)
   - Date and time
   - Success or failure
   - Origination of event

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "caller_spiffe_id": "spiffe://example.com/agent/payment-gateway",
  "callee_spiffe_id": "spiffe://example.com/agent/payment-processor",
  "capability": "process_payment",
  "action": "authorize",
  "decision": "allow",
  "trace_id": "abc123"
}
```

3. **Log Review** (10.6)
   - Send logs to SIEM
   - Set up automated analysis

---

## GDPR (General Data Protection Regulation)

### Overview

GDPR protects personal data of EU residents with requirements for consent, access, deletion, and security.

### Relevant Articles

#### Article 32: Security of Processing

**Requirement:** Implement appropriate technical and organizational measures to ensure a level of security appropriate to the risk.

**AgentWeave Controls:**

1. **Encryption** (Article 32(1)(a))
   - TLS 1.3 encryption in transit
   - Application responsible for encryption at rest

2. **Pseudonymization** (Article 32(1)(a))
   - SPIFFE IDs (pseudonymous identifiers)
   - Can correlate via SPIRE but not from IDs alone

3. **Confidentiality** (Article 32(1)(b))
   - Access control via OPA policies
   - Default deny

4. **Availability** (Article 32(1)(b))
   - Circuit breakers prevent cascading failures
   - Rate limiting prevents DoS

#### Article 30: Records of Processing Activities

**Requirement:** Maintain records of processing activities.

**AgentWeave Controls:**

1. **Audit Logging**
   - Record all data processing activities
   - Who processed what personal data

```yaml
observability:
  audit_log:
    enabled: true
    # Log processing activities
```

#### Article 33: Notification of Personal Data Breach

**Requirement:** Notify supervisory authority of breach within 72 hours.

**AgentWeave Controls:**

1. **Breach Detection**
   - Monitor for unauthorized access attempts
   - Alert on unusual patterns

```yaml
# Alert on authorization failures
- alert: PossibleDataBreach
  expr: rate(agentweave_authz_denied_total[5m]) > 20
  annotations:
    summary: "Possible data breach - high access denial rate"
```

2. **Audit Trail for Investigation**
   - Full logs of who accessed what
   - Trace IDs for incident investigation

### GDPR Implementation Recommendations

**For Personal Data Processing:**

1. **Data Minimization (Article 5(1)(c)):**
```python
@capability(name="get_user")
async def get_user(self, user_id: str, fields: list[str]):
    # Only return requested fields, not everything
    return await self.db.get_user(user_id, fields=fields)
```

2. **Right to Erasure (Article 17):**
```python
@capability(name="delete_user")
async def delete_user(self, user_id: str):
    # Implement deletion capability
    await self.db.delete_user(user_id)
    self.logger.info(f"Deleted user {user_id}")
```

3. **Data Portability (Article 20):**
```python
@capability(name="export_user_data")
async def export_user_data(self, user_id: str) -> dict:
    # Return data in structured format
    return await self.db.export_user(user_id)
```

---

## FedRAMP (Federal Risk and Authorization Management Program)

### Overview

FedRAMP standardizes security assessment for cloud services used by US federal agencies.

### Relevant Controls (NIST SP 800-53)

#### AC-2: Account Management

**AgentWeave Controls:**

- Unique accounts (SPIFFE IDs)
- Automatic credential expiration (SVID TTL)
- Revocation capability (delete SPIRE entries)

#### AC-3: Access Enforcement

**AgentWeave Controls:**

- Default deny authorization
- Policy-based access control (OPA)
- Cannot bypass authorization

#### AC-17: Remote Access

**AgentWeave Controls:**

- mTLS for all remote communication
- Cryptographic authentication
- Encryption in transit

#### AU-2: Audit Events

**AgentWeave Controls:**

- Audit all authorization decisions
- Log successful and failed access
- Log administrative actions

#### AU-3: Content of Audit Records

**AgentWeave Controls:**

Audit logs include:
- Event type (capability invoked)
- Date and time
- User identity (SPIFFE ID)
- Outcome (allow/deny)
- Source (caller SPIFFE ID)

#### IA-2: Identification and Authentication

**AgentWeave Controls:**

- Unique identification (SPIFFE IDs)
- Multifactor authentication (certificate + private key)
- Cryptographic authentication (mTLS)

#### SC-8: Transmission Confidentiality and Integrity

**AgentWeave Controls:**

- TLS 1.3 encryption
- Message integrity (MAC)
- No plaintext transmission

#### SC-12: Cryptographic Key Establishment

**AgentWeave Controls:**

- Automated key management (SPIRE)
- Regular rotation (SVID TTL)
- No manual key distribution

### FedRAMP Implementation

For FedRAMP authorization:

1. **Enable FIPS mode** (if required):
```yaml
transport:
  fips_mode: true
  tls_min_version: "1.2"  # FIPS 140-2 validated
```

2. **Continuous monitoring:**
```yaml
observability:
  metrics:
    enabled: true
  audit_log:
    enabled: true
    destination: "syslog"
  tracing:
    enabled: true
```

3. **Incident response:**
   - Documented procedures for security events
   - Integration with SIEM
   - Alerting on security events

---

## Compliance Checklist

Use this checklist to assess compliance readiness:

### Authentication & Identity
- [ ] SPIRE deployed and configured
- [ ] Unique SPIFFE ID per agent
- [ ] SVID TTL ≤ 1 hour
- [ ] Platform attestation enabled
- [ ] Credential rotation automated

### Authorization
- [ ] Default deny policy enforced
- [ ] OPA policies documented
- [ ] Least privilege applied
- [ ] Policy testing in place
- [ ] Policy review schedule defined

### Encryption
- [ ] TLS 1.3 enforced
- [ ] mTLS for all communication
- [ ] Strong cipher suites only
- [ ] Application-layer encryption for sensitive data at rest

### Audit Logging
- [ ] Audit logging enabled
- [ ] Logs include required fields
- [ ] Logs sent to SIEM
- [ ] Log retention configured
- [ ] Log review process defined

### Monitoring
- [ ] Security metrics collected
- [ ] Alerts configured
- [ ] Dashboards created
- [ ] Anomaly detection enabled

### Incident Response
- [ ] Incident response plan documented
- [ ] Revocation process defined
- [ ] Investigation procedures defined
- [ ] Communication plan defined

### Documentation
- [ ] Security controls documented
- [ ] Configuration documented
- [ ] Policies documented
- [ ] Procedures documented
- [ ] Evidence collected

---

## Evidence for Auditors

When preparing for compliance audits, collect:

### Technical Evidence

1. **Configuration Files**
   - Agent configurations showing security settings
   - OPA policy files
   - SPIRE registration entries

2. **Logs**
   - Sample audit logs
   - Authorization decisions
   - SVID rotation events

3. **Monitoring Screenshots**
   - Security dashboards
   - Alert configurations
   - Metric graphs

### Process Evidence

1. **Procedures**
   - Access provisioning process
   - Access revocation process
   - Policy review process
   - Incident response plan

2. **Training Records**
   - Security training for operators
   - Policy development training

3. **Review Records**
   - Policy review logs
   - Access review logs
   - Audit log review records

---

## Important Notes

1. **AgentWeave provides controls, not compliance:**
   - You must implement organizational policies
   - You must conduct regular audits
   - You must train personnel

2. **Application-layer security required:**
   - AgentWeave secures agent-to-agent communication
   - Your application must protect data at rest
   - Your application must implement business logic security

3. **Consult compliance experts:**
   - Each organization's compliance needs are unique
   - Regulations are subject to interpretation
   - Work with qualified compliance professionals

---

## Next Steps

- Review [Best Practices](best-practices/) for operational security
- Set up [Audit Logging](audit-logging/) for evidence collection
- See [Threat Model](threat-model/) for risk assessment
- Read main [Security Guide](/agentweave/security/) for implementation details

## References

- [SOC 2 Trust Service Criteria](https://www.aicpa.org/interestareas/frc/assuranceadvisoryservices/trustdataintegrityframework.html)
- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [PCI DSS Requirements](https://www.pcisecuritystandards.org/document_library)
- [GDPR Text](https://gdpr-info.eu/)
- [FedRAMP Controls](https://www.fedramp.gov/assets/resources/documents/FedRAMP_Security_Controls_Baseline.xlsx)
- [NIST SP 800-53](https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final)
