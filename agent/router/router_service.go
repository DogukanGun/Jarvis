package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"
)

// RouterService forwards all requests to the General Agent
type RouterService struct {
	generalAgentURL string
	httpClient      *http.Client
}

// AgentRequest represents the request to General Agent
type AgentRequest struct {
	Message   string `json:"message"`
	UserID    string `json:"user_id,omitempty"`
	ImageData string `json:"image_data,omitempty"`
}

// AgentResponse represents the response from General Agent
type AgentResponse struct {
	Response string `json:"response"`
	Error    string `json:"error,omitempty"`
}

func NewRouterService() (*RouterService, error) {
	generalAgentURL := os.Getenv("GENERAL_AGENT_URL")
	if generalAgentURL == "" {
		generalAgentURL = "http://localhost:8081"
	}

	return &RouterService{
		generalAgentURL: generalAgentURL,
		httpClient: &http.Client{
			Timeout: 5 * time.Minute,
		},
	}, nil
}

func (rs *RouterService) ProcessMessage(ctx context.Context, userMessage string, imageData string) (string, error) {
	log.Printf("Forwarding request to General Agent: %s", userMessage[:min(50, len(userMessage))])

	// Build request to General Agent
	request := AgentRequest{
		Message:   userMessage,
		UserID:    os.Getenv("USER_ID"),
		ImageData: imageData,
	}

	requestBody, err := json.Marshal(request)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %v", err)
	}

	// Send request to General Agent
	agentURL := fmt.Sprintf("%s/agent", rs.generalAgentURL)
	req, err := http.NewRequestWithContext(ctx, "POST", agentURL, bytes.NewReader(requestBody))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %v", err)
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := rs.httpClient.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to send request to General Agent: %v", err)
	}
	defer resp.Body.Close()

	// Read response
	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response: %v", err)
	}

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("General Agent returned status %d: %s", resp.StatusCode, string(body))
	}

	// Parse response
	var agentResp AgentResponse
	if err := json.Unmarshal(body, &agentResp); err != nil {
		// If it's not JSON, return the raw response
		return string(body), nil
	}

	if agentResp.Error != "" {
		return "", fmt.Errorf("General Agent error: %s", agentResp.Error)
	}

	log.Printf("Received response from General Agent")
	return agentResp.Response, nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
