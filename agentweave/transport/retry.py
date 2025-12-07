"""
Retry logic with exponential backoff for AgentWeave SDK.

This module provides configurable retry policies with exponential backoff
and jitter to prevent thundering herd problems.
"""

import asyncio
import random
from dataclasses import dataclass
from typing import Callable, TypeVar, ParamSpec, Any
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

P = ParamSpec('P')
T = TypeVar('T')


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Initial delay between retries in seconds (default: 1.0)
        max_delay: Maximum delay between retries in seconds (default: 30.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Whether to add random jitter to delays (default: True)
        retryable_exceptions: Tuple of exception types that should trigger retry
    """
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retryable_exceptions: tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )

    def __post_init__(self) -> None:
        """Validate retry configuration."""
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.base_delay <= 0:
            raise ValueError("base_delay must be positive")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if self.exponential_base <= 1:
            raise ValueError("exponential_base must be > 1")


class RetryPolicy:
    """Implements retry logic with exponential backoff and jitter.

    This class handles automatic retrying of operations with configurable
    backoff strategies. It supports:
    - Exponential backoff
    - Optional jitter to prevent thundering herd
    - Selective retry based on exception type
    - Detailed logging for audit trails

    Example:
        policy = RetryPolicy(RetryConfig(max_retries=3))
        result = await policy.execute(some_async_function, arg1, arg2)
    """

    def __init__(self, config: RetryConfig) -> None:
        """Initialize retry policy with configuration.

        Args:
            config: RetryConfig instance with retry parameters
        """
        self._config = config
        self._attempt_count = 0
        self._total_delay = 0.0

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay for the given retry attempt.

        Uses exponential backoff with optional jitter:
        delay = min(base * (exponential_base ^ attempt), max_delay)

        Args:
            attempt: The retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        # Calculate exponential delay
        delay = self._config.base_delay * (
            self._config.exponential_base ** attempt
        )

        # Cap at max_delay
        delay = min(delay, self._config.max_delay)

        # Add jitter if enabled (random value between 0 and delay)
        if self._config.jitter:
            delay = random.uniform(0, delay)

        return delay

    def _is_retryable(self, exception: Exception) -> bool:
        """Check if an exception should trigger a retry.

        Args:
            exception: The exception to check

        Returns:
            True if the exception is retryable, False otherwise
        """
        return isinstance(exception, self._config.retryable_exceptions)

    async def execute(
        self,
        func: Callable[P, T],
        *args: P.args,
        **kwargs: P.kwargs
    ) -> T:
        """Execute a function with retry logic.

        Args:
            func: Async function to execute
            *args: Positional arguments to pass to func
            **kwargs: Keyword arguments to pass to func

        Returns:
            Result of func

        Raises:
            The last exception if all retries are exhausted
        """
        last_exception: Exception | None = None

        for attempt in range(self._config.max_retries + 1):
            try:
                self._attempt_count = attempt
                logger.debug(
                    f"Executing attempt {attempt + 1}/{self._config.max_retries + 1}"
                )

                result = await func(*args, **kwargs)

                if attempt > 0:
                    logger.info(
                        f"Operation succeeded after {attempt} retries, "
                        f"total delay: {self._total_delay:.2f}s"
                    )

                return result

            except Exception as e:
                last_exception = e

                # Check if we should retry this exception
                if not self._is_retryable(e):
                    logger.warning(
                        f"Non-retryable exception: {type(e).__name__}: {e}"
                    )
                    raise

                # Check if we have retries left
                if attempt >= self._config.max_retries:
                    logger.error(
                        f"All {self._config.max_retries} retries exhausted. "
                        f"Last exception: {type(e).__name__}: {e}"
                    )
                    raise

                # Calculate delay and wait
                delay = self._calculate_delay(attempt)
                self._total_delay += delay

                logger.info(
                    f"Retry {attempt + 1}/{self._config.max_retries} after "
                    f"{type(e).__name__}: {e}. "
                    f"Waiting {delay:.2f}s before retry"
                )

                await asyncio.sleep(delay)

        # This should never be reached, but satisfy type checker
        if last_exception:
            raise last_exception
        raise RuntimeError("Unexpected retry state")

    def get_stats(self) -> dict[str, Any]:
        """Get statistics about retry attempts.

        Returns:
            Dictionary containing retry statistics
        """
        return {
            "attempt_count": self._attempt_count,
            "total_delay": self._total_delay,
            "max_retries": self._config.max_retries,
        }


def with_retry(config: RetryConfig | None = None):
    """Decorator to add retry logic to async functions.

    Args:
        config: RetryConfig instance, or None to use defaults

    Example:
        @with_retry(RetryConfig(max_retries=5))
        async def fetch_data():
            # This will be retried up to 5 times
            return await http_client.get(url)
    """
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            retry_config = config or RetryConfig()
            policy = RetryPolicy(retry_config)
            return await policy.execute(func, *args, **kwargs)

        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper

    return decorator
