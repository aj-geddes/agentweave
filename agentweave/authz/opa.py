"""
OPA (Open Policy Agent) authorization provider implementation.
"""

import asyncio
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Optional
from collections import OrderedDict

import httpx

from agentweave.authz.base import AuthorizationProvider, AuthzDecision


logger = logging.getLogger(__name__)


class CircuitBreaker:
    """
    Circuit breaker for OPA failures.

    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service has recovered
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        success_threshold: int = 2
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold

        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = "CLOSED"
        self._lock = asyncio.Lock()

    async def call(self, func, *args, **kwargs):
        """Execute a function with circuit breaker protection."""
        async with self._lock:
            if self.state == "OPEN":
                if datetime.utcnow() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                    logger.info("Circuit breaker entering HALF_OPEN state")
                    self.state = "HALF_OPEN"
                    self.success_count = 0
                else:
                    raise CircuitBreakerError("Circuit breaker is OPEN")

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except Exception as e:
            await self._on_failure()
            raise e

    async def _on_success(self):
        async with self._lock:
            self.failure_count = 0
            if self.state == "HALF_OPEN":
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    logger.info("Circuit breaker entering CLOSED state")
                    self.state = "CLOSED"
                    self.success_count = 0

    async def _on_failure(self):
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = datetime.utcnow()

            if self.state == "HALF_OPEN":
                logger.warning("Circuit breaker entering OPEN state from HALF_OPEN")
                self.state = "OPEN"
                self.success_count = 0
            elif self.failure_count >= self.failure_threshold:
                logger.warning(f"Circuit breaker entering OPEN state after {self.failure_count} failures")
                self.state = "OPEN"


class DecisionCache:
    """
    LRU cache for authorization decisions with TTL.
    """

    def __init__(self, max_size: int = 1000, ttl_seconds: float = 60.0):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: OrderedDict = OrderedDict()
        self._lock = asyncio.Lock()

    def _make_key(self, caller_id: str, resource: str, action: str, context: Optional[dict]) -> str:
        """Create cache key from decision parameters."""
        context_str = str(sorted(context.items())) if context else ""
        key_str = f"{caller_id}:{resource}:{action}:{context_str}"
        return hashlib.sha256(key_str.encode()).hexdigest()

    async def get(
        self,
        caller_id: str,
        resource: str,
        action: str,
        context: Optional[dict]
    ) -> Optional[AuthzDecision]:
        """Get cached decision if still valid."""
        async with self._lock:
            key = self._make_key(caller_id, resource, action, context)
            entry = self._cache.get(key)

            if entry is None:
                return None

            decision, timestamp = entry
            age = (datetime.utcnow() - timestamp).total_seconds()

            if age > self.ttl_seconds:
                del self._cache[key]
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            return decision

    async def put(
        self,
        caller_id: str,
        resource: str,
        action: str,
        context: Optional[dict],
        decision: AuthzDecision
    ):
        """Cache an authorization decision."""
        async with self._lock:
            key = self._make_key(caller_id, resource, action, context)
            self._cache[key] = (decision, datetime.utcnow())
            self._cache.move_to_end(key)

            # Evict oldest if over size
            if len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    async def clear(self):
        """Clear all cached decisions."""
        async with self._lock:
            self._cache.clear()


class OPAProvider(AuthorizationProvider):
    """
    OPA-based authorization provider.

    Features:
    - REST API integration with OPA
    - Circuit breaker for OPA failures
    - Decision caching with TTL
    - Automatic audit logging
    - Default deny in production mode
    - SPIFFE ID aware policy context
    """

    def __init__(
        self,
        endpoint: str = "http://localhost:8181",
        policy_path: str = "agentweave/authz/allow",
        default_deny: bool = True,
        cache_ttl: float = 60.0,
        cache_size: int = 1000,
        timeout: float = 5.0,
        circuit_breaker_threshold: int = 5,
        circuit_breaker_timeout: float = 30.0
    ):
        """
        Initialize OPA provider.

        Args:
            endpoint: OPA server base URL
            policy_path: Path to the policy decision endpoint
            default_deny: If True, deny requests when OPA is unavailable
            cache_ttl: Cache TTL in seconds
            cache_size: Maximum cache size
            timeout: Request timeout in seconds
            circuit_breaker_threshold: Failures before opening circuit
            circuit_breaker_timeout: Seconds before attempting recovery
        """
        self.endpoint = endpoint.rstrip('/')
        self.policy_path = policy_path.strip('/')
        self.default_deny = default_deny
        self.timeout = timeout

        self._client = httpx.AsyncClient(timeout=timeout)
        self._cache = DecisionCache(max_size=cache_size, ttl_seconds=cache_ttl)
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=circuit_breaker_threshold,
            recovery_timeout=circuit_breaker_timeout
        )

        logger.info(
            f"OPA provider initialized: endpoint={endpoint}, "
            f"policy_path={policy_path}, default_deny={default_deny}"
        )

    async def check(
        self,
        caller_id: str,
        resource: str,
        action: str,
        context: Optional[dict] = None
    ) -> AuthzDecision:
        """
        Check authorization via OPA.

        Args:
            caller_id: SPIFFE ID of the caller
            resource: Resource being accessed (typically target SPIFFE ID)
            action: Action being performed
            context: Additional context for policy evaluation

        Returns:
            AuthzDecision with the result
        """
        # Check cache first
        cached = await self._cache.get(caller_id, resource, action, context)
        if cached is not None:
            logger.debug(f"Cache hit for {caller_id} -> {resource}:{action}")
            return cached

        # Build OPA input document
        input_doc = self._build_input(caller_id, resource, action, context)

        try:
            # Query OPA with circuit breaker protection
            decision = await self._circuit_breaker.call(
                self._query_opa,
                input_doc
            )

            # Cache the decision
            await self._cache.put(caller_id, resource, action, context, decision)

            # Audit log
            self._audit_log(caller_id, resource, action, decision, context)

            return decision

        except CircuitBreakerError as e:
            logger.error(f"Circuit breaker open, applying default policy: {e}")
            return self._default_decision(caller_id, resource, action, str(e))

        except Exception as e:
            logger.error(f"OPA query failed: {e}", exc_info=True)
            return self._default_decision(caller_id, resource, action, str(e))

    def _build_input(
        self,
        caller_id: str,
        resource: str,
        action: str,
        context: Optional[dict]
    ) -> dict:
        """Build OPA input document with SPIFFE context."""
        input_doc = {
            "caller_spiffe_id": caller_id,
            "resource_spiffe_id": resource,
            "action": action,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Extract trust domains
        try:
            caller_domain = caller_id.split('/')[2] if caller_id.startswith('spiffe://') else None
            resource_domain = resource.split('/')[2] if resource.startswith('spiffe://') else None

            if caller_domain:
                input_doc["caller_trust_domain"] = caller_domain
            if resource_domain:
                input_doc["resource_trust_domain"] = resource_domain
        except IndexError:
            logger.warning(f"Failed to parse trust domains from SPIFFE IDs: {caller_id}, {resource}")

        # Add additional context
        if context:
            input_doc["context"] = context

        return input_doc

    async def _query_opa(self, input_doc: dict) -> AuthzDecision:
        """
        Query OPA for authorization decision.

        Args:
            input_doc: OPA input document

        Returns:
            AuthzDecision from OPA response

        Raises:
            httpx.HTTPError: On HTTP errors
            ValueError: On invalid OPA response
        """
        url = f"{self.endpoint}/v1/data/{self.policy_path}"

        logger.debug(f"Querying OPA: {url}")

        response = await self._client.post(
            url,
            json={"input": input_doc}
        )
        response.raise_for_status()

        result = response.json()

        # Parse OPA response
        # Expected format: {"result": true} or {"result": {"allow": true, "reason": "..."}}
        opa_result = result.get("result")

        if opa_result is None:
            raise ValueError("OPA response missing 'result' field")

        # Handle boolean result
        if isinstance(opa_result, bool):
            allowed = opa_result
            reason = "Policy decision" if allowed else "Policy denied"
            policy_id = None
        # Handle object result
        elif isinstance(opa_result, dict):
            allowed = opa_result.get("allow", False)
            reason = opa_result.get("reason", "Policy decision")
            policy_id = opa_result.get("policy_id")
        else:
            raise ValueError(f"Unexpected OPA result type: {type(opa_result)}")

        return AuthzDecision(
            allowed=allowed,
            reason=reason,
            policy_id=policy_id
        )

    def _default_decision(self, caller_id: str, resource: str, action: str, error: str) -> AuthzDecision:
        """
        Apply default policy when OPA is unavailable.

        Args:
            caller_id: Caller SPIFFE ID
            resource: Resource SPIFFE ID
            action: Action being performed
            error: Error message

        Returns:
            AuthzDecision based on default_deny setting
        """
        if self.default_deny:
            logger.warning(
                f"Default DENY applied: {caller_id} -> {resource}:{action} (OPA unavailable: {error})"
            )
            return AuthzDecision(
                allowed=False,
                reason=f"OPA unavailable, default deny policy applied: {error}",
                policy_id="default-deny"
            )
        else:
            logger.warning(
                f"Default ALLOW applied: {caller_id} -> {resource}:{action} (OPA unavailable: {error})"
            )
            return AuthzDecision(
                allowed=True,
                reason=f"OPA unavailable, default allow policy applied: {error}",
                policy_id="default-allow"
            )

    def _audit_log(
        self,
        caller_id: str,
        resource: str,
        action: str,
        decision: AuthzDecision,
        context: Optional[dict]
    ):
        """
        Log authorization decision for audit trail.

        Args:
            caller_id: Caller SPIFFE ID
            resource: Resource SPIFFE ID
            action: Action performed
            decision: Authorization decision
            context: Additional context
        """
        logger.info(
            f"AUTHZ: {decision.audit_id} | "
            f"caller={caller_id} | "
            f"resource={resource} | "
            f"action={action} | "
            f"allowed={decision.allowed} | "
            f"reason={decision.reason} | "
            f"policy_id={decision.policy_id}"
        )

    async def health_check(self) -> bool:
        """
        Check if OPA is healthy and reachable.

        Returns:
            True if OPA is healthy, False otherwise
        """
        try:
            url = f"{self.endpoint}/health"
            response = await self._client.get(url, timeout=2.0)
            return response.status_code == 200
        except Exception as e:
            logger.warning(f"OPA health check failed: {e}")
            return False

    async def close(self):
        """Close the HTTP client."""
        await self._client.aclose()


class CircuitBreakerError(Exception):
    """Raised when circuit breaker is open."""
    pass


class AuthorizationError(Exception):
    """Raised when authorization check fails."""
    pass
