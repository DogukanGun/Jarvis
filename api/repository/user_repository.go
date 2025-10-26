package repository

import (
	"context"
	"errors"
	"fmt"
	"time"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/bson/primitive"
	"go.mongodb.org/mongo-driver/mongo"

	"jarvis/api/data"
)

type UserRepository struct {
	collection *mongo.Collection
}

func NewUserRepository(db *mongo.Database) *UserRepository {
	return &UserRepository{
		collection: db.Collection("users"),
	}
}

func (r *UserRepository) Create(ctx context.Context, user *data.User) error {
	user.CreatedAt = time.Now()
	user.LastActive = time.Now()

	result, err := r.collection.InsertOne(ctx, user)
	if err != nil {
		return fmt.Errorf("failed to create user: %w", err)
	}

	if oid, ok := result.InsertedID.(primitive.ObjectID); ok {
		user.ID = oid.Hex()
	}

	return nil
}

func (r *UserRepository) GetByID(ctx context.Context, id string) (*data.User, error) {
	var user data.User

	filter := bson.M{"id": id}
	if oid, err := primitive.ObjectIDFromHex(id); err == nil {
		filter = bson.M{"id": oid}
	}

	err := r.collection.FindOne(ctx, filter).Decode(&user)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			return nil, fmt.Errorf("user not found")
		}
		return nil, fmt.Errorf("failed to get user: %w", err)
	}

	return &user, nil
}

func (r *UserRepository) GetByUsername(ctx context.Context, username string) (*data.User, error) {
	var user data.User

	filter := bson.M{"username": username}
	err := r.collection.FindOne(ctx, filter).Decode(&user)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			return nil, fmt.Errorf("user not found")
		}
		return nil, fmt.Errorf("failed to get user: %w", err)
	}

	return &user, nil
}

func (r *UserRepository) GetByEmail(ctx context.Context, email string) (*data.User, error) {
	var user data.User

	filter := bson.M{"email": email}
	err := r.collection.FindOne(ctx, filter).Decode(&user)
	if err != nil {
		if errors.Is(err, mongo.ErrNoDocuments) {
			return nil, fmt.Errorf("user not found")
		}
		return nil, fmt.Errorf("failed to get user: %w", err)
	}

	return &user, nil
}

func (r *UserRepository) GetByContainerID(ctx context.Context, containerID string) (*data.User, error) {
	var user data.User

	filter := bson.M{"container_id": containerID}
	err := r.collection.FindOne(ctx, filter).Decode(&user)
	if err != nil {
		if err == mongo.ErrNoDocuments {
			return nil, fmt.Errorf("user not found")
		}
		return nil, fmt.Errorf("failed to get user: %w", err)
	}

	return &user, nil
}

func (r *UserRepository) Update(ctx context.Context, user *data.User) error {
	filter := bson.M{"id": user.ID}

	update := bson.M{
		"$set": bson.M{
			"username":     user.Username,
			"email":        user.Email,
			"container_id": user.ContainerID,
			"last_active":  time.Now(),
		},
	}

	result, err := r.collection.UpdateOne(ctx, filter, update)
	if err != nil {
		return fmt.Errorf("failed to update user: %w", err)
	}

	if result.MatchedCount == 0 {
		return fmt.Errorf("user not found")
	}

	return nil
}

func (r *UserRepository) UpdateLastActive(ctx context.Context, id string) error {
	filter := bson.M{"id": id}
	if oid, err := primitive.ObjectIDFromHex(id); err == nil {
		filter = bson.M{"id": oid}
	}

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
		return fmt.Errorf("user not found")
	}

	return nil
}

func (r *UserRepository) UpdateContainerID(ctx context.Context, userID, containerID string) error {
	filter := bson.M{"id": userID}

	update := bson.M{
		"$set": bson.M{
			"container_id": containerID,
			"last_active":  time.Now(),
		},
	}

	result, err := r.collection.UpdateOne(ctx, filter, update)
	if err != nil {
		return fmt.Errorf("failed to update container ID: %w", err)
	}

	if result.MatchedCount == 0 {
		return fmt.Errorf("user not found")
	}

	return nil
}

func (r *UserRepository) Delete(ctx context.Context, id string) error {
	filter := bson.M{"id": id}
	if oid, err := primitive.ObjectIDFromHex(id); err == nil {
		filter = bson.M{"id": oid}
	}

	result, err := r.collection.DeleteOne(ctx, filter)
	if err != nil {
		return fmt.Errorf("failed to delete user: %w", err)
	}

	if result.DeletedCount == 0 {
		return fmt.Errorf("user not found")
	}

	return nil
}

func (r *UserRepository) GetAll(ctx context.Context) ([]*data.User, error) {
	var users []*data.User

	cursor, err := r.collection.Find(ctx, bson.M{})
	if err != nil {
		return nil, fmt.Errorf("failed to find users: %w", err)
	}
	defer cursor.Close(ctx)

	for cursor.Next(ctx) {
		var user data.User
		if err := cursor.Decode(&user); err != nil {
			return nil, fmt.Errorf("failed to decode user: %w", err)
		}
		users = append(users, &user)
	}

	if err := cursor.Err(); err != nil {
		return nil, fmt.Errorf("cursor error: %w", err)
	}

	return users, nil
}
