# Qwen Code HTTP Wrapper

HTTP wrapper for the Qwen Code Core module with Ollama support. This project enables integration of AI-powered coding assistance into multi-agent orchestration systems via a REST API with real-time event streaming.

## 🎯 Overview

This repository provides an HTTP interface to the Qwen Code Core module, allowing you to:

- Execute AI-powered coding tasks via REST API
- Monitor agent activities in real-time using Server-Sent Events (SSE)
- Handle bidirectional communication (questions/answers) between AI and orchestrator
- Use any Ollama model (gpt-oss:20b, llama3, deepseek-r1, etc.)
- Access all core tools (filesystem, grep, shell commands, etc.)

## 📦 Project Structure

```
qwen-code/
├── packages/
│   ├── core/           # Qwen Code Core module (AI operations)
│   ├── http-wrapper/   # HTTP API wrapper (main project)
│   └── test-utils/     # Testing utilities
├── package.json        # Root workspace configuration
├── pnpm-workspace.yaml # pnpm workspace setup
└── README.md          # This file
```

## 🚀 Quick Start

### Prerequisites

- Node.js >= 20.0.0
- pnpm (recommended) or npm
- Ollama running locally with a model installed

### 1. Install Dependencies

```bash
# Install pnpm if you haven't already
npm install -g pnpm

# Install dependencies
pnpm install
```

### 2. Start Ollama

```bash
# Make sure Ollama is running
ollama serve

# Pull a model if needed
ollama pull gpt-oss:20b
```

### 3. Start the HTTP Wrapper

```bash
# Development mode (with hot reload)
pnpm run dev

# Or use the convenience script
pnpm run dev:http-wrapper
```

The server will start on `http://localhost:3000`.

### 4. Test It

```bash
# Simple test
curl -X POST http://localhost:3000/api/task/start \
  -H "Content-Type: application/json" \
  -d '{"task": "Say hello and introduce yourself"}'

# Get task status (replace TASK_ID with the ID from above)
curl http://localhost:3000/api/task/TASK_ID/status

# Stream real-time events
curl -N http://localhost:3000/api/task/TASK_ID/stream
```

## 📚 Documentation

- **HTTP Wrapper API**: See `packages/http-wrapper/README.md` for detailed API documentation
- **Configuration**: The wrapper defaults to Ollama at `http://localhost:11434/v1` with the `gpt-oss:20b` model
- **Integration Examples**: Python and JavaScript examples are available in the wrapper's README

## 🛠️ Development

### Build

```bash
# Build all packages
pnpm run build

# Build only core
pnpm run build:core

# Build only HTTP wrapper
pnpm run build:http-wrapper
```

### Test

```bash
# Run tests for all packages
pnpm run test
```

### Type Check

```bash
# Type check all packages
pnpm run typecheck
```

## 🔧 Configuration

The HTTP wrapper is pre-configured for Ollama but supports various configurations:

### Environment Variables

```bash
# Default model
DEFAULT_MODEL=gpt-oss:20b

# Ollama API endpoint
OLLAMA_BASE_URL=http://localhost:11434/v1

# Server port
PORT=3000
```

### Per-Request Configuration

```bash
curl -X POST http://localhost:3000/api/task/start \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Your task here",
    "config": {
      "model": "llama3:latest",
      "workingDirectory": "/path/to/project",
      "maxTurns": 30
    }
  }'
```

## 🎨 Use Cases

### Multi-Agent Systems

Integrate this wrapper into your orchestrator to give agents coding capabilities:

```python
import requests

class CodingAgent:
    def __init__(self):
        self.base_url = "http://localhost:3000"
    
    def execute_task(self, task, working_dir):
        response = requests.post(
            f"{self.base_url}/api/task/start",
            json={
                "task": task,
                "config": {"workingDirectory": working_dir}
            }
        )
        return response.json()['taskId']
    
    def get_result(self, task_id):
        response = requests.get(
            f"{self.base_url}/api/task/{task_id}/status"
        )
        return response.json()
```

### Autonomous Development

Let the AI analyze, modify, and test codebases autonomously:

```bash
curl -X POST http://localhost:3000/api/task/start \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Analyze the codebase, identify performance bottlenecks, and suggest optimizations",
    "config": {
      "workingDirectory": "/Users/you/project",
      "maxTurns": 50
    }
  }'
```

## 🌟 Features

- ✅ **REST API**: Simple HTTP interface for task management
- ✅ **Real-time Streaming**: SSE for monitoring agent thoughts and tool calls
- ✅ **Question Handling**: Bidirectional communication for clarifications
- ✅ **Ollama Support**: Use local models (no API keys needed)
- ✅ **Tool Access**: Full access to filesystem, grep, shell, and more
- ✅ **Task Management**: Start, monitor, answer, cancel, and list tasks
- ✅ **Multiple Models**: Switch between any Ollama model on-the-fly

## 📊 Available Ollama Models

You can use any model installed in Ollama:

```bash
# List your models
ollama list

# Examples:
# - gpt-oss:20b
# - llama3:latest
# - llama3.2:latest
# - deepseek-r1:8b
# - mistral:7b
# - codellama:latest
```

## 🤝 Contributing

This is a specialized HTTP wrapper project. For core functionality improvements, refer to the original Qwen Code repository.

## 📄 License

See original Qwen Code license.

## 🔗 Links

- [Ollama](https://ollama.ai/)
- [Qwen Code](https://github.com/QwenLM/qwen-code)

## 🆘 Troubleshooting

### Server won't start

```bash
# Kill any process on port 3000
lsof -ti:3000 | xargs kill -9

# Restart
pnpm run dev
```

### Ollama not responding

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve
```

### Model not found

```bash
# Pull the model
ollama pull gpt-oss:20b
```

## ✅ Status

🟢 **Fully Operational**
- Core module: Working
- HTTP wrapper: Working
- Ollama integration: Working
- All tools: Accessible
- SSE streaming: Working

---

**Built for multi-agent orchestration systems** 🤖
