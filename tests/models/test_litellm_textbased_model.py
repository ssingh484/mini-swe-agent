import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from openai import AuthenticationError

from minisweagent.models import GLOBAL_MODEL_STATS
from minisweagent.models.litellm_textbased_model import LitellmTextbasedModel


def test_authentication_error_enhanced_message():
    """Test that AuthenticationError gets enhanced with config set instruction."""
    with patch("minisweagent.models.litellm_model.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        model = LitellmTextbasedModel(model_name="gpt-4")

        def side_effect(*args, **kwargs):
            raise AuthenticationError("Invalid API key", response=Mock(), body=None)

        mock_client.chat.completions.create.side_effect = side_effect

        with pytest.raises(AuthenticationError) as exc_info:
            model._query([{"role": "user", "content": "test"}])

        assert "You can permanently set your API key with `mini-extra config set KEY VALUE`." in str(exc_info.value)


def test_model_registry_loading():
    """Test that custom model registry is loaded and registered when provided."""
    model_costs = {
        "my-custom-model": {
            "max_tokens": 4096,
            "input_cost_per_token": 0.0001,
            "output_cost_per_token": 0.0002,
            "litellm_provider": "openai",
            "mode": "chat",
        }
    }

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(model_costs, f)
        registry_path = f.name

    try:
        with patch("minisweagent.models.litellm_model.LITELLM_AVAILABLE", True):
            with patch("minisweagent.models.litellm_model.litellm") as mock_litellm:
                with patch("minisweagent.models.litellm_model.OpenAI"):
                    _model = LitellmTextbasedModel(model_name="my-custom-model", litellm_model_registry=Path(registry_path))
                    mock_litellm.utils.register_model.assert_called_once_with(model_costs)
    finally:
        Path(registry_path).unlink()


def test_model_registry_none():
    """Test that no registry loading occurs when litellm_model_registry is None."""
    with patch("litellm.register_model") as mock_register:
        _model = LitellmTextbasedModel(model_name="gpt-4", litellm_model_registry=None)

        # Verifyminisweagent.models.litellm_model.LITELLM_AVAILABLE", True):
        with patch("minisweagent.models.litellm_model.litellm") as mock_litellm:
            with patch("minisweagent.models.litellm_model.OpenAI"):
                _model = LitellmTextbasedModel(model_name="gpt-4", litellm_model_registry=None)
                mock_litellm.utils.register_model.assert_not_called()


def test_model_registry_not_provided():
    """Test that no registry loading occurs when litellm_model_registry is not provided."""
    with patch("minisweagent.models.litellm_model.LITELLM_AVAILABLE", True):
        with patch("minisweagent.models.litellm_model.litellm") as mock_litellm:
            with patch("minisweagent.models.litellm_model.OpenAI"):
                _model = LitellmTextbasedModel(model_name="gpt-4o")
                mock_litellm.utils.register_modell_cost_tracking_ignore_errors():
    """Test that models work with cost_tracking='ignore_errors'."""
    model = LitellmTextbasedModel(model_name="gpt-4o", cost_tracking="ignore_errors")

    initial_cost = GLOBAL_MODEL_STATS.cost
with patch("minisweagent.models.litellm_model.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        model = LitellmTextbasedModel(model_name="gpt-4o", cost_tracking="ignore_errors")

        initial_cost = GLOBAL_MODEL_STATS.cost

        mock_response = Mock()
        mock_message = Mock()
        mock_message.content = "```mswea_bash_command\necho test\n```"
        mock_message.model_dump.return_value = {
            "role": "assistant",
            "content": "```mswea_bash_command\necho test\n```",
        }
        mock_response.choices = [Mock(message=mock_message)]
        mock_response.model_dump.return_value = {"test": "response"}
        mock_client.chat.completions.create.return_value = mock_response

        with patch("minisweagent.models.litellm_model.LITELLM_AVAILABLE", True):
            with patch("minisweagent.models.litellm_model.litellm") as mock_litellm:
                mock_litellm.cost_calculator.completion_cost.side_effect = ValueError("Model not found")
                messages = [{"role": "user", "content": "test"}]
                result = model.query(messages)

                assert result["content"] == "```mswea_bash_command\necho test\n```"
                assert result["extra"]["actions"] == [{"command": "echo test"}]
                assert GLOBAL_MODEL_STATS.cost == initial_cost


def test_litellm_model_cost_validation_zero_cost():
    """Test that zero cost raises error when cost tracking is enabled."""
    with patch("minisweagent.models.litellm_model.OpenAI") as mock_openai_class:
        mock_client = Mock()
        mock_openai_class.return_value = mock_client
        model = LitellmTextbasedModel(model_name="gpt-4o")

        mock_response = Mock()
        mock_response.choices = [Mock(message=Mock(content="Test response"))]
        mock_response.model_dump.return_value = {"test": "response"}
        mock_client.chat.completions.create.return_value = mock_response

        with patch("minisweagent.models.litellm_model.LITELLM_AVAILABLE", True):
            with patch("minisweagent.models.litellm_model.litellm") as mock_litellm:
                mock_litellm.cost_calculator.completion_cost.return_value = 0.0
                messages = [{"role": "user", "content": "test"}]

                with pytest.raises(RuntimeError) as exc_info:
                    model.query(messages)

                assert "Cost must be > 0.0, got 0.0" in str(exc_info.value)
    