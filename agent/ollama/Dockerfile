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

# Create startup script that starts Ollama and pulls the model
RUN echo '#!/bin/bash\n\
echo "Starting Ollama server..."\n\
ollama serve &\n\
\n\
echo "Waiting for Ollama to be ready..."\n\
sleep 10\n\
\n\
echo "Pulling llama3.2 model..."\n\
ollama pull llama3.2\n\
\n\
echo "Ollama setup complete. Keeping server running..."\n\
wait\n\
' > /start-ollama.sh && chmod +x /start-ollama.sh

# Set environment variables
ENV OLLAMA_HOST=0.0.0.0:11434

# Run the startup script
CMD ["/bin/bash", "/start-ollama.sh"]


