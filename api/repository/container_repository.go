package repository

import (
	"context"
	"go.mongodb.org/mongo-driver/bson"
	"go.mongodb.org/mongo-driver/mongo"

	"jarvis/api/data"
)

type ContainerRepository struct {
	*BaseRepository[*data.ContainerInfo]
}

func NewContainerRepository(db *mongo.Database) *ContainerRepository {
	return &ContainerRepository{
		BaseRepository: NewBaseRepository[*data.ContainerInfo](db, "containers"),
	}
}

func (r *ContainerRepository) GetByUserID(ctx context.Context, userID string) ([]*data.ContainerInfo, error) {
	filter := bson.M{"userid": userID}
	return r.FindBy(ctx, filter)
}

func (r *ContainerRepository) Update(ctx context.Context, container *data.ContainerInfo) error {
	updateFields := bson.M{
		"user_id": container.UserID,
		"status":  container.Status,
		"port":    container.Port,
	}
	return r.BaseRepository.Update(ctx, container, updateFields)
}
