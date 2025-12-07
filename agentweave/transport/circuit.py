"""
Circuit breaker pattern implementation for AgentWeave SDK.

This module implements the circuit breaker pattern to prevent cascading failures
and allow systems to recover gracefully from transient errors.
"""

import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TypeVar, ParamSpec, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


class CircuitState(Enum):
    """States of the circuit breaker."""
    CLOSED = "closed"      # Normal operation, requests pass through
    OPEN = "open"          # Circuit tripped, requests fail fast
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior.

    Attributes:
        failure_threshold: Number of failures before opening circuit (default: 5)
        success_threshold: Number of successes in HALF_OPEN to close circuit (default: 2)
        timeout: Seconds to wait before attempting recovery (default: 30.0)
        excluded_exceptions: Exceptions that don't count as failures
    """
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout: float = 30.0
    excluded_exceptions: tuple[type[Exception], ...] = ()

    def __post_init__(self) -> None:
        """Validate circuit breaker configuration."""
        if self.failure_threshold <= 0:
            raise ValueError("failure_threshold must be positive")
        if self.success_threshold <= 0:
            raise ValueError("success_threshold must be positive")
        if self.timeout <= 0:
            raise ValueError("timeout must be positive")


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker monitoring.

    Attributes:
        state: Current circuit state
        failure_count: Current count of consecutive failures
        success_count: Current count of consecutive successes (in HALF_OPEN)
        total_calls: Total number of calls attempted
        total_failures: Total number of failures
        total_successes: Total number of successes
        total_rejected: Total number of calls rejected (circuit open)
        last_failure_time: Timestamp of last failure
        last_state_change: Timestamp of last state change
    """
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    total_rejected: int = 0
    last_failure_time: float | None = None
    last_state_change: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary format."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count,
            "total_calls": self.total_calls,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "total_rejected": self.total_rejected,
            "last_failure_time": self.last_failure_time,
            "last_state_change": self.last_state_change,
        }


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open and rejects requests."""

    def __init__(self, target: str, metrics: CircuitBreakerMetrics):
        self.target = target
        self.metrics = metrics
        super().__init__(
            f"Circuit breaker is OPEN for {target}. "
            f"Failures: {metrics.failure_count}, "
            f"Last failure: {metrics.last_failure_time}"
        )


class CircuitBreaker:
    """Implements circuit breaker pattern for fault tolerance.

    The circuit breaker prevents cascading failures by:
    - CLOSED: Normal operation, all requests pass through
    - OPEN: After failure threshold, all requests fail fast
    - HALF_OPEN: After timeout, allow test requests to check recovery

    Example:
        circuit = CircuitBreaker("api-service", CircuitBreakerConfig())
        result = await circuit.call(api_function, arg1, arg2)
    """

    def __init__(self, name: str, config: CircuitBreakerConfig) -> None:
        """Initialize circuit breaker.

        Args:
            name: Name of the circuit (for logging/metrics)
            config: CircuitBreakerConfig instance
        """
        self._name = name
        self._config = config
        self._metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> CircuitState:
        """Get current circuit state."""
        return self._metrics.state

    @property
    def metrics(self) -> CircuitBreakerMetrics:
        """Get current metrics (read-only copy)."""
        return CircuitBreakerMetrics(
            state=self._metrics.state,
            failure_count=self._metrics.failure_count,
            success_count=self._metrics.success_count,
            total_calls=self._metrics.total_calls,
            total_failures=self._metrics.total_failures,
            total_successes=self._metrics.total_successes,
            total_rejected=self._metrics.total_rejected,
            last_failure_time=self._metrics.last_failure_time,
            last_state_change=self._metrics.last_state_change,
        )

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset from OPEN to HALF_OPEN.

        Returns:
            True if timeout has elapsed since last failure
        """
        if self._metrics.last_failure_time is None:
            return False

        elapsed = time.time() - self._metrics.last_failure_time
        return elapsed >= self._config.timeout

    async def _transition_state(self, new_state: CircuitState) -> None:
        """Transition to a new circuit state.

        Args:
            new_state: The state to transition to
        """
        old_state = self._metrics.state

        if old_state == new_state:
            return

        self._metrics.state = new_state
        self._metrics.last_state_change = time.time()

        logger.info(
            f"Circuit '{self._name}' transitioned: {old_state.value} -> {new_state.value}"
        )

        # Reset counters on state change
        if new_state == CircuitState.CLOSED:
            self._metrics.failure_count = 0
            self._metrics.success_count = 0
        elif new_state == CircuitState.HALF_OPEN:
            self._metrics.success_count = 0

    async def _record_success(self) -> None:
        """Record a successful call."""
        async with self._lock:
            self._metrics.total_calls += 1
            self._metrics.total_successes += 1

            if self._metrics.state == CircuitState.HALF_OPEN:
                self._metrics.success_count += 1
                logger.debug(
                    f"Circuit '{self._name}' HALF_OPEN success "
                    f"{self._metrics.success_count}/{self._config.success_threshold}"
                )

                if self._metrics.success_count >= self._config.success_threshold:
                    await self._transition_state(CircuitState.CLOSED)
                    logger.info(
                        f"Circuit '{self._name}' recovered and CLOSED after "
                        f"{self._config.success_threshold} successful calls"
                    )
            elif self._metrics.state == CircuitState.CLOSED:
                # Reset failure count on success
                self._metrics.failure_count = 0

    async def _record_failure(self, exception: Exception) -> None:
        """Record a failed call.

        Args:
            exception: The exception that caused the failure
        """
        # Check if this exception should be excluded
        if isinstance(exception, self._config.excluded_exceptions):
            logger.debug(
                f"Circuit '{self._name}' ignoring excluded exception: "
                f"{type(exception).__name__}"
            )
            return

        async with self._lock:
            self._metrics.total_calls += 1
            self._metrics.total_failures += 1
            self._metrics.failure_count += 1
            self._metrics.last_failure_time = time.time()

            logger.warning(
                f"Circuit '{self._name}' failure recorded: {type(exception).__name__}: {exception}"
            )

            if self._metrics.state == CircuitState.HALF_OPEN:
                # Any failure in HALF_OPEN immediately re-opens circuit
                await self._transition_state(CircuitState.OPEN)
                logger.warning(
                    f"Circuit '{self._name}' re-opened after failure in HALF_OPEN state"
                )

            elif self._metrics.state == CircuitState.CLOSED:
                if self._metrics.failure_count >= self._config.failure_threshold:
                    await self._transition_state(CircuitState.OPEN)
                    logger.error(
                        f"Circuit '{self._name}' OPENED after "
                        f"{self._metrics.failure_count} failures "
                        f"(threshold: {self._config.failure_threshold})"
                    )

    async def call(
        self,
        func: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs
    ) -> T:
        """Execute a function through the circuit breaker.

        Args:
            func: Async function to execute
            *args: Positional arguments to pass to func
            **kwargs: Keyword arguments to pass to func

        Returns:
            Result of func

        Raises:
            CircuitOpenError: If circuit is open and rejects the request
            Exception: Any exception raised by func
        """
        # Check if we should transition from OPEN to HALF_OPEN
        if self._metrics.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                async with self._lock:
                    # Double-check after acquiring lock
                    if self._should_attempt_reset():
                        await self._transition_state(CircuitState.HALF_OPEN)
                        logger.info(
                            f"Circuit '{self._name}' attempting recovery (HALF_OPEN)"
                        )

        # Reject if still open
        if self._metrics.state == CircuitState.OPEN:
            self._metrics.total_rejected += 1
            logger.debug(
                f"Circuit '{self._name}' rejected request (OPEN state)"
            )
            raise CircuitOpenError(self._name, self.metrics)

        # Execute the function
        try:
            result = await func(*args, **kwargs)
            await self._record_success()
            return result

        except Exception as e:
            await self._record_failure(e)
            raise

    async def reset(self) -> None:
        """Manually reset the circuit breaker to CLOSED state.

        This should be used with caution, typically for administrative purposes.
        """
        async with self._lock:
            await self._transition_state(CircuitState.CLOSED)
            self._metrics.failure_count = 0
            self._metrics.success_count = 0
            logger.warning(f"Circuit '{self._name}' manually reset to CLOSED")


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers per target.

    This allows per-target circuit breakers so that failures to one
    service don't affect calls to other services.
    """

    def __init__(self, default_config: CircuitBreakerConfig | None = None) -> None:
        """Initialize circuit breaker registry.

        Args:
            default_config: Default configuration for new circuit breakers
        """
        self._default_config = default_config or CircuitBreakerConfig()
        self._breakers: dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    async def get_breaker(
        self,
        target: str,
        config: CircuitBreakerConfig | None = None
    ) -> CircuitBreaker:
        """Get or create a circuit breaker for a target.

        Args:
            target: Target identifier (e.g., SPIFFE ID)
            config: Optional config override for this circuit

        Returns:
            CircuitBreaker instance for the target
        """
        if target in self._breakers:
            return self._breakers[target]

        async with self._lock:
            # Double-check after acquiring lock
            if target in self._breakers:
                return self._breakers[target]

            breaker_config = config or self._default_config
            breaker = CircuitBreaker(target, breaker_config)
            self._breakers[target] = breaker

            logger.info(f"Created circuit breaker for target: {target}")
            return breaker

    def get_all_metrics(self) -> dict[str, dict[str, Any]]:
        """Get metrics for all circuit breakers.

        Returns:
            Dictionary mapping target to metrics
        """
        return {
            target: breaker.metrics.to_dict()
            for target, breaker in self._breakers.items()
        }

    async def reset_all(self) -> None:
        """Reset all circuit breakers to CLOSED state."""
        for breaker in self._breakers.values():
            await breaker.reset()
        logger.warning("All circuit breakers reset")
