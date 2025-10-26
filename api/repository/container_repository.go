package repository

import (
	"context"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"

	"jarvis/api/data"
)

type ContainerRepository struct {
	collection *mongo.Collection
}

func NewContainerRepository(db *mongo.Database) *ContainerRepository {
	return &ContainerRepository{
		collection: db.Collection("containers"),
	}
}

func (r *ContainerRepository) Create(ctx context.Context, container *data.ContainerInfo) error {
	container.Created = time.Now()
	container.LastUsed = time.Now()

	result, err := r.collection.InsertOne(ctx, container)
	if err != nil {
		return fmt.Errorf("failed to create container: %w", err)
	}

	if oid, ok := result.InsertedID.(primitive.ObjectID); ok {
		container.ID = oid.Hex()
	}

	return nil
}

func (r *ContainerRepository) GetByID(ctx context.Context, id string) (*data.ContainerInfo, error) {
	var container data.ContainerInfo

	filter := bson.M{"id": id}

	err := r.collection.FindOne(ctx, filter).Decode(&container)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			return nil, fmt.Errorf("container not found")
		}
		return nil, fmt.Errorf("failed to get container: %w", err)
	}

	return &container, nil
}

func (r *ContainerRepository) GetByUserID(ctx context.Context, userID string) ([]*data.ContainerInfo, error) {
	var containers []*data.ContainerInfo

	filter := bson.M{"userid": userID}
	cursor, err := r.collection.Find(ctx, filter)
	if err != nil {
		return nil, fmt.Errorf("failed to find containers: %w", err)
	}
	defer cursor.Close(ctx)

	for cursor.Next(ctx) {
		var container data.ContainerInfo
		if err := cursor.Decode(&container); err != nil {
			return nil, fmt.Errorf("failed to decode container: %w", err)
		}
		containers = append(containers, &container)
	}

	if err := cursor.Err(); err != nil {
		return nil, fmt.Errorf("cursor error: %w", err)
	}

	return containers, nil
}

func (r *ContainerRepository) Update(ctx context.Context, container *data.ContainerInfo) error {
	filter := bson.M{"id": container.ID}

	update := bson.M{
		"$set": bson.M{
			"user_id":   container.UserID,
			"status":    container.Status,
			"port":      container.Port,
			"last_used": time.Now(),
		},
	}

	result, err := r.collection.UpdateOne(ctx, filter, update)
	if err != nil {
		return fmt.Errorf("failed to update container: %w", err)
	}

	if result.MatchedCount == 0 {
		return fmt.Errorf("container not found")
	}

	return nil
}

func (r *ContainerRepository) UpdateLastUsed(ctx context.Context, id string) error {
	filter := bson.M{"id": id}

	update := bson.M{
		"$set": bson.M{
			"last_used": time.Now(),
		},
	}

	result, err := r.collection.UpdateOne(ctx, filter, update)
	if err != nil {
		return fmt.Errorf("failed to update last used: %w", err)
	}

	if result.MatchedCount == 0 {
		return fmt.Errorf("container not found")
	}

	return nil
}

func (r *ContainerRepository) Delete(ctx context.Context, id string) error {
	filter := bson.M{"id": id}

	result, err := r.collection.DeleteOne(ctx, filter)
	if err != nil {
		return fmt.Errorf("failed to delete container: %w", err)
	}

	if result.DeletedCount == 0 {
		return fmt.Errorf("container not found")
	}

	return nil
}

func (r *ContainerRepository) GetAll(ctx context.Context) ([]*data.ContainerInfo, error) {
	var containers []*data.ContainerInfo

	cursor, err := r.collection.Find(ctx, bson.M{})
	if err != nil {
		return nil, fmt.Errorf("failed to find containers: %w", err)
	}
	defer cursor.Close(ctx)

	for cursor.Next(ctx) {
		var container data.ContainerInfo
		if err := cursor.Decode(&container); err != nil {
			return nil, fmt.Errorf("failed to decode container: %w", err)
		}
		containers = append(containers, &container)
	}

	if err := cursor.Err(); err != nil {
		return nil, fmt.Errorf("cursor error: %w", err)
	}

	return containers, nil
}
