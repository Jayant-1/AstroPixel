# Hugging Face Spaces Dockerfile for AstroPixel Backend
# Minimal, reliable setup for free tier

FROM python:3.11-slim

# Install system dependencies - minimal set
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    python3-gdal \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set environment
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV PYTHONPATH=/usr/lib/python3/dist-packages:$PYTHONPATH
ENV PYTHONUNBUFFERED=1

# Non-root user (HF requirement)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR $HOME/app

# Install dependencies with explicit numpy handling to avoid conflicts
COPY requirements-hf.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --force-reinstall --no-deps numpy==1.26.3 && \
    pip install --no-cache-dir -r requirements-hf.txt

# Copy app
COPY app/ ./app/
RUN mkdir -p uploads tiles datasets temp static

EXPOSE 7860
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7860"]
