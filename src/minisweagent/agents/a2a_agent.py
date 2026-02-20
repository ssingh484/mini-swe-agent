"""Agent for A2A server that accepts both tool calls and bash command blocks."""

import re

from pydantic import BaseModel

from minisweagent.agents.default import AgentConfig, DefaultAgent
from minisweagent.exceptions import FormatError


class A2AAgentConfig(AgentConfig):
    action_regex: str = r"```(?:bash|mswea_bash_command)\s*\n(.*?)\n```"
    """Regex to extract bash commands from the model's text output."""


class A2AAgent(DefaultAgent):
    """Agent that first parses tool calls, falls back to bash command blocks."""

    def __init__(self, model, env, *, config_class: type = A2AAgentConfig, **kwargs):
        super().__init__(model, env, config_class=config_class, **kwargs)

    def step(self) -> list[dict]:
        message = self.query()
        actions = message.get("extra", {}).get("actions", [])
        if actions:
            return self.execute_actions(message)
        return self.execute_actions(self._fallback_parse(message))

    def query(self) -> dict:
        """Query model, catching FormatError to allow fallback parsing."""
        try:
            return super().query()
        except FormatError as e:
            # FormatError means no tool calls found; return the last model message
            # so we can try bash block parsing on it
            if self.messages:
                return self.messages[-1]
            raise

    def _fallback_parse(self, message: dict) -> dict:
        """Try to extract bash commands from text content. Raises FormatError if none found."""
        content = message.get("content") or ""
        matches = [m.strip() for m in re.findall(self.config.action_regex, content, re.DOTALL)]
        if not matches:
            raise FormatError(
                {
                    "role": "user",
                    "content": (
                        "No tool calls or bash command blocks found. "
                        "Please use a bash tool call or include a ```bash code block."
                    ),
                    "extra": {"interrupt_type": "FormatError"},
                }
            )
        message.setdefault("extra", {})["actions"] = [{"command": cmd} for cmd in matches]
        return message
