FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for caching
COPY app/requirements.txt .

# Add FastAPI and uvicorn to requirements
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi uvicorn[standard]

# Copy application code
COPY app/ ./app/

# Create directory for SQLite database
RUN mkdir -p /data

# Environment variables
ENV PYTHONPATH=/app
ENV SQLITE_DB_PATH=/data/jarvis_episodes.db
ENV HOST=0.0.0.0
ENV PORT=8085

# Expose port
EXPOSE 8085

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8085/health')" || exit 1

# Run the API
CMD ["python", "-m", "app.api"]
