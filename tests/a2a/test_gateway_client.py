"""Tests for A2A protocol types."""

import pytest

from minisweagent.a2a.types import (
    INTERNAL_ERROR,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
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


@pytest.mark.parametrize(
    ("state",),
    [
        (TaskState.submitted,),
        (TaskState.working,),
        (TaskState.completed,),
        (TaskState.failed,),
        (TaskState.canceled,),
    ],
)
def test_task_lifecycle_states(state):
    task = Task(
        id="t1",
        status=TaskStatus(state=state),
    )
    assert task.status.state == state
    assert task.id == "t1"


def test_task_defaults():
    task = Task(status=TaskStatus(state=TaskState.submitted))
    assert task.id  # auto-generated uuid
    assert task.artifacts == []
    assert task.history == []


def test_agent_card_serialization():
    card = AgentCard(
        name="test",
        description="desc",
        url="http://localhost:5000",
        version="1.0.0",
        capabilities=AgentCapabilities(streaming=False),
        skills=[AgentSkill(id="s1", name="Skill", description="A skill")],
    )
    data = card.model_dump()
    assert data["name"] == "test"
    assert data["capabilities"]["streaming"] is False
    assert len(data["skills"]) == 1
    assert data["skills"][0]["id"] == "s1"


def test_jsonrpc_request_response_roundtrip():
    req = JSONRPCRequest(id=1, method="tasks/send", params={"id": "t1"})
    assert req.jsonrpc == "2.0"
    assert req.method == "tasks/send"

    resp = JSONRPCResponse(id=1, result={"id": "t1"})
    assert resp.error is None

    err_resp = JSONRPCResponse(
        id=1, error=JSONRPCError(code=TASK_NOT_FOUND, message="not found")
    )
    assert err_resp.result is None
    assert err_resp.error.code == TASK_NOT_FOUND


def test_message_with_text_parts():
    msg = Message(role="user", parts=[TextPart(text="hello")])
    assert msg.parts[0].text == "hello"
    assert msg.parts[0].type == "text"


def test_artifact():
    artifact = Artifact(name="result", parts=[TextPart(text="output")])
    assert artifact.index == 0
    assert artifact.parts[0].text == "output"


def test_error_codes_are_distinct():
    codes = [INTERNAL_ERROR, INVALID_REQUEST, METHOD_NOT_FOUND, TASK_NOT_FOUND]
    assert len(set(codes)) == len(codes)
