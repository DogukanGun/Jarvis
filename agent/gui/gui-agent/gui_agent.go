package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"time"

	"github.com/tmc/langchaingo/llms"
	"github.com/tmc/langchaingo/llms/ollama"
	"github.com/tmc/langchaingo/tools"
	jarvisTools "jarvis/agent/tools"
)

// GUIAgent represents a GUI-specialized AI agent
type GUIAgent struct {
	llm   llms.Model
	tools map[string]tools.Tool
}

// GUIAgentConfig holds configuration for creating a GUI agent
type GUIAgentConfig struct {
	OllamaHost   string
	OllamaModel  string
	GUIDaemonURL string
}

// ToolCall represents a tool invocation from the LLM
type ToolCall struct {
	Tool  string         `json:"tool"`
	Input map[string]any `json:"tool_input"`
}

// NewGUIAgent creates a new GUI-specialized agent instance
func NewGUIAgent(config GUIAgentConfig) (*GUIAgent, error) {
	// Initialize Ollama LLM
	ollamaHost := config.OllamaHost
	if ollamaHost == "" {
		ollamaHost = "http://127.0.0.1:11434"
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

	// Collect all tools
	var allTools []tools.Tool
	allTools = append(allTools, jarvisTools.GetGUITools()...)
	allTools = append(allTools, jarvisTools.GetVisualAnalyserTools()...)

	// Create tool map for easy lookup
	toolMap := make(map[string]tools.Tool)
	for _, tool := range allTools {
		toolMap[tool.Name()] = tool
	}

	return &GUIAgent{
		llm:   llm,
		tools: toolMap,
	}, nil
}

// ProcessMessage processes a GUI automation request
func (ga *GUIAgent) ProcessMessage(ctx context.Context, message string) (string, error) {
	if message == "" {
		return "", fmt.Errorf("message cannot be empty")
	}

	var msgs []llms.MessageContent

	// System message defines available tools
	msgs = append(msgs, llms.TextParts(llms.ChatMessageTypeSystem, ga.systemMessage()))
	msgs = append(msgs, llms.TextParts(llms.ChatMessageTypeHuman, message))

	// Try up to 5 iterations to complete the task
	for i := 0; i < 10; i++ {
		log.Printf("GUI Agent iteration %d", i+1)

		// Generate response
		resp, err := ga.llm.GenerateContent(ctx, msgs)
		if err != nil {
			return "", fmt.Errorf("failed to generate content: %v", err)
		}

		if len(resp.Choices) == 0 {
			return "", fmt.Errorf("no response from LLM")
		}

		choice := resp.Choices[0]
		content := choice.Content
		msgs = append(msgs, llms.TextParts(llms.ChatMessageTypeAI, content))

		log.Printf("LLM response: %s", content)

		// Try to parse as tool call
		if call := unmarshalToolCall(content); call != nil {
			log.Printf("Tool call: %s", call.Tool)

			// Validate tool exists
			tool, exists := ga.tools[call.Tool]
			if !exists {
				log.Printf("Invalid tool: %s", call.Tool)
				msgs = append(msgs, llms.TextParts(llms.ChatMessageTypeHuman,
					fmt.Sprintf("Tool '%s' does not exist. Available tools: %v", call.Tool, ga.getToolNames())))
				continue
			}

			// Execute tool
			inputJSON, _ := json.Marshal(call.Input)
			result, err := tool.Call(ctx, string(inputJSON))
			if err != nil {
				log.Printf("Tool error: %v", err)
				msgs = append(msgs, llms.TextParts(llms.ChatMessageTypeHuman,
					fmt.Sprintf("Tool execution failed: %v. Please try again.", err)))
				continue
			}

			log.Printf("Tool result: %s", result)

			// Check if we got a final answer
			if isFinalAnswer(result) {
				return result, nil
			}

			// Add tool result to conversation
			msgs = append(msgs, llms.TextParts(llms.ChatMessageTypeHuman,
				fmt.Sprintf("Tool '%s' returned: %s", call.Tool, result)))
		} else {
			// Not a tool call - might be a final answer or error
			log.Printf("Not a tool call, treating as final response")
			return content, nil
		}
	}

	return "Unable to complete the request after maximum iterations", nil
}

// unmarshalToolCall parses JSON tool call from LLM response
func unmarshalToolCall(content string) *ToolCall {
	var call ToolCall
	if err := json.Unmarshal([]byte(content), &call); err == nil && call.Tool != "" {
		return &call
	}
	return nil
}

// isFinalAnswer checks if the result is a completion indicator
func isFinalAnswer(result string) bool {
	// You can customize this logic
	return false
}

// getToolNames returns list of available tool names
func (ga *GUIAgent) getToolNames() []string {
	names := make([]string, 0, len(ga.tools))
	for name := range ga.tools {
		names = append(names, name)
	}
	return names
}

// systemMessage returns the system prompt for the GUI agent
func (ga *GUIAgent) systemMessage() string {
	toolDescriptions := ""
	for name, tool := range ga.tools {
		toolDescriptions += fmt.Sprintf("- %s: %s\n", name, tool.Description())
	}

	return fmt.Sprintf(`You are a GUI automation specialist AI assistant. Your job is to control the computer's graphical user interface using available tools.

Available tools:
%s

When the user asks you to do something, you should:
1. Think about which tool(s) you need to use
2. Respond with a JSON object in this EXACT format:
{
	"tool": "tool_name",
	"tool_input": {
		"param1": "value1",
		"param2": "value2"
	}
}

Important guidelines:
- For clicking UI elements: First use find_element or find_coordinates to locate it, then use click_mouse with those coordinates
- For typing: Use type_text with the text you want to type
- For screenshots: Use take_screenshot to capture the screen
- For information requests: Use find_element, describe_screen, or detect_text and then return the result directly to the user
- Always respond with valid JSON when using a tool
- Only use one tool at a time
- After a tool executes, you'll see its result and can decide what to do next

IMPORTANT: When to return a final answer vs continue with tools:
- If the user asked to DO something (click, type, open, etc.), execute the action tools and return confirmation
- If the user asked for INFORMATION (find, describe, what's on screen, etc.), use the visual analysis tools and return the result
- Don't use tools unnecessarily - once you have the information or completed the action, respond with the result

Example user request: "Click the submit button"
Your response:
{
	"tool": "find_element",
	"tool_input": {
		"query": "submit button"
	}
}

Then after getting coordinates, you would:
{
	"tool": "click_mouse",
	"tool_input": {
		"x": 500,
		"y": 300
	}
}

Example user request: "What's on the screen?"
Your response:
{
	"tool": "describe_screen",
	"tool_input": {}
}

Then after getting the description, you would respond with plain text (not JSON):
The screen shows [description from tool result]`, toolDescriptions)
}

// GetAvailableTools returns a list of available tool names
func (ga *GUIAgent) GetAvailableTools() []string {
	return ga.getToolNames()
}

// GetCapabilities returns a human-readable description of agent capabilities
func (ga *GUIAgent) GetCapabilities() map[string][]string {
	return map[string][]string{
		"Mouse Control": {
			"Move cursor to any position",
			"Click (left, right, middle button)",
			"Drag and drop operations",
			"Scroll in any direction",
			"Double-click and multi-click",
		},
		"Keyboard Control": {
			"Type text strings",
			"Press key combinations (Ctrl+C, etc.)",
			"Hold and release keys",
			"Paste text via clipboard",
		},
		"Screen Operations": {
			"Capture screenshots (base64 PNG)",
			"Get cursor position",
			"Wait/delay operations",
		},
		"Application Control": {
			"Launch applications",
			"Activate windows",
			"File read/write operations",
		},
		"Visual Analysis": {
			"Find UI elements by description",
			"Detect element coordinates for clicking",
			"Extract text from screenshots (OCR)",
			"Describe screen layout and content",
			"Identify applications and windows",
		},
	}
}
