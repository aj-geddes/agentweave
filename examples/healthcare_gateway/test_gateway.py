"""
Tests for the HIPAA-Compliant Healthcare Records Gateway.

Demonstrates testing field-level access control, audit trails,
data filtering, and claim validation logic.
Run with: pytest test_gateway.py -v
"""

import sys
from pathlib import Path

import pytest

# Allow importing the example module from this directory
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agentweave import AgentConfig
from agentweave.context import RequestContext, set_current_context
from agentweave.testing import MockIdentityProvider, MockAuthorizationProvider
from gateway import RecordsAgent, PATIENT_DB, ACTIVE_CLAIMS, ACCESS_LEVELS


# ---------------------------------------------------------------------------
# Helpers to set request context for different caller identities
# ---------------------------------------------------------------------------

def _set_hospital_context():
    """Set request context as a hospital internal agent."""
    ctx = RequestContext.create(
        caller_id="spiffe://hospital.health/agent/ehr",
        metadata={"task_type": "lookup_patient"},
    )
    set_current_context(ctx)
    return ctx


def _set_insurance_context():
    """Set request context as an insurance claims agent."""
    ctx = RequestContext.create(
        caller_id="spiffe://insurance.health/agent/claims",
        metadata={"task_type": "get_claim_data"},
    )
    set_current_context(ctx)
    return ctx


def _set_compliance_context():
    """Set request context as a compliance officer agent."""
    ctx = RequestContext.create(
        caller_id="spiffe://hospital.health/agent/compliance-officer",
        metadata={"task_type": "audit_report"},
    )
    set_current_context(ctx)
    return ctx


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def hospital_config():
    return AgentConfig(
        name="test-records",
        trust_domain="hospital.health",
        identity_provider="mtls-static",
        authz_provider="allow-all",
    )


@pytest.fixture
def records_agent(hospital_config):
    identity = MockIdentityProvider(
        spiffe_id="spiffe://hospital.health/agent/records",
        trust_domain="hospital.health",
    )
    authz = MockAuthorizationProvider(default_allow=True)
    agent = RecordsAgent(
        config=hospital_config,
        identity=identity,
        authz=authz,
    )
    return agent


# ---------------------------------------------------------------------------
# 1. Hospital internal lookup -- full record access
# ---------------------------------------------------------------------------

class TestHospitalInternalLookup:
    """Test hospital internal patient lookup returns all fields."""

    @pytest.mark.asyncio
    async def test_lookup_patient_returns_all_fields(self, records_agent):
        """Hospital internal lookup should return every field in the record."""
        _set_hospital_context()
        try:
            result = await records_agent.lookup_patient("P001")

            # Verify all hospital_internal fields are present
            assert result["patient_id"] == "P001"
            assert result["name"] == "Jane Smith"
            assert result["dob"] == "1985-03-15"
            assert result["ssn"] == "***-**-1234"
            assert result["address"] == "123 Main St, Springfield, IL"
            assert result["phone"] == "555-0101"
            assert result["insurance_id"] == "INS-A-789456"
            assert result["notes"] == "Patient managing conditions well. Follow-up in 3 months."

            # Verify nested data structures
            assert len(result["diagnoses"]) == 2
            assert result["diagnoses"][0]["code"] == "E11.9"
            assert result["diagnoses"][1]["code"] == "I10"

            assert len(result["medications"]) == 2
            assert result["medications"][0]["name"] == "Metformin"
            assert result["medications"][1]["name"] == "Lisinopril"

            assert len(result["lab_results"]) == 2
            assert result["lab_results"][0]["test"] == "HbA1c"
        finally:
            set_current_context(None)

    @pytest.mark.asyncio
    async def test_lookup_patient_not_found(self, records_agent):
        """Looking up a nonexistent patient should return an error."""
        _set_hospital_context()
        try:
            result = await records_agent.lookup_patient("P999")
            assert "error" in result
            assert result["patient_id"] == "P999"
        finally:
            set_current_context(None)


# ---------------------------------------------------------------------------
# 2. Insurance claim data filtering
# ---------------------------------------------------------------------------

class TestInsuranceClaimDataFiltering:
    """Test that insurance claim access returns only permitted fields."""

    @pytest.mark.asyncio
    async def test_claim_data_returns_only_insurance_fields(self, records_agent):
        """get_claim_data should return only insurance-level fields."""
        _set_insurance_context()
        try:
            result = await records_agent.get_claim_data(
                "P001", "CLM-001", "claim processing"
            )

            assert "error" not in result
            assert result["claim_id"] == "CLM-001"
            assert result["data_classification"] == "PHI - Insurance Claim Access"
            assert result["retention_notice"] == "Data must be deleted after claim resolution"

            patient_data = result["patient_data"]

            # Verify allowed fields are present
            assert patient_data["patient_id"] == "P001"
            assert patient_data["name"] == "Jane Smith"
            assert patient_data["dob"] == "1985-03-15"
            assert patient_data["insurance_id"] == "INS-A-789456"
            assert len(patient_data["diagnoses"]) == 2
            assert len(patient_data["medications"]) == 2

            # Verify sensitive fields are NOT present
            assert "ssn" not in patient_data
            assert "address" not in patient_data
            assert "phone" not in patient_data
            assert "notes" not in patient_data
            assert "lab_results" not in patient_data
        finally:
            set_current_context(None)

    @pytest.mark.asyncio
    async def test_claim_data_field_count(self, records_agent):
        """Filtered patient data should contain exactly the insurance_claim fields."""
        _set_insurance_context()
        try:
            result = await records_agent.get_claim_data(
                "P001", "CLM-001", "verification"
            )
            patient_data = result["patient_data"]
            expected_fields = set(ACCESS_LEVELS["insurance_claim"])
            actual_fields = set(patient_data.keys())
            assert actual_fields == expected_fields
        finally:
            set_current_context(None)


# ---------------------------------------------------------------------------
# 3. Invalid claim is rejected
# ---------------------------------------------------------------------------

class TestInvalidClaimRejected:
    """Test that a nonexistent claim ID is rejected."""

    @pytest.mark.asyncio
    async def test_invalid_claim_rejected(self, records_agent):
        """A nonexistent claim ID should be rejected with an error."""
        _set_insurance_context()
        try:
            result = await records_agent.get_claim_data("P001", "CLM-999", "test")
            assert "error" in result
            assert result["claim_id"] == "CLM-999"
        finally:
            set_current_context(None)


# ---------------------------------------------------------------------------
# 4. Claim / patient mismatch rejected
# ---------------------------------------------------------------------------

class TestClaimPatientMismatch:
    """Test that a claim belonging to a different patient is rejected."""

    @pytest.mark.asyncio
    async def test_claim_patient_mismatch_rejected(self, records_agent):
        """A claim that belongs to a different patient should be rejected."""
        _set_insurance_context()
        try:
            # CLM-001 belongs to P001, not P002
            result = await records_agent.get_claim_data("P002", "CLM-001", "test")
            assert "error" in result
            assert "match" in result["error"].lower() or "mismatch" in result["error"].lower()
        finally:
            set_current_context(None)

    @pytest.mark.asyncio
    async def test_valid_claim_for_correct_patient(self, records_agent):
        """CLM-002 should work for P002 (positive control)."""
        _set_insurance_context()
        try:
            result = await records_agent.get_claim_data(
                "P002", "CLM-002", "new claim processing"
            )
            assert "error" not in result
            assert result["patient_data"]["patient_id"] == "P002"
            assert result["patient_data"]["name"] == "John Doe"
        finally:
            set_current_context(None)


# ---------------------------------------------------------------------------
# 5. Audit trail logging
# ---------------------------------------------------------------------------

class TestAuditTrail:
    """Test HIPAA audit trail logging."""

    @pytest.mark.asyncio
    async def test_audit_entries_logged(self, records_agent):
        """Multiple operations should produce corresponding audit trail entries."""
        _set_hospital_context()
        try:
            await records_agent.lookup_patient("P001")
        finally:
            set_current_context(None)

        _set_insurance_context()
        try:
            await records_agent.get_claim_data("P001", "CLM-001", "audit test")
        finally:
            set_current_context(None)

        _set_hospital_context()
        try:
            await records_agent.lookup_patient("P002", reason="emergency")
        finally:
            set_current_context(None)

        _set_compliance_context()
        try:
            report = await records_agent.audit_report()
        finally:
            set_current_context(None)

        assert report["total_access_events"] == 3
        entries = report["entries"]
        assert len(entries) == 3

    @pytest.mark.asyncio
    async def test_audit_entry_has_correct_fields(self, records_agent):
        """Each audit entry should contain caller, action, and patient_id."""
        _set_hospital_context()
        try:
            await records_agent.lookup_patient("P001", reason="checkup")
        finally:
            set_current_context(None)

        _set_compliance_context()
        try:
            report = await records_agent.audit_report()
        finally:
            set_current_context(None)

        entry = report["entries"][0]

        assert "caller" in entry
        assert entry["action"] == "lookup_patient"
        assert entry["patient_id"] == "P001"
        assert entry["justification"] == "checkup"
        assert entry["access_granted"] is True
        assert "timestamp" in entry

    @pytest.mark.asyncio
    async def test_audit_filter_by_patient(self, records_agent):
        """Audit report should support filtering by patient_id."""
        _set_hospital_context()
        try:
            await records_agent.lookup_patient("P001")
            await records_agent.lookup_patient("P002")
        finally:
            set_current_context(None)

        _set_insurance_context()
        try:
            await records_agent.get_claim_data("P001", "CLM-001", "test")
        finally:
            set_current_context(None)

        # Filter to P001 only
        _set_compliance_context()
        try:
            report = await records_agent.audit_report(patient_id="P001")
        finally:
            set_current_context(None)

        # Should have 2 entries for P001 (lookup + claim data)
        assert report["total_access_events"] == 2
        for entry in report["entries"]:
            assert entry["patient_id"] == "P001"

    @pytest.mark.asyncio
    async def test_audit_denied_access_logged(self, records_agent):
        """Denied access attempts (invalid claim) should also be logged."""
        _set_insurance_context()
        try:
            await records_agent.get_claim_data("P001", "CLM-999", "suspicious")
        finally:
            set_current_context(None)

        _set_compliance_context()
        try:
            report = await records_agent.audit_report()
        finally:
            set_current_context(None)

        assert report["total_access_events"] == 1

        entry = report["entries"][0]
        assert entry["action"] == "get_claim_data:denied"
        assert entry["fields_accessed"] == []

    @pytest.mark.asyncio
    async def test_audit_report_has_generated_timestamp(self, records_agent):
        """Audit report should include a generated_at timestamp."""
        _set_compliance_context()
        try:
            report = await records_agent.audit_report()
        finally:
            set_current_context(None)

        assert "generated_at" in report


# ---------------------------------------------------------------------------
# 6. Field filtering utility
# ---------------------------------------------------------------------------

class TestFieldFiltering:
    """Test the _filter_fields utility method directly."""

    def test_filter_fields_basic(self, records_agent):
        """Filtering should return only the specified fields."""
        record = {
            "patient_id": "P001",
            "name": "Jane Smith",
            "ssn": "***-**-1234",
            "phone": "555-0101",
        }
        result = records_agent._filter_fields(record, ["patient_id", "name"])
        assert result == {"patient_id": "P001", "name": "Jane Smith"}
        assert "ssn" not in result
        assert "phone" not in result

    def test_filter_fields_empty_allowed(self, records_agent):
        """Empty allowed_fields list should return empty dict."""
        record = {"patient_id": "P001", "name": "Jane Smith"}
        result = records_agent._filter_fields(record, [])
        assert result == {}

    def test_filter_fields_all_allowed(self, records_agent):
        """Allowing all keys should return the full record."""
        record = {"patient_id": "P001", "name": "Jane Smith", "dob": "1985-03-15"}
        result = records_agent._filter_fields(
            record, ["patient_id", "name", "dob"]
        )
        assert result == record

    def test_filter_fields_nonexistent_allowed(self, records_agent):
        """Allowed fields not present in the record should be silently skipped."""
        record = {"patient_id": "P001"}
        result = records_agent._filter_fields(
            record, ["patient_id", "nonexistent_field"]
        )
        assert result == {"patient_id": "P001"}
        assert "nonexistent_field" not in result

    def test_filter_fields_preserves_nested_structures(self, records_agent):
        """Filtering should preserve nested list/dict values intact."""
        record = {
            "patient_id": "P001",
            "diagnoses": [
                {"code": "E11.9", "description": "Type 2 diabetes"},
            ],
            "ssn": "***-**-1234",
        }
        result = records_agent._filter_fields(record, ["patient_id", "diagnoses"])
        assert result["patient_id"] == "P001"
        assert len(result["diagnoses"]) == 1
        assert result["diagnoses"][0]["code"] == "E11.9"
        assert "ssn" not in result

    def test_filter_fields_with_hospital_internal_level(self, records_agent):
        """Using ACCESS_LEVELS['hospital_internal'] should include all fields."""
        patient = PATIENT_DB["P001"]
        result = records_agent._filter_fields(
            patient, ACCESS_LEVELS["hospital_internal"]
        )
        assert set(result.keys()) == set(ACCESS_LEVELS["hospital_internal"])

    def test_filter_fields_with_insurance_claim_level(self, records_agent):
        """Using ACCESS_LEVELS['insurance_claim'] should exclude sensitive fields."""
        patient = PATIENT_DB["P001"]
        result = records_agent._filter_fields(
            patient, ACCESS_LEVELS["insurance_claim"]
        )
        assert set(result.keys()) == set(ACCESS_LEVELS["insurance_claim"])
        assert "ssn" not in result
        assert "address" not in result
        assert "phone" not in result
        assert "notes" not in result
        assert "lab_results" not in result
