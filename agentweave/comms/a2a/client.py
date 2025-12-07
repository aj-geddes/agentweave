"""
A2A Protocol client implementation.

Provides client-side A2A protocol functionality for sending tasks,
polling status, and streaming results from remote agents.
"""

import json
import uuid
from typing import Optional, Dict, Any, AsyncIterator
import httpx
from httpx_sse import aconnect_sse

from agentweave.comms.a2a.card import AgentCard
from agentweave.comms.a2a.task import Task, TaskState, Message, MessagePart


class A2AClientError(Exception):
    """Base exception for A2A client errors."""
    pass


class TaskSubmissionError(A2AClientError):
    """Error submitting task to remote agent."""
    pass


class TaskStatusError(A2AClientError):
    """Error retrieving task status."""
    pass


class DiscoveryError(A2AClientError):
    """Error discovering agent card."""
    pass


class A2AClient:
    """
    Client for A2A protocol communication.

    Handles task submission, status polling, and streaming for agent-to-agent
    communication over HTTPS with JSON-RPC 2.0.
    """

    def __init__(
        self,
        identity_provider=None,
        authz_enforcer=None,
        timeout: float = 30.0,
        max_retries: int = 3
    ):
        """
        Initialize A2A client.

        Args:
            identity_provider: Identity provider for mTLS (optional for now)
            authz_enforcer: Authorization enforcer (optional for now)
            timeout: Default request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self._identity = identity_provider
        self._authz = authz_enforcer
        self._timeout = timeout
        self._max_retries = max_retries
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def _ensure_client(self) -> httpx.AsyncClient:
        """
        Ensure HTTP client is initialized.

        Returns:
            HTTP client instance
        """
        if self._http_client is None:
            # TODO: Add mTLS configuration when identity provider is available
            self._http_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                follow_redirects=True,
                # verify=True,  # Enable TLS verification
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client and cleanup resources."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def discover_agent(self, url: str) -> AgentCard:
        """
        Discover agent by fetching its agent card.

        Args:
            url: Base URL of the agent

        Returns:
            AgentCard for the discovered agent

        Raises:
            DiscoveryError: If agent card cannot be retrieved
        """
        client = await self._ensure_client()

        # Normalize URL
        base_url = url.rstrip('/')
        card_url = f"{base_url}/.well-known/agent.json"

        try:
            response = await client.get(card_url)
            response.raise_for_status()

            card_data = response.json()
            return AgentCard.from_dict(card_data)

        except httpx.HTTPError as e:
            raise DiscoveryError(f"Failed to discover agent at {url}: {e}") from e
        except (json.JSONDecodeError, ValueError) as e:
            raise DiscoveryError(f"Invalid agent card format: {e}") from e

    async def send_task(
        self,
        target_url: str,
        task_type: str,
        payload: Dict[str, Any],
        messages: Optional[list] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[float] = None
    ) -> Task:
        """
        Send a task to a remote agent.

        Args:
            target_url: Base URL of target agent
            task_type: Type of task/capability to invoke
            payload: Task payload data
            messages: Optional message history
            metadata: Optional task metadata
            timeout: Optional timeout override

        Returns:
            Task with initial response

        Raises:
            TaskSubmissionError: If task submission fails
        """
        client = await self._ensure_client()

        # TODO: Check authorization if enforcer is available
        # if self._authz:
        #     decision = await self._authz.check_outbound(...)
        #     if not decision.allowed:
        #         raise TaskSubmissionError(f"Not authorized: {decision.reason}")

        # Create task
        task = Task(
            type=task_type,
            payload=payload,
            messages=messages or [],
            metadata=metadata or {}
        )

        # Build JSON-RPC request
        rpc_request = task.to_jsonrpc(method="task.send")

        # Send to agent
        base_url = target_url.rstrip('/')
        endpoint = f"{base_url}/rpc"

        try:
            response = await client.post(
                endpoint,
                json=rpc_request,
                timeout=timeout or self._timeout
            )
            response.raise_for_status()

            result = response.json()

            # Handle JSON-RPC error
            if "error" in result:
                error_msg = result["error"].get("message", "Unknown error")
                raise TaskSubmissionError(f"Task submission failed: {error_msg}")

            # Parse response into task
            if "result" in result:
                task_data = result["result"]
                return self._parse_task_response(task_data)

            return task

        except httpx.HTTPError as e:
            raise TaskSubmissionError(f"Failed to send task to {target_url}: {e}") from e

    async def get_task_status(
        self,
        target_url: str,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Task:
        """
        Get the status of a task.

        Args:
            target_url: Base URL of target agent
            task_id: ID of the task
            timeout: Optional timeout override

        Returns:
            Task with current status

        Raises:
            TaskStatusError: If status retrieval fails
        """
        client = await self._ensure_client()

        # Build JSON-RPC request
        rpc_request = {
            "jsonrpc": "2.0",
            "method": "task.status",
            "params": {"task_id": task_id},
            "id": str(uuid.uuid4())
        }

        base_url = target_url.rstrip('/')
        endpoint = f"{base_url}/rpc"

        try:
            response = await client.post(
                endpoint,
                json=rpc_request,
                timeout=timeout or self._timeout
            )
            response.raise_for_status()

            result = response.json()

            if "error" in result:
                error_msg = result["error"].get("message", "Unknown error")
                raise TaskStatusError(f"Failed to get task status: {error_msg}")

            if "result" in result:
                return self._parse_task_response(result["result"])

            raise TaskStatusError("Invalid response format")

        except httpx.HTTPError as e:
            raise TaskStatusError(f"Failed to get task status: {e}") from e

    async def stream_task_updates(
        self,
        target_url: str,
        task_id: str,
        timeout: Optional[float] = None
    ) -> AsyncIterator[Task]:
        """
        Stream task updates via Server-Sent Events (SSE).

        Args:
            target_url: Base URL of target agent
            task_id: ID of the task
            timeout: Optional timeout override

        Yields:
            Task updates as they occur

        Raises:
            TaskStatusError: If streaming fails
        """
        client = await self._ensure_client()

        base_url = target_url.rstrip('/')
        endpoint = f"{base_url}/tasks/{task_id}/stream"

        try:
            async with aconnect_sse(
                client,
                "GET",
                endpoint,
                timeout=timeout or self._timeout
            ) as event_source:
                async for sse in event_source.aiter_sse():
                    if sse.event == "task_update":
                        task_data = json.loads(sse.data)
                        task = self._parse_task_response(task_data)
                        yield task

                        # Stop if task reached terminal state
                        if task.is_terminal():
                            break

        except httpx.HTTPError as e:
            raise TaskStatusError(f"Failed to stream task updates: {e}") from e

    async def poll_until_complete(
        self,
        target_url: str,
        task_id: str,
        poll_interval: float = 1.0,
        max_wait: Optional[float] = None
    ) -> Task:
        """
        Poll task status until completion.

        Args:
            target_url: Base URL of target agent
            task_id: ID of the task
            poll_interval: Seconds between polls
            max_wait: Maximum seconds to wait (None = unlimited)

        Returns:
            Completed task

        Raises:
            TaskStatusError: If polling fails
            TimeoutError: If max_wait is exceeded
        """
        import asyncio
        import time

        start_time = time.time()

        while True:
            task = await self.get_task_status(target_url, task_id)

            if task.is_terminal():
                return task

            if max_wait and (time.time() - start_time) > max_wait:
                raise TimeoutError(f"Task {task_id} did not complete within {max_wait}s")

            await asyncio.sleep(poll_interval)

    def _parse_task_response(self, data: Dict[str, Any]) -> Task:
        """
        Parse task from response data.

        Args:
            data: Response data dictionary

        Returns:
            Task instance
        """
        # Parse messages
        messages = []
        for msg_data in data.get("messages", []):
            parts = [
                MessagePart(type=p["type"], content=p["content"])
                for p in msg_data.get("parts", [])
            ]
            messages.append(Message(role=msg_data["role"], parts=parts))

        # Create task
        return Task(
            id=data.get("id", str(uuid.uuid4())),
            type=data.get("type", "unknown"),
            state=TaskState(data.get("state", "pending")),
            payload=data.get("payload", {}),
            messages=messages,
            result=data.get("result"),
            error=data.get("error"),
            metadata=data.get("metadata", {})
        )

    async def cancel_task(
        self,
        target_url: str,
        task_id: str,
        timeout: Optional[float] = None
    ) -> Task:
        """
        Cancel a running task.

        Args:
            target_url: Base URL of target agent
            task_id: ID of the task to cancel
            timeout: Optional timeout override

        Returns:
            Cancelled task

        Raises:
            TaskStatusError: If cancellation fails
        """
        client = await self._ensure_client()

        rpc_request = {
            "jsonrpc": "2.0",
            "method": "task.cancel",
            "params": {"task_id": task_id},
            "id": str(uuid.uuid4())
        }

        base_url = target_url.rstrip('/')
        endpoint = f"{base_url}/rpc"

        try:
            response = await client.post(
                endpoint,
                json=rpc_request,
                timeout=timeout or self._timeout
            )
            response.raise_for_status()

            result = response.json()

            if "error" in result:
                error_msg = result["error"].get("message", "Unknown error")
                raise TaskStatusError(f"Failed to cancel task: {error_msg}")

            if "result" in result:
                return self._parse_task_response(result["result"])

            raise TaskStatusError("Invalid response format")

        except httpx.HTTPError as e:
            raise TaskStatusError(f"Failed to cancel task: {e}") from e
