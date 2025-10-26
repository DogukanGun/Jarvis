package main

import (
	"context"
	"fmt"
	"strings"
	"time"

	"github.com/neo4j/neo4j-go-driver/v5/neo4j"
)

// KnowledgeGraph manages the Neo4j knowledge graph for user personalization and memory
type KnowledgeGraph struct {
	driver neo4j.DriverWithContext
	userID string
}

// KnowledgeEntity represents a knowledge entity in the graph
type KnowledgeEntity struct {
	ID         string            `json:"id"`
	Type       string            `json:"type"`
	Properties map[string]string `json:"properties"`
}

// Relationship represents a relationship between entities
type Relationship struct {
	From       string            `json:"from"`
	To         string            `json:"to"`
	Type       string            `json:"type"`
	Properties map[string]string `json:"properties"`
}

// Memory represents a conversation memory or interaction
type Memory struct {
	ID        string    `json:"id"`
	UserID    string    `json:"user_id"`
	Content   string    `json:"content"`
	Type      string    `json:"type"` // "message", "action", "preference", etc.
	Timestamp time.Time `json:"timestamp"`
	Context   string    `json:"context"`
}

// NewKnowledgeGraph creates a new knowledge graph manager
func NewKnowledgeGraph(uri, username, password, userID string) (*KnowledgeGraph, error) {
	driver, err := neo4j.NewDriverWithContext(uri, neo4j.BasicAuth(username, password, ""))
	if err != nil {
		return nil, fmt.Errorf("failed to create Neo4j driver: %v", err)
	}

	kg := &KnowledgeGraph{
		driver: driver,
		userID: userID,
	}

	// Initialize user-specific graph structure
	if err := kg.initializeUserGraph(); err != nil {
		return nil, fmt.Errorf("failed to initialize user graph: %v", err)
	}

	return kg, nil
}

// Close closes the Neo4j driver
func (kg *KnowledgeGraph) Close() error {
	return kg.driver.Close(context.Background())
}

// initializeUserGraph creates the initial graph structure for a user
func (kg *KnowledgeGraph) initializeUserGraph() error {
	ctx := context.Background()
	session := kg.driver.NewSession(ctx, neo4j.SessionConfig{})
	defer session.Close(ctx)

	// Create user node if it doesn't exist
	query := `
		MERGE (u:User {id: $userID})
		ON CREATE SET u.created_at = datetime(), u.name = $userID
		RETURN u.id as userId
	`

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		result, err := tx.Run(ctx, query, map[string]any{
			"userID": kg.userID,
		})
		if err != nil {
			return nil, err
		}
		return result.Collect(ctx)
	})

	return err
}

// AddMemory adds a new memory/interaction to the knowledge graph
func (kg *KnowledgeGraph) AddMemory(memory Memory) error {
	ctx := context.Background()
	session := kg.driver.NewSession(ctx, neo4j.SessionConfig{})
	defer session.Close(ctx)

	query := `
		MATCH (u:User {id: $userID})
		CREATE (m:Memory {
			id: $memoryID,
			content: $content,
			type: $type,
			timestamp: datetime($timestamp),
			context: $context
		})
		CREATE (u)-[:HAS_MEMORY]->(m)
		RETURN m.id as memoryId
	`

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		result, err := tx.Run(ctx, query, map[string]any{
			"userID":    kg.userID,
			"memoryID":  memory.ID,
			"content":   memory.Content,
			"type":      memory.Type,
			"timestamp": memory.Timestamp.Format(time.RFC3339),
			"context":   memory.Context,
		})
		if err != nil {
			return nil, err
		}
		return result.Collect(ctx)
	})

	return err
}

// AddEntity adds a knowledge entity to the graph
func (kg *KnowledgeGraph) AddEntity(entity KnowledgeEntity) error {
	ctx := context.Background()
	session := kg.driver.NewSession(ctx, neo4j.SessionConfig{})
	defer session.Close(ctx)

	// Build properties string for Cypher query
	propsStr := ""
	props := map[string]any{
		"userID":   kg.userID,
		"entityID": entity.ID,
		"type":     entity.Type,
	}

	for key, value := range entity.Properties {
		propsStr += fmt.Sprintf(", %s: $prop_%s", key, key)
		props[fmt.Sprintf("prop_%s", key)] = value
	}

	query := fmt.Sprintf(`
		MATCH (u:User {id: $userID})
		MERGE (e:Entity {id: $entityID, type: $type%s})
		MERGE (u)-[:KNOWS]->(e)
		RETURN e.id as entityId
	`, propsStr)

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		result, err := tx.Run(ctx, query, props)
		if err != nil {
			return nil, err
		}
		return result.Collect(ctx)
	})

	return err
}

// AddRelationship creates a relationship between entities
func (kg *KnowledgeGraph) AddRelationship(rel Relationship) error {
	ctx := context.Background()
	session := kg.driver.NewSession(ctx, neo4j.SessionConfig{})
	defer session.Close(ctx)

	// Build properties string for relationship
	propsStr := ""
	props := map[string]any{
		"userID": kg.userID,
		"fromID": rel.From,
		"toID":   rel.To,
		"type":   rel.Type,
	}

	for key, value := range rel.Properties {
		propsStr += fmt.Sprintf(", %s: $prop_%s", key, key)
		props[fmt.Sprintf("prop_%s", key)] = value
	}

	query := fmt.Sprintf(`
		MATCH (u:User {id: $userID})-[:KNOWS]->(from:Entity {id: $fromID})
		MATCH (u)-[:KNOWS]->(to:Entity {id: $toID})
		MERGE (from)-[r:%s {%s}]->(to)
		RETURN type(r) as relType
	`, rel.Type, strings.TrimPrefix(propsStr, ", "))

	_, err := session.ExecuteWrite(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		result, err := tx.Run(ctx, query, props)
		if err != nil {
			return nil, err
		}
		return result.Collect(ctx)
	})

	return err
}

// GetUserContext retrieves relevant context for the user based on current input
func (kg *KnowledgeGraph) GetUserContext(query string, limit int) (string, error) {
	ctx := context.Background()
	session := kg.driver.NewSession(ctx, neo4j.SessionConfig{})
	defer session.Close(ctx)

	// Get recent memories and related entities
	cypher := `
		MATCH (u:User {id: $userID})-[:HAS_MEMORY]->(m:Memory)
		WHERE m.content CONTAINS $query OR m.context CONTAINS $query
		RETURN m.content as content, m.type as type, m.timestamp as timestamp, m.context as context
		ORDER BY m.timestamp DESC
		LIMIT $limit
		UNION
		MATCH (u:User {id: $userID})-[:KNOWS]->(e:Entity)
		WHERE any(prop in keys(e) WHERE toString(e[prop]) CONTAINS $query)
		RETURN e.id as content, e.type as type, null as timestamp, 'entity' as context
		LIMIT $limit
	`

	result, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		result, err := tx.Run(ctx, cypher, map[string]any{
			"userID": kg.userID,
			"query":  query,
			"limit":  limit,
		})
		if err != nil {
			return nil, err
		}
		return result.Collect(ctx)
	})

	if err != nil {
		return "", err
	}

	records := result.([]*neo4j.Record)
	var contextParts []string

	for _, record := range records {
		content, _ := record.Get("content")
		recordType, _ := record.Get("type")
		context, _ := record.Get("context")

		contextParts = append(contextParts, fmt.Sprintf("[%s] %s (context: %s)",
			recordType, content, context))
	}

	if len(contextParts) == 0 {
		return "", nil
	}

	return "Relevant user context:\n" + strings.Join(contextParts, "\n"), nil
}

// GetUserPreferences retrieves user preferences and patterns
func (kg *KnowledgeGraph) GetUserPreferences() (map[string]string, error) {
	ctx := context.Background()
	session := kg.driver.NewSession(ctx, neo4j.SessionConfig{})
	defer session.Close(ctx)

	cypher := `
		MATCH (u:User {id: $userID})-[:HAS_MEMORY]->(m:Memory {type: 'preference'})
		RETURN m.content as preference, m.context as context
		UNION
		MATCH (u:User {id: $userID})-[:KNOWS]->(e:Entity {type: 'preference'})
		RETURN e.id as preference, coalesce(e.value, e.description) as context
	`

	result, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		result, err := tx.Run(ctx, cypher, map[string]any{
			"userID": kg.userID,
		})
		if err != nil {
			return nil, err
		}
		return result.Collect(ctx)
	})

	if err != nil {
		return nil, err
	}

	records := result.([]*neo4j.Record)
	preferences := make(map[string]string)

	for _, record := range records {
		pref, _ := record.Get("preference")
		context, _ := record.Get("context")
		if pref != nil && context != nil {
			preferences[pref.(string)] = context.(string)
		}
	}

	return preferences, nil
}

// UpdateUserPreference adds or updates a user preference
func (kg *KnowledgeGraph) UpdateUserPreference(key, value, context string) error {
	entity := KnowledgeEntity{
		ID:   fmt.Sprintf("pref_%s", key),
		Type: "preference",
		Properties: map[string]string{
			"key":         key,
			"value":       value,
			"description": context,
		},
	}

	return kg.AddEntity(entity)
}

// GetRecentInteractions gets the most recent user interactions for context
func (kg *KnowledgeGraph) GetRecentInteractions(limit int) ([]Memory, error) {
	ctx := context.Background()
	session := kg.driver.NewSession(ctx, neo4j.SessionConfig{})
	defer session.Close(ctx)

	cypher := `
		MATCH (u:User {id: $userID})-[:HAS_MEMORY]->(m:Memory)
		RETURN m.id as id, m.content as content, m.type as type, m.timestamp as timestamp, m.context as context
		ORDER BY m.timestamp DESC
		LIMIT $limit
	`

	result, err := session.ExecuteRead(ctx, func(tx neo4j.ManagedTransaction) (any, error) {
		result, err := tx.Run(ctx, cypher, map[string]any{
			"userID": kg.userID,
			"limit":  limit,
		})
		if err != nil {
			return nil, err
		}
		return result.Collect(ctx)
	})

	if err != nil {
		return nil, err
	}

	records := result.([]*neo4j.Record)
	var memories []Memory

	for _, record := range records {
		id, _ := record.Get("id")
		content, _ := record.Get("content")
		recordType, _ := record.Get("type")
		timestampStr, _ := record.Get("timestamp")
		context, _ := record.Get("context")

		timestamp, _ := time.Parse(time.RFC3339, timestampStr.(string))

		memories = append(memories, Memory{
			ID:        id.(string),
			UserID:    kg.userID,
			Content:   content.(string),
			Type:      recordType.(string),
			Timestamp: timestamp,
			Context:   context.(string),
		})
	}

	return memories, nil
}
