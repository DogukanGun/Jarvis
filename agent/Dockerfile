# Build stage
FROM golang:1.24-alpine AS builder

WORKDIR /app

# Install git and other dependencies
RUN apk add --no-cache git

# Copy go mod and sum files from agent directory
COPY ../go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy agent source code
COPY .. .

# Build the agent HTTP server
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o agent-http .

# Runtime stage
FROM alpine:latest

# Install runtime dependencies for agent tools
RUN apk --no-cache add ca-certificates python3 nodejs npm bash git curl

WORKDIR /root/

# Copy the binary from builder stage
COPY --from=builder /app/agent-http .

# Copy agent tools
COPY --from=builder /app/tools ./tools

# Expose port
EXPOSE 8080

# Set environment variables
ENV AGENT_MODE=http
ENV PORT=8080

# Run the agent HTTP server
CMD ["./agent-http"]