
## How Migrations Work

The PostgreSQL container automatically runs all `.sql` and `.sh` files in `/docker-entrypoint-initdb.d/` **on first initialization only** (when the database is created for the first time).

### Docker Compose Setup

```yaml
postgres:
  image: ankane/pgvector:v0.5.1
  volumes:
    - postgres_data:/var/lib/postgresql/data  # Persistent storage
    - ./visual_analyser/migrations:/docker-entrypoint-initdb.d  # Migration scripts
```

### Important Notes

1. **First-time Only**: Migrations in `/docker-entrypoint-initdb.d/` only run when the PostgreSQL data directory is empty (first container start).

2. **Existing Database**: If you've already started PostgreSQL before, you need to either:
   - Drop the existing volume and recreate
   - Run migrations manually

3. **Idempotent Scripts**: All migration scripts use `IF NOT EXISTS` / `CREATE OR REPLACE` to be safe if run multiple times.

## Running Migrations

### Automatic (First Time)

```bash
# Start services - migrations run automatically
cd agent
docker-compose up -d postgres

# Check logs to verify migration ran
docker-compose logs postgres | grep "vector"
```

### Manual Execution (Existing Database)

If you need to run migrations on an existing database:

```bash
# Option 1: Execute SQL file directly
docker exec -i jarvis-postgres psql -U jarvis -d jarvis < visual_analyser/migrations/001_init_vector_store.sql

# Option 2: Using psql interactive
docker exec -it jarvis-postgres psql -U jarvis -d jarvis
# Then run: \i /docker-entrypoint-initdb.d/001_init_vector_store.sql

# Option 3: Copy and execute
cat visual_analyser/migrations/001_init_vector_store.sql | \
  docker exec -i jarvis-postgres psql -U jarvis -d jarvis
```

### Fresh Start (Clean Database)

To reset and run migrations from scratch:

```bash
# Stop and remove all containers and volumes
cd agent
docker-compose down -v

# Start fresh - migrations will run automatically
docker-compose up -d postgres

# Wait for PostgreSQL to be ready
docker-compose logs -f postgres
```

## Verifying Migrations

### Check if pgvector extension is installed

```bash
docker exec -it jarvis-postgres psql -U jarvis -d jarvis -c "SELECT * FROM pg_extension WHERE extname='vector';"
```

Expected output:
```
 oid  | extname | extowner | extnamespace | extrelocatable | extversion | extconfig | extcondition 
------+---------+----------+--------------+----------------+------------+-----------+--------------
 16388| vector  |       10 |         2200 | t              | 0.5.1      |           | 
```

### Check if table exists

```bash
docker exec -it jarvis-postgres psql -U jarvis -d jarvis -c "\dt ip_asset_embeddings"
```

Expected output:
```
                List of relations
 Schema |         Name          | Type  | Owner  
--------+-----------------------+-------+--------
 public | ip_asset_embeddings   | table | jarvis
```

### Check indexes

```bash
docker exec -it jarvis-postgres psql -U jarvis -d jarvis -c "\d ip_asset_embeddings"
```

Should show:
- `idx_asset_id` - B-tree index on asset_id
- `idx_owner_id` - B-tree index on owner_id  
- `idx_embedding_cosine` - IVFFlat index on embedding

### Test vector operations

```bash
docker exec -it jarvis-postgres psql -U jarvis -d jarvis -c "
INSERT INTO ip_asset_embeddings (asset_id, owner_id, embedding, metadata) 
VALUES ('test-1', 'user-1', '[0.1, 0.2, 0.3]'::vector(3), '{}');
SELECT asset_id, owner_id FROM ip_asset_embeddings;
DELETE FROM ip_asset_embeddings WHERE asset_id = 'test-1';
"
```

## Migration Files

### 001_init_vector_store.sql

Initial setup including:
- ✅ pgvector extension
- ✅ `ip_asset_embeddings` table with vector(768) column
- ✅ Indexes for fast lookups and similarity search
- ✅ Triggers for automatic timestamp updates
- ✅ View for similarity search results
- ✅ Proper permissions for jarvis user

All statements are idempotent (safe to run multiple times).

## Troubleshooting

### Migrations didn't run

**Symptom**: Table doesn't exist after starting PostgreSQL

**Solution**:
```bash
# Check if volume already exists
docker volume ls | grep postgres

# Remove volume and restart
docker-compose down -v
docker-compose up -d postgres
```

### Permission denied errors

**Symptom**: Cannot create table or extension

**Solution**:
```bash
# Ensure you're using the correct database and user
docker exec -it jarvis-postgres psql -U jarvis -d jarvis

# Grant superuser if needed (for extension creation)
# This is typically not needed with ankane/pgvector image
```

### Vector type not found

**Symptom**: `type "vector" does not exist`

**Solution**:
```bash
# Manually enable pgvector extension
docker exec -it jarvis-postgres psql -U jarvis -d jarvis -c "CREATE EXTENSION vector;"

# Or recreate container
docker-compose down -v
docker-compose up -d postgres
```

### Index creation fails

**Symptom**: IVFFlat index creation fails

**Possible causes**:
1. Not enough data (IVFFlat needs at least ~1000 rows, but with `lists = 100` it should work with fewer)
2. pgvector not properly installed

**Solution**:
```bash
# Check pgvector version
docker exec -it jarvis-postgres psql -U jarvis -d jarvis -c "SELECT extversion FROM pg_extension WHERE extname='vector';"

# Create index with fewer lists
# Or skip index initially and create it after inserting data
```

## Best Practices

1. **Backup before migrations**: Always backup your data before running migrations on production
2. **Test locally first**: Test migration on a local copy of production data
3. **Idempotent migrations**: Always use `IF NOT EXISTS` and `CREATE OR REPLACE`
4. **Naming convention**: Use numbered prefixes: `001_`, `002_`, etc.
5. **Single responsibility**: Each migration file should handle one logical change
6. **Rollback plan**: Document how to undo each migration if needed

## Adding New Migrations

To add a new migration:

1. Create a new file: `migrations/002_your_change.sql`
2. Make it idempotent with `IF NOT EXISTS` / `CREATE OR REPLACE`
3. Test on a local database first
4. For existing databases, run manually:
   ```bash
   docker exec -i jarvis-postgres psql -U jarvis -d jarvis < visual_analyser/migrations/002_your_change.sql
   ```

## Example: Rolling Back

If you need to undo the migrations:

```bash
# Connect to database
docker exec -it jarvis-postgres psql -U jarvis -d jarvis

# Drop in reverse order
DROP VIEW IF EXISTS similar_assets;
DROP TRIGGER IF EXISTS update_ip_asset_embeddings_updated_at ON ip_asset_embeddings;
DROP FUNCTION IF EXISTS update_updated_at_column();
DROP TABLE IF EXISTS ip_asset_embeddings CASCADE;
DROP EXTENSION IF EXISTS vector;
```

Or simply recreate the database:

```bash
docker-compose down -v
docker-compose up -d postgres
```

