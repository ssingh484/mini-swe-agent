# Mini-SWE-Agent Examples

This directory contains example implementations and usage patterns for mini-swe-agent.

## A2A Gateway Example

The `a2a_gateway_example.py` file provides a minimal reference implementation of an A2A (Agent-to-Agent) gateway server.

### Quick Start

1. **Install Flask**:
   ```bash
   pip install flask
   ```

2. **Start the gateway**:
   ```bash
   python examples/a2a_gateway_example.py
   ```
   
   The gateway will start on `http://localhost:8000`

3. **Add a task** (in another terminal):
   ```bash
   curl -X POST http://localhost:8000/admin/tasks \
     -H "Content-Type: application/json" \
     -d '{
       "description": "Write a Python function to calculate fibonacci numbers",
       "context": {}
     }'
   ```

4. **Start an agent** (in another terminal):
   ```bash
   mini-a2a --gateway http://localhost:8000 --model gpt-4
   ```

### Gateway Endpoints

#### API Endpoints (for agents)
- `POST /api/v1/agents/register` - Register an agent
- `GET /api/v1/agents/{agent_id}/tasks/next` - Poll for tasks
- `POST /api/v1/tasks/{task_id}/result` - Submit results
- `POST /api/v1/agents/{agent_id}/heartbeat` - Send heartbeat
- `DELETE /api/v1/agents/{agent_id}` - Unregister agent

#### Admin Endpoints (for task management)
- `POST /admin/tasks` - Add a new task
- `GET /admin/tasks` - List all tasks
- `GET /admin/agents` - List registered agents
- `GET /admin/results` - List task results
- `GET /admin/results/{task_id}` - Get specific task result

#### Health Check
- `GET /health` - Gateway health status
- `GET /` - Gateway information

### Example Usage

```bash
# Start the gateway
python examples/a2a_gateway_example.py

# In another terminal, add some tasks
curl -X POST http://localhost:8000/admin/tasks \
  -H "Content-Type: application/json" \
  -d '{"description": "Create a hello world script"}'

curl -X POST http://localhost:8000/admin/tasks \
  -H "Content-Type: application/json" \
  -d '{"description": "Write unit tests for a calculator"}'

# Check gateway status
curl http://localhost:8000/health

# Start multiple agents to process tasks in parallel
mini-a2a --gateway http://localhost:8000 --model gpt-4 &
mini-a2a --gateway http://localhost:8000 --model gpt-4 &

# View results
curl http://localhost:8000/admin/results
```

### Production Considerations

This example gateway is for **testing and development only**. For production use, you should:

- ✅ Add proper authentication and authorization
- ✅ Use a persistent database (PostgreSQL, MongoDB, etc.)
- ✅ Implement proper task queueing (Redis, RabbitMQ, etc.)
- ✅ Add rate limiting and request validation
- ✅ Use HTTPS/TLS for secure communication
- ✅ Implement proper logging and monitoring
- ✅ Add health checks and error recovery
- ✅ Use a production WSGI server (Gunicorn, uWSGI)
- ✅ Implement task priorities and scheduling
- ✅ Add metrics and observability

### See Also

- [A2A Mode Documentation](../A2A_MODE.md) - Complete guide to A2A mode
- [LiteLLM Proxy Setup](../LITELLM_PROXY_MIGRATION.md) - Configure the LLM proxy
