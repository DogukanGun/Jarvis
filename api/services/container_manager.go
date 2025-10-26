package services

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"jarvis/api/data"
	"jarvis/api/repository"
	"net/http"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"sync"
	"time"
)

type ContainerManager struct {
	mutex      sync.RWMutex
	repository *repository.ContainerRepository
}

func NewContainerManager(repo *repository.ContainerRepository) *ContainerManager {
	return &ContainerManager{
		repository: repo,
	}
}

// CreateContainer creates a new Docker container for a user's agent
func (cm *ContainerManager) CreateContainer(userID string) (string, error) {
	cm.mutex.Lock()
	defer cm.mutex.Unlock()

	// Create user-specific container name
	containerName := fmt.Sprintf("jarvis-user-%s", userID)

	// Check if container already exists
	if cm.containerExists(containerName) {
		return "", fmt.Errorf("container already exists for user %s", userID)
	}

	// Ensure agent image is built
	if err := cm.ensureAgentImageExists(); err != nil {
		return "", fmt.Errorf("failed to ensure agent image exists: %v", err)
	}

	// Ensure jarvis network exists
	if err := cm.ensureNetworkExists(); err != nil {
		return "", fmt.Errorf("failed to ensure network exists: %v", err)
	}

	// Find available port (simple approach - in production use port management)
	port := cm.findAvailablePort()

	// Create a docker-compose service definition for this user's agent
	if err := cm.createUserAgentService(userID, containerName, port); err != nil {
		return "", fmt.Errorf("failed to create user agent service: %v", err)
	}

	// Start the user's agent service using docker-compose
	cmd := exec.Command("docker-compose", "-f", "./agent/docker-compose.yml", "-f", fmt.Sprintf("./agent/docker-compose.user-%s.yml", userID), "up", "-d", fmt.Sprintf("agent-%s", userID))
	output, err := cmd.CombinedOutput()
	if err != nil {
		return "", fmt.Errorf("failed to start user agent service: %v, output: %s", err, string(output))
	}

	// Store container info in database
	container := &data.ContainerInfo{
		ID:       containerName, // Use container name as ID for consistency
		UserID:   userID,
		Status:   "running",
		Port:     port,
		Created:  time.Now(),
		LastUsed: time.Now(),
	}

	ctx := context.Background()
	if err := cm.repository.Create(ctx, container); err != nil {
		return "", fmt.Errorf("failed to store container info: %v", err)
	}

	// Wait a moment for container to start
	time.Sleep(3 * time.Second)

	return containerName, nil
}

// SendMessage sends a message to a specific container via HTTP
func (cm *ContainerManager) SendMessage(containerID, message string) (string, error) {
	ctx := context.Background()
	container, err := cm.repository.GetByID(ctx, containerID)
	if err != nil {
		return "", fmt.Errorf("container not found: %v", err)
	}

	// Ensure container is running before sending message
	if err := cm.ensureContainerRunning(containerID); err != nil {
		return "", fmt.Errorf("container not available: %v", err)
	}

	// Update last used time
	if err := cm.repository.UpdateLastUsed(ctx, containerID); err != nil {
		// Log error but don't fail the message sending
		fmt.Printf("Warning: failed to update last used time: %v\n", err)
	}

	// Send HTTP request to container
	url := fmt.Sprintf("http://localhost:%d/agent", container.Port)

	requestBody := map[string]string{
		"message": message,
	}

	jsonData, err := json.Marshal(requestBody)
	if err != nil {
		return "", fmt.Errorf("failed to marshal request: %v", err)
	}

	client := &http.Client{
		Timeout: 30 * time.Second,
	}

	req, err := http.NewRequest("POST", url, bytes.NewBuffer(jsonData))
	if err != nil {
		return "", fmt.Errorf("failed to create request: %v", err)
	}

	req.Header.Set("Content-Type", "application/json")

	resp, err := client.Do(req)
	if err != nil {
		return "", fmt.Errorf("failed to send request to container: %v", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return "", fmt.Errorf("container returned status %d", resp.StatusCode)
	}

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		return "", fmt.Errorf("failed to read response: %v", err)
	}

	var response map[string]interface{}
	if err := json.Unmarshal(body, &response); err != nil {
		return "", fmt.Errorf("failed to parse response: %v", err)
	}

	if responseText, ok := response["response"].(string); ok {
		return responseText, nil
	}

	return string(body), nil
}

// containerExists checks if a container exists (running or stopped)
func (cm *ContainerManager) containerExists(containerName string) bool {
	cmd := exec.Command("docker", "inspect", containerName)
	err := cmd.Run()
	return err == nil
}

// IsContainerRunning checks if a container is running
func (cm *ContainerManager) IsContainerRunning(containerID string) bool {
	cmd := exec.Command("docker", "inspect", "-f", "{{.State.Running}}", containerID)
	output, err := cmd.Output()
	if err != nil {
		return false
	}

	return strings.TrimSpace(string(output)) == "true"
}

// ensureContainerRunning ensures a container is running and ready to receive messages
func (cm *ContainerManager) ensureContainerRunning(containerID string) error {
	// Check if container is running
	if cm.IsContainerRunning(containerID) {
		return nil
	}

	// Try to start the container
	cmd := exec.Command("docker", "start", containerID)
	output, err := cmd.CombinedOutput()
	if err != nil {
		return fmt.Errorf("failed to start container %s: %v, output: %s", containerID, err, string(output))
	}

	// Wait for container to be ready
	maxWait := 10 * time.Second
	waitInterval := 500 * time.Millisecond
	elapsed := time.Duration(0)

	for elapsed < maxWait {
		if cm.IsContainerRunning(containerID) {
			// Give it a moment more to fully initialize
			time.Sleep(2 * time.Second)
			return nil
		}
		time.Sleep(waitInterval)
		elapsed += waitInterval
	}

	return fmt.Errorf("container %s failed to start within %v", containerID, maxWait)
}

// StartContainer starts a stopped container
func (cm *ContainerManager) StartContainer(containerID string) error {
	cmd := exec.Command("docker", "start", containerID)
	_, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("failed to start container: %v", err)
	}

	// Update status in database
	ctx := context.Background()
	container, err := cm.repository.GetByID(ctx, containerID)
	if err != nil {
		return fmt.Errorf("failed to get container: %v", err)
	}

	container.Status = "running"
	container.LastUsed = time.Now()
	if err := cm.repository.Update(ctx, container); err != nil {
		return fmt.Errorf("failed to update container status: %v", err)
	}

	return nil
}

// StopContainer stops a running container
func (cm *ContainerManager) StopContainer(containerID string) error {
	cmd := exec.Command("docker", "stop", containerID)
	_, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("failed to stop container: %v", err)
	}

	// Update status in database
	ctx := context.Background()
	container, err := cm.repository.GetByID(ctx, containerID)
	if err != nil {
		return fmt.Errorf("failed to get container: %v", err)
	}

	container.Status = "stopped"
	if err := cm.repository.Update(ctx, container); err != nil {
		return fmt.Errorf("failed to update container status: %v", err)
	}

	return nil
}

// ListContainers returns all containers
func (cm *ContainerManager) ListContainers() ([]*data.ContainerInfo, error) {
	ctx := context.Background()
	containers, err := cm.repository.GetAll(ctx)
	if err != nil {
		return nil, fmt.Errorf("failed to get containers: %v", err)
	}

	// Update status from Docker for each container
	for _, container := range containers {
		if cm.IsContainerRunning(container.ID) {
			container.Status = "running"
		} else {
			container.Status = "stopped"
		}
		// Update status in database
		cm.repository.Update(ctx, container)
	}

	return containers, nil
}

// findAvailablePort finds an available port starting from 9000
func (cm *ContainerManager) findAvailablePort() int {
	ctx := context.Background()
	containers, err := cm.repository.GetAll(ctx)
	if err != nil {
		// Fallback to default port range if database query fails
		return 9000
	}

	usedPorts := make(map[int]bool)
	for _, container := range containers {
		usedPorts[container.Port] = true
	}

	// Also check for actually running Docker containers to avoid conflicts
	cmd := exec.Command("docker", "ps", "--format", "{{.Ports}}")
	output, err := cmd.Output()
	if err == nil {
		lines := strings.Split(string(output), "\n")
		for _, line := range lines {
			// Parse Docker port mappings like "0.0.0.0:9000->8080/tcp"
			if strings.Contains(line, "->") {
				parts := strings.Split(line, "->")
				if len(parts) > 0 {
					portPart := strings.Split(parts[0], ":")
					if len(portPart) > 1 {
						if port, err := strconv.Atoi(portPart[len(portPart)-1]); err == nil {
							usedPorts[port] = true
						}
					}
				}
			}
		}
	}

	for port := 9000; port < 10000; port++ {
		if !usedPorts[port] {
			return port
		}
	}

	// Fallback to a random high port
	return 9000 + len(containers)
}

// CleanupIdleContainers removes containers that haven't been used for a while
func (cm *ContainerManager) CleanupIdleContainers(maxIdleTime time.Duration) error {
	ctx := context.Background()
	containers, err := cm.repository.GetAll(ctx)
	if err != nil {
		return fmt.Errorf("failed to get containers for cleanup: %v", err)
	}

	now := time.Now()
	for _, container := range containers {
		if now.Sub(container.LastUsed) > maxIdleTime {
			// Stop and remove the container
			exec.Command("docker", "stop", container.ID).Run()
			exec.Command("docker", "rm", container.ID).Run()
			// Remove from database
			if err := cm.repository.Delete(ctx, container.ID); err != nil {
				fmt.Printf("Warning: failed to delete container %s from database: %v\n", container.ID, err)
			}
		}
	}
	return nil
}

// ensureAgentImageExists checks if the agent image exists and builds it if not
func (cm *ContainerManager) ensureAgentImageExists() error {
	// Check if image exists
	cmd := exec.Command("docker", "images", "-q", "jarvis-agent:latest")
	output, err := cmd.Output()
	if err != nil {
		return fmt.Errorf("failed to check if image exists: %v", err)
	}

	// If image doesn't exist, build it
	if strings.TrimSpace(string(output)) == "" {
		fmt.Println("Building jarvis-agent image...")
		buildCmd := exec.Command("docker", "build", "-t", "jarvis-agent:latest", "./agent")
		buildOutput, err := buildCmd.CombinedOutput()
		if err != nil {
			return fmt.Errorf("failed to build agent image: %v, output: %s", err, string(buildOutput))
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
		return fmt.Errorf("failed to create jarvis-network: %v, output: %s", err, string(output))
	}
	fmt.Println("Network jarvis-network created successfully")
	return nil
}

// createUserAgentService creates a docker-compose override file for a user's agent service
func (cm *ContainerManager) createUserAgentService(userID, containerName string, port int) error {
	composeOverride := fmt.Sprintf(`services:
  agent-%s:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: %s
    ports:
      - "%d:8080"
    environment:
      - OPENAI_API_KEY=%s
      - AGENT_MODE=http
      - USER_ID=%s
      - CONTAINER_NAME=%s
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=jarvispassword
    depends_on:
      neo4j:
        condition: service_healthy
    networks:
      - jarvis-network
    restart: unless-stopped
`, userID, containerName, port,
		getEnvOrDefault("OPENAI_API_KEY", ""),
		userID, containerName)

	// Write the override file
	overrideFile := fmt.Sprintf("./agent/docker-compose.user-%s.yml", userID)
	return os.WriteFile(overrideFile, []byte(composeOverride), 0644)
}

func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
