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
		userID: userID,
		port:   findAvailablePort(),
	}
}

// StartContainer creates and starts a new container for the CLI session
func (cm *ContainerManager) StartContainer() error {
	// Create unique container name for this CLI session
	cm.containerID = fmt.Sprintf("jarvis-cli-%s-%d", cm.userID, time.Now().Unix())

	// Ensure network exists (like API does)
	if err := cm.ensureNetworkExists(); err != nil {
		return fmt.Errorf("failed to ensure network exists: %w", err)
	}

	// Start using existing docker-compose with environment override
	cmd := exec.Command("docker-compose", "-f", "../agent/docker-compose.yml", "up", "-d", "agent-general")
	cmd.Dir = "./" // Stay in cli directory
	
	// Set environment variables for this user's container
	cmd.Env = append(os.Environ(),
		fmt.Sprintf("CONTAINER_NAME=%s", cm.containerID),
		fmt.Sprintf("CLI_PORT=%d", cm.port),
		fmt.Sprintf("USER_ID=%s", cm.userID),
		fmt.Sprintf("OPENAI_API_KEY=%s", os.Getenv("OPENAI_API_KEY")),
	)

	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to start container: %w, output: %s", err, string(output))
	}

	// Wait for container to be ready
	if err := cm.waitForContainer(); err != nil {
		// Get container logs for debugging
		cmd := exec.Command("docker", "logs", cm.containerID)
		if logs, logErr := cmd.Output(); logErr == nil && len(logs) > 0 {
			fmt.Printf("\nContainer logs:\n%s\n", string(logs))
		}

		cm.StopContainer()
		return fmt.Errorf("container failed to start properly: %w", err)
	}

	fmt.Printf("Container started: %s (port: %d)\n", cm.containerID, cm.port)
	return nil
}

// StopContainer stops the container using docker-compose
func (cm *ContainerManager) StopContainer() error {
	if cm.containerID == "" {
		return nil
	}

	// Stop using docker-compose with the same environment variables
	// First stop the service
	cmd := exec.Command("docker-compose", "-f", "../agent/docker-compose.yml", "stop", "agent-general")
	cmd.Dir = "./" // Stay in cli directory
	
	// Set the same environment variables that were used to start
	cmd.Env = append(os.Environ(),
		fmt.Sprintf("CONTAINER_NAME=%s", cm.containerID),
		fmt.Sprintf("CLI_PORT=%d", cm.port),
		fmt.Sprintf("USER_ID=%s", cm.userID),
		fmt.Sprintf("OPENAI_API_KEY=%s", os.Getenv("OPENAI_API_KEY")),
	)
	
	output, err := cmd.CombinedOutput()
	if err != nil {
		// Log error but don't fail cleanup
		fmt.Printf("Warning: docker-compose stop failed: %v, output: %s\n", err, string(output))
	}

	// Then remove the container
	cmd = exec.Command("docker-compose", "-f", "../agent/docker-compose.yml", "rm", "-f", "agent-general")
	cmd.Dir = "./" // Stay in cli directory
	cmd.Env = append(os.Environ(),
		fmt.Sprintf("CONTAINER_NAME=%s", cm.containerID),
		fmt.Sprintf("CLI_PORT=%d", cm.port),
		fmt.Sprintf("USER_ID=%s", cm.userID),
		fmt.Sprintf("OPENAI_API_KEY=%s", os.Getenv("OPENAI_API_KEY")),
	)
	
	output, err = cmd.CombinedOutput()
	if err != nil {
		// Log error but don't fail cleanup
		fmt.Printf("Warning: docker-compose rm failed: %v, output: %s\n", err, string(output))
	}

	fmt.Printf("Container stopped and removed via docker-compose: %s\n", cm.containerID)
	return nil
}

// SendMessage sends a message to the container and returns the response
func (cm *ContainerManager) SendMessage(message string) (string, error) {
	if cm.containerID == "" {
		return "", fmt.Errorf("no container running")
	}

	// Check if container is still running
	if !cm.isContainerRunning() {
		return "", fmt.Errorf("container is not running")
	}

	// Send HTTP request to container
	url := fmt.Sprintf("http://localhost:%d/agent", cm.port)

	requestBody := AgentRequest{
		Message: message,
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %w", err)
	}

	client := &http.Client{
		Timeout: 60 * time.Second, // Longer timeout for CLI operations
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %w", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to send request to container: %w", err)
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("container returned error (status %d): %s", resp.StatusCode, string(body))
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

// waitForContainer waits for the container to be ready to receive requests
func (cm *ContainerManager) waitForContainer() error {
	maxWait := 120 * time.Second // Increased to 2 minutes
	waitInterval := 2 * time.Second
	elapsed := time.Duration(0)

	fmt.Print("Waiting for agent to start")

	// First, check if container is running
	for elapsed < 30*time.Second {
		if cm.isContainerRunning() {
			break
		}
		fmt.Print(".")
		time.Sleep(1 * time.Second)
		elapsed += 1 * time.Second
	}

	if !cm.isContainerRunning() {
		fmt.Println()
		return fmt.Errorf("container failed to start")
	}

	fmt.Print(" (initializing)")

	// Then check if the HTTP endpoint is ready
	healthURL := fmt.Sprintf("http://localhost:%d/health", cm.port)
	agentURL := fmt.Sprintf("http://localhost:%d/agent", cm.port)
	client := &http.Client{Timeout: 5 * time.Second}

	elapsed = time.Duration(0)
	for elapsed < maxWait {
		// Try health endpoint first
		resp, err := client.Get(healthURL)
		if err == nil && resp.StatusCode == http.StatusOK {
			resp.Body.Close()
			fmt.Println(" ✓")
			return nil
		}
		if resp != nil {
			resp.Body.Close()
		}

		// If health endpoint fails, try agent endpoint
		resp, err = client.Get(agentURL)
		if err == nil && (resp.StatusCode == http.StatusOK || resp.StatusCode == http.StatusMethodNotAllowed) {
			resp.Body.Close()
			fmt.Println(" ✓")
			return nil
		}
		if resp != nil {
			resp.Body.Close()
		}

		fmt.Print(".")
		time.Sleep(waitInterval)
		elapsed += waitInterval
	}

	fmt.Println()
	return fmt.Errorf("container did not become ready within %v", maxWait)
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

// findAvailablePort finds an available port starting from 9000
func findAvailablePort() int {
	// Simple approach: use a random port in high range
	// In production, you might want to check for actual availability
	return 9000 + (int(time.Now().Unix()) % 1000)
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

