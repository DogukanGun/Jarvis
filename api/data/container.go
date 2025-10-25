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
