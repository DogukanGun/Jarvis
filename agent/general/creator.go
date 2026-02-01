package main

import (
	"context"
	"encoding/json"
	"fmt"
	"jarvis/agent/general/memory"
	jarvisTools "jarvis/agent/tools"
	"jarvis/agent/utils/kafka"
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/tmc/langchaingo/agents"
	"github.com/tmc/langchaingo/llms"
	"github.com/tmc/langchaingo/llms/ollama"
	"github.com/tmc/langchaingo/tools"
	"github.com/tmc/langchaingo/tools/wikipedia"
)

// JarvisAgent represents a Jarvis AI agent instance (orchestrator)
type JarvisAgent struct {
	executor       *agents.Executor
	llm            llms.Model
	userID         string
	episodicMemory *memory.EpisodicMemoryClient
	allTools       []tools.Tool
}

// AgentConfig holds configuration for creating an agent
type AgentConfig struct {
	UserID             string
	OllamaHost         string
	OllamaModel        string
	EpisodicMemoryURL  string
	GUIAgentURL        string
	VisualAnalyserURL  string
}

// DelegationDecision represents the LLM's decision on how to handle a request
type DelegationDecision struct {
	Action      string `json:"action"`       // "answer", "delegate_gui", "delegate_visual"
	Reasoning   string `json:"reasoning"`    // Why this decision
	Demand      string `json:"demand"`       // The task to delegate (if applicable)
}

// NewJarvisAgent creates a new Jarvis agent instance (orchestrator)
func NewJarvisAgent(config AgentConfig) (*JarvisAgent, error) {
	// Initialize Ollama LLM
	ollamaHost := config.OllamaHost
	if ollamaHost == "" {
		ollamaHost = "http://localhost:11434"
	}

	ollamaModel := config.OllamaModel
	if ollamaModel == "" {
		ollamaModel = "llama3.2"
	}

	llm, err := ollama.New(
		ollama.WithServerURL(ollamaHost),
		ollama.WithModel(ollamaModel),
		ollama.WithHTTPClient(&http.Client{
			Timeout: 3 * time.Minute,
		}),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to initialize Ollama: %v", err)
	}

	// Initialize Wikipedia tool with proper user agent
	wikipediaTool := wikipedia.New("Jarvis-AI-Agent/1.0 (https://github.com/user/jarvis)")

	// Get web tools (includes wrapped scraper)
	webTools, err := jarvisTools.GetWebTools()
	if err != nil {
		return nil, fmt.Errorf("failed to create web tools: %v", err)
	}

	var allTools []tools.Tool

	// Add custom tools
	allTools = append(allTools, jarvisTools.GetFileTools()...)
	allTools = append(allTools, jarvisTools.GetExecutionTools()...)
	allTools = append(allTools, jarvisTools.GetEnvironmentTools()...)

	// Add web tools
	allTools = append(allTools, webTools...)

	// Add external langchain tools
	allTools = append(allTools, wikipediaTool)

	// Initialize episodic memory client
	episodicMemoryURL := config.EpisodicMemoryURL
	if episodicMemoryURL == "" {
		episodicMemoryURL = os.Getenv("EPISODIC_MEMORY_URL")
	}
	if episodicMemoryURL == "" {
		episodicMemoryURL = "http://localhost:8085"
	}
	episodicMemory := memory.NewEpisodicMemoryClient(episodicMemoryURL)

	// Create agent executor using conversational agent for Ollama
	agent := agents.NewConversationalAgent(llm, allTools)
	executor := agents.NewExecutor(agent)

	return &JarvisAgent{
		executor:       executor,
		llm:            llm,
		userID:         config.UserID,
		episodicMemory: episodicMemory,
		allTools:       allTools,
	}, nil
}

// ProcessMessage processes a message and returns the agent's response
func (ja *JarvisAgent) ProcessMessage(ctx context.Context, message string) (string, error) {
	if message == "" {
		return "", fmt.Errorf("message cannot be empty")
	}

	log.Printf("Processing message for user %s: %s", ja.userID, message[:min(50, len(message))])

	// Step 1: Get context from Episodic Memory
	var memoryContext string
	memCtx, err := ja.episodicMemory.GetContext(ctx, ja.userID, message)
	if err != nil {
		log.Printf("Warning: failed to get memory context: %v", err)
	} else {
		memoryContext = ja.episodicMemory.FormatContextForLLM(memCtx)
	}

	// Step 2: Decide whether to answer directly or delegate
	decision, err := ja.decideAction(ctx, message, memoryContext)
	if err != nil {
		log.Printf("Warning: failed to decide action, defaulting to direct answer: %v", err)
		decision = &DelegationDecision{Action: "answer"}
	}

	log.Printf("Decision: %s - %s", decision.Action, decision.Reasoning)

	var response string

	// Step 3: Execute based on decision
	switch decision.Action {
	case "delegate_gui":
		response, err = ja.delegateToGUI(ctx, decision.Demand)
		if err != nil {
			log.Printf("GUI delegation failed, answering directly: %v", err)
			response, err = ja.answerDirectly(ctx, message, memoryContext)
		}

	case "delegate_visual":
		response, err = ja.delegateToVisualAnalyser(ctx, decision.Demand)
		if err != nil {
			log.Printf("Visual analyser delegation failed, answering directly: %v", err)
			response, err = ja.answerDirectly(ctx, message, memoryContext)
		}

	default: // "answer" or unknown
		response, err = ja.answerDirectly(ctx, message, memoryContext)
	}

	if err != nil {
		return "", err
	}

	// Step 4: Store interaction in Episodic Memory (async)
	go func() {
		storeCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()
		if err := ja.episodicMemory.StoreInteraction(storeCtx, ja.userID, message, response); err != nil {
			log.Printf("Warning: failed to store interaction: %v", err)
		}
	}()

	return response, nil
}

// decideAction uses LLM to decide whether to answer directly or delegate
func (ja *JarvisAgent) decideAction(ctx context.Context, message, memoryContext string) (*DelegationDecision, error) {
	prompt := fmt.Sprintf(`You are an AI orchestrator that decides how to handle user requests.

Available actions:
1. "answer" - Answer the question directly (for simple questions, personal queries, general knowledge, explanations)
2. "delegate_gui" - Delegate to GUI Agent (for mouse/keyboard control, taking screenshots, opening applications, desktop automation)
3. "delegate_visual" - Delegate to Visual Analyser (for image analysis, checking visual similarity, IP protection)

%s

User request: %s

Respond with a JSON object:
{
  "action": "answer" | "delegate_gui" | "delegate_visual",
  "reasoning": "brief explanation of why",
  "demand": "the specific task to delegate (only if delegating)"
}

Only respond with the JSON object, nothing else.`, memoryContext, message)

	resp, err := ja.llm.Call(ctx, prompt)
	if err != nil {
		return nil, fmt.Errorf("failed to get decision: %v", err)
	}

	// Parse JSON response
	var decision DelegationDecision

	// Try to extract JSON from response
	respStr := strings.TrimSpace(resp)

	// Find JSON in response
	startIdx := strings.Index(respStr, "{")
	endIdx := strings.LastIndex(respStr, "}")
	if startIdx != -1 && endIdx != -1 && endIdx > startIdx {
		respStr = respStr[startIdx : endIdx+1]
	}

	if err := json.Unmarshal([]byte(respStr), &decision); err != nil {
		log.Printf("Failed to parse decision JSON: %v, response: %s", err, resp)
		// Default to answering directly
		return &DelegationDecision{Action: "answer", Reasoning: "Failed to parse decision"}, nil
	}

	// Set demand to original message if not provided
	if decision.Demand == "" {
		decision.Demand = message
	}

	return &decision, nil
}

// answerDirectly uses the agent's tools to answer the question
func (ja *JarvisAgent) answerDirectly(ctx context.Context, message, memoryContext string) (string, error) {
	enhancedInput := message
	if memoryContext != "" {
		enhancedInput = fmt.Sprintf("%s\nUser message: %s", memoryContext, message)
	}

	result, err := ja.executor.Call(ctx, map[string]any{
		"input": enhancedInput,
	})
	if err != nil {
		return "", fmt.Errorf("agent processing error: %v", err)
	}

	// Extract response
	var response string
	if output, ok := result["output"]; ok {
		response = fmt.Sprintf("%v", output)
	} else {
		response = fmt.Sprintf("%v", result)
	}

	return response, nil
}

// delegateToGUI sends task to GUI Agent via Kafka
func (ja *JarvisAgent) delegateToGUI(ctx context.Context, demand string) (string, error) {
	log.Printf("Delegating to GUI Agent: %s", demand)

	message := kafka.AgentMessage{
		ID:        fmt.Sprintf("msg_%d", time.Now().UnixNano()),
		UserID:    ja.userID,
		Demand:    demand,
		Timestamp: time.Now().Unix(),
	}

	err := kafka.SendToGUIAgent(ctx, message)
	if err != nil {
		return "", fmt.Errorf("failed to send to GUI agent: %v", err)
	}

	return fmt.Sprintf("Task delegated to GUI Agent: %s (Message ID: %s)", demand, message.ID), nil
}

// delegateToVisualAnalyser sends task to Visual Analyser via Kafka
func (ja *JarvisAgent) delegateToVisualAnalyser(ctx context.Context, demand string) (string, error) {
	log.Printf("Delegating to Visual Analyser: %s", demand)

	message := kafka.AgentMessage{
		ID:        fmt.Sprintf("msg_%d", time.Now().UnixNano()),
		UserID:    ja.userID,
		Demand:    demand,
		Timestamp: time.Now().Unix(),
	}

	err := kafka.SendToVisualAnalyser(ctx, message)
	if err != nil {
		return "", fmt.Errorf("failed to send to visual analyser: %v", err)
	}

	return fmt.Sprintf("Task delegated to Visual Analyser: %s (Message ID: %s)", demand, message.ID), nil
}

// GetUserID returns the user ID associated with this agent
func (ja *JarvisAgent) GetUserID() string {
	return ja.userID
}

// GetAvailableTools returns a list of available tool names
func (ja *JarvisAgent) GetAvailableTools() []string {
	toolsList := []string{
		// File Operations
		"read_file", "write_file", "delete_file", "list_files",
		// Execution Tools
		"run_code", "execute_terminal", "evaluate_expression",
		// Environment Management
		"install_package", "check_version", "lint_code",
		// Communication Tools
		"commit_to_git", "create_pull_request", "comment_diff",
		// Web Tools
		"web_scraper", "Wikipedia",
		// Delegation
		"delegate_to_gui", "delegate_to_visual_analyser",
	}
	return toolsList
}

// GetCapabilities returns a human-readable description of agent capabilities
func (ja *JarvisAgent) GetCapabilities() map[string][]string {
	return map[string][]string{
		"File Operations": {
			"Read file contents",
			"Write content to files",
			"Delete files",
			"List directory contents",
		},
		"Code Execution": {
			"Execute code (Python, Go, JavaScript, Bash)",
			"Run terminal commands",
			"Evaluate mathematical expressions",
		},
		"Environment Management": {
			"Install packages (npm, pip, go get, etc.)",
			"Check tool versions",
			"Run code linters",
		},
		"Communication": {
			"Git commit operations",
			"Create GitHub/GitLab pull requests",
			"Comment on diffs/PRs",
		},
		"Web & Research": {
			"Scrape web content",
			"Search Wikipedia",
			"Retrieve online information",
		},
		"Delegation": {
			"Delegate GUI automation to GUI Agent",
			"Delegate image analysis to Visual Analyser",
		},
		"Memory": {
			"Remember past interactions",
			"Learn user preferences",
			"Provide personalized responses",
		},
	}
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
