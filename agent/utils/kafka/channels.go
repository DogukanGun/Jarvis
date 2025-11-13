package kafka

const (
	// Topic names for different agents
	CoderAgentTopic   = "coder-agent-requests"
	GeneralAgentTopic = "general-agent-requests"
	
	// Consumer group IDs
	CoderAgentGroup   = "coder-agent-group"
	GeneralAgentGroup = "general-agent-group"
)

// AgentMessage represents a message sent between agents
type AgentMessage struct {
	ID        string `json:"id"`
	UserID    string `json:"user_id"`
	Demand    string `json:"demand"`
	Timestamp int64  `json:"timestamp"`
}
