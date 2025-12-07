"""
A2A Protocol server implementation.

Provides FastAPI-based server for handling A2A protocol requests,
including JSON-RPC endpoints, agent card serving, and SSE streaming.
"""

import json
import uuid
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime, timezone

from fastapi import FastAPI, Request, HTTPException, Response
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio

from agentweave.comms.a2a.card import AgentCard
from agentweave.comms.a2a.task import Task, TaskState, TaskManager, Message, MessagePart


class SPIFFEMiddleware(BaseHTTPMiddleware):
    """
    Middleware to extract SPIFFE ID from client certificate.

    In production, this would extract the SPIFFE ID from the client's
    mTLS certificate and add it to request state.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and extract SPIFFE ID."""
        # TODO: Extract SPIFFE ID from client certificate
        # For now, use a placeholder
        request.state.spiffe_id = None

        # Get peer cert from TLS connection
        # if hasattr(request, 'scope') and 'client_cert' in request.scope:
        #     cert = request.scope['client_cert']
        #     spiffe_id = extract_spiffe_id_from_cert(cert)
        #     request.state.spiffe_id = spiffe_id

        response = await call_next(request)
        return response


class A2AServer:
    """
    A2A Protocol server using FastAPI.

    Provides JSON-RPC 2.0 endpoints, agent card serving, task management,
    and SSE streaming for long-running tasks.
    """

    def __init__(
        self,
        agent_card: AgentCard,
        task_manager: Optional[TaskManager] = None,
        authz_enforcer=None,
        enable_cors: bool = True
    ):
        """
        Initialize A2A server.

        Args:
            agent_card: Agent card to serve
            task_manager: Task manager instance (creates new if None)
            authz_enforcer: Authorization enforcer (optional)
            enable_cors: Enable CORS middleware
        """
        self.agent_card = agent_card
        self.task_manager = task_manager or TaskManager()
        self.authz = authz_enforcer

        # FastAPI app
        self.app = FastAPI(
            title=agent_card.name,
            description=agent_card.description,
            version=agent_card.version
        )

        # Task handlers
        self._task_handlers: Dict[str, Callable[[Task], Awaitable[Task]]] = {}

        # Setup middleware
        if enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],  # TODO: Configure based on security requirements
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        self.app.add_middleware(SPIFFEMiddleware)

        # Register routes
        self._register_routes()

    def _register_routes(self) -> None:
        """Register FastAPI routes."""

        @self.app.get("/.well-known/agent.json")
        async def get_agent_card():
            """Serve agent card at well-known endpoint."""
            return JSONResponse(content=self.agent_card.to_dict())

        @self.app.post("/rpc")
        async def handle_jsonrpc(request: Request):
            """Handle JSON-RPC 2.0 requests."""
            try:
                body = await request.json()
            except json.JSONDecodeError:
                return self._jsonrpc_error(
                    error_id=None,
                    code=-32700,
                    message="Parse error"
                )

            # Validate JSON-RPC format
            if not isinstance(body, dict) or body.get("jsonrpc") != "2.0":
                return self._jsonrpc_error(
                    error_id=body.get("id"),
                    code=-32600,
                    message="Invalid Request"
                )

            method = body.get("method")
            params = body.get("params", {})
            request_id = body.get("id")

            # Route to appropriate handler
            if method == "task.send":
                return await self._handle_task_send(request, params, request_id)
            elif method == "task.status":
                return await self._handle_task_status(request, params, request_id)
            elif method == "task.cancel":
                return await self._handle_task_cancel(request, params, request_id)
            else:
                return self._jsonrpc_error(
                    error_id=request_id,
                    code=-32601,
                    message=f"Method not found: {method}"
                )

        @self.app.get("/tasks/{task_id}/stream")
        async def stream_task_updates(task_id: str, request: Request):
            """Stream task updates via Server-Sent Events."""
            return StreamingResponse(
                self._stream_task_events(task_id),
                media_type="text/event-stream"
            )

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint."""
            return {"status": "healthy", "agent": self.agent_card.name}

    async def _handle_task_send(
        self,
        request: Request,
        params: Dict[str, Any],
        request_id: str
    ) -> JSONResponse:
        """
        Handle task.send JSON-RPC method.

        Args:
            request: FastAPI request
            params: RPC parameters
            request_id: JSON-RPC request ID

        Returns:
            JSON-RPC response
        """
        # Check authorization
        if self.authz:
            caller_id = getattr(request.state, 'spiffe_id', 'unknown')
            # decision = await self.authz.check_inbound(
            #     caller_id=caller_id,
            #     action=params.get("task_type"),
            #     context=params
            # )
            # if not decision.allowed:
            #     return self._jsonrpc_error(
            #         error_id=request_id,
            #         code=-32000,
            #         message=f"Not authorized: {decision.reason}"
            #     )

        # Create task
        task_type = params.get("task_type")
        if not task_type:
            return self._jsonrpc_error(
                error_id=request_id,
                code=-32602,
                message="Missing required parameter: task_type"
            )

        # Check if we have a handler for this task type
        if task_type not in self._task_handlers:
            return self._jsonrpc_error(
                error_id=request_id,
                code=-32000,
                message=f"No handler registered for task type: {task_type}"
            )

        # Parse messages
        messages = []
        for msg_data in params.get("messages", []):
            parts = [
                MessagePart(type=p["type"], content=p["content"])
                for p in msg_data.get("parts", [])
            ]
            messages.append(Message(role=msg_data["role"], parts=parts))

        # Create and store task
        task = await self.task_manager.create_task(
            task_type=task_type,
            payload=params.get("payload", {}),
            messages=messages,
            metadata={"caller_spiffe_id": getattr(request.state, 'spiffe_id', None)}
        )

        # Execute task asynchronously
        asyncio.create_task(self._execute_task(task))

        return self._jsonrpc_success(
            result=task.to_dict(),
            request_id=request_id
        )

    async def _handle_task_status(
        self,
        request: Request,
        params: Dict[str, Any],
        request_id: str
    ) -> JSONResponse:
        """
        Handle task.status JSON-RPC method.

        Args:
            request: FastAPI request
            params: RPC parameters
            request_id: JSON-RPC request ID

        Returns:
            JSON-RPC response
        """
        task_id = params.get("task_id")
        if not task_id:
            return self._jsonrpc_error(
                error_id=request_id,
                code=-32602,
                message="Missing required parameter: task_id"
            )

        task = await self.task_manager.get_task(task_id)
        if not task:
            return self._jsonrpc_error(
                error_id=request_id,
                code=-32000,
                message=f"Task not found: {task_id}"
            )

        return self._jsonrpc_success(
            result=task.to_dict(),
            request_id=request_id
        )

    async def _handle_task_cancel(
        self,
        request: Request,
        params: Dict[str, Any],
        request_id: str
    ) -> JSONResponse:
        """
        Handle task.cancel JSON-RPC method.

        Args:
            request: FastAPI request
            params: RPC parameters
            request_id: JSON-RPC request ID

        Returns:
            JSON-RPC response
        """
        task_id = params.get("task_id")
        if not task_id:
            return self._jsonrpc_error(
                error_id=request_id,
                code=-32602,
                message="Missing required parameter: task_id"
            )

        task = await self.task_manager.get_task(task_id)
        if not task:
            return self._jsonrpc_error(
                error_id=request_id,
                code=-32000,
                message=f"Task not found: {task_id}"
            )

        # Only cancel if not already terminal
        if not task.is_terminal():
            await self.task_manager.update_task(
                task_id=task_id,
                state=TaskState.CANCELLED
            )

        task = await self.task_manager.get_task(task_id)
        return self._jsonrpc_success(
            result=task.to_dict(),
            request_id=request_id
        )

    async def _execute_task(self, task: Task) -> None:
        """
        Execute a task using registered handler.

        Args:
            task: Task to execute
        """
        try:
            # Mark task as running
            await self.task_manager.update_task(
                task_id=task.id,
                state=TaskState.RUNNING
            )

            # Get handler
            handler = self._task_handlers.get(task.type)
            if not handler:
                await self.task_manager.update_task(
                    task_id=task.id,
                    state=TaskState.FAILED,
                    error=f"No handler for task type: {task.type}"
                )
                return

            # Execute handler
            updated_task = await handler(task)

            # Update task with result
            await self.task_manager.update_task(
                task_id=task.id,
                state=updated_task.state,
                result=updated_task.result,
                error=updated_task.error
            )

        except Exception as e:
            # Mark task as failed
            await self.task_manager.update_task(
                task_id=task.id,
                state=TaskState.FAILED,
                error=str(e)
            )

    async def _stream_task_events(self, task_id: str):
        """
        Stream task updates as Server-Sent Events.

        Args:
            task_id: Task ID to stream

        Yields:
            SSE formatted events
        """
        task = await self.task_manager.get_task(task_id)
        if not task:
            yield f"event: error\ndata: {json.dumps({'error': 'Task not found'})}\n\n"
            return

        # Send initial state
        yield f"event: task_update\ndata: {json.dumps(task.to_dict())}\n\n"

        # Poll for updates
        while not task.is_terminal():
            await asyncio.sleep(0.5)  # Poll interval
            task = await self.task_manager.get_task(task_id)
            if task:
                yield f"event: task_update\ndata: {json.dumps(task.to_dict())}\n\n"

        # Send final state
        yield f"event: task_complete\ndata: {json.dumps(task.to_dict())}\n\n"

    def register_task_handler(
        self,
        task_type: str,
        handler: Callable[[Task], Awaitable[Task]]
    ) -> None:
        """
        Register a handler for a task type.

        Args:
            task_type: Type of task
            handler: Async function that takes a Task and returns updated Task
        """
        self._task_handlers[task_type] = handler

        # Update agent card capabilities if not already present
        if not self.agent_card.has_capability(task_type):
            from agentweave.comms.a2a.card import Capability
            cap = Capability(
                name=task_type,
                description=f"Handler for {task_type}",
                input_modes=["application/json"],
                output_modes=["application/json"]
            )
            self.agent_card.capabilities.append(cap)

    def _jsonrpc_success(self, result: Any, request_id: str) -> JSONResponse:
        """
        Create JSON-RPC success response.

        Args:
            result: Result data
            request_id: Request ID

        Returns:
            JSON response
        """
        return JSONResponse({
            "jsonrpc": "2.0",
            "result": result,
            "id": request_id
        })

    def _jsonrpc_error(
        self,
        error_id: Optional[str],
        code: int,
        message: str,
        data: Optional[Any] = None
    ) -> JSONResponse:
        """
        Create JSON-RPC error response.

        Args:
            error_id: Request ID (can be None)
            code: Error code
            message: Error message
            data: Optional error data

        Returns:
            JSON response
        """
        error = {
            "code": code,
            "message": message
        }
        if data:
            error["data"] = data

        return JSONResponse({
            "jsonrpc": "2.0",
            "error": error,
            "id": error_id
        })

    def get_app(self) -> FastAPI:
        """
        Get FastAPI application instance.

        Returns:
            FastAPI app
        """
        return self.app

    async def start(self, host: str = "0.0.0.0", port: int = 8443):
        """
        Start the server.

        Args:
            host: Host to bind to
            port: Port to bind to

        Note:
            This is a convenience method. In production, use an ASGI server
            like uvicorn to run the FastAPI app.
        """
        import uvicorn
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
