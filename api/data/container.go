package data

import "time"

type ContainerInfo struct {
	ID       string    `json:"id"`
	UserID   string    `json:"user_id"`
	Status   string    `json:"status"`
	Port     int       `json:"port"`
	Created  time.Time `json:"created"`
	LastUsed time.Time `json:"last_used"`
}

func (c *ContainerInfo) GetID() string {
	return c.ID
}

func (c *ContainerInfo) SetID(id string) {
	c.ID = id
}

func (c *ContainerInfo) SetCreatedAt(t time.Time) {
	c.Created = t
}

func (c *ContainerInfo) SetLastActive(t time.Time) {
	c.LastUsed = t
}
