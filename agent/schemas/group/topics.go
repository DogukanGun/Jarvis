package group

import "fmt"

// Topic name generators for group communication

// EventsTopic returns the topic name for events in a group
func EventsTopic(groupID string) string {
	return fmt.Sprintf("group.%s.events", groupID)
}

// CommandsTopic returns the topic name for commands in a group
func CommandsTopic(groupID string) string {
	return fmt.Sprintf("group.%s.commands", groupID)
}

// ThreadTopic returns the topic name for a specific thread
func ThreadTopic(groupID, threadID string) string {
	return fmt.Sprintf("group.%s.thread.%s", groupID, threadID)
}

// AgentTopic returns the topic name for agent-specific commands
func AgentTopic(groupID, agentID string) string {
	return fmt.Sprintf("group.%s.agent.%s", groupID, agentID)
}

// ApprovalTopic returns the topic name for approval-related events
func ApprovalTopic(groupID string) string {
	return fmt.Sprintf("group.%s.approvals", groupID)
}

// ResultsTopic returns the topic name for results
func ResultsTopic(groupID string) string {
	return fmt.Sprintf("group.%s.results", groupID)
}

// AuditTopic returns the topic name for audit logs
func AuditTopic(groupID string) string {
	return fmt.Sprintf("group.%s.audit", groupID)
}

// TopicConfig holds topic configuration
type TopicConfig struct {
	Name              string
	Partitions        int32
	ReplicationFactor int16
	RetentionMs       int64 // -1 for infinite
	MinInSyncReplicas int16
}

// DefaultTopicConfigs returns the default configurations for group topics
func DefaultTopicConfigs(groupID string) []TopicConfig {
	return []TopicConfig{
		{
			Name:              EventsTopic(groupID),
			Partitions:        3,
			ReplicationFactor: 1,
			RetentionMs:       7 * 24 * 60 * 60 * 1000, // 7 days
			MinInSyncReplicas: 1,
		},
		{
			Name:              CommandsTopic(groupID),
			Partitions:        2,
			ReplicationFactor: 1,
			RetentionMs:       24 * 60 * 60 * 1000, // 1 day
			MinInSyncReplicas: 1,
		},
		{
			Name:              ApprovalTopic(groupID),
			Partitions:        1,
			ReplicationFactor: 1,
			RetentionMs:       30 * 24 * 60 * 60 * 1000, // 30 days
			MinInSyncReplicas: 1,
		},
		{
			Name:              ResultsTopic(groupID),
			Partitions:        3,
			ReplicationFactor: 1,
			RetentionMs:       30 * 24 * 60 * 60 * 1000, // 30 days
			MinInSyncReplicas: 1,
		},
		{
			Name:              AuditTopic(groupID),
			Partitions:        1,
			ReplicationFactor: 1,
			RetentionMs:       90 * 24 * 60 * 60 * 1000, // 90 days
			MinInSyncReplicas: 1,
		},
	}
}
