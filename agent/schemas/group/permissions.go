package group

import "fmt"

// Permission defines what actions a role can perform
type Permission string

const (
	// Chat permissions
	PermissionChatMessage Permission = "chat:message"

	// Proposal permissions
	PermissionProposalCreate   Permission = "proposal:create"
	PermissionProposalRead     Permission = "proposal:read"
	PermissionProposalUpdate   Permission = "proposal:update"
	PermissionProposalDelete   Permission = "proposal:delete"

	// Approval permissions
	PermissionApprovalRequest  Permission = "approval:request"
	PermissionApprovalGrant    Permission = "approval:grant"
	PermissionApprovalDeny     Permission = "approval:deny"

	// Task permissions
	PermissionTaskCreate       Permission = "task:create"
	PermissionTaskRead         Permission = "task:read"
	PermissionTaskCancel       Permission = "task:cancel"

	// Command permissions
	PermissionCommandRun       Permission = "command:run"
	PermissionCommandCancel    Permission = "command:cancel"

	// Thread permissions
	PermissionThreadCreate     Permission = "thread:create"
	PermissionThreadArchive    Permission = "thread:archive"

	// Admin permissions
	PermissionAdminAll         Permission = "admin:all"

	// Attachment permissions
	PermissionAttachmentCreate Permission = "attachment:create"
	PermissionAttachmentRead   Permission = "attachment:read"
	PermissionAttachmentDelete Permission = "attachment:delete"

	// Memory permissions
	PermissionMemoryPromote    Permission = "memory:promote"
)

// RolePermissions maps roles to their allowed permissions
var RolePermissions = map[Role][]Permission{
	RoleOwner: {
		PermissionChatMessage,
		PermissionProposalRead,
		PermissionApprovalGrant,
		PermissionApprovalDeny,
		PermissionAdminAll,
		PermissionAttachmentCreate,
		PermissionAttachmentRead,
		PermissionAttachmentDelete,
		PermissionMemoryPromote,
	},
	RoleAdmin: {
		PermissionChatMessage,
		PermissionProposalCreate,
		PermissionProposalRead,
		PermissionProposalUpdate,
		PermissionApprovalRequest,
		PermissionTaskCreate,
		PermissionTaskRead,
		PermissionTaskCancel,
		PermissionCommandRun,
		PermissionCommandCancel,
		PermissionThreadCreate,
		PermissionAttachmentCreate,
		PermissionAttachmentRead,
		PermissionAttachmentDelete,
	},
	RoleMember: {
		PermissionChatMessage,
		PermissionProposalRead,
		PermissionTaskRead,
		PermissionAttachmentRead,
	},
}

// CanPerform checks if a role can perform a permission
func CanPerform(role Role, permission Permission) bool {
	permissions, ok := RolePermissions[role]
	if !ok {
		return false
	}

	// Admin check for admin:all permission
	if role == RoleAdmin && permission == PermissionAdminAll {
		return true
	}

	for _, p := range permissions {
		if p == permission || p == PermissionAdminAll {
			return true
		}
	}
	return false
}

// ValidateEventPermission checks if a sender can publish a given event type
func ValidateEventPermission(sender Sender, eventType string) error {
	var requiredPerm Permission

	// Determine required permission based on event type
	switch eventType {
	case EventChatMessage:
		requiredPerm = PermissionChatMessage
	case EventProposalCreated, EventProposalUpdated:
		requiredPerm = PermissionProposalCreate
	case EventApprovalRequested:
		requiredPerm = PermissionApprovalRequest
	case EventApprovalGranted, EventApprovalDenied:
		requiredPerm = PermissionApprovalGrant
	case EventTaskCreated:
		requiredPerm = PermissionTaskCreate
	case EventTaskCancelled:
		requiredPerm = PermissionTaskCancel
	case EventCommandRun:
		requiredPerm = PermissionCommandRun
	case EventCommandCancel:
		requiredPerm = PermissionCommandCancel
	case EventThreadCreated:
		requiredPerm = PermissionThreadCreate
	case EventThreadArchived:
		requiredPerm = PermissionThreadArchive
	case EventAttachmentCreated:
		requiredPerm = PermissionAttachmentCreate
	case EventAttachmentDeleted:
		requiredPerm = PermissionAttachmentDelete
	case EventMemoryPromosal:
		requiredPerm = PermissionMemoryPromote
	default:
		// System events (results, errors, audit logs) can be sent by anyone
		return nil
	}

	if !CanPerform(sender.Role, requiredPerm) {
		return fmt.Errorf("role %s cannot perform %s (required: %s)", sender.Role, eventType, requiredPerm)
	}
	return nil
}

// ValidateEnvelope validates an envelope for correctness
func ValidateEnvelope(e *Envelope) error {
	if e.GroupID == "" {
		return fmt.Errorf("group_id is required")
	}
	if e.MessageID == "" {
		return fmt.Errorf("message_id is required")
	}
	if e.ThreadID == "" {
		return fmt.Errorf("thread_id is required")
	}
	if e.Sender.ID == "" {
		return fmt.Errorf("sender.id is required")
	}
	if e.Type == "" {
		return fmt.Errorf("type is required")
	}
	if e.Payload == nil {
		return fmt.Errorf("payload is required")
	}

	// Validate permissions
	if err := ValidateEventPermission(e.Sender, e.Type); err != nil {
		return err
	}

	return nil
}
