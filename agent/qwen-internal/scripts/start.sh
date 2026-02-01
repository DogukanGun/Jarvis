#!/bin/bash

# Qwen Agent System Startup Script
# Usage: ./scripts/start.sh [command]
# Commands: setup, start, stop, logs, status, restart

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$ROOT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Setup: Install dependencies and generate Prisma client
setup() {
    log_info "Installing dependencies..."
    pnpm install

    log_info "Building packages..."
    pnpm run build

    log_info "Starting PostgreSQL..."
    docker-compose up -d postgres

    log_info "Waiting for PostgreSQL to be ready..."
    sleep 5

    log_info "Running Prisma migrations..."
    cd packages/observation-hub
    npx prisma generate
    npx prisma db push
    cd "$ROOT_DIR"

    log_info "Setup complete!"
}

# Start all services
start() {
    log_info "Starting PostgreSQL..."
    docker-compose up -d

    log_info "Starting PM2 services..."
    pm2 start ecosystem.config.cjs

    log_info "All services started!"
    pm2 status
}

# Stop all services
stop() {
    log_info "Stopping PM2 services..."
    pm2 stop all 2>/dev/null || true

    log_info "Stopping Docker services..."
    docker-compose down

    log_info "All services stopped!"
}

# Show logs
logs() {
    pm2 logs
}

# Show status
status() {
    log_info "PM2 Status:"
    pm2 status

    log_info "\nDocker Status:"
    docker-compose ps
}

# Restart all services
restart() {
    stop
    start
}

# Dev mode - start with watch
dev() {
    log_info "Starting PostgreSQL..."
    docker-compose up -d

    log_info "Starting in development mode..."
    log_info "Run 'pnpm run dev' in each package directory for hot reload"

    # Start observation hub in background
    cd packages/observation-hub && pnpm run dev &

    # Start one agent for testing
    cd packages/http-wrapper && PORT=3001 AGENT_ID=qwen-1 OBSERVATION_HUB_URL=http://localhost:4000 pnpm run dev
}

# Main
case "${1:-help}" in
    setup)
        setup
        ;;
    start)
        start
        ;;
    stop)
        stop
        ;;
    logs)
        logs
        ;;
    status)
        status
        ;;
    restart)
        restart
        ;;
    dev)
        dev
        ;;
    *)
        echo "Qwen Agent System"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  setup    - Install dependencies, build, and run migrations"
        echo "  start    - Start all services with PM2"
        echo "  stop     - Stop all services"
        echo "  restart  - Restart all services"
        echo "  logs     - Show PM2 logs"
        echo "  status   - Show service status"
        echo "  dev      - Start in development mode"
        echo ""
        ;;
esac
