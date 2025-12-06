# Hugging Face Spaces Dockerfile for AstroPixel Backend
# Free tier: 2 vCPU, 16GB RAM - perfect for tile generation!

FROM python:3.11-slim

# Install system dependencies including GDAL
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Create non-root user (required by HF Spaces)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy requirements first for caching
COPY --chown=user requirements-huggingface.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-huggingface.txt

# Copy application code
COPY --chown=user app/ ./app/

# Create necessary directories (fallback if /data not available)
RUN mkdir -p uploads tiles datasets temp static

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=7860
ENV USE_S3=true
ENV DATABASE_URL=sqlite:///./nasa_explorer.db

# Hugging Face Spaces uses port 7860
EXPOSE 7860

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
