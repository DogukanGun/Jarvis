package base

import (
	"context"
)

// VectorStore defines the interface for vector storage and similarity search operations
type VectorStore interface {
	// Upsert inserts or updates an IP asset embedding
	// If the assetID already exists, it updates the embedding and metadata
	// If it doesn't exist, it creates a new entry
	Upsert(ctx context.Context, req *UpsertRequest) error

	// SearchNearest finds the K most similar assets to the given embedding
	// Returns assets ordered by similarity (highest first)
	SearchNearest(ctx context.Context, req *SearchRequest) (*SearchResponse, error)

	// GetByAssetID retrieves a specific asset by its ID
	GetByAssetID(ctx context.Context, assetID string) (*IPAsset, error)

	// GetByOwnerID retrieves all assets owned by a specific owner
	GetByOwnerID(ctx context.Context, ownerID string) ([]*IPAsset, error)

	// Delete removes an asset by its ID
	Delete(ctx context.Context, assetID string) error

	// Close closes the database connection
	Close() error
}
