package group

import (
	"encoding/json"
	"time"
)

// Role represents the role of a sender in the group
type Role string

const (
	RoleOwner  Role = "OWNER"
	RoleAdmin  Role = "ADMIN"
	RoleMember Role = "MEMBER"
)

// Sender represents who sent a message
type Sender struct {
	ID    string `json:"id"`
	Role  Role   `json:"role"`
	Agent string `json:"agent,omitempty"` // Agent name if sender is an agent
}

// ObjectRef represents a reference to an object in MinIO
type ObjectRef struct {
	Kind   string `json:"kind"`   // "minio"
	Bucket string `json:"bucket"`
	Key    string `json:"key"`
	ETag   string `json:"etag,omitempty"`
	Size   int64  `json:"size"`
	SHA256 string `json:"sha256,omitempty"`
}

// Envelope is the standard message wrapper for group communication
type Envelope struct {
	GroupID   string                 `json:"group_id"`
	MessageID string                 `json:"message_id"`
	Timestamp time.Time              `json:"timestamp"`
	ThreadID  string                 `json:"thread_id"`
	Sender    Sender                 `json:"sender"`
	Type      string                 `json:"type"` // Event type (chat.message, proposal.created, etc)
	Payload   map[string]interface{} `json:"payload"`
	Version   string                 `json:"version"` // Schema version for backwards compatibility
}

// MarshalJSON implements custom JSON marshaling for Envelope
func (e *Envelope) MarshalJSON() ([]byte, error) {
	type Alias Envelope
	return json.Marshal(&struct {
		Timestamp string `json:"timestamp"`
		*Alias
	}{
		Timestamp: e.Timestamp.UTC().Format(time.RFC3339Nano),
		Alias:     (*Alias)(e),
	})
}

// UnmarshalJSON implements custom JSON unmarshaling for Envelope
func (e *Envelope) UnmarshalJSON(data []byte) error {
	type Alias Envelope
	aux := &struct {
		Timestamp string `json:"timestamp"`
		*Alias
	}{
		Alias: (*Alias)(e),
	}
	if err := json.Unmarshal(data, &aux); err != nil {
		return err
	}
	var err error
	e.Timestamp, err = time.Parse(time.RFC3339Nano, aux.Timestamp)
	return err
}

// NewEnvelope creates a new envelope with default values
func NewEnvelope(groupID, threadID, messageID string, sender Sender, eventType string, payload map[string]interface{}) *Envelope {
	return &Envelope{
		GroupID:   groupID,
		MessageID: messageID,
		Timestamp: time.Now().UTC(),
		ThreadID:  threadID,
		Sender:    sender,
		Type:      eventType,
		Payload:   payload,
		Version:   "1.0",
	}
}
