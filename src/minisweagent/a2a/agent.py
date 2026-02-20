"""A2A protocol server.

Implements the Google A2A protocol: Agent Card discovery + JSON-RPC task handling.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from minisweagent import Environment, Model
from minisweagent.a2a.types import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
    TASK_NOT_CANCELABLE,
    TASK_NOT_FOUND,
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Artifact,
    JSONRPCError,
    JSONRPCRequest,
    JSONRPCResponse,
    Message,
    Task,
    TaskState,
    TaskStatus,
    TextPart,
)
from minisweagent.agents.a2a_agent import A2AAgent, A2AAgentConfig

logger = logging.getLogger("a2a_server")


class A2AServer:
    """A2A protocol server wrapping a DefaultAgent."""

    def __init__(
        self,
        model: Model,
        env: Environment,
        *,
        agent_config_class: type = A2AAgentConfig,
        agent_name: str = "mini-swe-agent",
        agent_description: str = "AI software engineering agent",
        host: str = "0.0.0.0",
        port: int = 5000,
        **agent_kwargs: Any,
    ):
        self.model = model
        self.env = env
        self.agent_config_class = agent_config_class
        self.agent_kwargs = agent_kwargs
        self.host = host
        self.port = port
        self.tasks: dict[str, Task] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)

        self.agent_card = AgentCard(
            name=agent_name,
            description=agent_description,
            url=f"http://{host}:{port}",
            version="1.0.0",
            capabilities=AgentCapabilities(streaming=False, pushNotifications=False),
            skills=[
                AgentSkill(
                    id="software-engineering",
                    name="Software Engineering",
                    description="Solve software engineering tasks: bug fixes, features, refactoring",
                    tags=["code", "bash", "debugging"],
                ),
            ],
        )

        self.app = Starlette(
            routes=[
                Route("/.well-known/agent.json", self._agent_card, methods=["GET"]),
                Route("/", self._jsonrpc, methods=["POST"]),
            ],
        )

    async def _agent_card(self, request: Request) -> JSONResponse:
        return JSONResponse(self.agent_card.model_dump())

    async def _jsonrpc(self, request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return self._error_response(None, INVALID_REQUEST, "Invalid JSON")

        try:
            rpc = JSONRPCRequest(**body)
        except Exception:
            return self._error_response(body.get("id"), INVALID_REQUEST, "Invalid JSON-RPC request")

        handlers = {
            "tasks/send": self._handle_tasks_send,
            "tasks/get": self._handle_tasks_get,
            "tasks/cancel": self._handle_tasks_cancel,
        }
        handler = handlers.get(rpc.method)
        if not handler:
            return self._error_response(rpc.id, METHOD_NOT_FOUND, f"Unknown method: {rpc.method}")

        return await handler(rpc)

    async def _handle_tasks_send(self, rpc: JSONRPCRequest) -> JSONResponse:
        params = rpc.params or {}
        task_id = params.get("id", str(uuid.uuid4()))
        session_id = params.get("sessionId")
        message_data = params.get("message")

        if not message_data:
            return self._error_response(rpc.id, INVALID_PARAMS, "Missing 'message' in params")

        # Extract text from message parts
        task_text = ""
        for part in message_data.get("parts", []):
            if part.get("type", "text") == "text":
                task_text += part.get("text", "")

        if not task_text:
            return self._error_response(rpc.id, INVALID_PARAMS, "No text content in message")

        task = Task(
            id=task_id,
            sessionId=session_id,
            status=TaskStatus(state=TaskState.submitted),
            history=[Message(role="user", parts=[TextPart(text=task_text)])],
        )
        self.tasks[task_id] = task

        # Run agent in background thread
        loop = asyncio.get_event_loop()
        loop.run_in_executor(self._executor, self._run_task, task_id, task_text)

        # Return current task state (submitted, will transition to working→completed)
        return self._success_response(rpc.id, task.model_dump())

    async def _handle_tasks_get(self, rpc: JSONRPCRequest) -> JSONResponse:
        params = rpc.params or {}
        task_id = params.get("id")
        if not task_id or task_id not in self.tasks:
            return self._error_response(rpc.id, TASK_NOT_FOUND, "Task not found")
        return self._success_response(rpc.id, self.tasks[task_id].model_dump())

    async def _handle_tasks_cancel(self, rpc: JSONRPCRequest) -> JSONResponse:
        params = rpc.params or {}
        task_id = params.get("id")
        if not task_id or task_id not in self.tasks:
            return self._error_response(rpc.id, TASK_NOT_FOUND, "Task not found")

        task = self.tasks[task_id]
        if task.status.state in (TaskState.completed, TaskState.failed, TaskState.canceled):
            return self._error_response(rpc.id, TASK_NOT_CANCELABLE, "Task already finished")

        task.status = TaskStatus(
            state=TaskState.canceled,
            message=Message(role="agent", parts=[TextPart(text="Task canceled")]),
        )
        return self._success_response(rpc.id, task.model_dump())

    def _run_task(self, task_id: str, task_text: str) -> None:
        """Execute task synchronously (called from thread pool)."""
        task = self.tasks[task_id]
        task.status = TaskStatus(state=TaskState.working)

        try:
            agent = A2AAgent(
                self.model,
                self.env,
                config_class=self.agent_config_class,
                **self.agent_kwargs,
            )
            result = agent.run(task=task_text)

            submission = result.get("submission", "")
            exit_status = result.get("exit_status", "completed")
            output_text = f"Exit: {exit_status}\n{submission}" if submission else f"Exit: {exit_status}"

            task.status = TaskStatus(
                state=TaskState.completed,
                message=Message(role="agent", parts=[TextPart(text=output_text)]),
            )
            task.artifacts = [
                Artifact(
                    name="result",
                    parts=[TextPart(text=output_text)],
                ),
            ]
            # Store full trajectory as metadata
            task.metadata = {"trajectory": agent.serialize(), "exit_status": exit_status}

        except Exception as e:
            logger.exception(f"Task {task_id} failed")
            task.status = TaskStatus(
                state=TaskState.failed,
                message=Message(role="agent", parts=[TextPart(text=str(e))]),
            )

    def _success_response(self, rpc_id: str | int | None, result: Any) -> JSONResponse:
        return JSONResponse(JSONRPCResponse(id=rpc_id, result=result).model_dump())

    def _error_response(self, rpc_id: str | int | None, code: int, message: str) -> JSONResponse:
        return JSONResponse(
            JSONRPCResponse(id=rpc_id, error=JSONRPCError(code=code, message=message)).model_dump()
        )
