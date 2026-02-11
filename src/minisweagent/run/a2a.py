"""A2A mode run script for mini-swe-agent.

This script runs the agent in A2A (Agent-to-Agent) mode where it:
1. Registers with an A2A gateway
2. Polls for tasks from the gateway
3. Executes tasks using the configured agent
4. Reports results back to the gateway
"""

import logging
import os
from pathlib import Path

import typer
import yaml

from minisweagent import package_dir
from minisweagent.a2a.agent import A2AAgent
from minisweagent.a2a.gateway_client import A2AGatewayConfig
from minisweagent.agents.default import AgentConfig
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.litellm_model import LitellmModel

app = typer.Typer()


@app.command()
def main(
    gateway_url: str = typer.Option(
        ...,
        "-g",
        "--gateway",
        help="A2A gateway URL (e.g., http://localhost:8000)",
        show_default=False,
        prompt="A2A Gateway URL",
    ),
    model_name: str = typer.Option(
        os.getenv("MSWEA_MODEL_NAME"),
        "-m",
        "--model",
        help="Model name (defaults to MSWEA_MODEL_NAME env var)",
        prompt="What model do you want to use?",
    ),
    agent_id: str = typer.Option(
        None,
        "--agent-id",
        help="Unique agent ID (auto-generated if not provided)",
    ),
    agent_name: str = typer.Option(
        "mini-swe-agent",
        "--agent-name",
        help="Human-readable agent name",
    ),
    api_key: str = typer.Option(
        os.getenv("A2A_GATEWAY_API_KEY"),
        "--api-key",
        help="API key for gateway authentication",
    ),
    poll_interval: float = typer.Option(
        5.0,
        "--poll-interval",
        help="Interval to poll gateway for tasks (seconds)",
    ),
    config_file: Path = typer.Option(
        package_dir / "config" / "default.yaml",
        "-c",
        "--config",
        help="Agent configuration file",
    ),
    proxy_base_url: str = typer.Option(
        os.getenv("LITELLM_PROXY_BASE_URL", "http://localhost:4000"),
        "--proxy-url",
        help="LiteLLM proxy base URL",
    ),
    proxy_api_key: str = typer.Option(
        os.getenv("LITELLM_PROXY_API_KEY", "sk-1234"),
        "--proxy-key",
        help="LiteLLM proxy API key",
    ),
    log_level: str = typer.Option(
        "INFO",
        "--log-level",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    ),
):
    """Run mini-swe-agent in A2A mode with gateway registration.
    
    The agent will:
    1. Register with the specified A2A gateway
    2. Poll for tasks from the gateway
    3. Execute tasks and report results
    4. Continue running until interrupted (Ctrl+C)
    
    Example:
        mini-a2a --gateway http://localhost:8000 --model gpt-4
    """
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger("mini-a2a")
    
    # Load agent configuration
    if not config_file.exists():
        logger.error(f"Config file not found: {config_file}")
        raise typer.Exit(1)
    
    config_data = yaml.safe_load(config_file.read_text())
    agent_config = config_data.get("agent", {})
    
    # Create gateway configuration
    gateway_config = A2AGatewayConfig(
        gateway_url=gateway_url,
        agent_id=agent_id,
        agent_name=agent_name,
        api_key=api_key,
        poll_interval=poll_interval,
    )
    
    # Create model with proxy configuration
    model = LitellmModel(
        model_name=model_name,
        proxy_base_url=proxy_base_url,
        api_key=proxy_api_key,
    )
    
    # Create environment
    env = LocalEnvironment()
    
    # Create and run A2A agent
    logger.info(f"Starting mini-swe-agent in A2A mode")
    logger.info(f"Gateway: {gateway_url}")
    logger.info(f"Agent: {agent_name} ({agent_id or 'auto'})")
    logger.info(f"Model: {model_name}")
    logger.info(f"Poll interval: {poll_interval}s")
    
    a2a_agent = A2AAgent(
        model=model,
        env=env,
        gateway_config=gateway_config,
        agent_config_class=AgentConfig,
        **agent_config,
    )
    
    try:
        a2a_agent.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise typer.Exit(1)
    finally:
        logger.info("Shutdown complete")


@app.command()
def test_task(
    task: str = typer.Option(
        ...,
        "-t",
        "--task",
        help="Task description to test",
        show_default=False,
        prompt=True,
    ),
    model_name: str = typer.Option(
        os.getenv("MSWEA_MODEL_NAME"),
        "-m",
        "--model",
        help="Model name",
        prompt="What model do you want to use?",
    ),
    config_file: Path = typer.Option(
        package_dir / "config" / "default.yaml",
        "-c",
        "--config",
        help="Agent configuration file",
    ),
):
    """Test A2A agent with a single task (without gateway connection).
    
    This is useful for testing the agent locally before connecting to a gateway.
    
    Example:
        mini-a2a test-task --task "Create a hello world Python script" --model gpt-4
    """
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("mini-a2a-test")
    
    config_data = yaml.safe_load(config_file.read_text())
    agent_config = config_data.get("agent", {})
    
    # Create a dummy gateway config (not used for test)
    gateway_config = A2AGatewayConfig(
        gateway_url="http://localhost:8000",
        agent_name="test-agent",
    )
    
    model = LitellmModel(model_name=model_name)
    env = LocalEnvironment()
    
    a2a_agent = A2AAgent(
        model=model,
        env=env,
        gateway_config=gateway_config,
        agent_config_class=AgentConfig,
        **agent_config,
    )
    
    logger.info(f"Testing task: {task[:100]}...")
    
    test_task_data = {
        "task_id": "test-001",
        "description": task,
        "context": {},
    }
    
    result = a2a_agent.run_single_task(test_task_data)
    
    logger.info(f"Task completed with status: {result.get('exit_status', 'unknown')}")
    logger.info(f"Submission: {result.get('submission', 'N/A')}")
    
    return result


if __name__ == "__main__":
    app()
