# HIPAA-Compliant Healthcare Records Gateway

This example demonstrates a healthcare system where patient records must be
accessed with strict authorization, full audit trails, and cross-organization
federation. A hospital's records agent can share limited patient data with an
authorized insurance agent, but only specific fields and only for active claims.

## Architecture

```
Hospital Trust Domain                    Insurance Trust Domain
(hospital.health)                        (insurance.health)

+-----------------------+                +---------------------+
| Records Agent         |<-- mTLS + --->| Claims Agent        |
| (patient data)        |   federation  | (process claims)    |
+-----------------------+                +---------------------+
| - lookup_patient      |                | - process_claim     |
| - get_records         |                | - verify_coverage   |
| - get_claim_data      |<-- limited ---|                     |
|   (filtered view)     |    access     |                     |
+-----------------------+                +---------------------+
```

## Features Demonstrated

- **Cross-domain federation** -- Two independent trust domains
  (`hospital.health` and `insurance.health`) communicate over mTLS with
  federated trust bundles.
- **Field-level data filtering** -- The Records Agent returns different
  subsets of patient data depending on the caller's identity. Hospital
  internal agents see everything; insurance agents see only the fields
  needed for claim processing.
- **Comprehensive audit trails** -- Every data access is logged with
  caller identity, fields accessed, and justification (HIPAA requirement).
- **Justification-based access** -- Insurance agents must provide a
  justification string and reference an active claim to retrieve any
  patient data.
- **OPA policies for data classification** -- Rego policies enforce which
  SPIFFE identities can invoke which capabilities.
- **@audit_log on every operation** -- All capability invocations produce
  structured audit entries.

## Files

| File | Purpose |
|------|---------|
| `gateway.py` | RecordsAgent and ClaimsAgent implementations |
| `config/hospital.yaml` | Hospital records agent configuration |
| `config/insurance.yaml` | Insurance claims agent configuration |
| `policies/hospital.rego` | OPA authorization policy for the hospital |
| `test_gateway.py` | Tests for data filtering, cross-domain access, and audit trails |

## Access Levels

| Caller Type | Fields Visible |
|-------------|---------------|
| Hospital Internal | patient_id, name, dob, ssn, address, phone, insurance_id, diagnoses, medications, lab_results, notes |
| Insurance Claim | patient_id, name, dob, insurance_id, diagnoses, medications |
| Insurance Verify | patient_id, name, dob, insurance_id |

## Running the Demo

```bash
# From the repository root
cd examples/healthcare_gateway

# Print the architecture overview
python gateway.py

# Run the tests
pytest test_gateway.py -v
```

## Running with Full Infrastructure

```bash
# 1. Start SPIRE server for hospital.health trust domain
# 2. Start SPIRE server for insurance.health trust domain
# 3. Configure federation between the two trust domains
# 4. Start OPA with the hospital policy loaded

agentweave serve config/hospital.yaml
agentweave serve config/insurance.yaml
```
