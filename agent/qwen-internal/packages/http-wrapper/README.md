# Qwen Code HTTP Wrapper

HTTP server wrapper for integrating Qwen Code's AI agent capabilities into multi-agent orchestrator systems. Provides REST API + Server-Sent Events (SSE) for real-time task monitoring and bidirectional question/answer flow.

## Features

- **RESTful API** for task management (start, cancel, status)
- **Server-Sent Events (SSE)** for real-time progress monitoring
- **Question/Answer Flow** with dual detection methods:
  - Explicit `ask_question` tool for agents
  - Implicit question detection from response patterns
- **Concurrent Task Execution** with isolated environments
- **Full Tool Access** to Qwen Code's capabilities (file operations, shell, web search, etc.)
- **TypeScript** with full type safety

## Architecture

```
┌─────────────────┐
│  Orchestrator   │
│     Agent       │
└────────┬────────┘
         │
         │ REST + SSE
         ▼
┌─────────────────┐
│   HTTP Server   │
│  (Express+SSE)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Wrapper Service │
│  Task Manager   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Qwen Code      │
│  @core Module   │
│  (GeminiClient) │
└─────────────────┘
```

## Installation

```bash
# Install dependencies
cd packages/http-wrapper
npm install

# Build
npm run build

# Development mode
npm run dev

# Production mode
npm start
```

## Quick Start

### 1. Start the Server

```bash
# Default port 3000
npm start

# Custom port
PORT=8080 npm start
```

### 2. Send a Task

```bash
curl -X POST http://localhost:3000/api/task/start \
  -H "Content-Type: application/json" \
  -d '{
    "task": "Analyze the codebase and find potential bugs",
    "config": {
      "workingDirectory": "/path/to/project",
      "model": "gemini-2.0-flash-exp",
      "maxTurns": 50
    }
  }'
```

Response:
```json
{
  "taskId": "abc-123-def",
  "streamUrl": "/api/task/abc-123-def/stream",
  "status": "pending"
}
```

### 3. Stream Events (SSE)

```bash
curl -N http://localhost:3000/api/task/abc-123-def/stream
```

Events:
```
event: thought
data: {"type":"thought","timestamp":1234567890,"taskId":"abc-123","content":"I'll search for common bug patterns..."}

event: tool_call
data: {"type":"tool_call","timestamp":1234567891,"taskId":"abc-123","callId":"call-1","name":"codebase_search","args":{...}}

event: question
data: {"type":"question","timestamp":1234567892,"taskId":"abc-123","question":"Should I check database queries or frontend code first?","questionId":"q-456"}

event: completed
data: {"type":"completed","timestamp":1234567893,"taskId":"abc-123","result":"Found 5 potential bugs..."}
```

### 4. Answer Questions

```bash
curl -X POST http://localhost:3000/api/task/abc-123-def/answer \
  -H "Content-Type: application/json" \
  -d '{"answer": "Check database queries first"}'
```

## API Reference

### POST `/api/task/start`

Start a new task.

**Request Body:**
```typescript
{
  task: string;           // The task description
  config?: {
    model?: string;       // AI model (default: gemini-2.0-flash-exp)
    maxTurns?: number;    // Max conversation turns (default: 100)
    approvalMode?: 'auto' | 'manual';
    allowedTools?: string[];
    workingDirectory?: string;
    timeout?: number;     // Minutes
    apiKey?: string;      // API key if needed
  }
}
```

**Response:**
```typescript
{
  taskId: string;
  streamUrl: string;
  status: 'pending';
}
```

### GET `/api/task/:taskId/stream`

Stream task events in real-time using Server-Sent Events (SSE).

**Event Types:**

| Event | Description | Data Fields |
|-------|-------------|-------------|
| `thought` | Agent's reasoning | `content` |
| `content` | Text response | `text` |
| `tool_call` | Tool execution request | `callId`, `name`, `args` |
| `tool_result` | Tool execution result | `callId`, `result`, `success` |
| `question` | Agent asking for input | `question`, `context`, `questionId` |
| `completed` | Task finished | `result`, `finalText` |
| `error` | Error occurred | `error`, `reason` |
| `status` | Status update | `status`, `message` |

### POST `/api/task/:taskId/answer`

Answer a pending question.

**Request Body:**
```typescript
{
  answer: string;
}
```

**Response:**
```typescript
{
  success: boolean;
  message: string;
}
```

### GET `/api/task/:taskId/status`

Get current task status.

**Response:**
```typescript
{
  taskId: string;
  status: 'pending' | 'running' | 'waiting_for_answer' | 'completed' | 'error' | 'cancelled';
  task: string;
  createdAt: number;
  startedAt?: number;
  completedAt?: number;
  result?: string;
  error?: string;
  hasPendingQuestion: boolean;
  pendingQuestion?: {
    questionId: string;
    question: string;
    context?: string;
  };
}
```

### POST `/api/task/:taskId/cancel`

Cancel a running task.

**Response:**
```typescript
{
  success: boolean;
  message: string;
  taskId: string;
}
```

### GET `/api/tasks`

List all tasks.

**Response:**
```typescript
{
  tasks: Array<{
    taskId: string;
    status: string;
    task: string;
    createdAt: number;
    startedAt?: number;
    completedAt?: number;
    hasPendingQuestion: boolean;
  }>;
}
```

### GET `/health`

Health check endpoint.

**Response:**
```typescript
{
  status: 'ok';
  timestamp: number;
  activeTasks: number;
}
```

## Usage Examples

### Basic TypeScript Client

```typescript
import { OrchestratorClient } from './examples/orchestrator-client';

const client = new OrchestratorClient('http://localhost:3000');

// Start a task
const { taskId } = await client.startTask('Analyze the codebase');

// Stream events
await client.streamTask(
  taskId,
  async (event) => {
    if (event.type === 'question') {
      console.log('Question:', event.question);
      await client.answerQuestion(taskId, 'Continue with analysis');
    } else if (event.type === 'content') {
      console.log('Response:', event.text);
    }
  },
  () => console.log('Completed'),
  (error) => console.error('Error:', error)
);
```

### Multi-Agent Orchestrator

```typescript
// Run multiple agents in parallel
const agents = [
  { name: 'Analyzer', task: 'Analyze code quality' },
  { name: 'Security', task: 'Check security issues' },
  { name: 'Docs', task: 'Review documentation' },
];

const results = await Promise.all(
  agents.map(async (agent) => {
    const { taskId } = await client.startTask(agent.task);
    
    return new Promise((resolve) => {
      client.streamTask(
        taskId,
        async (event) => {
          if (event.type === 'completed') {
            resolve({ agent: agent.name, result: event.result });
          }
        },
        () => {},
        (error) => console.error(error)
      );
    });
  })
);

console.log('All agents completed:', results);
```

### Python Client Example

```python
import requests
import json

class QwenCodeClient:
    def __init__(self, base_url='http://localhost:3000'):
        self.base_url = base_url
    
    def start_task(self, task, config=None):
        response = requests.post(
            f'{self.base_url}/api/task/start',
            json={'task': task, 'config': config or {}}
        )
        return response.json()
    
    def stream_events(self, task_id):
        response = requests.get(
            f'{self.base_url}/api/task/{task_id}/stream',
            stream=True
        )
        
        for line in response.iter_lines():
            if line.startswith(b'data:'):
                data = json.loads(line[5:])
                yield data
    
    def answer_question(self, task_id, answer):
        requests.post(
            f'{self.base_url}/api/task/{task_id}/answer',
            json={'answer': answer}
        )

# Usage
client = QwenCodeClient()
result = client.start_task('Analyze the codebase')
task_id = result['taskId']

for event in client.stream_events(task_id):
    if event['type'] == 'question':
        print(f"Question: {event['question']}")
        client.answer_question(task_id, 'Proceed')
    elif event['type'] == 'completed':
        print(f"Result: {event['result']}")
        break
```

## Question Detection

The wrapper supports two methods for detecting when the agent needs user input:

### 1. Explicit Method (Recommended)

The agent explicitly calls the `ask_question` tool:

```typescript
// Agent's perspective
await askQuestion({
  question: "Which approach should I use?",
  context: "I found two possible solutions..."
});
```

### 2. Implicit Method

Automatically detects questions from:
- Responses ending with `?`
- Common question patterns
- Waiting states (no pending tool calls)

Example detected patterns:
- "Should I continue with this approach?"
- "Which option would you prefer?"
- "Please let me know how to proceed"

## Configuration Options

```typescript
interface WrapperConfig {
  model?: string;              // AI model name
  maxTurns?: number;           // Max conversation turns
  approvalMode?: 'auto' | 'manual';
  allowedTools?: string[];     // Restrict tools (default: all)
  workingDirectory?: string;   // Working directory
  timeout?: number;            // Timeout in minutes
  apiKey?: string;             // API key
}
```

## Environment Variables

```bash
PORT=3000                      # Server port
GEMINI_API_KEY=your-key       # API key for Gemini
NODE_ENV=production           # Environment
```

## Development

### Run Tests

```bash
npm test
```

### Type Checking

```bash
npm run typecheck
```

### Linting

```bash
npm run lint
```

### Running Examples

```bash
# Simple task
tsx examples/orchestrator-client.ts 1

# Interactive task with questions
tsx examples/orchestrator-client.ts 2

# Multi-agent orchestrator
tsx examples/orchestrator-client.ts 3
```

## Deployment

### Docker

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY dist ./dist
EXPOSE 3000
CMD ["node", "dist/server.js"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  qwen-wrapper:
    build: .
    ports:
      - "3000:3000"
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - PORT=3000
    restart: unless-stopped
```

## Troubleshooting

### Events not streaming

Ensure your HTTP client supports SSE and doesn't buffer responses. Use `-N` flag with curl or set appropriate headers.

### Questions not detected

Use the explicit `ask_question` tool for reliable detection. Implicit detection is best-effort.

### Task stuck in "running" state

Check the server logs for errors. Tasks auto-cleanup after 1 hour of completion.

### Connection timeout

SSE connections send keepalive pings every 30 seconds. Ensure your proxy/firewall allows long-lived connections.

## License

Apache-2.0

## Contributing

This is part of the Qwen Code project. See the main repository for contribution guidelines.

