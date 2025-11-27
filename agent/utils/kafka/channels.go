package kafka

const (
	// Topic names for different agents
	CoderAgentTopic          = "coder-agent-requests"
	GeneralAgentTopic        = "general-agent-requests"
	VisualAnalyserAgentTopic = "visual-analyser-requests"
	IPRegistrationTopic      = "ip-registration-requests"

	// Consumer group IDs
	CoderAgentGroup          = "coder-agent-group"
	GeneralAgentGroup        = "general-agent-group"
	VisualAnalyserAgentGroup = "visual-analyser-group"
	IPAgentGroup             = "ip-agent-group"
)

// AgentMessage represents a message sent between agents
type AgentMessage struct {
	ID        string `json:"id"`
	UserID    string `json:"user_id"`
	Demand    string `json:"demand"`
	Timestamp int64  `json:"timestamp"`
	ImageData string `json:"image_data,omitempty"` // Base64 encoded image for visual analyser
}

// IPRegistrationMessage represents a message for IP registration
type IPRegistrationMessage struct {
	ID                 string `json:"id"`
	UserID             string `json:"user_id"`
	AssetID            string `json:"asset_id"`
	OwnerAddress       string `json:"owner_address"` // Ethereum address
	Title              string `json:"title"`
	Description        string `json:"description"`
	ImageData          string `json:"image_data"` // Base64 encoded image
	CommercialUse      bool   `json:"commercial_use"`
	CommercialRevShare int    `json:"commercial_rev_share"` // percentage (0-100)
	MintingFee         string `json:"minting_fee"`          // in ETH
	Timestamp          int64  `json:"timestamp"`
}
