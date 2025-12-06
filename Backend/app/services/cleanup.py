"""
Automatic cleanup service for expired datasets
Removes datasets older than 24 hours and their associated files
"""

import logging
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.database import SessionLocal
from app.models import Dataset
from app.services.storage import cloud_storage

logger = logging.getLogger(__name__)


async def delete_dataset_files(dataset: Dataset) -> bool:
    """
    Delete all files associated with a dataset
    
    Args:
        dataset: Dataset model instance
        
    Returns:
        True if successful
    """
    try:
        # Delete local tiles directory
        tiles_dir = Path(f"tiles/{dataset.id}")
        if tiles_dir.exists():
            import shutil
            shutil.rmtree(tiles_dir, ignore_errors=True)
            logger.info(f"Deleted local tiles for dataset {dataset.id}")
        
        # Delete uploaded file
        upload_path = Path(dataset.original_file_path)
        if upload_path.exists():
            upload_path.unlink(missing_ok=True)
            logger.info(f"Deleted upload file for dataset {dataset.id}")
        
        # Delete preview thumbnail if exists
        preview_path = Path(f"datasets/{dataset.id}_preview.jpg")
        if preview_path.exists():
            preview_path.unlink(missing_ok=True)
        
        # Delete from cloud storage if enabled
        if cloud_storage.enabled:
            await asyncio.to_thread(cloud_storage.delete_tiles, dataset.id)
            await asyncio.to_thread(cloud_storage.delete_dataset_metadata, dataset.id)
            logger.info(f"Deleted cloud files for dataset {dataset.id}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to delete files for dataset {dataset.id}: {e}")
        return False


async def cleanup_expired_datasets() -> int:
    """
    Find and delete all expired datasets
    
    Returns:
        Number of datasets deleted
    """
    db = SessionLocal()
    deleted_count = 0
    
    try:
        # Find all expired non-demo datasets
        now = datetime.utcnow()
        expired_datasets = db.query(Dataset).filter(
            and_(
                Dataset.is_demo == False,
                Dataset.expires_at != None,
                Dataset.expires_at <= now
            )
        ).all()
        
        logger.info(f"Found {len(expired_datasets)} expired datasets to cleanup")
        
        for dataset in expired_datasets:
            try:
                # Delete files first
                await delete_dataset_files(dataset)
                
                # Delete from database
                db.delete(dataset)
                db.commit()
                
                deleted_count += 1
                logger.info(f"✅ Deleted expired dataset: {dataset.name} (ID: {dataset.id})")
                
            except Exception as e:
                logger.error(f"Failed to delete dataset {dataset.id}: {e}")
                db.rollback()
                continue
        
        logger.info(f"Cleanup complete: {deleted_count} datasets deleted")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Cleanup job failed: {e}")
        db.rollback()
        return deleted_count
        
    finally:
        db.close()


async def cleanup_scheduler():
    """
    Background task that runs cleanup every hour
    """
    logger.info("🧹 Starting cleanup scheduler (runs every hour)")
    
    while True:
        try:
            # Run cleanup
            deleted = await cleanup_expired_datasets()
            
            if deleted > 0:
                logger.info(f"✨ Cleanup job completed: {deleted} datasets removed")
            
            # Wait 1 hour before next run
            await asyncio.sleep(3600)  # 1 hour
            
        except Exception as e:
            logger.error(f"Cleanup scheduler error: {e}")
            # Wait 5 minutes before retry on error
            await asyncio.sleep(300)


def get_time_until_expiry(expires_at: datetime) -> str:
    """
    Calculate human-readable time remaining until expiry
    
    Args:
        expires_at: Expiry timestamp
        
    Returns:
        Human-readable string like "23 hours" or "45 minutes"
    """
    if not expires_at:
        return None
    
    now = datetime.utcnow()
    delta = expires_at - now
    
    if delta.total_seconds() <= 0:
        return "Expired"
    
    # Calculate time components
    total_seconds = int(delta.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    
    if hours > 0:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    elif minutes > 0:
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        return "Less than a minute"
