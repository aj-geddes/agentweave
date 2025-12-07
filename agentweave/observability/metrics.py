"""
Prometheus metrics collection for AgentWeave SDK.

Provides comprehensive metrics for monitoring agent behavior, performance,
and security decisions.
"""

from typing import Optional
import time
from contextlib import contextmanager

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    CollectorRegistry,
    start_http_server,
    REGISTRY,
)


class MetricsCollector:
    """
    Collects and exposes Prometheus metrics for secure agents.

    Metrics include:
    - Request counters (total, by status, by capability)
    - Authorization decision counters
    - Error counters by type
    - Request/auth duration histograms
    - Active connections gauge
    - Circuit breaker state gauge

    All metrics include relevant labels for filtering and aggregation.
    """

    def __init__(
        self,
        agent_name: str,
        registry: Optional[CollectorRegistry] = None,
        enabled: bool = True,
    ):
        """
        Initialize metrics collector.

        Args:
            agent_name: Name of the agent (added as label to all metrics)
            registry: Prometheus registry (defaults to global REGISTRY)
            enabled: Whether metrics collection is enabled
        """
        self.agent_name = agent_name
        self.registry = registry or REGISTRY
        self.enabled = enabled

        if not self.enabled:
            return

        # Counters
        self.requests_total = Counter(
            "agentweave_requests_total",
            "Total number of requests received",
            ["agent_name", "capability", "status"],
            registry=self.registry,
        )

        self.auth_decisions_total = Counter(
            "agentweave_auth_decisions_total",
            "Total number of authorization decisions",
            ["agent_name", "peer_id", "capability", "decision"],
            registry=self.registry,
        )

        self.errors_total = Counter(
            "agentweave_errors_total",
            "Total number of errors",
            ["agent_name", "error_type", "capability"],
            registry=self.registry,
        )

        # Histograms
        self.request_duration_seconds = Histogram(
            "agentweave_request_duration_seconds",
            "Request processing duration in seconds",
            ["agent_name", "capability", "status"],
            buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
            registry=self.registry,
        )

        self.auth_check_duration_seconds = Histogram(
            "agentweave_auth_check_duration_seconds",
            "Authorization check duration in seconds",
            ["agent_name", "peer_id", "capability"],
            buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0),
            registry=self.registry,
        )

        # Gauges
        self.active_connections = Gauge(
            "agentweave_active_connections",
            "Number of active connections",
            ["agent_name", "peer_id"],
            registry=self.registry,
        )

        self.circuit_breaker_state = Gauge(
            "agentweave_circuit_breaker_state",
            "Circuit breaker state (0=closed, 1=open, 2=half-open)",
            ["agent_name", "peer_id"],
            registry=self.registry,
        )

    def record_request(
        self,
        capability: str,
        status: str,
    ) -> None:
        """
        Record a completed request.

        Args:
            capability: Capability that was invoked
            status: Status of the request (success, error, denied)
        """
        if not self.enabled:
            return

        self.requests_total.labels(
            agent_name=self.agent_name,
            capability=capability,
            status=status,
        ).inc()

    def record_auth_decision(
        self,
        peer_id: str,
        capability: str,
        decision: str,
    ) -> None:
        """
        Record an authorization decision.

        Args:
            peer_id: SPIFFE ID of the peer
            capability: Capability being checked
            decision: Decision result (allow, deny)
        """
        if not self.enabled:
            return

        self.auth_decisions_total.labels(
            agent_name=self.agent_name,
            peer_id=peer_id,
            capability=capability,
            decision=decision,
        ).inc()

    def record_error(
        self,
        error_type: str,
        capability: str = "unknown",
    ) -> None:
        """
        Record an error.

        Args:
            error_type: Type of error (auth_error, transport_error, etc.)
            capability: Capability where error occurred
        """
        if not self.enabled:
            return

        self.errors_total.labels(
            agent_name=self.agent_name,
            error_type=error_type,
            capability=capability,
        ).inc()

    @contextmanager
    def time_request(self, capability: str, status: str):
        """
        Context manager to time request duration.

        Args:
            capability: Capability being invoked
            status: Expected status (updated if exception occurs)

        Example:
            with metrics.time_request("search", "success"):
                await process_search()
        """
        if not self.enabled:
            yield
            return

        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.request_duration_seconds.labels(
                agent_name=self.agent_name,
                capability=capability,
                status=status,
            ).observe(duration)

    @contextmanager
    def time_auth_check(self, peer_id: str, capability: str):
        """
        Context manager to time authorization check duration.

        Args:
            peer_id: SPIFFE ID of the peer
            capability: Capability being checked

        Example:
            with metrics.time_auth_check(peer_id, "search"):
                decision = await check_authorization()
        """
        if not self.enabled:
            yield
            return

        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.auth_check_duration_seconds.labels(
                agent_name=self.agent_name,
                peer_id=peer_id,
                capability=capability,
            ).observe(duration)

    def set_active_connections(self, peer_id: str, count: int) -> None:
        """
        Set the number of active connections to a peer.

        Args:
            peer_id: SPIFFE ID of the peer
            count: Number of active connections
        """
        if not self.enabled:
            return

        self.active_connections.labels(
            agent_name=self.agent_name,
            peer_id=peer_id,
        ).set(count)

    def increment_active_connections(self, peer_id: str) -> None:
        """
        Increment active connections counter.

        Args:
            peer_id: SPIFFE ID of the peer
        """
        if not self.enabled:
            return

        self.active_connections.labels(
            agent_name=self.agent_name,
            peer_id=peer_id,
        ).inc()

    def decrement_active_connections(self, peer_id: str) -> None:
        """
        Decrement active connections counter.

        Args:
            peer_id: SPIFFE ID of the peer
        """
        if not self.enabled:
            return

        self.active_connections.labels(
            agent_name=self.agent_name,
            peer_id=peer_id,
        ).dec()

    def set_circuit_breaker_state(
        self,
        peer_id: str,
        state: str,
    ) -> None:
        """
        Set circuit breaker state for a peer.

        Args:
            peer_id: SPIFFE ID of the peer
            state: State of circuit breaker (closed, open, half_open)
        """
        if not self.enabled:
            return

        state_map = {
            "closed": 0,
            "open": 1,
            "half_open": 2,
        }

        self.circuit_breaker_state.labels(
            agent_name=self.agent_name,
            peer_id=peer_id,
        ).set(state_map.get(state, 0))

    def start_exposition_endpoint(
        self,
        port: int = 9090,
        addr: str = "0.0.0.0",
    ) -> None:
        """
        Start Prometheus metrics exposition HTTP server.

        Args:
            port: Port to listen on (default: 9090)
            addr: Address to bind to (default: 0.0.0.0)
        """
        if not self.enabled:
            return

        start_http_server(port=port, addr=addr, registry=self.registry)
