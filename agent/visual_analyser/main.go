package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
)

// VisualAnalyserServer handles HTTP requests
type VisualAnalyserServer struct {
	analyzer *ScreenAnalyzer
}

// NewVisualAnalyserServer creates a new server
func NewVisualAnalyserServer() *VisualAnalyserServer {
	return &VisualAnalyserServer{
		analyzer: NewScreenAnalyzer(),
	}
}

// handleAnalyze handles POST /analyze requests
func (s *VisualAnalyserServer) handleAnalyze(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req AnalyzeScreenRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		log.Printf("Error decoding request: %v", err)
		http.Error(w, "Invalid JSON", http.StatusBadRequest)
		return
	}

	// Log request (don't log full screenshot)
	log.Printf("Analyze request: action=%s, query=%s, screenshot_length=%d",
		req.Action, req.Query, len(req.Screenshot))

	// Process request
	response, err := s.analyzer.AnalyzeScreen(req)
	if err != nil {
		log.Printf("Error analyzing screen: %v", err)
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusInternalServerError)
		json.NewEncoder(w).Encode(AnalyzeScreenResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	// Send response
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(response)
}

// handleHealth handles GET /health requests
func (s *VisualAnalyserServer) handleHealth(w http.ResponseWriter, r *http.Request) {
	visionModel := os.Getenv("VISION_MODEL")
	if visionModel == "" {
		visionModel = "llama3.2-vision"
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(HealthResponse{
		Status: "healthy",
		Agent:  "visual-analyser",
		Model:  visionModel,
	})
}

// handleCapabilities handles GET /capabilities requests
func (s *VisualAnalyserServer) handleCapabilities(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"capabilities": s.analyzer.GetCapabilities(),
	})
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8081"
	}

	server := NewVisualAnalyserServer()

	// Setup routes
	http.HandleFunc("/analyze", server.handleAnalyze)
	http.HandleFunc("/health", server.handleHealth)
	http.HandleFunc("/capabilities", server.handleCapabilities)

	// Root endpoint
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{
			"service": "Jarvis Visual Analyser",
			"version": "1.0.0",
			"purpose": "GUI Screen Analysis",
			"status":  "running",
		})
	})

	log.Printf("Starting Visual Analyser on port %s", port)
	log.Printf("Vision Model: %s", os.Getenv("VISION_MODEL"))
	log.Printf("Endpoints:")
	log.Printf("  POST /analyze       - Analyze screenshot")
	log.Printf("  GET  /health        - Health check")
	log.Printf("  GET  /capabilities  - Get capabilities")

	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}
