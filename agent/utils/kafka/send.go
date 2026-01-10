package kafka

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/segmentio/kafka-go"
)

// Producer wraps a Kafka writer
type Producer struct {
	writer *kafka.Writer
}

// NewProducer creates a new Kafka producer
func NewProducer(topic string) (*Producer, error) {
	brokers := os.Getenv("KAFKA_BROKERS")
	if brokers == "" {
		brokers = "localhost:9092"
	}

	writer := &kafka.Writer{
		Addr:     kafka.TCP(brokers),
		Topic:    topic,
		Balancer: &kafka.LeastBytes{},
	}

	return &Producer{
		writer: writer,
	}, nil
}

// SendMessage sends a message to the configured topic
func (p *Producer) SendMessage(ctx context.Context, message AgentMessage) error {
	messageBytes, err := json.Marshal(message)
	if err != nil {
		return fmt.Errorf("failed to marshal message: %v", err)
	}

	kafkaMessage := kafka.Message{
		Key:   []byte(message.ID),
		Value: messageBytes,
		Time:  time.Now(),
	}

	err = p.writer.WriteMessages(ctx, kafkaMessage)
	if err != nil {
		return fmt.Errorf("failed to write message: %v", err)
	}

	log.Printf("Message sent to topic %s: %s", p.writer.Topic, message.ID)
	return nil
}

// Close closes the producer
func (p *Producer) Close() error {
	return p.writer.Close()
}

// SendToCoderAgent sends a message to the coder agent
func SendToCoderAgent(ctx context.Context, message AgentMessage) error {
	producer, err := NewProducer(CoderAgentTopic)
	if err != nil {
		return fmt.Errorf("failed to create coder producer: %v", err)
	}
	defer producer.Close()

	return producer.SendMessage(ctx, message)
}

// SendToGeneralAgent sends a message to the general agent
func SendToGeneralAgent(ctx context.Context, message AgentMessage) error {
	producer, err := NewProducer(GeneralAgentTopic)
	if err != nil {
		return fmt.Errorf("failed to create general producer: %v", err)
	}
	defer producer.Close()

	return producer.SendMessage(ctx, message)
}

// SendToVisualAnalyser sends a message to the visual analyser agent
func SendToVisualAnalyser(ctx context.Context, message AgentMessage) error {
	producer, err := NewProducer(VisualAnalyserAgentTopic)
	if err != nil {
		return fmt.Errorf("failed to create visual analyser producer: %v", err)
	}
	defer producer.Close()

	return producer.SendMessage(ctx, message)
}

// SendToGUIAgent sends a message to the GUI agent
func SendToGUIAgent(ctx context.Context, message AgentMessage) error {
	producer, err := NewProducer(GUIAgentTopic)
	if err != nil {
		return fmt.Errorf("failed to create GUI agent producer: %v", err)
	}
	defer producer.Close()

	return producer.SendMessage(ctx, message)
}

// SendIPRegistrationRequest sends a message to the IP agent for registration
func SendIPRegistrationRequest(ctx context.Context, message IPRegistrationMessage) error {
	producer, err := NewProducer(IPRegistrationTopic)
	if err != nil {
		return fmt.Errorf("failed to create IP registration producer: %v", err)
	}
	defer producer.Close()

	// Marshal message
	messageBytes, err := json.Marshal(message)
	if err != nil {
		return fmt.Errorf("failed to marshal IP registration message: %v", err)
	}

	kafkaMessage := kafka.Message{
		Key:   []byte(message.ID),
		Value: messageBytes,
		Time:  time.Now(),
	}

	err = producer.writer.WriteMessages(ctx, kafkaMessage)
	if err != nil {
		return fmt.Errorf("failed to write IP registration message: %v", err)
	}

	log.Printf("IP registration request sent to topic %s: %s", IPRegistrationTopic, message.ID)
	return nil
}
