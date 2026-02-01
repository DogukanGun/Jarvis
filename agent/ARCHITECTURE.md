# Jarvis Agent Architecture

## Overview

Jarvis is a multi-agent AI system with a hierarchical architecture. The General Agent acts as the central orchestrator, deciding whether to answer questions directly or delegate tasks to specialized agents.

## System Flow

```
User Request
     │
     ▼
┌─────────────┐
│   Router    │ (Port 8083)
│  (simple)   │
└──────┬──────┘
       │ HTTP forward
       ▼
┌─────────────┐     ┌──────────────────┐
│   General   │────▶│ Episodic Memory  │ (Port 8085)
│   Agent     │◀────│ (context/store)  │
│(Orchestrator│     └──────────────────┘
│  Port 8081) │
└──────┬──────┘
       │ LLM decides
       │
  ┌────┴────┬────────────┐
  │         │            │
  ▼         ▼            ▼
Answer   GUI Agent   Visual Analyser
Directly (Port 8082) (Port 8084)
         via Kafka    via Kafka
```

## Components

### 1. Router Service (Port 8083)

**Location:** `router/`

**Purpose:** Simple passthrough that forwards all requests to the General Agent.

**Endpoints:**
- `POST /message` - Forward user message to General Agent
- `GET /health` - Health check

**Files:**
- `router/main.go` - HTTP server
- `router/router_service.go` - Request forwarding logic

### 2. General Agent / Orchestrator (Port 8081)

**Location:** `general/`

**Purpose:** Central decision-maker that:
1. Queries Episodic Memory for context
2. Decides whether to answer directly or delegate
3. Executes the decision
4. Stores interaction in Episodic Memory

**Decision Logic:**
- **Answer directly:** Simple questions, personal queries, general knowledge, explanations
- **Delegate to GUI Agent:** Mouse/keyboard control, screenshots, opening applications, desktop automation
- **Delegate to Visual Analyser:** Image analysis, visual similarity, IP protection

**Endpoints:**
- `POST /agent` - Process user message
- `GET /health` - Health check
- `GET /capabilities` - List available capabilities

**Files:**
- `general/agent_http.go` - HTTP server
- `general/creator.go` - Agent logic, delegation, memory integration
- `general/memory/episodic_client.go` - Episodic Memory HTTP client

**Available Tools:**
- File Operations: read_file, write_file, delete_file, list_files
- Code Execution: run_code, execute_terminal, evaluate_expression
- Environment: install_package, check_version, lint_code
- Communication: commit_to_git, create_pull_request, comment_diff
- Web: web_scraper, Wikipedia

### 3. Episodic Memory Service (Port 8085)

**Location:** `memory/episodic/`

**Purpose:** Stores and retrieves user interactions, preferences, and context using a LangGraph-based pipeline.

**Endpoints:**
- `POST /query` - Query memory and get LLM response
- `POST /context` - Get memory context without LLM (used by General Agent)
- `POST /store` - Store an interaction
- `GET /health` - Health check

**Files:**
- `memory/episodic/app/api.py` - FastAPI HTTP server
- `memory/episodic/app/graphs/main_graph/graph.py` - LangGraph pipeline
- `memory/episodic/app/config.py` - Configuration

**Storage:**
- SQLite for short-term episodes
- mem0 API for long-term persistent memory

**Pipeline Nodes:**
1. `preprocess_input` - Normalize prompt, detect task type, extract entities
2. `mem0_needed` - Decide if long-term memory reload needed
3. `load_mem0` / `use_mem0_state` - Load or use cached mem0 state
4. `retrieve_episodes` - Query SQLite and mem0 for relevant context
5. `compose_context` - Build context for LLM
6. `llm_step` - Generate response
7. `return_output` - Format response
8. `enqueue_memory_write_graph` - Async memory storage

### 4. GUI Agent (Port 8082)

**Location:** `gui/gui-agent/`

**Purpose:** Desktop automation - mouse/keyboard control, screenshots, opening applications.

**Communication:** Receives tasks via Kafka topic `gui-agent-requests`

**Dependencies:**
- GUI Daemon (Port 9990) - XDotool wrapper for actual GUI control
- Visual Analyser - For screen analysis

### 5. Visual Analyser (Port 8084)

**Location:** `visual_analyser/`

**Purpose:** Image analysis using vision models.

**Communication:** Receives tasks via Kafka topic `visual-analyser-requests`

**Uses:** Ollama with llama3.2-vision model

### 6. GUI Daemon (Port 9990)

**Location:** `gui/gui-daemon/`

**Purpose:** Low-level GUI control using XDotool.

**Capabilities:**
- Mouse movement and clicks
- Keyboard input
- Screenshot capture
- Window management

## Infrastructure

### Kafka Message Broker (Port 9092)

**Topics:**
- `general-agent-requests` - Requests to General Agent
- `gui-agent-requests` - Tasks for GUI Agent
- `visual-analyser-requests` - Tasks for Visual Analyser
- `memory.approval.request` - Memory promotion approval requests
- `memory.approval.response` - Memory promotion approval responses

**Message Format:**
```go
type AgentMessage struct {
    ID        string // Unique message ID
    UserID    string // User identifier
    Demand    string // The task/request
    Timestamp int64  // Unix timestamp
    ImageData string // Base64 encoded (optional)
}
```

### Ollama LLM Service (Port 11434)

Shared LLM service used by all agents.

**Models:**
- `llama3.2` - Text generation
- `llama3.2-vision` - Image analysis
- `nomic-embed-text` - Embeddings for memory

### PostgreSQL with pgvector (Port 5432)

Used by Visual Analyser for image storage and similarity search.

### Neo4j (Port 7687)

Legacy knowledge graph database. Currently not used by the main flow.

## Docker Services

| Service | Port | Purpose |
|---------|------|---------|
| agent-router | 8083 | Request entry point |
| agent-general | 8081 | Orchestrator |
| episodic-memory | 8085 | Memory service |
| agent-gui | 8082 | GUI automation |
| visual-analyser | 8084 | Image analysis |
| gui-daemon | 9990 | Low-level GUI control |
| ollama | 11434 | LLM service |
| kafka | 9092 | Message broker |
| zookeeper | 2181 | Kafka coordination |
| postgres | 5432 | Database |
| neo4j | 7687 | Legacy graph DB |

## Environment Variables

### General Agent
```
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2
EPISODIC_MEMORY_URL=http://episodic-memory:8085
KAFKA_BROKERS=kafka:29092
USER_ID=default
```

### Episodic Memory
```
OLLAMA_BASE_URL=http://ollama:11434
LLM_MODEL=llama3.2
KAFKA_BOOTSTRAP_SERVERS=kafka:29092
SQLITE_DB_PATH=/data/jarvis_episodes.db
```

### Router
```
GENERAL_AGENT_URL=http://agent-general:8080
KAFKA_BROKERS=kafka:29092
USER_ID=default
```

## Request Flow Example

### Simple Question: "What is the capital of France?"

1. User sends request to Router (8083)
2. Router forwards to General Agent (8081)
3. General Agent queries Episodic Memory for context
4. General Agent decides: "answer" (simple question)
5. General Agent uses LLM to answer directly
6. Response returned to user
7. Interaction stored in Episodic Memory (async)

### GUI Task: "Take a screenshot"

1. User sends request to Router (8083)
2. Router forwards to General Agent (8081)
3. General Agent queries Episodic Memory for context
4. General Agent decides: "delegate_gui" (GUI automation)
5. General Agent sends task to GUI Agent via Kafka
6. GUI Agent processes task using GUI Daemon
7. Response: "Task delegated to GUI Agent"

### Image Analysis: "Analyze this image for similar content"

1. User sends request to Router (8083)
2. Router forwards to General Agent (8081)
3. General Agent queries Episodic Memory for context
4. General Agent decides: "delegate_visual" (image analysis)
5. General Agent sends task to Visual Analyser via Kafka
6. Visual Analyser processes using vision model
7. Response: "Task delegated to Visual Analyser"

## Running the System

```bash
cd agent
docker-compose up -d
```

### Health Checks

```bash
# Router
curl http://localhost:8083/health

# General Agent
curl http://localhost:8081/health

# Episodic Memory
curl http://localhost:8085/health

# GUI Agent
curl http://localhost:8082/health

# Visual Analyser
curl http://localhost:8084/health
```

### Send a Message

```bash
curl -X POST http://localhost:8083/message \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the capital of France?"}'
```

## File Structure

```
agent/
├── docker-compose.yml          # Service orchestration
├── ARCHITECTURE.md             # This file
├── router/                     # Router service
│   ├── main.go
│   ├── router_service.go
│   └── Dockerfile
├── general/                    # General Agent (Orchestrator)
│   ├── agent_http.go
│   ├── creator.go
│   ├── memory/
│   │   └── episodic_client.go
│   └── Dockerfile
├── memory/
│   └── episodic/              # Episodic Memory service
│       ├── app/
│       │   ├── api.py         # HTTP API
│       │   ├── config.py
│       │   ├── graphs/
│       │   │   ├── main_graph/
│       │   │   ├── memory_write_graph/
│       │   │   ├── reflection_graph/
│       │   │   └── user_approval_graph/
│       │   └── ...
│       └── Dockerfile
├── gui/
│   ├── gui-agent/             # GUI Agent
│   └── gui-daemon/            # GUI Daemon
├── visual_analyser/           # Visual Analyser
├── tools/                     # Shared tools
├── utils/
│   └── kafka/                 # Kafka utilities
└── ollama/                    # Ollama service
```
