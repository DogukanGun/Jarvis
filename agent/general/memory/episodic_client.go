package memory

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// EpisodicMemoryClient handles communication with the Episodic Memory service
type EpisodicMemoryClient struct {
	baseURL    string
	httpClient *http.Client
}

// ContextRequest represents a request for memory context
type ContextRequest struct {
	UserID  string                 `json:"user_id"`
	Prompt  string                 `json:"prompt"`
	Context map[string]interface{} `json:"context,omitempty"`
}

// ContextResponse represents the memory context returned
type ContextResponse struct {
	UserID            string                   `json:"user_id"`
	Prompt            string                   `json:"prompt"`
	NormalizedPrompt  string                   `json:"normalized_prompt"`
	TaskType          string                   `json:"task_type"`
	Entities          []string                 `json:"entities"`
	RetrievedEpisodes []map[string]interface{} `json:"retrieved_episodes"`
	Mem0Items         []map[string]interface{} `json:"mem0_items"`
	LLMContext        map[string]interface{}   `json:"llm_context"`
}

// StoreRequest represents a request to store a memory
type StoreRequest struct {
	UserID   string                 `json:"user_id"`
	Prompt   string                 `json:"prompt"`
	Response string                 `json:"response"`
	Context  map[string]interface{} `json:"context,omitempty"`
}

// NewEpisodicMemoryClient creates a new client for the Episodic Memory service
func NewEpisodicMemoryClient(baseURL string) *EpisodicMemoryClient {
	if baseURL == "" {
		baseURL = "http://localhost:8085"
	}

	return &EpisodicMemoryClient{
		baseURL: baseURL,
		httpClient: &http.Client{
			Timeout: 30 * time.Second,
		},
	}
}

// GetContext retrieves memory context for a user's prompt
func (c *EpisodicMemoryClient) GetContext(ctx context.Context, userID, prompt string) (*ContextResponse, error) {
	request := ContextRequest{
		UserID: userID,
		Prompt: prompt,
	}

	requestBody, err := json.Marshal(request)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal request: %v", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/context", bytes.NewReader(requestBody))
	if err != nil {
		return nil, fmt.Errorf("failed to create request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("failed to send request: %v", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read response: %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("episodic memory returned status %d: %s", resp.StatusCode, string(body))
	}

	var contextResp ContextResponse
	if err := json.Unmarshal(body, &contextResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal response: %v", err)
	}

	return &contextResp, nil
}

// StoreInteraction stores an interaction in episodic memory
func (c *EpisodicMemoryClient) StoreInteraction(ctx context.Context, userID, prompt, response string) error {
	request := StoreRequest{
		UserID:   userID,
		Prompt:   prompt,
		Response: response,
	}

	requestBody, err := json.Marshal(request)
	if err != nil {
		return fmt.Errorf("failed to marshal request: %v", err)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", c.baseURL+"/store", bytes.NewReader(requestBody))
	if err != nil {
		return fmt.Errorf("failed to create request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("episodic memory returned status %d: %s", resp.StatusCode, string(body))
	}

	return nil
}

// FormatContextForLLM formats the memory context into a string for LLM input
func (c *EpisodicMemoryClient) FormatContextForLLM(ctx *ContextResponse) string {
	if ctx == nil {
		return ""
	}

	var result string

	// Add relevant episodes
	if len(ctx.RetrievedEpisodes) > 0 {
		result += "Relevant past interactions:\n"
		for i, episode := range ctx.RetrievedEpisodes {
			if i >= 5 { // Limit to 5 episodes
				break
			}
			if content, ok := episode["content"].(string); ok {
				result += fmt.Sprintf("- %s\n", content)
			}
		}
		result += "\n"
	}

	// Add mem0 items (long-term memory)
	if len(ctx.Mem0Items) > 0 {
		result += "User preferences and facts:\n"
		for i, item := range ctx.Mem0Items {
			if i >= 5 { // Limit to 5 items
				break
			}
			if memory, ok := item["memory"].(string); ok {
				result += fmt.Sprintf("- %s\n", memory)
			}
		}
		result += "\n"
	}

	return result
}

// Health checks if the episodic memory service is healthy
func (c *EpisodicMemoryClient) Health(ctx context.Context) error {
	req, err := http.NewRequestWithContext(ctx, "GET", c.baseURL+"/health", nil)
	if err != nil {
		return fmt.Errorf("failed to create request: %v", err)
	}

	resp, err := c.httpClient.Do(req)
	if err != nil {
		return fmt.Errorf("failed to send request: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("episodic memory unhealthy: status %d", resp.StatusCode)
	}

	return nil
}
