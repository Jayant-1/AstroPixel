"""
Search and discovery endpoints
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional
import logging

from app.database import get_db
from app.models import Annotation, Dataset
from app.schemas import (
    AnnotationResponse,
    DatasetResponse,
    ComparisonRequest,
    ComparisonResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/search", response_model=List[AnnotationResponse])
async def search_annotations(
    q: str = Query(..., min_length=1, description="Search query"),
    dataset_id: Optional[int] = Query(None, description="Filter by dataset"),
    category: Optional[str] = Query(None, description="Filter by dataset category"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Full-text search for annotations

    - **q**: Search query (searches in label and description)
    - **dataset_id**: Optional dataset filter
    - **category**: Optional category filter
    - **limit**: Maximum results
    - **offset**: Pagination offset
    """
    # Build base query
    query = db.query(Annotation)

    # Add full-text search
    search_filter = or_(
        Annotation.label.ilike(f"%{q}%"), Annotation.description.ilike(f"%{q}%")
    )
    query = query.filter(search_filter)

    # Filter by dataset if provided
    if dataset_id:
        query = query.filter(Annotation.dataset_id == dataset_id)

    # Filter by category if provided
    if category:
        query = query.join(Dataset).filter(Dataset.category == category)

    # Execute query
    annotations = (
        query.order_by(Annotation.created_at.desc()).offset(offset).limit(limit).all()
    )

    # Convert to response format
    result = [
        {
            "id": ann.id,
            "dataset_id": ann.dataset_id,
            "user_id": ann.user_id,
            "geometry": ann.geometry_json,
            "annotation_type": ann.annotation_type,
            "label": ann.label,
            "description": ann.description,
            "properties": ann.properties,
            "confidence": ann.confidence,
            "created_at": ann.created_at,
            "updated_at": ann.updated_at,
        }
        for ann in annotations
    ]

    logger.info(f"Search for '{q}' returned {len(result)} results")
    return result


@router.get("/search/spatial", response_model=List[AnnotationResponse])
async def spatial_search(
    bbox: str = Query(..., description="Bounding box: minx,miny,maxx,maxy"),
    dataset_id: Optional[int] = Query(None, description="Filter by dataset"),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Spatial search for annotations within a bounding box
    Basic implementation using geometry_json - for production use PostGIS for better performance

    - **bbox**: Bounding box as "minx,miny,maxx,maxy"
    - **dataset_id**: Optional dataset filter
    - **limit**: Maximum results
    """
    # Parse bbox
    try:
        coords = [float(c) for c in bbox.split(",")]
        if len(coords) != 4:
            raise ValueError("Invalid bbox")
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid bbox format. Use: minx,miny,maxx,maxy"
        )

    minx, miny, maxx, maxy = coords

    # Build query
    query = db.query(Annotation)
    
    if dataset_id:
        query = query.filter(Annotation.dataset_id == dataset_id)

    annotations = query.limit(limit * 2).all()  # Get more to filter

    # Filter annotations by bbox (simple implementation)
    result = []
    for ann in annotations:
        if len(result) >= limit:
            break
            
        try:
            # Check if annotation geometry intersects bbox
            geometry = ann.geometry_json
            if geometry and "coordinates" in geometry:
                # Simple containment check for point geometries
                if geometry["type"] == "Point":
                    lon, lat = geometry["coordinates"]
                    if minx <= lon <= maxx and miny <= lat <= maxy:
                        result.append({
                            "id": ann.id,
                            "dataset_id": ann.dataset_id,
                            "user_id": ann.user_id,
                            "geometry": ann.geometry_json,
                            "annotation_type": ann.annotation_type,
                            "label": ann.label,
                            "description": ann.description,
                            "properties": ann.properties,
                            "confidence": ann.confidence,
                            "created_at": ann.created_at,
                            "updated_at": ann.updated_at,
                        })
        except Exception as e:
            logger.error(f"Error processing annotation {ann.id}: {e}")
            continue

    logger.info(f"Spatial search in bbox returned {len(result)} results")
    return result


@router.get("/search/similar")
async def find_similar(
    annotation_id: int = Query(..., description="Reference annotation ID"),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Find annotations similar to a reference annotation
    (Placeholder for AI-powered similarity search)

    - **annotation_id**: ID of reference annotation
    - **limit**: Maximum results
    """
    # Get reference annotation
    ref_annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()

    if not ref_annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    # Simple similarity based on label matching (can be enhanced with ML)
    similar = (
        db.query(Annotation)
        .filter(
            Annotation.id != annotation_id,
            Annotation.label.ilike(f"%{ref_annotation.label}%"),
        )
        .limit(limit)
        .all()
    )

    # Convert to response format
    result = [
        {
            "id": ann.id,
            "dataset_id": ann.dataset_id,
            "user_id": ann.user_id,
            "geometry": ann.geometry_json,
            "annotation_type": ann.annotation_type,
            "label": ann.label,
            "description": ann.description,
            "properties": ann.properties,
            "confidence": ann.confidence,
            "created_at": ann.created_at,
            "updated_at": ann.updated_at,
        }
        for ann in similar
    ]

    logger.info(
        f"Similar search for annotation {annotation_id} returned {len(result)} results"
    )
    return result


@router.post("/compare", response_model=ComparisonResponse)
async def compare_datasets(request: ComparisonRequest, db: Session = Depends(get_db)):
    """
    Get metadata for comparing multiple datasets

    - **request**: List of dataset IDs to compare (2-4 datasets)
    """
    if len(request.dataset_ids) < 2:
        raise HTTPException(
            status_code=400, detail="At least 2 datasets required for comparison"
        )

    if len(request.dataset_ids) > 4:
        raise HTTPException(
            status_code=400, detail="Maximum 4 datasets can be compared"
        )

    # Get datasets
    datasets = db.query(Dataset).filter(Dataset.id.in_(request.dataset_ids)).all()

    if len(datasets) != len(request.dataset_ids):
        raise HTTPException(status_code=404, detail="One or more datasets not found")

    return ComparisonResponse(datasets=datasets)


@router.get("/search/datasets", response_model=List[DatasetResponse])
async def search_datasets(
    q: str = Query(..., min_length=1, description="Search query"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    """
    Search datasets by name or description

    - **q**: Search query
    - **category**: Optional category filter
    - **limit**: Maximum results
    - **offset**: Pagination offset
    """
    # Build query
    query = db.query(Dataset)

    # Add search filter
    search_filter = or_(
        Dataset.name.ilike(f"%{q}%"), Dataset.description.ilike(f"%{q}%")
    )
    query = query.filter(search_filter)

    # Filter by category
    if category:
        query = query.filter(Dataset.category == category)

    # Execute
    datasets = (
        query.order_by(Dataset.created_at.desc()).offset(offset).limit(limit).all()
    )

    logger.info(f"Dataset search for '{q}' returned {len(datasets)} results")
    return datasets
