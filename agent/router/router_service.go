package main

import (
	"bufio"
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"github.com/tmc/langchaingo/llms"
	"github.com/tmc/langchaingo/llms/ollama"
	"io"
	"jarvis/agent/utils/kafka"
	"log"
	"net/http"
	"os"
	"slices"
	"strings"
	"time"
)

var flagVerbose = flag.Bool("v", false, "verbose mode")

type RouterService struct {
	llm llms.Model
}

func NewRouterService() (*RouterService, error) {
	flag.Parse()

	model := "llama3.2"
	if v := os.Getenv("OLLAMA_TEST_MODEL"); v != "" {
		model = v
	}

	// Set Ollama host from environment
	ollamaHost := os.Getenv("OLLAMA_HOST")
	if ollamaHost == "" {
		ollamaHost = "http://localhost:11434"
	}

	llm, err := ollama.New(
		ollama.WithServerURL(ollamaHost),
		ollama.WithModel(model),
		ollama.WithFormat("json"),
	)
	if err != nil {
		return nil, fmt.Errorf("failed to create ollama client: %v", err)
	}

	// Ensure model is pulled
	log.Printf("Ensuring model %s is available...", model)
	err = ensureModelAvailable(llm, model)
	if err != nil {
		log.Printf("Warning: could not ensure model availability: %v", err)
		// Don't fail service creation, model might be pulled later
	}

	return &RouterService{
		llm: llm,
	}, nil
}

// ensureModelAvailable checks if model exists and pulls it if needed
func ensureModelAvailable(llm llms.Model, modelName string) error {
	// First check if model is available by listing models
	if isModelAvailable(modelName) {
		log.Printf("Model %s is already available", modelName)
		return nil
	}

	log.Printf("Model %s not found, pulling it now...", modelName)

	// Pull the model using Ollama API
	err := pullModel(modelName)
	if err != nil {
		log.Printf("Failed to pull model %s: %v", modelName, err)
		return err
	}

	log.Printf("Successfully pulled model %s", modelName)
	return nil
}

// isModelAvailable checks if the model is already downloaded
func isModelAvailable(modelName string) bool {
	ollamaHost := os.Getenv("OLLAMA_HOST")
	if ollamaHost == "" {
		ollamaHost = "http://localhost:11434"
	}

	resp, err := http.Get(ollamaHost + "/api/tags")
	if err != nil {
		log.Printf("Failed to check available models: %v", err)
		return false
	}
	defer resp.Body.Close()

	var result struct {
		Models []struct {
			Name string `json:"name"`
		} `json:"models"`
	}

	if err := json.NewDecoder(resp.Body).Decode(&result); err != nil {
		log.Printf("Failed to decode models response: %v", err)
		return false
	}

	for _, model := range result.Models {
		if model.Name == modelName || model.Name == modelName+":latest" {
			return true
		}
	}

	return false
}

// pullModel downloads the specified model using Ollama API
func pullModel(modelName string) error {
	ollamaHost := os.Getenv("OLLAMA_HOST")
	if ollamaHost == "" {
		ollamaHost = "http://localhost:11434"
	}

	pullRequest := map[string]interface{}{
		"name": modelName,
	}

	requestBody, err := json.Marshal(pullRequest)
	if err != nil {
		return fmt.Errorf("failed to marshal pull request: %v", err)
	}

	// Create pull request with longer timeout for model download
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Minute)
	defer cancel()

	req, err := http.NewRequestWithContext(ctx, "POST", ollamaHost+"/api/pull", strings.NewReader(string(requestBody)))
	if err != nil {
		return fmt.Errorf("failed to create pull request: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send pull request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != 200 {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("pull request failed with status %d: %s", resp.StatusCode, string(body))
	}

	// Read the streaming response to track progress
	scanner := bufio.NewScanner(resp.Body)
	for scanner.Scan() {
		var pullProgress map[string]interface{}
		if err := json.Unmarshal(scanner.Bytes(), &pullProgress); err == nil {
			if status, ok := pullProgress["status"].(string); ok {
				log.Printf("Model pull progress: %s", status)

				// Check if pull is complete
				if status == "success" {
					return nil
				}
			}
		}
	}

	return scanner.Err()
}

func (rs *RouterService) ProcessMessage(ctx context.Context, userMessage string) (string, error) {
	var msgs []llms.MessageContent

	// system message defines the available tools.
	msgs = append(msgs, llms.TextParts(llms.ChatMessageTypeSystem, systemMessage()))
	msgs = append(msgs, llms.TextParts(llms.ChatMessageTypeHuman, userMessage))

	for retries := 3; retries > 0; retries = retries - 1 {
		resp, err := rs.llm.GenerateContent(ctx, msgs)
		if err != nil {
			return "", fmt.Errorf("failed to generate content: %v", err)
		}

		choice1 := resp.Choices[0]
		msgs = append(msgs, llms.TextParts(llms.ChatMessageTypeAI, choice1.Content))

		if c := unmarshalCall(choice1.Content); c != nil {
			log.Printf("Call: %v", c.Tool)
			if *flagVerbose {
				log.Printf("Call: %v (raw: %v)", c.Tool, choice1.Content)
			}
			msg, cont, result := rs.dispatchCall(c)
			if !cont {
				return result, nil
			}
			msgs = append(msgs, msg)
		} else {
			// Ollama doesn't always respond with a function call, let it try again.
			log.Printf("Not a call: %v", choice1.Content)
			msgs = append(msgs, llms.TextParts(llms.ChatMessageTypeHuman, "Sorry, I don't understand. Please try again."))
		}
	}

	return "Unable to process request after retries", nil
}

type Call struct {
	Tool  string         `json:"tool"`
	Input map[string]any `json:"tool_input"`
}

func unmarshalCall(input string) *Call {
	var c Call
	if err := json.Unmarshal([]byte(input), &c); err == nil && c.Tool != "" {
		return &c
	}
	return nil
}

func (rs *RouterService) dispatchCall(c *Call) (llms.MessageContent, bool, string) {
	// ollama doesn't always respond with a *valid* function call. As we're using prompt
	// engineering to inject the tools, it may hallucinate.
	if !validTool(c.Tool) {
		log.Printf("invalid function call: %#v, prompting model to try again", c)
		return llms.TextParts(llms.ChatMessageTypeHuman,
			"Tool does not exist, please try again."), true, ""
	}

	// we could make this more dynamic, by parsing the function schema.
	switch c.Tool {
	case "coder":
		demand, ok := c.Input["demand"].(string)
		if !ok {
			log.Printf("invalid input for coder: %v", c.Input)
			return llms.TextParts(llms.ChatMessageTypeHuman, "Invalid input format"), true, ""
		}

		log.Printf("Routing to coder agent: %s", demand)

		// Send message to coder agent via Kafka
		message := kafka.AgentMessage{
			ID:        fmt.Sprintf("msg_%d", time.Now().Unix()),
			UserID:    os.Getenv("USER_ID"),
			Demand:    demand,
			Timestamp: time.Now().Unix(),
		}

		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()

		err := kafka.SendToCoderAgent(ctx, message)
		if err != nil {
			log.Printf("Failed to send message to coder agent: %v", err)
			return llms.TextParts(llms.ChatMessageTypeHuman, "Failed to route to coder agent"), true, ""
		}

		response := fmt.Sprintf("Successfully routed coding request to coder agent (Message ID: %s)", message.ID)
		return llms.MessageContent{}, false, response

	case "general":
		demand, ok := c.Input["demand"].(string)
		if !ok {
			log.Printf("invalid input for general: %v", c.Input)
			return llms.TextParts(llms.ChatMessageTypeHuman, "Invalid input format"), true, ""
		}

		log.Printf("Routing to general agent: %s", demand)

		// Send message to general agent via Kafka
		message := kafka.AgentMessage{
			ID:        fmt.Sprintf("msg_%d", time.Now().Unix()),
			UserID:    os.Getenv("USER_ID"),
			Demand:    demand,
			Timestamp: time.Now().Unix(),
		}

		ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		defer cancel()

		err := kafka.SendToGeneralAgent(ctx, message)
		if err != nil {
			log.Printf("Failed to send message to general agent: %v", err)
			return llms.TextParts(llms.ChatMessageTypeHuman, "Failed to route to general agent"), true, ""
		}

		response := fmt.Sprintf("Successfully routed general request to general agent (Message ID: %s)", message.ID)
		return llms.MessageContent{}, false, response

	default:
		// we already checked above if we had a valid tool.
		panic("unreachable")
	}
}

func validTool(name string) bool {
	var valid []string
	for _, v := range functions {
		valid = append(valid, v.Name)
	}
	return slices.Contains(valid, name)
}

func systemMessage() string {
	bs, err := json.Marshal(functions)
	if err != nil {
		log.Fatal(err)
	}

	return fmt.Sprintf(`You have access to the following tools:

%s

To use a tool, respond with a JSON object with the following structure: 
{
	"tool": <name of the called tool>,
	"tool_input": <parameters for the tool matching the above JSON schema>
}
`, string(bs))
}

var functions = []llms.FunctionDefinition{
	{
		Name:        "coder",
		Description: "This is an agent which is responsible to handle coding part if user wants develop something",
		Parameters: json.RawMessage(`{
			"type": "object", 
			"properties": {
				"demand": {"type": "string", "description": "What user wants develop something"}
			}, 
			"required": ["demand"]
		}`),
	},
	{
		Name:        "general",
		Description: "This is agent which is responsible to answer user's question like general thing",
		Parameters: json.RawMessage(`{
			"type": "object", 
			"properties": {
				"demand": {"type": "string", "description": "What user wants develop something"}
			}, 
			"required": ["demand"]
		}`),
	},
}
