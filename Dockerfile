# Production Dockerfile for Telegram Group Music Bot
FROM python:3.10-slim-bullseye

# Install system dependencies (ffmpeg + nodejs are required for PyTgCalls audio streaming)
RUN apt-get update -y && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    curl \
    unzip \
    git \
    gcc \
    python3-dev \
    libffi-dev \
    libssl-dev && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -U pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY . .

# Run bot
CMD ["python3", "main.py"]
