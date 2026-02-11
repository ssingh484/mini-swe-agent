"""A2A protocol server for mini-swe-agent.

Implements the Google A2A protocol so this agent can be discovered
and used by A2A gateways like AgentCore or LiteLLM.
"""

from minisweagent.a2a.agent import A2AServer
from minisweagent.a2a.types import AgentCard, Task, TaskState

__all__ = ["A2AServer", "AgentCard", "Task", "TaskState"]
