"""
Tile serving endpoints
"""

from fastapi import APIRouter, Depends, HTTPException, Path as PathParam
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.orm import Session
from pathlib import Path
import logging
from typing import Optional

from app.database import get_db
from app.models import Dataset, User
from app.config import settings
from app.services.storage import cloud_storage
from app.services.auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


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
    # Get dataset
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

    # If cloud storage (R2) is enabled, check if tiles have been uploaded
    # Try metadata flag first, then check R2 directly for datasets synced from cloud
    if cloud_storage.enabled and cloud_storage.public_url:
        logger.info(f"🔍 Checking R2 for tile: dataset={dataset_id}, z={z}, x={x}, y={y}, format={format}")
        
        # Check if tiles have been uploaded to R2 (metadata flag)
        tiles_on_r2 = (
            dataset.extra_metadata and 
            dataset.extra_metadata.get('tiles_uploaded_to_cloud') == True
        )
        logger.info(f"📋 Metadata flag 'tiles_uploaded_to_cloud': {tiles_on_r2}")
        
        # If flag not set, check R2 directly (for datasets synced from cloud)
        if not tiles_on_r2:
            logger.info(f"🔎 Metadata flag not set, checking R2 directly...")
            tiles_on_r2 = cloud_storage.tile_exists(dataset_id, z, x, y, format)
            logger.info(f"✓ R2 check result for {format}: {tiles_on_r2}")
            
            # If exact format not found, try alternatives
            if not tiles_on_r2:
                if format.lower() in ["jpg", "jpeg"]:
                    logger.info(f"🔄 Trying PNG alternative...")
                    tiles_on_r2 = cloud_storage.tile_exists(dataset_id, z, x, y, "png")
                    if tiles_on_r2:
                        format = "png"
                        logger.info(f"✅ Found PNG alternative")
                elif format.lower() == "png":
                    logger.info(f"🔄 Trying JPG alternative...")
                    tiles_on_r2 = cloud_storage.tile_exists(dataset_id, z, x, y, "jpg")
                    if tiles_on_r2:
                        format = "jpg"
                        logger.info(f"✅ Found JPG alternative")
        
        if tiles_on_r2:
            # Generate R2 public URL and redirect
            tile_url = cloud_storage.get_tile_url(dataset_id, z, x, y, format, cache_bust)
            if tile_url:
                logger.info(f"🔗 Serving tile from R2: {dataset_id}/{z}/{x}/{y}.{format} → {tile_url}")
                return RedirectResponse(
                    url=tile_url,
                    status_code=302,
                    headers={
                        "Cache-Control": "public, max-age=31536000",
                        "Access-Control-Allow-Origin": "*",
                    }
                )

        # If we get here and cloud storage is enabled, log that we're falling back to local
        if cloud_storage.enabled:
            logger.warning(f"❌ Tile not found on R2 for dataset {dataset_id}/{z}/{x}/{y}.{format}, checking local storage")

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
