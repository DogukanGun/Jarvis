package group

import (
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestCanPerform(t *testing.T) {
	tests := []struct {
		name       string
		role       Role
		permission Permission
		expected   bool
	}{
		{
			name:       "owner can chat",
			role:       RoleOwner,
			permission: PermissionChatMessage,
			expected:   true,
		},
		{
			name:       "owner can grant approvals",
			role:       RoleOwner,
			permission: PermissionApprovalGrant,
			expected:   true,
		},
		{
			name:       "admin can create proposals",
			role:       RoleAdmin,
			permission: PermissionProposalCreate,
			expected:   true,
		},
		{
			name:       "member cannot create proposals",
			role:       RoleMember,
			permission: PermissionProposalCreate,
			expected:   false,
		},
		{
			name:       "member can chat",
			role:       RoleMember,
			permission: PermissionChatMessage,
			expected:   true,
		},
		{
			name:       "member cannot run commands",
			role:       RoleMember,
			permission: PermissionCommandRun,
			expected:   false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			result := CanPerform(tt.role, tt.permission)
			assert.Equal(t, tt.expected, result)
		})
	}
}

func TestValidateEventPermission(t *testing.T) {
	tests := []struct {
		name    string
		sender  Sender
		event   string
		wantErr bool
	}{
		{
			name:    "owner can send chat messages",
			sender:  Sender{ID: "user1", Role: RoleOwner},
			event:   EventChatMessage,
			wantErr: false,
		},
		{
			name:    "admin can create proposals",
			sender:  Sender{ID: "admin1", Role: RoleAdmin},
			event:   EventProposalCreated,
			wantErr: false,
		},
		{
			name:    "member cannot create proposals",
			sender:  Sender{ID: "agent1", Role: RoleMember},
			event:   EventProposalCreated,
			wantErr: true,
		},
		{
			name:    "only owner can grant approvals",
			sender:  Sender{ID: "admin1", Role: RoleAdmin},
			event:   EventApprovalGranted,
			wantErr: true,
		},
		{
			name:    "system events allowed",
			sender:  Sender{ID: "agent1", Role: RoleMember},
			event:   EventResultGenerated,
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := ValidateEventPermission(tt.sender, tt.event)
			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}

func TestValidateEnvelope(t *testing.T) {
	tests := []struct {
		name    string
		env     *Envelope
		wantErr bool
	}{
		{
			name: "valid envelope",
			env: &Envelope{
				GroupID:   "group1",
				MessageID: "msg1",
				ThreadID:  "thread1",
				Sender:    Sender{ID: "user1", Role: RoleOwner},
				Type:      EventChatMessage,
				Payload:   map[string]interface{}{"text": "hello"},
			},
			wantErr: false,
		},
		{
			name: "missing group_id",
			env: &Envelope{
				MessageID: "msg1",
				ThreadID:  "thread1",
				Sender:    Sender{ID: "user1", Role: RoleOwner},
				Type:      EventChatMessage,
				Payload:   map[string]interface{}{"text": "hello"},
			},
			wantErr: true,
		},
		{
			name: "missing message_id",
			env: &Envelope{
				GroupID:  "group1",
				ThreadID: "thread1",
				Sender:   Sender{ID: "user1", Role: RoleOwner},
				Type:     EventChatMessage,
				Payload:  map[string]interface{}{"text": "hello"},
			},
			wantErr: true,
		},
		{
			name: "missing sender.id",
			env: &Envelope{
				GroupID:   "group1",
				MessageID: "msg1",
				ThreadID:  "thread1",
				Sender:    Sender{Role: RoleOwner},
				Type:      EventChatMessage,
				Payload:   map[string]interface{}{"text": "hello"},
			},
			wantErr: true,
		},
		{
			name: "invalid permission",
			env: &Envelope{
				GroupID:   "group1",
				MessageID: "msg1",
				ThreadID:  "thread1",
				Sender:    Sender{ID: "agent1", Role: RoleMember},
				Type:      EventCommandRun,
				Payload:   map[string]interface{}{},
			},
			wantErr: true,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := ValidateEnvelope(tt.env)
			if tt.wantErr {
				assert.Error(t, err)
			} else {
				assert.NoError(t, err)
			}
		})
	}
}
