---
layout: page
title: Audit Logging
description: Comprehensive guide to audit logging for security monitoring, compliance, and forensics
permalink: /security/audit-logging/
parent: Security
nav_order: 4
---

# Audit Logging Guide

Audit logging is critical for security monitoring, compliance, incident response, and forensics. AgentWeave provides comprehensive audit logging for all security-relevant events.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## What Gets Logged

AgentWeave logs security-relevant events at multiple layers:

### 1. Authorization Decisions

Every authorization check is logged:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "level": "info",
  "event_type": "authorization",
  "caller_spiffe_id": "spiffe://example.com/agent/api-gateway/prod",
  "callee_spiffe_id": "spiffe://example.com/agent/data-processor/prod",
  "capability": "process_data",
  "action": "execute",
  "decision": "allow",
  "reason": "same_trust_domain",
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "span_id": "1234567890abcdef"
}
```

**Logged fields:**
- `timestamp`: ISO 8601 timestamp with milliseconds
- `event_type`: Type of event (authorization, capability_call, etc.)
- `caller_spiffe_id`: Who made the request
- `callee_spiffe_id`: Who received the request
- `capability`: Capability being invoked
- `action`: Specific action (execute, query, etc.)
- `decision`: allow or deny
- `reason`: Why access was allowed/denied (from OPA)
- `trace_id`: Distributed trace ID for correlation
- `span_id`: Span ID for detailed tracing

### 2. Capability Invocations

Every capability call is logged:

```json
{
  "timestamp": "2024-01-15T10:30:00.456Z",
  "level": "info",
  "event_type": "capability_call",
  "caller_spiffe_id": "spiffe://example.com/agent/api-gateway/prod",
  "callee_spiffe_id": "spiffe://example.com/agent/data-processor/prod",
  "capability": "process_data",
  "status": "success",
  "duration_ms": 123.45,
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "span_id": "abcdef1234567890"
}
```

### 3. Identity Events

SVID rotation and identity changes:

```json
{
  "timestamp": "2024-01-15T10:15:00.789Z",
  "level": "info",
  "event_type": "svid_update",
  "spiffe_id": "spiffe://example.com/agent/data-processor/prod",
  "expiry": "2024-01-15T11:15:00Z",
  "ttl_seconds": 3600,
  "trust_domain": "example.com"
}
```

### 4. Authentication Events

mTLS handshake results:

```json
{
  "timestamp": "2024-01-15T10:30:00.012Z",
  "level": "info",
  "event_type": "authentication",
  "peer_spiffe_id": "spiffe://example.com/agent/api-gateway/prod",
  "peer_trust_domain": "example.com",
  "tls_version": "1.3",
  "cipher_suite": "TLS_AES_256_GCM_SHA384",
  "status": "success"
}
```

### 5. Security Events

Anomalies and security-relevant events:

```json
{
  "timestamp": "2024-01-15T10:30:05.678Z",
  "level": "warning",
  "event_type": "security_event",
  "description": "High rate of authorization denials",
  "caller_spiffe_id": "spiffe://unknown.com/agent/suspicious",
  "denial_count": 50,
  "time_window_seconds": 60
}
```

### 6. Agent Lifecycle Events

Startup, shutdown, configuration changes:

```json
{
  "timestamp": "2024-01-15T10:00:00.000Z",
  "level": "info",
  "event_type": "agent_start",
  "agent_spiffe_id": "spiffe://example.com/agent/data-processor/prod",
  "version": "1.0.0",
  "config_hash": "sha256:abc123..."
}
```

---

## Audit Log Configuration

### Basic Configuration

Enable audit logging in your agent configuration:

```yaml
observability:
  audit_log:
    enabled: true
    level: "info"  # debug, info, warning, error
    format: "json"  # json or text
```

### Log Levels

Choose appropriate log level:

```yaml
observability:
  audit_log:
    level: "info"
```

**Levels:**
- `debug`: All events including verbose diagnostics
- `info`: Normal operational events (recommended)
- `warning`: Warnings and errors only
- `error`: Errors only

**Recommendations:**
- **Production**: `info` (captures all security events)
- **Development**: `debug` (helps debugging)
- **High-volume**: `warning` (reduces log volume)

### Field Selection

Control which fields are logged:

```yaml
observability:
  audit_log:
    fields:
      - "timestamp"
      - "event_type"
      - "caller_spiffe_id"
      - "callee_spiffe_id"
      - "capability"
      - "action"
      - "decision"
      - "reason"
      - "trace_id"
```

### Payload Logging

**Warning:** Logging payloads can expose sensitive data.

```yaml
observability:
  audit_log:
    include_payloads: false  # Recommended for production

    # If you must log payloads, redact sensitive fields
    redact_fields:
      - "password"
      - "ssn"
      - "credit_card"
      - "api_key"
```

**Best Practice:** Never log payloads in production unless required for compliance and properly secured.

---

## Log Destinations

### 1. File Destination

Write logs to local file:

```yaml
observability:
  audit_log:
    destination: "file"
    file_path: "/var/log/agentweave/audit.log"
    max_size_mb: 100
    max_backups: 10
    max_age_days: 30
    compress: true
```

**Considerations:**
- Set up log rotation (max_size_mb, max_backups)
- Ensure sufficient disk space
- Protect file with proper permissions (600)
- Not recommended for production (use centralized logging)

### 2. Syslog Destination

Send logs to syslog server:

```yaml
observability:
  audit_log:
    destination: "syslog"
    syslog_address: "logs.example.com:514"
    syslog_protocol: "tcp"  # tcp or udp
    syslog_facility: "local0"
    syslog_tag: "agentweave-audit"
```

**Protocols:**
- `tcp`: Reliable delivery (recommended)
- `udp`: Lower overhead, may lose logs
- `tls`: Encrypted syslog (port 6514)

**TLS Syslog:**
```yaml
observability:
  audit_log:
    destination: "syslog"
    syslog_address: "logs.example.com:6514"
    syslog_protocol: "tls"
    syslog_tls_verify: true
    syslog_tls_ca_cert: "/etc/ssl/syslog-ca.pem"
```

### 3. Cloud Logging

#### AWS CloudWatch

```yaml
observability:
  audit_log:
    destination: "cloudwatch"
    cloudwatch_group: "/aws/agentweave/audit"
    cloudwatch_stream: "agent-data-processor-prod"
    cloudwatch_region: "us-east-1"
```

#### Google Cloud Logging

```yaml
observability:
  audit_log:
    destination: "gcp_logging"
    gcp_project: "my-project"
    gcp_log_name: "agentweave-audit"
```

#### Azure Monitor

```yaml
observability:
  audit_log:
    destination: "azure_monitor"
    workspace_id: "12345678-1234-1234-1234-123456789012"
    workspace_key_env: "AZURE_WORKSPACE_KEY"
```

### 4. SIEM Integration

#### Splunk

```yaml
observability:
  audit_log:
    destination: "splunk"
    splunk_url: "https://splunk.example.com:8088"
    splunk_token_env: "SPLUNK_HEC_TOKEN"
    splunk_index: "agentweave_audit"
    splunk_source: "agentweave"
    splunk_sourcetype: "agentweave:audit"
```

#### Elastic Stack (ELK)

```yaml
observability:
  audit_log:
    destination: "elasticsearch"
    elasticsearch_url: "https://elasticsearch.example.com:9200"
    elasticsearch_index: "agentweave-audit"
    elasticsearch_api_key_env: "ELASTIC_API_KEY"
```

#### Datadog

```yaml
observability:
  audit_log:
    destination: "datadog"
    datadog_api_key_env: "DD_API_KEY"
    datadog_site: "datadoghq.com"
    datadog_service: "agentweave"
    datadog_source: "audit"
```

---

## Log Retention

### Retention Requirements

Configure retention based on compliance needs:

| Compliance | Minimum Retention |
|------------|------------------|
| SOC 2 | 1 year |
| HIPAA | 6 years |
| PCI DSS | 1 year (3 months online) |
| GDPR | As needed for purpose |
| FedRAMP | 1 year |

### Retention Configuration

#### In Cloud Logging

**AWS CloudWatch:**
```bash
aws logs put-retention-policy \
  --log-group-name /aws/agentweave/audit \
  --retention-in-days 2555  # 7 years for HIPAA
```

**GCP Logging:**
```bash
gcloud logging buckets update _Default \
  --location=global \
  --retention-days=2555
```

**Azure Monitor:**
```bash
az monitor log-analytics workspace update \
  --resource-group myResourceGroup \
  --workspace-name myWorkspace \
  --retention-time 2555
```

#### In SIEM

Configure retention in your SIEM:

**Splunk:**
```conf
[agentweave_audit]
coldPath = $SPLUNK_DB/agentweave_audit/colddb
homePath = $SPLUNK_DB/agentweave_audit/db
thawedPath = $SPLUNK_DB/agentweave_audit/thaweddb
maxTotalDataSizeMB = 500000
frozenTimePeriodInSecs = 220752000  # 7 years
```

### Archive to Cold Storage

For long-term retention, archive to object storage:

```yaml
# Example: Archive to S3 after 90 days
observability:
  audit_log:
    destination: "cloudwatch"
    cloudwatch_group: "/aws/agentweave/audit"
    archive:
      enabled: true
      after_days: 90
      s3_bucket: "agentweave-audit-archive"
      s3_prefix: "audit-logs/"
```

---

## Log Analysis

### Common Queries

#### Find All Access by Specific Agent

**Splunk:**
```spl
index=agentweave_audit caller_spiffe_id="spiffe://example.com/agent/api-gateway/prod"
| table timestamp, callee_spiffe_id, capability, decision
```

**Elastic:**
```json
{
  "query": {
    "term": {
      "caller_spiffe_id": "spiffe://example.com/agent/api-gateway/prod"
    }
  }
}
```

#### Find All Authorization Denials

**Splunk:**
```spl
index=agentweave_audit event_type=authorization decision=deny
| stats count by caller_spiffe_id, reason
| sort -count
```

**Elastic:**
```json
{
  "query": {
    "bool": {
      "must": [
        {"term": {"event_type": "authorization"}},
        {"term": {"decision": "deny"}}
      ]
    }
  },
  "aggs": {
    "by_caller": {
      "terms": {"field": "caller_spiffe_id"},
      "aggs": {
        "by_reason": {
          "terms": {"field": "reason"}
        }
      }
    }
  }
}
```

#### Find Access to Specific Capability

**Splunk:**
```spl
index=agentweave_audit capability="process_sensitive_data"
| table timestamp, caller_spiffe_id, decision, duration_ms
```

#### Trace Specific Request

**Splunk:**
```spl
index=agentweave_audit trace_id="a1b2c3d4-e5f6-7890-abcd-ef1234567890"
| sort timestamp
| table timestamp, event_type, caller_spiffe_id, callee_spiffe_id, capability, decision
```

#### Find High-Volume Callers

**Splunk:**
```spl
index=agentweave_audit event_type=capability_call
| stats count by caller_spiffe_id
| sort -count
| head 20
```

### Security Queries

#### Detect Brute Force Attempts

**Splunk:**
```spl
index=agentweave_audit event_type=authorization decision=deny
| bin _time span=1m
| stats count by _time, caller_spiffe_id
| where count > 10
```

#### Detect Unusual Access Patterns

**Splunk:**
```spl
index=agentweave_audit event_type=authorization
| stats count by caller_spiffe_id, callee_spiffe_id, capability
| where count < 10  # Unusual/rare combinations
```

#### Find Access Outside Business Hours

**Splunk:**
```spl
index=agentweave_audit event_type=capability_call
| eval hour=strftime(_time, "%H")
| where hour < 6 OR hour > 20
| table timestamp, caller_spiffe_id, capability
```

#### Detect Lateral Movement

**Splunk:**
```spl
index=agentweave_audit event_type=capability_call
| stats dc(callee_spiffe_id) as unique_targets by caller_spiffe_id
| where unique_targets > 10  # Calling many different agents
```

---

## Alerting on Security Events

### Prometheus Alerts

```yaml
groups:
  - name: agentweave-security
    rules:
      # High denial rate
      - alert: HighAuthzDenialRate
        expr: rate(agentweave_authz_denied_total[5m]) > 10
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High authorization denial rate"
          description: "{{ $value }} denials per second in last 5 minutes"

      # Unknown caller
      - alert: UnknownCallerAttempt
        expr: agentweave_authz_denied_total{reason="unknown_caller"} > 0
        labels:
          severity: critical
        annotations:
          summary: "Unknown agent attempted access"
          description: "Agent {{ $labels.caller }} not recognized"

      # SVID rotation failure
      - alert: SVIDRotationFailed
        expr: agentweave_svid_rotation_errors_total > 0
        labels:
          severity: critical
        annotations:
          summary: "SVID rotation failed"
          description: "Agent {{ $labels.agent }} failed to rotate SVID"

      # Unusual capability usage
      - alert: UnusualAdminCapability
        expr: rate(agentweave_capability_calls_total{capability="admin"}[1h]) > 1
        labels:
          severity: warning
        annotations:
          summary: "Unusual admin capability usage"
```

### SIEM Alerts

#### Splunk Alert: Multiple Failures from Same Caller

```spl
index=agentweave_audit event_type=authorization decision=deny
| bin _time span=5m
| stats count by _time, caller_spiffe_id
| where count > 20
```

**Action:** Send email, create ticket, trigger webhook

#### Elastic Watcher: Access to Sensitive Capability

```json
{
  "trigger": {
    "schedule": {"interval": "5m"}
  },
  "input": {
    "search": {
      "request": {
        "indices": ["agentweave-audit"],
        "body": {
          "query": {
            "bool": {
              "must": [
                {"term": {"capability": "delete_all_data"}},
                {"range": {"timestamp": {"gte": "now-5m"}}}
              ]
            }
          }
        }
      }
    }
  },
  "condition": {
    "compare": {"ctx.payload.hits.total": {"gt": 0}}
  },
  "actions": {
    "send_email": {
      "email": {
        "to": "security@example.com",
        "subject": "Critical: delete_all_data capability invoked",
        "body": "Someone invoked delete_all_data capability. Review immediately."
      }
    }
  }
}
```

---

## Compliance Reporting

### SOC 2 Audit Report

Generate report of all authorization decisions:

**Splunk:**
```spl
index=agentweave_audit event_type=authorization
  earliest=-30d@d latest=now
| stats count by decision, reason
| eval total=sum(count)
| eval percentage=round((count/total)*100, 2)
| table decision, reason, count, percentage
```

### HIPAA Access Report

Who accessed PHI and when:

**Splunk:**
```spl
index=agentweave_audit capability="get_patient_data"
  earliest=-1y@y latest=now
| table timestamp, caller_spiffe_id, decision, trace_id
| sort timestamp desc
```

### PCI DSS Cardholder Data Access

**Splunk:**
```spl
index=agentweave_audit capability="process_payment"
  earliest=-1y@y latest=now
| stats count by caller_spiffe_id, decision
| table caller_spiffe_id, decision, count
```

---

## Log Security

### Protect Log Files

If using file destination:

```bash
# Set proper permissions
chmod 600 /var/log/agentweave/audit.log
chown agentweave:agentweave /var/log/agentweave/audit.log

# Prevent modification
chattr +a /var/log/agentweave/audit.log  # Append-only
```

### Encrypt Logs in Transit

Use TLS for syslog:

```yaml
observability:
  audit_log:
    destination: "syslog"
    syslog_protocol: "tls"
    syslog_tls_verify: true
```

### Sign Logs

For tamper-evidence, consider log signing:

```yaml
observability:
  audit_log:
    signing:
      enabled: true
      key_path: "/etc/agentweave/signing-key.pem"
      algorithm: "RS256"
```

Each log entry includes signature:

```json
{
  "timestamp": "2024-01-15T10:30:00.123Z",
  "event_type": "authorization",
  "caller_spiffe_id": "spiffe://example.com/agent/api-gateway",
  // ... other fields ...
  "signature": "eyJhbGciOiJSUzI1NiIs..."
}
```

### Immutable Storage

Use write-once storage for compliance:

- **AWS S3**: Object Lock
- **GCP**: Bucket lock
- **Azure**: Immutable blob storage

**AWS S3 Example:**
```bash
aws s3api put-object-lock-configuration \
  --bucket agentweave-audit-archive \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Years": 7
      }
    }
  }'
```

---

## Best Practices

### Do's

✅ **Enable audit logging in production**
```yaml
observability:
  audit_log:
    enabled: true
```

✅ **Send logs to centralized SIEM**
```yaml
observability:
  audit_log:
    destination: "syslog"
    syslog_address: "siem.example.com:514"
```

✅ **Configure appropriate retention**
```yaml
observability:
  audit_log:
    retention_days: 2555  # 7 years for HIPAA
```

✅ **Set up automated alerts**
```yaml
# Prometheus alerts, SIEM alerts, etc.
```

✅ **Review logs regularly**
- Daily: Security events
- Weekly: Access patterns
- Monthly: Compliance reports

✅ **Test log pipeline**
```bash
# Ensure logs are reaching SIEM
agentweave test-audit-log
```

### Don'ts

❌ **Don't log sensitive payloads**
```yaml
observability:
  audit_log:
    include_payloads: false  # Keep this false!
```

❌ **Don't use only local file logging in production**
```yaml
# ❌ Bad for production
observability:
  audit_log:
    destination: "file"

# ✅ Good for production
observability:
  audit_log:
    destination: "syslog"
```

❌ **Don't ignore log volume**
- Monitor log volume metrics
- Set up alerts for unusual volume
- Have capacity planning

❌ **Don't forget log security**
- Encrypt in transit (TLS)
- Protect access (RBAC)
- Prevent tampering (immutable storage)

---

## Troubleshooting

### Logs Not Appearing

**Check agent logs:**
```bash
kubectl logs -n agentweave pod/data-processor-abc123 | grep audit
```

**Verify configuration:**
```bash
agentweave validate config/production.yaml
```

**Test connectivity:**
```bash
# Syslog
nc -zv logs.example.com 514

# HTTPS
curl -I https://splunk.example.com:8088
```

### High Log Volume

**Reduce verbosity:**
```yaml
observability:
  audit_log:
    level: "warning"  # Instead of "info"
```

**Filter events:**
```yaml
observability:
  audit_log:
    exclude_events:
      - "health_check"
      - "heartbeat"
```

**Sample logs:**
```yaml
observability:
  audit_log:
    sampling:
      enabled: true
      rate: 0.1  # Log 10% of events
```

---

## Summary

Audit logging provides:
- **Security monitoring**: Detect attacks and anomalies
- **Compliance**: Evidence for auditors
- **Forensics**: Investigate incidents
- **Operational insights**: Understand access patterns

**Key Recommendations:**
1. Enable audit logging in production
2. Send logs to centralized SIEM
3. Configure retention per compliance requirements
4. Set up automated alerts
5. Review logs regularly
6. Protect logs from tampering

## Next Steps

- Configure audit logging: See [Configuration Reference](../configuration/)
- Set up monitoring: See [Observability Guide](../guides/monitoring/)
- Review compliance: See [Compliance](compliance/)
- Understand threats: See [Threat Model](threat-model/)
