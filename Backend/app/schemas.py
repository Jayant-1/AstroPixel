"""
Pydantic schemas for API request/response validation
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime


# ===========================
# Dataset Schemas
# ===========================


class DatasetCreate(BaseModel):
    """Schema for creating a new dataset"""

    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., pattern="^(earth|mars|space)$")

    @validator("name")
    def validate_name(cls, v):
        if not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()


class DatasetUpdate(BaseModel):
    """Schema for updating dataset metadata"""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(None, pattern="^(earth|mars|space)$")


class DatasetResponse(BaseModel):
    """Schema for dataset response"""

    id: int
    name: str
    description: Optional[str]
    category: str
    width: int
    height: int
    max_zoom: int
    min_zoom: int
    tile_size: int
    processing_status: str
    processing_progress: int = 0  # 0-100 percentage
    created_at: datetime
    updated_at: datetime
    extra_metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class DatasetDetail(DatasetResponse):
    """Detailed dataset response with additional fields"""

    original_file_path: str
    tile_base_path: str
    projection: Optional[str]
    geotransform: Optional[Any] = None  # Can be list or dict
    bounds_json: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# ===========================
# Annotation Schemas
# ===========================


class AnnotationCreate(BaseModel):
    """Schema for creating an annotation"""

    dataset_id: int
    user_id: str = "anonymous"
    geometry: Dict[str, Any]  # GeoJSON geometry
    annotation_type: str = Field(..., pattern="^(point|polygon|rectangle|circle)$")
    label: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = ""
    properties: Optional[Dict[str, Any]] = {}
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @validator("geometry")
    def validate_geometry(cls, v):
        if "type" not in v or "coordinates" not in v:
            raise ValueError("Invalid GeoJSON geometry")
        return v


class AnnotationUpdate(BaseModel):
    """Schema for updating an annotation"""

    label: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    properties: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)


class AnnotationResponse(BaseModel):
    """Schema for annotation response"""

    id: int
    dataset_id: int
    user_id: str
    geometry: Dict[str, Any]
    annotation_type: str
    label: str
    description: Optional[str]
    properties: Dict[str, Any]
    confidence: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AnnotationBatchCreate(BaseModel):
    """Schema for batch creating annotations"""

    annotations: List[AnnotationCreate]


# ===========================
# Search Schemas
# ===========================


class SearchQuery(BaseModel):
    """Schema for search query"""

    q: str = Field(..., min_length=1)
    dataset_id: Optional[int] = None
    category: Optional[str] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


class SpatialQuery(BaseModel):
    """Schema for spatial search query"""

    bbox: str = Field(..., description="Bounding box: minx,miny,maxx,maxy")
    dataset_id: Optional[int] = None
    limit: int = Field(default=100, ge=1, le=1000)

    @validator("bbox")
    def validate_bbox(cls, v):
        coords = v.split(",")
        if len(coords) != 4:
            raise ValueError("BBox must have 4 coordinates")
        try:
            [float(c) for c in coords]
        except ValueError:
            raise ValueError("BBox coordinates must be numbers")
        return v


# ===========================
# Processing Schemas
# ===========================


class ProcessingStatus(BaseModel):
    """Schema for processing status"""

    status: str
    progress: Optional[float] = None
    message: Optional[str] = None
    task_id: Optional[str] = None


class ProcessingJobResponse(BaseModel):
    """Schema for processing job response"""

    id: int
    dataset_id: int
    task_id: str
    status: str
    progress: float
    error_message: Optional[str]
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ===========================
# Comparison Schemas
# ===========================


class ComparisonRequest(BaseModel):
    """Schema for comparison request"""

    dataset_ids: List[int] = Field(..., min_items=2, max_items=4)


class ComparisonResponse(BaseModel):
    """Schema for comparison response"""

    datasets: List[DatasetResponse]


# ===========================
# Statistics Schemas
# ===========================


class DatasetStats(BaseModel):
    """Schema for dataset statistics"""

    total_datasets: int
    datasets_by_category: Dict[str, int]
    total_annotations: int
    total_storage_size: int


# ===========================
# Utility Schemas
# ===========================


class MessageResponse(BaseModel):
    """Generic message response"""

    message: str
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response"""

    status: str
    timestamp: datetime
    database: bool
    redis: bool
