# Build stage for Go application
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

# Build the router agent HTTP server
WORKDIR /app/agent/router
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o router-http .

# Runtime stage - Use Alpine for minimal footprint
FROM alpine:latest

# Install runtime dependencies
RUN apk --no-cache add ca-certificates curl

WORKDIR /root/

# Copy the binary from builder stage
COPY --from=builder /app/agent/router/router-http .

# Copy agent utilities from build context 
COPY utils ./utils

# Expose port
EXPOSE 8080

# Set environment variables
ENV AGENT_MODE=http
ENV PORT=8080

# Run the router agent HTTP server
CMD ["./router-http"]