# Build stage  
FROM golang:1.24-alpine AS builder

WORKDIR /app

# Install git and other dependencies
RUN apk add --no-cache git

# Copy root go.mod and go.sum (from project root, one level up from agent/)
COPY ../go.mod ../go.sum ./

# Copy agent go.mod and go.sum (from agent/ directory - build context)
COPY go.mod go.sum ./agent/

# Copy agent source code (from agent/ directory - build context)
COPY . ./agent/

# Download dependencies from agent directory
WORKDIR /app/agent
RUN go mod download

# Build the general agent HTTP server
WORKDIR /app/agent/general
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o agent-http .

# Runtime stage
FROM alpine:latest

# Install runtime dependencies for agent tools
RUN apk --no-cache add ca-certificates python3 nodejs npm bash git curl

WORKDIR /root/

# Copy the binary from builder stage
COPY --from=builder /app/agent/general/agent-http .

# Copy agent tools and utilities from build context 
COPY tools ./tools

# Expose port
EXPOSE 8080

# Set environment variables
ENV AGENT_MODE=http
ENV PORT=8080

# Run the agent HTTP server
CMD ["./agent-http"]