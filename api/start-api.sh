#!/bin/bash

# Jarvis API Build and PM2 Start Script

# Get the directory where this script is located (api folder)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Get the parent directory (project root)
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Script location: $SCRIPT_DIR"
echo "Project root: $PROJECT_ROOT"
echo "🔨 Building Jarvis API..."

# Build the Go application
go build -o "$PROJECT_ROOT/jarvis-api" .

if [ $? -ne 0 ]; then
    echo "Build failed"
    exit 1
fi

echo "Build completed successfully"

# Set environment variables (you can modify these as needed)
export MONGODB_URI="mongodb://localhost:27017/jarvis"
export OPENAI_API_KEY="${OPENAI_API_KEY:-}"
export OS="${OS:-prod}"
export PORT="${PORT:-8080}"

echo "Starting Jarvis API with PM2..."

# Stop existing PM2 process if running
pm2 stop jarvis-api 2>/dev/null || true
pm2 delete jarvis-api 2>/dev/null || true

# Start the application with PM2 from the project root
cd "$PROJECT_ROOT"
pm2 start ./jarvis-api \
    --name "jarvis-api" \
    --env MONGODB_URI="$MONGODB_URI" \
    --env OPENAI_API_KEY="$OPENAI_API_KEY" \
    --env OS="$OS" \
    --env PORT="$PORT" \
    --restart-delay=3000 \
    --max-restarts=10

# Show PM2 status
pm2 status