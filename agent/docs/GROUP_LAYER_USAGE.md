# Jarvis Group Communication Layer - Usage Guide

## Overview

The Jarvis Group Communication Layer provides a WhatsApp-style group communication system for coordinating multi-agent orchestration workflows. It implements:

- **Hierarchical Roles**: OWNER (user) → ADMIN (orchestrator) → MEMBER (agents)
- **Rich Event Stream**: Thread-aware timeline with audit trail
- **Approval Workflows**: Plan → approve → implement gates
- **Attachment System**: MinIO-backed object references
- **Permission Enforcement**: Role-based access control

## Quick Start

### 1. Enable the Group Layer

Set the environment variable to enable the group layer:

```bash
export ENABLE_GROUP_LAYER=true
export GROUP_ID=jarvis-main
export KAFKA_BROKERS=localhost:9092
export MINIO_ENDPOINT=localhost:9000
export MINIO_ACCESS_KEY=minioadmin
export MINIO_SECRET_KEY=minioadmin
export MINIO_BUCKET=jarvis
```

### 2. Start Infrastructure

Ensure Kafka and MinIO are running:

```bash
# Docker Compose (if using docker-compose.yml)
docker-compose up -d kafka minio

# Or use the provided setup script
./scripts/setup_group_topics.sh
```

### 3. Start Services

```bash
# Router with orchestrator
./router/router_test

# General agent
python general/run_kafka_consumer.py

# Visual analyser
./visual_analyser

# Web fetcher
python web_fetcher/run_kafka_consumer.py
```

## Architecture

### Components

#### 1. **Router + Orchestrator**
- HTTP server on port 8080
- Consumes group events and commands
- Manages state (threads, approvals, tasks)
- Publishes orchestration events

#### 2. **Agents**
- **General Agent** (Python): Processing logic with LangChain
- **Visual Analyser** (Go): Image analysis with Ollama
- **Web Fetcher** (Python): Web content extraction
- All participate in group communication

#### 3. **Kafka Topics** (per group)
- `group.{id}.events`: Main event stream
- `group.{id}.commands`: Admin commands
- `group.{id}.approvals`: Approval tracking
- `group.{id}.results`: Result collection
- `group.{id}.audit`: Audit log

#### 4. **MinIO**
- Storage for attachments (images, code, etc.)
- Presigned URLs for downloads
- Bucket: `jarvis`

### Message Flow

```
Owner Chat Message
    ↓
[Router -> Orchestrator]
    ↓
Agent processes (proposal)
    ↓
Orchestrator publishes proposal
    ↓
[If requires_approval = true]
    → Owner approval requested
    → Owner grants/denies
    ↓
[If approved]
    → Create task
    → Dispatch to target agent
    → Agent executes
    ↓
Result published
    ↓
Summary generated
```

## Event Types

### Chat Events
- `chat.message` - Owner sends a message

### Proposal Events
- `proposal.created` - Agent proposes an action
- `proposal.updated` - Proposal is updated
- `proposal.rejected` - Proposal is rejected

### Approval Events
- `approval.requested` - Approval requested from owner
- `approval.granted` - Owner grants approval
- `approval.denied` - Owner denies approval
- `approval.timeout` - Approval expires

### Task Events
- `task.created` - New task created
- `task.started` - Task execution started
- `task.progress` - Progress update (0-100%)
- `task.completed` - Task completed successfully
- `task.failed` - Task execution failed
- `task.cancelled` - Task cancelled

### Result Events
- `result.generated` - Generic result
- `result.image_analysis` - Image analysis result
- `result.code_diff` - Code changes
- `result.plan` - Planning result
- `result.web_extraction` - Web content extraction
- `result.summary` - Thread summary

## Role-Based Permissions

### OWNER (User)
- Send chat messages
- View proposals
- Grant/deny approvals
- Promote memories
- Full admin access

### ADMIN (Orchestrator)
- Create proposals
- Request approvals
- Create and manage tasks
- Run commands
- Create threads

### MEMBER (Agents)
- Send chat messages
- View tasks/proposals
- Send results
- View attachments

## Usage Patterns

### Pattern 1: Chat → Proposal → Approval → Execute

```python
# Owner sends message
POST /message
{
  "message": "Can you write Python code to sort an array?",
  "group_id": "jarvis-main"
}

# System generates:
# 1. chat.message event
# 2. Agent processes and creates proposal.created event
# 3. Orchestrator publishes approval.requested event
# 4. Owner responds with approval.granted event
# 5. Orchestrator creates task
# 6. Agent executes and publishes result events
# 7. Orchestrator publishes result.summary event
```

### Pattern 2: Image Analysis

```
Owner uploads image →
Orchestrator creates task →
Visual agent analyzes →
Publishes result.image_analysis →
Summary generated
```

### Pattern 3: Plan → Approve → Implement

```
Owner: "Create a REST API"
  ↓
Qwen generates plan
  ↓
Orchestrator: approval.requested (plan)
  ↓
Owner: approval.granted
  ↓
Qwen implements
  ↓
Publishes result.code_diff
  ↓
Summary generated
```

## API Endpoints

### Router

**Health Check**
```bash
GET /health
```

**Orchestrator Status**
```bash
GET /orchestrator/status

Response:
{
  "enabled": true,
  "running": true,
  "messages": 123,
  "bytes": 456789,
  "lag": 0,
  "group_id": "jarvis-main",
  "topics": ["group.jarvis-main.events", "group.jarvis-main.commands"]
}
```

### Kafka Topics

Publish events by writing to Kafka topics:

```python
from kafka import KafkaProducer
import json

producer = KafkaProducer(
    bootstrap_servers=['localhost:9092'],
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

envelope = {
    "group_id": "jarvis-main",
    "message_id": "uuid",
    "timestamp": "2026-01-31T12:00:00Z",
    "thread_id": "thread-uuid",
    "sender": {
        "id": "user-id",
        "role": "OWNER",
        "agent": None
    },
    "type": "chat.message",
    "payload": {
        "text": "Your message here"
    },
    "version": "1.0"
}

producer.send(
    'group.jarvis-main.events',
    value=envelope,
    key=envelope['thread_id'].encode()
)
```

## Configuration

### Environment Variables

**Group Layer**
- `ENABLE_GROUP_LAYER`: "true" to enable (default: false)
- `GROUP_ID`: Group ID (default: "jarvis-main")

**Kafka**
- `KAFKA_BROKERS`: Comma-separated brokers (default: "localhost:9092")

**MinIO**
- `MINIO_ENDPOINT`: MinIO endpoint (default: "localhost:9000")
- `MINIO_ACCESS_KEY`: Access key (default: "minioadmin")
- `MINIO_SECRET_KEY`: Secret key (default: "minioadmin")
- `MINIO_BUCKET`: Bucket name (default: "jarvis")
- `MINIO_USE_SSL`: Use SSL (default: "false")

**Services**
- `QWEN_CODE_URL`: Qwen code service URL (default: "http://localhost:3000")
- `VISUAL_ANALYSER_URL`: Visual analyser URL (default: "http://localhost:8081")
- `WEB_FETCHER_URL`: Web fetcher URL (default: "http://localhost:8082")
- `OLLAMA_HOST`: Ollama host (default: "http://localhost:11434")

## Monitoring

### Check Consumer Lag

```bash
GET /orchestrator/status

# Monitor "lag" field - should be 0 or low
```

### View Kafka Topics

```bash
kafka-topics.sh --list --bootstrap-server localhost:9092 | grep "group.jarvis"
```

### Monitor Events

```bash
# Tail events topic
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic group.jarvis-main.events \
  --from-beginning
```

## Troubleshooting

### Consumer Lag High

**Symptoms**: `lag` > 1000 in `/orchestrator/status`

**Solutions**:
1. Check if Kafka is running: `kafka-broker-api-versions.sh --bootstrap-server localhost:9092`
2. Check if orchestrator is consuming: Check logs for "Processing event"
3. Increase consumer threads in `consumer.go`

### No Events Published

**Symptoms**: Events not appearing in topics

**Solutions**:
1. Check if Kafka is running
2. Check if topics exist: `kafka-topics.sh --list --bootstrap-server localhost:9092`
3. Run: `./scripts/setup_group_topics.sh` to create topics
4. Check logs for permission errors

### Approval Timeout

**Symptoms**: Approvals expire before owner response

**Solutions**:
1. Increase TTL: `NewStateManager(1440)` for 24 hours
2. Check if approval events are being published
3. Verify owner is online

### MinIO Errors

**Symptoms**: "failed to upload file"

**Solutions**:
1. Check if MinIO is running: `curl http://localhost:9000/minio/health/live`
2. Verify credentials in environment
3. Check bucket exists: `mc ls minio/jarvis`

## Testing

### Run Unit Tests

```bash
# Schema tests
go test ./schemas/group -v

# Orchestrator tests
go test ./router/orchestrator -v

# All tests
go test ./... -v
```

### Manual Integration Test

```bash
# 1. Start services
ENABLE_GROUP_LAYER=true docker-compose up -d

# 2. Send a message
curl -X POST http://localhost:8080/message \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello world"}'

# 3. Check orchestrator status
curl http://localhost:8080/orchestrator/status

# 4. Monitor events
kafka-console-consumer.sh \
  --bootstrap-server localhost:9092 \
  --topic group.jarvis-main.events \
  --from-beginning
```

## Performance Tuning

### Kafka Partitions
- `group.{id}.events`: 3 partitions for parallelism
- Increase if throughput > 1000 events/sec

### Consumer
- `MaxBytes`: 1MB per fetch
- `QueueCapacity`: 100 messages
- Adjust if lag increases

### Approvals
- TTL: 1440 minutes (24 hours)
- Timeout check: Every 30 seconds
- Adjust based on user response time

## Future Enhancements

- [ ] Persistent state (Redis/PostgreSQL)
- [ ] Web UI for timeline viewing
- [ ] Notification system for approvals
- [ ] ML-based auto-approval suggestions
- [ ] Multi-group support
- [ ] Agent collaboration workflows

## Support

For issues or questions:
1. Check logs: `docker logs router orchestrator-consumer`
2. Verify environment: Check environment variables
3. Check Kafka: `kafka-console-consumer.sh`
4. Check MinIO: `mc ls minio`

---

**Last Updated**: 2026-01-31
**Version**: 1.0.0
