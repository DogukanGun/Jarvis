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

type AgentServer struct {
	agent *JarvisAgent
}

type MessageRequest struct {
	Message string `json:"message"`
}

type MessageResponse struct {
	Response string `json:"response"`
	Error    string `json:"error,omitempty"`
}

func NewAgentServer(userID string) (*AgentServer, error) {
	config := AgentConfig{
		UserID:      userID,
		OpenAIModel: getEnvOrDefault("OPENAI_MODEL", "gpt-4o-mini"),
		OpenAIKey:   os.Getenv("OPENAI_API_KEY"),
	}

	jarvisAgent, err := NewJarvisAgent(config)
	if err != nil {
		return nil, fmt.Errorf("failed to create agent: %v", err)
	}

	return &AgentServer{
		agent: jarvisAgent,
	}, nil
}

func (s *AgentServer) handleAgent(w http.ResponseWriter, r *http.Request) {
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

	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
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

func (s *AgentServer) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status": "healthy",
		"userID": s.agent.GetUserID(),
	})
}

func (s *AgentServer) handleCapabilities(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"tools":        s.agent.GetAvailableTools(),
		"capabilities": s.agent.GetCapabilities(),
	})
}

func main() {
	userID := os.Getenv("USER_ID")
	if userID == "" {
		log.Fatal("USER_ID environment variable is required")
	}

	server, err := NewAgentServer(userID)
	if err != nil {
		log.Fatalf("Failed to create agent server: %v", err)
	}

	port := getEnvOrDefault("PORT", "8080")

	http.HandleFunc("/agent", server.handleAgent)
	http.HandleFunc("/health", server.handleHealth)
	http.HandleFunc("/capabilities", server.handleCapabilities)

	log.Printf("Starting agent server for user %s on port %s", userID, port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
