# JARVIS Multi-Agent System - Comprehensive Architecture Report

## Executive Summary

Jarvis is a sophisticated, distributed multi-agent orchestration platform that combines specialized AI agents for different domains (content creation, security analysis, web research, screen analysis) with a unified memory system and inter-agent communication infrastructure. The system uses LangGraph for workflow orchestration, Kafka for asynchronous message passing, and Ollama as the primary LLM backend.

**Key Characteristics:**
- **Modular Architecture**: Each agent is independently deployable
- **Scalable Communication**: Kafka-based async messaging for decoupled operations
- **Memory Intelligence**: Two-tier memory system (episodic + long-term)
- **Safety-First Design**: Multi-phase validation before execution
- **LLM Agnostic**: Supports Ollama, OpenAI, and other backends

---

# AGENTS OVERVIEW

## 1. General Agent
**Purpose:** General-purpose AI assistant with research and task execution capabilities

**Architecture:**
- FastAPI REST server (port 8080)
- LangChain ReAct framework for agentic reasoning
- Integrated tool ecosystem

**Capabilities:**
```
┌─────────────────────────────────────┐
│     GENERAL AGENT (port 8080)       │
├─────────────────────────────────────┤
│ ✓ Web Search (Brave/Perplexity)    │
│ ✓ Web Fetching & Content Extract   │
│ ✓ Shell Command Execution          │
│ ✓ Browser Automation (Playwright)  │
│ ✓ Cron Job Management              │
│ ✓ LLM: Ollama/OpenAI               │
└─────────────────────────────────────┘
```

**Use Cases:**
- Research tasks and information gathering
- Automated job scheduling
- Web interaction and automation
- General problem-solving queries

**Dependencies:**
- Ollama (llama3.2) or OpenAI (gpt-4o-mini)
- Tool Server (localhost:3000)
- Optional: Brave Search API, Perplexity API

---

## 2. Hacker Agent
**Purpose:** Security reconnaissance and network analysis

**Architecture:**
- Dual-phase reasoning system (Planner → Compiler)
- Multi-stage validation pipeline
- Safety guards for execution

**Capabilities:**
```
┌───────────────────────────────────────┐
│     HACKER AGENT (port 8000)          │
├───────────────────────────────────────┤
│ Security Tools:                       │
│ ✓ Domain DNS Reconnaissance           │
│ ✓ IP Resolution & Ping                │
│ ✓ Network Discovery (nmap)            │
│ ✓ OSINT (ReconSpider)                │
│ ✓ Password Cracking (John)            │
│ ✓ Port Scanning (netcat)              │
│ ✓ Reverse Lookup (whois)              │
│ ✓ SQL Injection Testing (sqlmap)      │
│ ✓ SSH Brute Force                     │
│                                       │
│ Execution Modes:                      │
│ ✓ Synchronous (immediate)            │
│ ✓ Asynchronous (background jobs)     │
└───────────────────────────────────────┘
```

**Execution Pipeline:**
```
User Input
    ↓
┌─────────────────────────────────────┐
│  PLANNER (Context-aware)             │
│  Decides what to do                  │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  COMPILER (Context-blind)            │
│  Converts to tool calls              │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  VALIDATOR (Safety check)            │
│  Validates before execution          │
└──────────────┬──────────────────────┘
               ↓
         (Valid? → Yes)
               ↓
┌─────────────────────────────────────┐
│  EXECUTOR (Tool runner)              │
│  Executes validated tools            │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  GUARDS (Post-execution checks)      │
│  Safety verification                 │
└─────────────────────────────────────┘
```

**API Endpoints:**
- `POST /run` - Execute security task
- `GET /tasks/{task_id}` - Get task status
- `GET /tasks` - List all tasks
- `DELETE /tasks/{task_id}` - Delete task

**Use Cases:**
- Network security assessments
- Vulnerability scanning
- OSINT investigations
- Penetration testing (authorized)
- Infrastructure audits

---

## 3. Content Creator Agent
**Purpose:** Media rendering pipeline for images and videos

**Architecture:**
- Kafka-driven worker pool
- Multi-worker parallel processing
- Asset storage in MinIO

**Capabilities:**
```
┌─────────────────────────────────────┐
│   CONTENT CREATOR (Kafka Workers)   │
├─────────────────────────────────────┤
│ ✓ Video Generation (LTX-2)          │
│ ✓ Image from Text Prompts           │
│ ✓ Image Generation with Reference   │
│ ✓ Image Editing/Manipulation        │
│ ✓ Request Validation & Routing      │
│ ✓ Result Upload to MinIO            │
│ ✓ Kafka Integration                 │
└─────────────────────────────────────┘
```

**Worker Pipeline:**
```
Kafka Request Topic
    ↓
┌──────────────────┐
│ ROUTER (Router)  │ - Validates & routes requests
└────────┬─────────┘
         ↓
   ┌─────┴─────┐
   ↓           ↓
┌──────────┐ ┌────────────┐
│ VIDEO    │ │ IMAGE      │ ... (other workers)
│ WORKER   │ │ WORKERS    │
└────┬─────┘ └─────┬──────┘
     ↓             ↓
┌──────────────────────────────────────┐
│ 1. Load Model                        │
│ 2. Generate (with parameters)        │
│ 3. Upload Result (MinIO)             │
│ 4. Publish Result (Kafka)            │
└──────────────────────────────────────┘
```

**Kafka Topics:**
- `media.render.requests` - Incoming work
- `media.render.video.requests` - Video jobs
- `media.render.image.*.requests` - Image variants
- `media.render.results` - Completed work

**Models Used:**
- Image: `CompVis/stable-diffusion-v1-4`
- Video: `Lightricks/LTX-2`

**Use Cases:**
- Automated content generation
- Batch media processing
- AI-powered creative tools
- Multi-format asset generation

---

## 4. Web Fetcher Service
**Purpose:** Web crawling and content extraction

**Architecture:**
- Crawlee (Playwright-based) for browser automation
- In-memory storage per request
- Rate-limited crawling

**Capabilities:**
```
┌────────────────────────────────┐
│    WEB FETCHER SERVICE         │
├────────────────────────────────┤
│ ✓ Single Page Fetch            │
│ ✓ Site Page Discovery          │
│ ✓ Full Site Content Crawling   │
│ ✓ Content Extraction           │
│ ✓ Rate Limiting                │
│ ✓ Configurable Truncation      │
└────────────────────────────────┘
```

**API Endpoints:**
- `POST /page` - Fetch single page
- `POST /site/pages` - Discover all page URLs
- `POST /site/contents` - Extract all page contents

**Safety Limits:**
- Global cap: 500 pages
- Default discovery: 200 pages max
- Default content fetch: 50 pages max
- Per-page limit: 50,000 characters

**Use Cases:**
- Content research and aggregation
- Website archival
- SEO analysis
- Data extraction

---

## 5. Visual Analyser Agent
**Purpose:** GUI screen analysis and understanding

**Architecture:**
- Go-based HTTP server
- Vision LLM integration
- Real-time screen analysis

**Capabilities:**
```
┌────────────────────────────────┐
│  VISUAL ANALYSER (port 8081)   │
├────────────────────────────────┤
│ ✓ Screenshot Analysis          │
│ ✓ UI Element Detection         │
│ ✓ Text Extraction              │
│ ✓ Interactive Element ID       │
│ ✓ Layout Description           │
│ ✓ LLM: llama3.2-vision         │
└────────────────────────────────┘
```

**API Endpoints:**
- `POST /analyze` - Analyze screenshot
- `GET /health` - Health check
- `GET /capabilities` - Agent capabilities

**Use Cases:**
- GUI automation and testing
- Accessibility analysis
- Screen-based interaction
- UI/UX analysis

---

## 6. Qwen Code Agent
**Purpose:** AI-powered code generation and execution

**Architecture:**
- Node.js/TypeScript monorepo
- REST API with SSE streaming
- Real-time event streaming

**Capabilities:**
```
┌────────────────────────────────┐
│   QWEN CODE (port 3000)        │
├────────────────────────────────┤
│ ✓ Code Generation              │
│ ✓ Code Execution               │
│ ✓ Real-time Event Streaming    │
│ ✓ File Operations              │
│ ✓ Shell Command Support        │
│ ✓ Grep & Search                │
│ ✓ Model: gpt-oss:20b, etc.    │
└────────────────────────────────┘
```

**API Endpoints:**
- `POST /api/task/start` - Start coding task
- `GET /api/task/{task_id}/status` - Task status
- `GET /api/task/{task_id}/stream` - Real-time events

**Use Cases:**
- Automated code generation
- Script generation and execution
- Real-time development assistance
- Code-to-deployment automation

---

## 7. Router Service
**Purpose:** Central message routing and agent orchestration

**Architecture:**
- Go-based router
- LLM-based routing decisions
- Context-aware message dispatch

**Capabilities:**
```
┌─────────────────────────────────┐
│    ROUTER SERVICE (Central)     │
├─────────────────────────────────┤
│ ✓ Message Processing            │
│ ✓ Context-aware Routing         │
│ ✓ Tool Dispatch                 │
│ ✓ Image Data Support            │
│ ✓ Model Auto-pulling            │
└─────────────────────────────────┘
```

**Role:**
Routes user messages to appropriate agents based on:
- Message content analysis
- Task type detection
- Agent capabilities
- Context awareness

---

## 8. Memory System

### 8A. Episodic Memory (Short-term)
**Purpose:** Contextual working memory with semantic search

**Architecture:**
```
┌─────────────────────────────────┐
│   EPISODIC MEMORY (SQLite)      │
├─────────────────────────────────┤
│ Storage Type: SQLite DB         │
│ Entry Point: Main Graph (9 node)│
│ Embeddings: Ollama              │
│ Retrieval: Semantic similarity  │
│ Deduplication: Fingerprinting   │
│ Auto-Promotion: To Mem0         │
└─────────────────────────────────┘
```

**Main Pipeline (9 Nodes):**
1. **Preprocess Input** - Normalize prompt, extract entities
2. **Mem0 Check** - Router: decide if long-term memory needed
3. **Load Mem0** - Fetch persistent memory (if needed)
4. **Use Mem0 State** - Apply cached state
5. **Retrieve Episodes** - Query similar past interactions
6. **Compose Context** - Build LLM input from episodes + mem0
7. **LLM Step** - Call LLM with full context
8. **Return Output** - Format response
9. **Enqueue Write** - Queue memory update job

**State Management:**
```
INPUT PHASE:
  - user_id, prompt, context, task_type

PREPROCESSING:
  - normalized_prompt, entities, app detection

MEMORY PHASE:
  - mem0_state, mem0_items, mem0_loaded

RETRIEVAL PHASE:
  - retrieved_episodes (up to 5), similarity scores

LLM PHASE:
  - composed_context, llm_output, memory_intents

OUTPUT PHASE:
  - response_payload, memory_write_job
```

**Supporting Components:**

**Memory Write Graph:**
- Processes memory intents from LLM
- Creates episode candidates
- Performs deduplication
- Generates embeddings

**Reflection Graph (Periodic):**
- Runs on configurable schedule (6 hours default)
- Extracts patterns from recent episodes
- Proposes memory promotions
- Identifies frequently reinforced events

**Approval Graph (Event-driven):**
- Listens to Kafka for user approvals
- Processes promotion confirmations
- Updates Mem0 with approved items

**Configuration:**
```python
EPISODE_RETRIEVE_LIMIT = 5
EPISODE_MIN_IMPORTANCE = 0.3
MAX_EPISODES_IN_CONTEXT = 5
MAX_MEM0_ITEMS_IN_CONTEXT = 10
PROMOTION_THRESHOLD_COUNT = 3
PROMOTION_MIN_CONFIDENCE = 0.7
PROMOTION_LOOKBACK_DAYS = 30
REFLECTION_SCHEDULE_HOURS = 6
```

**Episode Types:**
- INTERACTION - User conversation
- TASK_COMPLETION - Completed action
- ERROR - Failed execution
- OBSERVATION - System event
- USER_FEEDBACK - Explicit feedback

**Use Cases:**
- Context-aware responses
- Consistency in conversations
- Error pattern detection
- Personalized behavior

### 8B. Long-term Memory (Mem0)
**Purpose:** Persistent semantic memory with graph knowledge

**Architecture:**
```
┌─────────────────────────────┐
│   MEM0 LONG-TERM MEMORY     │
├─────────────────────────────┤
│ Vector DB: Qdrant           │
│ Graph DB: Neo4j (optional)  │
│ LLM: Ollama                 │
│ Embeddings: Ollama          │
│ Interface: FastAPI + CLI    │
└─────────────────────────────┘
```

**Features:**
- CRUD operations on memories
- Semantic search across memory
- Graph relationship tracking
- Multi-user support
- Memory metadata & tagging

**Promotion Flow:**
```
Episode Created (Episodic)
    ↓
Reach Reinforcement Threshold
    ↓
Reflection Graph Detects Pattern
    ↓
Promotion Proposal Created
    ↓
User Approval via Kafka
    ↓
Approved → Mem0 Write
    ↓
Long-term Memory Available
```

---

# SYSTEM ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          USER / EXTERNAL INTERFACE                           │
└──────────────────────────┬──────────────────────────────────────────────────┘
                           │
                           ↓
            ┌──────────────────────────────┐
            │    ROUTER SERVICE (Go)       │  ← Central orchestration
            │  (LLM-based routing)         │
            └──────┬───────────────────────┘
                   │
        ┌──────────┼──────────┬────────────────┬──────────────────┐
        ↓          ↓          ↓                ↓                  ↓
    ┌────────┐ ┌────────┐ ┌────────┐  ┌──────────┐  ┌──────────────┐
    │General │ │Hacker  │ │Web     │  │Visual    │  │Qwen Code     │
    │Agent   │ │Agent   │ │Fetcher │  │Analyser  │  │(port 3000)   │
    │(8080)  │ │(8000)  │ │Service │  │(8081)    │  │              │
    └────────┘ └────────┘ └────────┘  └──────────┘  └──────────────┘
        │          │          │            │              │
        │ ReAct    │ Planner→  │ Crawlee    │ Vision LLM    │ TypeScript
        │ + Tools  │ Compiler  │ Playwright │ + HTTP        │ Monorepo
        └────────────────────────────────────────────────────────────────┐
                                 │                                        │
                 ┌───────────────┼───────────────┐                       │
                 ↓               ↓               ↓                       │
    ┌─────────────────────────────────────────────────────────────────┐ │
    │ CONTENT CREATOR AGENT (Kafka Workers)                          │ │
    ├─────────────────────────────────────────────────────────────────┤ │
    │ Router→Video→Image(Prompt)→Image(Ref)→Image(Edit)             │ │
    │ Workers consume: media.render.*.requests                        │ │
    │ Produces: media.render.results                                  │ │
    │ Models: LTX-2, Stable Diffusion                                │ │
    └──────┬────────────────────────────────────────────┬────────────┘ │
           ↓                                            ↓                │
        ┌────────────────────┐              ┌──────────────────────┐   │
        │ KAFKA MESSAGE BUS  │              │   MINIO (S3)         │   │
        │ (async messaging)  │              │   (asset storage)    │   │
        │                    │              │                      │   │
        │ Topics:            │              └──────────────────────┘   │
        │ • media.render.*   │                                        │
        │ • memory.approval  │                                        │
        │ • memory.write     │                                        │
        └────────────────────┘                                        │
           ↓                                                           │
    ┌─────────────────────────────────────────────────────────────────┐ │
    │ MEMORY SYSTEM                                                    │ │
    ├─────────────────────────────────────────────────────────────────┤ │
    │                                                                   │ │
    │ ┌─────────────────────────────┐  ┌──────────────────────────┐   │ │
    │ │ EPISODIC (Short-term)       │  │ MEM0 (Long-term)        │   │ │
    │ ├─────────────────────────────┤  ├──────────────────────────┤   │ │
    │ │ Storage: SQLite             │  │ Vector DB: Qdrant        │   │ │
    │ │ Main Graph: 9 nodes         │  │ Graph DB: Neo4j          │   │ │
    │ │ Retrieval: Semantic search  │  │ Features: CRUD, search   │   │ │
    │ │ Dedup: Fingerprinting       │  │ Promotion from episodic  │   │ │
    │ │                             │  │                          │   │ │
    │ │ Nodes:                      │  │                          │   │ │
    │ │ 1. Preprocess input         │  │                          │   │ │
    │ │ 2. Mem0 needed (router)     │  │                          │   │ │
    │ │ 3. Load mem0                │  │                          │   │ │
    │ │ 4. Use mem0 state           │  │                          │   │ │
    │ │ 5. Retrieve episodes        │  │                          │   │ │
    │ │ 6. Compose context          │  │                          │   │ │
    │ │ 7. LLM step                 │  │                          │   │ │
    │ │ 8. Return output            │  │                          │   │ │
    │ │ 9. Enqueue memory write     │  │                          │   │ │
    │ │                             │  │                          │   │ │
    │ │ Background Processes:       │  │                          │   │ │
    │ │ • Memory Write Graph        │  │                          │   │ │
    │ │ • Reflection Graph (6h)     │  │                          │   │ │
    │ │ • Approval Consumer         │  │                          │   │ │
    │ └─────────────────────────────┘  └──────────────────────────┘   │ │
    │         ↓                                  ↑                    │ │
    │         └──────────────────────────────────┘                    │ │
    │            (Promotion Pipeline)                                 │ │
    └─────────────────────────────────────────────────────────────────┘ │
                                                                         │
                  ┌─────────────────────────────────────────────┐       │
                  │         OLLAMA LLM BACKEND                 │       │
                  ├─────────────────────────────────────────────┤       │
                  │ (localhost:11434)                           │       │
                  │ Models:                                     │       │
                  │ • llama3.2 (default)                       │       │
                  │ • llama3.2-vision (visual analyser)         │       │
                  │ • nomic-embed-text (embeddings)            │       │
                  │ • gpt-oss:20b, deepseek-r1, etc.          │       │
                  └─────────────────────────────────────────────┘       │
                                                                         │
                              [Legend]                                  │
                        ↑ = Data flow                                   │
                        → = Request/Response                            │
                        ─ = Connection                                  │
                                                                         │
└──────────────────────────────────────────────────────────────────────┘
```

---

# INTER-AGENT COMMUNICATION & DEPENDENCIES

## Communication Protocols

### 1. **HTTP REST APIs** (Synchronous)
Used for immediate request-response patterns:

| Agent | Port | Purpose |
|-------|------|---------|
| General Agent | 8080 | Research, tool execution |
| Hacker Agent | 8000 | Security analysis |
| Visual Analyser | 8081 | Screenshot analysis |
| Qwen Code | 3000 | Code generation |
| Web Fetcher | (varies) | Content extraction |
| Mem0 API | (varies) | Memory operations |

### 2. **Kafka Message Bus** (Asynchronous)
Used for decoupled, event-driven communication:

| Topic | Producer | Consumer(s) |
|-------|----------|------------|
| `media.render.requests` | Router | Content Creator Router |
| `media.render.video.requests` | Content Creator Router | Video Worker |
| `media.render.image.*.requests` | Content Creator Router | Image Workers |
| `media.render.results` | All Workers | External systems |
| `memory.approval.request` | Memory Write Graph | User Approval System |
| `memory.approval.response` | User Approval | Memory System |

### 3. **LLM Backend** (Ollama)
Shared LLM service used by all agents:
- Port: 11434
- Primary Backend: Ollama
- Fallback: OpenAI API
- Models: Configurable per agent

### 4. **Data Storage**
Persistent storage for various agent states:

| Type | Tool | Used By |
|------|------|---------|
| Vector Embeddings | Qdrant | Mem0, Memory Write |
| Relational Data | SQLite | Episodic Memory |
| Graph Knowledge | Neo4j | Mem0 (optional) |
| Media Assets | MinIO (S3) | Content Creator |

---

# ARCHITECTURAL PATTERNS

## 1. LangGraph-Based Workflow Orchestration
All Python agents use LangGraph's StateGraph pattern:

```python
# Pattern: State-driven workflow
graph = StateGraph(StateSchema)
graph.add_node("step1", process_fn1)
graph.add_node("step2", process_fn2)
graph.add_edge("step1", "step2")
graph.add_conditional_edges("step2", router_fn, {"path_a": "step3a", "path_b": "step3b"})
graph.compile()
```

**Benefits:**
- Deterministic execution
- State type safety (TypedDict)
- Easy debugging and visualization
- Natural conditional routing
- Testable components

## 2. Multi-Phase Reasoning (Hacker Agent)
Complex decision-making with staged validation:

```
Context-Aware Phase: Planner decides WHAT to do
                         ↓
Context-Blind Phase: Compiler decides HOW to do it
                         ↓
Validation Phase: Validator checks if safe
                         ↓
Execution Phase: Executor runs safe commands
                         ↓
Safety Phase: Guards verify post-execution
```

**Benefits:**
- Separation of concerns
- Prevents context leakage
- Safety-first approach
- Auditability

## 3. Worker Pool Architecture (Content Creator)
Kafka-driven parallel processing:

```
Kafka Topic → Worker Pool (N instances)
                     ↓
         1. Load Model (async)
         2. Generate (parallel)
         3. Upload Result
         4. Publish Completion
```

**Benefits:**
- Horizontal scaling
- Loose coupling
- Backpressure handling
- Graceful shutdown

## 4. Two-Tier Memory Hierarchy
Automatic learning and knowledge elevation:

```
Episodic (Fast, Contextual)
         ↓
    [Reinforcement Counter]
    [Pattern Extraction]
         ↓
Approved by User
         ↓
Mem0 (Persistent, Semantic)
```

**Benefits:**
- Lightweight working memory
- Intelligent promotion
- User feedback integration
- Scalable knowledge base

## 5. Tool Registry Pattern
Safe, validated tool invocation:

```
Tool Definition → Registration → Validation → Execution
```

Each tool:
- Has explicit input/output schema
- Is validated before execution
- Can be disabled/enabled
- Produces audit logs

## 6. Event-Driven State Machine
Kafka enables reactive, asynchronous operations:

```
Event Generated
     ↓
Multiple Consumers React in Parallel
     ↓
State Updated
     ↓
Downstream Events Triggered
```

## 7. Context Composition
Building rich LLM context from multiple sources:

```
User Input
    ↓
+ Retrieved Episodes (semantic search)
    ↓
+ Mem0 Items (persistent memory)
    ↓
+ Current State
    ↓
= Complete Context → LLM
```

---

# DATA FLOW EXAMPLE: Complete User Journey

```
┌─────────────────────────────────────────────────────────────────┐
│ USER REQUEST: "Show me network vulnerabilities on example.com"  │
└────────────────┬────────────────────────────────────────────────┘
                 ↓
        ┌──────────────────────┐
        │  Router Service      │
        │  (LLM decides: need   │
        │   Hacker Agent)      │
        └────────┬─────────────┘
                 ↓
        ┌──────────────────────────────────────┐
        │  HACKER AGENT (port 8000)            │
        │  Request queued for processing       │
        └────────┬─────────────────────────────┘
                 ↓
    ┌────────────────────────────┐
    │ PLANNER NODE               │
    │ (Context-aware)            │
    │ Decision:                  │
    │ - Use nmap for port scan   │
    │ - Use whois for DNS info   │
    └────────┬───────────────────┘
             ↓
    ┌────────────────────────────┐
    │ COMPILER NODE              │
    │ (Translate to tool calls)  │
    └────────┬───────────────────┘
             ↓
    ┌────────────────────────────┐
    │ VALIDATOR NODE             │
    │ Safety checks:             │
    │ ✓ Valid tool calls         │
    │ ✓ No command injection     │
    │ ✓ Authorized domain        │
    └────────┬───────────────────┘
             ↓ (Valid)
    ┌────────────────────────────┐
    │ EXECUTOR NODE              │
    │ 1. nmap scan               │
    │ 2. whois lookup            │
    │ 3. gather results          │
    └────────┬───────────────────┘
             ↓
    ┌────────────────────────────┐
    │ GUARDS NODE                │
    │ Post-execution safety:     │
    │ ✓ Results sanitized        │
    │ ✓ No credential exposure   │
    └────────┬───────────────────┘
             ↓
        ┌──────────────────────────────┐
        │ RESPONSE COMPILED            │
        │ - Scan results              │
        │ - DNS information           │
        │ - Analysis                  │
        └────────┬─────────────────────┘
                 ↓
        ┌──────────────────────────────┐
        │ EPISODIC MEMORY SYSTEM       │
        │ (Background)                 │
        │ 1. Create episode record     │
        │ 2. Generate embedding       │
        │ 3. Deduplication check      │
        │ 4. Store in SQLite          │
        └────────┬─────────────────────┘
                 ↓
        ┌──────────────────────────────┐
        │ Kafka Event: memory.write    │
        │ - Episode created           │
        │ - Indexed and searchable    │
        └──────────────────────────────┘
                 ↓
        ┌──────────────────────────────┐
        │ MEMORY WRITE GRAPH           │
        │ (Async worker)               │
        │ 1. Process memory intents   │
        │ 2. Create candidates        │
        │ 3. Embed using Ollama       │
        │ 4. Store finalized episode  │
        └──────────────────────────────┘
                 ↓
        ┌──────────────────────────────┐
        │ PERIODIC REFLECTION          │
        │ (Every 6 hours)              │
        │ 1. Analyze recent episodes  │
        │ 2. Extract patterns         │
        │ 3. Propose promotions       │
        │ 4. Publish to Kafka         │
        └──────────────────────────────┘
                 ↓
        ┌──────────────────────────────┐
        │ USER APPROVAL SYSTEM         │
        │ User reviews proposals:      │
        │ - Accept pattern → Mem0      │
        │ - Reject → Stay episodic    │
        └──────────────────────────────┘
                 ↓
        ┌──────────────────────────────┐
        │ MEM0 LONG-TERM MEMORY        │
        │ (If approved)                │
        │ Pattern available for:       │
        │ - Future requests           │
        │ - Similar queries           │
        │ - Pattern matching          │
        └──────────────────────────────┘

RESULT: User gets immediate response + system learns for future
```

---

# TECHNOLOGY STACK

## Core Technologies

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **LLM Framework** | LangChain (Python), LangChain Go | Agentic reasoning, tool integration |
| **Workflow Engine** | LangGraph | State-driven workflow orchestration |
| **Web Framework** | FastAPI | REST API servers (Python agents) |
| **Message Queue** | Apache Kafka | Async inter-agent communication |
| **LLM Backend** | Ollama (primary), OpenAI (fallback) | Language model inference |
| **Embeddings** | Ollama (nomic-embed-text) | Semantic similarity search |
| **Vector Database** | Qdrant | Embedding storage & semantic search |
| **Graph Database** | Neo4j (optional) | Knowledge graph (Mem0) |
| **Relational DB** | SQLite | Episode storage (episodic memory) |
| **Object Storage** | MinIO (S3-compatible) | Media asset storage |
| **Web Crawling** | Crawlee + Playwright | Browser automation & crawling |
| **Languages** | Python, Go, TypeScript | Multi-language implementation |

## Development & Deployment

| Tool | Usage |
|------|-------|
| Docker & Docker Compose | Containerization & orchestration |
| Poetry | Python dependency management |
| pnpm | Node.js monorepo management |
| pytest | Python testing framework |
| FastAPI Swagger | API documentation & testing |

---

# DEPLOYMENT & CONFIGURATION

## Environment Setup

### Required Services
```yaml
Services to run:
├── Ollama (LLM backend)
│   └── Port: 11434
│       Models: llama3.2, nomic-embed-text, llama3.2-vision
│
├── Kafka (message broker)
│   └── Topics auto-created by producers
│
├── Qdrant (vector database)
│   └── Port: 6333
│
├── MinIO (object storage, optional)
│   └── For Content Creator
│
├── Neo4j (graph database, optional)
│   └── For Mem0 knowledge graph
│
└── SQLite (embedded)
    └── For Episodic Memory
```

### Configuration Files
Each agent can be configured via:
- Environment variables
- Configuration files (.env)
- Docker Compose overrides
- Runtime parameters

### Common Environment Variables
```bash
# LLM Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
OPENAI_API_KEY=<optional>

# Message Queue
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Storage
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin

# Services
GENERAL_AGENT_PORT=8080
HACKER_AGENT_PORT=8000
VISUAL_ANALYSER_PORT=8081
QWEN_CODE_PORT=3000

# Memory
EPISODIC_DB_PATH=jarvis_episodes.db
MEM0_API_URL=http://localhost:5000

# Optional
OPENAI_API_KEY=<if using OpenAI>
BRAVE_SEARCH_API_KEY=<if using Brave Search>
```

---

# QUICK START GUIDE FOR DEVELOPERS

## Getting Started

### 1. **Start Core Services**
```bash
# From the project root
docker-compose up -d ollama kafka qdrant

# Wait for services to be healthy
sleep 10
```

### 2. **Deploy Desired Agents**
```bash
# Option A: General Agent (Research & Tasks)
cd general/
python -m pip install -r requirements.txt
python app/main.py

# Option B: Hacker Agent (Security Analysis)
cd hacker/
pip install -r requirements.txt
python api.py

# Option C: Content Creator (Media Generation)
cd content_creator/
pip install -r requirements.txt
python main.py --worker-type video  # or image-prompt, etc.
```

### 3. **Enable Memory System** (Optional)
```bash
cd memory/episodic/
pip install -r requirements.txt
python -m app.graphs.main_graph  # Starts main graph + workers
```

### 4. **Route Requests**
```bash
# Send requests to Router
curl -X POST http://localhost:8080/
  -H "Content-Type: application/json"
  -d '{"query": "Search for Python ML frameworks"}'
```

## API Usage Examples

### General Agent
```bash
curl -X POST http://localhost:8080/
  -H "Content-Type: application/json"
  -d '{"query": "What are the latest developments in LLMs?"}'
```

### Hacker Agent
```bash
curl -X POST http://localhost:8000/run
  -H "Content-Type: application/json"
  -d '{
    "command": "nmap -sV example.com",
    "mode": "sync"
  }'
```

### Content Creator
```bash
# Via Kafka
kafka-console-producer --topic media.render.requests
{
  "request_id": "123",
  "type": "image_generation",
  "prompt": "A futuristic city landscape"
}
```

### Visual Analyser
```bash
curl -X POST http://localhost:8081/analyze
  -H "Content-Type: application/json"
  -F "screenshot=@screenshot.png"
  -F "query=Find the login button"
```

---

# SYSTEM CAPABILITIES SUMMARY

## What Jarvis Can Do

### Information & Research
- ✓ Web search and research
- ✓ Web content extraction and crawling
- ✓ Information aggregation
- ✓ Data extraction from websites
- ✓ Context-aware knowledge retrieval

### Task Execution
- ✓ Shell command execution (with safety)
- ✓ Browser automation
- ✓ Scheduling and cron management
- ✓ Workflow orchestration
- ✓ Background job processing

### Security & Analysis
- ✓ Network reconnaissance
- ✓ Vulnerability scanning
- ✓ OSINT investigations
- ✓ Security assessment
- ✓ Penetration testing (authorized)

### Creative Content
- ✓ Video generation from prompts
- ✓ Image generation from text
- ✓ Image editing and manipulation
- ✓ Image generation with references
- ✓ Batch content processing

### UI & Interaction
- ✓ Screenshot analysis
- ✓ UI element detection
- ✓ Screen layout understanding
- ✓ Text extraction from images
- ✓ Interactive element mapping

### Code & Development
- ✓ Code generation
- ✓ Script generation
- ✓ Code execution
- ✓ Real-time development assistance
- ✓ Automated script deployment

### Intelligence & Learning
- ✓ Contextual memory (short-term)
- ✓ Persistent memory (long-term)
- ✓ Semantic knowledge retrieval
- ✓ Pattern learning
- ✓ User feedback integration
- ✓ Automatic knowledge elevation

### System Reliability
- ✓ Multi-phase validation
- ✓ Safety guards
- ✓ Error handling
- ✓ Audit logging
- ✓ Graceful degradation

---

# LIMITATIONS & CONSIDERATIONS

## Safety & Security
- All tool execution goes through validation
- Commands are sanitized before execution
- No raw arbitrary code execution (except Qwen Code)
- Memory system redacts sensitive data

## Performance
- Ollama model loading is non-blocking
- Kafka provides backpressure handling
- Memory retrieval limited to 5 episodes (configurable)
- Content crawling limited to 500 pages max

## Scalability
- Each agent is independently deployable
- Kafka enables horizontal scaling
- Stateless design allows multi-instance deployment
- Database choices optimized for their use case

## Current Limitations
- GUI agent (bytebot) is under development
- Internet Archive module not implemented
- Some integrations require API keys
- Vision model quality depends on Ollama installation

---

# CONCLUSION

Jarvis is a sophisticated, production-ready multi-agent system that combines:
- **Specialized expertise** through domain-specific agents
- **Intelligent coordination** via central routing
- **Learning capability** through dual-tier memory
- **Safe execution** through multi-phase validation
- **Scalable architecture** via message-driven design

The system is designed to be:
1. **Modular** - Each agent is independently deployable
2. **Extensible** - Easy to add new agents or tools
3. **Observable** - Comprehensive logging and state tracking
4. **Safe** - Multiple validation layers before execution
5. **Intelligent** - Learning from interactions over time

Developers using Jarvis can leverage this sophisticated orchestration layer to build complex, multi-agent AI applications without managing the underlying coordination complexity.

---

**Document Version:** 1.0
**Last Updated:** 2026-01-31
**Status:** Complete Architecture Documentation
