---
layout: page
title: Performance Tuning
description: Optimize AgentWeave agents for production performance
parent: How-To Guides
nav_order: 5
---

# Performance Tuning

This guide shows you how to optimize AgentWeave agents for high performance, including connection pooling, caching, async best practices, and monitoring.

## Table of Contents
{: .no_toc .text-delta }

1. TOC
{:toc}

---

## Connection Pool Configuration

Connection pooling reuses TCP connections to reduce overhead and improve throughput.

### Default Configuration

```yaml
# config.yaml
transport:
  connection_pool:
    max_connections: 100           # Maximum connections per destination
    idle_timeout_seconds: 60       # Close idle connections after 60s
    max_keepalive_seconds: 300     # Maximum connection lifetime
    connect_timeout_seconds: 10    # Connection establishment timeout
```

### Sizing Connection Pools

**Rule of thumb:** `max_connections = (expected_concurrent_requests × average_request_time) + buffer`

**Examples:**

**Low-traffic agent (< 10 req/s):**
```yaml
transport:
  connection_pool:
    max_connections: 10
    idle_timeout_seconds: 30
```

**Medium-traffic agent (10-100 req/s):**
```yaml
transport:
  connection_pool:
    max_connections: 50
    idle_timeout_seconds: 60
```

**High-traffic agent (> 100 req/s):**
```yaml
transport:
  connection_pool:
    max_connections: 200
    idle_timeout_seconds: 120
    max_keepalive_seconds: 600
```

### Monitoring Connection Pool Health

```python
from agentweave import SecureAgent
from agentweave.observability.metrics import get_metrics_registry

class MonitoredAgent(SecureAgent):
    async def start(self):
        await super().start()

        # Start connection pool monitoring
        asyncio.create_task(self._monitor_connection_pool())

    async def _monitor_connection_pool(self):
        """Monitor connection pool metrics."""
        metrics = get_metrics_registry()

        while self.is_running:
            # Get pool stats from transport layer
            pool_stats = await self.transport.get_pool_stats()

            metrics.gauge("connection_pool.active", pool_stats.active)
            metrics.gauge("connection_pool.idle", pool_stats.idle)
            metrics.gauge("connection_pool.total", pool_stats.total)
            metrics.gauge("connection_pool.utilization",
                         pool_stats.active / pool_stats.max_connections)

            # Alert if pool is exhausted
            if pool_stats.active >= pool_stats.max_connections * 0.9:
                self.logger.warning(
                    "Connection pool near capacity",
                    extra={
                        "active": pool_stats.active,
                        "max": pool_stats.max_connections,
                        "utilization": pool_stats.active / pool_stats.max_connections
                    }
                )

            await asyncio.sleep(10)  # Check every 10 seconds
```

---

## Cache Tuning (OPA Decision Cache)

Caching OPA authorization decisions can significantly improve performance.

### Enable Decision Caching

```yaml
# config.yaml
authorization:
  provider: opa
  opa_endpoint: http://localhost:8181
  policy_path: agentweave/authz

  # Decision cache configuration
  cache:
    enabled: true
    ttl_seconds: 300              # Cache for 5 minutes
    max_size: 10000               # Max 10k cached decisions
    eviction_policy: lru          # Least recently used
```

### Cache Hit Ratio Monitoring

```python
from agentweave.authz import OPAAuthzProvider

class CachedAuthzAgent(SecureAgent):
    def __init__(self):
        super().__init__()
        self.cache_hits = 0
        self.cache_misses = 0

    async def _check_authorization_with_metrics(
        self,
        caller_id: str,
        action: str
    ) -> bool:
        """Check authorization and track cache performance."""
        # Check if decision is cached
        cache_key = f"{caller_id}:{action}"
        cached_decision = await self.authz_provider.cache.get(cache_key)

        if cached_decision is not None:
            self.cache_hits += 1
            return cached_decision.allowed
        else:
            self.cache_misses += 1

        # Make OPA decision
        decision = await self.authz_provider.check_inbound(caller_id, action)

        # Log cache performance
        total = self.cache_hits + self.cache_misses
        hit_ratio = self.cache_hits / total if total > 0 else 0

        if total % 100 == 0:  # Log every 100 requests
            self.logger.info(
                f"Authorization cache hit ratio: {hit_ratio:.2%}",
                extra={
                    "hits": self.cache_hits,
                    "misses": self.cache_misses,
                    "ratio": hit_ratio
                }
            )

        return decision.allowed
```

### Cache Invalidation Strategy

```python
from agentweave.authz.cache import DecisionCache

class SmartCacheAgent(SecureAgent):
    def __init__(self):
        super().__init__()
        self.decision_cache = DecisionCache(
            ttl_seconds=300,
            max_size=10000
        )

    async def invalidate_cache_for_agent(self, spiffe_id: str):
        """Invalidate all cached decisions involving an agent."""
        # When agent permissions change, clear related cache entries
        await self.decision_cache.invalidate_pattern(f"*{spiffe_id}*")

        self.logger.info(
            f"Invalidated cache for {spiffe_id}",
            extra={"spiffe_id": spiffe_id}
        )

    async def on_policy_update(self, policy_version: str):
        """Clear all cached decisions when policy updates."""
        await self.decision_cache.clear()

        self.logger.info(
            "Cleared authorization cache due to policy update",
            extra={"policy_version": policy_version}
        )
```

---

## Async Best Practices

Maximize concurrency and avoid blocking the event loop.

### Use asyncio.gather for Parallel Calls

```python
import asyncio
from agentweave import SecureAgent, capability

class ParallelAgent(SecureAgent):
    @capability("aggregate")
    async def aggregate(self, query: dict) -> dict:
        # BAD: Sequential calls (slow)
        # search_results = await self.call_agent("search", "search", query)
        # index_results = await self.call_agent("indexer", "query", query)
        # storage_results = await self.call_agent("storage", "retrieve", query)

        # GOOD: Parallel calls (fast)
        search_task = self.call_agent(
            "spiffe://yourdomain.com/agent/search",
            "search",
            query
        )
        index_task = self.call_agent(
            "spiffe://yourdomain.com/agent/indexer",
            "query",
            query
        )
        storage_task = self.call_agent(
            "spiffe://yourdomain.com/agent/storage",
            "retrieve",
            query
        )

        # Wait for all to complete
        search_results, index_results, storage_results = await asyncio.gather(
            search_task,
            index_task,
            storage_task,
            return_exceptions=True  # Don't fail if one fails
        )

        return {
            "search": search_results if not isinstance(search_results, Exception) else None,
            "index": index_results if not isinstance(index_results, Exception) else None,
            "storage": storage_results if not isinstance(storage_results, Exception) else None,
        }
```

### Avoid Blocking I/O

```python
import asyncio
import aiofiles
from agentweave import SecureAgent, capability

class NonBlockingAgent(SecureAgent):
    @capability("process_file")
    async def process_file(self, filepath: str) -> dict:
        # BAD: Blocking I/O
        # with open(filepath, 'r') as f:
        #     data = f.read()  # Blocks event loop!

        # GOOD: Async I/O
        async with aiofiles.open(filepath, 'r') as f:
            data = await f.read()  # Non-blocking

        # Process data
        result = await self._process_data(data)
        return result

    async def _process_data(self, data: str) -> dict:
        # If you must use blocking code, run in executor
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,  # Uses default ThreadPoolExecutor
            self._blocking_computation,
            data
        )
        return result

    def _blocking_computation(self, data: str) -> dict:
        """CPU-intensive computation that would block event loop."""
        # Heavy computation here
        return {"processed": len(data)}
```

### Use Semaphores for Concurrency Control

```python
import asyncio
from agentweave import SecureAgent

class ThrottledAgent(SecureAgent):
    def __init__(self):
        super().__init__()
        # Limit to 10 concurrent outbound calls
        self.call_semaphore = asyncio.Semaphore(10)

    async def call_with_throttle(
        self,
        callee_id: str,
        action: str,
        payload: dict
    ) -> dict:
        """Make call with concurrency limiting."""
        async with self.call_semaphore:
            return await self.call_agent(callee_id, action, payload)

    @capability("batch_process")
    async def batch_process(self, items: list) -> list:
        """Process many items with concurrency limit."""
        tasks = [
            self.call_with_throttle(
                "spiffe://yourdomain.com/agent/processor",
                "process",
                {"item": item}
            )
            for item in items
        ]

        # Process all, but only 10 concurrent at a time
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
```

---

## Profiling Agents

Identify performance bottlenecks in your agents.

### Using cProfile

```python
import cProfile
import pstats
from agentweave import SecureAgent

class ProfiledAgent(SecureAgent):
    @capability("profile_test")
    async def profile_test(self, data: dict) -> dict:
        """Capability that can be profiled."""
        profiler = cProfile.Profile()
        profiler.enable()

        try:
            result = await self._do_work(data)
            return result
        finally:
            profiler.disable()

            # Print top 20 time-consuming functions
            stats = pstats.Stats(profiler)
            stats.sort_stats('cumulative')
            stats.print_stats(20)
```

### Using py-spy

```bash
# Install py-spy
pip install py-spy

# Profile running agent
py-spy top --pid $(pgrep -f "python.*agent.py")

# Generate flamegraph
py-spy record --pid $(pgrep -f "python.*agent.py") --output profile.svg

# Profile for 60 seconds
py-spy record --pid $(pgrep -f "python.*agent.py") --duration 60 --output profile.svg
```

### Custom Performance Metrics

```python
import time
from functools import wraps
from agentweave import SecureAgent, capability
from agentweave.observability.metrics import get_metrics_registry

def measure_time(metric_name: str):
    """Decorator to measure execution time."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start
                metrics = get_metrics_registry()
                metrics.histogram(metric_name, duration)
        return wrapper
    return decorator


class MetricsAgent(SecureAgent):
    @capability("search")
    @measure_time("capability.search.duration")
    async def search(self, query: str) -> dict:
        """Search capability with automatic timing."""
        results = await self._perform_search(query)
        return {"results": results}

    @measure_time("search.database.query")
    async def _perform_search(self, query: str) -> list:
        """Database search (timed separately)."""
        # Database query here
        return []
```

---

## Metrics to Monitor

Key performance indicators for AgentWeave agents.

### Request Metrics

```python
from agentweave.observability.metrics import get_metrics_registry

class MonitoredAgent(SecureAgent):
    def __init__(self):
        super().__init__()
        self.metrics = get_metrics_registry()

    @capability("process")
    async def process(self, data: dict) -> dict:
        # Track request count
        self.metrics.counter("requests.total").inc()
        self.metrics.counter("requests.by_capability", {"capability": "process"}).inc()

        start_time = time.perf_counter()

        try:
            result = await self._do_processing(data)

            # Track success
            self.metrics.counter("requests.success").inc()

            # Track duration
            duration = time.perf_counter() - start_time
            self.metrics.histogram("request.duration", duration, {"capability": "process"})

            # Track payload size
            self.metrics.histogram("request.payload_size", len(str(data)))

            return result

        except Exception as e:
            # Track errors
            self.metrics.counter("requests.error", {"error_type": type(e).__name__}).inc()
            raise
```

### System Metrics

```python
import psutil
import asyncio

class SystemMetricsAgent(SecureAgent):
    async def start(self):
        await super().start()
        asyncio.create_task(self._collect_system_metrics())

    async def _collect_system_metrics(self):
        """Collect system-level metrics."""
        metrics = get_metrics_registry()

        while self.is_running:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.gauge("system.cpu.percent", cpu_percent)

            # Memory usage
            memory = psutil.virtual_memory()
            metrics.gauge("system.memory.percent", memory.percent)
            metrics.gauge("system.memory.available_mb", memory.available / 1024 / 1024)

            # Disk usage
            disk = psutil.disk_usage('/')
            metrics.gauge("system.disk.percent", disk.percent)

            # Network I/O
            net_io = psutil.net_io_counters()
            metrics.counter("system.network.bytes_sent", net_io.bytes_sent)
            metrics.counter("system.network.bytes_recv", net_io.bytes_recv)

            await asyncio.sleep(30)  # Collect every 30 seconds
```

### Authorization Metrics

```python
class AuthzMetricsAgent(SecureAgent):
    async def _check_authorization_with_metrics(
        self,
        caller_id: str,
        action: str
    ):
        """Check authorization and emit metrics."""
        metrics = get_metrics_registry()

        start = time.perf_counter()

        try:
            decision = await self.authz_provider.check_inbound(caller_id, action)

            # Track decision time
            duration = time.perf_counter() - start
            metrics.histogram("authz.check.duration", duration)

            # Track decision outcome
            if decision.allowed:
                metrics.counter("authz.decisions.allowed").inc()
            else:
                metrics.counter("authz.decisions.denied").inc()

            # Track by action
            metrics.counter(
                "authz.decisions.by_action",
                {"action": action, "result": "allowed" if decision.allowed else "denied"}
            ).inc()

            return decision

        except Exception as e:
            metrics.counter("authz.check.errors", {"error_type": type(e).__name__}).inc()
            raise
```

---

## Common Bottlenecks

### 1. Sequential Agent Calls

**Problem:** Calling agents one after another

```python
# SLOW: Sequential (total time = sum of all calls)
result1 = await agent.call_agent("agent1", "action1", {})
result2 = await agent.call_agent("agent2", "action2", {})
result3 = await agent.call_agent("agent3", "action3", {})
# Total: 300ms + 200ms + 150ms = 650ms
```

**Solution:** Parallel calls with asyncio.gather

```python
# FAST: Parallel (total time = max of all calls)
results = await asyncio.gather(
    agent.call_agent("agent1", "action1", {}),
    agent.call_agent("agent2", "action2", {}),
    agent.call_agent("agent3", "action3", {}),
)
# Total: max(300ms, 200ms, 150ms) = 300ms
```

### 2. OPA Policy Evaluation Overhead

**Problem:** Every request hits OPA

**Solution:** Enable decision caching (see Cache Tuning section)

### 3. Connection Pool Exhaustion

**Problem:** Too many concurrent requests, not enough connections

**Symptoms:**
- Requests waiting for connections
- High request latency
- Timeout errors

**Solution:** Increase connection pool size or add concurrency limits

```yaml
transport:
  connection_pool:
    max_connections: 200  # Increase from default 100
```

### 4. Blocking I/O in Event Loop

**Problem:** Synchronous I/O blocks all requests

**Solution:** Use async I/O libraries (aiofiles, aiomysql, aioredis, etc.)

### 5. Large Payload Serialization

**Problem:** JSON serialization/deserialization is slow for large payloads

**Solution:** Use streaming or chunked transfer

```python
class StreamingAgent(SecureAgent):
    @capability("process_large_data")
    async def process_large_data(self, data_url: str) -> dict:
        # Instead of loading entire payload
        # BAD: data = await download_all(data_url)

        # Stream and process in chunks
        async for chunk in self._stream_download(data_url):
            await self._process_chunk(chunk)

        return {"status": "completed"}
```

---

## Scaling Strategies

### Horizontal Scaling

Deploy multiple instances of your agent behind a load balancer.

```yaml
# kubernetes/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: search-agent
spec:
  replicas: 5  # Run 5 instances
  selector:
    matchLabels:
      app: search-agent
  template:
    metadata:
      labels:
        app: search-agent
    spec:
      containers:
      - name: search-agent
        image: myorg/search-agent:v1
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
```

### Vertical Scaling

Increase resources for a single instance.

```yaml
# Increase CPU/memory limits
resources:
  requests:
    cpu: 2000m    # 2 cores
    memory: 4Gi   # 4 GB
  limits:
    cpu: 4000m    # 4 cores
    memory: 8Gi   # 8 GB
```

### Auto-scaling

Automatically scale based on metrics.

```yaml
# kubernetes/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: search-agent-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: search-agent
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Pods
    pods:
      metric:
        name: requests_per_second
      target:
        type: AverageValue
        averageValue: "100"
```

---

## Performance Testing

Load test your agents before production.

### Using Locust

```python
# locustfile.py
from locust import HttpUser, task, between
import json

class AgentUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def search(self):
        """Simulate search request."""
        payload = {
            "action": "search",
            "query": "test query",
            "limit": 10
        }
        self.client.post(
            "/task",
            json=payload,
            headers={"Content-Type": "application/json"}
        )

    @task(2)  # 2x weight
    def process(self):
        """Simulate process request."""
        payload = {
            "action": "process",
            "data": {"key": "value"}
        }
        self.client.post("/task", json=payload)
```

Run load test:

```bash
# Install locust
pip install locust

# Run test
locust -f locustfile.py --host https://agent.yourdomain.com --users 100 --spawn-rate 10

# Results show:
# - Requests per second
# - Response times (p50, p95, p99)
# - Failure rate
```

---

## Related Guides

- [Production Checklist](production-checklist.md) - Performance items for production
- [Error Handling](error-handling.md) - Configure retries and circuit breakers
- [Testing Your Agents](testing.md) - Performance testing

---

## External Resources

- [Python asyncio Performance Tips](https://docs.python.org/3/library/asyncio-dev.html)
- [Profiling Python Code](https://docs.python.org/3/library/profile.html)
- [py-spy: Sampling Profiler](https://github.com/benfred/py-spy)
- [Locust Load Testing](https://locust.io/)
- [Kubernetes HPA](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
