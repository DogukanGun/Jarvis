# Playwright Python image includes browser deps; we add app deps and ensure Chromium
FROM mcr.microsoft.com/playwright/python:v1.57.0-noble

WORKDIR /app

# Install app dependencies and Chromium
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN playwright install chromium

# Copy application code
COPY main.py crawler_service.py ./

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
