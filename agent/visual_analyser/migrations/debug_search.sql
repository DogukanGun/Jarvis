-- Debug script to test vector search manually

-- 1. Check if pgvector extension is installed
SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';

-- 2. Check if table exists and has data
SELECT COUNT(*) as total_rows FROM ip_asset_embeddings;

-- 3. Check indexes
SELECT 
    indexname, 
    indexdef,
    idx_scan as times_used
FROM pg_stat_user_indexes 
WHERE tablename = 'ip_asset_embeddings'
ORDER BY indexname;

-- 4. Sample data (show first row)
SELECT 
    asset_id, 
    owner_id, 
    array_length(embedding::float[], 1) as embedding_dims,
    created_at
FROM ip_asset_embeddings 
LIMIT 1;

-- 5. Test cosine distance query (if data exists)
-- Replace the embedding value with an actual embedding from your data
-- Example: Get first embedding and search for similar ones
DO $$
DECLARE
    test_embedding vector(768);
BEGIN
    -- Get first embedding
    SELECT embedding INTO test_embedding 
    FROM ip_asset_embeddings 
    LIMIT 1;
    
    IF test_embedding IS NOT NULL THEN
        RAISE NOTICE 'Testing search with first embedding...';
        
        -- This would be the actual search query
        -- Uncomment to run:
        -- SELECT 
        --     asset_id,
        --     1 - (embedding <=> test_embedding) / 2 AS similarity
        -- FROM ip_asset_embeddings
        -- ORDER BY embedding <=> test_embedding
        -- LIMIT 5;
    ELSE
        RAISE NOTICE 'No data in table to test with';
    END IF;
END $$;

-- 6. Check query plan for vector search
EXPLAIN ANALYZE
SELECT 
    asset_id,
    owner_id,
    1 - (embedding <=> (SELECT embedding FROM ip_asset_embeddings LIMIT 1)) / 2 AS similarity
FROM ip_asset_embeddings
WHERE (SELECT COUNT(*) FROM ip_asset_embeddings) > 0
ORDER BY embedding <=> (SELECT embedding FROM ip_asset_embeddings LIMIT 1)
LIMIT 3;

-- 7. Force sequential scan (disable index) to test if index is the issue
SET enable_indexscan = off;
SET enable_bitmapscan = off;

EXPLAIN ANALYZE
SELECT 
    asset_id,
    1 - (embedding <=> (SELECT embedding FROM ip_asset_embeddings LIMIT 1)) / 2 AS similarity
FROM ip_asset_embeddings
WHERE (SELECT COUNT(*) FROM ip_asset_embeddings) > 0
ORDER BY embedding <=> (SELECT embedding FROM ip_asset_embeddings LIMIT 1)
LIMIT 3;

-- Reset settings
SET enable_indexscan = on;
SET enable_bitmapscan = on;

-- 8. Check if IVFFlat index has been built
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
WHERE indexname = 'idx_embedding_cosine';

