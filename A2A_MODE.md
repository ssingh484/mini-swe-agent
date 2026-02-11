# A2A (Agent-to-Agent) Mode

Mini-swe-agent now supports A2A (Agent-to-Agent) mode, allowing the agent to register with an A2A gateway and receive tasks dynamically.

## Overview

In A2A mode, the agent:

1. **Registers** with an A2A gateway
2. **Polls** for tasks from the gateway
3. **Executes** tasks using the standard mini-swe-agent workflow
4. **Reports** results back to the gateway
5. **Sends heartbeats** to indicate its status (available/busy)
6. **Handles graceful shutdown** when interrupted

This enables distributed agent deployments, task queuing, and multi-agent coordination.

## Quick Start

### Install

Make sure you have mini-swe-agent installed:

```bash
pip install mini-swe-agent
```

### Basic Usage

Run the agent in A2A mode:

```bash
mini-a2a --gateway http://localhost:8000 --model gpt-4
```

The agent will:
- Register with the gateway at `http://localhost:8000`
- Poll for tasks every 5 seconds (configurable)
- Execute tasks as they arrive
- Run indefinitely until interrupted (Ctrl+C)

### Configuration Options

```bash
mini-a2a \
  --gateway http://localhost:8000 \          # Gateway URL (required)
  --model gpt-4 \                            # LLM model to use
  --agent-id my-agent-001 \                  # Unique agent ID (optional, auto-generated)
  --agent-name "My SWE Agent" \              # Human-readable name
  --api-key your-gateway-key \               # Gateway API key (if required)
  --poll-interval 10 \                       # Poll every 10 seconds
  --config path/to/config.yaml \             # Agent config file
  --proxy-url http://localhost:4000 \        # LiteLLM proxy URL
  --proxy-key your-proxy-key \               # LiteLLM proxy API key
  --log-level DEBUG                          # Logging level
```

### Environment Variables

You can also configure via environment variables:

```bash
# Model and proxy configuration
export MSWEA_MODEL_NAME=gpt-4
export LITELLM_PROXY_BASE_URL=http://localhost:4000
export LITELLM_PROXY_API_KEY=sk-1234

# A2A gateway configuration
export A2A_GATEWAY_API_KEY=your-gateway-key

# Run the agent
mini-a2a --gateway http://localhost:8000
```

## A2A Gateway API Specification

The agent expects the gateway to implement the following REST API:

### 1. Register Agent

**POST** `/api/v1/agents/register`

Request:
```json
{
  "agent_id": "optional-agent-id",
  "agent_name": "mini-swe-agent",
  "agent_description": "Mini SWE Agent - AI software engineering agent",
  "capabilities": ["bash_execution", "code_editing", "software_engineering"],
  "status": "available"
}
```

Response:
```json
{
  "agent_id": "agent-12345",
  "status": "registered",
  "message": "Agent successfully registered"
}
```

### 2. Poll for Task

**GET** `/api/v1/agents/{agent_id}/tasks/next`

Response (task available):
```json
{
  "task_id": "task-67890",
  "description": "Fix the bug in user_service.py",
  "context": {
    "repository": "https://github.com/example/repo",
    "issue_number": 42
  }
}
```

Response (no tasks): HTTP 204 No Content

### 3. Submit Result

**POST** `/api/v1/tasks/{task_id}/result`

Request:
```json
{
  "agent_id": "agent-12345",
  "task_id": "task-67890",
  "status": "completed",
  "result": {
    "exit_status": "submitted",
    "submission": "Fixed the bug by...",
    "trajectory": { /* full agent trajectory */ }
  }
}
```

Response:
```json
{
  "status": "accepted",
  "message": "Result recorded"
}
```

### 4. Send Heartbeat

**POST** `/api/v1/agents/{agent_id}/heartbeat`

Request:
```json
{
  "agent_id": "agent-12345",
  "status": "available"
}
```

Response:
```json
{
  "status": "ok"
}
```

### 5. Unregister Agent

**DELETE** `/api/v1/agents/{agent_id}`

Response:
```json
{
  "status": "unregistered"
}
```

## Testing Locally

You can test the agent without a gateway using the test command:

```bash
mini-a2a test-task --task "Create a hello world Python script" --model gpt-4
```

This runs a single task locally and prints the result.

## Example Gateway Implementation

Here's a minimal Flask gateway implementation for testing:

```python
from flask import Flask, jsonify, request
from queue import Queue
import uuid

app = Flask(__name__)
agents = {}
tasks = Queue()
results = {}

@app.route('/api/v1/agents/register', methods=['POST'])
def register_agent():
    data = request.json
    agent_id = data.get('agent_id') or str(uuid.uuid4())
    agents[agent_id] = data
    return jsonify({'agent_id': agent_id, 'status': 'registered'})

@app.route('/api/v1/agents/<agent_id>/tasks/next', methods=['GET'])
def get_next_task(agent_id):
    if tasks.empty():
        return '', 204
    task = tasks.get()
    return jsonify(task)

@app.route('/api/v1/tasks/<task_id>/result', methods=['POST'])
def submit_result(task_id):
    results[task_id] = request.json
    return jsonify({'status': 'accepted'})

@app.route('/api/v1/agents/<agent_id>/heartbeat', methods=['POST'])
def heartbeat(agent_id):
    return jsonify({'status': 'ok'})

@app.route('/api/v1/agents/<agent_id>', methods=['DELETE'])
def unregister_agent(agent_id):
    agents.pop(agent_id, None)
    return jsonify({'status': 'unregistered'})

# Admin endpoint to add tasks
@app.route('/admin/tasks', methods=['POST'])
def add_task():
    task = request.json
    task['task_id'] = task.get('task_id', str(uuid.uuid4()))
    tasks.put(task)
    return jsonify({'task_id': task['task_id']})

if __name__ == '__main__':
    app.run(port=8000)
```

Save this as `gateway.py` and run:

```bash
pip install flask
python gateway.py
```

Then submit a task:

```bash
curl -X POST http://localhost:8000/admin/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "description": "Write a function to calculate fibonacci numbers",
    "context": {}
  }'
```

## Production Considerations

### Security

- **Authentication**: Use API keys for gateway authentication
- **Authorization**: Verify agent permissions
- **TLS**: Use HTTPS for gateway communication
- **Input validation**: Validate all task inputs

### Scalability

- **Multiple agents**: Run multiple agent instances for parallel processing
- **Load balancing**: Distribute tasks across agents
- **Task priorities**: Implement priority queues
- **Timeouts**: Handle long-running tasks

### Monitoring

- **Heartbeats**: Detect and handle dead agents
- **Metrics**: Track task completion rates, errors, costs
- **Logging**: Centralized logging for debugging
- **Alerts**: Notify on failures or anomalies

### Reliability

- **Retry logic**: Retry failed tasks
- **Error handling**: Graceful degradation
- **State persistence**: Save task state for recovery
- **Health checks**: Regular gateway health checks

## Docker Deployment

Run the agent in a container:

```dockerfile
FROM python:3.10-slim

WORKDIR /app

RUN pip install mini-swe-agent

CMD ["mini-a2a", "--gateway", "${GATEWAY_URL}", "--model", "${MODEL_NAME}"]
```

Build and run:

```bash
docker build -t mini-swe-agent-a2a .
docker run -e GATEWAY_URL=http://gateway:8000 \
           -e MODEL_NAME=gpt-4 \
           -e LITELLM_PROXY_BASE_URL=http://proxy:4000 \
           mini-swe-agent-a2a
```

## Use Cases

### 1. Distributed SWE-bench Evaluation

Run multiple agents to evaluate SWE-bench instances in parallel:

```bash
# Start 10 agents
for i in {1..10}; do
  mini-a2a --gateway http://gateway:8000 --model gpt-4 --agent-id "eval-agent-$i" &
done
```

### 2. Multi-Repository Monitoring

Agents continuously monitor repositories for new issues:

```bash
mini-a2a --gateway http://gateway:8000 --model gpt-4 --agent-name "repo-monitor"
```

### 3. On-Demand Code Review

Agents review pull requests as they're submitted:

```bash
mini-a2a --gateway http://gateway:8000 --model claude-3-opus --agent-name "code-reviewer"
```

### 4. Hybrid Agent Teams

Mix different models for different task types:

```bash
# Fast agent for simple tasks
mini-a2a --gateway http://gateway:8000 --model gpt-4 &

# Powerful agent for complex tasks  
mini-a2a --gateway http://gateway:8000 --model claude-3-opus &
```

## Troubleshooting

### Connection Refused

```
Error: Connection refused to http://localhost:8000
```

**Solution**: Verify the gateway is running and accessible.

### Authentication Failed

```
Error: HTTP 401 Unauthorized
```

**Solution**: Check your API key configuration.

### No Tasks Received

**Solution**: 
- Verify tasks are being added to the gateway queue
- Check the agent logs for polling activity
- Ensure the agent is registered successfully

### Agent Not Responding

**Solution**:
- Check if the agent process is running
- Verify heartbeats are being sent
- Check for errors in agent logs

## Advanced Configuration

### Custom Agent Configuration

Use a custom config file for specialized behavior:

```yaml
# custom_a2a_config.yaml
agent:
  system_template: |
    You are a specialized code review agent.
    Focus on security vulnerabilities and performance issues.
  instance_template: |
    Review the following code:
    {{ task }}
  step_limit: 50
  cost_limit: 5.0
```

Run with custom config:

```bash
mini-a2a --gateway http://localhost:8000 --config custom_a2a_config.yaml
```

### Environment-Specific Settings

For sandboxed execution:

```python
from minisweagent.environments.docker import DockerEnvironment
from minisweagent.a2a.agent import A2AAgent

# Use Docker environment instead of local
env = DockerEnvironment(image="python:3.10")
a2a_agent = A2AAgent(model, env, gateway_config, **agent_config)
a2a_agent.run()
```

## API Reference

See the source code documentation:

- [A2AGatewayClient](../src/minisweagent/a2a/gateway_client.py) - Gateway client implementation
- [A2AAgent](../src/minisweagent/a2a/agent.py) - A2A agent wrapper
- [A2A Run Script](../src/minisweagent/run/a2a.py) - Command-line interface

## Contributing

We welcome contributions to improve A2A mode:

- Gateway implementations for popular platforms
- Enhanced error handling and retry logic
- Task prioritization and scheduling
- Multi-agent coordination protocols
- Monitoring and observability tools

Please see [CONTRIBUTING.md](../docs/contributing.md) for guidelines.
