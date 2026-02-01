# Event Type Reference

## Overview

This document describes all event types in the Jarvis Group Communication Layer.

## Message Envelope Structure

All events are wrapped in an envelope:

```json
{
  "group_id": "jarvis-main",
  "message_id": "uuid",
  "timestamp": "2026-01-31T12:00:00Z",
  "thread_id": "thread-uuid",
  "sender": {
    "id": "user-id",
    "role": "OWNER|ADMIN|MEMBER",
    "agent": "agent-name"
  },
  "type": "event.type",
  "payload": { /* event-specific payload */ },
  "version": "1.0"
}
```

## Chat Events

### chat.message
Owner sends a message to the group.

**Allowed Senders**: OWNER

**Payload**:
```json
{
  "text": "Message content",
  "image_url": "https://example.com/image.png",  // optional
  "image_data": "base64-encoded-image",          // optional
  "attachments": [                               // optional
    {
      "kind": "minio",
      "bucket": "jarvis",
      "key": "2026-01-31/uuid/file.txt",
      "size": 1024,
      "etag": "abc123"
    }
  ]
}
```

**Example Use Case**:
```
Owner: "Can you analyze this screenshot and write Python code?"
↓
Agent processes the message
↓
Generates proposal.created event
```

## Proposal Events

### proposal.created
Agent proposes an action based on a message.

**Allowed Senders**: ADMIN, orchestrator

**Payload**:
```json
{
  "proposal_id": "uuid",
  "title": "Code Generation",
  "description": "Generate Python sorting function",
  "action": "execute_proposal",
  "context": "Original message that triggered proposal",
  "confidence": 0.85,
  "requires_approval": true,
  "attachments": [],
  "metadata": {
    "source_agent": "general-agent",
    "processing_time_ms": 250
  }
}
```

**Note**: If `requires_approval` is true, orchestrator will publish `approval.requested`.

### proposal.updated
Update an existing proposal.

**Allowed Senders**: ADMIN

**Payload**:
```json
{
  "proposal_id": "uuid",
  "title": "Updated Title",
  "description": "Updated description",
  "confidence": 0.9
}
```

### proposal.rejected
Explicitly reject a proposal.

**Allowed Senders**: OWNER

**Payload**:
```json
{
  "proposal_id": "uuid",
  "reason": "Doesn't meet requirements"
}
```

## Approval Events

### approval.requested
Request approval from owner for a proposal.

**Allowed Senders**: ADMIN, orchestrator

**Payload**:
```json
{
  "approval_id": "uuid",
  "proposal_id": "uuid",
  "text": "Please review and approve the following proposal: ...",
  "metadata": {
    "expires_in_minutes": 1440
  }
}
```

**Triggers**: When proposal.created has `requires_approval: true`.

### approval.granted
Owner grants approval for a proposal.

**Allowed Senders**: OWNER

**Payload**:
```json
{
  "approval_id": "uuid",
  "reason": "Looks good to me"
}
```

**Triggers**:
- Task creation
- Proposal execution

### approval.denied
Owner denies approval for a proposal.

**Allowed Senders**: OWNER

**Payload**:
```json
{
  "approval_id": "uuid",
  "reason": "Need more information"
}
```

**Triggers**: Proposal cancellation

### approval.timeout
Approval request expired without response.

**Allowed Senders**: orchestrator (system)

**Payload**:
```json
{
  "approval_id": "uuid",
  "reason": "Approval request expired after 24 hours"
}
```

## Task Events

### task.created
New task created for execution.

**Allowed Senders**: ADMIN, orchestrator

**Payload**:
```json
{
  "task_id": "uuid",
  "proposal_id": "uuid",
  "approval_id": "uuid",
  "action": "execute_proposal",
  "target_agent": "general-agent",
  "args": {
    "prompt": "Write sorting function",
    "language": "python"
  },
  "status": "created",
  "progress": 0
}
```

### task.started
Task execution started.

**Allowed Senders**: Agent (MEMBER)

**Payload**:
```json
{
  "task_id": "uuid",
  "target_agent": "general-agent",
  "status": "started",
  "progress": 0
}
```

### task.progress
Progress update during execution (0-100%).

**Allowed Senders**: Agent (MEMBER)

**Payload**:
```json
{
  "task_id": "uuid",
  "status": "progress",
  "progress": 45,
  "duration": 2500
}
```

### task.completed
Task execution completed successfully.

**Allowed Senders**: Agent (MEMBER)

**Payload**:
```json
{
  "task_id": "uuid",
  "status": "completed",
  "result": "def sort_array(arr): return sorted(arr)",
  "duration": 5000
}
```

### task.failed
Task execution failed.

**Allowed Senders**: Agent (MEMBER)

**Payload**:
```json
{
  "task_id": "uuid",
  "status": "failed",
  "error": "Memory limit exceeded",
  "duration": 3000
}
```

### task.cancelled
Task was cancelled.

**Allowed Senders**: ADMIN

**Payload**:
```json
{
  "task_id": "uuid",
  "status": "cancelled",
  "reason": "User requested cancellation"
}
```

## Result Events

### result.generated
Generic result event.

**Allowed Senders**: Agent (MEMBER)

**Payload**:
```json
{
  "task_id": "uuid",
  "proposal_id": "uuid",
  "type": "text",
  "data": {
    "output": "Result content"
  },
  "success": true,
  "duration": 5000
}
```

### result.image_analysis
Image analysis result from visual analyser.

**Allowed Senders**: visual-analyser

**Payload**:
```json
{
  "task_id": "uuid",
  "type": "image_analysis",
  "data": {
    "analysis": "The screenshot shows a login form with...",
    "detected_elements": ["text field", "button"],
    "confidence": 0.92
  },
  "success": true,
  "duration": 8000
}
```

### result.code_diff
Code changes result from Qwen.

**Allowed Senders**: qwen-code

**Payload**:
```json
{
  "task_id": "uuid",
  "type": "code_diff",
  "data": {
    "language": "python",
    "code": "def sort_array(arr): return sorted(arr)",
    "diff": "+ def sort_array\n+ return sorted",
    "filename": "solution.py"
  },
  "success": true,
  "duration": 12000,
  "attachments": [
    {
      "kind": "minio",
      "bucket": "jarvis",
      "key": "2026-01-31/uuid/solution.py",
      "size": 256,
      "etag": "abc123"
    }
  ]
}
```

### result.plan
Planning result from Qwen.

**Allowed Senders**: qwen-code

**Payload**:
```json
{
  "task_id": "uuid",
  "type": "plan",
  "data": {
    "plan": "1. Parse requirements\n2. Design architecture\n3. Implement...",
    "estimated_time_hours": 4
  },
  "success": true,
  "duration": 6000
}
```

### result.web_extraction
Web content extraction result from web fetcher.

**Allowed Senders**: web-fetcher

**Payload**:
```json
{
  "task_id": "uuid",
  "type": "web_extraction",
  "data": {
    "url": "https://example.com/prices",
    "content": "Extracted content here...",
    "extraction_method": "css_selector"
  },
  "success": true,
  "duration": 3000
}
```

### result.summary
Summary of completed thread from orchestrator.

**Allowed Senders**: orchestrator

**Payload**:
```json
{
  "title": "Code Generation Summary",
  "text": "Generated Python sorting function",
  "status": "success",
  "task_count": 3,
  "result_count": 3,
  "start_time": "2026-01-31T12:00:00Z",
  "end_time": "2026-01-31T12:05:00Z"
}
```

## Command Events

### command.run
Execute a command on a target agent.

**Allowed Senders**: ADMIN, OWNER

**Payload**:
```json
{
  "command": "analyze_image",
  "target_agent": "visual-analyser",
  "args": {
    "image_url": "https://example.com/image.png",
    "prompt": "Describe what you see"
  }
}
```

### command.cancel
Cancel an executing command.

**Allowed Senders**: ADMIN, OWNER

**Payload**:
```json
{
  "task_id": "uuid",
  "reason": "User requested cancellation"
}
```

### command.approve
Approve a pending approval.

**Allowed Senders**: OWNER

**Payload**:
```json
{
  "approval_id": "uuid",
  "reason": "Approved"
}
```

### command.reject
Reject a pending approval.

**Allowed Senders**: OWNER

**Payload**:
```json
{
  "approval_id": "uuid",
  "reason": "Please revise"
}
```

## System Events

### thread.created
New thread created.

**Allowed Senders**: ADMIN, orchestrator

**Payload**:
```json
{
  "thread_id": "uuid",
  "title": "Code Generation Task",
  "created_at": "2026-01-31T12:00:00Z"
}
```

### thread.archived
Thread archived (completed or abandoned).

**Allowed Senders**: ADMIN, OWNER

**Payload**:
```json
{
  "thread_id": "uuid",
  "reason": "Completed"
}
```

### error
Error occurred.

**Allowed Senders**: Any (MEMBER agents)

**Payload**:
```json
{
  "code": "AGENT_ERROR",
  "text": "Error message",
  "source": "general-agent",
  "recoverable": true,
  "details": {
    "exception_type": "TimeoutError"
  }
}
```

### audit.log
Audit log entry.

**Allowed Senders**: orchestrator

**Payload**:
```json
{
  "action": "approval_granted",
  "actor": "user-123",
  "resource": "approval-uuid",
  "result": "success",
  "timestamp": "2026-01-31T12:00:00Z"
}
```

## Attachment Events

### attachment.created
Attachment uploaded.

**Allowed Senders**: ADMIN, OWNER

**Payload**:
```json
{
  "attachment_id": "uuid",
  "name": "screenshot.png",
  "size": 102400,
  "mime": "image/png",
  "object_ref": {
    "kind": "minio",
    "bucket": "jarvis",
    "key": "2026-01-31/uuid/screenshot.png",
    "size": 102400,
    "etag": "abc123",
    "sha256": "hash"
  },
  "uploaded_by": "user-123"
}
```

### attachment.deleted
Attachment deleted.

**Allowed Senders**: ADMIN, OWNER

**Payload**:
```json
{
  "attachment_id": "uuid",
  "reason": "Cleanup"
}
```

## Memory Events

### memory.promotion
Memory promotion request.

**Allowed Senders**: ADMIN, OWNER

**Payload**:
```json
{
  "episode_id": "uuid",
  "content": "Important fact to remember",
  "confidence": 0.95,
  "reasoning": "Critical for future decisions",
  "category": "technical_knowledge"
}
```

### memory.proposal
Proposal for memory promotion from agent.

**Allowed Senders**: Agent (MEMBER)

**Payload**:
```json
{
  "episode_id": "uuid",
  "content": "Learned fact",
  "confidence": 0.85,
  "category": "user_preference",
  "requires_approval": true
}
```

## Event Flow Examples

### Example 1: Simple Chat Response

```
Owner sends chat.message
  ↓
Agent generates proposal.created (no approval needed)
  ↓
Orchestrator publishes task.created
  ↓
Agent publishes task.started
  ↓
Agent publishes task.progress (optional)
  ↓
Agent publishes task.completed
  ↓
Agent publishes result.generated
  ↓
Orchestrator publishes result.summary
```

### Example 2: Approval Workflow

```
Agent generates proposal.created (requires_approval: true)
  ↓
Orchestrator publishes approval.requested
  ↓
Owner publishes approval.granted
  ↓
Orchestrator publishes task.created
  ↓
Agent executes...
  ↓
Agent publishes result
  ↓
Orchestrator publishes result.summary
```

### Example 3: Error Handling

```
Agent starts task.started
  ↓
Agent encounters error
  ↓
Agent publishes error event
  ↓
Agent publishes task.failed
  ↓
Orchestrator publishes result.summary (status: failed)
```

---

**Version**: 1.0.0
**Last Updated**: 2026-01-31
