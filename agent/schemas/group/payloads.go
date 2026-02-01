package group

// ChatMessagePayload represents a chat message
type ChatMessagePayload struct {
	Text        string      `json:"text"`
	ImageURL    string      `json:"image_url,omitempty"`
	ImageData   string      `json:"image_data,omitempty"` // Base64 encoded
	Attachments []ObjectRef `json:"attachments,omitempty"`
}

// ProposalPayload represents a proposal for an action
type ProposalPayload struct {
	ProposalID  string      `json:"proposal_id"`
	Title       string      `json:"title"`
	Description string      `json:"description"`
	Action      string      `json:"action"` // The action to take
	Context     string      `json:"context"` // Context from the original message
	Confidence  float32     `json:"confidence"` // Confidence score 0-1
	RequiresApproval bool   `json:"requires_approval"`
	Attachments []ObjectRef `json:"attachments,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// ApprovalPayload represents an approval request or decision
type ApprovalPayload struct {
	ApprovalID  string                 `json:"approval_id"`
	ProposalID  string                 `json:"proposal_id"`
	TaskID      string                 `json:"task_id,omitempty"`
	Status      ApprovalStatus         `json:"status"`
	Reason      string                 `json:"reason,omitempty"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// TaskPayload represents a task that needs to be executed
type TaskPayload struct {
	TaskID       string                 `json:"task_id"`
	ProposalID   string                 `json:"proposal_id,omitempty"`
	ApprovalID   string                 `json:"approval_id,omitempty"`
	Action       string                 `json:"action"`
	TargetAgent  string                 `json:"target_agent"`
	Args         map[string]interface{} `json:"args"`
	Status       TaskStatus             `json:"status"`
	Progress     int                    `json:"progress"` // 0-100
	Duration     int64                  `json:"duration"` // milliseconds
	Error        string                 `json:"error,omitempty"`
	Attachments  []ObjectRef            `json:"attachments,omitempty"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
}

// ResultPayload represents a result from task execution
type ResultPayload struct {
	TaskID       string                 `json:"task_id"`
	ProposalID   string                 `json:"proposal_id,omitempty"`
	Type         ResultType             `json:"type"`
	Data         map[string]interface{} `json:"data"`
	Success      bool                   `json:"success"`
	Error        string                 `json:"error,omitempty"`
	Duration     int64                  `json:"duration"` // milliseconds
	Attachments  []ObjectRef            `json:"attachments,omitempty"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
}

// CommandPayload represents a command to be executed
type CommandPayload struct {
	CommandID   string                 `json:"command_id"`
	Command     string                 `json:"command"`
	TargetAgent string                 `json:"target_agent"`
	Args        map[string]interface{} `json:"args"`
	Metadata    map[string]interface{} `json:"metadata,omitempty"`
}

// SummaryPayload represents a summary of completed work
type SummaryPayload struct {
	ThreadID     string        `json:"thread_id"`
	Title        string        `json:"title"`
	Description  string        `json:"description"`
	Status       string        `json:"status"` // success, partial, failed
	TaskCount    int           `json:"task_count"`
	ResultCount  int           `json:"result_count"`
	StartTime    string        `json:"start_time"`
	EndTime      string        `json:"end_time"`
	Attachments  []ObjectRef   `json:"attachments,omitempty"`
	Metadata     map[string]interface{} `json:"metadata,omitempty"`
}

// AttachmentPayload represents an attachment
type AttachmentPayload struct {
	AttachmentID string    `json:"attachment_id"`
	Name         string    `json:"name"`
	Size         int64     `json:"size"`
	MIME         string    `json:"mime"`
	ObjectRef    ObjectRef `json:"object_ref"`
	UploadedAt   string    `json:"uploaded_at"`
	UploadedBy   string    `json:"uploaded_by"`
}

// ErrorPayload represents an error that occurred
type ErrorPayload struct {
	ErrorID    string                 `json:"error_id"`
	Code       string                 `json:"code"`
	Message    string                 `json:"message"`
	Details    map[string]interface{} `json:"details,omitempty"`
	Source     string                 `json:"source"` // Which component generated the error
	Recoverable bool                  `json:"recoverable"`
	Context    string                 `json:"context,omitempty"`
}

// AuditLogPayload represents an audit log entry
type AuditLogPayload struct {
	Action     string                 `json:"action"`
	Actor      string                 `json:"actor"`
	Resource   string                 `json:"resource"`
	Changes    map[string]interface{} `json:"changes,omitempty"`
	Result     string                 `json:"result"` // success, failure, partial
	Details    map[string]interface{} `json:"details,omitempty"`
	Timestamp  string                 `json:"timestamp"`
}

// MemoryPromotionPayload represents a memory promotion request
type MemoryPromotionPayload struct {
	EpisodeID   string `json:"episode_id"`
	Content     string `json:"content"`
	Confidence  float32 `json:"confidence"`
	Reasoning   string `json:"reasoning"`
	Category    string `json:"category"`
	RequiresApproval bool `json:"requires_approval"`
}
