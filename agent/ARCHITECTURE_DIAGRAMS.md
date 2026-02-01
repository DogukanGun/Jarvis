# Jarvis Architecture - Visual Diagrams

## 1. System Overview Diagram

```
┌────────────────────────────────────────────────────────────────────────────┐
│                         JARVIS MULTI-AGENT SYSTEM                          │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │                    USER INTERFACE LAYER                            │  │
│  │  (CLI / API / Messaging / Browser / GUI)                          │  │
│  └────────────────┬───────────────────────────────────────────────────┘  │
│                   │                                                       │
│  ┌────────────────▼───────────────────────────────────────────────────┐  │
│  │                    ROUTER SERVICE                                  │  │
│  │              (Central Orchestration - Go)                         │  │
│  │  • LLM-based request routing                                      │  │
│  │  • Context-aware dispatch                                         │  │
│  │  • Agent capability matching                                      │  │
│  └────────────────┬───────────────────────────────────────────────────┘  │
│                   │                                                       │
│  ┌────────────────┼────────────────┬────────────┬──────────┬─────────┐   │
│  │                │                │            │          │         │   │
│  ▼                ▼                ▼            ▼          ▼         ▼   │
│ ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ ┌──────────┐   │
│ │ GENERAL  │  │ HACKER   │  │ CONTENT  │  │   WEB    │ │ VISUAL   │   │
│ │ AGENT    │  │ AGENT    │  │ CREATOR  │  │ FETCHER  │ │ANALYSER  │   │
│ │(8080)    │  │(8000)    │  │(Workers) │  │(Service) │ │(8081)    │   │
│ └──────────┘  └──────────┘  └──────────┘  └──────────┘ └──────────┘   │
│                                                                        │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │               COMMUNICATION INFRASTRUCTURE                       │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │                                                                  │ │
│ │  HTTP REST APIs    Kafka Message Bus        Direct Ollama      │ │
│ │  (Synchronous)     (Asynchronous)          (LLM Backend)       │ │
│ │  ├─ Port 8080      ├─ media.render.*      ├─ port 11434       │ │
│ │  ├─ Port 8000      ├─ memory.approval     ├─ llama3.2          │ │
│ │  ├─ Port 8081      ├─ memory.write        ├─ nomic-embed-text  │ │
│ │  └─ Port 3000      └─ (extensible)        └─ llama3.2-vision   │ │
│ │                                                                  │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │                  MEMORY & LEARNING SYSTEM                        │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │                                                                  │ │
│ │  ┌─────────────────────┐        ┌──────────────────────────┐   │ │
│ │  │ EPISODIC MEMORY     │        │ MEM0 LONG-TERM MEMORY   │   │ │
│ │  │ (Short-term)        │        │ (Persistent)            │   │ │
│ │  ├─────────────────────┤        ├──────────────────────────┤   │ │
│ │  │ • SQLite storage    │        │ • Qdrant (vectors)      │   │ │
│ │  │ • 9-node pipeline   │        │ • Neo4j (graph)         │   │ │
│ │  │ • Semantic search   │        │ • Semantic search       │   │ │
│ │  │ • Deduplication     │        │ • Graph relationships   │   │ │
│ │  │ • Fingerprinting    │        │ • Persistent state      │   │ │
│ │  │ • Auto-promotion    │        │ • User feedback         │   │ │
│ │  └──────────┬──────────┘        └──────────────────────────┘   │ │
│ │             │                            ▲                     │ │
│ │             │ (Automatic Promotion)      │                     │ │
│ │             └────────────────────────────┘                     │ │
│ │                                                                  │ │
│ │  Background Processes:                                         │ │
│ │  • Memory Write Graph (async writes)                           │ │
│ │  • Reflection Graph (pattern extraction every 6h)              │ │
│ │  • User Approval Graph (feedback processing)                   │ │
│ │                                                                  │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
│ ┌──────────────────────────────────────────────────────────────────┐ │
│ │                  EXTERNAL STORAGE & SERVICES                     │ │
│ ├──────────────────────────────────────────────────────────────────┤ │
│ │                                                                  │ │
│ │  ┌─────────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐      │ │
│ │  │   MINIO     │  │  QWEN    │  │  Qwen    │  │ Other  │      │ │
│ │  │   (S3)      │  │  Code    │  │ Internal │  │ Tools  │      │ │
│ │  │   Media     │  │  (3000)  │  │ Services │  │        │      │ │
│ │  │  Storage    │  │   Code   │  │          │  │        │      │ │
│ │  │             │  │   Gen    │  │          │  │        │      │ │
│ │  └─────────────┘  └──────────┘  └──────────┘  └────────┘      │ │
│ │                                                                  │ │
│ └──────────────────────────────────────────────────────────────────┘ │
│                                                                        │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Agent Capabilities Matrix

```
┌─────────────────┬──────┬──────┬────────┬────┬───────┬──────┐
│ CAPABILITY      │ Gen. │Hack. │Content │Web │Visual │Qwen  │
├─────────────────┼──────┼──────┼────────┼────┼───────┼──────┤
│ Web Search      │  ✓   │      │        │    │       │      │
│ Web Fetch       │  ✓   │      │        │ ✓  │       │      │
│ Shell Execute   │  ✓   │  ✓   │        │    │       │      │
│ Browser Auto    │  ✓   │      │        │    │       │      │
│ Cron Scheduling │  ✓   │      │        │    │       │      │
│ Security Scan   │      │  ✓   │        │    │       │      │
│ OSINT           │      │  ✓   │        │    │       │      │
│ SQL Injection   │      │  ✓   │        │    │       │      │
│ Video Gen       │      │      │  ✓     │    │       │      │
│ Image Gen       │      │      │  ✓     │    │       │      │
│ Image Edit      │      │      │  ✓     │    │       │      │
│ Site Crawling   │      │      │        │ ✓  │       │      │
│ Screenshot Anal │      │      │        │    │  ✓    │      │
│ UI Detection    │      │      │        │    │  ✓    │      │
│ Code Generation │      │      │        │    │       │  ✓   │
│ Code Execution  │      │      │        │    │       │  ✓   │
│ Memory Mgmt     │      │      │        │    │       │      │
│ Context Aware   │  ~   │  ~   │   ~    │ ~  │   ~   │  ~   │
└─────────────────┴──────┴──────┴────────┴────┴───────┴──────┘

Legend: ✓ = Direct capability, ~ = Via memory system, (blank) = Not applicable
```

---

## 3. Hacker Agent - Execution Pipeline

```
                           USER REQUEST
                                │
                                ▼
                    ┌─────────────────────┐
                    │  INIT STATE NODE    │
                    │ Initialize context  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────────────┐
                    │   PLANNER NODE              │
                    │ (Context-aware decision)    │
                    │                             │
                    │ LLM analyzes:               │
                    │ • User request              │
                    │ • Available tools           │
                    │ • Context & history         │
                    │                             │
                    │ Output:                     │
                    │ • Decision (what to do)     │
                    │ • Action type               │
                    │ • Reasoning                 │
                    └──────────┬──────────────────┘
                               │
                ┌──────────────┼──────────────┐
                │              │              │
           (run_cli)      (direct_tool)   (finish)
                │              │              │
                ▼              ▼              │
        ┌──────────────┐  ┌──────────┐      │
        │  COMPILER    │  │ RESPONSE │      │
        │  NODE        │  │ SENT     │      │
        │              │  └──────────┘      │
        │ Translates   │                    │
        │ decision to  │                    │
        │ tool calls   │                    │
        └──────┬───────┘                    │
               │                            │
               ▼                            │
        ┌──────────────┐                   │
        │  VALIDATOR   │                   │
        │  NODE        │                   │
        │              │                   │
        │ Safety       │                   │
        │ checks:      │                   │
        │ ✓ Valid cmd  │                   │
        │ ✓ No inject  │                   │
        │ ✓ No access  │                   │
        └──────┬───────┘                   │
               │                           │
         (Valid?)                          │
        ┌──────┴──────┐                    │
        │             │                    │
       (Yes)        (No)                   │
        │             │                    │
        ▼             └────────────────────┼─→ (Error reported)
    ┌──────────────┐                      │
    │  EXECUTOR    │                      │
    │  NODE        │                      │
    │              │                      │
    │ Runs tools:  │                      │
    │ • nmap       │                      │
    │ • whois      │                      │
    │ • sqlmap     │                      │
    │ • etc.       │                      │
    └──────┬───────┘                      │
           │                              │
           ▼                              │
    ┌──────────────┐                     │
    │  GUARDS      │                     │
    │  NODE        │                     │
    │              │                     │
    │ Post-exec    │                     │
    │ checks:      │                     │
    │ ✓ Results OK │                     │
    │ ✓ No creds   │                     │
    │ ✓ No PII     │                     │
    └──────┬───────┘                     │
           │                             │
           └─────────────┬───────────────┘
                         │
                         ▼
                   ┌──────────────┐
                   │  RESPONSE TO │
                   │  USER        │
                   └──────────────┘
```

---

## 4. Memory System - Episode Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                    EPISODE LIFECYCLE                            │
└─────────────────────────────────────────────────────────────────┘

USER REQUEST
      │
      ▼
┌──────────────────────────────┐
│ 1. PREPROCESS INPUT          │
│    • Normalize text          │
│    • Extract entities        │
│    • Detect task type        │
└──────────────┬───────────────┘
               │
               ▼
        ┌─────────────┐
        │ Mem0 Needed?│──(No)──┐
        └──────┬──────┘        │
            (Yes)              │
               │               │
               ▼               │
┌──────────────────────────────┐
│ 2. LOAD MEM0                 │
│    (Long-term memory)        │
│    • Query Qdrant            │
│    • Get related memories    │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ 3. RETRIEVE EPISODES         │
│    (Short-term memory)       │
│    • Semantic similarity     │
│    • Top 5 similar episodes  │
│    • Min importance: 0.3     │
└──────────────┬───────────────┘
               │
               ▼
┌──────────────────────────────┐
│ 4. COMPOSE CONTEXT           │◄──┐
│    • User input              │   │
│    • Retrieved episodes      │   │
│    • Mem0 items             │   │
│    → Complete context        │   │
└──────────────┬───────────────┘   │
               │                   │
               ▼                   │
┌──────────────────────────────┐   │
│ 5. LLM STEP                  │   │
│    • Call LLM with context   │   │
│    • Extract memory intents  │   │
│    • Generate response       │   │
└──────────────┬───────────────┘   │
               │                   │
               ▼                   │
┌──────────────────────────────┐   │
│ 6. RETURN OUTPUT             │   │
│    → Response to user        │   │
└──────────────┬───────────────┘   │
               │                   │
               ▼                   │
        ┌─────────────────────────────────────┐
        │ 7. ENQUEUE MEMORY WRITE             │
        │    (Background job)                 │
        │    Kafka: memory.write event        │
        └──────────┬──────────────────────────┘
                   │ (Async)
                   ▼
        ┌─────────────────────────────────────┐
        │ MEMORY WRITE GRAPH (Worker)         │
        │ • Extract memory intents           │
        │ • Create episode candidate         │
        │ • Fingerprint check (dedup)        │
        │ • Generate embedding (nomic)       │
        │ • Store in SQLite                  │
        └──────────┬──────────────────────────┘
                   │
                   ▼
        ┌─────────────────────────────────────┐
        │ EPISODIC MEMORY (Stored)            │
        │ • ID, embedding, importance        │
        │ • Type, content, timestamp         │
        │ • Reinforcement count              │
        │ • Available for future retrieval   │
        └──────────┬──────────────────────────┘
                   │
         ┌─────────┴─────────┐
         │ (Runs periodically)
         ▼
   ┌─────────────────────────────┐
   │ REFLECTION GRAPH (Every 6h) │
   │ • Analyze recent episodes  │
   │ • Extract patterns         │
   │ • Create proposals         │
   │ • Kafka: approval.request  │
   └──────────┬─────────────────┘
              │
              ▼
   ┌─────────────────────────────┐
   │ USER APPROVAL SYSTEM        │
   │ User reviews & votes on:    │
   │ "Promote this pattern?"     │
   │ Kafka: approval.response    │
   └──────────┬─────────────────┘
              │
         (Approved?)
         ├─(Yes)──┐
         │        │
    (No) │        ▼
         │    ┌──────────────┐
         │    │ MEM0 WRITE   │
         │    │ • Store in   │
         │    │   Qdrant     │
         │    │ • Update Neo4j
         │    │ • Available  │
         │    │   for all    │
         │    │   future ops │
         │    └──────────────┘
         │
         └─────────┬────────────┘
                   │
                   ▼
         ┌──────────────────┐
         │ Episode lifecycle│
         │ continues...     │
         └──────────────────┘

STATES ACROSS LIFECYCLE:

┌─────────────────────────────────────────────┐
│ Episodic → Reinforced → Promotion Proposed │
│  (current) → (repeated) → (approved user)   │
│                                             │
│ → Mem0 (persistent long-term memory)       │
│   (available for all future queries)        │
│   (enables pattern matching)                │
│   (drives intelligent behavior)             │
└─────────────────────────────────────────────┘
```

---

## 5. Content Creator - Media Generation Pipeline

```
                        KAFKA TOPIC
                  media.render.requests
                            │
                            ▼
                  ┌──────────────────────┐
                  │  ROUTER WORKER       │
                  │  (Request Validator) │
                  │                      │
                  │  • Validate request  │
                  │  • Route based on    │
                  │    media type        │
                  └─────────┬────────────┘
                            │
            ┌───────────────┼───────────────┬──────────────┐
            │               │               │              │
      (video)          (image_prompt)  (image_ref)   (image_edit)
            │               │               │              │
            ▼               ▼               ▼              ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────┐  ┌──────────┐
    │ VIDEO WORKER │ │ IMAGE PROMPT │ │ IMAGE    │  │ IMAGE    │
    │              │ │ WORKER       │ │ REFERENCE│  │ EDIT     │
    │              │ │              │ │ WORKER   │  │ WORKER   │
    └──────┬───────┘ └──────┬───────┘ └────┬─────┘  └────┬─────┘
           │                │              │             │
           └────────────────┼──────────────┼─────────────┘
                            │
        ┌───────────────────┴───────────────────┐
        │ (Each worker runs same pipeline)       │
        └───────────────────┬───────────────────┘
                            │
                            ▼
                  ┌──────────────────────┐
                  │  1. LOAD MODEL       │
                  │  • LTX-2 (video)     │
                  │  • Stable Diffusion  │
                  │    (images)          │
                  │  • Cache in memory   │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  2. GENERATE         │
                  │  • LLM-based params  │
                  │  • Model inference   │
                  │  • Output format     │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  3. UPLOAD RESULT    │
                  │  • Push to MinIO     │
                  │  • Get S3 URL        │
                  │  • Store reference   │
                  └──────────┬───────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │  4. PUBLISH RESULT   │
                  │  • Kafka topic:      │
                  │    media.render.     │
                  │    results           │
                  │  • Result metadata   │
                  │  • Asset URL         │
                  └──────────┬───────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ RESULT AVAILABLE │
                    │ (External access)│
                    └──────────────────┘


WORKER CONFIGURATION:

┌────────────────────────────────────────┐
│ WORKER INSTANCES (Configurable)        │
├────────────────────────────────────────┤
│ Video Workers:        N instances      │
│ Image Prompt:         N instances      │
│ Image Reference:      N instances      │
│ Image Edit:           N instances      │
│                                        │
│ Scaled based on:                       │
│ • Message queue depth                  │
│ • Available GPU/CPU                    │
│ • Model memory requirements            │
└────────────────────────────────────────┘
```

---

## 6. Communication Patterns

```
┌────────────────────────────────────────────────────────────────┐
│              INTER-AGENT COMMUNICATION PATTERNS               │
└────────────────────────────────────────────────────────────────┘

1. SYNCHRONOUS (HTTP REST)
   ─────────────────────────

   Client
    │
    ├─ Request (HTTP POST)
    │          ↓
    ├─ Agent processes synchronously
    │          ↓
    ├─ Response (JSON)
    │
    └─ Immediate result

   Typical use: Real-time queries, analysis


2. ASYNCHRONOUS (Kafka)
   ──────────────────────

   Producer
    │
    ├─ Publish message to topic
    │          ↓
    ├─ Message queued in Kafka
    │          ↓
    ├─ Consumer subscribes (may be offline)
    │          ↓
    ├─ Consumer processes
    │          ↓
    ├─ Result published to result topic
    │
    └─ No immediate response guarantee

   Typical use: Media generation, background jobs


3. HYBRID (Request + Callback)
   ────────────────────────────

   Client
    │
    ├─ POST request with callback URL
    │          ↓
    ├─ Agent (HTTP) returns task_id immediately
    │          ↓
    ├─ Agent processes in background
    │          ↓
    ├─ On completion, POST to callback URL
    │
    └─ Later: Client can poll status

   Typical use: Long-running tasks


AGENT COMMUNICATION MATRIX:

┌──────────────┬────────┬────────┬────────┬────────┬────────┐
│ From \ To    │General │Hacker  │Content │Visual  │Memory  │
├──────────────┼────────┼────────┼────────┼────────┼────────┤
│General       │  —     │  REST  │ Kafka  │  REST  │ Event  │
│Hacker       │  REST  │  —     │ Kafka  │  REST  │ Event  │
│Content      │ Kafka  │ Kafka  │  —     │ Kafka  │ Kafka  │
│Visual       │  REST  │  REST  │ Kafka  │  —     │ Event  │
│Memory       │ Event  │ Event  │ Kafka  │ Event  │  —     │
└──────────────┴────────┴────────┴────────┴────────┴────────┘

REST  = HTTP REST API (synchronous)
Kafka = Message topic (asynchronous)
Event = Kafka event (notification-driven)
```

---

## 7. Technology Stack Layers

```
┌─────────────────────────────────────────────────────────────┐
│ APPLICATION LAYER                                           │
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐│
│ │  Agents      │ │  Tools       │ │  Services           ││
│ │  - General   │ │  - Web fetch │ │  - Memory system    ││
│ │  - Hacker    │ │  - Browser   │ │  - Reflection       ││
│ │  - Creator   │ │  - Cron      │ │  - Approval         ││
│ │  - Web       │ │  - Exec      │ │                     ││
│ │  - Visual    │ │  - Security  │ │                     ││
│ │  - Qwen      │ │              │ │                     ││
│ └──────────────┘ └──────────────┘ └──────────────────────┘│
│                                                             │
│ ORCHESTRATION LAYER                                        │
│ ┌──────────────────────────────────────────────────────────┤
│ │  LangGraph (workflow engine)                            │
│ │  - State-driven execution                              │
│ │  - Deterministic flows                                 │
│ │  - Conditional routing                                 │
│ │  - Type-safe state schemas                             │
│ └──────────────────────────────────────────────────────────┤
│                                                             │
│ FRAMEWORK LAYER                                            │
│ ┌──────────────────────────────────────────────────────────┤
│ │  LangChain (Python)  │  LangChain Go  │  FastAPI       │
│ │  - Agent framework   │  - Go agent    │  - REST server │
│ │  - Tool integration  │  - Integration │  - Routing     │
│ │  - LLM abstraction   │  - Utilities   │  - Async       │
│ └──────────────────────────────────────────────────────────┤
│                                                             │
│ COMMUNICATION LAYER                                        │
│ ┌─────────────────────┬────────────────┬──────────────────┤
│ │  Kafka              │  HTTP/REST     │  WebSockets      │
│ │  - Async messaging  │  - Sync API    │  - Real-time     │
│ │  - Event streaming  │  - JSON-RPC    │  - Event stream  │
│ │  - Topic-based      │  - Resource    │  - Bidirectional │
│ └─────────────────────┴────────────────┴──────────────────┤
│                                                             │
│ DATA & STORAGE LAYER                                       │
│ ┌──────────────┬──────────────┬──────────┬────────────────┤
│ │  Embeddings  │  Knowledge   │ Episodic │ Media Storage  │
│ │  - Qdrant    │  - Neo4j     │ - SQLite │ - MinIO (S3)   │
│ │  - Semantic  │  - Graph     │ - Vector │ - Object store │
│ │  - Vector    │  - Relations │ - Events │ - Versioning   │
│ └──────────────┴──────────────┴──────────┴────────────────┤
│                                                             │
│ AI/ML LAYER                                                │
│ ┌──────────────────────────────────────────────────────────┤
│ │  Ollama (Primary LLM Backend)    │  OpenAI (Fallback)   │
│ │  - Multiple model support        │  - gpt-4o-mini       │
│ │  - Local inference               │  - Cloud-based       │
│ │  - Models:                       │  - API-based         │
│ │    • llama3.2 (chat)            │                      │
│ │    • nomic-embed-text (embed)   │                      │
│ │    • llama3.2-vision (vision)   │                      │
│ └──────────────────────────────────────────────────────────┤
│                                                             │
│ INFRASTRUCTURE LAYER                                       │
│ ├──────────────────────────────────────────────────────────┤
│ │  Docker    │  Docker Compose  │  (Optional: Kubernetes) │
│ │  - Images  │  - Orchestration │  - Container mgmt      │
│ │  - Volumes │  - Networking    │  - Auto-scaling        │
│ │  - Networks│  - Service mesh  │  - Load balancing      │
│ └──────────────────────────────────────────────────────────┤
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 8. Request Routing Flow

```
                    USER REQUEST
                         │
                         ▼
                 ┌──────────────────┐
                 │ ROUTER SERVICE   │
                 │ (Central Hub)    │
                 └────────┬─────────┘
                          │
         ┌────────────────┴────────────────┐
         │ LLM Analysis:                   │
         │ • Parse request                 │
         │ • Extract intent                │
         │ • Identify required tools       │
         │ • Match agent capability        │
         └────────────────┬────────────────┘
                          │
            ┌─────────────┼─────────────┐
            │             │             │
         (Type: A)   (Type: B)     (Type: C)
            │             │             │
            ▼             ▼             ▼
    ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
    │ Route to     │ │ Route to     │ │ Route to     │
    │ General Agent│ │ Hacker Agent │ │ Content Creat│
    │              │ │              │ │              │
    │ (Research)   │ │ (Security)   │ │ (Media Gen)  │
    └────────┬─────┘ └────────┬─────┘ └────────┬─────┘
             │                │                │
             ▼                ▼                ▼
    ┌──────────────────────────────────────────────┐
    │ AGENT PROCESSES REQUEST                      │
    │ • Execute tools/workflow                    │
    │ • Interact with dependencies                │
    │ • Generate response                         │
    └────────┬─────────────────────────────────────┘
             │
             ▼
    ┌──────────────────────────────────────────────┐
    │ TRIGGER MEMORY SYSTEM                        │
    │ (Async background job)                      │
    │ • Episodic write                            │
    │ • Semantic embedding                        │
    │ • Pattern detection                         │
    │ • Promotion proposals                       │
    └────────┬─────────────────────────────────────┘
             │
             ▼
    ┌──────────────────────────────────────────────┐
    │ RESPONSE RETURNED TO USER                    │
    │ + Learning in background                    │
    └──────────────────────────────────────────────┘
```

---

## 9. Data Flow - Complete Request-to-Memory Journey

```
┌──────────────────────────────────────────────────────────────────┐
│ COMPLETE REQUEST LIFECYCLE                                       │
└──────────────────────────────────────────────────────────────────┘

TIME → (Synchronous)         (Asynchronous Background)      (Periodic)
        ├─────────────────┬───────────────────────────────┬──────────────

    USER REQUEST
        │
        ├─→ Router
        │    ├─→ Select Agent
        │    └─→ Compose Prompt
        │
        ├─→ [AGENT PROCESSING]
        │    ├─ Check episodic memory (retrieve similar)
        │    ├─ Check long-term memory (if needed)
        │    ├─ Compose context
        │    ├─ Call LLM
        │    ├─ Extract memory intents
        │    └─ Generate response
        │
        ├─→ Return to User
        │
        └─→ [Time ≈ 100ms-5s]

                          │
                          ├─→ Kafka Event: memory.write
                          │    └─ Contains: episode data, intents
                          │
                          ├─→ Memory Write Graph
                          │    ├─ Parse intents
                          │    ├─ Create episode
                          │    ├─ Fingerprint check
                          │    ├─ Embed (nomic-embed-text)
                          │    └─ Store in SQLite
                          │
                          ├─→ Episode Stored + Indexed
                          │    └─ Available for future retrieval
                          │
                          └─→ [Time ≈ 500ms-2s]

                                              │
                                              ├─→ [Every 6 hours]
                                              │
                                              ├─→ Reflection Graph
                                              │    ├─ Analyze recent episodes
                                              │    ├─ Identify patterns
                                              │    ├─ Create proposals
                                              │    └─ Publish promotion candidates
                                              │
                                              ├─→ User Approval System
                                              │    ├─ Present patterns
                                              │    ├─ User votes
                                              │    └─ Collect feedback
                                              │
                                              ├─→ Approved Items
                                              │    ├─ Write to Mem0
                                              │    ├─ Store in Qdrant
                                              │    ├─ Add Neo4j relations
                                              │    └─ Available for all users
                                              │
                                              └─→ [Time ≈ Minutes]

MEMORY VISIBILITY:
  During request:
  └─ Episodic (previous 5 similar → context)

  After 6 hours (if reinforced):
  └─ Mem0 (all users can benefit)

REINFORCEMENT:
  Repeated similar queries → Higher confidence → Faster promotion
```

---

## 10. Deployment Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ JARVIS DEPLOYMENT ARCHITECTURE                                  │
└─────────────────────────────────────────────────────────────────┘

DEVELOPMENT MODE:
┌──────────────────────────────────────────────────────────────┐
│ docker-compose (single machine)                              │
├──────────────────────────────────────────────────────────────┤
│ Services:                                                    │
│ ├─ Ollama (localhost:11434)                                │
│ ├─ Kafka (localhost:9092)                                  │
│ ├─ Qdrant (localhost:6333)                                 │
│ ├─ MinIO (localhost:9000)                                  │
│ └─ (optional: Neo4j)                                       │
│                                                              │
│ Agents (localhost):                                          │
│ ├─ General Agent (8080)                                    │
│ ├─ Hacker Agent (8000)                                     │
│ ├─ Visual Analyser (8081)                                  │
│ └─ Qwen Code (3000)                                        │
└──────────────────────────────────────────────────────────────┘

PRODUCTION MODE:
┌──────────────────────────────────────────────────────────────┐
│ Kubernetes Cluster                                           │
├──────────────────────────────────────────────────────────────┤
│ Core Services (StatefulSets):                               │
│ ├─ Kafka Cluster (3+ brokers)                              │
│ ├─ Ollama Server Cluster (load-balanced)                   │
│ ├─ Qdrant Cluster (high-availability)                      │
│ └─ MinIO Cluster (distributed storage)                     │
│                                                              │
│ Agents (Deployments):                                       │
│ ├─ General Agent (2+ replicas)                            │
│ ├─ Hacker Agent (2+ replicas)                             │
│ ├─ Content Creator Workers (10+ replicas)                 │
│ ├─ Visual Analyser (2+ replicas)                          │
│ ├─ Qwen Code (2+ replicas)                                │
│ ├─ Router Service (3+ replicas)                           │
│ └─ Memory System (2+ replicas)                            │
│                                                              │
│ Infrastructure:                                             │
│ ├─ Ingress controller (routing)                           │
│ ├─ Service mesh (optional, e.g., Istio)                   │
│ ├─ PVC (persistent storage)                               │
│ ├─ ConfigMaps (configuration)                             │
│ └─ Secrets (credentials)                                  │
│                                                              │
│ Monitoring:                                                 │
│ ├─ Prometheus (metrics)                                   │
│ ├─ Grafana (dashboards)                                   │
│ ├─ ELK Stack (logging)                                    │
│ └─ Jaeger (distributed tracing)                           │
└──────────────────────────────────────────────────────────────┘

SCALING CONSIDERATIONS:
┌──────────────────────────────────────────────────────────────┐
│ Horizontal Scaling Points:                                   │
│                                                              │
│ Content Creator Workers                                     │
│ └─ Scale based on Kafka queue depth                        │
│                                                              │
│ General Agent Instances                                     │
│ └─ Scale based on REST request rate                        │
│                                                              │
│ Ollama Replicas                                            │
│ └─ Load-balanced LLM inference                             │
│                                                              │
│ Memory Write Graph Workers                                 │
│ └─ Scale based on memory.write topic depth               │
│                                                              │
│ Resource Constraints:                                       │
│ └─ GPU memory (Ollama, video generation)                  │
│ └─ Disk I/O (Kafka, SQLite)                               │
│ └─ Network bandwidth (Kafka producers)                    │
└──────────────────────────────────────────────────────────────┘
```

---

This comprehensive visual guide covers:
1. ✓ System overview diagram
2. ✓ Agent capabilities matrix
3. ✓ Hacker agent execution pipeline
4. ✓ Memory system episode lifecycle
5. ✓ Content creator media pipeline
6. ✓ Communication patterns
7. ✓ Technology stack layers
8. ✓ Request routing flow
9. ✓ Complete data flow journey
10. ✓ Deployment architecture

All diagrams use ASCII art for universal compatibility and can be rendered in any text editor or markdown viewer.
