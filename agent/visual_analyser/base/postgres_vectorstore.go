package base

import (
	"context"
	"fmt"
	"math"

	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
	"github.com/pgvector/pgvector-go"
)

// PostgresVectorStore implements VectorStore using PostgreSQL + pgvector
type PostgresVectorStore struct {
	pool *pgxpool.Pool
}

// NewPostgresVectorStore creates a new PostgreSQL vector store
func NewPostgresVectorStore(ctx context.Context, connString string) (*PostgresVectorStore, error) {
	config, err := pgxpool.ParseConfig(connString)
	if err != nil {
		return nil, fmt.Errorf("failed to parse connection string: %w", err)
	}

	pool, err := pgxpool.NewWithConfig(ctx, config)
	if err != nil {
		return nil, fmt.Errorf("failed to create connection pool: %w", err)
	}

	// Test connection
	if err := pool.Ping(ctx); err != nil {
		return nil, fmt.Errorf("failed to ping database: %w", err)
	}

	return &PostgresVectorStore{
		pool: pool,
	}, nil
}

// Upsert inserts or updates an IP asset embedding
func (s *PostgresVectorStore) Upsert(ctx context.Context, req *UpsertRequest) error {
	// Validate input
	if req.AssetID == "" {
		return fmt.Errorf("asset_id cannot be empty")
	}
	if req.OwnerID == "" {
		return fmt.Errorf("owner_id cannot be empty")
	}
	if len(req.Embedding) == 0 {
		return fmt.Errorf("embedding cannot be empty")
	}

	// Convert embedding to pgvector
	vec := pgvector.NewVector(req.Embedding)

	// Convert metadata to JSON
	metadataJSON, err := MetadataToJSON(req.Metadata)
	if err != nil {
		return fmt.Errorf("failed to marshal metadata: %w", err)
	}

	// Upsert query using ON CONFLICT
	query := `
		INSERT INTO ip_asset_embeddings (asset_id, owner_id, embedding, metadata)
		VALUES ($1, $2, $3, $4)
		ON CONFLICT (asset_id) 
		DO UPDATE SET 
			owner_id = EXCLUDED.owner_id,
			embedding = EXCLUDED.embedding,
			metadata = EXCLUDED.metadata,
			updated_at = CURRENT_TIMESTAMP
	`

	_, err = s.pool.Exec(ctx, query, req.AssetID, req.OwnerID, vec, metadataJSON)
	if err != nil {
		return fmt.Errorf("failed to upsert asset: %w", err)
	}

	return nil
}

// SearchNearest finds the K most similar assets using cosine similarity
func (s *PostgresVectorStore) SearchNearest(ctx context.Context, req *SearchRequest) (*SearchResponse, error) {
	// Validate input
	if len(req.Embedding) == 0 {
		return nil, fmt.Errorf("embedding cannot be empty")
	}
	if req.TopK <= 0 {
		req.TopK = 10 // Default to 10 results
	}

	// Convert embedding to pgvector
	vec := pgvector.NewVector(req.Embedding)

	// Query for nearest neighbors using cosine distance
	// Cosine distance ranges from 0 (identical) to 2 (opposite)
	// We convert it to similarity: 1 - (distance / 2) so it ranges from 0 to 1
	// NOTE: For small datasets (<1000 rows), IVFFlat index may not be used,
	// falling back to sequential scan. This is expected PostgreSQL behavior.
	query := `
		SELECT 
			asset_id,
			owner_id,
			metadata,
			created_at,
			1 - (embedding <=> $1) / 2 AS similarity
		FROM ip_asset_embeddings
		ORDER BY embedding <=> $1
		LIMIT $2
	`

	rows, err := s.pool.Query(ctx, query, vec, req.TopK)
	if err != nil {
		return nil, fmt.Errorf("failed to search nearest neighbors: %w", err)
	}
	defer rows.Close()

	var results []SimilarAsset
	for rows.Next() {
		var asset SimilarAsset
		var metadataJSON []byte

		err := rows.Scan(
			&asset.AssetID,
			&asset.OwnerID,
			&metadataJSON,
			&asset.CreatedAt,
			&asset.Similarity,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}

		// Parse metadata
		asset.Metadata, err = JSONToMetadata(metadataJSON)
		if err != nil {
			return nil, fmt.Errorf("failed to parse metadata: %w", err)
		}

		// Apply minimum score filter if specified
		if req.MinScore > 0 && asset.Similarity < req.MinScore {
			continue
		}

		results = append(results, asset)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating rows: %w", err)
	}

	return &SearchResponse{
		Results: results,
		Count:   len(results),
	}, nil
}

// GetByAssetID retrieves a specific asset by its ID
func (s *PostgresVectorStore) GetByAssetID(ctx context.Context, assetID string) (*IPAsset, error) {
	query := `
		SELECT id, asset_id, owner_id, embedding, metadata, created_at, updated_at
		FROM ip_asset_embeddings
		WHERE asset_id = $1
	`

	var asset IPAsset
	var metadataJSON []byte

	err := s.pool.QueryRow(ctx, query, assetID).Scan(
		&asset.ID,
		&asset.AssetID,
		&asset.OwnerID,
		&asset.Embedding,
		&metadataJSON,
		&asset.CreatedAt,
		&asset.UpdatedAt,
	)

	if err != nil {
		if err == pgx.ErrNoRows {
			return nil, fmt.Errorf("asset not found: %s", assetID)
		}
		return nil, fmt.Errorf("failed to get asset: %w", err)
	}

	// Parse metadata
	asset.Metadata, err = JSONToMetadata(metadataJSON)
	if err != nil {
		return nil, fmt.Errorf("failed to parse metadata: %w", err)
	}

	return &asset, nil
}

// GetByOwnerID retrieves all assets owned by a specific owner
func (s *PostgresVectorStore) GetByOwnerID(ctx context.Context, ownerID string) ([]*IPAsset, error) {
	query := `
		SELECT id, asset_id, owner_id, embedding, metadata, created_at, updated_at
		FROM ip_asset_embeddings
		WHERE owner_id = $1
		ORDER BY created_at DESC
	`

	rows, err := s.pool.Query(ctx, query, ownerID)
	if err != nil {
		return nil, fmt.Errorf("failed to query assets: %w", err)
	}
	defer rows.Close()

	var assets []*IPAsset
	for rows.Next() {
		var asset IPAsset
		var metadataJSON []byte

		err := rows.Scan(
			&asset.ID,
			&asset.AssetID,
			&asset.OwnerID,
			&asset.Embedding,
			&metadataJSON,
			&asset.CreatedAt,
			&asset.UpdatedAt,
		)
		if err != nil {
			return nil, fmt.Errorf("failed to scan row: %w", err)
		}

		// Parse metadata
		asset.Metadata, err = JSONToMetadata(metadataJSON)
		if err != nil {
			return nil, fmt.Errorf("failed to parse metadata: %w", err)
		}

		assets = append(assets, &asset)
	}

	if err := rows.Err(); err != nil {
		return nil, fmt.Errorf("error iterating rows: %w", err)
	}

	return assets, nil
}

// Delete removes an asset by its ID
func (s *PostgresVectorStore) Delete(ctx context.Context, assetID string) error {
	query := `DELETE FROM ip_asset_embeddings WHERE asset_id = $1`

	result, err := s.pool.Exec(ctx, query, assetID)
	if err != nil {
		return fmt.Errorf("failed to delete asset: %w", err)
	}

	if result.RowsAffected() == 0 {
		return fmt.Errorf("asset not found: %s", assetID)
	}

	return nil
}

// Close closes the database connection pool
func (s *PostgresVectorStore) Close() error {
	s.pool.Close()
	return nil
}

// CosineSimilarity calculates cosine similarity between two vectors
// Returns a value between -1 and 1, where 1 means identical
func CosineSimilarity(a, b []float32) float64 {
	if len(a) != len(b) {
		return 0
	}

	var dotProduct, normA, normB float64
	for i := range a {
		dotProduct += float64(a[i]) * float64(b[i])
		normA += float64(a[i]) * float64(a[i])
		normB += float64(b[i]) * float64(b[i])
	}

	if normA == 0 || normB == 0 {
		return 0
	}

	return dotProduct / (math.Sqrt(normA) * math.Sqrt(normB))
}

// NormalizeEmbedding normalizes an embedding vector to unit length
func NormalizeEmbedding(embedding []float32) []float32 {
	var norm float64
	for _, v := range embedding {
		norm += float64(v) * float64(v)
	}
	norm = math.Sqrt(norm)

	if norm == 0 {
		return embedding
	}

	normalized := make([]float32, len(embedding))
	for i, v := range embedding {
		normalized[i] = float32(float64(v) / norm)
	}

	return normalized
}
