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
    pool_size=10,
    max_overflow=20,
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
    except Exception as e:
        logger.error(f"Error creating database tables: {e}")
        raise


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
