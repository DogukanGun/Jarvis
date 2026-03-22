FROM python:3.11-slim

WORKDIR /app

COPY app/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY run_server.py .

EXPOSE 8686

CMD ["python", "run_server.py"]
