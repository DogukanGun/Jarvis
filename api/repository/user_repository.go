package repository

import (
	"context"

	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"

	"jarvis/api/data"
)

type UserRepository struct {
	*BaseRepository[*data.User]
}

func NewUserRepository(db *mongo.Database) *UserRepository {
	return &UserRepository{
		BaseRepository: NewBaseRepository[*data.User](db, "users"),
	}
}

func (r *UserRepository) GetByUsername(ctx context.Context, username string) (*data.User, error) {
	filter := bson.M{"username": username}
	return r.FindOneBy(ctx, filter)
}

func (r *UserRepository) GetByEmail(ctx context.Context, email string) (*data.User, error) {
	filter := bson.M{"email": email}
	return r.FindOneBy(ctx, filter)
}

func (r *UserRepository) GetByWalletAddress(ctx context.Context, walletAddress string) (*data.User, error) {
	filter := bson.M{"wallet_address": walletAddress}
	return r.FindOneBy(ctx, filter)
}

func (r *UserRepository) GetByContainerID(ctx context.Context, containerID string) (*data.User, error) {
	filter := bson.M{"container_id": containerID}
	return r.FindOneBy(ctx, filter)
}

func (r *UserRepository) Update(ctx context.Context, user *data.User) error {
	updateFields := bson.M{
		"username":     user.Username,
		"email":        user.Email,
		"container_id": user.ContainerID,
	}
	return r.BaseRepository.Update(ctx, user, updateFields)
}

func (r *UserRepository) UpdateContainerID(ctx context.Context, userID, containerID string) error {
	user := &data.User{ID: userID}
	updateFields := bson.M{
		"container_id": containerID,
	}
	return r.BaseRepository.Update(ctx, user, updateFields)
}
