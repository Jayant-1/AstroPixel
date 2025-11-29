# Backend Deployment Guide

This document explains recommended deployment options for the backend service and example settings for Render (Docker-based). The backend depends on native libraries (GDAL, rasterio) so Docker or a host that supports OS-level packages is strongly recommended.

## Quick local test

1. Activate your conda environment:

```pwsh
conda activate astropixel
cd "E:\Code\Work Station\Hackathon\AstroPixel\Backend"
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000/docs` to verify the API.

## Recommended: Deploy with Docker (Render example)

Render and similar hosts can build your Docker image which lets you install GDAL system packages reliably.

1. Ensure the repository includes a `Dockerfile` in `Backend/` that installs required OS packages (GDAL). Example base snippet (Debian/Ubuntu):

```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends \
    gdal-bin libgdal-dev build-essential \
 && rm -rf /var/lib/apt/lists/*
ENV CPLUS_INCLUDE_PATH=/usr/include/gdal
ENV C_INCLUDE_PATH=/usr/include/gdal
WORKDIR /app
COPY . /app
RUN pip install --no-cache-dir -r requirements.txt
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "$PORT"]
```

2. Push code to GitHub. In Render: create a new **Web Service** → Connect GitHub → Select repo.

3. In Render service settings choose **Docker** (it will use your `Dockerfile`). Set the service root to `Backend` if needed.

4. Add Environment Variables (Render → Environment):

- `DATABASE_URL` = `postgresql://<user>:<pass>@<host>:5432/<db>` (production Postgres recommended)
- `REDIS_URL` = `redis://<host>:6379/0` (if using Celery)
- `SECRET_KEY` = `...` (secure random string)
- `CORS_ORIGINS` = `https://<your-vercel-domain>.vercel.app` (include your frontend domain)
- `USE_S3`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_BUCKET_NAME` (if storing tiles in S3)

5. Persistent storage: don't rely on container filesystem for tiles or database. Use S3 or attach a persistent volume if your provider supports it.

6. Start the service. Render will build the image, install GDAL and Python deps, and run your app.

## Other hosting options

- Railway / Fly / DigitalOcean App Platform: Prefer Docker deployment. If using a non-Docker flow, ensure you can install system packages or use an image that already has GDAL.
- Heroku: Use the `heroku-buildpack-apt` or a Docker container. Heroku's default dynos are not ideal for GDAL-heavy tasks.
- AWS ECS / Fargate: Works well with Docker images and ECR.

## Notes & production considerations

- Database: Use Postgres for production, not SQLite.
- Offload tile storage to S3 for scale and persistence.
- Run tile generation in background workers (Celery + Redis) rather than blocking web requests.
- Monitor resource usage: tile generation is CPU and memory intensive.

## Verifying deployment

1. Check backend health endpoint: `GET https://<backend-url>/api/health` (or `/api/`) to ensure service is up.
2. Verify tiles serve: `GET https://<backend-url>/api/tiles/{dataset_id}/{z}/{x}/{y}.jpg` returns images.

---

Last updated: 2025-11-29
