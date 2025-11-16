# Use Ubuntu as the base image
FROM ubuntu:latest

# Update package lists and install necessary packages including curl for health checks
RUN apt-get update && \
    apt-get install -y g++ python3 python3-pip git htop curl wget && \
    rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Expose Ollama port
EXPOSE 11434

# Set environment variables
ENV OLLAMA_HOST=0.0.0.0:11434

# Start Ollama in background and pull the model during build
RUN ollama serve & \
    sleep 10 && \
    ollama pull llama3.2 && \
    pkill ollama

# Create startup script that just starts Ollama (model already downloaded)
RUN echo '#!/bin/bash\n\
echo "Starting Ollama server with pre-downloaded models..."\n\
ollama serve\n\
' > /start-ollama.sh && chmod +x /start-ollama.sh

# Run the startup script
CMD ["/bin/bash", "/start-ollama.sh"]


