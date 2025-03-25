# Start with PyTorch image that includes CUDA support
FROM pytorch/pytorch:2.1.0-cuda12.1-cudnn8-runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Add these lines to make apt non-interactive
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=America/Los_Angeles

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    git \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Create required directories
RUN mkdir -p texts audio final outputs temp assets images default_assets

# Copy requirements file first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies BEFORE using nltk
RUN pip install -r requirements.txt

# Download necessary NLTK data AFTER installing nltk
RUN python -c "import nltk; nltk.download('vader_lexicon')"

# Copy asset files to default_assets directory
COPY assets/minecraft.mp4 /app/default_assets/minecraft.mp4
COPY assets/subway.mp4 /app/default_assets/subway.mp4
COPY assets/default.mp3 /app/default_assets/default.mp3

# Copy the rest of the application code
COPY . .

# Create Force Alignment patch - make IPython import optional
RUN sed -i 's/import IPython/try:\n    import IPython\n    HAS_IPYTHON = True\nexcept ImportError:\n    HAS_IPYTHON = False/' force_alignment.py

# Add a startup script to copy default assets if /app/assets is empty
RUN echo '#!/bin/bash\n\
    if [ ! -f /app/assets/minecraft.mp4 ]; then\n\
    echo "Copying default minecraft.mp4..."\n\
    cp /app/default_assets/minecraft.mp4 /app/assets/ || echo "Failed to copy minecraft.mp4"\n\
    fi\n\
    if [ ! -f /app/assets/subway.mp4 ]; then\n\
    echo "Copying default subway.mp4..."\n\
    cp /app/default_assets/subway.mp4 /app/assets/ || echo "Failed to copy subway.mp4"\n\
    fi\n\
    if [ ! -f /app/assets/default.mp3 ]; then\n\
    echo "Copying default audio file..."\n\
    cp /app/default_assets/default.mp3 /app/assets/ || echo "Failed to copy default.mp3"\n\
    fi\n\
    python server.py\n' > /app/startup.sh && chmod +x /app/startup.sh

# Ensure all directories exist and have correct permissions
RUN chmod -R 755 .

# Expose port
EXPOSE 5500

# Run the startup script
CMD ["/app/startup.sh"]