FROM arm64v8/python:3.9-slim-bullseye

LABEL maintainer="your.email@example.com"
LABEL description="Blueberry Audio Capture - Wake word detection and ASR"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    portaudio19-dev \
    libasound2-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY asr.py .
COPY audio.py .
COPY config.py .
COPY main.py .
COPY mqtt_client.py .
COPY SECRETS.py .
COPY vad.py .
COPY wakeword.py .

# Create logs directory
RUN mkdir -p logs

# Download Porcupine wake word model (if not already in image)
# Note: Add your blueberry.ppn file to the build context
COPY model/ ./model/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MQTT_BROKER=mosquitto
ENV MQTT_PORT=1883

# Run as non-root user
RUN useradd -m -u 1000 blueberry && \
    chown -R blueberry:blueberry /app
USER blueberry

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD python -c "import mqtt_client; print('OK')" || exit 1

# Start the application
CMD ["py", "-u", "main.py"]