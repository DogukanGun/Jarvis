package group

// Event type constants for group communication
const (
	// Chat events
	EventChatMessage = "chat.message"

	// Proposal events
	EventProposalCreated  = "proposal.created"
	EventProposalUpdated  = "proposal.updated"
	EventProposalRejected = "proposal.rejected"

	// Approval events
	EventApprovalRequested = "approval.requested"
	EventApprovalGranted   = "approval.granted"
	EventApprovalDenied    = "approval.denied"
	EventApprovalTimeout   = "approval.timeout"

	// Task events
	EventTaskCreated      = "task.created"
	EventTaskStarted      = "task.started"
	EventTaskProgress     = "task.progress"
	EventTaskCompleted    = "task.completed"
	EventTaskFailed       = "task.failed"
	EventTaskCancelled    = "task.cancelled"

	// Result events
	EventResultGenerated      = "result.generated"
	EventResultImageAnalysis  = "result.image_analysis"
	EventResultCodeDiff       = "result.code_diff"
	EventResultPlan           = "result.plan"
	EventResultWebExtraction  = "result.web_extraction"
	EventResultSummary        = "result.summary"

	// Command events (admin/orchestrator only)
	EventCommandRun            = "command.run"
	EventCommandCancel         = "command.cancel"
	EventCommandApprove        = "command.approve"
	EventCommandReject         = "command.reject"

	// System events
	EventThreadCreated   = "thread.created"
	EventThreadArchived  = "thread.archived"
	EventError           = "error"
	EventAuditLog        = "audit.log"

	// Attachment events
	EventAttachmentCreated = "attachment.created"
	EventAttachmentDeleted = "attachment.deleted"

	// Memory events
	EventMemoryPromotion = "memory.promotion"
	EventMemoryPromosal  = "memory.proposal"
)

// PayloadKeys are common keys used in event payloads
const (
	PayloadKeyText         = "text"
	PayloadKeyImageURL     = "image_url"
	PayloadKeyImageData    = "image_data"     // Base64 encoded
	PayloadKeyResult       = "result"
	PayloadKeyError        = "error"
	PayloadKeyTaskID       = "task_id"
	PayloadKeyApprovalID   = "approval_id"
	PayloadKeyProposalID   = "proposal_id"
	PayloadKeyThreadID     = "thread_id"
	PayloadKeyTargetAgent  = "target_agent"   // Which agent to run command on
	PayloadKeyCommand      = "command"
	PayloadKeyArgs         = "args"
	PayloadKeyStatus       = "status"
	PayloadKeyProgress     = "progress"       // 0-100
	PayloadKeyDuration     = "duration"       // In milliseconds
	PayloadKeyAttachments  = "attachments"    // []ObjectRef
	PayloadKeyContext      = "context"
	PayloadKeyMetadata     = "metadata"
	PayloadKeyReason       = "reason"
	PayloadKeyTimedOut     = "timed_out"
)

// ApprovalStatus represents the status of an approval
type ApprovalStatus string

const (
	ApprovalStatusPending  ApprovalStatus = "pending"
	ApprovalStatusGranted  ApprovalStatus = "granted"
	ApprovalStatusDenied   ApprovalStatus = "denied"
	ApprovalStatusTimeout  ApprovalStatus = "timeout"
)

// TaskStatus represents the status of a task
type TaskStatus string

const (
	TaskStatusCreated   TaskStatus = "created"
	TaskStatusStarted   TaskStatus = "started"
	TaskStatusProgress  TaskStatus = "progress"
	TaskStatusCompleted TaskStatus = "completed"
	TaskStatusFailed    TaskStatus = "failed"
	TaskStatusCancelled TaskStatus = "cancelled"
)

// ResultType represents the type of result
type ResultType string

const (
	ResultTypeText          ResultType = "text"
	ResultTypeImageAnalysis ResultType = "image_analysis"
	ResultTypeCodeDiff      ResultType = "code_diff"
	ResultTypePlan          ResultType = "plan"
	ResultTypeWebExtraction ResultType = "web_extraction"
	ResultTypeSummary       ResultType = "summary"
)
