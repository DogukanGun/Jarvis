package workflows

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"time"

	"github.com/google/uuid"
	"jarvis/agent/schemas/group"
)

// QwenWorkflow handles the Plan -> Approve -> Implement workflow with Qwen
type QwenWorkflow struct {
	qwenURL string
	httpClient *http.Client
}

// NewQwenWorkflow creates a new Qwen workflow handler
func NewQwenWorkflow(qwenURL string) *QwenWorkflow {
	if qwenURL == "" {
		qwenURL = "http://localhost:3000"
	}

	return &QwenWorkflow{
		qwenURL: qwenURL,
		httpClient: &http.Client{
			Timeout: 5 * time.Minute,
		},
	}
}

// PlanRequest represents a request to Qwen for planning
type PlanRequest struct {
	Prompt string `json:"prompt"`
	Mode   string `json:"mode"` // "plan" or "implement"
}

// PlanResponse represents a response from Qwen
type PlanResponse struct {
	TaskID string `json:"task_id"`
	Status string `json:"status"`
	Plan   string `json:"plan,omitempty"`
	Output string `json:"output,omitempty"`
}

// TaskStatus represents the status of a Qwen task
type TaskStatus struct {
	TaskID string `json:"task_id"`
	Status string `json:"status"` // "pending", "running", "completed", "failed"
	Result string `json:"result,omitempty"`
	Error  string `json:"error,omitempty"`
}

// StartPlanTask starts a planning task with Qwen
func (qw *QwenWorkflow) StartPlanTask(ctx context.Context, prompt string) (string, error) {
	log.Printf("Starting plan task in Qwen: %s", prompt)

	reqBody := PlanRequest{
		Prompt: prompt,
		Mode:   "plan",
	}

	jsonBody, err := json.Marshal(reqBody)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %v", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", fmt.Sprintf("%s/api/task/start", qw.qwenURL),
		io.NopCloser(nil))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Body = io.NopCloser(bytes.NewReader(jsonBody))

	resp, err := qw.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to call Qwen API: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("Qwen API returned %d: %s", resp.StatusCode, string(body))
	}

	var planResp PlanResponse
	if err := json.NewDecoder(resp.Body).Decode(&planResp); err != nil {
		return "", fmt.Errorf("failed to decode response: %v", err)
	}

	return planResp.TaskID, nil
}

// StartImplementTask starts an implementation task with Qwen
func (qw *QwenWorkflow) StartImplementTask(ctx context.Context, prompt string, planContext string) (string, error) {
	log.Printf("Starting implement task in Qwen")

	// Combine prompt with plan context
	fullPrompt := fmt.Sprintf("%s\n\nBased on plan:\n%s", prompt, planContext)

	reqBody := PlanRequest{
		Prompt: fullPrompt,
		Mode:   "implement",
	}

	jsonBody, err := json.Marshal(reqBody)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %v", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", fmt.Sprintf("%s/api/task/start", qw.qwenURL),
		io.NopCloser(nil))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")
	req.Body = io.NopCloser(bytes.NewReader(jsonBody))

	resp, err := qw.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to call Qwen API: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return "", fmt.Errorf("Qwen API returned %d: %s", resp.StatusCode, string(body))
	}

	var implResp PlanResponse
	if err := json.NewDecoder(resp.Body).Decode(&implResp); err != nil {
		return "", fmt.Errorf("failed to decode response: %v", err)
	}

	return implResp.TaskID, nil
}

// GetTaskStatus retrieves the status of a Qwen task
func (qw *QwenWorkflow) GetTaskStatus(ctx context.Context, taskID string) (*TaskStatus, error) {
	req, err := http.NewRequestWithContext(ctx, "GET",
		fmt.Sprintf("%s/api/task/%s/status", qw.qwenURL, taskID), nil)
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %v", err)
	}

	resp, err := qw.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to call Qwen API: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return nil, fmt.Errorf("Qwen API returned %d: %s", resp.StatusCode, string(body))
	}

	var taskStatus TaskStatus
	if err := json.NewDecoder(resp.Body).Decode(&taskStatus); err != nil {
		return nil, fmt.Errorf("failed to decode response: %v", err)
	}

	return &taskStatus, nil
}

// PollTaskCompletion polls until a task is complete with timeout
func (qw *QwenWorkflow) PollTaskCompletion(ctx context.Context, taskID string, maxWait time.Duration) (*TaskStatus, error) {
	deadline := time.Now().Add(maxWait)
	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			return nil, ctx.Err()
		case <-ticker.C:
			if time.Now().After(deadline) {
				return nil, fmt.Errorf("task polling timed out after %v", maxWait)
			}

			status, err := qw.GetTaskStatus(ctx, taskID)
			if err != nil {
				log.Printf("Error getting task status: %v", err)
				continue
			}

			if status.Status == "completed" || status.Status == "failed" {
				return status, nil
			}

			log.Printf("Task %s status: %s", taskID, status.Status)
		}
	}
}

// ExecutePlanApprovalWorkflow executes a plan -> approve -> implement workflow
func (qw *QwenWorkflow) ExecutePlanApprovalWorkflow(
	ctx context.Context,
	initialPrompt string,
	onPlanGenerated func(plan string) error,
	onImplementationComplete func(code string) error,
) error {
	log.Printf("Starting plan-approval workflow")

	// Step 1: Generate plan
	taskID, err := qw.StartPlanTask(ctx, initialPrompt)
	if err != nil {
		return fmt.Errorf("failed to start plan task: %v", err)
	}

	log.Printf("Plan task started: %s", taskID)

	// Step 2: Poll for plan completion
	planStatus, err := qw.PollTaskCompletion(ctx, taskID, 5*time.Minute)
	if err != nil {
		return fmt.Errorf("failed to wait for plan: %v", err)
	}

	if planStatus.Status == "failed" {
		return fmt.Errorf("plan task failed: %s", planStatus.Error)
	}

	plan := planStatus.Result
	log.Printf("Plan generated: %s", plan[:min(100, len(plan))])

	// Step 3: Callback for approval (outside this workflow)
	if onPlanGenerated != nil {
		if err := onPlanGenerated(plan); err != nil {
			return fmt.Errorf("plan generation callback failed: %v", err)
		}
	}

	// Step 4: Start implementation (after approval)
	implTaskID, err := qw.StartImplementTask(ctx, initialPrompt, plan)
	if err != nil {
		return fmt.Errorf("failed to start implement task: %v", err)
	}

	log.Printf("Implementation task started: %s", implTaskID)

	// Step 5: Poll for implementation completion
	implStatus, err := qw.PollTaskCompletion(ctx, implTaskID, 10*time.Minute)
	if err != nil {
		return fmt.Errorf("failed to wait for implementation: %v", err)
	}

	if implStatus.Status == "failed" {
		return fmt.Errorf("implementation task failed: %s", implStatus.Error)
	}

	code := implStatus.Result
	log.Printf("Implementation completed")

	// Step 6: Callback for implementation completion
	if onImplementationComplete != nil {
		if err := onImplementationComplete(code); err != nil {
			return fmt.Errorf("implementation callback failed: %v", err)
		}
	}

	return nil
}

// min returns the minimum of two integers
func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}

// CreatePlanProposal creates a proposal event for a plan
func CreatePlanProposal(groupID string, threadID string, prompt string) *group.Envelope {
	proposalID := uuid.New().String()

	return group.NewEnvelope(
		groupID,
		threadID,
		uuid.New().String(),
		group.Sender{
			ID:    "orchestrator",
			Role:  group.RoleAdmin,
			Agent: "orchestrator",
		},
		group.EventProposalCreated,
		map[string]interface{}{
			"proposal_id":       proposalID,
			"title":             "Code Planning",
			"description":       prompt,
			"action":            "qwen_plan",
			"context":           prompt,
			"confidence":        0.9,
			"requires_approval": true,
		},
	)
}

// CreateImplementProposal creates a proposal event for implementation
func CreateImplementProposal(groupID string, threadID string, plan string) *group.Envelope {
	proposalID := uuid.New().String()

	return group.NewEnvelope(
		groupID,
		threadID,
		uuid.New().String(),
		group.Sender{
			ID:    "orchestrator",
			Role:  group.RoleAdmin,
			Agent: "orchestrator",
		},
		group.EventProposalCreated,
		map[string]interface{}{
			"proposal_id":       proposalID,
			"title":             "Code Implementation",
			"description":       fmt.Sprintf("Implement based on plan: %s", plan[:min(100, len(plan))]),
			"action":            "qwen_implement",
			"context":           plan,
			"confidence":        0.85,
			"requires_approval": true,
		},
	)
}
