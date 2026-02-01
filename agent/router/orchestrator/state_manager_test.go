package orchestrator

import (
	"testing"
	"time"

	"github.com/stretchr/testify/assert"
)

func TestStateManager_CreateThread(t *testing.T) {
	sm := NewStateManager(60)

	thread, err := sm.CreateThread("group1", "thread1", "Test Thread")
	assert.NoError(t, err)
	assert.Equal(t, "thread1", thread.ThreadID)
	assert.Equal(t, "Test Thread", thread.Title)
	assert.Equal(t, "active", thread.Status)

	// Try to create duplicate
	_, err = sm.CreateThread("group1", "thread1", "Duplicate")
	assert.Error(t, err)
}

func TestStateManager_CreateApprovalGate(t *testing.T) {
	sm := NewStateManager(60)

	approval, err := sm.CreateApprovalGate("approval1", "proposal1", "task1", "user1")
	assert.NoError(t, err)
	assert.Equal(t, "approval1", approval.ApprovalID)
	assert.Equal(t, "pending", approval.Status)

	// Verify TTL
	assert.True(t, time.Now().Before(approval.ExpiresAt))
}

func TestStateManager_GrantApproval(t *testing.T) {
	sm := NewStateManager(60)

	_, err := sm.CreateApprovalGate("approval1", "proposal1", "task1", "user1")
	assert.NoError(t, err)

	err = sm.GrantApproval("approval1")
	assert.NoError(t, err)

	approval, err := sm.GetApprovalGate("approval1")
	assert.NoError(t, err)
	assert.Equal(t, "granted", approval.Status)
}

func TestStateManager_DenyApproval(t *testing.T) {
	sm := NewStateManager(60)

	_, err := sm.CreateApprovalGate("approval1", "proposal1", "task1", "user1")
	assert.NoError(t, err)

	err = sm.DenyApproval("approval1")
	assert.NoError(t, err)

	approval, err := sm.GetApprovalGate("approval1")
	assert.NoError(t, err)
	assert.Equal(t, "denied", approval.Status)
}

func TestStateManager_CreateTask(t *testing.T) {
	sm := NewStateManager(60)

	task, err := sm.CreateTask("task1", "proposal1", "approval1", "agent1", "execute")
	assert.NoError(t, err)
	assert.Equal(t, "task1", task.TaskID)
	assert.Equal(t, "created", task.Status)
	assert.Equal(t, 0, task.Progress)

	// Try to create duplicate
	_, err = sm.CreateTask("task1", "proposal2", "approval2", "agent2", "execute")
	assert.Error(t, err)
}

func TestStateManager_UpdateTaskStatus(t *testing.T) {
	sm := NewStateManager(60)

	_, err := sm.CreateTask("task1", "proposal1", "approval1", "agent1", "execute")
	assert.NoError(t, err)

	err = sm.UpdateTaskStatus("task1", "started", 0, "")
	assert.NoError(t, err)

	task, err := sm.GetTask("task1")
	assert.NoError(t, err)
	assert.Equal(t, "started", task.Status)

	err = sm.UpdateTaskStatus("task1", "progress", 50, "")
	assert.NoError(t, err)

	task, err = sm.GetTask("task1")
	assert.NoError(t, err)
	assert.Equal(t, "progress", task.Status)
	assert.Equal(t, 50, task.Progress)
}

func TestStateManager_CompleteTask(t *testing.T) {
	sm := NewStateManager(60)

	_, err := sm.CreateTask("task1", "proposal1", "approval1", "agent1", "execute")
	assert.NoError(t, err)

	result := map[string]interface{}{"output": "success"}
	err = sm.CompleteTask("task1", result)
	assert.NoError(t, err)

	task, err := sm.GetTask("task1")
	assert.NoError(t, err)
	assert.Equal(t, "completed", task.Status)
	assert.Equal(t, 100, task.Progress)
}

func TestStateManager_FailTask(t *testing.T) {
	sm := NewStateManager(60)

	_, err := sm.CreateTask("task1", "proposal1", "approval1", "agent1", "execute")
	assert.NoError(t, err)

	err = sm.FailTask("task1", "Connection timeout")
	assert.NoError(t, err)

	task, err := sm.GetTask("task1")
	assert.NoError(t, err)
	assert.Equal(t, "failed", task.Status)
	assert.Equal(t, "Connection timeout", task.Error)
}

func TestStateManager_GetPendingApprovals(t *testing.T) {
	sm := NewStateManager(60)

	_, err := sm.CreateApprovalGate("approval1", "proposal1", "task1", "user1")
	assert.NoError(t, err)

	_, err = sm.CreateApprovalGate("approval2", "proposal2", "task2", "user1")
	assert.NoError(t, err)

	pending := sm.GetPendingApprovals()
	assert.Equal(t, 2, len(pending))

	// Grant one approval
	sm.GrantApproval("approval1")

	pending = sm.GetPendingApprovals()
	assert.Equal(t, 1, len(pending))
	assert.Equal(t, "approval2", pending[0].ApprovalID)
}

func TestStateManager_GetTasksByStatus(t *testing.T) {
	sm := NewStateManager(60)

	_, err := sm.CreateTask("task1", "proposal1", "approval1", "agent1", "execute")
	assert.NoError(t, err)

	_, err = sm.CreateTask("task2", "proposal2", "approval2", "agent1", "execute")
	assert.NoError(t, err)

	sm.CompleteTask("task1", "result")

	completed := sm.GetTasksByStatus("completed")
	assert.Equal(t, 1, len(completed))
	assert.Equal(t, "task1", completed[0].TaskID)

	created := sm.GetTasksByStatus("created")
	assert.Equal(t, 1, len(created))
	assert.Equal(t, "task2", created[0].TaskID)
}

func TestStateManager_AddMessageToThread(t *testing.T) {
	sm := NewStateManager(60)

	sm.CreateThread("group1", "thread1", "Test")

	err := sm.AddMessageToThread("thread1", "msg1")
	assert.NoError(t, err)

	err = sm.AddMessageToThread("thread1", "msg2")
	assert.NoError(t, err)

	thread, _ := sm.GetThread("thread1")
	assert.Equal(t, 2, len(thread.Messages))
}

func TestStateManager_ExpiredApprovals(t *testing.T) {
	sm := NewStateManager(1) // 1 minute TTL

	_, err := sm.CreateApprovalGate("approval1", "proposal1", "task1", "user1")
	assert.NoError(t, err)

	// Should not be expired yet
	expired := sm.GetExpiredApprovals()
	assert.Equal(t, 0, len(expired))

	// Manually set expiration to past
	approval, _ := sm.GetApprovalGate("approval1")
	approval.ExpiresAt = time.Now().Add(-1 * time.Second)

	// Should now be expired
	expired = sm.GetExpiredApprovals()
	assert.Equal(t, 1, len(expired))
}
