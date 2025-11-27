package base

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"strings"

	"github.com/segmentio/kafka-go"
)

// KafkaConsumer handles incoming messages from Kafka
type KafkaConsumer struct {
	reader      *kafka.Reader
	vectorStore VectorStore
}

// AgentMessage represents a message from the router
type AgentMessage struct {
	ID        string `json:"id"`
	UserID    string `json:"user_id"`
	Demand    string `json:"demand"`
	Timestamp int64  `json:"timestamp"`
	ImageData string `json:"image_data,omitempty"` // Base64 encoded image
}

// NewKafkaConsumer creates a new Kafka consumer
func NewKafkaConsumer(vectorStore VectorStore) (*KafkaConsumer, error) {
	brokers := os.Getenv("KAFKA_BROKERS")
	if brokers == "" {
		brokers = "localhost:9092"
	}

	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers:  []string{brokers},
		Topic:    "visual-analyser-requests",
		GroupID:  "visual-analyser-group",
		MinBytes: 10e3, // 10KB
		MaxBytes: 10e6, // 10MB
	})

	return &KafkaConsumer{
		reader:      reader,
		vectorStore: vectorStore,
	}, nil
}

// Start begins consuming messages from Kafka
func (kc *KafkaConsumer) Start(ctx context.Context) error {
	log.Println("Starting Kafka consumer for visual-analyser-requests...")

	for {
		select {
		case <-ctx.Done():
			log.Println("Kafka consumer shutting down...")
			return kc.reader.Close()
		default:
			msg, err := kc.reader.FetchMessage(ctx)
			if err != nil {
				log.Printf("Error fetching message: %v", err)
				continue
			}

			log.Printf("Received message: key=%s", string(msg.Key))

			// Process the message
			if err := kc.processMessage(ctx, msg.Value); err != nil {
				log.Printf("Error processing message: %v", err)
			}

			// Commit the message
			if err := kc.reader.CommitMessages(ctx, msg); err != nil {
				log.Printf("Error committing message: %v", err)
			}
		}
	}
}

// processMessage handles an incoming agent message
func (kc *KafkaConsumer) processMessage(ctx context.Context, data []byte) error {
	var agentMsg AgentMessage
	if err := json.Unmarshal(data, &agentMsg); err != nil {
		return fmt.Errorf("failed to unmarshal message: %w", err)
	}

	log.Printf("Processing visual analysis request from user %s: %s", agentMsg.UserID, agentMsg.Demand)

	// Check if image data is provided
	if agentMsg.ImageData == "" {
		log.Printf("Warning: No image data provided in message %s", agentMsg.ID)
		return fmt.Errorf("no image data provided")
	}

	// Decode base64 image
	imageBytes, err := base64.StdEncoding.DecodeString(agentMsg.ImageData)
	if err != nil {
		log.Printf("Failed to decode base64 image: %v", err)
		return fmt.Errorf("invalid base64 image data: %w", err)
	}

	log.Printf("Image decoded successfully: %d bytes", len(imageBytes))

	// Determine the action based on demand
	demand := strings.ToLower(agentMsg.Demand)

	if strings.Contains(demand, "register") || strings.Contains(demand, "add") || strings.Contains(demand, "store") {
		// Register new IP asset
		return kc.handleIPRegistration(ctx, agentMsg, imageBytes)
	} else if strings.Contains(demand, "check") || strings.Contains(demand, "search") || strings.Contains(demand, "similar") || strings.Contains(demand, "find") {
		// Check for similar images
		return kc.handleSimilarityCheck(ctx, agentMsg, imageBytes)
	} else {
		// Default to similarity check
		return kc.handleSimilarityCheck(ctx, agentMsg, imageBytes)
	}
}

// handleIPRegistration registers a new IP asset
func (kc *KafkaConsumer) handleIPRegistration(ctx context.Context, msg AgentMessage, imageBytes []byte) error {
	log.Printf("Handling IP registration for user %s", msg.UserID)

	// TODO: Extract features from image and generate embedding
	// For now, this is a placeholder. In production, you would:
	// 1. Use a pre-trained model (ResNet, CLIP, etc.) to extract features
	// 2. Generate a 768-dimensional embedding
	// 3. Normalize the embedding

	// Placeholder: Generate a dummy embedding
	// In production, replace this with actual feature extraction
	embedding := generatePlaceholderEmbedding(imageBytes)

	// First check if similar images exist
	searchReq := &SearchRequest{
		Embedding: embedding,
		TopK:      5,
		MinScore:  0.85, // High threshold for IP registration
	}

	results, err := kc.vectorStore.SearchNearest(ctx, searchReq)
	if err != nil {
		log.Printf("Failed to search for similar assets: %v", err)
		return err
	}

	// Check for conflicts
	if results.Count > 0 && results.Results[0].Similarity >= 0.85 {
		log.Printf("IP conflict detected! Similar asset found: %s (similarity: %.2f)",
			results.Results[0].AssetID, results.Results[0].Similarity)
		// TODO: Send response back to user about conflict
		return fmt.Errorf("IP conflict: similar asset exists")
	}

	// No conflict, register the asset
	assetID := fmt.Sprintf("asset_%s_%d", msg.UserID, msg.Timestamp)

	upsertReq := &UpsertRequest{
		AssetID:   assetID,
		OwnerID:   msg.UserID,
		Embedding: embedding,
		Metadata: map[string]interface{}{
			"demand":           msg.Demand,
			"registered_at":    msg.Timestamp,
			"message_id":       msg.ID,
			"image_size_bytes": len(imageBytes),
		},
	}

	if err := kc.vectorStore.Upsert(ctx, upsertReq); err != nil {
		log.Printf("Failed to register IP asset: %v", err)
		return err
	}

	log.Printf("Successfully registered IP asset: %s", assetID)
	// TODO: Send success response back to user

	return nil
}

// handleSimilarityCheck checks for similar images
func (kc *KafkaConsumer) handleSimilarityCheck(ctx context.Context, msg AgentMessage, imageBytes []byte) error {
	log.Printf("Handling similarity check for user %s", msg.UserID)

	// TODO: Extract features from image and generate embedding
	embedding := generatePlaceholderEmbedding(imageBytes)

	// Search for similar assets
	searchReq := &SearchRequest{
		Embedding: embedding,
		TopK:      10,
		MinScore:  0.70, // Lower threshold for similarity check
	}

	results, err := kc.vectorStore.SearchNearest(ctx, searchReq)
	if err != nil {
		log.Printf("Failed to search for similar assets: %v", err)
		return err
	}

	log.Printf("Found %d similar assets", results.Count)
	for i, result := range results.Results {
		log.Printf("  %d. %s (similarity: %.4f, owner: %s)",
			i+1, result.AssetID, result.Similarity, result.OwnerID)
	}

	// TODO: Send results back to user

	return nil
}

// generatePlaceholderEmbedding creates a placeholder embedding
// TODO: Replace with actual feature extraction using ML model
func generatePlaceholderEmbedding(imageBytes []byte) []float32 {
	// This is a PLACEHOLDER implementation
	// In production, you would:
	// 1. Load a pre-trained model (e.g., ResNet, CLIP, etc.)
	// 2. Preprocess the image
	// 3. Run inference to get embeddings
	// 4. Return the normalized embedding vector

	// For now, create a deterministic embedding based on image bytes
	// This allows testing without requiring an ML model
	embedding := make([]float32, 768)

	// Simple hash-based approach for testing
	// NOT suitable for production!
	sum := uint64(0)
	for i, b := range imageBytes {
		sum += uint64(b) * uint64(i+1)
	}

	for i := range embedding {
		sum = (sum*1103515245 + 12345) & 0x7fffffff
		embedding[i] = float32(sum%1000) / 1000.0
	}

	// Normalize
	return NormalizeEmbedding(embedding)
}

// Close closes the Kafka consumer
func (kc *KafkaConsumer) Close() error {
	return kc.reader.Close()
}
