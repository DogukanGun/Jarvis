package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/signal"
	"strings"
	"sync"
	"syscall"
	"time"

	"github.com/google/uuid"
	"github.com/segmentio/kafka-go"
	"jarvis/agent/schemas/group"
)

// KafkaConsumer consumes events from the group communication layer
type KafkaConsumer struct {
	reader         *kafka.Reader
	producer       *kafka.Writer
	groupID        string
	agentID        string
	brokers        []string
	mu             sync.Mutex
	running        bool
	visionService  *VisionService
}

// NewKafkaConsumer creates a new Kafka consumer for the visual analyser
func NewKafkaConsumer(brokers []string, groupID, agentID string, visionService *VisionService) (*KafkaConsumer, error) {
	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers:        brokers,
		Topic:          group.EventsTopic(groupID),
		GroupID:        fmt.Sprintf("%s-group", agentID),
		StartOffset:    kafka.LastOffset,
		CommitInterval: time.Second,
		SessionTimeout: 10 * time.Second,
		MaxBytes:       1024 * 1024, // 1MB
	})

	producer := &kafka.Writer{
		Addr:     kafka.TCP(brokers...),
		Topic:    group.EventsTopic(groupID),
		Balancer: &kafka.LeastBytes{},
	}

	return &KafkaConsumer{
		reader:        reader,
		producer:      producer,
		groupID:       groupID,
		agentID:       agentID,
		brokers:       brokers,
		running:       false,
		visionService: visionService,
	}, nil
}

// createEnvelope creates a group layer envelope for publishing
func (kc *KafkaConsumer) createEnvelope(eventType string, payload map[string]interface{}, threadID string) *group.Envelope {
	if threadID == "" {
		threadID = uuid.New().String()
	}

	return group.NewEnvelope(
		kc.groupID,
		threadID,
		uuid.New().String(),
		group.Sender{
			ID:    kc.agentID,
			Role:  group.RoleMember,
			Agent: kc.agentID,
		},
		eventType,
		payload,
	)
}

// publishEvent publishes an event to the events topic
func (kc *KafkaConsumer) publishEvent(ctx context.Context, eventType string, payload map[string]interface{}, threadID string) error {
	envelope := kc.createEnvelope(eventType, payload, threadID)

	data, err := json.Marshal(envelope)
	if err != nil {
		return fmt.Errorf("failed to marshal envelope: %v", err)
	}

	message := kafka.Message{
		Key:   []byte(envelope.ThreadID),
		Value: data,
	}

	if err := kc.producer.WriteMessages(ctx, message); err != nil {
		return fmt.Errorf("failed to publish event: %v", err)
	}

	log.Printf("Published %s event: %s", eventType, envelope.MessageID)
	return nil
}

// handleCommand handles a command execution request
func (kc *KafkaConsumer) handleCommand(ctx context.Context, envelope *group.Envelope) error {
	targetAgent, _ := envelope.Payload["target_agent"].(string)
	command, _ := envelope.Payload["command"].(string)
	taskID, _ := envelope.Payload["task_id"].(string)
	if taskID == "" {
		taskID = uuid.New().String()
	}

	if targetAgent != kc.agentID {
		log.Printf("Command not for this agent (%s != %s)", targetAgent, kc.agentID)
		return nil
	}

	log.Printf("Received command: %s", command)

	// Publish task started event
	if err := kc.publishEvent(ctx, group.EventTaskStarted, map[string]interface{}{
		"task_id":       taskID,
		"target_agent":  kc.agentID,
		"status":        "started",
		"thread_id":     envelope.ThreadID,
	}, envelope.ThreadID); err != nil {
		log.Printf("Failed to publish task started event: %v", err)
	}

	// Execute the analysis
	imageURL, _ := envelope.Payload["image_url"].(string)
	imageData, _ := envelope.Payload["image_data"].(string)
	prompt, _ := envelope.Payload["prompt"].(string)

	if imageURL == "" && imageData == "" {
		errMsg := "No image provided"
		log.Printf("Error: %s", errMsg)

		if err := kc.publishEvent(ctx, group.EventTaskFailed, map[string]interface{}{
			"task_id":   taskID,
			"error":     errMsg,
			"status":    "failed",
			"thread_id": envelope.ThreadID,
		}, envelope.ThreadID); err != nil {
			log.Printf("Failed to publish task failed event: %v", err)
		}
		return nil
	}

	// Run vision analysis
	var result string
	var err error

	if imageData != "" {
		result, err = kc.visionService.AnalyzeImage(imageData, prompt)
	} else if imageURL != "" {
		// For URL, fetch it first - simplified to just analyze if we had base64
		result, err = kc.visionService.AnalyzeImage(imageURL, prompt)
	} else {
		err = fmt.Errorf("no image data or URL provided")
	}

	if err != nil {
		log.Printf("Error analyzing image: %v", err)

		if err := kc.publishEvent(ctx, group.EventTaskFailed, map[string]interface{}{
			"task_id":   taskID,
			"error":     err.Error(),
			"status":    "failed",
			"thread_id": envelope.ThreadID,
		}, envelope.ThreadID); err != nil {
			log.Printf("Failed to publish task failed event: %v", err)
		}
		return nil
	}

	// Publish task completed event
	if err := kc.publishEvent(ctx, group.EventTaskCompleted, map[string]interface{}{
		"task_id":   taskID,
		"status":    "completed",
		"result":    result,
		"duration":  0,
		"thread_id": envelope.ThreadID,
	}, envelope.ThreadID); err != nil {
		log.Printf("Failed to publish task completed event: %v", err)
	}

	// Publish result event
	if err := kc.publishEvent(ctx, group.EventResultImageAnalysis, map[string]interface{}{
		"task_id":   taskID,
		"type":      "image_analysis",
		"data":      map[string]interface{}{"analysis": result},
		"success":   true,
		"duration":  0,
		"thread_id": envelope.ThreadID,
	}, envelope.ThreadID); err != nil {
		log.Printf("Failed to publish result event: %v", err)
	}

	return nil
}

// processMessage processes a single Kafka message
func (kc *KafkaConsumer) processMessage(ctx context.Context, msg kafka.Message) error {
	var envelope group.Envelope

	if err := json.Unmarshal(msg.Value, &envelope); err != nil {
		return fmt.Errorf("failed to unmarshal envelope: %v", err)
	}

	// Validate envelope
	if err := group.ValidateEnvelope(&envelope); err != nil {
		return fmt.Errorf("invalid envelope: %v", err)
	}

	// Check group matches
	if envelope.GroupID != kc.groupID {
		return fmt.Errorf("envelope group_id mismatch: expected %s, got %s", kc.groupID, envelope.GroupID)
	}

	// Route by event type
	switch envelope.Type {
	case group.EventCommandRun:
		return kc.handleCommand(ctx, &envelope)
	default:
		log.Printf("Ignoring event type: %s", envelope.Type)
		return nil
	}
}

// Start starts consuming messages from Kafka
func (kc *KafkaConsumer) Start(ctx context.Context) error {
	kc.mu.Lock()
	if kc.running {
		kc.mu.Unlock()
		return fmt.Errorf("consumer already running")
	}
	kc.running = true
	kc.mu.Unlock()

	log.Printf("Starting Kafka consumer for %s in group %s", kc.agentID, kc.groupID)

	// Setup signal handling
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-sigChan:
			log.Println("Received shutdown signal, stopping consumer...")
			return kc.Stop()
		default:
		}

		// Read message with timeout
		msgCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		msg, err := kc.reader.ReadMessage(msgCtx)
		cancel()

		if err != nil {
			if err == context.DeadlineExceeded {
				continue
			}
			log.Printf("Error reading message: %v", err)
			continue
		}

		// Process message
		if err := kc.processMessage(ctx, msg); err != nil {
			log.Printf("Error processing message: %v", err)
		}
	}
}

// Stop stops the consumer
func (kc *KafkaConsumer) Stop() error {
	kc.mu.Lock()
	defer kc.mu.Unlock()

	if !kc.running {
		return fmt.Errorf("consumer not running")
	}

	kc.running = false

	if err := kc.reader.Close(); err != nil {
		return fmt.Errorf("failed to close reader: %v", err)
	}

	if err := kc.producer.Close(); err != nil {
		return fmt.Errorf("failed to close producer: %v", err)
	}

	log.Println("Consumer stopped")
	return nil
}

// IsRunning returns whether the consumer is running
func (kc *KafkaConsumer) IsRunning() bool {
	kc.mu.Lock()
	defer kc.mu.Unlock()
	return kc.running
}

// parseBrokers parses broker string and returns slice of broker addresses
func parseBrokers(brokerString string) []string {
	if brokerString == "" {
		brokerString = "localhost:9092"
	}

	brokers := strings.Split(brokerString, ",")
	for i, b := range brokers {
		brokers[i] = strings.TrimSpace(b)
	}

	return brokers
}

// StartKafkaConsumer starts the Kafka consumer in a goroutine if enabled
func StartKafkaConsumer(visionService *VisionService) (*KafkaConsumer, error) {
	if os.Getenv("ENABLE_GROUP_LAYER") != "true" {
		log.Println("Group layer not enabled, skipping Kafka consumer")
		return nil, nil
	}

	groupID := os.Getenv("GROUP_ID")
	if groupID == "" {
		groupID = "jarvis-main"
	}

	agentID := os.Getenv("AGENT_ID")
	if agentID == "" {
		agentID = "visual-analyser"
	}

	brokerString := os.Getenv("KAFKA_BROKERS")
	brokers := parseBrokers(brokerString)

	log.Printf("Initializing Kafka consumer for %s in group %s", agentID, groupID)

	consumer, err := NewKafkaConsumer(brokers, groupID, agentID, visionService)
	if err != nil {
		return nil, fmt.Errorf("failed to create consumer: %v", err)
	}

	// Start consumer in a goroutine
	go func() {
		ctx := context.Background()
		if err := consumer.Start(ctx); err != nil {
			log.Printf("Consumer exited with error: %v", err)
		}
	}()

	time.Sleep(100 * time.Millisecond)
	if !consumer.IsRunning() {
		return nil, fmt.Errorf("failed to start consumer")
	}

	log.Println("Kafka consumer started successfully")
	return consumer, nil
}
