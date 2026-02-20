FROM arm64v8/python:3.9-slim-bullseye

LABEL maintainer="vedant.240102162@iiitbh.ac.in"
LABEL description="Blueberry Audio Output - TTS synthesis and playback"

# Install system dependencies for audio playback
RUN apt-get update && apt-get install -y --no-install-recommends \
    espeak-ng \
    alsa-utils \
    libasound2 \
    libsndfile1 \
    pulseaudio \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY output.py .

# Create directories
RUN mkdir -p logs tts_cache

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV MQTT_BROKER=mosquitto
ENV MQTT_PORT=1883
ENV ESPEAK_DATA_PATH=/usr/share/espeak-ng-data

# Run as non-root user
RUN useradd -m -u 1000 blueberry && \
    chown -R blueberry:blueberry /app
USER blueberry

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import paho.mqtt.client as mqtt; print('OK')" || exit 1

# Start the application
CMD ["py", "-u", "output.py"]