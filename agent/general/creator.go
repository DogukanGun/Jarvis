package main

import (
	"context"
	"fmt"
	"jarvis/agent/general/db"
	jarvisTools2 "jarvis/agent/tools"
	"time"

	"github.com/tmc/langchaingo/agents"
	"github.com/tmc/langchaingo/llms/openai"
	"github.com/tmc/langchaingo/tools"
	"github.com/tmc/langchaingo/tools/wikipedia"
)

// JarvisAgent represents a Jarvis AI agent instance
type JarvisAgent struct {
	executor       *agents.Executor
	userID         string
	knowledgeGraph *db.KnowledgeGraph
}

// AgentConfig holds configuration for creating an agent
type AgentConfig struct {
	UserID      string
	OpenAIModel string
	OpenAIKey   string
	Neo4jURI    string
	Neo4jUser   string
	Neo4jPass   string
}

// NewJarvisAgent creates a new Jarvis agent instance
func NewJarvisAgent(config AgentConfig) (*JarvisAgent, error) {
	// Initialize OpenAI LLM
	model := config.OpenAIModel
	if model == "" {
		model = "gpt-4o-mini"
	}

	var llm *openai.LLM
	var err error

	if config.OpenAIKey != "" {
		llm, err = openai.New(
			openai.WithModel(model),
			openai.WithToken(config.OpenAIKey),
		)
	} else {
		llm, err = openai.New(openai.WithModel(model))
	}

	if err != nil {
		return nil, fmt.Errorf("failed to initialize OpenAI: %v", err)
	}

	// Initialize Wikipedia tool with proper user agent
	wikipediaTool := wikipedia.New("Jarvis-AI-Agent/1.0 (https://github.com/user/jarvis)")

	// Get web tools (includes wrapped scraper)
	webTools, err := jarvisTools2.GetWebTools()
	if err != nil {
		return nil, fmt.Errorf("failed to create web tools: %v", err)
	}

	var allTools []tools.Tool

	// Add custom tools
	allTools = append(allTools, jarvisTools2.GetFileTools()...)
	allTools = append(allTools, jarvisTools2.GetExecutionTools()...)
	allTools = append(allTools, jarvisTools2.GetEnvironmentTools()...)

	// Add web tools
	allTools = append(allTools, webTools...)

	// Add external langchain tools
	allTools = append(allTools, wikipediaTool)

	// Initialize knowledge graph if Neo4j config is provided
	var kg *db.KnowledgeGraph
	if config.Neo4jURI != "" {
		kg, err = db.NewKnowledgeGraph(config.Neo4jURI, config.Neo4jUser, config.Neo4jPass, config.UserID)
		if err != nil {
			return nil, fmt.Errorf("failed to initialize knowledge graph: %v", err)
		}
	}

	// Create OpenAI Functions agent
	agent := agents.NewOpenAIFunctionsAgent(llm, allTools)
	executor := agents.NewExecutor(agent)

	return &JarvisAgent{
		executor:       executor,
		userID:         config.UserID,
		knowledgeGraph: kg,
	}, nil
}

// ProcessMessage processes a message and returns the agent's response
func (ja *JarvisAgent) ProcessMessage(ctx context.Context, message string) (string, error) {
	if message == "" {
		return "", fmt.Errorf("message cannot be empty")
	}

	var enhancedInput string = message

	// Enhance input with knowledge graph context if available
	if ja.knowledgeGraph != nil {
		// Get relevant context from knowledge graph
		context, err := ja.knowledgeGraph.GetUserContext(message, 5)
		if err == nil && context != "" {
			enhancedInput = fmt.Sprintf("%s\n\n%s", context, message)
		}

		// Get user preferences
		prefs, err := ja.knowledgeGraph.GetUserPreferences()
		if err == nil && len(prefs) > 0 {
			prefsStr := "User preferences:\n"
			for key, value := range prefs {
				prefsStr += fmt.Sprintf("- %s: %s\n", key, value)
			}
			enhancedInput = fmt.Sprintf("%s\n%s\nUser message: %s", prefsStr, context, message)
		}

		// Store the user message as memory
		memory := db.Memory{
			ID:        fmt.Sprintf("msg_%d", time.Now().Unix()),
			UserID:    ja.userID,
			Content:   message,
			Type:      "user_message",
			Timestamp: time.Now(),
			Context:   "conversation",
		}
		ja.knowledgeGraph.AddMemory(memory)
	}

	// Process message with agent
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

	// Store the agent response as memory
	if ja.knowledgeGraph != nil {
		agentMemory := db.Memory{
			ID:        fmt.Sprintf("resp_%d", time.Now().Unix()),
			UserID:    ja.userID,
			Content:   response,
			Type:      "agent_response",
			Timestamp: time.Now(),
			Context:   "conversation",
		}
		ja.knowledgeGraph.AddMemory(agentMemory)
	}

	return response, nil
}

// GetUserID returns the user ID associated with this agent
func (ja *JarvisAgent) GetUserID() string {
	return ja.userID
}

// GetAvailableTools returns a list of available tool names
func (ja *JarvisAgent) GetAvailableTools() []string {
	tools := []string{
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
	}
	return tools
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
	}
}
