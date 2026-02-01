# Visual Analyser Dockerfile
FROM golang:1.24-alpine AS builder

WORKDIR /app

# Copy Go modules
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy all source code
COPY . .

# Build the application
RUN CGO_ENABLED=0 GOOS=linux go build -a -installsuffix cgo -o visual-analyser ./visual_analyser

# Final stage
FROM alpine:latest

RUN apk --no-cache add ca-certificates curl

WORKDIR /root/

# Copy the binary from builder
COPY --from=builder /app/visual-analyser .

EXPOSE 8081

CMD ["./visual-analyser"]
