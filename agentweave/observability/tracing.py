"""
OpenTelemetry distributed tracing for AgentWeave SDK.

Provides automatic span creation for all agent operations with context
propagation across agent-to-agent calls.
"""

from typing import Optional, Dict, Any
from contextlib import contextmanager
import logging

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.trace import Status, StatusCode, SpanKind
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

logger = logging.getLogger(__name__)


class TracingProvider:
    """
    Manages OpenTelemetry tracing for secure agents.

    Automatically creates spans for:
    - Incoming requests
    - Outgoing A2A calls
    - Authorization checks
    - Identity operations

    Propagates trace context across agent boundaries using W3C Trace Context.
    """

    def __init__(
        self,
        agent_name: str,
        service_version: str = "1.0.0",
        otlp_endpoint: Optional[str] = None,
        enabled: bool = True,
    ):
        """
        Initialize tracing provider.

        Args:
            agent_name: Name of the agent (added to trace metadata)
            service_version: Version of the service
            otlp_endpoint: OTLP collector endpoint (e.g., "http://collector:4317")
            enabled: Whether tracing is enabled
        """
        self.agent_name = agent_name
        self.service_version = service_version
        self.otlp_endpoint = otlp_endpoint
        self.enabled = enabled
        self.tracer: Optional[trace.Tracer] = None
        self.propagator = TraceContextTextMapPropagator()

        if self.enabled:
            self._initialize_tracing()

    def _initialize_tracing(self) -> None:
        """Initialize OpenTelemetry tracing with OTLP exporter."""
        # Create resource with service metadata
        resource = Resource.create(
            {
                "service.name": f"agentweave-{self.agent_name}",
                "service.version": self.service_version,
                "service.namespace": "agentweaves",
            }
        )

        # Create tracer provider
        provider = TracerProvider(resource=resource)

        # Configure OTLP exporter if endpoint provided
        if self.otlp_endpoint:
            otlp_exporter = OTLPSpanExporter(endpoint=self.otlp_endpoint)
            span_processor = BatchSpanProcessor(otlp_exporter)
            provider.add_span_processor(span_processor)

        # Set as global tracer provider
        trace.set_tracer_provider(provider)

        # Get tracer instance
        self.tracer = trace.get_tracer(
            instrumenting_module_name=__name__,
            instrumenting_library_version=self.service_version,
        )

        logger.info(
            f"Tracing initialized for agent '{self.agent_name}' "
            f"(endpoint: {self.otlp_endpoint or 'none'})"
        )

    @contextmanager
    def trace_incoming_request(
        self,
        capability: str,
        caller_id: str,
        context: Optional[Dict[str, str]] = None,
    ):
        """
        Create a span for an incoming request.

        Args:
            capability: Capability being invoked
            caller_id: SPIFFE ID of the caller
            context: Optional trace context from caller (for propagation)

        Yields:
            Span object for adding additional attributes

        Example:
            with tracer.trace_incoming_request("search", caller_id, headers):
                result = await handle_search()
        """
        if not self.enabled or not self.tracer:
            yield None
            return

        # Extract parent context if provided
        parent_context = None
        if context:
            parent_context = self.propagator.extract(context)

        with self.tracer.start_as_current_span(
            name=f"handle_{capability}",
            kind=SpanKind.SERVER,
            context=parent_context,
        ) as span:
            # Add standard attributes
            span.set_attribute("agent.name", self.agent_name)
            span.set_attribute("agent.capability", capability)
            span.set_attribute("agent.caller.spiffe_id", caller_id)
            span.set_attribute("span.type", "incoming_request")

            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    @contextmanager
    def trace_outgoing_call(
        self,
        target_agent: str,
        capability: str,
    ):
        """
        Create a span for an outgoing A2A call.

        Args:
            target_agent: SPIFFE ID of target agent
            capability: Capability being invoked

        Yields:
            Tuple of (span, carrier dict with trace context for propagation)

        Example:
            with tracer.trace_outgoing_call(target_id, "search") as (span, carrier):
                response = await client.call(target_id, capability, headers=carrier)
        """
        if not self.enabled or not self.tracer:
            yield None, {}
            return

        with self.tracer.start_as_current_span(
            name=f"call_{capability}",
            kind=SpanKind.CLIENT,
        ) as span:
            # Add standard attributes
            span.set_attribute("agent.name", self.agent_name)
            span.set_attribute("agent.target.spiffe_id", target_agent)
            span.set_attribute("agent.capability", capability)
            span.set_attribute("span.type", "outgoing_call")

            # Inject trace context for propagation
            carrier: Dict[str, str] = {}
            self.propagator.inject(carrier)

            try:
                yield span, carrier
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    @contextmanager
    def trace_auth_check(
        self,
        peer_id: str,
        capability: str,
        direction: str = "inbound",
    ):
        """
        Create a span for an authorization check.

        Args:
            peer_id: SPIFFE ID of the peer
            capability: Capability being checked
            direction: Direction of check (inbound or outbound)

        Yields:
            Span object for adding decision result

        Example:
            with tracer.trace_auth_check(peer_id, "search", "inbound") as span:
                decision = await opa.check(peer_id, capability)
                span.set_attribute("authz.decision", "allow" if decision else "deny")
        """
        if not self.enabled or not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(
            name=f"authz_check_{direction}",
            kind=SpanKind.INTERNAL,
        ) as span:
            # Add standard attributes
            span.set_attribute("agent.name", self.agent_name)
            span.set_attribute("agent.peer.spiffe_id", peer_id)
            span.set_attribute("agent.capability", capability)
            span.set_attribute("authz.direction", direction)
            span.set_attribute("span.type", "authorization_check")

            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    @contextmanager
    def trace_identity_operation(
        self,
        operation: str,
    ):
        """
        Create a span for an identity operation.

        Args:
            operation: Type of operation (fetch_svid, verify_peer, etc.)

        Yields:
            Span object for adding additional attributes

        Example:
            with tracer.trace_identity_operation("fetch_svid") as span:
                svid = await identity_provider.get_svid()
                span.set_attribute("svid.spiffe_id", svid.spiffe_id)
        """
        if not self.enabled or not self.tracer:
            yield None
            return

        with self.tracer.start_as_current_span(
            name=f"identity_{operation}",
            kind=SpanKind.INTERNAL,
        ) as span:
            # Add standard attributes
            span.set_attribute("agent.name", self.agent_name)
            span.set_attribute("identity.operation", operation)
            span.set_attribute("span.type", "identity_operation")

            try:
                yield span
                span.set_status(Status(StatusCode.OK))
            except Exception as e:
                span.set_status(Status(StatusCode.ERROR, str(e)))
                span.record_exception(e)
                raise

    def get_current_trace_id(self) -> Optional[str]:
        """
        Get the current trace ID for correlation with logs.

        Returns:
            Trace ID in hexadecimal format, or None if no active span
        """
        if not self.enabled:
            return None

        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().trace_id, "032x")
        return None

    def get_current_span_id(self) -> Optional[str]:
        """
        Get the current span ID for correlation with logs.

        Returns:
            Span ID in hexadecimal format, or None if no active span
        """
        if not self.enabled:
            return None

        span = trace.get_current_span()
        if span and span.get_span_context().is_valid:
            return format(span.get_span_context().span_id, "016x")
        return None

    def inject_context(self, carrier: Dict[str, str]) -> None:
        """
        Inject current trace context into carrier for propagation.

        Args:
            carrier: Dictionary to inject context into (e.g., HTTP headers)
        """
        if not self.enabled:
            return

        self.propagator.inject(carrier)

    def extract_context(self, carrier: Dict[str, str]) -> Any:
        """
        Extract trace context from carrier.

        Args:
            carrier: Dictionary containing trace context (e.g., HTTP headers)

        Returns:
            Extracted context for use in span creation
        """
        if not self.enabled:
            return None

        return self.propagator.extract(carrier)
