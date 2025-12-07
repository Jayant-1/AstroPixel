"""
Database models for NASA Gigapixel Explorer
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Float,
    Text,
    Boolean,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from datetime import datetime

from app.database import Base


class User(Base):
    """User model for authentication"""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    
    # User status
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    
    # Profile
    avatar_url = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_login = Column(DateTime)

    # Relationships
    datasets = relationship("Dataset", back_populates="owner", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, email='{self.email}', username='{self.username}')>"


class Dataset(Base):
    """Dataset model representing a NASA gigapixel image"""

    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True, nullable=False)
    description = Column(Text)
    category = Column(String(50), index=True)  # earth, mars, space
    
    # Owner
    owner_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)

    # File paths
    original_file_path = Column(Text, nullable=False)
    tile_base_path = Column(Text, nullable=False)

    # Image dimensions
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)

    # Zoom levels
    max_zoom = Column(Integer, nullable=False)
    min_zoom = Column(Integer, default=0)
    tile_size = Column(Integer, default=256)

    # Geospatial metadata
    projection = Column(String(255))
    geotransform = Column(JSON)
    # Note: bounds column disabled for SQLite compatibility
    # For PostgreSQL with PostGIS, uncomment the following line:
    # bounds = Column(Geometry("POLYGON", srid=4326))
    bounds_json = Column(JSON)  # Store bounds as JSON for SQLite

    # Additional metadata
    extra_metadata = Column(JSON)  # Renamed from 'metadata' (SQLAlchemy reserved word)

    # Processing status
    processing_status = Column(
        String(50), default="pending"
    )  # pending, processing, completed, failed
    processing_progress = Column(Integer, default=0)  # 0-100 percentage

    # Visibility and lifecycle management
    is_demo = Column(Boolean, default=False, nullable=False, index=True)  # Demo datasets for guest users
    expires_at = Column(DateTime, nullable=True, index=True)  # Auto-delete timestamp (NULL for demo datasets)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    owner = relationship("User", back_populates="datasets")
    annotations = relationship(
        "Annotation", back_populates="dataset", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return (
            f"<Dataset(id={self.id}, name='{self.name}', category='{self.category}')>"
        )


class Annotation(Base):
    """Annotation model for marking features on datasets"""

    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(
        Integer,
        ForeignKey("datasets.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id = Column(String(255), index=True, nullable=True, default="anonymous")

    # Geometry (PostGIS) - Disabled for SQLite
    # For PostgreSQL with PostGIS, uncomment:
    # geometry = Column(Geometry("GEOMETRY", srid=4326), nullable=False)
    geometry_json = Column(JSON, nullable=False)  # Store geometry as GeoJSON for SQLite
    annotation_type = Column(String(50))  # point, polygon, rectangle, circle

    # Annotation details
    label = Column(String(255), nullable=False, index=True)
    description = Column(Text)
    properties = Column(JSON, default={})
    confidence = Column(Float, default=1.0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    dataset = relationship("Dataset", back_populates="annotations")

    def __repr__(self):
        return f"<Annotation(id={self.id}, dataset_id={self.dataset_id}, label='{self.label}')>"


class ProcessingJob(Base):
    """Model for tracking tile generation jobs"""

    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    dataset_id = Column(
        Integer, ForeignKey("datasets.id", ondelete="CASCADE"), index=True
    )
    task_id = Column(String(255), unique=True, index=True)
    status = Column(
        String(50), default="pending"
    )  # pending, running, completed, failed
    progress = Column(Float, default=0.0)
    error_message = Column(Text)

    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<ProcessingJob(id={self.id}, dataset_id={self.dataset_id}, status='{self.status}')>"
