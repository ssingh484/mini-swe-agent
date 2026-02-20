"""Start mini-swe-agent as an A2A protocol server."""

import logging
import os
from pathlib import Path

import typer
import yaml

from minisweagent import package_dir
from minisweagent.agents.a2a_agent import A2AAgentConfig
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.litellm_model import LitellmModel

app = typer.Typer()


@app.command()
def main(
    model_name: str = typer.Option(
        os.getenv("MSWEA_MODEL_NAME"),
        "-m",
        "--model",
        help="Model name (defaults to MSWEA_MODEL_NAME env var)",
        prompt="What model do you want to use?",
    ),
    host: str = typer.Option("0.0.0.0", "--host", help="Host to bind the server to"),
    port: int = typer.Option(5000, "--port", "-p", help="Port to listen on"),
    agent_name: str = typer.Option("mini-swe-agent", "--agent-name", help="Agent name in Agent Card"),
    config_file: Path = typer.Option(
        package_dir / "config" / "mini.yaml",
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
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level"),
):
    """Start mini-swe-agent as an A2A protocol server.

    Gateways like AgentCore or LiteLLM can discover this agent via
    GET /.well-known/agent.json and send tasks via JSON-RPC at POST /.

    Example:
        mini-a2a --model gpt-4 --port 5000
    """
    import uvicorn

    from minisweagent.a2a.agent import A2AServer

    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    if not config_file.exists():
        raise typer.Exit(1)

    agent_config = yaml.safe_load(config_file.read_text()).get("agent", {})

    model = LitellmModel(
        model_name=model_name,
        proxy_base_url=proxy_base_url,
        api_key=proxy_api_key,
    )
    env = LocalEnvironment()

    server = A2AServer(
        model=model,
        env=env,
        agent_config_class=A2AAgentConfig,
        agent_name=agent_name,
        host=host,
        port=port,
        **agent_config,
    )

    typer.echo(f"A2A server starting on http://{host}:{port}")
    typer.echo(f"Agent Card: http://{host}:{port}/.well-known/agent.json")
    uvicorn.run(server.app, host=host, port=port)


if __name__ == "__main__":
    app()
