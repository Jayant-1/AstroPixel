"""
Simple annotation endpoints that work without PostGIS
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from app.database import get_db
from app.models import Annotation, Dataset
from app.schemas import (
    AnnotationCreate,
    AnnotationUpdate,
    AnnotationResponse,
    MessageResponse,
)

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/annotations/{dataset_id}", response_model=List[AnnotationResponse])
async def get_annotations_by_dataset(
    dataset_id: int,
    annotation_type: Optional[str] = Query(
        None, description="Filter by annotation type"
    ),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
):
    """
    Get all annotations for a specific dataset with pagination
    
    Optimizations:
    - Indexed query on (dataset_id, annotation_type, user_id)
    - Pagination enabled (default 100 items per page, max 1000)
    - Database-level filtering to minimize data transfer

    - **dataset_id**: ID of the dataset
    - **annotation_type**: Optional filter by type (point, polygon, rectangle, circle)
    - **user_id**: Optional filter by user
    - **skip**: Pagination offset
    - **limit**: Maximum results
    """
    # Verify dataset exists (fast lookup)
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Build optimized query with filters applied at database level
    query = db.query(Annotation).filter(Annotation.dataset_id == dataset_id)

    if annotation_type:
        query = query.filter(Annotation.annotation_type == annotation_type)

    if user_id:
        query = query.filter(Annotation.user_id == user_id)

    # Apply pagination at database level (more efficient than in-memory)
    annotations = query.order_by(Annotation.created_at.desc()).offset(skip).limit(limit).all()

    # Convert geometry_json to proper format for response
    result = []
    for ann in annotations:
        ann_dict = {
            "id": ann.id,
            "dataset_id": ann.dataset_id,
            "user_id": ann.user_id,
            "geometry": ann.geometry_json,  # Already in JSON format
            "annotation_type": ann.annotation_type,
            "label": ann.label,
            "description": ann.description,
            "properties": ann.properties,
            "confidence": ann.confidence,
            "created_at": ann.created_at,
            "updated_at": ann.updated_at,
        }
        result.append(ann_dict)

    return result


@router.post("/annotations", response_model=AnnotationResponse, status_code=201)
async def create_annotation(
    annotation: AnnotationCreate,
    db: Session = Depends(get_db),
):
    """
    Create a new annotation

    - **dataset_id**: ID of the dataset
    - **geometry**: GeoJSON geometry object
    - **annotation_type**: Type of annotation (point, polygon, rectangle, circle)
    - **label**: Label for the annotation
    - **description**: Optional description
    - **properties**: Optional additional properties
    - **confidence**: Confidence score (0.0-1.0)
    """
    # Verify dataset exists
    dataset = db.query(Dataset).filter(Dataset.id == annotation.dataset_id).first()
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Create annotation with geometry as JSON
    new_annotation = Annotation(
        dataset_id=annotation.dataset_id,
        user_id=annotation.user_id,
        geometry_json=annotation.geometry,  # Store as JSON
        annotation_type=annotation.annotation_type,
        label=annotation.label,
        description=annotation.description,
        properties=annotation.properties,
        confidence=annotation.confidence,
    )

    db.add(new_annotation)
    db.commit()
    db.refresh(new_annotation)

    logger.info(
        f"Created annotation {new_annotation.id} for dataset {annotation.dataset_id}"
    )

    return {
        "id": new_annotation.id,
        "dataset_id": new_annotation.dataset_id,
        "user_id": new_annotation.user_id,
        "geometry": new_annotation.geometry_json,
        "annotation_type": new_annotation.annotation_type,
        "label": new_annotation.label,
        "description": new_annotation.description,
        "properties": new_annotation.properties,
        "confidence": new_annotation.confidence,
        "created_at": new_annotation.created_at,
        "updated_at": new_annotation.updated_at,
    }


@router.put("/annotations/{annotation_id}", response_model=AnnotationResponse)
async def update_annotation(
    annotation_id: int,
    annotation_update: AnnotationUpdate,
    db: Session = Depends(get_db),
):
    """
    Update an existing annotation

    - **annotation_id**: ID of the annotation to update
    - **annotation_update**: Fields to update (label, description, properties, confidence)
    """
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()

    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    # Update fields if provided
    if annotation_update.label is not None:
        annotation.label = annotation_update.label
    if annotation_update.description is not None:
        annotation.description = annotation_update.description
    if annotation_update.properties is not None:
        annotation.properties = annotation_update.properties
    if annotation_update.confidence is not None:
        annotation.confidence = annotation_update.confidence

    db.commit()
    db.refresh(annotation)

    logger.info(f"Updated annotation {annotation_id}")

    return {
        "id": annotation.id,
        "dataset_id": annotation.dataset_id,
        "user_id": annotation.user_id,
        "geometry": annotation.geometry_json,
        "annotation_type": annotation.annotation_type,
        "label": annotation.label,
        "description": annotation.description,
        "properties": annotation.properties,
        "confidence": annotation.confidence,
        "created_at": annotation.created_at,
        "updated_at": annotation.updated_at,
    }


@router.delete("/annotations/{annotation_id}", response_model=MessageResponse)
async def delete_annotation(
    annotation_id: int,
    db: Session = Depends(get_db),
):
    """
    Delete an annotation

    - **annotation_id**: ID of the annotation to delete
    """
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()

    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    db.delete(annotation)
    db.commit()

    logger.info(f"Deleted annotation {annotation_id}")

    return MessageResponse(message=f"Annotation {annotation_id} deleted successfully")
