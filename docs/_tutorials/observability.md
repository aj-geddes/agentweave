---
layout: tutorial
title: Adding Observability
permalink: /tutorials/observability/
nav_order: 5
parent: Tutorials
difficulty: Intermediate
duration: 30 minutes
---

# Adding Observability

In this tutorial, you'll add comprehensive observability to your agents with metrics, distributed tracing, and structured logging. You'll set up a complete observability stack to monitor production agents.

## Learning Objectives

By completing this tutorial, you will:
- Configure Prometheus metrics for agents
- Set up OpenTelemetry distributed tracing
- Implement structured logging best practices
- Deploy Grafana dashboards for visualization
- Use Jaeger to view distributed traces
- Understand audit logging patterns

## Prerequisites

Before starting, ensure you have:
- **Completed** [Building Your First Agent](/tutorials/first-agent/)
- **Docker or Kubernetes** for running observability tools
- **Basic monitoring knowledge** (metrics, logs, traces)
- **8GB RAM minimum** for running the observability stack

**Time estimate:** 30 minutes

## The Three Pillars of Observability

**Metrics** - Quantitative measurements over time
- Request rates, error rates, latencies
- System resources (CPU, memory)
- Business metrics (documents processed, etc.)

**Logs** - Discrete events with context
- Structured JSON logs
- Request/response details
- Error messages and stack traces

**Traces** - Request flows through distributed systems
- End-to-end request visualization
- Performance bottlenecks
- Service dependencies

## Architecture Overview

```
┌─────────────┐
│   Agent     │ ──metrics──> Prometheus ──> Grafana
│             │
│             │ ──logs────> stdout ──> Loki (optional)
│             │
│             │ ──traces──> OTLP Collector ──> Jaeger
└─────────────┘
```

## Step 1: Configure Metrics

AgentWeave automatically exports Prometheus metrics. Let's enable and customize them.

### Agent Configuration with Metrics

Create `config/observable_agent.yaml`:

```yaml
identity:
  spiffe_id: "spiffe://example.org/observable-agent"
  spire_socket: "/tmp/spire-agent/public/api.sock"
  trust_domain: "example.org"

authorization:
  engine: "opa"
  default_policy: "allow_all"

server:
  host: "0.0.0.0"
  port: 8443
  mtls:
    enabled: true
    cert_source: "spire"

# Observability Configuration
observability:
  # Metrics configuration
  metrics:
    enabled: true
    port: 9090
    path: "/metrics"

    # Custom labels added to all metrics
    labels:
      environment: "production"
      team: "platform"
      region: "us-west-2"

    # Histogram buckets for latency tracking
    latency_buckets: [0.001, 0.005, 0.010, 0.025, 0.050, 0.100, 0.250, 0.500, 1.0, 2.5, 5.0, 10.0]

  # Logging configuration
  logging:
    level: "INFO"  # DEBUG, INFO, WARNING, ERROR
    format: "json"  # json or text

    # Include caller information
    include_caller: true

    # Fields to include in every log
    default_fields:
      service: "observable-agent"
      version: "1.0.0"

  # Tracing configuration
  tracing:
    enabled: true

    # OpenTelemetry exporter
    exporter: "otlp"  # otlp, jaeger, zipkin

    # OTLP endpoint (collector)
    otlp_endpoint: "localhost:4317"

    # Sampling rate (0.0 to 1.0)
    # 1.0 = trace every request
    # 0.1 = trace 10% of requests
    sampling_rate: 1.0

    # Service name in traces
    service_name: "observable-agent"

metadata:
  name: "Observable Agent"
  version: "1.0.0"
```

### Available Metrics

AgentWeave automatically tracks:

```
# Request metrics
agentweave_requests_total{capability, status, caller_trust_domain}
agentweave_requests_in_flight{capability}

# Latency metrics (histogram)
agentweave_request_duration_seconds{capability, status}

# Agent call metrics (for A2A communication)
agentweave_agent_calls_total{target_agent, capability, status}
agentweave_agent_call_duration_seconds{target_agent, capability}

# Authorization metrics
agentweave_authz_decisions_total{policy, decision}
agentweave_authz_duration_seconds{policy}

# Identity metrics
agentweave_identity_renewals_total{status}
agentweave_identity_ttl_seconds
```

### Test Metrics Endpoint

Start your agent and check metrics:

```bash
# Start agent
python agent.py config/observable_agent.yaml

# In another terminal, check metrics
curl http://localhost:9090/metrics
```

Output:
```
# HELP agentweave_requests_total Total requests processed
# TYPE agentweave_requests_total counter
agentweave_requests_total{capability="process",status="success",caller_trust_domain="example.org"} 42.0

# HELP agentweave_request_duration_seconds Request duration
# TYPE agentweave_request_duration_seconds histogram
agentweave_request_duration_seconds_bucket{capability="process",status="success",le="0.005"} 10.0
agentweave_request_duration_seconds_bucket{capability="process",status="success",le="0.010"} 35.0
agentweave_request_duration_seconds_sum{capability="process",status="success"} 1.234
agentweave_request_duration_seconds_count{capability="process",status="success"} 42.0
```

## Step 2: Set Up Prometheus

Create a Prometheus configuration to scrape your agent.

### Prometheus Configuration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

  # Attach these labels to all metrics
  external_labels:
    cluster: 'agentweave-cluster'
    environment: 'production'

# Scrape configurations
scrape_configs:
  # Scrape AgentWeave agents
  - job_name: 'agentweave-agents'

    # Scrape every 5 seconds for demo
    scrape_interval: 5s

    # Static targets (for demo)
    static_configs:
      - targets:
          - 'host.docker.internal:9090'  # Observable agent
          - 'host.docker.internal:9091'  # Another agent
        labels:
          service: 'agentweave'

    # For Kubernetes discovery
    # kubernetes_sd_configs:
    #   - role: pod
    #     namespaces:
    #       names:
    #         - agentweave
    # relabel_configs:
    #   - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
    #     action: keep
    #     regex: true

  # Scrape Prometheus itself
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
```

### Run Prometheus with Docker

```bash
# Run Prometheus
docker run -d \
  --name prometheus \
  -p 9091:9090 \
  -v $(pwd)/prometheus.yml:/etc/prometheus/prometheus.yml \
  prom/prometheus:latest

# Check Prometheus UI
open http://localhost:9091
```

In the Prometheus UI:
1. Go to Status > Targets
2. Verify your agent appears and is "UP"
3. Go to Graph
4. Query: `rate(agentweave_requests_total[5m])`

## Step 3: Configure Distributed Tracing

Set up OpenTelemetry and Jaeger for distributed tracing.

### Run Jaeger All-in-One

```bash
docker run -d \
  --name jaeger \
  -e COLLECTOR_OTLP_ENABLED=true \
  -p 16686:16686 \
  -p 4317:4317 \
  -p 4318:4318 \
  jaegertracing/all-in-one:latest
```

Ports:
- `16686` - Jaeger UI
- `4317` - OTLP gRPC receiver
- `4318` - OTLP HTTP receiver

### Agent Tracing Configuration

Your agent is already configured for tracing (see Step 1). The key settings:

```yaml
observability:
  tracing:
    enabled: true
    exporter: "otlp"
    otlp_endpoint: "localhost:4317"
    sampling_rate: 1.0  # Trace everything
```

### Test Distributed Tracing

Make some requests to your agent:

```bash
# Make several requests
for i in {1..10}; do
  agentweave-cli call \
    --agent spiffe://example.org/observable-agent \
    --capability process \
    --params '{"data": "test"}'
  sleep 1
done
```

View traces in Jaeger:
1. Open http://localhost:16686
2. Select service: "observable-agent"
3. Click "Find Traces"
4. Click on a trace to see details

You'll see:
- Request duration
- Capability execution time
- Authorization check time
- Identity verification time
- Any agent-to-agent calls

### Tracing Multi-Agent Systems

For multi-agent systems, traces automatically propagate across agents:

```
Trace: process-document-req-12345
├─ Span: orchestrator.process_document [150ms]
│  ├─ Span: authz.check [2ms]
│  ├─ Span: call_agent(worker) [140ms]
│  │  ├─ Span: mtls.handshake [10ms]
│  │  ├─ Span: worker.analyze_document [125ms]
│  │  │  ├─ Span: authz.check [2ms]
│  │  │  └─ Span: analyze.execute [120ms]
│  │  └─ Span: response.serialize [3ms]
│  └─ Span: response.build [5ms]
```

## Step 4: Structured Logging

AgentWeave uses structured JSON logging by default.

### Using the Logger in Your Agent

```python
from agentweave import Agent, capability
from agentweave.context import AgentContext

class LoggingAgent(Agent):
    """Agent demonstrating logging best practices."""

    @capability(name="process_order")
    async def process_order(
        self,
        context: AgentContext,
        order_id: str,
        amount: float
    ):
        # Log with structured fields
        self.logger.info(
            "Processing order",
            extra={
                "order_id": order_id,
                "amount": amount,
                "caller": context.caller_spiffe_id,
                "trace_id": context.trace_id
            }
        )

        try:
            # Business logic
            result = await self._process_order_internal(order_id, amount)

            # Log success
            self.logger.info(
                "Order processed successfully",
                extra={
                    "order_id": order_id,
                    "duration_ms": result['duration'],
                    "status": "success"
                }
            )

            return result

        except ValueError as e:
            # Log validation errors as warnings
            self.logger.warning(
                "Invalid order data",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                    "error_type": "validation"
                }
            )
            raise

        except Exception as e:
            # Log unexpected errors
            self.logger.error(
                "Failed to process order",
                extra={
                    "order_id": order_id,
                    "error": str(e),
                    "error_type": type(e).__name__
                },
                exc_info=True  # Include stack trace
            )
            raise
```

### Log Output

```json
{
  "timestamp": "2025-12-07T10:30:15.123Z",
  "level": "INFO",
  "message": "Processing order",
  "service": "observable-agent",
  "version": "1.0.0",
  "order_id": "ord-12345",
  "amount": 99.99,
  "caller": "spiffe://example.org/client",
  "trace_id": "abc123def456"
}
```

### Logging Best Practices

1. **Use structured fields** - Don't concatenate strings
   ```python
   # Good
   self.logger.info("Order processed", extra={"order_id": order_id})

   # Bad
   self.logger.info(f"Order {order_id} processed")
   ```

2. **Include trace ID** - Correlate logs with traces
   ```python
   extra={"trace_id": context.trace_id}
   ```

3. **Log at appropriate levels**
   - `DEBUG` - Detailed diagnostic info
   - `INFO` - Normal operation events
   - `WARNING` - Expected errors, retries
   - `ERROR` - Unexpected errors, failures

4. **Include caller identity** - For audit trails
   ```python
   extra={"caller": context.caller_spiffe_id}
   ```

## Step 5: Set Up Grafana Dashboard

Visualize your metrics with Grafana.

### Run Grafana

```bash
docker run -d \
  --name grafana \
  -p 3000:3000 \
  grafana/grafana:latest
```

Access Grafana:
1. Open http://localhost:3000
2. Login: admin / admin
3. Add data source: Prometheus (http://host.docker.internal:9091)

### Sample Dashboard JSON

Create a dashboard with these panels:

**Request Rate Panel:**
```promql
rate(agentweave_requests_total[5m])
```

**Error Rate Panel:**
```promql
rate(agentweave_requests_total{status="error"}[5m])
/
rate(agentweave_requests_total[5m])
```

**P95 Latency Panel:**
```promql
histogram_quantile(0.95,
  rate(agentweave_request_duration_seconds_bucket[5m])
)
```

**Requests by Capability Panel:**
```promql
sum by (capability) (
  rate(agentweave_requests_total[5m])
)
```

**Active Requests Panel:**
```promql
agentweave_requests_in_flight
```

### Import Pre-built Dashboard

AgentWeave provides a pre-built Grafana dashboard:

```bash
# Download dashboard
curl -O https://github.com/aj-geddes/agentweave/raw/main/observability/grafana-dashboard.json

# Import in Grafana UI:
# Dashboards > Import > Upload JSON file
```

## Step 6: Complete Observability Stack with Docker Compose

Run everything together with Docker Compose.

### docker-compose.yml

```yaml
version: '3.8'

services:
  # Prometheus - Metrics collection
  prometheus:
    image: prom/prometheus:latest
    container_name: prometheus
    ports:
      - "9091:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    networks:
      - observability

  # Grafana - Visualization
  grafana:
    image: grafana/grafana:latest
    container_name: grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana-datasources.yml:/etc/grafana/provisioning/datasources/datasources.yml
      - ./grafana-dashboard.json:/etc/grafana/provisioning/dashboards/agentweave.json
    networks:
      - observability
    depends_on:
      - prometheus

  # Jaeger - Distributed tracing
  jaeger:
    image: jaegertracing/all-in-one:latest
    container_name: jaeger
    ports:
      - "16686:16686"  # Jaeger UI
      - "4317:4317"    # OTLP gRPC
      - "4318:4318"    # OTLP HTTP
    environment:
      - COLLECTOR_OTLP_ENABLED=true
    networks:
      - observability

  # Loki - Log aggregation (optional)
  loki:
    image: grafana/loki:latest
    container_name: loki
    ports:
      - "3100:3100"
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - observability

  # Promtail - Log shipper (optional)
  promtail:
    image: grafana/promtail:latest
    container_name: promtail
    volumes:
      - /var/log:/var/log
      - ./promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml
    networks:
      - observability
    depends_on:
      - loki

networks:
  observability:
    driver: bridge

volumes:
  prometheus-data:
  grafana-data:
```

### Start the Stack

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

Access the services:
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9091
- Jaeger: http://localhost:16686

## Step 7: Audit Logging

AgentWeave automatically logs authorization decisions for audit trails.

### Audit Log Format

```json
{
  "timestamp": "2025-12-07T10:30:15.123Z",
  "level": "INFO",
  "message": "Authorization decision",
  "event_type": "authz",
  "caller_spiffe_id": "spiffe://example.org/client",
  "agent_spiffe_id": "spiffe://example.org/agent",
  "capability": "process_data",
  "decision": "allow",
  "policy": "agentweave.authz",
  "duration_ms": 2.3,
  "trace_id": "abc123"
}
```

### Query Audit Logs

If using Loki, query audit logs:

```logql
{service="observable-agent"}
  | json
  | event_type="authz"
  | decision="deny"
```

Or with jq from files:

```bash
cat agent.log | jq 'select(.event_type == "authz" and .decision == "deny")'
```

## Summary

You've set up comprehensive observability! You've learned:

- Configuring Prometheus metrics
- Setting up distributed tracing with Jaeger
- Structured logging best practices
- Creating Grafana dashboards
- Running a complete observability stack
- Implementing audit logging

## Exercises

1. **Create custom metrics** in your agent using `self.metrics.counter()`
2. **Add custom trace spans** to track specific operations
3. **Build a Grafana alert** for high error rates
4. **Set up log aggregation** with Loki
5. **Create a dashboard** for business metrics (documents processed, etc.)

## What's Next?

Continue learning:

- **[Deploying to Kubernetes](/tutorials/kubernetes-deployment/)** - Production deployment
- **[Tutorial: Observability](/tutorials/observability/)** - Advanced monitoring patterns
- **[Security: Audit Logging](/security/audit-logging/)** - Compliance and audit trails
- **[How-To: Performance](/guides/performance/)** - Debug performance issues

## Troubleshooting

### Metrics not appearing in Prometheus
- Check agent metrics endpoint: `curl localhost:9090/metrics`
- Verify Prometheus scrape config
- Check Prometheus targets page: http://localhost:9091/targets
- Check firewall rules

### No traces in Jaeger
- Verify tracing.enabled is true in config
- Check OTLP endpoint is correct
- Ensure Jaeger collector is running
- Check sampling_rate (should be > 0)

### High cardinality metrics
- Avoid using unbounded labels (user IDs, request IDs)
- Use histograms for latency, not separate metrics per request
- Review label usage

See [Troubleshooting Guide](/troubleshooting/) for more help.
