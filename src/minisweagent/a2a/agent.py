"""A2A Agent wrapper for gateway-based operation."""

import logging
import signal
import sys
import time
from typing import Any

from minisweagent import Environment, Model
from minisweagent.a2a.gateway_client import A2AGatewayClient, A2AGatewayConfig
from minisweagent.agents.default import AgentConfig, DefaultAgent


class A2AAgent:
    """Agent wrapper that operates in A2A mode with gateway registration.
    
    This wrapper:
    - Registers with an A2A gateway
    - Polls for tasks from the gateway
    - Executes tasks using the underlying agent
    - Reports results back to the gateway
    - Handles heartbeats and graceful shutdown
    """

    def __init__(
        self,
        model: Model,
        env: Environment,
        gateway_config: A2AGatewayConfig,
        agent_config_class: type = AgentConfig,
        **agent_kwargs,
    ):
        """Initialize A2A agent.
        
        Args:
            model: Language model to use
            env: Environment for task execution
            gateway_config: Configuration for A2A gateway connection
            agent_config_class: Agent configuration class
            **agent_kwargs: Additional arguments for agent configuration
        """
        self.model = model
        self.env = env
        self.gateway_config = gateway_config
        self.agent_config_class = agent_config_class
        self.agent_kwargs = agent_kwargs
        self.logger = logging.getLogger("a2a_agent")
        self.gateway_client = A2AGatewayClient(gateway_config)
        self.running = False
        self.current_task_id: str | None = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False

    def register(self) -> dict[str, Any]:
        """Register with the A2A gateway."""
        return self.gateway_client.register()

    def unregister(self):
        """Unregister from the gateway."""
        try:
            self.gateway_client.unregister()
        except Exception as e:
            self.logger.error(f"Error during unregistration: {e}")

    def run(self) -> None:
        """Main loop: register, poll for tasks, execute, report results.
        
        This method runs indefinitely until interrupted.
        """
        try:
            # Register with gateway
            self.logger.info(f"Registering with A2A gateway at {self.gateway_config.gateway_url}")
            registration_info = self.register()
            self.logger.info(f"Registration successful: {registration_info}")
            
            self.running = True
            last_heartbeat = time.time()
            heartbeat_interval = 30.0  # Send heartbeat every 30 seconds
            
            while self.running:
                try:
                    # Send heartbeat if needed
                    if time.time() - last_heartbeat > heartbeat_interval:
                        status = "busy" if self.current_task_id else "available"
                        self.gateway_client.send_heartbeat(status=status)
                        last_heartbeat = time.time()
                    
                    # Poll for new task
                    task = self.gateway_client.poll_for_task()
                    
                    if task:
                        self.logger.info(f"Received task: {task.get('task_id', 'unknown')}")
                        self._execute_task(task)
                    else:
                        # No task available, wait before polling again
                        time.sleep(self.gateway_config.poll_interval)
                        
                except KeyboardInterrupt:
                    self.logger.info("Keyboard interrupt received")
                    self.running = False
                    break
                except Exception as e:
                    self.logger.error(f"Error in main loop: {e}", exc_info=True)
                    time.sleep(self.gateway_config.poll_interval)
                    
        finally:
            self.logger.info("Shutting down A2A agent")
            self.unregister()
            self.gateway_client.close()

    def _execute_task(self, task: dict[str, Any]) -> None:
        """Execute a task received from the gateway.
        
        Args:
            task: Task data from gateway containing task_id and task description
        """
        task_id = task.get("task_id")
        if not task_id:
            self.logger.error("Task missing task_id, skipping")
            return
        
        self.current_task_id = task_id
        
        try:
            # Extract task information
            task_description = task.get("description", task.get("task", ""))
            task_context = task.get("context", {})
            
            self.logger.info(f"Starting task {task_id}: {task_description[:100]}...")
            
            # Send heartbeat to indicate we're busy
            self.gateway_client.send_heartbeat(status="busy")
            
            # Create and run agent for this task
            agent = DefaultAgent(
                self.model,
                self.env,
                config_class=self.agent_config_class,
                **self.agent_kwargs,
            )
            
            result = agent.run(task=task_description, **task_context)
            
            # Add trajectory data to result
            result["trajectory"] = agent.serialize()
            result["task_id"] = task_id
            
            self.logger.info(f"Task {task_id} completed with status: {result.get('exit_status', 'unknown')}")
            
            # Submit result to gateway
            self.gateway_client.submit_result(task_id, result)
            
        except Exception as e:
            self.logger.error(f"Error executing task {task_id}: {e}", exc_info=True)
            
            # Report error to gateway
            try:
                error_result = {
                    "exit_status": "error",
                    "submission": "",
                    "error": str(e),
                    "task_id": task_id,
                }
                self.gateway_client.submit_result(task_id, error_result)
            except Exception as submit_error:
                self.logger.error(f"Failed to submit error result: {submit_error}")
                
        finally:
            self.current_task_id = None

    def run_single_task(self, task: dict[str, Any]) -> dict[str, Any]:
        """Execute a single task and return the result (without gateway loop).
        
        Useful for testing or one-off task execution.
        
        Args:
            task: Task data containing description and context
            
        Returns:
            Result dictionary with exit_status, submission, and trajectory
        """
        agent = DefaultAgent(
            self.model,
            self.env,
            config_class=self.agent_config_class,
            **self.agent_kwargs,
        )
        
        task_description = task.get("description", task.get("task", ""))
        task_context = task.get("context", {})
        
        result = agent.run(task=task_description, **task_context)
        result["trajectory"] = agent.serialize()
        
        return result
