# Build stage
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Install git and other dependencies
RUN apk add --no-cache git

# Copy go mod and sum files
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the API
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o jarvis-api .

# Runtime stage
FROM alpine:latest

# Install Docker CLI for container management
RUN apk --no-cache add ca-certificates docker-cli

WORKDIR /root/

# Copy the binary from builder stage
COPY --from=builder /app/jarvis-api .

# Expose port
EXPOSE 8080

# Run the API
CMD ["./jarvis-api"]