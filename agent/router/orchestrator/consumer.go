package orchestrator

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

	"github.com/segmentio/kafka-go"
	"jarvis/agent/schemas/group"
)

// Consumer consumes events from Kafka topics
type Consumer struct {
	reader           *kafka.Reader
	processor        *EventProcessor
	stateManager     *StateManager
	groupID          string
	mu               sync.Mutex
	running          bool
	approvalCheckTicker *time.Ticker
}

// NewConsumer creates a new consumer
func NewConsumer(brokers []string, groupID string, processor *EventProcessor, stateManager *StateManager) (*Consumer, error) {
	// Subscribe to both events and commands topics
	topics := []string{
		group.EventsTopic(groupID),
		group.CommandsTopic(groupID),
	}

	reader := kafka.NewReader(kafka.ReaderConfig{
		Brokers:        brokers,
		Topic:          topics[0], // Start with events topic
		GroupID:        fmt.Sprintf("orchestrator-%s", groupID),
		StartOffset:    kafka.LastOffset,
		CommitInterval: time.Second,
		SessionTimeout: 10 * time.Second,
		MaxBytes:       1024 * 1024, // 1MB
		QueueCapacity:  100,
	})

	return &Consumer{
		reader:       reader,
		processor:    processor,
		stateManager: stateManager,
		groupID:      groupID,
		running:      false,
	}, nil
}

// Start starts the consumer loop
func (c *Consumer) Start(ctx context.Context) error {
	c.mu.Lock()
	if c.running {
		c.mu.Unlock()
		return fmt.Errorf("consumer already running")
	}
	c.running = true
	c.mu.Unlock()

	// Start approval timeout check ticker
	c.approvalCheckTicker = time.NewTicker(30 * time.Second)

	// Setup signal handling
	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan, syscall.SIGINT, syscall.SIGTERM)

	// Start approval timeout check loop
	go c.approvalTimeoutLoop(ctx)

	log.Printf("Starting orchestrator consumer for group: %s", c.groupID)

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-sigChan:
			log.Println("Received shutdown signal, stopping consumer...")
			return c.Stop()
		default:
		}

		// Read message with timeout
		msgCtx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
		msg, err := c.reader.ReadMessage(msgCtx)
		cancel()

		if err != nil {
			if err == context.DeadlineExceeded {
				// Timeout is normal, continue
				continue
			}
			log.Printf("Error reading message: %v", err)
			continue
		}

		// Process message
		if err := c.processMessage(ctx, msg); err != nil {
			log.Printf("Error processing message: %v", err)
			// Don't stop consumer on processing error
		}
	}
}

// processMessage processes a single Kafka message
func (c *Consumer) processMessage(ctx context.Context, msg kafka.Message) error {
	var envelope group.Envelope

	if err := json.Unmarshal(msg.Value, &envelope); err != nil {
		return fmt.Errorf("failed to unmarshal envelope: %v", err)
	}

	// Validate envelope
	if err := group.ValidateEnvelope(&envelope); err != nil {
		return fmt.Errorf("invalid envelope: %v", err)
	}

	// Check group matches
	if envelope.GroupID != c.groupID {
		return fmt.Errorf("envelope group_id mismatch: expected %s, got %s", c.groupID, envelope.GroupID)
	}

	// Process the envelope
	procCtx, cancel := context.WithTimeout(ctx, 30*time.Second)
	defer cancel()

	return c.processor.ProcessEnvelope(procCtx, &envelope)
}

// approvalTimeoutLoop periodically checks for expired approvals
func (c *Consumer) approvalTimeoutLoop(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case <-c.approvalCheckTicker.C:
			procCtx, cancel := context.WithTimeout(ctx, 10*time.Second)
			if err := c.processor.ProcessApprovalTimeouts(procCtx); err != nil {
				log.Printf("Error processing approval timeouts: %v", err)
			}
			cancel()
		}
	}
}

// Stop stops the consumer
func (c *Consumer) Stop() error {
	c.mu.Lock()
	defer c.mu.Unlock()

	if !c.running {
		return fmt.Errorf("consumer not running")
	}

	c.running = false

	if c.approvalCheckTicker != nil {
		c.approvalCheckTicker.Stop()
	}

	if err := c.reader.Close(); err != nil {
		return fmt.Errorf("failed to close reader: %v", err)
	}

	log.Println("Consumer stopped")
	return nil
}

// IsRunning returns whether the consumer is running
func (c *Consumer) IsRunning() bool {
	c.mu.Lock()
	defer c.mu.Unlock()
	return c.running
}

// GetConsumerLag returns the current consumer lag (simplified)
func (c *Consumer) GetConsumerLag() (int64, error) {
	// Note: kafka-go reader doesn't expose per-partition stats in newer versions
	// Return 0 for now as placeholder
	return 0, nil
}

// GetReaderStats returns consumer statistics
func (c *Consumer) GetReaderStats() kafka.ReaderStats {
	return c.reader.Stats()
}

// ConsumerManager manages orchestrator consumer lifecycle
type ConsumerManager struct {
	consumer *Consumer
	ctx      context.Context
	cancel   context.CancelFunc
}

// NewConsumerManager creates a new consumer manager
func NewConsumerManager(brokers []string, groupID string, processor *EventProcessor, stateManager *StateManager) (*ConsumerManager, error) {
	consumer, err := NewConsumer(brokers, groupID, processor, stateManager)
	if err != nil {
		return nil, fmt.Errorf("failed to create consumer: %v", err)
	}

	return &ConsumerManager{
		consumer: consumer,
	}, nil
}

// Start starts the consumer in a background goroutine
func (cm *ConsumerManager) Start() error {
	cm.ctx, cm.cancel = context.WithCancel(context.Background())

	go func() {
		if err := cm.consumer.Start(cm.ctx); err != nil {
			log.Printf("Consumer exited with error: %v", err)
		}
	}()

	// Give it time to start
	time.Sleep(100 * time.Millisecond)

	if !cm.consumer.IsRunning() {
		return fmt.Errorf("failed to start consumer")
	}

	log.Println("Consumer started successfully")
	return nil
}

// Stop stops the consumer
func (cm *ConsumerManager) Stop() error {
	if cm.cancel != nil {
		cm.cancel()
	}

	if err := cm.consumer.Stop(); err != nil {
		return err
	}

	return nil
}

// GetStatus returns the current consumer status
func (cm *ConsumerManager) GetStatus() map[string]interface{} {
	stats := cm.consumer.GetReaderStats()
	lag, _ := cm.consumer.GetConsumerLag()

	status := map[string]interface{}{
		"running":            cm.consumer.IsRunning(),
		"messages":           stats.Messages,
		"bytes":              stats.Bytes,
		"rebalances":         stats.Rebalances,
		"timeouts":           stats.Timeouts,
		"errors":             stats.Errors,
		"lag":                lag,
		"group_id":           cm.consumer.groupID,
		"topics":             []string{group.EventsTopic(cm.consumer.groupID), group.CommandsTopic(cm.consumer.groupID)},
	}

	return status
}

// ParseBrokers parses broker string and returns slice of broker addresses
func ParseBrokers(brokerString string) []string {
	if brokerString == "" {
		brokerString = "localhost:9092"
	}

	// Split by comma and trim spaces
	brokers := strings.Split(brokerString, ",")
	for i, b := range brokers {
		brokers[i] = strings.TrimSpace(b)
	}

	return brokers
}
