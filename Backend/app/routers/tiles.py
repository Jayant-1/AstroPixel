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

    # Check if tiles were uploaded to cloud storage (R2)
    # Only redirect if we have evidence tiles exist in R2
    tiles_in_cloud = False
    if cloud_storage.enabled and cloud_storage.public_url:
        # Check if dataset has cloud storage metadata indicating successful upload
        if dataset.extra_metadata and dataset.extra_metadata.get('tiles_uploaded_to_cloud'):
            tiles_in_cloud = True
        # Also check if preview_url exists (means R2 upload happened)
        elif dataset.extra_metadata and dataset.extra_metadata.get('preview_url'):
            tiles_in_cloud = True
    
    if tiles_in_cloud:
        # Redirect to R2 public URL for better performance
        tile_url = cloud_storage.get_tile_url(dataset_id, z, x, y, format)
        logger.debug(f"Redirecting to R2: {tile_url}")
        if tile_url:
            return RedirectResponse(
                url=tile_url,
                status_code=302,
                headers={"Cache-Control": "public, max-age=31536000"}
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
    if cloud_storage.enabled and cloud_storage.public_url:
        # Check if dataset has preview_url in metadata
        if dataset.extra_metadata and dataset.extra_metadata.get('preview_url'):
            return RedirectResponse(
                url=dataset.extra_metadata['preview_url'],
                status_code=302,
                headers={"Cache-Control": "public, max-age=86400"}
            )
        # Fallback to constructing R2 URL
        preview_url = f"{cloud_storage.public_url}/previews/{dataset_id}_preview.jpg"
        return RedirectResponse(
            url=preview_url,
            status_code=302,
            headers={"Cache-Control": "public, max-age=86400"}
        )

    # Fallback to local file
    preview_path = settings.DATASETS_DIR / f"{dataset_id}_preview.jpg"

    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Preview not available")

    return FileResponse(
        preview_path,
        media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},  # 1 day
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
