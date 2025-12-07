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
# LAZY IMPORT: PerfectTileGenerator is imported only when needed to save memory at startup
# from app.services.perfect_tile_generator import PerfectTileGenerator
from app.services.storage import cloud_storage
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
        import psutil
        import gc
        import time
        from sqlalchemy.exc import OperationalError
        
        # Create new database session for background task
        from app.database import SessionLocal
        db = SessionLocal()
        
        def safe_commit(max_retries=3):
            """Safely commit with retry logic for connection issues"""
            for attempt in range(max_retries):
                try:
                    db.commit()
                    return True
                except OperationalError as e:
                    logger.warning(f"Database commit failed (attempt {attempt + 1}/{max_retries}): {e}")
                    try:
                        db.rollback()
                    except:
                        pass
                    
                    if attempt < max_retries - 1:
                        time.sleep(2)  # Wait before retry
                    else:
                        logger.error(f"Failed to commit after {max_retries} attempts")
                        return False
            return False
        
        try:
            dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
            if not dataset:
                logger.error(f"Dataset {dataset_id} not found for background processing")
                return

            # Check available memory BEFORE starting
            memory = psutil.virtual_memory()
            available_mb = memory.available / (1024 * 1024)
            file_size_mb = file_path.stat().st_size / (1024 * 1024)
            
            logger.info(f"Memory check: {available_mb:.0f}MB available, file size: {file_size_mb:.0f}MB")
            
            # For PSB/PSD files, we need at least 3x file size in RAM
            # For TIFF files with rasterio streaming, we need less
            file_ext = str(file_path).lower()
            is_psb = file_ext.endswith(('.psb', '.psd'))
            
            min_required_mb = file_size_mb * 3 if is_psb else 200  # PSB needs more, TIFF can stream
            
            if available_mb < min_required_mb:
                logger.error(f"Insufficient memory for tile generation!")
                logger.error(f"Available: {available_mb:.0f}MB, Required: {min_required_mb:.0f}MB")
                logger.error(f"File type: {'PSB/PSD' if is_psb else 'TIFF'}")
                
                dataset.processing_status = "failed"
                dataset.processing_progress = 0
                dataset.extra_metadata = dataset.extra_metadata or {}
                dataset.extra_metadata['error'] = f"Insufficient memory. Available: {available_mb:.0f}MB, Required: ~{min_required_mb:.0f}MB. Try a smaller file or upgrade server."
                safe_commit()
                return

            # Force garbage collection before starting
            gc.collect()

            dataset.processing_status = "processing"
            dataset.processing_progress = 0
            safe_commit()

            # LAZY IMPORT: Try perfect tile generator first, fall back to simple generator
            tile_path = Path(dataset.tile_base_path)
            tile_gen = None
            
            try:
                from app.services.perfect_tile_generator import PerfectTileGenerator
                tile_gen = PerfectTileGenerator(
                    input_file=file_path,
                    output_dir=tile_path,
                    tile_size=settings.TILE_SIZE,
                )
                logger.info(f"Using PerfectTileGenerator for dataset {dataset_id}")
            except Exception as e:
                logger.warning(f"PerfectTileGenerator not available: {e}")
                logger.info(f"Falling back to SimpleTileGenerator")
                
                try:
                    from app.services.simple_tile_generator import SimpleTileGenerator
                    tile_gen = SimpleTileGenerator(
                        input_file=file_path,
                        output_dir=tile_path,
                        tile_size=settings.TILE_SIZE,
                    )
                except Exception as e2:
                    logger.error(f"SimpleTileGenerator also failed: {e2}")
                    dataset.processing_status = "failed"
                    dataset.extra_metadata = dataset.extra_metadata or {}
                    dataset.extra_metadata['error'] = f"No tile generator available: {str(e2)}"
                    safe_commit()
                    return
            
            if not tile_gen:
                logger.error("No tile generator could be initialized")
                dataset.processing_status = "failed"
                dataset.extra_metadata = dataset.extra_metadata or {}
                dataset.extra_metadata['error'] = "No tile generator available"
                safe_commit()
                return

            logger.info(f"Starting background tile generation for dataset {dataset_id}")

            # Progress callback
            def update_progress(progress: int):
                dataset.processing_progress = progress
                safe_commit()
            import shutil
                logger.info(f"Dataset {dataset_id} progress: {progress}%")

            success = tile_gen.generate_tiles(progress_callback=update_progress)

            if success:
                # Mark as completed FIRST and commit immediately
                dataset.processing_status = "completed"
                dataset.processing_progress = 100
                safe_commit()
                logger.info(f"Dataset {dataset_id} processing completed - status committed")

                # Generate preview thumbnail
                preview_path = settings.DATASETS_DIR / f"{dataset_id}_preview.jpg"
                try:
                    tile_gen.generate_preview(preview_path)
                except Exception as e:
                    logger.error(f"Failed to generate preview: {e}")
                
                # Upload to cloud storage if enabled (Cloudflare R2)

                # Check available disk space BEFORE starting
                disk = shutil.disk_usage(str(file_path.parent))
                available_disk_mb = disk.free / (1024 * 1024)
                min_disk_required_mb = file_size_mb * 2  # Require at least 2x file size for temp/tiles
                logger.info(f"Disk check: {available_disk_mb:.0f}MB available, file size: {file_size_mb:.0f}MB")
                if available_disk_mb < min_disk_required_mb:
                    logger.error(f"Insufficient disk space for tile generation!")
                    dataset.processing_status = "failed"
                    dataset.processing_progress = 0
                    dataset.extra_metadata = dataset.extra_metadata or {}
                    dataset.extra_metadata['error'] = f"Insufficient disk space. Available: {available_disk_mb:.0f}MB, Required: ~{min_disk_required_mb:.0f}MB. Try a smaller file or free up space."
                    safe_commit()
                    return

                # Log memory usage before tile generation
                logger.info(f"Memory usage before tile gen: {psutil.Process().memory_info().rss / (1024*1024):.2f} MB")
                logger.info(f"Cloud storage enabled: {cloud_storage.enabled}, Bucket: {cloud_storage.bucket_name}, Public URL: {cloud_storage.public_url}")
                if cloud_storage.enabled:
                    logger.info(f"📤 Uploading tiles to R2 for dataset {dataset_id}")
                    try:
                        tile_path = Path(dataset.tile_base_path)
                        uploaded = cloud_storage.upload_tiles_directory(tile_path, dataset_id)
                        logger.info(f"✅ Successfully uploaded {uploaded} tiles to R2")
                        
                        # Mark tiles as uploaded to cloud
                        dataset.extra_metadata = dataset.extra_metadata or {}
                        dataset.extra_metadata['tiles_uploaded_to_cloud'] = True
                        dataset.extra_metadata['tiles_count'] = uploaded
                        
                        # Upload preview
                        if preview_path.exists():
                            preview_url = cloud_storage.upload_preview(preview_path, dataset_id)
                            if preview_url:
                                dataset.extra_metadata['preview_url'] = preview_url
                                logger.info(f"✅ Uploaded preview to: {preview_url}")
                        
                        # Save dataset metadata to R2
                        safe_commit()

                # Log memory usage after gc
                logger.info(f"Memory usage after gc: {psutil.Process().memory_info().rss / (1024*1024):.2f} MB")
                        db.refresh(dataset)
                # Log memory usage after tile generation
                logger.info(f"Memory usage after tile gen: {psutil.Process().memory_info().rss / (1024*1024):.2f} MB")
                        DatasetProcessor._save_dataset_metadata_to_cloud(dataset)
                        
                    except Exception as e:
                        logger.error(f"❌ Failed to upload to R2: {e}", exc_info=True)
                        dataset.extra_metadata = dataset.extra_metadata or {}
                        dataset.extra_metadata['r2_upload_error'] = str(e)
                        safe_commit()
                else:
                    logger.warning(f"⚠️  Cloud storage disabled - tiles NOT uploaded to R2 (tiles available locally only)")
            else:
                dataset.processing_status = "failed"
                dataset.processing_progress = 0
                logger.error(f"Dataset {dataset_id} processing failed")

            safe_commit()

        except Exception as e:
            logger.error(f"Error in background tile processing for dataset {dataset_id}: {e}", exc_info=True)
            if "dataset" in locals():
                dataset.processing_status = "failed"
                dataset.processing_progress = 0
                safe_commit()
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
                    Image.MAX_IMAGE_PIXELS = None  # Disable decompression bomb protection

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

    @staticmethod
    def _save_dataset_metadata_to_cloud(dataset: Dataset) -> bool:
        """
        Save dataset metadata to R2 for persistence across restarts
        Only saves DEMO datasets as per production requirements.
        
        Args:
            dataset: Dataset model instance
            
        Returns:
            True if successful
        """
        try:
            if not cloud_storage.enabled:
                return False
            
            # Only persist demo datasets to R2 metadata
            if not dataset.is_demo:
                logger.info(f"Skipping R2 metadata save for non-demo dataset {dataset.id}")
                return False
            
            # Convert dataset to dictionary using current model field names
            dataset_dict = {
                'id': dataset.id,
                'name': dataset.name,
                'description': dataset.description,
                'category': dataset.category,
                'original_file_path': dataset.original_file_path,
                'tile_base_path': dataset.tile_base_path,
                'width': dataset.width,
                'height': dataset.height,
                'tile_size': dataset.tile_size,
                'min_zoom': dataset.min_zoom,
                'max_zoom': dataset.max_zoom,
                'processing_status': dataset.processing_status,
                'extra_metadata': dataset.extra_metadata or {},
                'created_at': str(dataset.created_at) if dataset.created_at else None,
                'updated_at': str(dataset.updated_at) if dataset.updated_at else None,
            }
            
            success = cloud_storage.save_dataset_metadata(dataset_dict)
            if success:
                logger.info(f"✅ Saved dataset {dataset.id} metadata to R2")
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to save dataset metadata to cloud: {e}")
            return False

        except Exception as e:
            logger.error(f"Error getting dataset stats: {e}")
            return {}
