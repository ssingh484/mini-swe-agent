"""Tests for A2A agent wrapper."""

from unittest.mock import MagicMock, patch

import pytest

from minisweagent.a2a.agent import A2AAgent
from minisweagent.a2a.gateway_client import A2AGatewayConfig


@patch("minisweagent.a2a.agent.A2AGatewayClient")
def test_a2a_agent_initialization(mock_gateway_client_class):
    mock_model = MagicMock()
    mock_env = MagicMock()
    
    gateway_config = A2AGatewayConfig(
        gateway_url="http://localhost:8000",
        agent_name="test-agent",
    )
    
    agent = A2AAgent(
        model=mock_model,
        env=mock_env,
        gateway_config=gateway_config,
    )
    
    assert agent.model == mock_model
    assert agent.env == mock_env
    assert agent.gateway_config == gateway_config
    assert agent.running is False
    assert agent.current_task_id is None


@patch("minisweagent.a2a.agent.A2AGatewayClient")
def test_register(mock_gateway_client_class):
    mock_gateway = MagicMock()
    mock_gateway_client_class.return_value = mock_gateway
    mock_gateway.register.return_value = {"agent_id": "agent-123", "status": "registered"}
    
    gateway_config = A2AGatewayConfig(gateway_url="http://localhost:8000")
    agent = A2AAgent(
        model=MagicMock(),
        env=MagicMock(),
        gateway_config=gateway_config,
    )
    
    result = agent.register()
    
    assert result["agent_id"] == "agent-123"
    mock_gateway.register.assert_called_once()


@patch("minisweagent.a2a.agent.A2AGatewayClient")
@patch("minisweagent.a2a.agent.DefaultAgent")
def test_run_single_task(mock_agent_class, mock_gateway_client_class):
    mock_gateway = MagicMock()
    mock_gateway_client_class.return_value = mock_gateway
    
    mock_agent_instance = MagicMock()
    mock_agent_instance.run.return_value = {"exit_status": "completed", "submission": "Done"}
    mock_agent_instance.serialize.return_value = {"messages": []}
    mock_agent_class.return_value = mock_agent_instance
    
    gateway_config = A2AGatewayConfig(gateway_url="http://localhost:8000")
    a2a_agent = A2AAgent(
        model=MagicMock(),
        env=MagicMock(),
        gateway_config=gateway_config,
    )
    
    task = {
        "task_id": "test-001",
        "description": "Test task",
        "context": {"key": "value"}
    }
    
    result = a2a_agent.run_single_task(task)
    
    assert result["exit_status"] == "completed"
    assert "trajectory" in result
    mock_agent_instance.run.assert_called_once_with(task="Test task", key="value")


@patch("minisweagent.a2a.agent.A2AGatewayClient")
@patch("minisweagent.a2a.agent.DefaultAgent")
def test_execute_task_success(mock_agent_class, mock_gateway_client_class):
    mock_gateway = MagicMock()
    mock_gateway_client_class.return_value = mock_gateway
    
    mock_agent_instance = MagicMock()
    mock_agent_instance.run.return_value = {"exit_status": "submitted", "submission": "Fixed"}
    mock_agent_instance.serialize.return_value = {"messages": []}
    mock_agent_class.return_value = mock_agent_instance
    
    gateway_config = A2AGatewayConfig(gateway_url="http://localhost:8000")
    a2a_agent = A2AAgent(
        model=MagicMock(),
        env=MagicMock(),
        gateway_config=gateway_config,
    )
    
    task = {
        "task_id": "task-001",
        "description": "Fix the bug",
        "context": {}
    }
    
    a2a_agent._execute_task(task)
    
    mock_agent_instance.run.assert_called_once()
    mock_gateway.submit_result.assert_called_once()
    assert a2a_agent.current_task_id is None


@patch("minisweagent.a2a.agent.A2AGatewayClient")
@patch("minisweagent.a2a.agent.DefaultAgent")
def test_execute_task_error(mock_agent_class, mock_gateway_client_class):
    mock_gateway = MagicMock()
    mock_gateway_client_class.return_value = mock_gateway
    
    mock_agent_instance = MagicMock()
    mock_agent_instance.run.side_effect = RuntimeError("Test error")
    mock_agent_class.return_value = mock_agent_instance
    
    gateway_config = A2AGatewayConfig(gateway_url="http://localhost:8000")
    a2a_agent = A2AAgent(
        model=MagicMock(),
        env=MagicMock(),
        gateway_config=gateway_config,
    )
    
    task = {
        "task_id": "task-001",
        "description": "Fix the bug",
        "context": {}
    }
    
    a2a_agent._execute_task(task)
    
    # Should submit error result
    mock_gateway.submit_result.assert_called_once()
    call_args = mock_gateway.submit_result.call_args
    assert call_args[0][0] == "task-001"
    assert call_args[0][1]["exit_status"] == "error"


@patch("minisweagent.a2a.agent.A2AGatewayClient")
def test_execute_task_missing_task_id(mock_gateway_client_class):
    mock_gateway = MagicMock()
    mock_gateway_client_class.return_value = mock_gateway
    
    gateway_config = A2AGatewayConfig(gateway_url="http://localhost:8000")
    a2a_agent = A2AAgent(
        model=MagicMock(),
        env=MagicMock(),
        gateway_config=gateway_config,
    )
    
    task = {"description": "Task without ID"}
    
    a2a_agent._execute_task(task)
    
    # Should not attempt to submit result
    mock_gateway.submit_result.assert_not_called()
