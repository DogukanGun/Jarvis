package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"time"

	"go.mongodb.org/mongo-driver/mongo"
	"go.mongodb.org/mongo-driver/mongo/options"
)

type Database struct {
	client   *mongo.Client
	database *mongo.Database
}

func NewDatabase() (*Database, error) {
	// Get MongoDB connection string from environment
	mongoURI := os.Getenv("MONGODB_URI")
	if mongoURI == "" {
		mongoURI = "mongodb://localhost:27017" // Default local MongoDB
	}

	dbName := os.Getenv("MONGODB_DATABASE")
	if dbName == "" {
		dbName = "jarvis_api" // Default database name
	}

	// Set client options
	clientOptions := options.Client().ApplyURI(mongoURI)

	// Connect to MongoDB
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	client, err := mongo.Connect(ctx, clientOptions)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to MongoDB: %v", err)
	}

	// Ping the database to verify connection
	err = client.Ping(ctx, nil)
	if err != nil {
		return nil, fmt.Errorf("failed to ping MongoDB: %v", err)
	}

	log.Printf("Connected to MongoDB at %s", mongoURI)

	database := client.Database(dbName)

	return &Database{
		client:   client,
		database: database,
	}, nil
}

func (db *Database) Close() error {
	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()
	return db.client.Disconnect(ctx)
}

func (db *Database) GetCollection(name string) *mongo.Collection {
	return db.database.Collection(name)
}

func (db *Database) GetDatabase() *mongo.Database {
	return db.database
}
