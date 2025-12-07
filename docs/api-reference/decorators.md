---
layout: api
title: Decorators Module
parent: API Reference
nav_order: 3
---

# Decorators Module

The decorators module (`agentweave.decorators`) provides security decorators that enable declarative security controls on agent methods, including capability registration, peer verification, and audit logging.

## Decorators

### @capability

```python
def capability(name: str, description: Optional[str] = None)
```

Decorator to register a method as an agent capability.

This decorator:
- Registers the method in the capability registry
- Auto-generates capability metadata
- Wraps the method with authorization checks

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | *required* | The name of the capability |
| `description` | `str` | `None` | Optional description (defaults to method docstring) |

**Usage:**

```python
from agentweave import SecureAgent, capability

class DataAgent(SecureAgent):
    @capability("search", description="Search the database")
    async def search(self, query: str) -> dict:
        return {"results": [...]}
```

**Notes:**

- The decorated method must be async
- The method is automatically discovered by `SecureAgent.register_capabilities()`
- Authorization checks are performed automatically when the capability is invoked
- The capability name should be lowercase with underscores (validated by `Capability` model)

**Example with Multiple Capabilities:**

```python
class DataAgent(SecureAgent):
    @capability("search", description="Search the database")
    async def search(self, query: str) -> dict:
        return {"results": [...]}

    @capability("process", description="Process data")
    async def process(self, data: dict) -> dict:
        return {"status": "processed"}

    @capability("aggregate", description="Aggregate results")
    async def aggregate(self, items: list) -> dict:
        return {"total": sum(items)}
```

---

### @requires_peer

```python
def requires_peer(spiffe_pattern: str)
```

Decorator to restrict a capability to specific SPIFFE ID patterns.

This decorator enforces that only callers matching the given SPIFFE ID pattern can invoke the capability. Supports wildcards using fnmatch syntax.

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `spiffe_pattern` | `str` | SPIFFE ID pattern (e.g., `"spiffe://domain/agent/*"`) |

**Pattern Syntax:**

- `*` - Matches any sequence of characters
- `?` - Matches any single character
- `[seq]` - Matches any character in seq
- `[!seq]` - Matches any character not in seq

**Usage:**

```python
from agentweave import SecureAgent, capability, requires_peer

class SecureDataAgent(SecureAgent):
    @capability("search")
    @requires_peer("spiffe://agentweave.io/agent/*")
    async def search(self, query: str) -> dict:
        # Only agents in agentweave.io trust domain can call this
        return {"results": [...]}

    @capability("delete_data")
    @requires_peer("spiffe://agentweave.io/agent/admin-*")
    async def delete_data(self, id: str) -> dict:
        # Only admin agents can call this
        return {"deleted": id}
```

**Stacking Order:**

This decorator should be used in combination with `@capability` and placed **after** it in the decorator stack:

```python
@capability("delete_data")        # First
@requires_peer("spiffe://...")    # Second
async def delete_data(self, id: str) -> dict:
    pass
```

**Raises:**

| Exception | Description |
|-----------|-------------|
| `PermissionError` | If caller's SPIFFE ID doesn't match the pattern |
| `PermissionError` | If no request context is available |

**Examples:**

```python
# Allow any agent in the trust domain
@capability("public_data")
@requires_peer("spiffe://agentweave.io/agent/*")
async def get_public_data(self) -> dict:
    return {"data": "public"}

# Allow only specific agent
@capability("admin_action")
@requires_peer("spiffe://agentweave.io/agent/admin")
async def admin_action(self) -> dict:
    return {"status": "ok"}

# Allow agents with specific prefix
@capability("worker_task")
@requires_peer("spiffe://agentweave.io/agent/worker-*")
async def worker_task(self, task: dict) -> dict:
    return {"result": "processed"}

# Allow multiple patterns (stack multiple decorators)
@capability("cross_domain")
@requires_peer("spiffe://agentweave.io/agent/*")
@requires_peer("spiffe://partner.io/agent/*")
async def cross_domain_task(self) -> dict:
    return {"status": "ok"}
```

---

### @audit_log

```python
def audit_log(level: str = "info")
```

Decorator to enforce audit logging for capability calls.

This decorator logs:
- Caller identity
- Action (capability name)
- Result (success/failure)
- Timing information

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `level` | `str` | `"info"` | Logging level (`"debug"`, `"info"`, `"warning"`, `"error"`) |

**Usage:**

```python
from agentweave import SecureAgent, capability, audit_log

class AuditedAgent(SecureAgent):
    @capability("delete_data")
    @audit_log(level="warning")
    async def delete_data(self, id: str) -> dict:
        # This call will be audit logged at WARNING level
        return {"deleted": id}

    @capability("sensitive_operation")
    @audit_log(level="error")
    async def sensitive_operation(self) -> dict:
        # Critical operations logged at ERROR level
        return {"status": "completed"}
```

**Audit Log Format:**

```python
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "caller": "spiffe://agentweave.io/agent/caller-agent",
    "action": "delete_data",
    "success": True,
    "duration_ms": 123.45
}

# On error:
{
    "task_id": "550e8400-e29b-41d4-a716-446655440000",
    "caller": "spiffe://agentweave.io/agent/caller-agent",
    "action": "delete_data",
    "success": False,
    "duration_ms": 45.67,
    "error": "Database connection failed"
}
```

**Stacking Order:**

This decorator can be stacked with `@capability` and `@requires_peer`:

```python
@capability("admin_delete")          # First
@requires_peer("spiffe://.../admin-*")  # Second
@audit_log(level="warning")          # Third
async def admin_delete(self, id: str) -> dict:
    pass
```

**Valid Levels:**

| Level | Use Case |
|-------|----------|
| `"debug"` | Development and troubleshooting |
| `"info"` | Normal operations (default) |
| `"warning"` | Sensitive operations (data modification) |
| `"error"` | Critical operations (security-relevant) |

**Raises:**

| Exception | Description |
|-----------|-------------|
| `ValueError` | If an invalid log level is provided |

**Examples:**

```python
# Standard audit logging
@capability("update_user")
@audit_log(level="info")
async def update_user(self, user_id: str, data: dict) -> dict:
    return {"updated": user_id}

# High-priority audit for sensitive operations
@capability("delete_user")
@audit_log(level="warning")
async def delete_user(self, user_id: str) -> dict:
    return {"deleted": user_id}

# Critical security operations
@capability("grant_admin_access")
@requires_peer("spiffe://agentweave.io/agent/security-admin")
@audit_log(level="error")
async def grant_admin_access(self, user_id: str) -> dict:
    return {"granted": user_id}
```

---

## Functions

### get_registered_capabilities

```python
def get_registered_capabilities() -> dict[str, CapabilityMetadata]
```

Get all registered capabilities.

**Returns:** `dict[str, CapabilityMetadata]` - Dictionary mapping capability names to their metadata

**Example:**

```python
from agentweave.decorators import get_registered_capabilities

# After defining capabilities
capabilities = get_registered_capabilities()
for name, metadata in capabilities.items():
    print(f"{name}: {metadata.description}")
```

**CapabilityMetadata Structure:**

```python
@dataclass
class CapabilityMetadata:
    name: str
    description: Optional[str]
    handler: Optional[Callable]
    requires_peer_patterns: list[str]
    audit_level: Optional[str]
```

---

### clear_capability_registry

```python
def clear_capability_registry() -> None
```

Clear the capability registry.

This is primarily useful for testing purposes to ensure a clean state between tests.

**Example:**

```python
from agentweave.decorators import clear_capability_registry

# In test teardown
def teardown():
    clear_capability_registry()
```

---

## Decorator Stacking

When using multiple decorators, follow this order:

```python
@capability("name", description="...")     # 1. Always first
@requires_peer("spiffe://...")             # 2. Peer verification
@audit_log(level="warning")                # 3. Audit logging
async def my_capability(self, ...) -> ...:
    pass
```

**Execution Order (when method is called):**

1. `@audit_log` - Start timing and setup audit
2. `@requires_peer` - Verify caller's SPIFFE ID
3. `@capability` - Check OPA authorization
4. **Method executes**
5. `@audit_log` - Log result and duration

---

## Complete Example

```python
from agentweave import SecureAgent, capability, requires_peer, audit_log

class DataManagementAgent(SecureAgent):
    """Agent for managing sensitive data with comprehensive security."""

    @capability("search", description="Search the database")
    @requires_peer("spiffe://agentweave.io/agent/*")
    async def search(self, query: str) -> dict:
        """Anyone in the trust domain can search."""
        results = await self._search_db(query)
        return {"results": results}

    @capability("update_data", description="Update existing data")
    @requires_peer("spiffe://agentweave.io/agent/editor-*")
    @audit_log(level="info")
    async def update_data(self, id: str, data: dict) -> dict:
        """Only editor agents can update data."""
        await self._update_db(id, data)
        return {"updated": id}

    @capability("delete_data", description="Delete sensitive data")
    @requires_peer("spiffe://agentweave.io/agent/admin-*")
    @audit_log(level="warning")
    async def delete_data(self, id: str) -> dict:
        """Only admin agents can delete data."""
        await self._delete_from_db(id)
        return {"deleted": id}

    @capability("grant_access", description="Grant access to data")
    @requires_peer("spiffe://agentweave.io/agent/security-admin")
    @audit_log(level="error")
    async def grant_access(self, user_id: str, resource_id: str) -> dict:
        """Only the security admin agent can grant access."""
        await self._grant_access_db(user_id, resource_id)
        return {"granted": True}

    # Helper methods (not capabilities)
    async def _search_db(self, query: str) -> list:
        return []

    async def _update_db(self, id: str, data: dict) -> None:
        pass

    async def _delete_from_db(self, id: str) -> None:
        pass

    async def _grant_access_db(self, user_id: str, resource_id: str) -> None:
        pass

# Run the agent
if __name__ == "__main__":
    agent = DataManagementAgent.from_config("config.yaml")
    agent.run()
```

---

## Best Practices

### 1. Always Use @capability First

```python
# Correct
@capability("search")
@requires_peer("spiffe://...")
async def search(self, query: str) -> dict:
    pass

# Incorrect - won't work properly
@requires_peer("spiffe://...")
@capability("search")
async def search(self, query: str) -> dict:
    pass
```

### 2. Use Descriptive Capability Names

```python
# Good
@capability("search_users", description="Search for users in the directory")
@capability("delete_expired_data", description="Delete data past retention period")

# Avoid
@capability("do_stuff", description="Does stuff")
@capability("x", description="Something")
```

### 3. Apply @audit_log to Sensitive Operations

```python
# Always audit data modifications
@capability("update_user")
@audit_log(level="info")
async def update_user(self, user_id: str, data: dict) -> dict:
    pass

# Always audit deletions
@capability("delete_user")
@audit_log(level="warning")
async def delete_user(self, user_id: str) -> dict:
    pass

# Always audit access grants
@capability("grant_admin")
@audit_log(level="error")
async def grant_admin(self, user_id: str) -> dict:
    pass
```

### 4. Use Specific SPIFFE Patterns

```python
# Good - specific patterns
@requires_peer("spiffe://agentweave.io/agent/admin-*")
@requires_peer("spiffe://agentweave.io/agent/data-processor")

# Avoid - too permissive
@requires_peer("spiffe://*")
@requires_peer("*")
```

---

## See Also

- [Agent Module](agent.md) - Agent classes and lifecycle
- [Context Module](context.md) - Request context management
- [Security Guide](../security.md) - Security best practices
