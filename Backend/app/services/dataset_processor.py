"""
Dataset processing service
Handles upload, processing, and management of NASA datasets
"""

from pathlib import Path
from typing import Optional, Dict, Any
import logging
import shutil
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Dataset, ProcessingJob
from app.schemas import DatasetCreate
from app.services.tile_generator import TileGenerator
from app.services.perfect_tile_generator import PerfectTileGenerator
from app.config import settings

logger = logging.getLogger(__name__)


class DatasetProcessor:
    """Process and manage NASA datasets"""

    @staticmethod
    async def create_dataset_entry(
        file_path: Path, dataset_info: DatasetCreate, db: Session
    ) -> Dataset:
        """
        Create dataset entry with metadata extraction (fast, synchronous)
        Tile generation happens separately in background
        
        Args:
            file_path: Path to uploaded file
            dataset_info: Dataset creation information
            db: Database session
            
        Returns:
            Created Dataset object with pending status
        """
        try:
            # Check if dataset with same name already exists
            existing = (
                db.query(Dataset).filter(Dataset.name == dataset_info.name).first()
            )
            if existing:
                raise ValueError(
                    f"Dataset with name '{dataset_info.name}' already exists"
                )

            # Create temporary dataset entry
            temp_dataset = Dataset(
                name=dataset_info.name,
                description=dataset_info.description,
                category=dataset_info.category,
                original_file_path=str(file_path),
                tile_base_path="",
                width=0,
                height=0,
                max_zoom=0,
                processing_status="pending",
                processing_progress=0,
            )
            db.add(temp_dataset)
            db.commit()
            db.refresh(temp_dataset)

            # Extract metadata quickly (no tile generation yet)
            final_tile_path = settings.TILES_DIR / str(temp_dataset.id)
            generator = TileGenerator(
                input_file=file_path,
                output_dir=final_tile_path,
                tile_size=settings.TILE_SIZE,
                tile_format=settings.TILE_FORMAT,
                quality=settings.TILE_QUALITY,
            )

            logger.info(f"Extracting metadata from {file_path.name}")
            metadata = generator.get_metadata()

            # Update dataset with metadata
            temp_dataset.tile_base_path = str(final_tile_path)
            temp_dataset.width = metadata["width"]
            temp_dataset.height = metadata["height"]
            temp_dataset.max_zoom = metadata["max_zoom"]
            temp_dataset.min_zoom = 0
            temp_dataset.tile_size = settings.TILE_SIZE
            temp_dataset.projection = metadata["projection"]
            temp_dataset.geotransform = metadata["geotransform"]
            temp_dataset.extra_metadata = metadata
            temp_dataset.bounds_json = metadata["bounds"]

            db.commit()
            db.refresh(temp_dataset)

            logger.info(f"Created dataset entry: {temp_dataset.id} - {temp_dataset.name}")
            return temp_dataset

        except Exception as e:
            logger.error(f"Error creating dataset entry: {e}")
            if "temp_dataset" in locals():
                db.rollback()
            raise

    @staticmethod
    def process_tiles_background(dataset_id: int, file_path: Path):
        """
        Process tiles in background (long-running operation)
        This runs asynchronously after the upload endpoint returns
        
        Args:
            dataset_id: ID of dataset to process
            file_path: Path to uploaded file
        """
        # Create new database session for background task
        from app.database import SessionLocal
        db = SessionLocal()
        
        try:
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if not dataset:
                logger.error(f"Dataset {dataset_id} not found for background processing")
                return

            dataset.processing_status = "processing"
            dataset.processing_progress = 0
            db.commit()

            # Use Perfect Tile Generator
            tile_path = Path(dataset.tile_base_path)
            tile_gen = PerfectTileGenerator(
                input_file=file_path,
                output_dir=tile_path,
                tile_size=settings.TILE_SIZE,
            )

            logger.info(f"Starting background tile generation for dataset {dataset_id}")

            # Progress callback
            def update_progress(progress: int):
                dataset.processing_progress = progress
                db.commit()
                logger.info(f"Dataset {dataset_id} progress: {progress}%")

            success = tile_gen.generate_tiles(progress_callback=update_progress)

            if success:
                dataset.processing_status = "completed"
                dataset.processing_progress = 100
                logger.info(f"Dataset {dataset_id} processing completed")

                # Generate preview thumbnail
                preview_path = settings.DATASETS_DIR / f"{dataset_id}_preview.jpg"
                tile_gen.generate_preview(preview_path)
            else:
                dataset.processing_status = "failed"
                dataset.processing_progress = 0
                logger.error(f"Dataset {dataset_id} processing failed")

            db.commit()

        except Exception as e:
            logger.error(f"Error in background tile processing for dataset {dataset_id}: {e}", exc_info=True)
            if "dataset" in locals():
                dataset.processing_status = "failed"
                dataset.processing_progress = 0
                db.commit()
        finally:
            db.close()

    @staticmethod
    async def process_dataset(
        file_path: Path, dataset_info: DatasetCreate, db: Session
    ) -> Dataset:
        """
        Process uploaded GeoTIFF file and create dataset entry

        Args:
            file_path: Path to uploaded .tif file
            dataset_info: Dataset creation information
            db: Database session

        Returns:
            Created Dataset object
        """
        try:
            # Check if dataset with same name already exists
            existing = (
                db.query(Dataset).filter(Dataset.name == dataset_info.name).first()
            )
            if existing:
                raise ValueError(
                    f"Dataset with name '{dataset_info.name}' already exists"
                )

            # Create a temporary dataset entry first to get an ID
            temp_dataset = Dataset(
                name=dataset_info.name,
                description=dataset_info.description,
                category=dataset_info.category,
                original_file_path=str(file_path),
                tile_base_path="",  # Will be updated
                width=0,
                height=0,
                max_zoom=0,
                processing_status="pending",
            )
            db.add(temp_dataset)
            db.commit()
            db.refresh(temp_dataset)

            # Now create tile generator with proper path
            final_tile_path = settings.TILES_DIR / str(temp_dataset.id)
            generator = TileGenerator(
                input_file=file_path,
                output_dir=final_tile_path,
                tile_size=settings.TILE_SIZE,
                tile_format=settings.TILE_FORMAT,
                quality=settings.TILE_QUALITY,
            )

            # Extract metadata
            logger.info(f"Extracting metadata from {file_path.name}")
            metadata = generator.get_metadata()

            # Update dataset entry with metadata
            dataset = temp_dataset
            dataset.tile_base_path = str(final_tile_path)
            dataset.width = metadata["width"]
            dataset.height = metadata["height"]
            dataset.max_zoom = metadata["max_zoom"]
            dataset.min_zoom = 0
            dataset.tile_size = settings.TILE_SIZE
            dataset.projection = metadata["projection"]
            dataset.geotransform = metadata["geotransform"]
            dataset.extra_metadata = metadata
            dataset.bounds_json = metadata["bounds"]

            db.commit()
            db.refresh(dataset)

            logger.info(f"Created dataset entry: {dataset.id} - {dataset.name}")

            # Use Perfect Tile Generator - handles all file sizes optimally
            megapixels = metadata["width"] * metadata["height"] / 1_000_000
            file_size_gb = file_path.stat().st_size / (1024**3)  # File size in GB

            logger.info(
                f"✨ File ({file_size_gb:.2f}GB, {megapixels:.1f}MP) - Using Perfect Tile Generator"
            )
            tile_gen = PerfectTileGenerator(
                input_file=file_path,
                output_dir=final_tile_path,
                tile_size=settings.TILE_SIZE,
            )

            # Start tile generation (synchronous for now, can be made async with Celery)
            dataset.processing_status = "processing"
            dataset.processing_progress = 0
            db.commit()

            logger.info(f"Starting tile generation for dataset {dataset.id}")

            # Progress callback to update database
            def update_progress(progress: int):
                dataset.processing_progress = progress
                db.commit()
                logger.info(f"Dataset {dataset.id} progress: {progress}%")

            success = tile_gen.generate_tiles(progress_callback=update_progress)

            if success:
                dataset.processing_status = "completed"
                dataset.processing_progress = 100
                logger.info(f"Dataset {dataset.id} processed successfully")

                # Generate preview thumbnail
                preview_path = settings.DATASETS_DIR / f"{dataset.id}_preview.jpg"
                if hasattr(tile_gen, "generate_preview"):
                    tile_gen.generate_preview(preview_path)
                else:
                    # Fallback preview generation
                    from PIL import Image

                    with Image.open(file_path) as img:
                        img.thumbnail((512, 512))
                        img.save(preview_path, "JPEG", quality=90)

            else:
                dataset.processing_status = "failed"
                dataset.processing_progress = 0
                logger.error(f"Dataset {dataset.id} processing failed")

            db.commit()
            db.refresh(dataset)

            return dataset

        except Exception as e:
            logger.error(f"Error processing dataset: {e}")
            if "dataset" in locals():
                dataset.processing_status = "failed"
                db.commit()
            raise

    @staticmethod
    def delete_dataset(dataset_id: int, db: Session) -> bool:
        """
        Delete dataset and associated files

        Args:
            dataset_id: ID of dataset to delete
            db: Database session

        Returns:
            True if successful
        """
        try:
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if not dataset:
                raise ValueError(f"Dataset {dataset_id} not found")

            # Delete tile directory
            tile_dir = Path(dataset.tile_base_path)
            if tile_dir.exists():
                shutil.rmtree(tile_dir)
                logger.info(f"Deleted tiles for dataset {dataset_id}")

            # Delete original file
            original_file = Path(dataset.original_file_path)
            if original_file.exists():
                original_file.unlink()
                logger.info(f"Deleted original file for dataset {dataset_id}")

            # Delete preview
            preview_path = settings.DATASETS_DIR / f"{dataset_id}_preview.jpg"
            if preview_path.exists():
                preview_path.unlink()

            # Delete database entry (cascade will delete annotations)
            db.delete(dataset)
            db.commit()

            logger.info(f"Dataset {dataset_id} deleted successfully")
            return True

        except Exception as e:
            logger.error(f"Error deleting dataset {dataset_id}: {e}")
            return False

    @staticmethod
    def reprocess_dataset(dataset_id: int, db: Session) -> bool:
        """
        Regenerate tiles for an existing dataset

        Args:
            dataset_id: ID of dataset to reprocess
            db: Database session

        Returns:
            True if successful
        """
        try:
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if not dataset:
                raise ValueError(f"Dataset {dataset_id} not found")

            original_file = Path(dataset.original_file_path)
            if not original_file.exists():
                raise ValueError(f"Original file not found: {original_file}")

            # Delete existing tiles
            tile_dir = Path(dataset.tile_base_path)
            if tile_dir.exists():
                shutil.rmtree(tile_dir)

            # Create tile generator
            generator = TileGenerator(
                input_file=original_file,
                output_dir=tile_dir,
                tile_size=settings.TILE_SIZE,
                tile_format=settings.TILE_FORMAT,
                quality=settings.TILE_QUALITY,
            )

            # Update status
            dataset.processing_status = "processing"
            db.commit()

            # Generate tiles
            logger.info(f"Reprocessing dataset {dataset_id}")
            success = generator.generate_tiles()

            if success:
                dataset.processing_status = "completed"
                logger.info(f"Dataset {dataset_id} reprocessed successfully")
            else:
                dataset.processing_status = "failed"
                logger.error(f"Dataset {dataset_id} reprocessing failed")

            db.commit()
            return success

        except Exception as e:
            logger.error(f"Error reprocessing dataset {dataset_id}: {e}")
            if "dataset" in locals():
                dataset.processing_status = "failed"
                db.commit()
            return False

    @staticmethod
    def get_dataset_stats(db: Session) -> Dict[str, Any]:
        """
        Get statistics about datasets

        Args:
            db: Database session

        Returns:
            Dictionary with statistics
        """
        try:
            total = db.query(Dataset).count()

            # Count by category
            earth_count = db.query(Dataset).filter(Dataset.category == "earth").count()
            mars_count = db.query(Dataset).filter(Dataset.category == "mars").count()
            space_count = db.query(Dataset).filter(Dataset.category == "space").count()

            # Count by status
            completed = (
                db.query(Dataset)
                .filter(Dataset.processing_status == "completed")
                .count()
            )
            processing = (
                db.query(Dataset)
                .filter(Dataset.processing_status == "processing")
                .count()
            )
            failed = (
                db.query(Dataset).filter(Dataset.processing_status == "failed").count()
            )

            # Calculate total storage (approximate)
            total_pixels = (
                db.query(db.func.sum(Dataset.width * Dataset.height)).scalar() or 0
            )

            return {
                "total_datasets": total,
                "by_category": {
                    "earth": earth_count,
                    "mars": mars_count,
                    "space": space_count,
                },
                "by_status": {
                    "completed": completed,
                    "processing": processing,
                    "failed": failed,
                },
                "total_pixels": total_pixels,
            }

        except Exception as e:
            logger.error(f"Error getting dataset stats: {e}")
            return {}
