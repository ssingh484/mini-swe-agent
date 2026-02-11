"""A2A protocol data types (Google A2A spec)."""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# === Parts ===

class TextPart(BaseModel):
    type: str = "text"
    text: str


class FilePart(BaseModel):
    type: str = "file"
    file: dict[str, str]


class DataPart(BaseModel):
    type: str = "data"
    data: dict[str, Any]


Part = TextPart | FilePart | DataPart


# === Messages ===

class Message(BaseModel):
    role: str
    parts: list[Part]


# === Task ===

class TaskState(str, Enum):
    submitted = "submitted"
    working = "working"
    input_required = "input-required"
    completed = "completed"
    failed = "failed"
    canceled = "canceled"


class TaskStatus(BaseModel):
    state: TaskState
    message: Message | None = None


class Artifact(BaseModel):
    name: str | None = None
    description: str | None = None
    parts: list[Part]
    index: int = 0


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sessionId: str | None = None
    status: TaskStatus
    artifacts: list[Artifact] = []
    history: list[Message] = []
    metadata: dict[str, Any] = {}


# === JSON-RPC ===

class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    method: str
    params: dict[str, Any] | None = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: str | int | None = None
    result: Any | None = None
    error: JSONRPCError | None = None


class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Any | None = None


# === Agent Card ===

class AgentSkill(BaseModel):
    id: str
    name: str
    description: str
    tags: list[str] = []
    examples: list[str] = []


class AgentCapabilities(BaseModel):
    streaming: bool = False
    pushNotifications: bool = False
    stateTransitionHistory: bool = True


class AgentProvider(BaseModel):
    organization: str
    url: str = ""


class AgentCard(BaseModel):
    name: str
    description: str
    url: str
    version: str
    capabilities: AgentCapabilities = AgentCapabilities()
    skills: list[AgentSkill] = []
    provider: AgentProvider | None = None
    documentationUrl: str | None = None
    defaultInputModes: list[str] = ["text"]
    defaultOutputModes: list[str] = ["text"]


# Error codes
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
TASK_NOT_FOUND = -32001
TASK_NOT_CANCELABLE = -32002
