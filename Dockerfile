# Build stage
FROM python:3.10-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=America/Los_Angeles \
    PIP_DEFAULT_TIMEOUT=1000 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    git \
    build-essential \
    cmake \
    libatlas-base-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory and required subdirectories
WORKDIR /app
RUN mkdir -p texts audio final outputs temp assets/videos && \
    touch outputs/.gitkeep temp/.gitkeep

# Just clone gentle and copy what we need
RUN git clone https://github.com/lowerquality/gentle.git /gentle && \
    mkdir -p /app/gentle && \
    cp -r /gentle/gentle/* /app/gentle/

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies and ensure NLTK data is downloaded correctly
RUN pip install --no-cache-dir torch==2.1.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt && \
    python -c "import nltk; nltk.download('vader_lexicon', download_dir='/usr/local/share/nltk_data')" && \
    ls -la /usr/local/share/nltk_data || exit 1

# Copy the application code
COPY . .

# Create startup script
RUN echo '#!/bin/bash\n\
    mkdir -p /app/assets/videos\n\
    python run.py' > /app/startup.sh && \
    chmod +x /app/startup.sh

# Final stage
FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=America/Los_Angeles

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    libatlas-base-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy from builder stage
COPY --from=builder /app /app
COPY --from=builder /usr/local/share/nltk_data /usr/local/share/nltk_data
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages

# Expose port
EXPOSE 5500

# Run the startup script
CMD ["/app/startup.sh"]