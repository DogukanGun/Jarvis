package main

import (
	"encoding/json"
	"log"
	"net/http"
	"os"
)

// ComputerUseController handles HTTP requests
type ComputerUseController struct {
	service *ComputerUseService
}

// NewComputerUseController creates a new controller
func NewComputerUseController() *ComputerUseController {
	return &ComputerUseController{
		service: NewComputerUseService(),
	}
}

// HandleComputerUse handles POST /computer-use requests
func (c *ComputerUseController) HandleComputerUse(w http.ResponseWriter, r *http.Request) {
	// Only accept POST requests
	if r.Method != http.MethodPost {
		c.sendError(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Parse request body
	var action ComputerAction
	if err := json.NewDecoder(r.Body).Decode(&action); err != nil {
		log.Printf("Error decoding request: %v", err)
		c.sendError(w, "Invalid JSON request", http.StatusBadRequest)
		return
	}

	// Log action (don't log base64 data)
	if action.Action == "write_file" {
		log.Printf("Computer action request: write_file (data omitted)")
	} else {
		log.Printf("Computer action request: %s", action.Action)
	}

	// Execute action
	result, err := c.service.ExecuteAction(action)
	if err != nil {
		log.Printf("Error executing action: %v", err)
		c.sendError(w, err.Error(), http.StatusInternalServerError)
		return
	}

	// Send success response
	c.sendSuccess(w, result)
}

// HandleHealth handles GET /health requests
func (c *ComputerUseController) HandleHealth(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]string{
		"status":  "healthy",
		"service": "gui-daemon",
	})
}

// sendSuccess sends a success response
func (c *ComputerUseController) sendSuccess(w http.ResponseWriter, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)

	response := Response{
		Success: true,
		Data:    data,
	}

	if err := json.NewEncoder(w).Encode(response); err != nil {
		log.Printf("Error encoding response: %v", err)
	}
}

// sendError sends an error response
func (c *ComputerUseController) sendError(w http.ResponseWriter, message string, statusCode int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)

	response := Response{
		Success: false,
		Error:   message,
	}

	if err := json.NewEncoder(w).Encode(response); err != nil {
		log.Printf("Error encoding error response: %v", err)
	}
}

// loggingMiddleware logs all HTTP requests
func loggingMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		log.Printf("%s %s from %s", r.Method, r.URL.Path, r.RemoteAddr)
		next(w, r)
	}
}

// corsMiddleware adds CORS headers
func corsMiddleware(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")

		// Handle preflight requests
		if r.Method == "OPTIONS" {
			w.WriteHeader(http.StatusOK)
			return
		}

		next(w, r)
	}
}

func main() {
	// Get port from environment or use default
	port := os.Getenv("PORT")
	if port == "" {
		port = "9990"
	}

	// Create controller
	controller := NewComputerUseController()

	// Setup routes
	http.HandleFunc("/computer-use", corsMiddleware(loggingMiddleware(controller.HandleComputerUse)))
	http.HandleFunc("/health", corsMiddleware(loggingMiddleware(controller.HandleHealth)))

	// Root endpoint
	http.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{
			"service": "Jarvis GUI Daemon",
			"version": "1.0.0",
			"status":  "running",
		})
	})

	// Start server
	log.Printf("Starting Jarvis GUI Daemon on port %s", port)
	log.Printf("Endpoints:")
	log.Printf("  POST /computer-use - Execute computer actions")
	log.Printf("  GET  /health       - Health check")

	if err := http.ListenAndServe(":"+port, nil); err != nil {
		log.Fatalf("Server failed to start: %v", err)
	}
}
