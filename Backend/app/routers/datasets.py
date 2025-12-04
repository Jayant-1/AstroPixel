"""
Dataset management endpoints
"""

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Query,
    HTTPException,
    BackgroundTasks,
)
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
import logging
import shutil
import re

from app.database import get_db
from app.models import Dataset
from app.schemas import (
    DatasetCreate,
    DatasetResponse,
    DatasetDetail,
    DatasetUpdate,
    MessageResponse,
    ProcessingStatus,
    DatasetStats,
)
from app.services.storage import cloud_storage
from app.services.dataset_processor import DatasetProcessor
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


# This route handles /datasets/{id}_preview.jpg requests
# Must be defined in main.py BEFORE the static mount to work
preview_router = APIRouter()


@preview_router.get("/datasets/{dataset_id}_preview.jpg")
async def get_dataset_preview(dataset_id: int, db: Session = Depends(get_db)):
    """
    Get preview thumbnail for a dataset - redirects to R2 if cloud storage enabled
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
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.post("/datasets/upload", response_model=DatasetResponse, status_code=201)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str = Query(..., description="Dataset name"),
    description: Optional[str] = Query(None, description="Dataset description"),
    category: str = Query(
        ..., description="Dataset category", pattern="^(earth|mars|space)$"
    ),
    db: Session = Depends(get_db),
):
    """
    Upload and process a new dataset

    - **file**: Image file (.tif, .tiff, .psb, .psd) - Supports GeoTIFF and Photoshop Big formats
    - **name**: Unique dataset name
    - **description**: Optional description
    - **category**: Dataset category (earth, mars, or space)
    """
    # Validate file type - support TIFF and PSB/PSD files
    valid_extensions = (".tif", ".tiff", ".TIF", ".TIFF", ".psb", ".PSB", ".psd", ".PSD")
    if not file.filename.endswith(valid_extensions):
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file format. Supported formats: .tif, .tiff, .psb, .psd"
        )

    # Check file size (40GB limit - supports large PSB files up to 25GB+)
    if file.size and file.size > settings.MAX_UPLOAD_SIZE:
        size_gb = file.size / (1024**3)
        max_gb = settings.MAX_UPLOAD_SIZE / (1024**3)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_gb:.1f}GB (you uploaded {size_gb:.1f}GB)",
        )

    # Save uploaded file
    file_path = settings.UPLOAD_DIR / file.filename
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"Saved uploaded file: {file_path}")
    except Exception as e:
        logger.error(f"Error saving uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Error saving file")

    # Create dataset info
    dataset_info = DatasetCreate(name=name, description=description, category=category)

    # Create dataset entry immediately (with pending status)
    try:
        dataset = await DatasetProcessor.create_dataset_entry(file_path, dataset_info, db)
        
        # Start background tile generation (pass dataset.id, not db session)
        background_tasks.add_task(
            DatasetProcessor.process_tiles_background,
            dataset.id,
            file_path
        )
        
        logger.info(f"Dataset {dataset.id} created, tile generation started in background")
        return dataset
        
    except ValueError as e:
        # Clean up uploaded file
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # Clean up uploaded file
        if file_path.exists():
            file_path.unlink()
        logger.error(f"Error creating dataset: {e}")
        raise HTTPException(status_code=500, detail="Error creating dataset")


@router.post("/datasets/from-folder", response_model=MessageResponse)
async def process_folder_datasets(
    folder_path: str = Query(..., description="Path to folder containing .tif files"),
    db: Session = Depends(get_db),
):
    """
    Process all GeoTIFF files from a specified folder

    - **folder_path**: Path to folder containing .tif files
    """
    folder = Path(folder_path)

    if not folder.exists() or not folder.is_dir():
        raise HTTPException(status_code=400, detail="Invalid folder path")

    # Find all .tif and .psb files
    tif_files = list(folder.glob("*.tif")) + list(folder.glob("*.tiff"))
    tif_files += list(folder.glob("*.TIF")) + list(folder.glob("*.TIFF"))
    tif_files += list(folder.glob("*.psb")) + list(folder.glob("*.PSB"))

    if not tif_files:
        raise HTTPException(status_code=400, detail="No .tif or .psb files found in folder")

    processed_count = 0
    failed_count = 0

    for tif_file in tif_files:
        # Auto-detect category from filename
        filename_lower = tif_file.stem.lower()
        if any(
            word in filename_lower for word in ["earth", "landsat", "modis", "sentinel"]
        ):
            category = "earth"
        elif any(word in filename_lower for word in ["mars", "hirise", "ctx"]):
            category = "mars"
        elif any(
            word in filename_lower for word in ["messier", "ngc", "galaxy", "nebula"]
        ):
            category = "space"
        else:
            category = "space"  # Default

        dataset_info = DatasetCreate(
            name=tif_file.stem,
            description=f"Auto-imported from {tif_file.name}",
            category=category,
        )

        try:
            dataset = await DatasetProcessor.process_dataset(tif_file, dataset_info, db)
            processed_count += 1
            logger.info(f"Processed dataset: {dataset.name}")
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to process {tif_file.name}: {e}")

    return MessageResponse(
        message=f"Processed {processed_count} datasets successfully",
        detail=f"{failed_count} failed" if failed_count > 0 else None,
    )


@router.get("/datasets", response_model=List[DatasetResponse])
async def list_datasets(
    category: Optional[str] = Query(None, description="Filter by category"),
    status: Optional[str] = Query(None, description="Filter by processing status"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of records to return"
    ),
    db: Session = Depends(get_db),
):
    """
    List all datasets with optional filtering

    - **category**: Filter by category (earth, mars, space)
    - **status**: Filter by processing status (pending, processing, completed, failed)
    - **skip**: Pagination offset
    - **limit**: Maximum results to return
    """
    query = db.query(Dataset)

    if category:
        query = query.filter(Dataset.category == category)

    if status:
        query = query.filter(Dataset.processing_status == status)

    datasets = query.order_by(Dataset.created_at.desc()).offset(skip).limit(limit).all()
    return datasets


@router.get("/datasets/{dataset_id}", response_model=DatasetDetail)
async def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """
    Get detailed information about a specific dataset

    - **dataset_id**: ID of the dataset
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return dataset


@router.put("/datasets/{dataset_id}", response_model=DatasetResponse)
async def update_dataset(
    dataset_id: int, dataset_update: DatasetUpdate, db: Session = Depends(get_db)
):
    """
    Update dataset metadata

    - **dataset_id**: ID of the dataset
    - **dataset_update**: Fields to update
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Update fields
    if dataset_update.name is not None:
        dataset.name = dataset_update.name
    if dataset_update.description is not None:
        dataset.description = dataset_update.description
    if dataset_update.category is not None:
        dataset.category = dataset_update.category

    db.commit()
    db.refresh(dataset)

    return dataset


@router.delete("/datasets/{dataset_id}", response_model=MessageResponse)
async def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """
    Delete dataset and associated tiles

    - **dataset_id**: ID of the dataset to delete
    """
    success = DatasetProcessor.delete_dataset(dataset_id, db)

    if not success:
        raise HTTPException(
            status_code=404, detail="Dataset not found or could not be deleted"
        )

    return MessageResponse(message=f"Dataset {dataset_id} deleted successfully")


@router.get("/datasets/{dataset_id}/status", response_model=ProcessingStatus)
async def get_processing_status(dataset_id: int, db: Session = Depends(get_db)):
    """
    Get dataset processing status

    - **dataset_id**: ID of the dataset
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return ProcessingStatus(
        status=dataset.processing_status,
        message=f"Dataset is {dataset.processing_status}",
        progress=1.0 if dataset.processing_status == "completed" else 0.0,
    )


@router.post("/datasets/{dataset_id}/reprocess", response_model=MessageResponse)
async def reprocess_dataset(dataset_id: int, db: Session = Depends(get_db)):
    """
    Regenerate tiles for an existing dataset

    - **dataset_id**: ID of the dataset to reprocess
    """
    success = DatasetProcessor.reprocess_dataset(dataset_id, db)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to reprocess dataset")

    return MessageResponse(message=f"Dataset {dataset_id} reprocessing started")


@router.get("/stats", response_model=DatasetStats)
async def get_statistics(db: Session = Depends(get_db)):
    """
    Get overall dataset statistics
    """
    stats = DatasetProcessor.get_dataset_stats(db)

    # Count total annotations
    from app.models import Annotation

    total_annotations = db.query(Annotation).count()

    return DatasetStats(
        total_datasets=stats.get("total_datasets", 0),
        datasets_by_category=stats.get("by_category", {}),
        total_annotations=total_annotations,
        total_storage_size=stats.get("total_pixels", 0) * 3,  # Rough estimate
    )
