"""A2A Gateway client for agent registration and communication."""

import logging
from typing import Any

import httpx
from pydantic import BaseModel


class A2AGatewayConfig(BaseModel):
    """Configuration for A2A gateway connection."""

    gateway_url: str
    """Base URL of the A2A gateway (e.g., http://localhost:8000)"""
    agent_id: str | None = None
    """Unique identifier for this agent. Auto-generated if not provided."""
    agent_name: str = "mini-swe-agent"
    """Human-readable name for this agent"""
    agent_description: str = "Mini SWE Agent - AI software engineering agent"
    """Description of agent capabilities"""
    api_key: str | None = None
    """Optional API key for gateway authentication"""
    timeout: float = 30.0
    """Timeout for HTTP requests in seconds"""
    poll_interval: float = 5.0
    """Interval to poll gateway for new tasks in seconds"""


class A2AGatewayClient:
    """Client for communicating with an A2A gateway.
    
    This client handles:
    - Registering the agent with the gateway
    - Polling for new tasks
    - Submitting task results
    - Health checks and heartbeats
    """

    def __init__(self, config: A2AGatewayConfig):
        self.config = config
        self.logger = logging.getLogger("a2a_gateway")
        self.client = httpx.Client(
            base_url=config.gateway_url,
            timeout=config.timeout,
            headers=self._get_headers(),
        )
        self.registered = False
        
    def _get_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        return headers

    def register(self) -> dict[str, Any]:
        """Register this agent with the gateway.
        
        Returns:
            Registration response from gateway including assigned agent_id
        """
        payload = {
            "agent_name": self.config.agent_name,
            "agent_description": self.config.agent_description,
            "capabilities": ["bash_execution", "code_editing", "software_engineering"],
            "status": "available",
        }
        
        if self.config.agent_id:
            payload["agent_id"] = self.config.agent_id
        
        try:
            response = self.client.post("/api/v1/agents/register", json=payload)
            response.raise_for_status()
            result = response.json()
            
            if not self.config.agent_id and "agent_id" in result:
                self.config.agent_id = result["agent_id"]
            
            self.registered = True
            self.logger.info(f"Successfully registered agent with ID: {self.config.agent_id}")
            return result
            
        except httpx.HTTPError as e:
            self.logger.error(f"Failed to register with gateway: {e}")
            raise RuntimeError(f"A2A gateway registration failed: {e}") from e

    def unregister(self) -> dict[str, Any]:
        """Unregister this agent from the gateway."""
        if not self.config.agent_id:
            raise ValueError("Cannot unregister: agent_id not set")
        
        try:
            response = self.client.delete(f"/api/v1/agents/{self.config.agent_id}")
            response.raise_for_status()
            self.registered = False
            self.logger.info(f"Unregistered agent {self.config.agent_id}")
            return response.json()
        except httpx.HTTPError as e:
            self.logger.error(f"Failed to unregister: {e}")
            raise

    def poll_for_task(self) -> dict[str, Any] | None:
        """Poll the gateway for a new task.
        
        Returns:
            Task data if available, None otherwise
        """
        if not self.config.agent_id:
            raise ValueError("Cannot poll: agent not registered")
        
        try:
            response = self.client.get(f"/api/v1/agents/{self.config.agent_id}/tasks/next")
            if response.status_code == 204:  # No content - no tasks available
                return None
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            self.logger.warning(f"Error polling for tasks: {e}")
            return None

    def submit_result(self, task_id: str, result: dict[str, Any]) -> dict[str, Any]:
        """Submit the result of a completed task.
        
        Args:
            task_id: ID of the task that was completed
            result: Result data including status, output, etc.
            
        Returns:
            Response from gateway
        """
        if not self.config.agent_id:
            raise ValueError("Cannot submit result: agent not registered")
        
        payload = {
            "agent_id": self.config.agent_id,
            "task_id": task_id,
            "status": result.get("exit_status", "completed"),
            "result": result,
        }
        
        try:
            response = self.client.post(f"/api/v1/tasks/{task_id}/result", json=payload)
            response.raise_for_status()
            self.logger.info(f"Submitted result for task {task_id}")
            return response.json()
        except httpx.HTTPError as e:
            self.logger.error(f"Failed to submit result for task {task_id}: {e}")
            raise

    def send_heartbeat(self, status: str = "available") -> dict[str, Any]:
        """Send a heartbeat to the gateway to indicate agent is alive.
        
        Args:
            status: Current agent status (available, busy, error)
            
        Returns:
            Response from gateway
        """
        if not self.config.agent_id:
            raise ValueError("Cannot send heartbeat: agent not registered")
        
        payload = {"status": status, "agent_id": self.config.agent_id}
        
        try:
            response = self.client.post(f"/api/v1/agents/{self.config.agent_id}/heartbeat", json=payload)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            self.logger.debug(f"Heartbeat failed: {e}")
            return {}

    def close(self):
        """Close the HTTP client connection."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
