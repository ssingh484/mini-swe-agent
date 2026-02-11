"""Simple example A2A gateway server for testing.

This is a minimal reference implementation for testing A2A mode.
For production use, you should implement proper authentication, persistence,
load balancing, and error handling.

Install dependencies:
    pip install flask

Run the server:
    python examples/a2a_gateway_example.py

Add a task:
    curl -X POST http://localhost:8000/admin/tasks \
      -H "Content-Type: application/json" \
      -d '{"description": "Write a hello world script", "context": {}}'

Start an agent:
    mini-a2a --gateway http://localhost:8000 --model gpt-4
"""

import uuid
from datetime import datetime
from queue import Queue

from flask import Flask, jsonify, request

app = Flask(__name__)

# In-memory storage (use a database in production)
agents = {}
tasks = Queue()
results = {}
task_metadata = {}


@app.route("/api/v1/agents/register", methods=["POST"])
def register_agent():
    """Register a new agent with the gateway."""
    data = request.json
    agent_id = data.get("agent_id") or f"agent-{uuid.uuid4()}"
    
    agents[agent_id] = {
        "agent_id": agent_id,
        "agent_name": data.get("agent_name", "unknown"),
        "agent_description": data.get("agent_description", ""),
        "capabilities": data.get("capabilities", []),
        "status": data.get("status", "available"),
        "registered_at": datetime.now().isoformat(),
        "last_heartbeat": datetime.now().isoformat(),
    }
    
    print(f"✓ Agent registered: {agent_id} ({agents[agent_id]['agent_name']})")
    
    return jsonify({
        "agent_id": agent_id,
        "status": "registered",
        "message": "Agent successfully registered"
    })


@app.route("/api/v1/agents/<agent_id>/tasks/next", methods=["GET"])
def get_next_task(agent_id):
    """Poll for the next available task."""
    if agent_id not in agents:
        return jsonify({"error": "Agent not registered"}), 404
    
    if tasks.empty():
        return "", 204  # No content - no tasks available
    
    task = tasks.get()
    print(f"→ Task {task['task_id']} assigned to agent {agent_id}")
    
    return jsonify(task)


@app.route("/api/v1/tasks/<task_id>/result", methods=["POST"])
def submit_result(task_id):
    """Receive task results from an agent."""
    data = request.json
    agent_id = data.get("agent_id")
    
    results[task_id] = {
        "task_id": task_id,
        "agent_id": agent_id,
        "status": data.get("status", "unknown"),
        "result": data.get("result", {}),
        "submitted_at": datetime.now().isoformat(),
    }
    
    print(f"✓ Result received for task {task_id} from agent {agent_id}")
    print(f"  Status: {results[task_id]['status']}")
    
    return jsonify({
        "status": "accepted",
        "message": "Result recorded"
    })


@app.route("/api/v1/agents/<agent_id>/heartbeat", methods=["POST"])
def heartbeat(agent_id):
    """Receive heartbeat from an agent."""
    if agent_id not in agents:
        return jsonify({"error": "Agent not registered"}), 404
    
    data = request.json
    agents[agent_id]["status"] = data.get("status", "available")
    agents[agent_id]["last_heartbeat"] = datetime.now().isoformat()
    
    return jsonify({"status": "ok"})


@app.route("/api/v1/agents/<agent_id>", methods=["DELETE"])
def unregister_agent(agent_id):
    """Unregister an agent."""
    if agent_id in agents:
        agent_name = agents[agent_id]["agent_name"]
        del agents[agent_id]
        print(f"✗ Agent unregistered: {agent_id} ({agent_name})")
        return jsonify({"status": "unregistered"})
    
    return jsonify({"error": "Agent not found"}), 404


# Admin endpoints

@app.route("/admin/tasks", methods=["POST"])
def add_task():
    """Add a new task to the queue (admin endpoint)."""
    data = request.json
    task_id = data.get("task_id") or f"task-{uuid.uuid4()}"
    
    task = {
        "task_id": task_id,
        "description": data.get("description", ""),
        "context": data.get("context", {}),
    }
    
    task_metadata[task_id] = {
        **task,
        "created_at": datetime.now().isoformat(),
        "status": "pending",
    }
    
    tasks.put(task)
    print(f"+ Task added: {task_id}")
    
    return jsonify({
        "task_id": task_id,
        "status": "queued",
        "message": "Task added to queue"
    })


@app.route("/admin/agents", methods=["GET"])
def list_agents():
    """List all registered agents (admin endpoint)."""
    return jsonify({"agents": list(agents.values())})


@app.route("/admin/tasks", methods=["GET"])
def list_tasks():
    """List all tasks (admin endpoint)."""
    return jsonify({
        "tasks": list(task_metadata.values()),
        "queue_size": tasks.qsize()
    })


@app.route("/admin/results", methods=["GET"])
def list_results():
    """List all task results (admin endpoint)."""
    return jsonify({"results": list(results.values())})


@app.route("/admin/results/<task_id>", methods=["GET"])
def get_result(task_id):
    """Get result for a specific task (admin endpoint)."""
    if task_id not in results:
        return jsonify({"error": "Result not found"}), 404
    
    return jsonify(results[task_id])


@app.route("/health", methods=["GET"])
def health():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "agents": len(agents),
        "pending_tasks": tasks.qsize(),
        "completed_tasks": len(results)
    })


@app.route("/", methods=["GET"])
def index():
    """Gateway information."""
    return jsonify({
        "name": "Mini-SWE-Agent A2A Gateway",
        "version": "1.0.0",
        "endpoints": {
            "agent_registration": "/api/v1/agents/register",
            "task_polling": "/api/v1/agents/{agent_id}/tasks/next",
            "result_submission": "/api/v1/tasks/{task_id}/result",
            "heartbeat": "/api/v1/agents/{agent_id}/heartbeat",
            "admin_tasks": "/admin/tasks",
            "admin_agents": "/admin/agents",
            "health": "/health"
        }
    })


if __name__ == "__main__":
    print("=" * 60)
    print("Starting Mini-SWE-Agent A2A Gateway")
    print("=" * 60)
    print()
    print("Gateway: http://localhost:8000")
    print("Health:  http://localhost:8000/health")
    print("Admin:   http://localhost:8000/admin/agents")
    print()
    print("To add a task:")
    print('  curl -X POST http://localhost:8000/admin/tasks \\')
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"description": "Your task here"}\'')
    print()
    print("To start an agent:")
    print("  mini-a2a --gateway http://localhost:8000 --model gpt-4")
    print()
    print("=" * 60)
    print()
    
    app.run(host="0.0.0.0", port=8000, debug=True)
