# Build stage
FROM golang:1.23-alpine AS builder

WORKDIR /build

# Copy go.mod and go.sum first for better caching
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY gui-agent/ ./gui-agent/
COPY tools/ ./tools/

# Build the application
WORKDIR /build/gui-agent
RUN CGO_ENABLED=0 GOOS=linux go build -o gui-agent .

# Runtime stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates

WORKDIR /app

COPY --from=builder /build/gui-agent/gui-agent .

EXPOSE 8080

CMD ["./gui-agent"]
