FROM python:3.11-slim

WORKDIR /app

# Install system dependencies including GDAL
RUN apt-get update && apt-get install -y \
    gdal-bin \
    libgdal-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Set GDAL environment variables
ENV GDAL_CONFIG=/usr/bin/gdal-config
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads tiles datasets temp

# Expose port (informational)
EXPOSE 8000

# Run application
# Use shell form so $PORT (provided by Render) is expanded. Reduce workers to 1 to lower memory usage on small instances.
CMD uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1
