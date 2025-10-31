package repository

import (
	"context"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"
)

type Entity interface {
	GetID() string
	SetID(id string)
	SetCreatedAt(t time.Time)
	SetLastActive(t time.Time)
}

type BaseRepository[T Entity] struct {
	collection *mongo.Collection
}

func NewBaseRepository[T Entity](db *mongo.Database, collectionName string) *BaseRepository[T] {
	return &BaseRepository[T]{
		collection: db.Collection(collectionName),
	}
}

func (r *BaseRepository[T]) Create(ctx context.Context, entity T) error {
	entity.SetCreatedAt(time.Now())
	entity.SetLastActive(time.Now())

	result, err := r.collection.InsertOne(ctx, entity)
	if err != nil {
		return fmt.Errorf("failed to create entity: %w", err)
	}

	if oid, ok := result.InsertedID.(primitive.ObjectID); ok {
		entity.SetID(oid.Hex())
	}

	return nil
}

func (r *BaseRepository[T]) GetByID(ctx context.Context, id string) (T, error) {
	var entity T

	filter := r.buildIDFilter(id)

	err := r.collection.FindOne(ctx, filter).Decode(&entity)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			return entity, fmt.Errorf("entity not found")
		}
		return entity, fmt.Errorf("failed to get entity: %w", err)
	}

	return entity, nil
}

func (r *BaseRepository[T]) Update(ctx context.Context, entity T, updateFields bson.M) error {
	filter := bson.M{"id": entity.GetID()}

	updateFields["last_active"] = time.Now()
	update := bson.M{"$set": updateFields}

	result, err := r.collection.UpdateOne(ctx, filter, update)
	if err != nil {
		return fmt.Errorf("failed to update entity: %w", err)
	}

	if result.MatchedCount == 0 {
		return fmt.Errorf("entity not found")
	}

	return nil
}

func (r *BaseRepository[T]) UpdateLastActive(ctx context.Context, id string) error {
	filter := r.buildIDFilter(id)

	update := bson.M{
		"$set": bson.M{
			"last_active": time.Now(),
		},
	}

	result, err := r.collection.UpdateOne(ctx, filter, update)
	if err != nil {
		return fmt.Errorf("failed to update last active: %w", err)
	}

	if result.MatchedCount == 0 {
		return fmt.Errorf("entity not found")
	}

	return nil
}

func (r *BaseRepository[T]) Delete(ctx context.Context, id string) error {
	filter := r.buildIDFilter(id)

	result, err := r.collection.DeleteOne(ctx, filter)
	if err != nil {
		return fmt.Errorf("failed to delete entity: %w", err)
	}

	if result.DeletedCount == 0 {
		return fmt.Errorf("entity not found")
	}

	return nil
}

func (r *BaseRepository[T]) GetAll(ctx context.Context) ([]T, error) {
	var entities []T

	cursor, err := r.collection.Find(ctx, bson.M{})
	if err != nil {
		return nil, fmt.Errorf("failed to find entities: %w", err)
	}
	defer cursor.Close(ctx)

	for cursor.Next(ctx) {
		var entity T
		if err := cursor.Decode(&entity); err != nil {
			return nil, fmt.Errorf("failed to decode entity: %w", err)
		}
		entities = append(entities, entity)
	}

	if err := cursor.Err(); err != nil {
		return nil, fmt.Errorf("cursor error: %w", err)
	}

	return entities, nil
}

func (r *BaseRepository[T]) FindBy(ctx context.Context, filter bson.M) ([]T, error) {
	var entities []T

	cursor, err := r.collection.Find(ctx, filter)
	if err != nil {
		return nil, fmt.Errorf("failed to find entities: %w", err)
	}
	defer cursor.Close(ctx)

	for cursor.Next(ctx) {
		var entity T
		if err := cursor.Decode(&entity); err != nil {
			return nil, fmt.Errorf("failed to decode entity: %w", err)
		}
		entities = append(entities, entity)
	}

	if err := cursor.Err(); err != nil {
		return nil, fmt.Errorf("cursor error: %w", err)
	}

	return entities, nil
}

func (r *BaseRepository[T]) FindOneBy(ctx context.Context, filter bson.M) (T, error) {
	var entity T

	err := r.collection.FindOne(ctx, filter).Decode(&entity)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			return entity, fmt.Errorf("entity not found")
		}
		return entity, fmt.Errorf("failed to get entity: %w", err)
	}

	return entity, nil
}

func (r *BaseRepository[T]) buildIDFilter(id string) bson.M {
	filter := bson.M{"id": id}
	if oid, err := primitive.ObjectIDFromHex(id); err == nil {
		filter = bson.M{"id": oid}
	}
	return filter
}
