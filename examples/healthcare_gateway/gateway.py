"""
HIPAA-Compliant Healthcare Records Gateway

Demonstrates:
- Cross-domain federation between hospital and insurance
- Field-level access control based on caller identity
- Comprehensive audit trails for HIPAA compliance
- Data classification and redaction
- Every operation audit-logged with justification
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from agentweave import (
    SecureAgent,
    AgentConfig,
    capability,
    requires_peer,
    audit_log,
    get_current_context,
)


# Simulated patient database
PATIENT_DB = {
    "P001": {
        "patient_id": "P001",
        "name": "Jane Smith",
        "dob": "1985-03-15",
        "ssn": "***-**-1234",
        "address": "123 Main St, Springfield, IL",
        "phone": "555-0101",
        "insurance_id": "INS-A-789456",
        "diagnoses": [
            {"code": "E11.9", "description": "Type 2 diabetes", "date": "2023-01-15"},
            {"code": "I10", "description": "Essential hypertension", "date": "2023-06-01"},
        ],
        "medications": [
            {"name": "Metformin", "dosage": "500mg", "frequency": "2x daily"},
            {"name": "Lisinopril", "dosage": "10mg", "frequency": "1x daily"},
        ],
        "lab_results": [
            {"test": "HbA1c", "value": "7.2%", "date": "2024-01-10", "status": "above_normal"},
            {"test": "Blood Pressure", "value": "138/88", "date": "2024-01-10", "status": "elevated"},
        ],
        "notes": "Patient managing conditions well. Follow-up in 3 months.",
    },
    "P002": {
        "patient_id": "P002",
        "name": "John Doe",
        "dob": "1972-08-22",
        "ssn": "***-**-5678",
        "address": "456 Oak Ave, Chicago, IL",
        "phone": "555-0202",
        "insurance_id": "INS-B-123789",
        "diagnoses": [
            {"code": "M54.5", "description": "Low back pain", "date": "2024-01-05"},
        ],
        "medications": [
            {"name": "Ibuprofen", "dosage": "400mg", "frequency": "as needed"},
        ],
        "lab_results": [],
        "notes": "Acute episode. Physical therapy recommended.",
    },
}

# Active claims that justify insurance access
ACTIVE_CLAIMS = {
    "CLM-001": {
        "patient_id": "P001",
        "insurance_id": "INS-A-789456",
        "status": "active",
        "type": "ongoing_treatment",
    },
    "CLM-002": {
        "patient_id": "P002",
        "insurance_id": "INS-B-123789",
        "status": "active",
        "type": "new_claim",
    },
}

# Fields visible to different caller types
ACCESS_LEVELS = {
    "hospital_internal": [
        "patient_id", "name", "dob", "ssn", "address", "phone",
        "insurance_id", "diagnoses", "medications", "lab_results", "notes",
    ],
    "insurance_claim": [
        "patient_id", "name", "dob", "insurance_id",
        "diagnoses", "medications",
    ],
    "insurance_verify": [
        "patient_id", "name", "dob", "insurance_id",
    ],
}


class RecordsAgent(SecureAgent):
    """
    Hospital Records Agent - manages patient data with strict access control.

    Capabilities:
    - lookup_patient: Find patient by ID (hospital internal only)
    - get_records: Get full patient records (hospital internal only)
    - get_claim_data: Get filtered patient data for insurance claims
    - audit_report: Generate HIPAA audit report (compliance officers only)
    """

    def __init__(self, config: AgentConfig, **kwargs):
        super().__init__(config=config, **kwargs)
        self._audit_trail: list[dict] = []

    def _log_access(self, caller: str, patient_id: str, action: str,
                    fields_accessed: list[str], justification: str):
        """Log every data access for HIPAA compliance."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "caller": caller,
            "patient_id": patient_id,
            "action": action,
            "fields_accessed": fields_accessed,
            "justification": justification,
            "access_granted": True,
        }
        self._audit_trail.append(entry)

    def _filter_fields(self, record: dict, allowed_fields: list[str]) -> dict:
        """Return only the allowed fields from a patient record."""
        return {k: v for k, v in record.items() if k in allowed_fields}

    @capability("lookup_patient")
    @requires_peer("spiffe://hospital.health/agent/*")
    @audit_log()
    async def lookup_patient(self, patient_id: str,
                             reason: str = "clinical") -> dict:
        """
        Look up a patient by ID. Hospital internal use only.
        Full access to all fields.
        """
        ctx = get_current_context()
        caller = ctx.caller_id if ctx else "unknown"

        patient = PATIENT_DB.get(patient_id)
        if not patient:
            return {"error": "Patient not found", "patient_id": patient_id}

        fields = ACCESS_LEVELS["hospital_internal"]
        self._log_access(caller, patient_id, "lookup_patient", fields, reason)

        return self._filter_fields(patient, fields)

    @capability("get_records")
    @requires_peer("spiffe://hospital.health/agent/*")
    @audit_log()
    async def get_records(self, patient_id: str, record_type: str = "all",
                          reason: str = "clinical") -> dict:
        """
        Get patient records. Hospital internal only.
        Can filter by record type: diagnoses, medications, lab_results, all.
        """
        ctx = get_current_context()
        caller = ctx.caller_id if ctx else "unknown"

        patient = PATIENT_DB.get(patient_id)
        if not patient:
            return {"error": "Patient not found", "patient_id": patient_id}

        if record_type == "all":
            data = self._filter_fields(patient, ACCESS_LEVELS["hospital_internal"])
        elif record_type in ("diagnoses", "medications", "lab_results"):
            data = {
                "patient_id": patient["patient_id"],
                "name": patient["name"],
                record_type: patient.get(record_type, []),
            }
        else:
            return {"error": f"Unknown record type: {record_type}"}

        self._log_access(caller, patient_id, f"get_records:{record_type}",
                         list(data.keys()), reason)
        return data

    @capability("get_claim_data")
    @requires_peer("spiffe://insurance.health/agent/*")
    @audit_log()
    async def get_claim_data(self, patient_id: str, claim_id: str,
                             justification: str) -> dict:
        """
        Get filtered patient data for insurance claim processing.

        Only returns fields authorized for insurance access.
        Requires an active claim and justification.
        """
        ctx = get_current_context()
        caller = ctx.caller_id if ctx else "unknown"

        # Verify claim exists and is active
        claim = ACTIVE_CLAIMS.get(claim_id)
        if not claim:
            self._log_access(caller, patient_id, "get_claim_data:denied",
                             [], f"Claim {claim_id} not found")
            return {"error": "Claim not found", "claim_id": claim_id}

        if claim["patient_id"] != patient_id:
            self._log_access(caller, patient_id, "get_claim_data:denied",
                             [], f"Claim {claim_id} does not match patient")
            return {"error": "Claim does not match patient"}

        if claim["status"] != "active":
            self._log_access(caller, patient_id, "get_claim_data:denied",
                             [], f"Claim {claim_id} is not active")
            return {"error": "Claim is not active"}

        # Get patient data with insurance-level filtering
        patient = PATIENT_DB.get(patient_id)
        if not patient:
            return {"error": "Patient not found"}

        fields = ACCESS_LEVELS["insurance_claim"]
        filtered = self._filter_fields(patient, fields)

        self._log_access(caller, patient_id, "get_claim_data",
                         fields, justification)

        return {
            "claim_id": claim_id,
            "patient_data": filtered,
            "data_classification": "PHI - Insurance Claim Access",
            "retention_notice": "Data must be deleted after claim resolution",
        }

    @capability("audit_report")
    @requires_peer("spiffe://hospital.health/agent/compliance*")
    @audit_log()
    async def audit_report(self, patient_id: Optional[str] = None,
                           start_date: Optional[str] = None) -> dict:
        """
        Generate audit report. Compliance officers only.
        """
        entries = self._audit_trail
        if patient_id:
            entries = [e for e in entries if e["patient_id"] == patient_id]
        if start_date:
            entries = [e for e in entries if e["timestamp"] >= start_date]

        return {
            "total_access_events": len(entries),
            "entries": entries,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


class ClaimsAgent(SecureAgent):
    """
    Insurance Claims Agent - processes claims by requesting data from hospitals.

    Demonstrates cross-domain federation: insurance.health -> hospital.health
    """

    @capability("process_claim")
    @audit_log()
    async def process_claim(self, claim_id: str, patient_id: str) -> dict:
        """
        Process an insurance claim by requesting patient data from hospital.
        """
        # Request patient data from hospital records agent
        patient_data = await self.call_agent(
            target="spiffe://hospital.health/agent/records",
            task_type="get_claim_data",
            payload={
                "patient_id": patient_id,
                "claim_id": claim_id,
                "justification": f"Processing claim {claim_id}",
            },
        )

        if "error" in patient_data:
            return {
                "claim_id": claim_id,
                "status": "failed",
                "reason": patient_data["error"],
            }

        # Process the claim with filtered patient data
        diagnoses = patient_data.get("patient_data", {}).get("diagnoses", [])

        return {
            "claim_id": claim_id,
            "status": "processing",
            "patient_id": patient_id,
            "diagnoses_count": len(diagnoses),
            "data_classification": patient_data.get("data_classification"),
            "next_step": "medical_review",
        }

    @capability("verify_coverage")
    @audit_log()
    async def verify_coverage(self, patient_id: str,
                              procedure_code: str) -> dict:
        """Verify if a procedure is covered under patient's plan."""
        return {
            "patient_id": patient_id,
            "procedure_code": procedure_code,
            "covered": True,
            "copay": "$25.00",
            "requires_preauth": procedure_code.startswith("7"),
        }


async def demo():
    """Demonstrate the healthcare gateway."""
    print("HIPAA-Compliant Healthcare Records Gateway")
    print("=" * 50)
    print()
    print("Trust Domains:")
    print("  hospital.health  - Hospital internal systems")
    print("  insurance.health - Insurance company systems")
    print()
    print("Access Control:")
    print("  Hospital agents  -> Full patient records")
    print("  Insurance agents -> Filtered claim data only")
    print("  Compliance agents -> Audit reports")
    print()
    print("Data Classification:")
    for level, fields in ACCESS_LEVELS.items():
        print(f"  {level}: {', '.join(fields)}")


if __name__ == "__main__":
    asyncio.run(demo())
