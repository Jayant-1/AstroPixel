---
title: AstroPixel Backend
emoji: 🔭
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# AstroPixel - NASA Gigapixel Image Explorer Backend

FastAPI backend for processing and serving NASA imagery tiles.

## Features
- GeoTIFF tile generation using GDAL
- Cloudflare R2 cloud storage integration
- RESTful API for dataset management
- OpenSeadragon-compatible tile serving

## API Endpoints
- `GET /api/health` - Health check
- `GET /api/datasets` - List all datasets
- `POST /api/datasets/upload` - Upload new dataset
- `GET /api/tiles/{id}/{z}/{x}/{y}.png` - Get tile

## Environment Variables
Set these in your Space's Settings > Repository secrets:
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_ENDPOINT_URL`
- `R2_BUCKET_NAME`
- `R2_PUBLIC_URL`
