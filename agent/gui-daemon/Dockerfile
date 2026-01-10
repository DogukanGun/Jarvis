# Use Ubuntu as base for better X11/GUI support
FROM ubuntu:22.04

# Avoid prompts from apt
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    gcc \
    g++ \
    make \
    pkg-config \
    libx11-dev \
    libxtst-dev \
    libpng-dev \
    libxinerama-dev \
    libxkbcommon-dev \
    xorg \
    xvfb \
    x11vnc \
    xdotool \
    wmctrl \
    && rm -rf /var/lib/apt/lists/*

# Install Go
ENV GO_VERSION=1.21.5
RUN wget https://go.dev/dl/go${GO_VERSION}.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go${GO_VERSION}.linux-amd64.tar.gz && \
    rm go${GO_VERSION}.linux-amd64.tar.gz

# Set Go environment variables
ENV PATH="/usr/local/go/bin:${PATH}"
ENV GOPATH="/go"
ENV PATH="${GOPATH}/bin:${PATH}"

# Create app directory
WORKDIR /app

# Copy go.mod and go.sum
COPY go.mod ./

# Download dependencies
RUN go mod download

# Copy source code
COPY . .

# Build the application
RUN go build -o gui-daemon .

# Expose port
EXPOSE 9990

# Set display for X11
ENV DISPLAY=:99

# Start Xvfb and the application
CMD Xvfb :99 -screen 0 1920x1080x24 & \
    sleep 2 && \
    ./gui-daemon
