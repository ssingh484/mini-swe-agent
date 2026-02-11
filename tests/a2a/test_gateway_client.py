"""Tests for A2A gateway client."""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from minisweagent.a2a.gateway_client import A2AGatewayClient, A2AGatewayConfig


def test_gateway_config_defaults():
    config = A2AGatewayConfig(gateway_url="http://localhost:8000")
    assert config.gateway_url == "http://localhost:8000"
    assert config.agent_name == "mini-swe-agent"
    assert config.poll_interval == 5.0
    assert config.timeout == 30.0


def test_gateway_config_custom():
    config = A2AGatewayConfig(
        gateway_url="http://example.com:9000",
        agent_id="custom-001",
        agent_name="Test Agent",
        api_key="secret-key",
        poll_interval=10.0,
    )
    assert config.gateway_url == "http://example.com:9000"
    assert config.agent_id == "custom-001"
    assert config.agent_name == "Test Agent"
    assert config.api_key == "secret-key"
    assert config.poll_interval == 10.0


@patch("minisweagent.a2a.gateway_client.httpx.Client")
def test_register_success(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_id": "agent-123", "status": "registered"}
    mock_client.post.return_value = mock_response
    
    config = A2AGatewayConfig(gateway_url="http://localhost:8000")
    client = A2AGatewayClient(config)
    
    result = client.register()
    
    assert result["agent_id"] == "agent-123"
    assert result["status"] == "registered"
    assert client.config.agent_id == "agent-123"
    assert client.registered is True


@patch("minisweagent.a2a.gateway_client.httpx.Client")
def test_register_with_custom_agent_id(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"agent_id": "custom-001", "status": "registered"}
    mock_client.post.return_value = mock_response
    
    config = A2AGatewayConfig(gateway_url="http://localhost:8000", agent_id="custom-001")
    client = A2AGatewayClient(config)
    
    result = client.register()
    
    assert client.config.agent_id == "custom-001"


@patch("minisweagent.a2a.gateway_client.httpx.Client")
def test_register_failure(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    mock_client.post.side_effect = httpx.HTTPError("Connection failed")
    
    config = A2AGatewayConfig(gateway_url="http://localhost:8000")
    client = A2AGatewayClient(config)
    
    with pytest.raises(RuntimeError, match="A2A gateway registration failed"):
        client.register()


@patch("minisweagent.a2a.gateway_client.httpx.Client")
def test_poll_for_task_success(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "task_id": "task-001",
        "description": "Test task",
        "context": {}
    }
    mock_client.get.return_value = mock_response
    
    config = A2AGatewayConfig(gateway_url="http://localhost:8000", agent_id="agent-123")
    client = A2AGatewayClient(config)
    
    task = client.poll_for_task()
    
    assert task is not None
    assert task["task_id"] == "task-001"
    assert task["description"] == "Test task"


@patch("minisweagent.a2a.gateway_client.httpx.Client")
def test_poll_for_task_no_tasks(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.status_code = 204
    mock_client.get.return_value = mock_response
    
    config = A2AGatewayConfig(gateway_url="http://localhost:8000", agent_id="agent-123")
    client = A2AGatewayClient(config)
    
    task = client.poll_for_task()
    
    assert task is None


@patch("minisweagent.a2a.gateway_client.httpx.Client")
def test_poll_for_task_without_agent_id(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    config = A2AGatewayConfig(gateway_url="http://localhost:8000")
    client = A2AGatewayClient(config)
    
    with pytest.raises(ValueError, match="Cannot poll: agent not registered"):
        client.poll_for_task()


@patch("minisweagent.a2a.gateway_client.httpx.Client")
def test_submit_result_success(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "accepted"}
    mock_client.post.return_value = mock_response
    
    config = A2AGatewayConfig(gateway_url="http://localhost:8000", agent_id="agent-123")
    client = A2AGatewayClient(config)
    
    result = {"exit_status": "completed", "submission": "done"}
    response = client.submit_result("task-001", result)
    
    assert response["status"] == "accepted"


@patch("minisweagent.a2a.gateway_client.httpx.Client")
def test_send_heartbeat(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_client.post.return_value = mock_response
    
    config = A2AGatewayConfig(gateway_url="http://localhost:8000", agent_id="agent-123")
    client = A2AGatewayClient(config)
    
    response = client.send_heartbeat("available")
    
    assert response["status"] == "ok"


@patch("minisweagent.a2a.gateway_client.httpx.Client")
def test_unregister(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "unregistered"}
    mock_client.delete.return_value = mock_response
    
    config = A2AGatewayConfig(gateway_url="http://localhost:8000", agent_id="agent-123")
    client = A2AGatewayClient(config)
    client.registered = True
    
    response = client.unregister()
    
    assert response["status"] == "unregistered"
    assert client.registered is False


@patch("minisweagent.a2a.gateway_client.httpx.Client")
def test_context_manager(mock_client_class):
    mock_client = MagicMock()
    mock_client_class.return_value = mock_client
    
    config = A2AGatewayConfig(gateway_url="http://localhost:8000")
    
    with A2AGatewayClient(config) as client:
        assert client is not None
    
    mock_client.close.assert_called_once()
