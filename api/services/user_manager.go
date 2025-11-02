package services

import (
	"context"
	"jarvis/api/data"
	"jarvis/api/repository"
)

type UserManager struct {
	repository *repository.UserRepository
}

func NewUserManager(repo *repository.UserRepository) *UserManager {
	return &UserManager{
		repository: repo,
	}
}

// AddUser adds a new user to the system
func (um *UserManager) AddUser(user *data.User) error {
	ctx := context.Background()
	return um.repository.Create(ctx, user)
}

// GetUser retrieves a user by ID
func (um *UserManager) GetUser(userID string) (*data.User, error) {
	ctx := context.Background()
	return um.repository.GetByID(ctx, userID)
}

// GetUserByUsername retrieves a user by username
func (um *UserManager) GetUserByUsername(username string) (*data.User, error) {
	ctx := context.Background()
	return um.repository.GetByUsername(ctx, username)
}

// GetUserByEmail retrieves a user by email
func (um *UserManager) GetUserByEmail(email string) (*data.User, error) {
	ctx := context.Background()
	return um.repository.GetByEmail(ctx, email)
}

// GetUserByWalletAddress retrieves a user by wallet address
func (um *UserManager) GetUserByWalletAddress(walletAddress string) (*data.User, error) {
	ctx := context.Background()
	return um.repository.GetByWalletAddress(ctx, walletAddress)
}

// GetUserByContainerID retrieves a user by container ID
func (um *UserManager) GetUserByContainerID(containerID string) (*data.User, error) {
	ctx := context.Background()
	return um.repository.GetByContainerID(ctx, containerID)
}

// UserExists checks if a user exists by username
func (um *UserManager) UserExists(username string) bool {
	ctx := context.Background()
	_, err := um.repository.GetByUsername(ctx, username)
	return err == nil
}

// UpdateLastActive updates the user's last active timestamp
func (um *UserManager) UpdateLastActive(userID string) error {
	ctx := context.Background()
	return um.repository.UpdateLastActive(ctx, userID)
}

// UpdateUser updates user information
func (um *UserManager) UpdateUser(user *data.User) error {
	ctx := context.Background()
	return um.repository.Update(ctx, user)
}

// UpdateContainerID updates the user's container ID
func (um *UserManager) UpdateContainerID(userID, containerID string) error {
	ctx := context.Background()
	return um.repository.UpdateContainerID(ctx, userID, containerID)
}

// ListUsers returns all users (without sensitive data)
func (um *UserManager) ListUsers() ([]*data.User, error) {
	ctx := context.Background()
	users, err := um.repository.GetAll(ctx)
	if err != nil {
		return nil, err
	}

	// Create copies without sensitive data if needed
	publicUsers := make([]*data.User, len(users))
	for i, user := range users {
		publicUsers[i] = &data.User{
			ID:          user.ID,
			Username:    user.Username,
			Email:       user.Email,
			ContainerID: user.ContainerID,
			CreatedAt:   user.CreatedAt,
			LastActive:  user.LastActive,
		}
	}

	return publicUsers, nil
}

// RemoveUser removes a user from the system
func (um *UserManager) RemoveUser(userID string) error {
	ctx := context.Background()
	return um.repository.Delete(ctx, userID)
}
