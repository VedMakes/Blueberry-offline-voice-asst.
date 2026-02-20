FROM arm64v8/python:3.9-slim-bullseye

LABEL maintainer="your.email@example.com"
LABEL description="Blueberry Processing - Rasa NLU with KleidiAI optimization"

# Install system dependencies for Rasa and KleidiAI
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
# KleidiAI for ARM optimization
RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir tensorflow-aarch64

# Copy Rasa configuration
COPY config.yml .
COPY domain.yml .
COPY endpoints.yml .
COPY credentials.yml .

# Copy training data
COPY data/ ./data/

# Copy trained models
COPY models/ ./models/

# Copy actions server
COPY actions/ ./actions/

# Copy services (temporal parser, time daemon)
COPY services/ ./services/

# Copy Rasa bridge
COPY rasa_bridge.py .

# Copy database schema
COPY database/ ./database/

# Create logs directory
RUN mkdir -p logs

# Create SQLite database
RUN touch assistant_data.db && \
    python -c "import sqlite3; conn = sqlite3.connect('assistant_data.db'); conn.close()"

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MQTT_BROKER=mosquitto
ENV MQTT_PORT=1883
ENV RASA_MODEL_DIR=/app/models
ENV TF_ENABLE_ONEDNN_OPTS=1

# Run as non-root user
RUN useradd -m -u 1000 blueberry && \
    chown -R blueberry:blueberry /app
USER blueberry

# Expose ports
EXPOSE 5005 5055 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5005/status || exit 1

# Start script to run all services
COPY start_services.sh .
RUN chmod +x start_services.sh

CMD ["./start_services.sh"]