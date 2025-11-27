package base

import (
	"encoding/json"
	"time"

	"github.com/pgvector/pgvector-go"
)

// IPAsset represents an IP asset with its embedding
type IPAsset struct {
	ID        int64                  `json:"id"`
	AssetID   string                 `json:"asset_id"`
	OwnerID   string                 `json:"owner_id"`
	Embedding pgvector.Vector        `json:"embedding"`
	Metadata  map[string]interface{} `json:"metadata"`
	CreatedAt time.Time              `json:"created_at"`
	UpdatedAt time.Time              `json:"updated_at"`
}

// SimilarAsset represents a similar asset found during search
type SimilarAsset struct {
	AssetID    string                 `json:"asset_id"`
	OwnerID    string                 `json:"owner_id"`
	Similarity float64                `json:"similarity"`
	Metadata   map[string]interface{} `json:"metadata"`
	CreatedAt  time.Time              `json:"created_at"`
}

// UpsertRequest represents a request to upsert an embedding
type UpsertRequest struct {
	AssetID   string                 `json:"asset_id"`
	OwnerID   string                 `json:"owner_id"`
	Embedding []float32              `json:"embedding"`
	Metadata  map[string]interface{} `json:"metadata"`
}

// SearchRequest represents a search query
type SearchRequest struct {
	Embedding []float32 `json:"embedding"`
	TopK      int       `json:"top_k"`
	MinScore  float64   `json:"min_score,omitempty"` // Optional minimum similarity threshold
}

// SearchResponse represents search results
type SearchResponse struct {
	Results []SimilarAsset `json:"results"`
	Count   int            `json:"count"`
}

// MetadataToJSON converts metadata map to JSON
func MetadataToJSON(metadata map[string]interface{}) ([]byte, error) {
	if metadata == nil {
		return []byte("{}"), nil
	}
	return json.Marshal(metadata)
}

// JSONToMetadata converts JSON to metadata map
func JSONToMetadata(data []byte) (map[string]interface{}, error) {
	var metadata map[string]interface{}
	if len(data) == 0 {
		return make(map[string]interface{}), nil
	}
	err := json.Unmarshal(data, &metadata)
	return metadata, err
}
