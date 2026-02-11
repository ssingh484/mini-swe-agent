# A2A Protocol Server

Mini-swe-agent implements the [Google A2A protocol](https://google.github.io/A2A/), allowing it to be discovered and used by A2A gateways like **AgentCore** or **LiteLLM**.

## Overview

The agent runs as an HTTP server that exposes:

- **`GET /.well-known/agent.json`** — Agent Card for discovery
- **`POST /`** — JSON-RPC 2.0 endpoint for task management

Supported JSON-RPC methods:

| Method | Description |
|---|---|
| `tasks/send` | Submit a task to the agent |
| `tasks/get` | Get current task status |
| `tasks/cancel` | Cancel a running task |

## Quick Start

```bash
pip install mini-swe-agent
mini-a2a --model gpt-4 --port 5000
```

The agent will start serving at `http://0.0.0.0:5000`. Gateways can discover it via `http://<host>:5000/.well-known/agent.json`.

## CLI Options

```bash
mini-a2a \
  --model gpt-4 \                      # LLM model to use
  --host 0.0.0.0 \                     # Bind address
  --port 5000 \                        # Port
  --agent-name "my-swe-agent" \        # Name in Agent Card
  --config path/to/config.yaml \       # Agent config file
  --proxy-url http://localhost:4000 \  # LiteLLM proxy URL
  --proxy-key sk-1234 \               # LiteLLM proxy API key
  --log-level INFO                     # Logging level
```

## Environment Variables

```bash
export MSWEA_MODEL_NAME=gpt-4
export LITELLM_PROXY_BASE_URL=http://localhost:4000
export LITELLM_PROXY_API_KEY=sk-1234
mini-a2a
```

## Agent Card

The agent card served at `/.well-known/agent.json`:

```json
{
  "name": "mini-swe-agent",
  "description": "AI software engineering agent",
  "url": "http://0.0.0.0:5000",
  "version": "1.0.0",
  "capabilities": {
    "streaming": false,
    "pushNotifications": false,
    "stateTransitionHistory": true
  },
  "skills": [
    {
      "id": "software-engineering",
      "name": "Software Engineering",
      "description": "Solve software engineering tasks: bug fixes, features, refactoring",
      "tags": ["code", "bash", "debugging"]
    }
  ],
  "defaultInputModes": ["text"],
  "defaultOutputModes": ["text"]
}
```

## Sending Tasks (JSON-RPC)

### tasks/send

```bash
curl -X POST http://localhost:5000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tasks/send",
    "params": {
      "id": "task-001",
      "message": {
        "role": "user",
        "parts": [{"type": "text", "text": "Fix the bug in auth.py"}]
      }
    }
  }'
```

### tasks/get

```bash
curl -X POST http://localhost:5000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tasks/get",
    "params": {"id": "task-001"}
  }'
```

### tasks/cancel

```bash
curl -X POST http://localhost:5000/ \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tasks/cancel",
    "params": {"id": "task-001"}
  }'
```

## Task Lifecycle

```
submitted → working → completed
                    → failed
         → canceled
```

## Docker

```dockerfile
FROM python:3.10-slim
RUN pip install mini-swe-agent
EXPOSE 5000
CMD ["mini-a2a", "--model", "${MODEL_NAME}", "--port", "5000"]
```

## Python API

```python
from minisweagent.a2a import A2AServer
from minisweagent.environments.local import LocalEnvironment
from minisweagent.models.litellm_model import LitellmModel

server = A2AServer(
    model=LitellmModel(model_name="gpt-4"),
    env=LocalEnvironment(),
    system_template="You are a helpful agent.",
    instance_template="{{ task }}",
    port=5000,
)

import uvicorn
uvicorn.run(server.app, host="0.0.0.0", port=5000)
```
