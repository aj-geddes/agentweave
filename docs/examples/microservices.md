---
layout: page
title: Microservices Pattern
permalink: /examples/microservices/
parent: Examples Overview
nav_order: 5
---

# Microservices Pattern Example

**Complexity:** Intermediate
**Time to Complete:** 45 minutes
**Prerequisites:** Understanding of microservices architecture

This example demonstrates converting traditional HTTP/REST microservices to secure AgentWeave agents. We'll build an e-commerce system with User, Order, and Payment services, comparing the traditional approach with the AgentWeave pattern.

## What You'll Learn

- Converting microservices to secure agents
- Service-to-service communication patterns
- Comparison with service mesh (Istio, Linkerd)
- API gateway agent pattern
- Service discovery
- Benefits of agent-based architecture

## Traditional vs AgentWeave Architecture

### Traditional Microservices (Without Service Mesh)

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────┐
│ API Gateway │
└──────┬──────┘
       │ HTTP (insecure)
       ├────────────┬───────────┬─────────────┐
       │            │           │             │
       ▼            ▼           ▼             ▼
  ┌────────┐  ┌─────────┐  ┌────────┐  ┌──────────┐
  │  User  │  │  Order  │  │Payment │  │Inventory │
  │Service │  │ Service │  │Service │  │ Service  │
  └────────┘  └─────────┘  └────────┘  └──────────┘

Issues:
- No mutual TLS between services
- Manual auth token passing
- No fine-grained authorization
- Poor observability
- Complex service discovery
```

### With Service Mesh (Istio)

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────┐
│ API Gateway │
└──────┬──────┘
       │
       ├────────────┬───────────┬─────────────┐
       │            │           │             │
       ▼            ▼           ▼             ▼
  ┌────────┐  ┌─────────┐  ┌────────┐  ┌──────────┐
  │  User  │  │  Order  │  │Payment │  │Inventory │
  │+Envoy  │  │ +Envoy  │  │+Envoy  │  │  +Envoy  │
  └────────┘  └─────────┘  └────────┘  └──────────┘

Better but:
- Complex Envoy configuration
- Separate control plane (Istiod)
- Policy in Envoy config, not code
- Still application-level auth issues
```

### With AgentWeave

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ mTLS (SPIFFE)
       ▼
┌─────────────────┐
│  Gateway Agent  │
│  (SPIFFE ID)    │
└────────┬────────┘
         │ All calls use:
         │ - mTLS with SPIFFE
         │ - OPA authorization
         │ - A2A protocol
         ├────────────┬───────────┬─────────────┐
         │            │           │             │
         ▼            ▼           ▼             ▼
    ┌────────┐  ┌─────────┐  ┌────────┐  ┌──────────┐
    │  User  │  │  Order  │  │Payment │  │Inventory │
    │ Agent  │  │  Agent  │  │ Agent  │  │  Agent   │
    └────────┘  └─────────┘  └────────┘  └──────────┘

Benefits:
- No sidecar needed
- Identity + authorization in SDK
- Policy as code (Rego)
- Built-in observability
- Simple service discovery
```

## Scenario: E-Commerce System

**Services (Agents)**:
- **User Agent**: User registration, authentication, profile management
- **Order Agent**: Create/manage orders, order history
- **Payment Agent**: Process payments, refunds
- **Inventory Agent**: Stock management, availability checks
- **Gateway Agent**: Public API, request routing

## Complete Code

### User Agent

```python
# user_agent.py
"""
User Agent - Manages user accounts and authentication.

Traditional Equivalent: User Microservice
Port: 8080 (HTTP) → 8443 (HTTPS + mTLS)
"""

import asyncio
from typing import Dict, Any, Optional
from pydantic import BaseModel, EmailStr

from agentweave import SecureAgent, capability
from agentweave.types import TaskResult, Message, DataPart


class User(BaseModel):
    """User model."""
    user_id: str
    email: EmailStr
    name: str
    tier: str = "free"  # free, premium, enterprise


class UserAgent(SecureAgent):
    """Manages user accounts."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._users: Dict[str, User] = {}  # In production, use database

    @capability("create_user")
    async def create_user(
        self,
        email: str,
        name: str,
        tier: str = "free"
    ) -> TaskResult:
        """
        Create new user account.

        In traditional microservice:
        - POST /api/v1/users
        - Manual JWT validation
        - Application-level authorization

        With AgentWeave:
        - Caller identity verified by SDK (SPIFFE)
        - OPA policy checked automatically
        - No manual auth code needed
        """
        import uuid

        user_id = str(uuid.uuid4())
        user = User(
            user_id=user_id,
            email=email,
            name=name,
            tier=tier
        )

        self._users[user_id] = user

        self.logger.info(
            "User created",
            extra={
                "user_id": user_id,
                "caller": self.context.caller_spiffe_id
            }
        )

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data=user.dict())]
            )]
        )

    @capability("get_user")
    async def get_user(self, user_id: str) -> TaskResult:
        """
        Get user by ID.

        Traditional: GET /api/v1/users/{user_id}
        """
        user = self._users.get(user_id)

        if not user:
            return TaskResult(
                status="failed",
                error=f"User {user_id} not found"
            )

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data=user.dict())]
            )]
        )

    @capability("update_tier")
    async def update_tier(
        self,
        user_id: str,
        new_tier: str
    ) -> TaskResult:
        """
        Update user tier (admin only).

        Traditional: PATCH /api/v1/users/{user_id}/tier
        Required: Admin JWT token

        AgentWeave: OPA policy ensures only admin agents can call this
        """
        user = self._users.get(user_id)

        if not user:
            return TaskResult(
                status="failed",
                error=f"User {user_id} not found"
            )

        user.tier = new_tier
        self._users[user_id] = user

        self.logger.info(
            "User tier updated",
            extra={
                "user_id": user_id,
                "new_tier": new_tier,
                "caller": self.context.caller_spiffe_id
            }
        )

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data=user.dict())]
            )]
        )


async def main():
    agent = UserAgent.from_config("config/user.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Order Agent

```python
# order_agent.py
"""
Order Agent - Manages customer orders.

Calls: User Agent, Payment Agent, Inventory Agent
"""

import asyncio
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime

from agentweave import SecureAgent, capability
from agentweave.types import TaskResult, Message, DataPart
from agentweave.exceptions import AgentCallError


class OrderAgent(SecureAgent):
    """Manages customer orders."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Agent dependencies
        self.user_agent = "spiffe://agentweave.io/agent/user"
        self.payment_agent = "spiffe://agentweave.io/agent/payment"
        self.inventory_agent = "spiffe://agentweave.io/agent/inventory"

        self._orders: Dict[str, Dict] = {}

    @capability("create_order")
    async def create_order(
        self,
        user_id: str,
        items: List[Dict[str, Any]],
        payment_method: str
    ) -> TaskResult:
        """
        Create new order.

        Workflow:
        1. Verify user exists (call User Agent)
        2. Check inventory (call Inventory Agent)
        3. Process payment (call Payment Agent)
        4. Create order
        5. Update inventory

        Traditional microservices:
        - 5 HTTP calls with manual auth
        - Complex error handling
        - No built-in retries

        AgentWeave:
        - 5 agent calls with automatic mTLS
        - OPA policies enforce permissions
        - Built-in retries, circuit breakers
        - Distributed tracing included
        """
        import uuid

        order_id = str(uuid.uuid4())

        self.logger.info(
            "Creating order",
            extra={
                "order_id": order_id,
                "user_id": user_id,
                "items_count": len(items)
            }
        )

        try:
            # Step 1: Verify user
            user_result = await self.call_agent(
                target=self.user_agent,
                task_type="get_user",
                payload={"user_id": user_id}
            )

            if user_result.status != "completed":
                raise AgentCallError(f"User not found: {user_id}")

            user = user_result.artifacts[0]["data"]

            # Step 2: Check inventory availability
            inventory_result = await self.call_agent(
                target=self.inventory_agent,
                task_type="check_availability",
                payload={"items": items}
            )

            if inventory_result.status != "completed":
                raise AgentCallError("Items not available")

            # Step 3: Calculate total
            total = self._calculate_total(items)

            # Step 4: Process payment
            payment_result = await self.call_agent(
                target=self.payment_agent,
                task_type="process_payment",
                payload={
                    "user_id": user_id,
                    "amount": str(total),
                    "payment_method": payment_method,
                    "order_id": order_id
                }
            )

            if payment_result.status != "completed":
                raise AgentCallError("Payment failed")

            payment_data = payment_result.artifacts[0]["data"]

            # Step 5: Reserve inventory
            await self.call_agent(
                target=self.inventory_agent,
                task_type="reserve_items",
                payload={"order_id": order_id, "items": items}
            )

            # Step 6: Create order record
            order = {
                "order_id": order_id,
                "user_id": user_id,
                "items": items,
                "total": str(total),
                "payment_method": payment_method,
                "transaction_id": payment_data["transaction_id"],
                "status": "confirmed",
                "created_at": datetime.utcnow().isoformat()
            }

            self._orders[order_id] = order

            return TaskResult(
                status="completed",
                messages=[Message(
                    role="assistant",
                    parts=[DataPart(data=order)]
                )]
            )

        except AgentCallError as e:
            self.logger.error(f"Order creation failed: {e}")
            # In production, implement compensating transactions
            return TaskResult(
                status="failed",
                error=f"Failed to create order: {e}"
            )

    @capability("get_order")
    async def get_order(self, order_id: str) -> TaskResult:
        """Get order by ID."""
        order = self._orders.get(order_id)

        if not order:
            return TaskResult(
                status="failed",
                error=f"Order {order_id} not found"
            )

        return TaskResult(
            status="completed",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data=order)]
            )]
        )

    def _calculate_total(self, items: List[Dict[str, Any]]) -> Decimal:
        """Calculate order total."""
        total = Decimal("0")
        for item in items:
            price = Decimal(str(item["price"]))
            quantity = item["quantity"]
            total += price * quantity
        return total


async def main():
    agent = OrderAgent.from_config("config/order.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

### Gateway Agent

```python
# gateway_agent.py
"""
Gateway Agent - Public-facing API gateway.

Traditional: Kong, NGINX, AWS API Gateway
AgentWeave: Secure agent with routing logic
"""

import asyncio
from typing import Dict, Any

from agentweave import SecureAgent, capability
from agentweave.types import TaskResult
from agentweave.exceptions import AgentCallError


class GatewayAgent(SecureAgent):
    """
    API Gateway implemented as an agent.

    Benefits over traditional gateway:
    - No separate gateway configuration
    - Routing logic in Python (testable)
    - Same security model as other agents
    - Built-in observability
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Service registry
        self.services = {
            "user": "spiffe://agentweave.io/agent/user",
            "order": "spiffe://agentweave.io/agent/order",
            "payment": "spiffe://agentweave.io/agent/payment",
            "inventory": "spiffe://agentweave.io/agent/inventory"
        }

    @capability("route")
    async def route(
        self,
        service: str,
        action: str,
        payload: Dict[str, Any]
    ) -> TaskResult:
        """
        Route request to appropriate service.

        Traditional API Gateway:
        - Complex YAML/JSON configuration
        - Limited routing logic
        - Manual auth integration

        AgentWeave Gateway:
        - Python routing logic
        - Automatic mTLS to services
        - Type-safe payloads
        """
        target = self.services.get(service)

        if not target:
            return TaskResult(
                status="failed",
                error=f"Service {service} not found"
            )

        self.logger.info(
            "Routing request",
            extra={
                "service": service,
                "action": action,
                "target": target
            }
        )

        try:
            result = await self.call_agent(
                target=target,
                task_type=action,
                payload=payload,
                timeout=30.0
            )

            return result

        except AgentCallError as e:
            self.logger.error(f"Routing failed: {e}")
            return TaskResult(
                status="failed",
                error=f"Service call failed: {e}"
            )

    @capability("health")
    async def health(self) -> TaskResult:
        """
        Health check all services.

        Returns status of all backend services.
        """
        results = {}

        for service_name, service_id in self.services.items():
            try:
                # Try to call health endpoint with short timeout
                result = await self.call_agent(
                    target=service_id,
                    task_type="health",
                    payload={},
                    timeout=5.0
                )
                results[service_name] = "healthy" if result.status == "completed" else "unhealthy"
            except Exception as e:
                results[service_name] = f"unhealthy: {e}"

        all_healthy = all(status == "healthy" for status in results.values())

        return TaskResult(
            status="completed" if all_healthy else "degraded",
            messages=[Message(
                role="assistant",
                parts=[DataPart(data={
                    "gateway": "healthy",
                    "services": results
                })]
            )]
        )


async def main():
    agent = GatewayAgent.from_config("config/gateway.yaml")
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
```

## Authorization Policies

### Gateway Policy

```rego
# policies/gateway_authz.rego
package gateway.authz

import rego.v1

default allow := false

# Gateway can call any internal service
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/gateway"
    startswith(input.callee_spiffe_id, "spiffe://agentweave.io/agent/")
}

# External clients can call gateway
allow if {
    startswith(input.caller_spiffe_id, "spiffe://agentweave.io/client/")
    input.callee_spiffe_id == "spiffe://agentweave.io/agent/gateway"
    input.action in ["route", "health"]
}
```

### Order Agent Policy

```rego
# policies/order_authz.rego
package order.authz

import rego.v1

default allow := false

# Gateway can call order agent
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/gateway"
    input.callee_spiffe_id == "spiffe://agentweave.io/agent/order"
    input.action in ["create_order", "get_order"]
}

# Order agent can call user, payment, inventory
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/order"
    input.callee_spiffe_id in [
        "spiffe://agentweave.io/agent/user",
        "spiffe://agentweave.io/agent/payment",
        "spiffe://agentweave.io/agent/inventory"
    ]
}
```

### User Agent Policy

```rego
# policies/user_authz.rego
package user.authz

import rego.v1

default allow := false

# Gateway can call user agent for create/get
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/gateway"
    input.action in ["create_user", "get_user"]
}

# Order agent can get users
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/order"
    input.action == "get_user"
}

# Only admin agent can update tiers
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/admin"
    input.action == "update_tier"
}
```

## Docker Compose

```yaml
# docker-compose.yaml
version: '3.8'

services:
  # Infrastructure (SPIRE, OPA)
  spire-server:
    # ... (same as other examples)

  spire-agent:
    # ... (same as other examples)

  opa:
    # ... (same as other examples)

  # Database
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: ecommerce
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app

  # Service Agents
  gateway:
    build: .
    command: python gateway_agent.py
    ports:
      - "8443:8443"
    environment:
      - AGENTWEAVE_CONFIG=/config/gateway.yaml

  user:
    build: .
    command: python user_agent.py
    ports:
      - "8444:8443"
    environment:
      - AGENTWEAVE_CONFIG=/config/user.yaml

  order:
    build: .
    command: python order_agent.py
    ports:
      - "8445:8443"
    environment:
      - AGENTWEAVE_CONFIG=/config/order.yaml

  payment:
    build: .
    command: python payment_agent.py
    ports:
      - "8446:8443"
    environment:
      - AGENTWEAVE_CONFIG=/config/payment.yaml

  inventory:
    build: .
    command: python inventory_agent.py
    ports:
      - "8447:8443"
    environment:
      - AGENTWEAVE_CONFIG=/config/inventory.yaml
```

## Comparison Table

| Aspect | Traditional | Service Mesh | AgentWeave |
|--------|-------------|--------------|------------|
| **mTLS** | Manual (cert management) | Automatic (via Envoy) | Automatic (SPIFFE SDK) |
| **Authorization** | Application code + JWT | Envoy + external authz | OPA + SDK (built-in) |
| **Service Discovery** | DNS, Consul, etc. | K8s service + Envoy | SPIFFE ID (explicit) |
| **Observability** | Manual instrumentation | Envoy metrics + sidecar | SDK built-in |
| **Configuration** | Per-service | Centralized YAML | Code + Config |
| **Sidecars** | None (insecure) or manual | Required (Envoy) | None (SDK handles it) |
| **Policy Language** | Application code | Envoy config | Rego (testable) |
| **Complexity** | Low (but insecure) | High (Istio/Linkerd) | Medium (SDK) |

## Running the Example

```bash
# Start all services
docker-compose up -d

# Register all agents with SPIRE
for svc in gateway user order payment inventory; do
    docker-compose exec spire-server \
        /opt/spire/bin/spire-server entry create \
        -spiffeID spiffe://agentweave.io/agent/$svc \
        -parentID spiffe://agentweave.io/agent/spire-agent \
        -selector docker:label:com.docker.compose.service:$svc
done

# Test: Create user
agentweave call \
    --target spiffe://agentweave.io/agent/gateway \
    --capability route \
    --data '{
        "service": "user",
        "action": "create_user",
        "payload": {
            "email": "user@example.com",
            "name": "John Doe",
            "tier": "premium"
        }
    }'

# Test: Create order (calls user, payment, inventory)
agentweave call \
    --target spiffe://agentweave.io/agent/gateway \
    --capability route \
    --data '{
        "service": "order",
        "action": "create_order",
        "payload": {
            "user_id": "<user-id-from-above>",
            "items": [
                {"sku": "WIDGET-001", "quantity": 2, "price": "19.99"}
            ],
            "payment_method": "credit_card"
        }
    }'
```

## Key Takeaways

### No Sidecar Required

Traditional service mesh:
```
┌──────────────────┐
│  Order Service   │
│  ┌────────────┐  │
│  │   App      │  │
│  └─────┬──────┘  │
│        │         │
│  ┌─────▼──────┐  │
│  │   Envoy    │◄─┼─ Complexity
│  └────────────┘  │
└──────────────────┘
```

AgentWeave:
```
┌──────────────────┐
│  Order Agent     │
│  (SDK handles    │
│   mTLS, authz)   │
└──────────────────┘
```

### Policy as Code

Service mesh (YAML):
```yaml
apiVersion: security.istio.io/v1beta1
kind: AuthorizationPolicy
metadata:
  name: order-policy
spec:
  selector:
    matchLabels:
      app: order
  rules:
  - from:
    - source:
        principals: ["cluster.local/ns/default/sa/gateway"]
```

AgentWeave (Rego):
```rego
allow if {
    input.caller_spiffe_id == "spiffe://agentweave.io/agent/gateway"
    input.action == "create_order"
}
```

### Built-in Observability

No manual instrumentation needed:

```python
# This automatically creates traces, metrics, logs
result = await self.call_agent(
    target=self.payment_agent,
    task_type="process_payment",
    payload={...}
)
```

## Next Steps

- **Production Deployment**: See [Kubernetes Guide](/deployment/kubernetes/)
- **Advanced Patterns**: Saga pattern for distributed transactions
- **Monitoring**: Set up Grafana dashboards for agent metrics
- **Security**: Learn [Security Best Practices](/security/best-practices/)

---

**Complete Code**: [GitHub Repository](https://github.com/aj-geddes/agentweave/tree/main/examples/microservices)
