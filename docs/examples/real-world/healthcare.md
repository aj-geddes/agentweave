---
layout: page
title: Healthcare Use Case
permalink: /examples/real-world/healthcare/
parent: Real-World Scenarios
grand_parent: Examples Overview
nav_order: 2
---

# Healthcare: HIPAA-Compliant Patient Data Processing

**Industry**: Healthcare
**Scenario**: Multi-hospital patient analytics with HIPAA compliance
**Compliance**: HIPAA, HITECH, state privacy laws
**Time to Complete**: 60 minutes

## Business Problem

**HealthNet Analytics** provides analytics across multiple hospitals:

1. **Process patient data** from multiple hospital systems
2. **Maintain HIPAA compliance** for PHI (Protected Health Information)
3. **Implement consent-based access** - patients control who sees their data
4. **De-identify data** for research and analytics
5. **Audit all PHI access** for HIPAA breach notification requirements
6. **Cross-organization sharing** between hospitals (federated trust domains)

### HIPAA Requirements

| Requirement | HIPAA Rule | Implementation |
|-------------|-----------|----------------|
| Access Control | 164.312(a)(1) | OPA policies + SPIFFE identity |
| Audit Controls | 164.312(b) | Immutable audit logs |
| Integrity | 164.312(c)(1) | mTLS, cryptographic verification |
| Transmission Security | 164.312(e)(1) | mTLS for all PHI |
| Minimum Necessary | 164.502(b) | Data minimization in agents |
| Patient Consent | State laws | Consent service integration |

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              Hospital A (Trust Domain: hospital-a.org)        │
│                                                               │
│  ┌────────────┐      ┌─────────────┐      ┌──────────────┐  │
│  │   EMR      │─────►│ Ingestion   │─────►│ Consent      │  │
│  │  System    │      │   Agent     │      │  Service     │  │
│  └────────────┘      └─────────────┘      └──────┬───────┘  │
│                                                    │          │
└────────────────────────────────────────────────────┼──────────┘
                                                     │
                                    Check consent    │
                                                     ▼
┌────────────────────────────────────────────────────┼──────────┐
│         Central Analytics (Trust Domain: analytics.org)       │
│                                                     │          │
│  ┌──────────────┐      ┌──────────────┐      ┌────▼───────┐  │
│  │De-Identify   │◄─────│  Analytics   │◄─────│   PHI      │  │
│  │   Agent      │      │    Agent     │      │ Aggregator │  │
│  └──────┬───────┘      └──────────────┘      └────────────┘  │
│         │                                                      │
│         ▼                                                      │
│  ┌──────────────┐                                             │
│  │  Research    │  ← De-identified data only                  │
│  │  Database    │                                             │
│  └──────────────┘                                             │
└──────────────────────────────────────────────────────────────┘
                           │
                           │ Federation (SPIFFE trust)
                           ▼
┌──────────────────────────────────────────────────────────────┐
│              Hospital B (Trust Domain: hospital-b.org)        │
│                                                               │
│  Similar architecture to Hospital A                          │
│  Can share with Analytics (with patient consent)             │
└──────────────────────────────────────────────────────────────┘

All PHI access:
- Requires patient consent
- Uses mTLS (HIPAA 164.312(e))
- Logged for audit (HIPAA 164.312(b))
- Minimum necessary (HIPAA 164.502(b))
```

## Complete Code

### PHI Ingestion Agent

```python
# phi_ingestion_agent.py
"""
PHI Ingestion Agent - Receives patient data from EMR systems.

HIPAA Compliance:
- 164.312(a)(1) - Access Control
- 164.312(b) - Audit Controls
- 164.312(c)(1) - Integrity
- 164.502(b) - Minimum Necessary

This agent runs in hospital's trust domain.
"""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field

from agentweave import SecureAgent, capability, requires_peer
from agentweave.types import TaskResult, Message, DataPart
from agentweave.exceptions import AgentCallError


class PatientRecord(BaseModel):
    """
    Patient health record (PHI).

    Contains Protected Health Information (PHI) under HIPAA.
    """
    patient_id: str  # Internal hospital ID
    mrn: str  # Medical Record Number
    first_name: str
    last_name: str
    date_of_birth: str
    ssn: Optional[str] = None
    diagnosis_codes: List[str] = Field(default_factory=list)
    procedure_codes: List[str] = Field(default_factory=list)
    medications: List[str] = Field(default_factory=list)
    lab_results: Dict[str, Any] = Field(default_factory=dict)
    visit_date: str
    hospital_id: str


class PHIIngestionAgent(SecureAgent):
    """
    Ingests patient records from EMR system.

    HIPAA Controls:
    - Only EMR system can send data (SPIFFE + OPA)
    - All access logged (audit trail)
    - Data validated before processing
    - Consent checked before sharing
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.consent_service = "spiffe://hospital-a.org/agent/consent"
        self.analytics_aggregator = "spiffe://analytics.org/agent/aggregator"

    @capability("ingest_phi")
    @requires_peer("spiffe://hospital-a.org/system/emr")
    async def ingest_phi(
        self,
        patient_record: Dict[str, Any]
    ) -> TaskResult:
        """
        Ingest PHI from EMR system.

        HIPAA 164.312(b): Log all access to PHI
        """
        try:
            # Validate PHI
            record = PatientRecord(**patient_record)

            # Log PHI access (HIPAA 164.312(b))
            await self._log_phi_access(
                action="ingest",
                patient_id=record.patient_id,
                data_elements=self._get_data_elements(record)
            )

            self.logger.info(
                "PHI ingested",
                extra={
                    "patient_id": self._hash_id(record.patient_id),  # Hash for logs
                    "hospital_id": record.hospital_id,
                    "visit_date": record.visit_date
                }
            )

            # Check patient consent for analytics sharing
            consent_result = await self.call_agent(
                target=self.consent_service,
                task_type="check_consent",
                payload={
                    "patient_id": record.patient_id,
                    "purpose": "analytics",
                    "recipient": "analytics.org"
                },
                timeout=5.0
            )

            if consent_result.status != "completed":
                raise AgentCallError("Consent check failed")

            consent_data = consent_result.artifacts[0]["data"]

            if consent_data["consented"]:
                # Patient consented - send to analytics
                # Only send minimum necessary data (HIPAA 164.502(b))
                minimal_record = self._minimize_data(
                    record,
                    purpose="analytics"
                )

                await self._send_to_analytics(minimal_record)

                return TaskResult(
                    status="completed",
                    messages=[Message(
                        role="assistant",
                        parts=[DataPart(data={
                            "status": "ingested_and_shared",
                            "patient_id": record.patient_id,
                            "analytics_shared": True
                        })]
                    )]
                )
            else:
                # No consent - store locally only
                self.logger.info(
                    "Patient did not consent to analytics sharing",
                    extra={"patient_id": self._hash_id(record.patient_id)}
                )

                return TaskResult(
                    status="completed",
                    messages=[Message(
                        role="assistant",
                        parts=[DataPart(data={
                            "status": "ingested",
                            "patient_id": record.patient_id,
                            "analytics_shared": False,
                            "reason": "no_consent"
                        })]
                    )]
                )

        except Exception as e:
            self.logger.error(f"PHI ingestion failed: {e}")

            # Log failed access attempt (security incident)
            await self._log_phi_access(
                action="ingest_failed",
                patient_id=patient_record.get("patient_id", "unknown"),
                error=str(e)
            )

            return TaskResult(
                status="failed",
                error=f"Failed to ingest PHI: {e}"
            )

    def _minimize_data(
        self,
        record: PatientRecord,
        purpose: str
    ) -> Dict[str, Any]:
        """
        Implement "Minimum Necessary" rule (HIPAA 164.502(b)).

        Only include data elements necessary for stated purpose.
        """
        if purpose == "analytics":
            # Analytics doesn't need direct identifiers
            return {
                "patient_id": record.patient_id,  # Internal ID, not sent
                "age_range": self._calculate_age_range(record.date_of_birth),
                "diagnosis_codes": record.diagnosis_codes,
                "procedure_codes": record.procedure_codes,
                "lab_results": record.lab_results,
                "visit_date": record.visit_date,
                "hospital_id": record.hospital_id,
                # Note: NO name, DOB, SSN
            }
        else:
            # Full record for other purposes
            return record.dict()

    async def _send_to_analytics(self, minimal_record: Dict[str, Any]):
        """
        Send minimized record to analytics (federated call).

        HIPAA 164.312(e)(1): Transmission security
        - Enforced by AgentWeave SDK (mTLS)
        """
        try:
            result = await self.call_agent(
                target=self.analytics_aggregator,
                task_type="receive_phi",
                payload={"record": minimal_record},
                timeout=10.0
            )

            if result.status != "completed":
                raise AgentCallError(f"Analytics rejected data: {result.error}")

        except AgentCallError as e:
            self.logger.error(f"Failed to send to analytics: {e}")
            # Don't fail ingestion if analytics unavailable
            # But log for investigation

    async def _log_phi_access(
        self,
        action: str,
        patient_id: str,
        data_elements: List[str] = None,
        error: str = None
    ):
        """
        Log PHI access (HIPAA 164.312(b)).

        Audit log must include:
        - Date and time
        - User/system accessing
        - Action performed
        - PHI accessed
        """
        audit_record = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "patient_id": self._hash_id(patient_id),  # Hash in logs
            "accessor": str(self.context.caller_spiffe_id),
            "data_elements": data_elements,
            "error": error
        }

        # In production, write to WORM storage (Write Once Read Many)
        # For HIPAA compliance, audit logs must be tamper-proof
        self.logger.info("PHI access logged", extra=audit_record)

    def _get_data_elements(self, record: PatientRecord) -> List[str]:
        """Get list of data elements in record."""
        elements = ["demographics"]
        if record.diagnosis_codes:
            elements.append("diagnoses")
        if record.medications:
            elements.append("medications")
        if record.lab_results:
            elements.append("lab_results")
        return elements

    @staticmethod
    def _hash_id(patient_id: str) -> str:
        """Hash patient ID for logging (don't log actual PHI)."""
        import hashlib
        return hashlib.sha256(patient_id.encode()).hexdigest()[:16]

    @staticmethod
    def _calculate_age_range(date_of_birth: str) -> str:
        """Calculate age range (de-identified)."""
        from datetime import datetime
        dob = datetime.fromisoformat(date_of_birth)
        age = (datetime.utcnow() - dob).days // 365

        if age < 18:
            return "0-17"
        elif age < 30:
            return "18-29"
        elif age < 50:
            return "30-49"
        elif age < 70:
            return "50-69"
        else:
            return "70+"


async def main():
    agent = PHIIngestionAgent.from_config("config/phi_ingestion.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### De-Identification Agent

```python
# deidentification_agent.py
"""
De-Identification Agent - Removes identifiers for research.

HIPAA Safe Harbor Method (164.514(b)(2)):
Removes 18 types of identifiers to de-identify PHI.
"""

import asyncio
from typing import Dict, Any, List
from datetime import datetime
import hashlib

from agentweave import SecureAgent, capability, requires_peer
from agentweave.types import TaskResult, Message, DataPart


class DeIdentificationAgent(SecureAgent):
    """
    De-identifies PHI for research use.

    Implements HIPAA Safe Harbor method:
    1. Remove 18 identifier types
    2. No actual knowledge residual info could identify patient
    """

    # HIPAA Safe Harbor: 18 identifiers to remove
    IDENTIFIERS_TO_REMOVE = [
        "names",
        "geographic_subdivisions_smaller_than_state",
        "dates_except_year",
        "telephone_numbers",
        "fax_numbers",
        "email_addresses",
        "social_security_numbers",
        "medical_record_numbers",
        "health_plan_numbers",
        "account_numbers",
        "certificate_license_numbers",
        "vehicle_identifiers",
        "device_identifiers",
        "web_urls",
        "ip_addresses",
        "biometric_identifiers",
        "full_face_photos",
        "other_unique_identifiers"
    ]

    @capability("deidentify")
    @requires_peer("spiffe://analytics.org/agent/analytics")
    async def deidentify(
        self,
        phi_record: Dict[str, Any],
        method: str = "safe_harbor"
    ) -> TaskResult:
        """
        De-identify PHI record.

        Methods:
        - safe_harbor: Remove 18 identifiers (HIPAA 164.514(b)(2))
        - expert_determination: Statistical method (164.514(b)(1))
        """
        self.logger.info(
            "De-identifying PHI",
            extra={
                "method": method,
                "record_id": phi_record.get("patient_id", "unknown")
            }
        )

        if method == "safe_harbor":
            deidentified = await self._safe_harbor_deidentify(phi_record)
        elif method == "expert_determination":
            deidentified = await self._expert_determination_deidentify(phi_record)
        else:
            return TaskResult(
                status="failed",
                error=f"Unknown method: {method}"
            )

        # Add de-identification attestation
        deidentified["deidentification"] = {
            "method": method,
            "performed_at": datetime.utcnow().isoformat(),
            "performed_by": str(self.spiffe_id),
            "hipaa_compliant": True
        }

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data=deidentified)]
            )],
            artifacts=[
                {
                    "type": "deidentified_record",
                    "data": deidentified
                }
            ]
        )

    async def _safe_harbor_deidentify(
        self,
        phi_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply HIPAA Safe Harbor de-identification.

        Removes all 18 identifier types.
        """
        deidentified = {
            # Keep: Diagnosis, procedures, lab results (clinical data)
            "diagnosis_codes": phi_record.get("diagnosis_codes", []),
            "procedure_codes": phi_record.get("procedure_codes", []),
            "lab_results": phi_record.get("lab_results", {}),
            "medications": phi_record.get("medications", []),

            # Geographic: Only state allowed
            "state": self._extract_state(phi_record.get("zip_code")),

            # Dates: Only year allowed
            "visit_year": self._extract_year(phi_record.get("visit_date")),

            # Age: Over 89 must be aggregated
            "age": self._safe_harbor_age(phi_record.get("date_of_birth")),

            # De-identified ID (not linkable to patient)
            "research_id": self._generate_research_id(phi_record.get("patient_id"))
        }

        # Remove all other fields (names, MRN, SSN, etc.)
        return deidentified

    async def _expert_determination_deidentify(
        self,
        phi_record: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply expert determination de-identification.

        Uses statistical methods to ensure very small re-identification risk.
        """
        # In production, use k-anonymity, l-diversity, etc.
        # For demo, use safe harbor
        return await self._safe_harbor_deidentify(phi_record)

    @staticmethod
    def _extract_state(zip_code: str) -> str:
        """Extract state from zip code."""
        # In production, use zip code database
        return "CA"  # Placeholder

    @staticmethod
    def _extract_year(date_str: str) -> int:
        """Extract year from date."""
        if not date_str:
            return None
        return datetime.fromisoformat(date_str).year

    @staticmethod
    def _safe_harbor_age(date_of_birth: str) -> str:
        """
        Calculate age per Safe Harbor rules.

        Ages over 89 must be aggregated to "90+".
        """
        if not date_of_birth:
            return "unknown"

        dob = datetime.fromisoformat(date_of_birth)
        age = (datetime.utcnow() - dob).days // 365

        if age > 89:
            return "90+"
        else:
            return str(age)

    @staticmethod
    def _generate_research_id(patient_id: str) -> str:
        """
        Generate research ID that cannot be linked back to patient.

        Uses one-way hash with secret salt.
        """
        # In production, use HSM-protected secret salt
        salt = "SECRET_SALT_STORED_IN_HSM"
        combined = f"{patient_id}:{salt}"
        return hashlib.sha256(combined.encode()).hexdigest()


async def main():
    agent = DeIdentificationAgent.from_config("config/deidentification.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

## OPA Policies for HIPAA Compliance

```rego
# policies/hipaa_authz.rego
package hipaa.authz

import rego.v1

default allow := false

# EMR system can send PHI to ingestion agent
allow if {
    input.caller_spiffe_id == "spiffe://hospital-a.org/system/emr"
    input.callee_spiffe_id == "spiffe://hospital-a.org/agent/phi-ingestion"
    input.action == "ingest_phi"
}

# Ingestion agent can check consent
allow if {
    input.caller_spiffe_id == "spiffe://hospital-a.org/agent/phi-ingestion"
    input.callee_spiffe_id == "spiffe://hospital-a.org/agent/consent"
    input.action == "check_consent"
}

# Ingestion agent can send to analytics (federated) IF:
# 1. Patient consented
# 2. Data minimized
allow if {
    input.caller_spiffe_id == "spiffe://hospital-a.org/agent/phi-ingestion"
    input.callee_spiffe_id == "spiffe://analytics.org/agent/aggregator"
    input.action == "receive_phi"

    # Verify consent (in production, check consent service)
    patient_consented

    # Verify data minimization
    is_minimized
}

patient_consented if {
    # In production, verify against consent database
    # For demo, check context
    input.context.patient_consented == true
}

is_minimized if {
    # Verify no direct identifiers in payload
    payload := input.context.payload.record

    # Must NOT contain direct identifiers
    not payload.first_name
    not payload.last_name
    not payload.ssn
    not payload.date_of_birth  # Only age_range allowed
}

# Analytics agent can request de-identification
allow if {
    input.caller_spiffe_id == "spiffe://analytics.org/agent/analytics"
    input.callee_spiffe_id == "spiffe://analytics.org/agent/deidentification"
    input.action == "deidentify"
}

# Only designated research agents can access de-identified data
allow if {
    input.caller_spiffe_id in data.hipaa.approved_researchers
    input.action == "query_research_database"
    is_deidentified_only
}

is_deidentified_only if {
    # Verify query only accesses de-identified data
    # In production, check database security labels
    true
}
```

### Consent Policy

```rego
# policies/consent_policy.rego
package consent.policy

import rego.v1

# Patient consent requirements
default allow := false

# Allow PHI sharing if:
# 1. Patient has active consent
# 2. Purpose matches consent
# 3. Recipient is authorized
# 4. Data is minimized

allow if {
    has_active_consent
    purpose_matches
    recipient_authorized
    data_minimized
}

has_active_consent if {
    # Check consent database
    consent := data.consents[input.patient_id]
    consent.status == "active"
    consent.expiry > time.now_ns()
}

purpose_matches if {
    consent := data.consents[input.patient_id]
    input.purpose in consent.approved_purposes
}

recipient_authorized if {
    consent := data.consents[input.patient_id]
    input.recipient in consent.approved_recipients
}

data_minimized if {
    # Verify only minimum necessary data elements
    input.data_elements
    all_necessary(input.data_elements)
}

all_necessary(elements) if {
    every element in elements {
        element in data.necessary_elements[input.purpose]
    }
}
```

## Configuration

```yaml
# config/phi_ingestion.yaml (Hospital A)
agent:
  name: "phi-ingestion"
  trust_domain: "hospital-a.org"
  description: "PHI ingestion with HIPAA compliance"

  capabilities:
    - name: "ingest_phi"
      description: "Ingest PHI from EMR system"

identity:
  provider: "spiffe"
  spiffe_endpoint: "unix:///run/spire/sockets/agent.sock"

  # Federated trust with analytics domain
  allowed_trust_domains:
    - "hospital-a.org"
    - "analytics.org"  # Federated for analytics sharing

authorization:
  provider: "opa"
  opa_endpoint: "http://opa:8181"
  policy_path: "hipaa/authz"
  default_action: "deny"

  audit:
    enabled: true
    destination: "file:///var/log/hipaa/phi-access.log"
    # HIPAA requires 6-year retention
    retention_years: 6
    # Audit logs must be tamper-proof
    integrity_protection: true

transport:
  tls_min_version: "1.3"
  peer_verification: "strict"
  # HIPAA requires encryption in transit
  encryption: "required"

server:
  host: "0.0.0.0"
  port: 8443
```

## Running the Example

```bash
# Start infrastructure (SPIRE federation for hospitals)
docker-compose -f docker-compose-hospitals.yaml up -d

# Register agents
./scripts/register-hospital-agents.sh

# Ingest PHI (with consent)
agentweave call \
    --target spiffe://hospital-a.org/agent/phi-ingestion \
    --capability ingest_phi \
    --data @sample_patient_record.json

# Check audit logs (HIPAA requirement)
tail -f /var/log/hipaa/phi-access.log
```

## Key Takeaways

### HIPAA Compliance Built-In

| HIPAA Requirement | AgentWeave Implementation |
|-------------------|---------------------------|
| **Access Control** (164.312(a)) | SPIFFE + OPA policies |
| **Audit Controls** (164.312(b)) | Automatic audit logging |
| **Integrity** (164.312(c)) | mTLS, cryptographic signatures |
| **Transmission Security** (164.312(e)) | mTLS (TLS 1.3 minimum) |
| **Minimum Necessary** (164.502(b)) | Data minimization in code |

### Consent-Based Access

```rego
allow if {
    has_active_consent
    purpose_matches
    recipient_authorized
}
```

### Immutable Audit Trail

Every PHI access logged:
```
[2025-12-07T10:00:00Z] accessor=spiffe://hospital-a.org/agent/phi-ingestion
                       action=ingest patient_id=<hash>
                       data_elements=[demographics,diagnoses]
```

### Federation for Multi-Hospital

Hospitals maintain separate trust domains but can share via federation:

```
hospital-a.org ←→ analytics.org ←→ hospital-b.org
```

## Compliance Benefits

- **Automatic audit logging**: Can't forget to log
- **Policy-enforced consent**: Can't access without consent
- **Data minimization**: Built into agent logic
- **Tamper-proof logs**: WORM storage integration
- **Cross-organization**: Federation with cryptographic trust

---

**Complete Code**: [GitHub Repository](https://github.com/agentweave/examples/tree/main/real-world/healthcare)
