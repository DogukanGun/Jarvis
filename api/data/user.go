package data

import "time"

type User struct {
	ID          string    `json:"id"`
	Username    string    `json:"username"`
	Email       string    `json:"email"`
	ContainerID string    `json:"container_id"`
	CreatedAt   time.Time `json:"created_at"`
	LastActive  time.Time `json:"last_active"`
}
