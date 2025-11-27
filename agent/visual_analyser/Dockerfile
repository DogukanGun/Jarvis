# Build stage
FROM golang:1.21-alpine AS builder

# Install build dependencies
RUN apk add --no-cache git gcc musl-dev

WORKDIR /app

# Copy go mod files from agent root
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the visual_analyser application
RUN CGO_ENABLED=1 GOOS=linux go build -a -installsuffix cgo -o visual-analyser ./visual_analyser

# Runtime stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates wget

WORKDIR /root/

# Copy the binary from builder
COPY --from=builder /app/visual-analyser .

# Expose port
EXPOSE 8080

# Run the application
CMD ["./visual-analyser"]

