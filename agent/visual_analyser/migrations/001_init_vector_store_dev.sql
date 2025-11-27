-- Development/Testing Migration (No IVFFlat Index)
-- Use this for small datasets or testing environments
-- IVFFlat index requires significant data (>1000 rows) to work effectively

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create IP asset embeddings table
CREATE TABLE IF NOT EXISTS ip_asset_embeddings (
    id SERIAL PRIMARY KEY,
    asset_id VARCHAR(255) UNIQUE NOT NULL,
    owner_id VARCHAR(255) NOT NULL,
    embedding vector(768) NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for asset_id lookups
CREATE INDEX IF NOT EXISTS idx_asset_id ON ip_asset_embeddings(asset_id);

-- Create index for owner_id lookups
CREATE INDEX IF NOT EXISTS idx_owner_id ON ip_asset_embeddings(owner_id);

-- NOTE: IVFFlat index is NOT created in dev mode for small datasets
-- For production with >1000 rows, use 001_init_vector_store.sql instead
-- Or run: CREATE INDEX idx_embedding_cosine ON ip_asset_embeddings 
--         USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to automatically update updated_at (drop first if exists)
DROP TRIGGER IF EXISTS update_ip_asset_embeddings_updated_at ON ip_asset_embeddings;
CREATE TRIGGER update_ip_asset_embeddings_updated_at 
    BEFORE UPDATE ON ip_asset_embeddings 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create view for similarity search results
CREATE OR REPLACE VIEW similar_assets AS
SELECT 
    asset_id,
    owner_id,
    embedding,
    metadata,
    created_at,
    updated_at
FROM ip_asset_embeddings;

-- Grant necessary permissions
GRANT ALL PRIVILEGES ON ip_asset_embeddings TO jarvis;
GRANT ALL PRIVILEGES ON similar_assets TO jarvis;

