package cmd

import (
	"context"
	"encoding/json"

	"jarvis/agent/visual_analyser/base"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

// Config holds the application configuration
type Config struct {
	DatabaseURL string
	Port        string
}

// Application holds the main application state
type Application struct {
	vectorStore base.VectorStore
	config      *Config
}

func main() {
	// Load configuration
	config := &Config{
		DatabaseURL: getEnv("DATABASE_URL", "postgres://jarvis:jarvispassword@postgres:5432/jarvis?sslmode=disable"),
		Port:        getEnv("PORT", "8080"),
	}

	// Create context
	ctx, cancel := context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	// Initialize vector store
	log.Println("Connecting to database...")
	vectorStore, err := base.NewPostgresVectorStore(ctx, config.DatabaseURL)
	if err != nil {
		log.Fatalf("Failed to initialize vector store: %v", err)
	}
	defer vectorStore.Close()

	log.Println("Database connection established")

	// Create application
	app := &Application{
		vectorStore: vectorStore,
		config:      config,
	}

	// Setup HTTP server
	mux := http.NewServeMux()
	mux.HandleFunc("/health", app.healthHandler)
	mux.HandleFunc("/api/v1/embeddings/upsert", app.upsertHandler)
	mux.HandleFunc("/api/v1/embeddings/search", app.searchHandler)
	mux.HandleFunc("/api/v1/embeddings/asset/", app.getAssetHandler)
	mux.HandleFunc("/api/v1/embeddings/owner/", app.getByOwnerHandler)
	mux.HandleFunc("/api/v1/embeddings/delete/", app.deleteHandler)
	mux.HandleFunc("/api/v1/ip/register", app.registerIPHandler)
	mux.HandleFunc("/api/v1/ip/check", app.checkIPHandler)

	// Add logging middleware
	handler := loggingMiddleware(mux)

	// Start server
	server := &http.Server{
		Addr:         ":" + config.Port,
		Handler:      handler,
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  120 * time.Second,
	}

	// Start Kafka consumer (optional - only if Kafka is enabled)
	enableKafka := getEnv("ENABLE_KAFKA", "false")
	var kafkaConsumer *base.KafkaConsumer
	if enableKafka == "true" {
		log.Println("Kafka integration enabled, starting consumer...")
		kafkaConsumer, err = base.NewKafkaConsumer(vectorStore)
		if err != nil {
			log.Printf("Warning: Failed to create Kafka consumer: %v", err)
			log.Println("Continuing without Kafka integration...")
		} else {
			// Start Kafka consumer in background
			kafkaCtx, kafkaCancel := context.WithCancel(context.Background())
			defer kafkaCancel()

			go func() {
				if err := kafkaConsumer.Start(kafkaCtx); err != nil {
					log.Printf("Kafka consumer error: %v", err)
				}
			}()
			log.Println("Kafka consumer started successfully")
		}
	} else {
		log.Println("Kafka integration disabled (set ENABLE_KAFKA=true to enable)")
	}

	// Graceful shutdown
	go func() {
		log.Printf("Visual Analyser Service starting on port %s...", config.Port)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Server failed to start: %v", err)
		}
	}()

	// Wait for interrupt signal
	quit := make(chan os.Signal, 1)
	signal.Notify(quit, syscall.SIGINT, syscall.SIGTERM)
	<-quit

	log.Println("Shutting down server...")

	// Close Kafka consumer if it was started
	if kafkaConsumer != nil {
		log.Println("Closing Kafka consumer...")
		if err := kafkaConsumer.Close(); err != nil {
			log.Printf("Error closing Kafka consumer: %v", err)
		}
	}

	ctx, cancel = context.WithTimeout(context.Background(), 30*time.Second)
	defer cancel()

	if err := server.Shutdown(ctx); err != nil {
		log.Printf("Server forced to shutdown: %v", err)
	}

	log.Println("Server stopped")
}

// Health check endpoint
func (app *Application) healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	json.NewEncoder(w).Encode(map[string]interface{}{
		"status":    "healthy",
		"service":   "visual-analyser",
		"timestamp": time.Now().UTC(),
	})
}

// Upsert embedding endpoint
func (app *Application) upsertHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req base.UpsertRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	if err := app.vectorStore.Upsert(ctx, &req); err != nil {
		log.Printf("Upsert failed: %v", err)
		respondError(w, "Failed to upsert embedding", http.StatusInternalServerError)
		return
	}

	respondJSON(w, map[string]interface{}{
		"success":  true,
		"message":  "Embedding upserted successfully",
		"asset_id": req.AssetID,
	}, http.StatusOK)
}

// Search nearest neighbors endpoint
func (app *Application) searchHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req base.SearchRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	results, err := app.vectorStore.SearchNearest(ctx, &req)
	if err != nil {
		log.Printf("Search failed: %v", err)
		respondError(w, "Failed to search embeddings", http.StatusInternalServerError)
		return
	}

	respondJSON(w, results, http.StatusOK)
}

// Get asset by ID endpoint
func (app *Application) getAssetHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract asset ID from path
	assetID := r.URL.Path[len("/api/v1/embeddings/asset/"):]
	if assetID == "" {
		respondError(w, "Asset ID is required", http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	asset, err := app.vectorStore.GetByAssetID(ctx, assetID)
	if err != nil {
		log.Printf("Get asset failed: %v", err)
		respondError(w, "Asset not found", http.StatusNotFound)
		return
	}

	respondJSON(w, asset, http.StatusOK)
}

// Get assets by owner ID endpoint
func (app *Application) getByOwnerHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract owner ID from path
	ownerID := r.URL.Path[len("/api/v1/embeddings/owner/"):]
	if ownerID == "" {
		respondError(w, "Owner ID is required", http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	assets, err := app.vectorStore.GetByOwnerID(ctx, ownerID)
	if err != nil {
		log.Printf("Get assets by owner failed: %v", err)
		respondError(w, "Failed to get assets", http.StatusInternalServerError)
		return
	}

	respondJSON(w, map[string]interface{}{
		"assets": assets,
		"count":  len(assets),
	}, http.StatusOK)
}

// Delete asset endpoint
func (app *Application) deleteHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodDelete {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	// Extract asset ID from path
	assetID := r.URL.Path[len("/api/v1/embeddings/delete/"):]
	if assetID == "" {
		respondError(w, "Asset ID is required", http.StatusBadRequest)
		return
	}

	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	if err := app.vectorStore.Delete(ctx, assetID); err != nil {
		log.Printf("Delete failed: %v", err)
		respondError(w, "Failed to delete asset", http.StatusInternalServerError)
		return
	}

	respondJSON(w, map[string]interface{}{
		"success": true,
		"message": "Asset deleted successfully",
	}, http.StatusOK)
}

// IPRegistrationRequest represents a request to register a new IP asset
type IPRegistrationRequest struct {
	AssetID   string                 `json:"asset_id"`
	OwnerID   string                 `json:"owner_id"`
	Embedding []float32              `json:"embedding"`
	Metadata  map[string]interface{} `json:"metadata"`
	Threshold float64                `json:"threshold"` // Similarity threshold (0-1)
}

// IPCheckRequest represents a request to check if an IP asset already exists
type IPCheckRequest struct {
	Embedding []float32 `json:"embedding"`
	Threshold float64   `json:"threshold"` // Similarity threshold (0-1)
	TopK      int       `json:"top_k"`
}

// Convert to visualanalyser types
func (r *IPRegistrationRequest) toUpsertRequest() *base.UpsertRequest {
	return &base.UpsertRequest{
		AssetID:   r.AssetID,
		OwnerID:   r.OwnerID,
		Embedding: r.Embedding,
		Metadata:  r.Metadata,
	}
}

func (r *IPCheckRequest) toSearchRequest() *base.SearchRequest {
	return &base.SearchRequest{
		Embedding: r.Embedding,
		TopK:      r.TopK,
		MinScore:  r.Threshold,
	}
}

// Register new IP asset with conflict detection
func (app *Application) registerIPHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req IPRegistrationRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Set default threshold if not provided
	if req.Threshold == 0 {
		req.Threshold = 0.85 // Default 85% similarity threshold
	}

	ctx, cancel := context.WithTimeout(r.Context(), 15*time.Second)
	defer cancel()

	// Step 1: Check for similar existing assets
	searchReq := &base.SearchRequest{
		Embedding: req.Embedding,
		TopK:      5,
		MinScore:  req.Threshold,
	}

	searchResults, err := app.vectorStore.SearchNearest(ctx, searchReq)
	if err != nil {
		log.Printf("Search during registration failed: %v", err)
		respondError(w, "Failed to check for conflicts", http.StatusInternalServerError)
		return
	}

	// Step 2: Check if any results exceed the threshold (potential conflict)
	if searchResults.Count > 0 {
		var conflictingAssets []base.SimilarAsset
		for _, result := range searchResults.Results {
			if result.Similarity >= req.Threshold {
				conflictingAssets = append(conflictingAssets, result)
			}
		}

		if len(conflictingAssets) > 0 {
			// IP conflict detected
			respondJSON(w, map[string]interface{}{
				"success":            false,
				"conflict_detected":  true,
				"message":            "Similar IP assets already exist",
				"conflicting_assets": conflictingAssets,
				"conflict_count":     len(conflictingAssets),
			}, http.StatusConflict)
			return
		}
	}

	// Step 3: No conflicts, register the asset
	upsertReq := req.toUpsertRequest()

	if err := app.vectorStore.Upsert(ctx, upsertReq); err != nil {
		log.Printf("Registration failed: %v", err)
		respondError(w, "Failed to register IP asset", http.StatusInternalServerError)
		return
	}

	respondJSON(w, map[string]interface{}{
		"success":           true,
		"conflict_detected": false,
		"message":           "IP asset registered successfully",
		"asset_id":          req.AssetID,
	}, http.StatusCreated)
}

// Check if IP asset is unique without registering
func (app *Application) checkIPHandler(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var req IPCheckRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		respondError(w, "Invalid request body", http.StatusBadRequest)
		return
	}

	// Set defaults
	if req.Threshold == 0 {
		req.Threshold = 0.85
	}
	if req.TopK == 0 {
		req.TopK = 10
	}

	ctx, cancel := context.WithTimeout(r.Context(), 10*time.Second)
	defer cancel()

	searchReq := req.toSearchRequest()

	results, err := app.vectorStore.SearchNearest(ctx, searchReq)
	if err != nil {
		log.Printf("IP check failed: %v", err)
		respondError(w, "Failed to check IP uniqueness", http.StatusInternalServerError)
		return
	}

	// Analyze results
	isUnique := true
	var conflictingAssets []base.SimilarAsset

	for _, result := range results.Results {
		if result.Similarity >= req.Threshold {
			isUnique = false
			conflictingAssets = append(conflictingAssets, result)
		}
	}

	respondJSON(w, map[string]interface{}{
		"is_unique":          isUnique,
		"threshold":          req.Threshold,
		"similar_assets":     results.Results,
		"conflicting_assets": conflictingAssets,
		"conflict_count":     len(conflictingAssets),
	}, http.StatusOK)
}

// Helper functions
func getEnv(key, defaultValue string) string {
	if value := os.Getenv(key); value != "" {
		return value
	}
	return defaultValue
}

func respondJSON(w http.ResponseWriter, data interface{}, statusCode int) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(statusCode)
	if err := json.NewEncoder(w).Encode(data); err != nil {
		log.Printf("Failed to encode JSON response: %v", err)
	}
}

func respondError(w http.ResponseWriter, message string, statusCode int) {
	respondJSON(w, map[string]interface{}{
		"error":   true,
		"message": message,
	}, statusCode)
}

func loggingMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		log.Printf("[%s] %s %s", r.Method, r.URL.Path, r.RemoteAddr)
		next.ServeHTTP(w, r)
		log.Printf("[%s] %s completed in %v", r.Method, r.URL.Path, time.Since(start))
	})
}
