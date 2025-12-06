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
    Form,
)
from fastapi.responses import RedirectResponse, FileResponse, JSONResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
import logging
import shutil
import re
import aiofiles
import uuid
import os

from datetime import datetime, timedelta

from app.database import get_db
from app.models import Dataset, User
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
from app.services.cleanup import get_time_until_expiry
from app.services.auth import get_current_user, get_current_user_required
from app.config import settings

# Optimized chunk size for fast uploads (8MB chunks)
UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024  # 8MB

# Store for tracking chunked uploads
chunked_uploads = {}

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


# ============================================================================
# CHUNKED UPLOAD ENDPOINTS - For large files (10GB+)
# ============================================================================

@router.post("/datasets/upload/init")
async def init_chunked_upload(
    filename: str = Query(..., description="Original filename"),
    filesize: int = Query(..., description="Total file size in bytes"),
    total_chunks: int = Query(..., description="Total number of chunks"),
):
    """
    Initialize a chunked upload session for large files.
    Returns an upload_id to use for subsequent chunk uploads.
    """
    # Validate file type
    valid_extensions = (".tif", ".tiff", ".TIF", ".TIFF", ".psb", ".PSB", ".psd", ".PSD")
    if not filename.endswith(valid_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format. Supported: .tif, .tiff, .psb, .psd"
        )
    
    # Generate unique upload ID
    upload_id = str(uuid.uuid4())
    
    # Create temp directory for chunks
    temp_dir = settings.TEMP_DIR / upload_id
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    # Store upload session info
    chunked_uploads[upload_id] = {
        "filename": filename,
        "filesize": filesize,
        "total_chunks": total_chunks,
        "received_chunks": set(),
        "temp_dir": temp_dir,
    }
    
    logger.info(f"Initialized chunked upload: {upload_id} for {filename} ({filesize / (1024**3):.2f} GB, {total_chunks} chunks)")
    
    return {
        "upload_id": upload_id,
        "chunk_size": UPLOAD_CHUNK_SIZE,
        "message": "Upload initialized. Send chunks to /api/datasets/upload/chunk"
    }


@router.post("/datasets/upload/chunk")
async def upload_chunk(
    upload_id: str = Form(...),
    chunk_index: int = Form(...),
    chunk: UploadFile = File(...),
):
    """
    Upload a single chunk of a large file.
    """
    if upload_id not in chunked_uploads:
        raise HTTPException(status_code=404, detail="Upload session not found. Initialize first.")
    
    session = chunked_uploads[upload_id]
    
    # Save chunk to temp directory
    chunk_path = session["temp_dir"] / f"chunk_{chunk_index:06d}"
    
    try:
        async with aiofiles.open(chunk_path, "wb") as f:
            content = await chunk.read()
            await f.write(content)
        
        session["received_chunks"].add(chunk_index)
        received = len(session["received_chunks"])
        total = session["total_chunks"]
        
        logger.debug(f"Chunk {chunk_index} received for {upload_id} ({received}/{total})")
        
        return {
            "chunk_index": chunk_index,
            "received": received,
            "total": total,
            "complete": received == total
        }
    except Exception as e:
        logger.error(f"Error saving chunk {chunk_index}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save chunk: {str(e)}")


@router.post("/datasets/upload/complete", response_model=DatasetResponse)
async def complete_chunked_upload(
    background_tasks: BackgroundTasks,
    upload_id: str = Query(...),
    name: str = Query(..., description="Dataset name"),
    description: Optional[str] = Query(None),
    category: str = Query(..., pattern="^(earth|mars|space)$"),
    db: Session = Depends(get_db),
):
    """
    Complete a chunked upload by assembling chunks and processing the dataset.
    """
    if upload_id not in chunked_uploads:
        raise HTTPException(status_code=404, detail="Upload session not found")
    
    session = chunked_uploads[upload_id]
    
    # Verify all chunks received
    if len(session["received_chunks"]) != session["total_chunks"]:
        missing = session["total_chunks"] - len(session["received_chunks"])
        raise HTTPException(
            status_code=400,
            detail=f"Upload incomplete. Missing {missing} chunks."
        )
    
    # Assemble chunks into final file
    final_path = settings.UPLOAD_DIR / session["filename"]
    
    try:
        logger.info(f"Assembling {session['total_chunks']} chunks into {final_path}")
        
        async with aiofiles.open(final_path, "wb") as outfile:
            for i in range(session["total_chunks"]):
                chunk_path = session["temp_dir"] / f"chunk_{i:06d}"
                async with aiofiles.open(chunk_path, "rb") as chunk_file:
                    content = await chunk_file.read()
                    await outfile.write(content)
        
        logger.info(f"File assembled: {final_path} ({final_path.stat().st_size / (1024**3):.2f} GB)")
        
        # Clean up temp chunks
        shutil.rmtree(session["temp_dir"], ignore_errors=True)
        del chunked_uploads[upload_id]
        
        # Create dataset (same as regular upload)
        dataset_info = DatasetCreate(name=name, description=description, category=category)
        
        try:
            dataset = await DatasetProcessor.create_dataset_entry(final_path, dataset_info, db)
        except ValueError as ve:
            logger.error(f"Dataset creation failed (ValueError): {ve}")
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as de:
            logger.error(f"Dataset creation failed: {de}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Failed to create dataset: {str(de)}")
        
        background_tasks.add_task(
            DatasetProcessor.process_tiles_background,
            dataset.id,
            final_path
        )
        
        logger.info(f"Dataset {dataset.id} created from chunked upload")
        return dataset
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        logger.error(f"Error completing chunked upload: {e}", exc_info=True)
        # Clean up on error
        if upload_id in chunked_uploads:
            shutil.rmtree(session["temp_dir"], ignore_errors=True)
            del chunked_uploads[upload_id]
        raise HTTPException(status_code=500, detail=f"Failed to complete upload: {str(e)}")


@router.delete("/datasets/upload/{upload_id}")
async def cancel_chunked_upload(upload_id: str):
    """Cancel and clean up a chunked upload session."""
    if upload_id not in chunked_uploads:
        raise HTTPException(status_code=404, detail="Upload session not found")
    
    session = chunked_uploads[upload_id]
    shutil.rmtree(session["temp_dir"], ignore_errors=True)
    del chunked_uploads[upload_id]
    
    return {"message": "Upload cancelled and cleaned up"}


# ============================================================================
# REGULAR UPLOAD ENDPOINT
# ============================================================================

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
    current_user = Depends(get_current_user_required),
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

    # Save uploaded file with optimized async streaming
    file_path = settings.UPLOAD_DIR / file.filename
    try:
        # Use async file writing with large chunks for speed
        async with aiofiles.open(file_path, "wb") as buffer:
            while chunk := await file.read(UPLOAD_CHUNK_SIZE):
                await buffer.write(chunk)
        logger.info(f"Saved uploaded file: {file_path}")
    except Exception as e:
        logger.error(f"Error saving uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Error saving file")

    # Create dataset info
    dataset_info = DatasetCreate(name=name, description=description, category=category)

    # Create dataset entry immediately (with pending status)
    try:
        dataset = await DatasetProcessor.create_dataset_entry(file_path, dataset_info, db)
        
        # Set owner and expiry for user uploads (not demo datasets)
        dataset.owner_id = current_user.id
        dataset.is_demo = False
        dataset.expires_at = datetime.utcnow() + timedelta(hours=24)
        db.commit()
        db.refresh(dataset)
        
        # Start background tile generation (pass dataset.id, not db session)
        background_tasks.add_task(
            DatasetProcessor.process_tiles_background,
            dataset.id,
            file_path
        )
        
        logger.info(f"Dataset {dataset.id} created by user {current_user.id}, expires at {dataset.expires_at}")
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
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    List datasets:
    - Authenticated users: Only their own datasets
    - Guest users: Only demo datasets (is_demo=True)

    - **category**: Filter by category (earth, mars, space)
    - **status**: Filter by processing status (pending, processing, completed, failed)
    - **skip**: Pagination offset
    - **limit**: Maximum results to return
    """
    query = db.query(Dataset)

    # Filter by ownership: users see only their datasets, guests see only demos
    if current_user:
        # Authenticated user: show only their datasets
        query = query.filter(Dataset.owner_id == current_user.id)
    else:
        # Guest user: show only demo datasets
        query = query.filter(Dataset.is_demo == True)

    if category:
        query = query.filter(Dataset.category == category)

    if status:
        query = query.filter(Dataset.processing_status == status)

    datasets = query.order_by(Dataset.created_at.desc()).offset(skip).limit(limit).all()
    
    # Calculate time_until_expiry for datasets expiring within 1 hour
    result = []
    for dataset in datasets:
        dataset_dict = DatasetResponse.model_validate(dataset).model_dump()
        
        # Add time until expiry if dataset expires within 1 hour
        if dataset.expires_at:
            now = datetime.utcnow()
            time_left = (dataset.expires_at - now).total_seconds()
            if 0 < time_left <= 3600:  # Show only if expiring within 1 hour
                dataset_dict['time_until_expiry'] = get_time_until_expiry(dataset.expires_at)
        
        result.append(DatasetResponse(**dataset_dict))
    
    return result


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
    dataset_id: int, 
    dataset_update: DatasetUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    Update dataset metadata
    
    Restrictions:
    - Only the owner can update their dataset
    - Demo datasets cannot be modified

    - **dataset_id**: ID of the dataset
    - **dataset_update**: Fields to update
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Prevent modification of demo datasets
    if dataset.is_demo:
        raise HTTPException(
            status_code=403,
            detail="Demo datasets cannot be modified"
        )
    
    # Check ownership
    if dataset.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to update this dataset"
        )

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
async def delete_dataset(
    dataset_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required)
):
    """
    Delete dataset and associated tiles
    
    Restrictions:
    - Only the owner can delete their dataset
    - Demo datasets cannot be deleted by anyone

    - **dataset_id**: ID of the dataset to delete
    """
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Prevent deletion of demo datasets
    if dataset.is_demo:
        raise HTTPException(
            status_code=403, 
            detail="Demo datasets cannot be deleted"
        )
    
    # Check ownership
    if dataset.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You don't have permission to delete this dataset"
        )
    
    success = DatasetProcessor.delete_dataset(dataset_id, db)

    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to delete dataset"
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
