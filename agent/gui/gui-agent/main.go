package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"
)

type GUIAgentServer struct {
	agent *GUIAgent
}

type MessageRequest struct {
	Message string `json:"message"`
}

type MessageResponse struct {
	Response string `json:"response"`
	Error    string `json:"error,omitempty"`
}

func NewGUIAgentServer() (*GUIAgentServer, error) {
	config := GUIAgentConfig{
		OllamaHost:   getEnvOrDefault("OLLAMA_HOST", "http://127.0.0.1:11434"),
		OllamaModel:  getEnvOrDefault("OLLAMA_MODEL", "llama3.2"),
		GUIDaemonURL: getEnvOrDefault("GUI_DAEMON_URL", "http://localhost:9990/"),
	}

	guiAgent, err := NewGUIAgent(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create GUI agent: %v", err)
	}

	return &GUIAgentServer{
		agent: guiAgent,
	}, nil
}

func (s *GUIAgentServer) handleAgent(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req MessageRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	if req.Message == "" {
		http.Error(w, "Message is required", http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Hour)
	defer cancel()

	response, err := s.agent.ProcessMessage(ctx, req.Message)

	w.Header().Set("Content-Type", "application/json")

	resp := MessageResponse{
		Response: response,
	}

	if err != nil {
		resp.Error = err.Error()
	}

	json.NewEncoder(w).Encode(resp)
}

func (s *GUIAgentServer) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status": "healthy",
		"agent":  "gui-agent",
	})
}

func (s *GUIAgentServer) handleCapabilities(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"tools":        s.agent.GetAvailableTools(),
		"capabilities": s.agent.GetCapabilities(),
	})
}

func main() {

	server, err := NewGUIAgentServer()
	if err != nil {
		log.Fatalf("Failed to create GUI agent server: %v", err)
	}

	port := getEnvOrDefault("PORT", "8080")

	http.HandleFunc("/agent", server.handleAgent)
	http.HandleFunc("/health", server.handleHealth)
	http.HandleFunc("/capabilities", server.handleCapabilities)

	log.Printf("GUI Daemon URL: %s", os.Getenv("GUI_DAEMON_URL"))
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
