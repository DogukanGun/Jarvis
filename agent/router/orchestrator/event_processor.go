package orchestrator

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/google/uuid"
	"jarvis/agent/schemas/group"
)

// EventProcessor processes incoming events and orchestrates workflows
type EventProcessor struct {
	stateManager *StateManager
	publisher    *Publisher
	groupID      string
	adminID      string
}

// NewEventProcessor creates a new event processor
func NewEventProcessor(stateManager *StateManager, publisher *Publisher, groupID string) *EventProcessor {
	adminID := os.Getenv("ADMIN_ID")
	if adminID == "" {
		adminID = "orchestrator"
	}

	return &EventProcessor{
		stateManager: stateManager,
		publisher:    publisher,
		groupID:      groupID,
		adminID:      adminID,
	}
}

// ProcessEnvelope processes an incoming envelope
func (ep *EventProcessor) ProcessEnvelope(ctx context.Context, envelope *group.Envelope) error {
	if envelope == nil {
		return fmt.Errorf("envelope is nil")
	}

	log.Printf("Processing event: %s from %s (role: %s)", envelope.Type, envelope.Sender.ID, envelope.Sender.Role)

	// Route by event type
	switch envelope.Type {
	case group.EventChatMessage:
		return ep.handleChatMessage(ctx, envelope)
	case group.EventProposalCreated:
		return ep.handleProposalCreated(ctx, envelope)
	case group.EventApprovalRequested:
		return ep.handleApprovalRequested(ctx, envelope)
	case group.EventApprovalGranted:
		return ep.handleApprovalGranted(ctx, envelope)
	case group.EventApprovalDenied:
		return ep.handleApprovalDenied(ctx, envelope)
	case group.EventTaskStarted:
		return ep.handleTaskStarted(ctx, envelope)
	case group.EventTaskProgress:
		return ep.handleTaskProgress(ctx, envelope)
	case group.EventTaskCompleted:
		return ep.handleTaskCompleted(ctx, envelope)
	case group.EventTaskFailed:
		return ep.handleTaskFailed(ctx, envelope)
	case group.EventResultGenerated, group.EventResultImageAnalysis, group.EventResultCodeDiff,
		group.EventResultPlan, group.EventResultWebExtraction:
		return ep.handleResult(ctx, envelope)
	default:
		log.Printf("Ignoring event type: %s", envelope.Type)
		return nil
	}
}

// handleChatMessage handles incoming chat messages from owner
func (ep *EventProcessor) handleChatMessage(ctx context.Context, envelope *group.Envelope) error {
	// Only owner can send chat messages
	if envelope.Sender.Role != group.RoleOwner {
		log.Printf("Non-owner sent chat message, ignoring")
		return nil
	}

	// Ensure thread exists
	if _, err := ep.stateManager.GetThread(envelope.ThreadID); err != nil {
		// Create new thread
		text, _ := envelope.Payload["text"].(string)
		if _, err := ep.stateManager.CreateThread(ep.groupID, envelope.ThreadID, text); err != nil {
			return fmt.Errorf("failed to create thread: %v", err)
		}
	}

	// Add message to thread
	if err := ep.stateManager.AddMessageToThread(envelope.ThreadID, envelope.MessageID); err != nil {
		return fmt.Errorf("failed to add message to thread: %v", err)
	}

	// In real implementation, would call LLM to analyze intent and generate proposal
	// For now, just log it
	text, _ := envelope.Payload["text"].(string)
	log.Printf("Chat message from owner: %s", text)

	return nil
}

// handleProposalCreated handles proposal creation
func (ep *EventProcessor) handleProposalCreated(ctx context.Context, envelope *group.Envelope) error {
	// Admin should send proposals
	if envelope.Sender.Role != group.RoleAdmin && envelope.Sender.Agent != "orchestrator" {
		log.Printf("Non-admin sent proposal, ignoring")
		return nil
	}

	proposalID, _ := envelope.Payload["proposal_id"].(string)
	requiresApproval, _ := envelope.Payload["requires_approval"].(bool)

	log.Printf("Proposal created: %s (requires_approval: %v)", proposalID, requiresApproval)

	if requiresApproval {
		// Create approval gate
		approvalID := uuid.New().String()
		if _, err := ep.stateManager.CreateApprovalGate(approvalID, proposalID, "", envelope.Sender.ID); err != nil {
			return fmt.Errorf("failed to create approval gate: %v", err)
		}

		// Publish approval request to owner
		description, _ := envelope.Payload[group.PayloadKeyText].(string)
		_, err := ep.publisher.PublishApprovalRequest(ctx, group.Sender{
			ID:    ep.adminID,
			Role:  group.RoleAdmin,
			Agent: "orchestrator",
		}, proposalID, description)

		if err != nil {
			return fmt.Errorf("failed to publish approval request: %v", err)
		}
	}

	return nil
}

// handleApprovalRequested handles approval requests
func (ep *EventProcessor) handleApprovalRequested(ctx context.Context, envelope *group.Envelope) error {
	approvalID, _ := envelope.Payload[group.PayloadKeyApprovalID].(string)
	proposalID, _ := envelope.Payload[group.PayloadKeyProposalID].(string)

	log.Printf("Approval requested: %s for proposal %s", approvalID, proposalID)

	// Gate created in proposal handler, just track it
	return nil
}

// handleApprovalGranted handles approval grants from owner
func (ep *EventProcessor) handleApprovalGranted(ctx context.Context, envelope *group.Envelope) error {
	approvalID, _ := envelope.Payload[group.PayloadKeyApprovalID].(string)

	// Only owner can grant approvals
	if envelope.Sender.Role != group.RoleOwner {
		log.Printf("Non-owner tried to grant approval, rejecting")
		return nil
	}

	if err := ep.stateManager.GrantApproval(approvalID); err != nil {
		return fmt.Errorf("failed to grant approval: %v", err)
	}

	log.Printf("Approval granted: %s", approvalID)

	// In real implementation, would trigger task creation based on proposal
	return nil
}

// handleApprovalDenied handles approval denials from owner
func (ep *EventProcessor) handleApprovalDenied(ctx context.Context, envelope *group.Envelope) error {
	approvalID, _ := envelope.Payload[group.PayloadKeyApprovalID].(string)

	// Only owner can deny approvals
	if envelope.Sender.Role != group.RoleOwner {
		log.Printf("Non-owner tried to deny approval, rejecting")
		return nil
	}

	if err := ep.stateManager.DenyApproval(approvalID); err != nil {
		return fmt.Errorf("failed to deny approval: %v", err)
	}

	log.Printf("Approval denied: %s", approvalID)
	return nil
}

// handleTaskStarted handles task start notifications
func (ep *EventProcessor) handleTaskStarted(ctx context.Context, envelope *group.Envelope) error {
	taskID, _ := envelope.Payload[group.PayloadKeyTaskID].(string)
	targetAgent, _ := envelope.Payload[group.PayloadKeyTargetAgent].(string)

	log.Printf("Task started: %s by agent %s", taskID, targetAgent)

	if err := ep.stateManager.UpdateTaskStatus(taskID, "started", 0, ""); err != nil {
		// Task might not exist in state yet, log and continue
		log.Printf("Task %s not in state: %v", taskID, err)
	}

	return nil
}

// handleTaskProgress handles task progress updates
func (ep *EventProcessor) handleTaskProgress(ctx context.Context, envelope *group.Envelope) error {
	taskID, _ := envelope.Payload[group.PayloadKeyTaskID].(string)
	progress, _ := envelope.Payload[group.PayloadKeyProgress].(float64)

	log.Printf("Task progress: %s - %d%%", taskID, int(progress))

	if err := ep.stateManager.UpdateTaskStatus(taskID, "progress", int(progress), ""); err != nil {
		log.Printf("Failed to update task progress: %v", err)
	}

	return nil
}

// handleTaskCompleted handles task completion
func (ep *EventProcessor) handleTaskCompleted(ctx context.Context, envelope *group.Envelope) error {
	taskID, _ := envelope.Payload[group.PayloadKeyTaskID].(string)

	log.Printf("Task completed: %s", taskID)

	result := envelope.Payload["result"]
	if err := ep.stateManager.CompleteTask(taskID, result); err != nil {
		log.Printf("Failed to complete task: %v", err)
	}

	return nil
}

// handleTaskFailed handles task failures
func (ep *EventProcessor) handleTaskFailed(ctx context.Context, envelope *group.Envelope) error {
	taskID, _ := envelope.Payload[group.PayloadKeyTaskID].(string)
	errorMsg, _ := envelope.Payload[group.PayloadKeyError].(string)

	log.Printf("Task failed: %s - %s", taskID, errorMsg)

	if err := ep.stateManager.FailTask(taskID, errorMsg); err != nil {
		log.Printf("Failed to mark task as failed: %v", err)
	}

	return nil
}

// handleResult handles result events
func (ep *EventProcessor) handleResult(ctx context.Context, envelope *group.Envelope) error {
	taskID, _ := envelope.Payload[group.PayloadKeyTaskID].(string)
	data := envelope.Payload["data"]

	log.Printf("Result received for task: %s", taskID)

	// Store result in task state
	task, err := ep.stateManager.GetTask(taskID)
	if err != nil {
		// Task might not exist in state, still process result
		log.Printf("Task %s not in state: %v", taskID, err)
		return nil
	}

	task.Result = data
	return nil
}

// ProcessApprovalTimeouts checks for expired approvals and publishes timeout events
func (ep *EventProcessor) ProcessApprovalTimeouts(ctx context.Context) error {
	expired := ep.stateManager.GetExpiredApprovals()

	orchestrator := group.Sender{
		ID:    ep.adminID,
		Role:  group.RoleAdmin,
		Agent: "orchestrator",
	}

	for _, approval := range expired {
		log.Printf("Approval timed out: %s", approval.ApprovalID)

		// Mark as timeout (don't auto-deny in state, let events be source of truth)
		payload := map[string]interface{}{
			group.PayloadKeyApprovalID: approval.ApprovalID,
			group.PayloadKeyText:       "Approval request expired",
		}

		_, err := ep.publisher.PublishEvent(ctx, orchestrator, group.EventApprovalTimeout, payload)
		if err != nil {
			log.Printf("Failed to publish timeout event: %v", err)
		}
	}

	return nil
}

// GenerateThreadSummary generates a summary of a completed thread
func (ep *EventProcessor) GenerateThreadSummary(ctx context.Context, threadID string) error {
	thread, err := ep.stateManager.GetThread(threadID)
	if err != nil {
		return fmt.Errorf("failed to get thread: %v", err)
	}

	// Count tasks and results
	tasks := ep.stateManager.GetTasksByStatus("completed")
	taskCount := 0
	for _, t := range tasks {
		// Count only tasks from this thread
		if t.ProposalID != "" {
			taskCount++
		}
	}

	summary := group.SummaryPayload{
		ThreadID:    threadID,
		Title:       thread.Title,
		Description: fmt.Sprintf("Completed %d tasks", taskCount),
		Status:      "success",
		TaskCount:   taskCount,
		ResultCount: taskCount,
		StartTime:   thread.CreatedAt.Format(time.RFC3339),
		EndTime:     time.Now().Format(time.RFC3339),
	}

	_, err = ep.publisher.PublishSummary(ctx, summary)
	return err
}
