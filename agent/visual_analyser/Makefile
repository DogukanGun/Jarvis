.PHONY: help build run test clean docker-build docker-run docker-stop deps

# Variables
APP_NAME=visual-analyser
DOCKER_IMAGE=jarvis-visual-analyser
DATABASE_URL=postgres://jarvis:jarvispassword@localhost:5432/jarvis?sslmode=disable

help: ## Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-20s %s\n", $$1, $$2}'

deps: ## Download Go dependencies
	cd .. && go mod download
	cd .. && go mod tidy

build: ## Build the application
	cd .. && go build -o visual_analyser/$(APP_NAME) ./visual_analyser

run: ## Run the application locally
	export DATABASE_URL=$(DATABASE_URL) && cd .. && go run ./visual_analyser

test: ## Run tests
	cd .. && go test -v -cover ./visual_analyser

test-integration: ## Run integration tests (requires database)
	export TEST_DATABASE_URL=$(DATABASE_URL) && cd .. && go test -v -run TestPostgresVectorStore ./visual_analyser

test-coverage: ## Run tests with coverage report
	cd .. && go test -v -coverprofile=visual_analyser/coverage.out ./visual_analyser
	cd .. && go tool cover -html=visual_analyser/coverage.out -o visual_analyser/coverage.html
	@echo "Coverage report: coverage.html"

lint: ## Run linter
	@command -v golangci-lint >/dev/null 2>&1 || { echo "golangci-lint not installed. Run: brew install golangci-lint"; exit 1; }
	cd .. && golangci-lint run ./visual_analyser/...

clean: ## Clean build artifacts
	rm -f $(APP_NAME)
	rm -f coverage.out coverage.html
	cd .. && go clean

docker-build: ## Build Docker image
	docker build -t $(DOCKER_IMAGE) .

docker-run: ## Run Docker container
	docker run -d --name $(DOCKER_IMAGE) \
		-p 8084:8080 \
		-e DATABASE_URL=$(DATABASE_URL) \
		$(DOCKER_IMAGE)

docker-stop: ## Stop and remove Docker container
	docker stop $(DOCKER_IMAGE) || true
	docker rm $(DOCKER_IMAGE) || true

docker-logs: ## View Docker container logs
	docker logs -f $(DOCKER_IMAGE)

compose-up: ## Start all services with docker-compose
	cd .. && docker-compose up -d

compose-down: ## Stop all services
	cd .. && docker-compose down

compose-logs: ## View visual-analyser logs
	cd .. && docker-compose logs -f visual-analyser

compose-restart: ## Restart visual-analyser service
	cd .. && docker-compose restart visual-analyser

api-test: ## Run API tests (requires service to be running)
	chmod +x test_api.sh
	./test_api.sh

dev: ## Run in development mode with auto-reload (requires air)
	@command -v air >/dev/null 2>&1 || { echo "air not installed. Run: go install github.com/cosmtrek/air@latest"; exit 1; }
	air

install-tools: ## Install development tools
	go install github.com/cosmtrek/air@latest
	go install github.com/golangci/golangci-lint/cmd/golangci-lint@latest

db-migrate: ## Run database migrations (via docker-compose)
	@echo "Migrations run automatically on PostgreSQL startup"
	@echo "Check migrations at: ./migrations/001_init_vector_store.sql"

db-shell: ## Open PostgreSQL shell
	docker exec -it jarvis-postgres psql -U jarvis -d jarvis

db-test-connection: ## Test database connection
	@echo "Testing database connection..."
	@psql $(DATABASE_URL) -c "SELECT version();" || echo "Connection failed"

.DEFAULT_GOAL := help

