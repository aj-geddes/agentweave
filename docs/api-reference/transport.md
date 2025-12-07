---
layout: api
title: Transport Module API Reference
parent: API Reference
nav_order: 1
---

# Transport Module API Reference

The `agentweave.transport` module provides secure, mTLS-enforced communication infrastructure with cryptographic identity verification. All components in this module enforce mutual TLS authentication and cannot be disabled.

**Security Guarantees:**
- Mutual TLS authentication is MANDATORY (cannot be disabled)
- SPIFFE ID verification on all connections
- TLS 1.3 preferred, 1.2 minimum
- Automatic certificate rotation support
- Full audit logging of all connections

---

## SecureChannel

**Import:** `from agentweave.transport import SecureChannel`

Secure mTLS communication channel with mandatory peer verification. This class wraps `httpx.AsyncClient` and enforces mutual TLS authentication using SPIFFE SVIDs.

### Constructor

```python
SecureChannel(
    identity_provider: IdentityProvider,
    peer_spiffe_id: str,
    config: TransportConfig | None = None
)
```

**Parameters:**
- `identity_provider` (IdentityProvider): Provider for this workload's SPIFFE identity
- `peer_spiffe_id` (str): Expected SPIFFE ID of the peer (must start with "spiffe://")
- `config` (TransportConfig, optional): Transport configuration (uses defaults if None)

**Raises:**
- `ValueError`: If peer_spiffe_id is invalid

### Properties

#### peer_spiffe_id
```python
@property
def peer_spiffe_id(self) -> str
```
Get expected peer SPIFFE ID.

**Returns:** str - The SPIFFE ID of the peer

#### my_spiffe_id
```python
@property
def my_spiffe_id(self) -> str
```
Get this workload's SPIFFE ID.

**Returns:** str - This workload's SPIFFE ID

### Methods

#### request
```python
async def request(
    method: str,
    url: str,
    **kwargs: Any
) -> httpx.Response
```
Make HTTP request over secure mTLS channel with automatic retry if configured.

**Parameters:**
- `method` (str): HTTP method (GET, POST, PUT, DELETE, etc.)
- `url` (str): Request URL
- `**kwargs`: Additional arguments passed to httpx

**Returns:** `httpx.Response` - HTTP response object

**Raises:**
- `httpx.HTTPError`: On request failure
- `PeerVerificationError`: If peer verification fails

#### get
```python
async def get(url: str, **kwargs: Any) -> httpx.Response
```
Make GET request over secure channel.

**Parameters:**
- `url` (str): Request URL
- `**kwargs`: Additional arguments passed to httpx

**Returns:** `httpx.Response`

#### post
```python
async def post(url: str, **kwargs: Any) -> httpx.Response
```
Make POST request over secure channel.

**Parameters:**
- `url` (str): Request URL
- `**kwargs`: Additional arguments passed to httpx (e.g., `json`, `data`, `headers`)

**Returns:** `httpx.Response`

#### put
```python
async def put(url: str, **kwargs: Any) -> httpx.Response
```
Make PUT request over secure channel.

**Parameters:**
- `url` (str): Request URL
- `**kwargs`: Additional arguments passed to httpx

**Returns:** `httpx.Response`

#### delete
```python
async def delete(url: str, **kwargs: Any) -> httpx.Response
```
Make DELETE request over secure channel.

**Parameters:**
- `url` (str): Request URL
- `**kwargs`: Additional arguments passed to httpx

**Returns:** `httpx.Response`

#### close
```python
async def close() -> None
```
Close the HTTP client and cleanup resources.

### Context Manager Support

SecureChannel supports async context manager protocol:

```python
async with SecureChannel(identity, peer_id, config) as channel:
    response = await channel.get("https://api.example.com/data")
```

### Example

```python
from agentweave.transport import SecureChannel, TransportConfig, RetryConfig

# Create configuration with retry
config = TransportConfig(
    tls_min_version=ssl.TLSVersion.TLSv1_3,
    timeout=30.0,
    retry_config=RetryConfig(max_retries=3)
)

# Create secure channel
channel = SecureChannel(
    identity_provider=identity,
    peer_spiffe_id="spiffe://example.com/api-service",
    config=config
)

# Use as context manager
async with channel:
    response = await channel.get("https://api-service.example.com/data")
    data = response.json()
```

---

## TransportConfig

**Import:** `from agentweave.transport import TransportConfig`

Configuration for secure transport behavior.

### Constructor

```python
TransportConfig(
    tls_min_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_3,
    tls_max_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_3,
    timeout: float = 30.0,
    verify_peer: bool = True,  # CANNOT BE DISABLED
    retry_config: RetryConfig | None = None
)
```

**Parameters:**
- `tls_min_version` (ssl.TLSVersion): Minimum TLS version (must be TLSv1_2 or higher)
- `tls_max_version` (ssl.TLSVersion): Maximum TLS version
- `timeout` (float): Request timeout in seconds (must be positive)
- `verify_peer` (bool): Always True, cannot be disabled (enforced by __post_init__)
- `retry_config` (RetryConfig, optional): Configuration for retry logic

**Raises:**
- `ValueError`: If verify_peer is False, tls_min_version is less than TLSv1_2, or timeout is not positive

---

## ConnectionPool

**Import:** `from agentweave.transport import ConnectionPool`

Thread-safe connection pool for managing multiple SecureChannel instances to different targets.

### Constructor

```python
ConnectionPool(
    identity_provider: IdentityProvider,
    config: PoolConfig | None = None,
    transport_config: TransportConfig | None = None
)
```

**Parameters:**
- `identity_provider` (IdentityProvider): Provider for SPIFFE identity
- `config` (PoolConfig, optional): Pool configuration
- `transport_config` (TransportConfig, optional): Transport configuration for new channels

### Methods

#### start
```python
async def start() -> None
```
Start background tasks for cleanup and health checking.

#### stop
```python
async def stop() -> None
```
Stop background tasks and close all connections.

#### acquire
```python
async def acquire(target_id: str) -> PooledChannelContext
```
Acquire a connection to the target. Returns a context manager that yields SecureChannel.

**Parameters:**
- `target_id` (str): SPIFFE ID of the target (must start with "spiffe://")

**Returns:** `PooledChannelContext` - Context manager that yields SecureChannel

**Raises:**
- `ValueError`: If target_id is invalid
- `PoolExhaustedError`: If pool is exhausted and can't create new connection

**Usage:**
```python
async with pool.acquire("spiffe://example.com/service") as channel:
    response = await channel.get("/api/endpoint")
```

#### release
```python
async def release(connection: PooledConnection) -> None
```
Release a connection back to the pool (normally handled by context manager).

**Parameters:**
- `connection` (PooledConnection): Connection to release

#### close_all
```python
async def close_all() -> None
```
Close all pooled connections.

#### get_stats
```python
def get_stats() -> dict[str, Any]
```
Get pool statistics.

**Returns:** Dictionary containing:
- `total_connections` (int): Total number of active connections
- `total_acquisitions` (int): Total number of acquisitions
- `total_creations` (int): Total number of connections created
- `total_cleanups` (int): Total number of connections cleaned up
- `pool_sizes` (dict): Per-target pool sizes
- `target_count` (int): Number of different targets

### Example

```python
from agentweave.transport import ConnectionPool, PoolConfig

# Create pool
pool = ConnectionPool(
    identity_provider=identity,
    config=PoolConfig(max_connections_per_target=10, idle_timeout=60.0)
)

await pool.start()

# Acquire and use connection
async with pool.acquire("spiffe://example.com/service") as channel:
    response = await channel.get("/api/data")

# Get statistics
stats = pool.get_stats()
print(f"Total connections: {stats['total_connections']}")

await pool.stop()
```

---

## PoolConfig

**Import:** `from agentweave.transport import PoolConfig`

Configuration for connection pool behavior.

### Constructor

```python
PoolConfig(
    max_connections_per_target: int = 10,
    max_total_connections: int = 100,
    idle_timeout: float = 60.0,
    health_check_interval: float = 30.0,
    cleanup_interval: float = 10.0
)
```

**Parameters:**
- `max_connections_per_target` (int): Maximum connections per target (default: 10)
- `max_total_connections` (int): Maximum total connections across all targets (default: 100)
- `idle_timeout` (float): Seconds before closing idle connection (default: 60.0)
- `health_check_interval` (float): Seconds between health checks (default: 30.0)
- `cleanup_interval` (float): Seconds between cleanup runs (default: 10.0)

**Raises:**
- `ValueError`: If parameters violate constraints

---

## CircuitBreaker

**Import:** `from agentweave.transport import CircuitBreaker`

Implements circuit breaker pattern for fault tolerance and preventing cascading failures.

### States

Circuit breaker operates in three states:
- **CLOSED**: Normal operation, all requests pass through
- **OPEN**: After failure threshold, all requests fail fast
- **HALF_OPEN**: After timeout, allow test requests to check recovery

### Constructor

```python
CircuitBreaker(
    name: str,
    config: CircuitBreakerConfig
)
```

**Parameters:**
- `name` (str): Name of the circuit (for logging/metrics)
- `config` (CircuitBreakerConfig): Circuit breaker configuration

### Properties

#### state
```python
@property
def state(self) -> CircuitState
```
Get current circuit state.

**Returns:** `CircuitState` - Current state (CLOSED, OPEN, or HALF_OPEN)

#### metrics
```python
@property
def metrics(self) -> CircuitBreakerMetrics
```
Get current metrics (read-only copy).

**Returns:** `CircuitBreakerMetrics` - Snapshot of current metrics

### Methods

#### call
```python
async def call(
    func: Callable[P, T],
    *args: P.args,
    **kwargs: P.kwargs
) -> T
```
Execute a function through the circuit breaker.

**Parameters:**
- `func` (Callable): Async function to execute
- `*args`: Positional arguments to pass to func
- `**kwargs`: Keyword arguments to pass to func

**Returns:** Result of func

**Raises:**
- `CircuitOpenError`: If circuit is open and rejects the request
- `Exception`: Any exception raised by func

#### reset
```python
async def reset() -> None
```
Manually reset the circuit breaker to CLOSED state. Use with caution.

### Example

```python
from agentweave.transport import CircuitBreaker, CircuitBreakerConfig

# Create circuit breaker
circuit = CircuitBreaker(
    name="api-service",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        success_threshold=2,
        timeout=30.0
    )
)

# Use circuit breaker
try:
    result = await circuit.call(api_function, arg1, arg2)
except CircuitOpenError:
    # Circuit is open, service is down
    return fallback_response()
```

---

## CircuitBreakerConfig

**Import:** `from agentweave.transport import CircuitBreakerConfig`

Configuration for circuit breaker behavior.

### Constructor

```python
CircuitBreakerConfig(
    failure_threshold: int = 5,
    success_threshold: int = 2,
    timeout: float = 30.0,
    excluded_exceptions: tuple[type[Exception], ...] = ()
)
```

**Parameters:**
- `failure_threshold` (int): Number of failures before opening circuit (default: 5)
- `success_threshold` (int): Number of successes in HALF_OPEN to close circuit (default: 2)
- `timeout` (float): Seconds to wait before attempting recovery (default: 30.0)
- `excluded_exceptions` (tuple): Exceptions that don't count as failures

**Raises:**
- `ValueError`: If parameters are invalid

---

## CircuitState

**Import:** `from agentweave.transport import CircuitState`

Enumeration of circuit breaker states.

```python
class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit tripped, fail fast
    HALF_OPEN = "half_open"  # Testing recovery
```

---

## RetryPolicy

**Import:** `from agentweave.transport import RetryPolicy`

Implements retry logic with exponential backoff and jitter to prevent thundering herd problems.

### Constructor

```python
RetryPolicy(config: RetryConfig)
```

**Parameters:**
- `config` (RetryConfig): Retry configuration

### Methods

#### execute
```python
async def execute(
    func: Callable[P, T],
    *args: P.args,
    **kwargs: P.kwargs
) -> T
```
Execute a function with retry logic.

**Parameters:**
- `func` (Callable): Async function to execute
- `*args`: Positional arguments to pass to func
- `**kwargs`: Keyword arguments to pass to func

**Returns:** Result of func

**Raises:** The last exception if all retries are exhausted

#### get_stats
```python
def get_stats() -> dict[str, Any]
```
Get statistics about retry attempts.

**Returns:** Dictionary with retry statistics

### Example

```python
from agentweave.transport import RetryPolicy, RetryConfig

policy = RetryPolicy(
    RetryConfig(
        max_retries=3,
        base_delay=1.0,
        exponential_base=2.0,
        jitter=True
    )
)

result = await policy.execute(unreliable_function, arg1, arg2)
```

---

## RetryConfig

**Import:** `from agentweave.transport import RetryConfig`

Configuration for retry behavior.

### Constructor

```python
RetryConfig(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple[type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )
)
```

**Parameters:**
- `max_retries` (int): Maximum number of retry attempts (default: 3)
- `base_delay` (float): Initial delay between retries in seconds (default: 1.0)
- `max_delay` (float): Maximum delay between retries in seconds (default: 30.0)
- `exponential_base` (float): Base for exponential backoff (default: 2.0)
- `jitter` (bool): Whether to add random jitter to delays (default: True)
- `retryable_exceptions` (tuple): Exception types that should trigger retry

**Raises:**
- `ValueError`: If parameters are invalid

### Retry Delay Calculation

Delay is calculated as: `min(base_delay * (exponential_base ^ attempt), max_delay)`

With jitter enabled, the actual delay is randomized between 0 and the calculated value.

---

## Exceptions

### PeerVerificationError

**Import:** `from agentweave.transport import PeerVerificationError`

Raised when peer certificate verification fails during mTLS handshake.

```python
class PeerVerificationError(Exception):
    expected_id: str  # Expected SPIFFE ID
    actual_id: str | None  # Actual SPIFFE ID from certificate
```

### ConnectionPoolError

**Import:** `from agentweave.transport import ConnectionPoolError`

Base exception for connection pool errors.

### PoolExhaustedError

**Import:** `from agentweave.transport import PoolExhaustedError`

Raised when connection pool is exhausted and cannot create new connections.

```python
class PoolExhaustedError(ConnectionPoolError):
    target_id: str  # SPIFFE ID of the target
    max_connections: int  # Maximum connections allowed
```

### CircuitOpenError

**Import:** `from agentweave.transport import CircuitOpenError`

Raised when circuit breaker is open and rejects requests.

```python
class CircuitOpenError(Exception):
    target: str  # Name of the circuit
    metrics: CircuitBreakerMetrics  # Current metrics
```

---

## Usage Patterns

### Basic Secure Channel

```python
from agentweave.transport import SecureChannel, TransportConfig

config = TransportConfig(timeout=30.0)
channel = SecureChannel(identity, peer_id, config)

async with channel:
    response = await channel.get("https://service/api")
```

### Connection Pooling

```python
from agentweave.transport import ConnectionPool, PoolConfig

pool = ConnectionPool(
    identity,
    PoolConfig(max_connections_per_target=10)
)
await pool.start()

async with pool.acquire(peer_id) as channel:
    response = await channel.get("/api")

await pool.stop()
```

### Circuit Breaker Protection

```python
from agentweave.transport import CircuitBreaker, CircuitBreakerConfig

circuit = CircuitBreaker(
    "service",
    CircuitBreakerConfig(failure_threshold=5)
)

try:
    result = await circuit.call(service_function)
except CircuitOpenError:
    # Handle service down scenario
    result = fallback()
```

### Retry with Backoff

```python
from agentweave.transport import RetryPolicy, RetryConfig

policy = RetryPolicy(
    RetryConfig(max_retries=3, base_delay=1.0)
)

result = await policy.execute(unreliable_call)
```

### Combined Pattern

```python
# Pool + Circuit Breaker + Retry
pool = ConnectionPool(identity, PoolConfig())
circuit_registry = CircuitBreakerRegistry()

await pool.start()

circuit = await circuit_registry.get_breaker(peer_id)

async with pool.acquire(peer_id) as channel:
    result = await circuit.call(channel.get, "/api")
```
