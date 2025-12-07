"""
Connection pooling for AgentWeave SDK.

This module provides a ConnectionPool that manages multiple SecureChannel instances,
implementing per-target connection limits, idle connection cleanup, and health checking.
"""

import asyncio
import time
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol
from collections import defaultdict

from .channel import SecureChannel, TransportConfig


logger = logging.getLogger(__name__)


# Identity provider protocol (to avoid circular imports)
class IdentityProvider(Protocol):
    """Protocol for identity providers."""

    def get_spiffe_id(self) -> str:
        """Get this workload's SPIFFE ID."""
        ...


@dataclass(frozen=True)
class PoolConfig:
    """Configuration for connection pool.

    Attributes:
        max_connections_per_target: Maximum connections per target (default: 10)
        max_total_connections: Maximum total connections (default: 100)
        idle_timeout: Seconds before closing idle connection (default: 60.0)
        health_check_interval: Seconds between health checks (default: 30.0)
        cleanup_interval: Seconds between cleanup runs (default: 10.0)
    """
    max_connections_per_target: int = 10
    max_total_connections: int = 100
    idle_timeout: float = 60.0
    health_check_interval: float = 30.0
    cleanup_interval: float = 10.0

    def __post_init__(self) -> None:
        """Validate pool configuration."""
        if self.max_connections_per_target <= 0:
            raise ValueError("max_connections_per_target must be positive")
        if self.max_total_connections < self.max_connections_per_target:
            raise ValueError(
                "max_total_connections must be >= max_connections_per_target"
            )
        if self.idle_timeout <= 0:
            raise ValueError("idle_timeout must be positive")
        if self.health_check_interval <= 0:
            raise ValueError("health_check_interval must be positive")
        if self.cleanup_interval <= 0:
            raise ValueError("cleanup_interval must be positive")


@dataclass
class PooledConnection:
    """Wrapper for a pooled connection with metadata.

    Attributes:
        channel: The secure channel instance
        target_id: SPIFFE ID of the target
        created_at: Timestamp when connection was created
        last_used: Timestamp of last use
        in_use: Whether connection is currently in use
        health_status: Health status ("healthy", "unhealthy", "unknown")
        use_count: Number of times this connection has been used
    """
    channel: SecureChannel
    target_id: str
    created_at: float = field(default_factory=time.time)
    last_used: float = field(default_factory=time.time)
    in_use: bool = False
    health_status: str = "unknown"
    use_count: int = 0

    def is_idle(self, idle_timeout: float) -> bool:
        """Check if connection has been idle too long.

        Args:
            idle_timeout: Idle timeout in seconds

        Returns:
            True if connection has been idle longer than timeout
        """
        if self.in_use:
            return False
        return (time.time() - self.last_used) > idle_timeout

    def mark_used(self) -> None:
        """Mark connection as used."""
        self.last_used = time.time()
        self.use_count += 1


class ConnectionPoolError(Exception):
    """Base exception for connection pool errors."""
    pass


class PoolExhaustedError(ConnectionPoolError):
    """Raised when connection pool is exhausted."""

    def __init__(self, target_id: str, max_connections: int):
        super().__init__(
            f"Connection pool exhausted for target {target_id}. "
            f"Max connections: {max_connections}"
        )


class ConnectionPool:
    """Thread-safe connection pool for SecureChannel instances.

    This class manages a pool of connections to different targets, providing:
    - Per-target connection limits
    - Idle connection cleanup
    - Health checking of pooled connections
    - Thread-safe connection acquisition and release

    Example:
        pool = ConnectionPool(identity_provider, PoolConfig())
        async with pool.acquire("spiffe://example.com/service") as channel:
            response = await channel.get("/api/endpoint")
    """

    def __init__(
        self,
        identity_provider: IdentityProvider,
        config: PoolConfig | None = None,
        transport_config: TransportConfig | None = None,
    ) -> None:
        """Initialize connection pool.

        Args:
            identity_provider: Provider for SPIFFE identity
            config: Pool configuration
            transport_config: Transport configuration for new channels
        """
        self._identity = identity_provider
        self._config = config or PoolConfig()
        self._transport_config = transport_config or TransportConfig()

        # Pool storage: target_id -> list of pooled connections
        self._pools: dict[str, list[PooledConnection]] = defaultdict(list)

        # Locks for thread safety
        self._pool_lock = asyncio.Lock()
        self._target_locks: dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)

        # Background tasks
        self._cleanup_task: asyncio.Task | None = None
        self._health_check_task: asyncio.Task | None = None
        self._running = False

        # Metrics
        self._total_connections = 0
        self._total_acquisitions = 0
        self._total_creations = 0
        self._total_cleanups = 0

        logger.info(
            f"ConnectionPool initialized (max per target: "
            f"{self._config.max_connections_per_target}, "
            f"max total: {self._config.max_total_connections})"
        )

    async def start(self) -> None:
        """Start background tasks for cleanup and health checking."""
        if self._running:
            return

        self._running = True

        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

        # Start health check task
        self._health_check_task = asyncio.create_task(self._health_check_loop())

        logger.info("ConnectionPool background tasks started")

    async def stop(self) -> None:
        """Stop background tasks and close all connections."""
        if not self._running:
            return

        self._running = False

        # Cancel background tasks
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Close all connections
        await self.close_all()

        logger.info("ConnectionPool stopped")

    async def _create_connection(self, target_id: str) -> PooledConnection:
        """Create a new pooled connection.

        Args:
            target_id: SPIFFE ID of the target

        Returns:
            New PooledConnection instance
        """
        channel = SecureChannel(
            identity_provider=self._identity,
            peer_spiffe_id=target_id,
            config=self._transport_config,
        )

        connection = PooledConnection(
            channel=channel,
            target_id=target_id,
        )

        self._total_creations += 1
        self._total_connections += 1

        logger.debug(
            f"Created new connection to {target_id} "
            f"(total: {self._total_connections})"
        )

        return connection

    async def _get_available_connection(
        self, target_id: str
    ) -> PooledConnection | None:
        """Get an available connection from the pool.

        Args:
            target_id: SPIFFE ID of the target

        Returns:
            Available connection or None if none available
        """
        pool = self._pools.get(target_id, [])

        for conn in pool:
            if not conn.in_use:
                conn.in_use = True
                conn.mark_used()
                logger.debug(
                    f"Reusing connection to {target_id} "
                    f"(use count: {conn.use_count})"
                )
                return conn

        return None

    async def acquire(self, target_id: str) -> "PooledChannelContext":
        """Acquire a connection to the target.

        This is the primary method for getting connections from the pool.
        It should be used with async context manager:

        async with pool.acquire(target_id) as channel:
            response = await channel.get("/api")

        Args:
            target_id: SPIFFE ID of the target

        Returns:
            Context manager that yields SecureChannel

        Raises:
            PoolExhaustedError: If pool is exhausted and can't create new connection
        """
        if not target_id.startswith("spiffe://"):
            raise ValueError(f"Invalid SPIFFE ID: {target_id}")

        self._total_acquisitions += 1

        # Try to get existing connection
        async with self._target_locks[target_id]:
            conn = await self._get_available_connection(target_id)

            if conn is None:
                # Check if we can create a new connection
                pool = self._pools[target_id]
                pool_size = len(pool)

                if pool_size >= self._config.max_connections_per_target:
                    raise PoolExhaustedError(
                        target_id,
                        self._config.max_connections_per_target,
                    )

                if self._total_connections >= self._config.max_total_connections:
                    raise PoolExhaustedError(
                        target_id,
                        self._config.max_total_connections,
                    )

                # Create new connection
                conn = await self._create_connection(target_id)
                conn.in_use = True
                pool.append(conn)

        return PooledChannelContext(self, conn)

    async def release(self, connection: PooledConnection) -> None:
        """Release a connection back to the pool.

        Args:
            connection: Connection to release
        """
        async with self._target_locks[connection.target_id]:
            connection.in_use = False
            logger.debug(f"Released connection to {connection.target_id}")

    async def _cleanup_idle_connections(self) -> None:
        """Remove and close idle connections."""
        cleaned = 0

        async with self._pool_lock:
            for target_id, pool in list(self._pools.items()):
                to_remove = []

                for conn in pool:
                    if conn.is_idle(self._config.idle_timeout):
                        to_remove.append(conn)

                # Remove and close idle connections
                for conn in to_remove:
                    pool.remove(conn)
                    await conn.channel.close()
                    self._total_connections -= 1
                    cleaned += 1

                # Remove empty pools
                if not pool:
                    del self._pools[target_id]

        if cleaned > 0:
            self._total_cleanups += cleaned
            logger.debug(f"Cleaned up {cleaned} idle connections")

    async def _cleanup_loop(self) -> None:
        """Background task to cleanup idle connections."""
        while self._running:
            try:
                await asyncio.sleep(self._config.cleanup_interval)
                await self._cleanup_idle_connections()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in cleanup loop: {e}")

    async def _health_check_connection(
        self, connection: PooledConnection
    ) -> bool:
        """Health check a single connection.

        Args:
            connection: Connection to check

        Returns:
            True if healthy, False otherwise
        """
        # For now, just check if connection is not in use
        # In a real implementation, we might send a ping request
        try:
            if connection.in_use:
                return True

            # Simple check: has the connection been created recently?
            age = time.time() - connection.created_at
            if age > self._config.health_check_interval * 10:
                # Connection is old, mark as potentially unhealthy
                connection.health_status = "unhealthy"
                return False

            connection.health_status = "healthy"
            return True

        except Exception as e:
            logger.warning(
                f"Health check failed for {connection.target_id}: {e}"
            )
            connection.health_status = "unhealthy"
            return False

    async def _health_check_loop(self) -> None:
        """Background task to health check connections."""
        while self._running:
            try:
                await asyncio.sleep(self._config.health_check_interval)

                # Health check all connections
                for target_id, pool in self._pools.items():
                    for conn in pool:
                        if not conn.in_use:
                            await self._health_check_connection(conn)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")

    async def close_all(self) -> None:
        """Close all pooled connections."""
        async with self._pool_lock:
            for target_id, pool in self._pools.items():
                for conn in pool:
                    await conn.channel.close()

            self._pools.clear()
            self._total_connections = 0

        logger.info("All pooled connections closed")

    def get_stats(self) -> dict[str, Any]:
        """Get pool statistics.

        Returns:
            Dictionary of pool statistics
        """
        pool_sizes = {
            target_id: len(pool)
            for target_id, pool in self._pools.items()
        }

        return {
            "total_connections": self._total_connections,
            "total_acquisitions": self._total_acquisitions,
            "total_creations": self._total_creations,
            "total_cleanups": self._total_cleanups,
            "pool_sizes": pool_sizes,
            "target_count": len(self._pools),
        }


class PooledChannelContext:
    """Context manager for pooled channel acquisition.

    This ensures connections are properly released back to the pool.
    """

    def __init__(self, pool: ConnectionPool, connection: PooledConnection):
        """Initialize context.

        Args:
            pool: Connection pool
            connection: Pooled connection
        """
        self._pool = pool
        self._connection = connection

    async def __aenter__(self) -> SecureChannel:
        """Enter context, return the channel."""
        return self._connection.channel

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context, release connection back to pool."""
        await self._pool.release(self._connection)
