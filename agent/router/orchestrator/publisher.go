package orchestrator

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"

	"github.com/google/uuid"
	"github.com/segmentio/kafka-go"
	"jarvis/agent/schemas/group"
)

// Publisher publishes events to Kafka topics
type Publisher struct {
	eventWriter *kafka.Writer
	cmdWriter   *kafka.Writer
	groupID     string
}

// NewPublisher creates a new publisher
func NewPublisher(brokers []string, groupID string) (*Publisher, error) {
	eventWriter := &kafka.Writer{
		Addr:     kafka.TCP(brokers...),
		Topic:    group.EventsTopic(groupID),
		Balancer: &kafka.LeastBytes{},
	}

	cmdWriter := &kafka.Writer{
		Addr:     kafka.TCP(brokers...),
		Topic:    group.CommandsTopic(groupID),
		Balancer: &kafka.LeastBytes{},
	}

	return &Publisher{
		eventWriter: eventWriter,
		cmdWriter:   cmdWriter,
		groupID:     groupID,
	}, nil
}

// PublishEvent publishes an event to the events topic
func (p *Publisher) PublishEvent(ctx context.Context, sender group.Sender, eventType string, payload map[string]interface{}) (*group.Envelope, error) {
	// Generate IDs
	messageID := uuid.New().String()
	threadID, ok := payload["thread_id"].(string)
	if !ok || threadID == "" {
		threadID = uuid.New().String()
	}

	// Create envelope
	envelope := group.NewEnvelope(p.groupID, threadID, messageID, sender, eventType, payload)

	// Validate
	if err := group.ValidateEnvelope(envelope); err != nil {
		return nil, fmt.Errorf("invalid envelope: %v", err)
	}

	// Serialize
	data, err := json.Marshal(envelope)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal envelope: %v", err)
	}

	// Write to Kafka
	message := kafka.Message{
		Key:   []byte(envelope.ThreadID),
		Value: data,
	}

	if err := p.eventWriter.WriteMessages(ctx, message); err != nil {
		return nil, fmt.Errorf("failed to publish event: %v", err)
	}

	log.Printf("Published %s event: %s", eventType, messageID)
	return envelope, nil
}

// PublishCommand publishes a command (admin only)
func (p *Publisher) PublishCommand(ctx context.Context, sender group.Sender, command string, targetAgent string, args map[string]interface{}) (*group.Envelope, error) {
	// Verify sender has permission
	if !group.CanPerform(sender.Role, group.PermissionCommandRun) {
		return nil, fmt.Errorf("role %s cannot run commands", sender.Role)
	}

	payload := map[string]interface{}{
		group.PayloadKeyCommand:     command,
		group.PayloadKeyTargetAgent: targetAgent,
		group.PayloadKeyArgs:        args,
	}

	return p.PublishEvent(ctx, sender, group.EventCommandRun, payload)
}

// PublishApprovalRequest publishes an approval request
func (p *Publisher) PublishApprovalRequest(ctx context.Context, sender group.Sender, proposalID string, description string) (*group.Envelope, error) {
	approvalID := uuid.New().String()
	threadID := uuid.New().String() // Get from context ideally

	payload := map[string]interface{}{
		group.PayloadKeyApprovalID: approvalID,
		group.PayloadKeyProposalID: proposalID,
		group.PayloadKeyText:       description,
		group.PayloadKeyThreadID:   threadID,
	}

	return p.PublishEvent(ctx, sender, group.EventApprovalRequested, payload)
}

// PublishProposal publishes a proposal event
func (p *Publisher) PublishProposal(ctx context.Context, sender group.Sender, proposalPayload group.ProposalPayload, threadID string) (*group.Envelope, error) {
	payload := map[string]interface{}{
		group.PayloadKeyText:        proposalPayload.Description,
		"proposal_id":               proposalPayload.ProposalID,
		"title":                     proposalPayload.Title,
		"action":                    proposalPayload.Action,
		"context":                   proposalPayload.Context,
		"confidence":                proposalPayload.Confidence,
		"requires_approval":         proposalPayload.RequiresApproval,
		group.PayloadKeyThreadID:    threadID,
	}

	if len(proposalPayload.Attachments) > 0 {
		payload[group.PayloadKeyAttachments] = proposalPayload.Attachments
	}

	payload["metadata"] = proposalPayload.Metadata

	return p.PublishEvent(ctx, sender, group.EventProposalCreated, payload)
}

// PublishTaskEvent publishes a task event
func (p *Publisher) PublishTaskEvent(ctx context.Context, sender group.Sender, task group.TaskPayload) (*group.Envelope, error) {
	eventType := group.EventTaskCreated
	switch task.Status {
	case "started":
		eventType = group.EventTaskStarted
	case "progress":
		eventType = group.EventTaskProgress
	case "completed":
		eventType = group.EventTaskCompleted
	case "failed":
		eventType = group.EventTaskFailed
	}

	payload := map[string]interface{}{
		group.PayloadKeyTaskID:      task.TaskID,
		group.PayloadKeyProposalID:  task.ProposalID,
		group.PayloadKeyApprovalID:  task.ApprovalID,
		"action":                    task.Action,
		group.PayloadKeyTargetAgent: task.TargetAgent,
		"args":                      task.Args,
		group.PayloadKeyStatus:      task.Status,
		group.PayloadKeyProgress:    task.Progress,
		group.PayloadKeyDuration:    task.Duration,
		group.PayloadKeyThreadID:    task.TaskID[:8], // Use prefix for now
	}

	if task.Error != "" {
		payload[group.PayloadKeyError] = task.Error
	}

	if len(task.Attachments) > 0 {
		payload[group.PayloadKeyAttachments] = task.Attachments
	}

	if task.Metadata != nil {
		payload[group.PayloadKeyMetadata] = task.Metadata
	}

	return p.PublishEvent(ctx, sender, eventType, payload)
}

// PublishResult publishes a result event
func (p *Publisher) PublishResult(ctx context.Context, sender group.Sender, result group.ResultPayload) (*group.Envelope, error) {
	eventType := group.EventResultGenerated
	switch result.Type {
	case group.ResultTypeImageAnalysis:
		eventType = group.EventResultImageAnalysis
	case group.ResultTypeCodeDiff:
		eventType = group.EventResultCodeDiff
	case group.ResultTypePlan:
		eventType = group.EventResultPlan
	case group.ResultTypeWebExtraction:
		eventType = group.EventResultWebExtraction
	}

	payload := map[string]interface{}{
		group.PayloadKeyTaskID:     result.TaskID,
		group.PayloadKeyProposalID: result.ProposalID,
		"type":                     result.Type,
		"data":                     result.Data,
		"success":                  result.Success,
		group.PayloadKeyDuration:   result.Duration,
		group.PayloadKeyThreadID:   result.TaskID[:8],
	}

	if result.Error != "" {
		payload[group.PayloadKeyError] = result.Error
	}

	if len(result.Attachments) > 0 {
		payload[group.PayloadKeyAttachments] = result.Attachments
	}

	if result.Metadata != nil {
		payload[group.PayloadKeyMetadata] = result.Metadata
	}

	return p.PublishEvent(ctx, sender, eventType, payload)
}

// PublishError publishes an error event
func (p *Publisher) PublishError(ctx context.Context, sender group.Sender, code string, message string, details map[string]interface{}) (*group.Envelope, error) {
	payload := map[string]interface{}{
		"code":    code,
		group.PayloadKeyText: message,
		"details": details,
		"source":  sender.Agent,
	}

	return p.PublishEvent(ctx, sender, group.EventError, payload)
}

// PublishApprovalDecision publishes an approval decision
func (p *Publisher) PublishApprovalDecision(ctx context.Context, sender group.Sender, approvalID string, granted bool, reason string, threadID string) (*group.Envelope, error) {
	eventType := group.EventApprovalDenied
	if granted {
		eventType = group.EventApprovalGranted
	}

	payload := map[string]interface{}{
		group.PayloadKeyApprovalID: approvalID,
		group.PayloadKeyText:       reason,
		group.PayloadKeyThreadID:   threadID,
	}

	return p.PublishEvent(ctx, sender, eventType, payload)
}

// PublishSummary publishes a thread summary
func (p *Publisher) PublishSummary(ctx context.Context, summary group.SummaryPayload) (*group.Envelope, error) {
	orchestratorID := os.Getenv("ORCHESTRATOR_ID")
	if orchestratorID == "" {
		orchestratorID = "orchestrator"
	}

	sender := group.Sender{
		ID:    orchestratorID,
		Role:  group.RoleAdmin,
		Agent: "orchestrator",
	}

	payload := map[string]interface{}{
		"title":       summary.Title,
		group.PayloadKeyText: summary.Description,
		group.PayloadKeyStatus:    summary.Status,
		"task_count":  summary.TaskCount,
		"result_count": summary.ResultCount,
		"start_time":  summary.StartTime,
		"end_time":    summary.EndTime,
		group.PayloadKeyThreadID: summary.ThreadID,
	}

	if len(summary.Attachments) > 0 {
		payload[group.PayloadKeyAttachments] = summary.Attachments
	}

	if summary.Metadata != nil {
		payload[group.PayloadKeyMetadata] = summary.Metadata
	}

	return p.PublishEvent(ctx, sender, group.EventResultSummary, payload)
}

// Close closes the writers
func (p *Publisher) Close() error {
	if p.eventWriter != nil {
		if err := p.eventWriter.Close(); err != nil {
			return fmt.Errorf("failed to close event writer: %v", err)
		}
	}
	if p.cmdWriter != nil {
		if err := p.cmdWriter.Close(); err != nil {
			return fmt.Errorf("failed to close command writer: %v", err)
		}
	}
	return nil
}
