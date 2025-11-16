package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"strings"
	"time"
)

type ContainerManager struct {
	containerID string
	port        int
	userID      string
	routerURL   string
}

type AgentRequest struct {
	Message string `json:"message"`
}

type AgentResponse struct {
	Response string `json:"response"`
	Error    string `json:"error,omitempty"`
}

func NewContainerManager(userID string) *ContainerManager {
	return &ContainerManager{
		userID:    userID,
		routerURL: "http://localhost:8083", // Router service port from docker-compose
	}
}

// StartContainer starts the docker-compose services and connects to the router
func (cm *ContainerManager) StartContainer() error {
	fmt.Println("Starting Jarvis services...")

	// Start all services using docker-compose
	cmd := exec.Command("docker-compose", "-f", "../agent/docker-compose.yml", "up", "-d")
	cmd.Dir = "./"

	// Set environment variables
	cmd.Env = append(os.Environ(),
		fmt.Sprintf("USER_ID=%s", cm.userID),
		fmt.Sprintf("OPENAI_API_KEY=%s", os.Getenv("OPENAI_API_KEY")),
	)

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to start services: %w, output: %s", err, string(output))
	}

	// Set a session identifier for this CLI connection
	cm.containerID = fmt.Sprintf("jarvis-agent-router") // Use the actual router container name

	fmt.Print("Waiting for router service")

	// Wait for router service to be ready
	if err := cm.waitForRouter(); err != nil {
		return fmt.Errorf("router service failed to start: %w", err)
	}

	fmt.Println(" ✓\nJarvis is ready!")
	return nil
}

// StopContainer stops the docker-compose services
func (cm *ContainerManager) StopContainer() error {
	if cm.containerID == "" {
		return nil
	}

	fmt.Println("Stopping Jarvis services...")

	// Stop all services using docker-compose
	cmd := exec.Command("docker-compose", "-f", "../agent/docker-compose.yml", "down")
	cmd.Dir = "./"

	// Set environment variables
	cmd.Env = append(os.Environ(),
		fmt.Sprintf("USER_ID=%s", cm.userID),
		fmt.Sprintf("OPENAI_API_KEY=%s", os.Getenv("OPENAI_API_KEY")),
	)

	output, err := cmd.CombinedOutput()
	if err != nil {
		// Log error but don't fail cleanup
		fmt.Printf("Warning: docker-compose down failed: %v, output: %s\n", err, string(output))
	}

	fmt.Println("Jarvis services stopped")
	cm.containerID = ""
	return nil
}

// SendMessage sends a message to the router service and returns the response
func (cm *ContainerManager) SendMessage(message string) (string, error) {
	if cm.containerID == "" {
		return "", fmt.Errorf("no session active")
	}

	// Check if router service is still running
	if !cm.isContainerRunning() {
		return "", fmt.Errorf("router service is not running")
	}

	// Send HTTP request to router service
	url := fmt.Sprintf("%s/message", cm.routerURL)

	requestBody := AgentRequest{
		Message: message,
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %w", err)
	}

	client := &http.Client{
		Timeout: 300 * time.Second, // 5 minute timeout for router operations
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to send request to router service: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("router service returned error (status %d): %s", resp.StatusCode, string(body))
	}

	var response AgentResponse
	if err := json.Unmarshal(body, &response); err != nil {
		// If we can't parse as JSON, assume it's plain text response
		return string(body), nil
	}

	if response.Error != "" {
		return "", fmt.Errorf("agent error: %s", response.Error)
	}

	return response.Response, nil
}

// isContainerRunning checks if the container is currently running
func (cm *ContainerManager) isContainerRunning() bool {
	if cm.containerID == "" {
		return false
	}

	cmd := exec.Command("docker", "inspect", "-f", "{{.State.Running}}", cm.containerID)
	output, err := cmd.Output()
	if err != nil {
		return false
	}

	return strings.TrimSpace(string(output)) == "true"
}

// waitForRouter waits for the router service to be ready to receive requests
func (cm *ContainerManager) waitForRouter() error {
	maxWait := 120 * time.Second
	waitInterval := 2 * time.Second
	elapsed := time.Duration(0)

	// Check if router service is ready
	healthURL := fmt.Sprintf("%s/health", cm.routerURL)
	client := &http.Client{Timeout: 5 * time.Second}

	for elapsed < maxWait {
		resp, err := client.Get(healthURL)
		if err == nil && resp.StatusCode == http.StatusOK {
			resp.Body.Close()
			return nil
		}
		if resp != nil {
			resp.Body.Close()
		}

		fmt.Print(".")
		time.Sleep(waitInterval)
		elapsed += waitInterval
	}

	return fmt.Errorf("router service did not become ready within %v", maxWait)
}

// ensureAgentImageExists checks if the agent image exists and builds it if not
func (cm *ContainerManager) ensureAgentImageExists() error {
	// Check if image exists
	cmd := exec.Command("docker", "images", "-q", "jarvis-agent:latest")
	output, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("failed to check if image exists: %w", err)
	}

	// If image doesn't exist, build it
	if strings.TrimSpace(string(output)) == "" {
		fmt.Println("Building jarvis-agent image...")

		// Find the agent directory relative to CLI
		agentDir := "../agent"
		if _, err := os.Stat(agentDir); os.IsNotExist(err) {
			agentDir = "../agent"
		}

		buildCmd := exec.Command("docker", "build", "-t", "jarvis-agent:latest", agentDir)
		buildOutput, err := buildCmd.CombinedOutput()
		if err != nil {
			return fmt.Errorf("failed to build agent image: %w, output: %s", err, string(buildOutput))
		}
		fmt.Println("Agent image built successfully")
	}

	return nil
}

// ensureNetworkExists checks if the jarvis network exists and creates it if not
func (cm *ContainerManager) ensureNetworkExists() error {
	// Check if agent_jarvis-network exists (from docker-compose)
	cmd := exec.Command("docker", "network", "inspect", "agent_jarvis-network")
	err := cmd.Run()
	if err == nil {
		return nil // Network already exists
	}

	// If not, check for standalone jarvis-network
	cmd = exec.Command("docker", "network", "inspect", "jarvis-network")
	err = cmd.Run()
	if err == nil {
		return nil // Network already exists
	}

	// Create the network
	fmt.Println("Creating jarvis-network...")
	createCmd := exec.Command("docker", "network", "create", "jarvis-network")
	output, err := createCmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to create jarvis-network: %w, output: %s", err, string(output))
	}
	fmt.Println("Network jarvis-network created successfully")
	return nil
}
