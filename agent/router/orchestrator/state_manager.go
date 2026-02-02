package orchestrator

import (
	"fmt"
	"sync"
	"time"
)

// ApprovalGate represents a pending approval
type ApprovalGate struct {
	ApprovalID  string
	ProposalID  string
	TaskID      string
	CreatedAt   time.Time
	ExpiresAt   time.Time
	Status      string // pending, granted, denied
	RequestedBy string
}

// Thread represents a conversation thread
type Thread struct {
	ThreadID    string
	GroupID     string
	CreatedAt   time.Time
	UpdatedAt   time.Time
	Title       string
	Status      string // active, archived
	Messages    []string
	ApprovalIDs []string
	TaskIDs     []string
}

// TaskState represents the state of a task
type TaskState struct {
	TaskID      string
	ProposalID  string
	ApprovalID  string
	Status      string // created, started, progress, completed, failed, cancelled
	Progress    int    // 0-100
	CreatedAt   time.Time
	UpdatedAt   time.Time
	Error       string
	Result      interface{}
	TargetAgent string
}

// StateManager manages the state of threads, approvals, and tasks
type StateManager struct {
	mu         sync.RWMutex
	threads    map[string]*Thread
	approvals  map[string]*ApprovalGate
	tasks      map[string]*TaskState
	approvalTTL time.Duration // How long approval gates last before auto-deny
}

// NewStateManager creates a new state manager
func NewStateManager(approvalTTLMinutes int) *StateManager {
	return &StateManager{
		threads:     make(map[string]*Thread),
		approvals:   make(map[string]*ApprovalGate),
		tasks:       make(map[string]*TaskState),
		approvalTTL: time.Duration(approvalTTLMinutes) * time.Minute,
	}
}

// CreateThread creates a new thread
func (sm *StateManager) CreateThread(groupID, threadID, title string) (*Thread, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	if _, exists := sm.threads[threadID]; exists {
		return nil, fmt.Errorf("thread %s already exists", threadID)
	}

	now := time.Now()
	thread := &Thread{
		ThreadID:  threadID,
		GroupID:   groupID,
		CreatedAt: now,
		UpdatedAt: now,
		Title:     title,
		Status:    "active",
		Messages:  make([]string, 0),
		ApprovalIDs: make([]string, 0),
		TaskIDs:   make([]string, 0),
	}

	sm.threads[threadID] = thread
	return thread, nil
}

// GetThread retrieves a thread
func (sm *StateManager) GetThread(threadID string) (*Thread, error) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	thread, exists := sm.threads[threadID]
	if !exists {
		return nil, fmt.Errorf("thread %s not found", threadID)
	}
	return thread, nil
}

// UpdateThreadActivity updates the thread's last update time
func (sm *StateManager) UpdateThreadActivity(threadID string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	thread, exists := sm.threads[threadID]
	if !exists {
		return fmt.Errorf("thread %s not found", threadID)
	}
	thread.UpdatedAt = time.Now()
	return nil
}

// AddMessageToThread adds a message ID to a thread
func (sm *StateManager) AddMessageToThread(threadID, messageID string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	thread, exists := sm.threads[threadID]
	if !exists {
		return fmt.Errorf("thread %s not found", threadID)
	}
	thread.Messages = append(thread.Messages, messageID)
	thread.UpdatedAt = time.Now()
	return nil
}

// CreateApprovalGate creates a pending approval
func (sm *StateManager) CreateApprovalGate(approvalID, proposalID, taskID, requestedBy string) (*ApprovalGate, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	if _, exists := sm.approvals[approvalID]; exists {
		return nil, fmt.Errorf("approval %s already exists", approvalID)
	}

	now := time.Now()
	approval := &ApprovalGate{
		ApprovalID:  approvalID,
		ProposalID:  proposalID,
		TaskID:      taskID,
		CreatedAt:   now,
		ExpiresAt:   now.Add(sm.approvalTTL),
		Status:      "pending",
		RequestedBy: requestedBy,
	}

	sm.approvals[approvalID] = approval
	return approval, nil
}

// GetApprovalGate retrieves an approval gate
func (sm *StateManager) GetApprovalGate(approvalID string) (*ApprovalGate, error) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	approval, exists := sm.approvals[approvalID]
	if !exists {
		return nil, fmt.Errorf("approval %s not found", approvalID)
	}
	return approval, nil
}

// GrantApproval marks an approval as granted
func (sm *StateManager) GrantApproval(approvalID string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	approval, exists := sm.approvals[approvalID]
	if !exists {
		return fmt.Errorf("approval %s not found", approvalID)
	}

	approval.Status = "granted"
	return nil
}

// DenyApproval marks an approval as denied
func (sm *StateManager) DenyApproval(approvalID string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	approval, exists := sm.approvals[approvalID]
	if !exists {
		return fmt.Errorf("approval %s not found", approvalID)
	}

	approval.Status = "denied"
	return nil
}

// GetPendingApprovals returns all pending approvals that haven't timed out
func (sm *StateManager) GetPendingApprovals() []*ApprovalGate {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	now := time.Now()
	var pending []*ApprovalGate

	for _, approval := range sm.approvals {
		if approval.Status == "pending" && now.Before(approval.ExpiresAt) {
			pending = append(pending, approval)
		}
	}

	return pending
}

// GetExpiredApprovals returns all pending approvals that have timed out
func (sm *StateManager) GetExpiredApprovals() []*ApprovalGate {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	now := time.Now()
	var expired []*ApprovalGate

	for _, approval := range sm.approvals {
		if approval.Status == "pending" && now.After(approval.ExpiresAt) {
			expired = append(expired, approval)
		}
	}

	return expired
}

// CreateTask creates a new task
func (sm *StateManager) CreateTask(taskID, proposalID, approvalID, targetAgent, action string) (*TaskState, error) {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	if _, exists := sm.tasks[taskID]; exists {
		return nil, fmt.Errorf("task %s already exists", taskID)
	}

	now := time.Now()
	task := &TaskState{
		TaskID:      taskID,
		ProposalID:  proposalID,
		ApprovalID:  approvalID,
		Status:      "created",
		Progress:    0,
		CreatedAt:   now,
		UpdatedAt:   now,
		TargetAgent: targetAgent,
	}

	sm.tasks[taskID] = task
	return task, nil
}

// GetTask retrieves a task
func (sm *StateManager) GetTask(taskID string) (*TaskState, error) {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	task, exists := sm.tasks[taskID]
	if !exists {
		return nil, fmt.Errorf("task %s not found", taskID)
	}
	return task, nil
}

// UpdateTaskStatus updates task status and progress
func (sm *StateManager) UpdateTaskStatus(taskID, status string, progress int, error string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	task, exists := sm.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}

	task.Status = status
	task.Progress = progress
	task.Error = error
	task.UpdatedAt = time.Now()
	return nil
}

// CompleteTask marks a task as completed with a result
func (sm *StateManager) CompleteTask(taskID string, result interface{}) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	task, exists := sm.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}

	task.Status = "completed"
	task.Progress = 100
	task.Result = result
	task.UpdatedAt = time.Now()
	return nil
}

// FailTask marks a task as failed
func (sm *StateManager) FailTask(taskID, error string) error {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	task, exists := sm.tasks[taskID]
	if !exists {
		return fmt.Errorf("task %s not found", taskID)
	}

	task.Status = "failed"
	task.Error = error
	task.UpdatedAt = time.Now()
	return nil
}

// GetTasksByStatus returns all tasks with a specific status
func (sm *StateManager) GetTasksByStatus(status string) []*TaskState {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	var tasks []*TaskState
	for _, task := range sm.tasks {
		if task.Status == status {
			tasks = append(tasks, task)
		}
	}
	return tasks
}

// GetPendingTasks returns all tasks that are not terminal (completed/failed/cancelled)
func (sm *StateManager) GetPendingTasks() []*TaskState {
	sm.mu.RLock()
	defer sm.mu.RUnlock()

	var pending []*TaskState
	for _, task := range sm.tasks {
		if task.Status != "completed" && task.Status != "failed" && task.Status != "cancelled" {
			pending = append(pending, task)
		}
	}
	return pending
}

// ClearExpiredApprovals removes expired approval gates from state (call periodically)
func (sm *StateManager) ClearExpiredApprovals() []*ApprovalGate {
	sm.mu.Lock()
	defer sm.mu.Unlock()

	now := time.Now()
	var cleared []*ApprovalGate

	for _, approval := range sm.approvals {
		if approval.Status == "pending" && now.After(approval.ExpiresAt) {
			cleared = append(cleared, approval)
			// Don't delete, just keep track - events will record the timeout
		}
	}

	return cleared
}
