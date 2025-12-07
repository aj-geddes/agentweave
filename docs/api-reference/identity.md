---
layout: page
title: Identity Module
description: API reference for the agentweave.identity module
nav_order: 1
parent: API Reference
---

# Identity Module

The `agentweave.identity` module provides cryptographic identity management using SPIFFE/SPIRE. All agents must have a verified identity before they can communicate with other agents.

## Module Overview

```python
from agentweave.identity import (
    IdentityProvider,          # Abstract base class
    SPIFFEIdentityProvider,    # SPIFFE/SPIRE implementation
    IdentityError,             # Base exception
    TrustDomainError,         # Trust domain errors
    SVIDExpiredError,         # SVID expiration errors
    ConnectionError,          # Connection errors
)
```

## Classes

### IdentityProvider

Abstract base class that defines the interface for all identity providers.

```python
from abc import ABC, abstractmethod
import ssl
from typing import Optional
from spiffe import X509Svid, X509Bundle

class IdentityProvider(ABC):
    """Abstract base class for identity providers."""
```

#### Methods

##### get_identity()

Get the SPIFFE ID of this workload.

```python
async def get_identity(self) -> str
```

**Returns:**
- `str`: The SPIFFE ID in the format `spiffe://trust-domain/path`

**Raises:**
- `IdentityError`: If identity cannot be determined

**Example:**

```python
identity = await provider.get_identity()
print(identity)  # spiffe://agentweave.io/agent/search/prod
```

---

##### get_svid()

Get the current X.509 SVID for this workload.

```python
async def get_svid(self) -> X509Svid
```

Returns a cached SVID if available and valid, or fetches a new one if needed. The SVID contains the certificate chain and private key needed for mTLS.

**Returns:**
- `X509Svid`: The X.509 SVID containing certificate and private key

**Raises:**
- `IdentityError`: If SVID cannot be obtained

**Example:**

```python
svid = await provider.get_svid()
print(f"SVID expires: {svid.leaf.not_valid_after_utc}")
print(f"SPIFFE ID: {svid.spiffe_id}")
```

---

##### get_trust_bundle()

Get the trust bundle for verifying peer SVIDs.

```python
async def get_trust_bundle(self, trust_domain: Optional[str] = None) -> X509Bundle
```

The trust bundle contains the CA certificates needed to verify SVIDs from peers in the specified trust domain.

**Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `trust_domain` | `Optional[str]` | The trust domain to get the bundle for. If None, returns the bundle for this workload's trust domain. | `None` |

**Returns:**
- `X509Bundle`: The trust bundle containing CA certificates

**Raises:**
- `IdentityError`: If trust bundle cannot be obtained
- `TrustDomainError`: If the trust domain is not recognized

**Example:**

```python
# Get our own trust bundle
bundle = await provider.get_trust_bundle()

# Get trust bundle for another domain
partner_bundle = await provider.get_trust_bundle("partner.com")
```

---

##### create_tls_context()

Create an SSL context configured for mTLS.

```python
async def create_tls_context(self, server: bool = False) -> ssl.SSLContext
```

The SSL context will be configured with:
- Current SVID certificate and private key
- Trust bundle for peer verification
- TLS 1.3 minimum version (or as configured)
- Mutual authentication enabled
- Hostname checking disabled (SPIFFE uses SPIFFE ID verification)

**Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `server` | `bool` | If True, create a server-side SSL context. If False, create a client-side context. | `False` |

**Returns:**
- `ssl.SSLContext`: Configured SSL context ready for use

**Raises:**
- `IdentityError`: If SSL context cannot be created

**Example:**

```python
# Client context
client_ctx = await provider.create_tls_context(server=False)

# Server context
server_ctx = await provider.create_tls_context(server=True)
```

---

##### health_check()

Check if the identity provider is healthy.

```python
async def health_check(self) -> bool
```

This method verifies that the provider can obtain identity and trust bundles. It's useful for readiness probes.

**Returns:**
- `bool`: True if healthy, False otherwise

**Example:**

```python
if await provider.health_check():
    print("Identity provider is healthy")
else:
    print("Identity provider is unhealthy")
```

---

### SPIFFEIdentityProvider

SPIFFE Workload API-based identity provider implementation.

```python
class SPIFFEIdentityProvider(IdentityProvider):
    """SPIFFE Workload API-based identity provider."""
```

This provider connects to a SPIRE agent (or other SPIFFE Workload API implementation) to obtain X.509 SVIDs for workload identity. It handles:
- Automatic SVID fetching and caching
- Certificate rotation with callbacks
- Trust bundle management for multiple trust domains
- mTLS SSL context creation

The provider will automatically watch for SVID updates and invoke registered callbacks when rotation occurs.

#### Constructor

```python
def __init__(
    self,
    endpoint: Optional[str] = None,
    tls_min_version: ssl.TLSVersion = ssl.TLSVersion.TLSv1_3,
)
```

**Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `endpoint` | `Optional[str]` | The SPIFFE Workload API endpoint. If None, will use the `SPIFFE_ENDPOINT_SOCKET` environment variable, or default to `unix:///run/spire/sockets/agent.sock` | `None` |
| `tls_min_version` | `ssl.TLSVersion` | Minimum TLS version for SSL contexts. | `ssl.TLSVersion.TLSv1_3` |

**Example:**

```python
import ssl
from agentweave.identity import SPIFFEIdentityProvider

# Use default endpoint
provider = SPIFFEIdentityProvider()

# Use custom endpoint
provider = SPIFFEIdentityProvider(
    endpoint="unix:///custom/path/agent.sock"
)

# Use TLS 1.2 minimum
provider = SPIFFEIdentityProvider(
    tls_min_version=ssl.TLSVersion.TLSv1_2
)
```

#### Methods

##### initialize()

Initialize the connection to the SPIFFE Workload API.

```python
async def initialize(self) -> None
```

This method must be called before using the provider. It establishes the connection to the SPIRE agent and fetches the initial SVID.

**Raises:**
- `ConnectionError`: If connection to Workload API fails
- `IdentityError`: If initial SVID cannot be fetched

**Example:**

```python
provider = SPIFFEIdentityProvider()
await provider.initialize()
```

---

##### shutdown()

Shutdown the identity provider and cleanup resources.

```python
async def shutdown(self) -> None
```

This cancels the SVID watch task and cleans up temporary files.

**Example:**

```python
await provider.shutdown()
```

---

##### register_rotation_callback()

Register a callback to be invoked when SVID rotates.

```python
def register_rotation_callback(
    self,
    callback: Callable[[X509Svid], Awaitable[None]]
) -> None
```

The callback will be called with the new SVID whenever automatic rotation occurs. This is useful for updating SSL contexts or notifying other components.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `callback` | `Callable[[X509Svid], Awaitable[None]]` | Async function that takes an X509Svid parameter |

**Example:**

```python
async def on_svid_rotation(new_svid: X509Svid):
    print(f"SVID rotated: {new_svid.spiffe_id}")
    print(f"New expiration: {new_svid.leaf.not_valid_after_utc}")
    # Update TLS contexts, etc.

provider.register_rotation_callback(on_svid_rotation)
```

---

##### get_identity()

Get the SPIFFE ID of this workload.

```python
async def get_identity(self) -> str
```

**Returns:**
- `str`: The SPIFFE ID in the format `spiffe://trust-domain/path`

**Raises:**
- `IdentityError`: If identity cannot be determined or provider not initialized

**Example:**

```python
identity = await provider.get_identity()
print(identity)  # spiffe://agentweave.io/agent/search/prod
```

---

##### get_svid()

Get the current X.509 SVID for this workload.

```python
async def get_svid(self) -> X509Svid
```

Returns a cached SVID if available, or fetches a new one. The SVID is automatically rotated when it approaches expiration.

**Returns:**
- `X509Svid`: The X.509 SVID containing certificate and private key

**Raises:**
- `IdentityError`: If SVID cannot be obtained or provider not initialized

**Example:**

```python
svid = await provider.get_svid()
print(f"Certificate chain length: {len(svid.cert_chain())}")
```

---

##### get_trust_bundle()

Get the trust bundle for verifying peer SVIDs.

```python
async def get_trust_bundle(self, trust_domain: Optional[str] = None) -> X509Bundle
```

**Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `trust_domain` | `Optional[str]` | The trust domain to get the bundle for. If None, returns the bundle for this workload's trust domain. | `None` |

**Returns:**
- `X509Bundle`: The trust bundle containing CA certificates

**Raises:**
- `IdentityError`: If trust bundle cannot be obtained or provider not initialized
- `TrustDomainError`: If the trust domain is not recognized

**Example:**

```python
# Get our own trust bundle
bundle = await provider.get_trust_bundle()

# Get trust bundle for federated domain
partner_bundle = await provider.get_trust_bundle("partner.agentweave.io")
```

---

##### create_tls_context()

Create an SSL context configured for mTLS.

```python
async def create_tls_context(self, server: bool = False) -> ssl.SSLContext
```

The context is configured with:
- Current SVID certificate and private key
- Trust bundle for peer verification
- TLS 1.3 minimum version (configurable)
- Mutual authentication enabled
- Hostname checking disabled (SPIFFE uses SPIFFE ID verification)

**Parameters:**

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `server` | `bool` | If True, create a server-side SSL context. If False, create a client-side context. | `False` |

**Returns:**
- `ssl.SSLContext`: Configured SSL context ready for use

**Raises:**
- `IdentityError`: If SSL context cannot be created or provider not initialized

**Example:**

```python
# Create client context for making requests
client_ctx = await provider.create_tls_context(server=False)

# Create server context for accepting connections
server_ctx = await provider.create_tls_context(server=True)
```

---

##### health_check()

Check if the identity provider is healthy.

```python
async def health_check(self) -> bool
```

**Returns:**
- `bool`: True if healthy and initialized, False otherwise

**Example:**

```python
if await provider.health_check():
    await agent.start()
else:
    logger.error("Identity provider unhealthy, cannot start agent")
```

---

## Usage Examples

### Basic Usage

```python
from agentweave.identity import SPIFFEIdentityProvider

# Create and initialize provider
provider = SPIFFEIdentityProvider()
await provider.initialize()

try:
    # Get identity information
    identity = await provider.get_identity()
    print(f"My identity: {identity}")

    # Get SVID for certificate details
    svid = await provider.get_svid()
    print(f"Certificate expires: {svid.leaf.not_valid_after_utc}")

    # Create TLS context for secure communication
    tls_ctx = await provider.create_tls_context(server=False)

finally:
    await provider.shutdown()
```

### Context Manager Pattern

```python
from agentweave.identity import SPIFFEIdentityProvider

async def main():
    provider = SPIFFEIdentityProvider(
        endpoint="unix:///run/spire/sockets/agent.sock"
    )

    await provider.initialize()
    try:
        identity = await provider.get_identity()
        print(f"Identity: {identity}")
    finally:
        await provider.shutdown()
```

### SVID Rotation Handling

```python
from agentweave.identity import SPIFFEIdentityProvider
from spiffe import X509Svid
import logging

logger = logging.getLogger(__name__)

async def handle_rotation(new_svid: X509Svid):
    """Handle SVID rotation by updating SSL contexts."""
    logger.info(f"SVID rotated for {new_svid.spiffe_id}")
    logger.info(f"New expiration: {new_svid.leaf.not_valid_after_utc}")

    # Update TLS contexts, reconnect clients, etc.
    await update_tls_contexts(new_svid)

# Register callback
provider = SPIFFEIdentityProvider()
provider.register_rotation_callback(handle_rotation)
await provider.initialize()
```

### Multi-Trust Domain Setup

```python
from agentweave.identity import SPIFFEIdentityProvider

provider = SPIFFEIdentityProvider()
await provider.initialize()

# Get our own trust domain bundle
our_bundle = await provider.get_trust_bundle()

# Get federated trust domain bundles
partner_bundle = await provider.get_trust_bundle("partner.agentweave.io")
customer_bundle = await provider.get_trust_bundle("customer.example.com")

print(f"Our trust domain: {our_bundle.trust_domain}")
print(f"Partner trust domain: {partner_bundle.trust_domain}")
```

### Health Monitoring

```python
from agentweave.identity import SPIFFEIdentityProvider
import asyncio

async def monitor_health(provider: SPIFFEIdentityProvider):
    """Periodically check identity provider health."""
    while True:
        is_healthy = await provider.health_check()
        if not is_healthy:
            logger.error("Identity provider unhealthy!")
            # Trigger alerts, circuit breakers, etc.

        await asyncio.sleep(30)  # Check every 30 seconds

provider = SPIFFEIdentityProvider()
await provider.initialize()

# Start health monitoring in background
asyncio.create_task(monitor_health(provider))
```

---

## Exceptions

### IdentityError

Base exception for identity-related errors.

```python
class IdentityError(Exception):
    """Base exception for identity-related errors."""
```

**Usage:**

```python
from agentweave.identity import IdentityError

try:
    svid = await provider.get_svid()
except IdentityError as e:
    logger.error(f"Failed to get SVID: {e}")
```

---

### TrustDomainError

Exception raised when a trust domain is not recognized or trusted.

```python
class TrustDomainError(IdentityError):
    """Exception raised when a trust domain is not recognized or trusted."""
```

**Usage:**

```python
from agentweave.identity import TrustDomainError

try:
    bundle = await provider.get_trust_bundle("unknown-domain.com")
except TrustDomainError as e:
    logger.error(f"Trust domain not found: {e}")
```

---

### SVIDExpiredError

Exception raised when an SVID has expired and cannot be renewed.

```python
class SVIDExpiredError(IdentityError):
    """Exception raised when an SVID has expired and cannot be renewed."""
```

**Usage:**

```python
from agentweave.identity import SVIDExpiredError

try:
    svid = await provider.get_svid()
except SVIDExpiredError as e:
    logger.critical(f"SVID expired and rotation failed: {e}")
    # Trigger emergency shutdown
```

---

### ConnectionError

Exception raised when connection to identity provider fails.

```python
class ConnectionError(IdentityError):
    """Exception raised when connection to identity provider fails."""
```

**Usage:**

```python
from agentweave.identity import ConnectionError

try:
    await provider.initialize()
except ConnectionError as e:
    logger.error(f"Cannot connect to SPIRE agent: {e}")
    # Check that SPIRE agent is running
```

---

## Best Practices

### 1. Always Initialize Before Use

```python
provider = SPIFFEIdentityProvider()
await provider.initialize()  # Required!
```

### 2. Handle Cleanup Properly

```python
try:
    await provider.initialize()
    # Use provider
finally:
    await provider.shutdown()
```

### 3. Monitor SVID Expiration

```python
svid = await provider.get_svid()
time_until_expiry = svid.leaf.not_valid_after_utc - datetime.utcnow()
if time_until_expiry < timedelta(hours=1):
    logger.warning("SVID expires soon!")
```

### 4. Register Rotation Callbacks Early

```python
provider = SPIFFEIdentityProvider()
provider.register_rotation_callback(handle_rotation)
await provider.initialize()
```

### 5. Use Health Checks

```python
# In Kubernetes readiness probe
async def readiness():
    return await identity_provider.health_check()
```

---

## See Also

- [Authorization Module](authz.md) - Policy-based access control
- [Security Guide](../security.md) - Security architecture and best practices
- [SPIFFE/SPIRE Documentation](https://spiffe.io/docs/) - Official SPIFFE documentation
