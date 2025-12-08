"""
Tile serving endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Path as PathParam
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from pathlib import Path
import logging
from typing import Optional
from functools import lru_cache
from time import time

from app.database import get_db
from app.models import Dataset, User
from app.config import settings
from app.services.storage import cloud_storage
from app.services.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Simple cache for dataset metadata (id -> (timestamp, tiles_on_r2, max_zoom, tile_base_path))
_dataset_cache = {}
_cache_ttl = 300  # 5 minutes


@router.get("/tiles/{dataset_id}/{z}/{x}/{y}.{format}")
async def get_tile(
    dataset_id: int = PathParam(..., description="Dataset ID"),
    z: int = PathParam(..., ge=0, le=30, description="Zoom level"),
    x: int = PathParam(..., ge=0, description="Tile X coordinate"),
    y: int = PathParam(..., ge=0, description="Tile Y coordinate"),
    format: str = PathParam(..., pattern="^(jpg|png|webp)$", description="Tile format"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Serve individual tiles for a dataset
    
    Access control:
    - Demo datasets: Anyone can access
    - User datasets: Only the owner can access

    - **dataset_id**: ID of the dataset
    - **z**: Zoom level (0 = furthest out)
    - **x**: Tile X coordinate
    - **y**: Tile Y coordinate
    - **format**: Image format (jpg, png, webp)
    """
    # Check cache first to avoid DB query on subsequent requests
    now = time()
    cache_key = dataset_id
    cached = _dataset_cache.get(cache_key)
    
    # Use cache if valid (regardless of R2 status)
    if cached and (now - cached[0]) < _cache_ttl:
        cache_bust = cached[4]  # cache_bust
        max_zoom = cached[2]
        tiles_on_r2 = cached[1]
        tile_base_path = cached[3]
        
        # Validate zoom level from cache
        if z > max_zoom:
            raise HTTPException(
                status_code=400, detail=f"Zoom level {z} exceeds maximum {max_zoom}"
            )
        
        # If R2 is enabled and tiles are on R2, redirect
        if cloud_storage.enabled and cloud_storage.public_url and tiles_on_r2:
            tile_url = cloud_storage.get_tile_url(dataset_id, z, x, y, format, cache_bust)
            if tile_url:
                return RedirectResponse(
                    url=tile_url,
                    status_code=302,
                    headers={
                        "Cache-Control": "public, max-age=31536000, immutable",
                        "Access-Control-Allow-Origin": "*",
                    }
                )
        
        # Otherwise serve from local tiles using cached path
        if Path(tile_base_path).is_absolute():
            tile_base = Path(tile_base_path)
        else:
            tile_base = settings.BASE_DIR / tile_base_path
        
        tile_path = tile_base / str(z) / str(x) / f"{y}.{format}"
        
        # If requested format doesn't exist, try fallback formats
        if not tile_path.exists():
            fallback_formats = ["png", "webp"] if format.lower() in ["jpg", "jpeg"] else ["jpg", "jpeg", "webp"] if format.lower() == "png" else ["png", "jpg", "jpeg"]
            for fallback_format in fallback_formats:
                fallback_path = tile_base / str(z) / str(x) / f"{y}.{fallback_format}"
                if fallback_path.exists():
                    tile_path = fallback_path
                    format = fallback_format
                    break
            else:
                raise HTTPException(status_code=404, detail=f"Tile {z}/{x}/{y} not found")
        
        media_type_map = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}
        return FileResponse(
            tile_path,
            media_type=media_type_map.get(format.lower(), f"image/{format}"),
            headers={
                "Cache-Control": "public, max-age=31536000, immutable",
                "X-Tile-Status": "exists",
                "X-Tile-Format": format,
                "Access-Control-Allow-Origin": "*",
                "Cross-Origin-Resource-Policy": "cross-origin",
                "ETag": f'"{dataset_id}-{z}-{x}-{y}-{format}"',
            },
        )
    
    # Cache miss or local tiles - query database
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check permissions: demo datasets are public, user datasets require ownership
    if not dataset.is_demo:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required to access this dataset")
        if dataset.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="You don't have permission to access this dataset")

    # Allow serving tiles if completed OR if tiles exist locally (processing might be stuck)
    if dataset.processing_status not in ["completed", "processing"]:
        raise HTTPException(
            status_code=503, detail=f"Dataset is {dataset.processing_status}"
        )

    # Cache-busting token to avoid stale tiles when dataset IDs get reused
    cache_bust = None
    if dataset.updated_at:
        cache_bust = str(int(dataset.updated_at.timestamp()))
    elif dataset.created_at:
        cache_bust = str(int(dataset.created_at.timestamp()))

    # Check if tiles are on R2
    tiles_on_r2 = (
        dataset.extra_metadata and 
        dataset.extra_metadata.get('tiles_uploaded_to_cloud') == True
    )
    
    # Cache dataset metadata for future requests
    _dataset_cache[cache_key] = (now, tiles_on_r2, dataset.max_zoom, dataset.tile_base_path, cache_bust)
    
    # If cloud storage (R2) is enabled and tiles are uploaded, serve from R2
    if cloud_storage.enabled and cloud_storage.public_url and tiles_on_r2:
        tile_url = cloud_storage.get_tile_url(dataset_id, z, x, y, format, cache_bust)
        if tile_url:
            logger.debug(f"⚡ Redirecting to R2: {dataset_id}/{z}/{x}/{y}.{format}")
            return RedirectResponse(
                url=tile_url,
                status_code=302,
                headers={
                    "Cache-Control": "public, max-age=31536000, immutable",
                    "Access-Control-Allow-Origin": "*",
                }
            )

    # Validate zoom level
    if z > dataset.max_zoom:
        raise HTTPException(
            status_code=400, detail=f"Zoom level {z} exceeds maximum {dataset.max_zoom}"
        )

    # Construct tile path
    # Handle both relative and absolute paths
    if Path(dataset.tile_base_path).is_absolute():
        tile_base = Path(dataset.tile_base_path)
    else:
        # Relative path - make it relative to TILES_DIR or BASE_DIR
        tile_base = settings.BASE_DIR / dataset.tile_base_path

    tile_path = tile_base / str(z) / str(x) / f"{y}.{format}"

    # If requested format doesn't exist, try fallback formats
    if not tile_path.exists():
        # Try alternative formats (PNG if JPG requested, JPG if PNG requested)
        fallback_formats = []
        if format.lower() == "jpg" or format.lower() == "jpeg":
            fallback_formats = ["png", "webp"]
        elif format.lower() == "png":
            fallback_formats = ["jpg", "jpeg", "webp"]
        elif format.lower() == "webp":
            fallback_formats = ["png", "jpg", "jpeg"]
        
        # Try fallback formats
        for fallback_format in fallback_formats:
            fallback_path = tile_base / str(z) / str(x) / f"{y}.{fallback_format}"
            if fallback_path.exists():
                logger.info(
                    f"Tile {z}/{x}/{y} requested as {format} but found as {fallback_format}, serving fallback"
                )
                tile_path = fallback_path
                format = fallback_format  # Update format for media type
                break
        else:
            # No fallback found, return 404
            raise HTTPException(
                status_code=404,
                detail=f"Tile {z}/{x}/{y} not found for dataset {dataset_id} (tried: {format}, {', '.join(fallback_formats)})"
            )

    # Serve tile with caching headers
    # Normalize media type (jpg/jpeg -> jpeg)
    media_type_map = {
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "png": "image/png",
        "webp": "image/webp",
    }
    media_type = media_type_map.get(format.lower(), f"image/{format}")

    return FileResponse(
        tile_path,
        media_type=media_type,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",  # 1 year, immutable
            "X-Tile-Status": "exists",
            "X-Tile-Format": format,  # Indicate actual format served
            "Access-Control-Allow-Origin": "*",  # Allow CORS for canvas export
            "Cross-Origin-Resource-Policy": "cross-origin",
            "ETag": f'"{dataset_id}-{z}-{x}-{y}-{format}"',
        },
    )


@router.get("/tiles/{dataset_id}/preview")
async def get_preview(dataset_id: int, db: Session = Depends(get_db)):
    """
    Get preview thumbnail for a dataset

    - **dataset_id**: ID of the dataset
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check if preview is stored in cloud storage (R2)
    cache_bust = None
    if dataset.updated_at:
        cache_bust = str(int(dataset.updated_at.timestamp()))
    elif dataset.created_at:
        cache_bust = str(int(dataset.created_at.timestamp()))

    if cloud_storage.enabled and cloud_storage.public_url:
        # Check if dataset has preview_url in metadata
        if dataset.extra_metadata and dataset.extra_metadata.get('preview_url'):
            preview_url = dataset.extra_metadata['preview_url']
            if cache_bust:
                separator = '&' if '?' in preview_url else '?'
                preview_url = f"{preview_url}{separator}v={cache_bust}"
            return RedirectResponse(
                url=preview_url,
                status_code=302,
                headers={
                    "Cache-Control": "public, max-age=86400",
                    "Access-Control-Allow-Origin": "*",
                }
            )
        # Fallback to constructing R2 URL
        preview_url = f"{cloud_storage.public_url}/previews/{dataset_id}_preview.jpg"
        if cache_bust:
            preview_url = f"{preview_url}?v={cache_bust}"
        return RedirectResponse(
            url=preview_url,
            status_code=302,
            headers={
                "Cache-Control": "public, max-age=86400",
                "Access-Control-Allow-Origin": "*",
            }
        )

    # Fallback to local file
    preview_path = settings.DATASETS_DIR / f"{dataset_id}_preview.jpg"

    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Preview not available")

    return FileResponse(
        preview_path,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=86400",  # 1 day
            "Access-Control-Allow-Origin": "*",  # Allow CORS for canvas export
            "Cross-Origin-Resource-Policy": "cross-origin",
        },
    )


@router.get("/tiles/{dataset_id}/info")
async def get_tile_info(dataset_id: int, db: Session = Depends(get_db)):
    """
    Get tile metadata for OpenSeadragon configuration

    - **dataset_id**: ID of the dataset
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Return OpenSeadragon-compatible tile source info
    return {
        "type": "zoomify",
        "width": dataset.width,
        "height": dataset.height,
        "tileSize": dataset.tile_size,
        "minZoom": dataset.min_zoom,
        "maxZoom": dataset.max_zoom,
        "tilesUrl": f"{settings.API_PREFIX}/tiles/{dataset_id}/{{z}}/{{x}}/{{y}}.png",
        "profile": "level0",
        "bounds": (
            dataset.extra_metadata.get("bounds") if dataset.extra_metadata else None
        ),
    }
