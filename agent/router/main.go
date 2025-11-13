package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/go-chi/chi/v5"
	"github.com/go-chi/chi/v5/middleware"
)

type RouterServer struct {
	routerService *RouterService
}

type MessageRequest struct {
	Message string `json:"message"`
}

type MessageResponse struct {
	Response string `json:"response"`
	Error    string `json:"error,omitempty"`
}

func NewRouterServer() (*RouterServer, error) {
	routerService, err := NewRouterService()
	if err != nil {
		return nil, fmt.Errorf("failed to create router service: %v", err)
	}

	return &RouterServer{
		routerService: routerService,
	}, nil
}

func (s *RouterServer) handleMessage(w http.ResponseWriter, r *http.Request) {
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

	response, err := s.routerService.ProcessMessage(ctx, req.Message)

	w.Header().Set("Content-Type", "application/json")

	resp := MessageResponse{
		Response: response,
	}

	if err != nil {
		resp.Error = err.Error()
	}

	json.NewEncoder(w).Encode(resp)
}

func (s *RouterServer) handleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status": "healthy",
		"service": "router",
	})
}

func main() {
	server, err := NewRouterServer()
	if err != nil {
		log.Fatalf("Failed to create router server: %v", err)
	}

	port := getEnvOrDefault("PORT", "8080")

	r := chi.NewRouter()
	r.Use(middleware.Logger)
	r.Use(middleware.Recoverer)
	
	r.Post("/message", server.handleMessage)
	r.Get("/health", server.handleHealth)

	log.Printf("Starting router server on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, r))
}

func getEnvOrDefault(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}
