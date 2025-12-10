"""
Database configuration and session management
"""

from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator
import logging

from app.config import settings

logger = logging.getLogger(__name__)

# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=20,  # Increased from 10 for better concurrency
    max_overflow=40,  # Doubled from 20 for burst traffic
    pool_recycle=3600,  # Recycle connections every hour (prevent stale connections)
    pool_timeout=30,  # Wait up to 30 seconds for a connection
    echo=settings.DEBUG,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for getting database sessions

    Yields:
        Session: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Initialize database (create all tables)"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables created successfully")
        
        # Sync datasets from R2 cloud storage if enabled
        sync_datasets_from_cloud()
        
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


def sync_datasets_from_cloud() -> None:
    """
    Sync dataset metadata from R2 cloud storage to local SQLite database.
    This ensures datasets persist across backend restarts on HF Spaces.
    """
    try:
        # Import here to avoid circular imports
        from app.services.storage import cloud_storage
        from app.models import Dataset
        
        if not cloud_storage.enabled:
            logger.info("Cloud storage not enabled, skipping R2 sync")
            return
        
        # Load datasets from R2
        cloud_datasets = cloud_storage.load_all_datasets_metadata()
        
        if not cloud_datasets:
            logger.info("No datasets found in R2 metadata")
            return
        
        # Sync to local database
        db = SessionLocal()
        try:
            synced = 0
            for ds_data in cloud_datasets:
                # Check if dataset already exists in local DB
                existing = db.query(Dataset).filter(Dataset.id == ds_data.get('id')).first()
                
                if not existing:
                    # Create new dataset from R2 metadata
                    # NOTE: We treat all R2-synced datasets as DEMO datasets per production requirements
                    # Only demo datasets are saved to R2 metadata in the first place
                    
                    # Handle both old and new schema field names
                    original_file_path = ds_data.get('original_file_path') or ds_data.get('original_filename') or 'unknown'
                    tile_base_path = ds_data.get('tile_base_path') or ds_data.get('file_path') or f"tiles/{ds_data.get('id')}"
                    
                    dataset = Dataset(
                        id=ds_data.get('id'),
                        name=ds_data.get('name'),
                        description=ds_data.get('description'),
                        category=ds_data.get('category', 'space'),
                        original_file_path=original_file_path,
                        tile_base_path=tile_base_path,
                        width=ds_data.get('width', 0),
                        height=ds_data.get('height', 0),
                        tile_size=ds_data.get('tile_size', 256),
                        min_zoom=ds_data.get('min_zoom', 0),
                        max_zoom=ds_data.get('max_zoom', 0),
                        processing_status=ds_data.get('processing_status', 'completed'),
                        extra_metadata=ds_data.get('extra_metadata', {}),
                        is_demo=True,  # Mark synced datasets from R2 as demo
                        owner_id=None,  # Demo datasets have no owner
                        expires_at=None,  # Demo datasets never expire
                    )
                    db.add(dataset)
                    synced += 1
                    logger.info(f"✅ Synced dataset from R2: {ds_data.get('name')} (ID: {ds_data.get('id')})")
            
            db.commit()
            logger.info(f"✅ Synced {synced} datasets from R2 to local database")
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"❌ Failed to sync datasets from R2: {e}")
        # Don't raise - this is a best-effort sync


def create_spatial_indexes() -> None:
    """Create spatial indexes for PostGIS tables"""
    # Skip spatial indexes for SQLite (doesn't support GIST)
    if "sqlite" in settings.DATABASE_URL.lower():
        logger.info("Skipping spatial indexes (SQLite doesn't support GIST)")
        return

    try:
        with engine.connect() as conn:
            # Only create spatial indexes if the corresponding columns exist.
            # This avoids errors when running against a Postgres database
            # where the geometry/bounds columns are not present (e.g., migrations
            # not applied or models configured for SQLite compatibility).
            has_annotations_geometry = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='annotations' AND column_name='geometry'"
                )
            ).fetchone()

            if has_annotations_geometry:
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_annotations_geometry "
                        "ON annotations USING GIST(geometry)"
                    )
                )
                logger.info("Created idx_annotations_geometry")
            else:
                logger.info("Skipping idx_annotations_geometry (column not present)")

            has_datasets_bounds = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns "
                    "WHERE table_name='datasets' AND column_name='bounds'"
                )
            ).fetchone()

            if has_datasets_bounds:
                conn.execute(
                    text(
                        "CREATE INDEX IF NOT EXISTS idx_datasets_bounds "
                        "ON datasets USING GIST(bounds)"
                    )
                )
                logger.info("Created idx_datasets_bounds")
            else:
                logger.info("Skipping idx_datasets_bounds (column not present)")

            conn.commit()
            logger.info("Spatial indexes creation step completed")
    except Exception as e:
        logger.warning(f"Could not create spatial indexes: {e}")
