#!/bin/bash

echo "Building Jarvis Agent Base Docker Image..."

# Build the base Docker image that will be used for all users
docker build -t jarvis-agent-base:latest .

if [ $? -eq 0 ]; then
    echo "Base Docker image built successfully!"
else
    echo "Failed to build Docker image"
    exit 1
fi