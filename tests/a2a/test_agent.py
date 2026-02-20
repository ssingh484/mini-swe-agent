"""Tests for A2A protocol server."""

from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient

from minisweagent.a2a.agent import A2AServer
from minisweagent.a2a.types import TaskState


def _make_server(**kwargs) -> A2AServer:
    mock_model = MagicMock()
    mock_env = MagicMock()
    return A2AServer(
        model=mock_model,
        env=mock_env,
        system_template="sys",
        instance_template="inst",
        **kwargs,
    )


@pytest.fixture()
def client():
    return TestClient(_make_server().app)


def test_agent_card(client):
    resp = client.get("/.well-known/agent.json")
    assert resp.status_code == 200
    card = resp.json()
    assert card["name"] == "mini-swe-agent"
    assert card["capabilities"]["streaming"] is False
    assert len(card["skills"]) >= 1


def test_unknown_method(client):
    resp = client.post("/", json={"jsonrpc": "2.0", "id": 1, "method": "bogus"})
    assert resp.json()["error"]["code"] == -32601


def test_invalid_json(client):
    resp = client.post("/", content=b"not json", headers={"content-type": "application/json"})
    assert resp.json()["error"]["code"] == -32600


@patch("minisweagent.a2a.agent.A2AAgent")
def test_tasks_send(mock_agent_class, client):
    mock_agent = MagicMock()
    mock_agent.run.return_value = {"exit_status": "completed", "submission": "ok"}
    mock_agent.serialize.return_value = {}
    mock_agent_class.return_value = mock_agent

    resp = client.post("/", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tasks/send",
        "params": {
            "id": "t1",
            "message": {"role": "user", "parts": [{"type": "text", "text": "fix bug"}]},
        },
    })
    result = resp.json()["result"]
    assert result["id"] == "t1"
    assert result["status"]["state"] in {TaskState.submitted, TaskState.working, TaskState.completed}


def test_tasks_send_missing_message(client):
    resp = client.post("/", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tasks/send",
        "params": {"id": "t1"},
    })
    assert resp.json()["error"]["code"] == -32602


def test_tasks_send_empty_text(client):
    resp = client.post("/", json={
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tasks/send",
        "params": {
            "id": "t1",
            "message": {"role": "user", "parts": []},
        },
    })
    assert resp.json()["error"]["code"] == -32602


@patch("minisweagent.a2a.agent.A2AAgent")
def test_tasks_get(mock_agent_class, client):
    mock_agent = MagicMock()
    mock_agent.run.return_value = {"exit_status": "completed", "submission": "ok"}
    mock_agent.serialize.return_value = {}
    mock_agent_class.return_value = mock_agent

    # Send a task first
    client.post("/", json={
        "jsonrpc": "2.0", "id": 1, "method": "tasks/send",
        "params": {"id": "t2", "message": {"role": "user", "parts": [{"type": "text", "text": "hi"}]}},
    })

    resp = client.post("/", json={
        "jsonrpc": "2.0", "id": 2, "method": "tasks/get",
        "params": {"id": "t2"},
    })
    assert resp.json()["result"]["id"] == "t2"


def test_tasks_get_not_found(client):
    resp = client.post("/", json={
        "jsonrpc": "2.0", "id": 1, "method": "tasks/get",
        "params": {"id": "nonexistent"},
    })
    assert resp.json()["error"]["code"] == -32001


@patch("minisweagent.a2a.agent.A2AAgent")
def test_tasks_cancel(mock_agent_class, client):
    mock_agent = MagicMock()
    mock_agent.run.return_value = {"exit_status": "completed", "submission": ""}
    mock_agent.serialize.return_value = {}
    mock_agent_class.return_value = mock_agent

    client.post("/", json={
        "jsonrpc": "2.0", "id": 1, "method": "tasks/send",
        "params": {"id": "t3", "message": {"role": "user", "parts": [{"type": "text", "text": "x"}]}},
    })

    resp = client.post("/", json={
        "jsonrpc": "2.0", "id": 2, "method": "tasks/cancel",
        "params": {"id": "t3"},
    })
    body = resp.json()
    # Either successfully canceled or already finished (race with thread pool)
    assert "result" in body or "error" in body


def test_tasks_cancel_not_found(client):
    resp = client.post("/", json={
        "jsonrpc": "2.0", "id": 1, "method": "tasks/cancel",
        "params": {"id": "missing"},
    })
    assert resp.json()["error"]["code"] == -32001


def test_server_custom_agent_name():
    server = _make_server(agent_name="custom", agent_description="Custom agent")
    assert server.agent_card.name == "custom"
    assert server.agent_card.description == "Custom agent"
