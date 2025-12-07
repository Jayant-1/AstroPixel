"""
Reset Production Database and Storage
======================================
This script completely wipes all data from Neon PostgreSQL and Cloudflare R2.
Use with EXTREME CAUTION - this is IRREVERSIBLE!

Usage:
    python reset_production.py

The script will:
1. Delete all records from all database tables
2. Delete all objects from R2 bucket
3. Reset auto-increment sequences
4. Provide a confirmation summary
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.database import SessionLocal, engine
from app.models import Dataset, User, Annotation
from app.services.storage import cloud_storage
from app.config import settings
from sqlalchemy import text
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def confirm_reset():
    """Ask for user confirmation before proceeding"""
    print("\n" + "=" * 70)
    print("⚠️  WARNING: DESTRUCTIVE OPERATION ⚠️")
    print("=" * 70)
    print("\nThis script will permanently delete:")
    print("  ✗ ALL datasets from Neon database")
    print("  ✗ ALL users from Neon database")
    print("  ✗ ALL annotations from Neon database")
    print("  ✗ ALL tiles from R2 bucket")
    print("  ✗ ALL previews from R2 bucket")
    print("  ✗ ALL metadata from R2 bucket")
    print("\nCurrent configuration:")
    print(f"  Database: {settings.DB_HOST}/{settings.DB_NAME}")
    print(f"  R2 Bucket: {settings.AWS_BUCKET_NAME}")
    print(f"  R2 Enabled: {settings.USE_S3}")
    print("\n" + "=" * 70)
    
    response = input("\nType 'DELETE EVERYTHING' to confirm: ").strip()
    
    if response != "DELETE EVERYTHING":
        print("\n❌ Reset cancelled.")
        return False
    
    # Double confirmation
    response2 = input("\nAre you absolutely sure? Type 'YES' to proceed: ").strip().upper()
    
    if response2 != "YES":
        print("\n❌ Reset cancelled.")
        return False
    
    return True


def reset_database():
    """Delete all data from Neon database"""
    logger.info("🗄️  Resetting Neon database...")
    
    db = SessionLocal()
    try:
        # Count records before deletion
        dataset_count = db.query(Dataset).count()
        user_count = db.query(User).count()
        annotation_count = db.query(Annotation).count()
        
        logger.info(f"Found {dataset_count} datasets, {user_count} users, {annotation_count} annotations")
        
        # Delete in order (respecting foreign keys)
        logger.info("Deleting annotations...")
        deleted_annotations = db.query(Annotation).delete()
        db.commit()
        
        logger.info("Deleting datasets...")
        deleted_datasets = db.query(Dataset).delete()
        db.commit()
        
        logger.info("Deleting users...")
        deleted_users = db.query(User).delete()
        db.commit()
        
        # Reset sequences (auto-increment IDs)
        logger.info("Resetting ID sequences...")
        try:
            db.execute(text("ALTER SEQUENCE datasets_id_seq RESTART WITH 1"))
            db.execute(text("ALTER SEQUENCE users_id_seq RESTART WITH 1"))
            db.execute(text("ALTER SEQUENCE annotations_id_seq RESTART WITH 1"))
            db.commit()
            logger.info("✅ Sequences reset successfully")
        except Exception as e:
            logger.warning(f"Could not reset sequences (may not exist yet): {e}")
            db.rollback()
        
        logger.info(f"✅ Database reset complete:")
        logger.info(f"   - Deleted {deleted_datasets} datasets")
        logger.info(f"   - Deleted {deleted_users} users")
        logger.info(f"   - Deleted {deleted_annotations} annotations")
        
        return {
            "datasets": deleted_datasets,
            "users": deleted_users,
            "annotations": deleted_annotations
        }
        
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


def reset_r2():
    """Delete all objects from R2 bucket"""
    if not cloud_storage.enabled:
        logger.warning("⚠️  R2 storage is disabled, skipping...")
        return {"deleted": 0, "skipped": True}
    
    logger.info(f"☁️  Resetting R2 bucket: {cloud_storage.bucket_name}...")
    
    try:
        deleted_count = 0
        
        # List all objects in bucket
        logger.info("Listing all objects in R2 bucket...")
        paginator = cloud_storage.client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=cloud_storage.bucket_name)
        
        for page in pages:
            if 'Contents' not in page:
                continue
            
            objects = page['Contents']
            logger.info(f"Found {len(objects)} objects in this page")
            
            # Delete objects in batches of 1000 (S3 limit)
            batch_size = 1000
            for i in range(0, len(objects), batch_size):
                batch = objects[i:i + batch_size]
                
                # Prepare delete request
                delete_keys = [{'Key': obj['Key']} for obj in batch]
                
                logger.info(f"Deleting batch of {len(delete_keys)} objects...")
                response = cloud_storage.client.delete_objects(
                    Bucket=cloud_storage.bucket_name,
                    Delete={'Objects': delete_keys}
                )
                
                deleted = len(response.get('Deleted', []))
                deleted_count += deleted
                logger.info(f"  ✓ Deleted {deleted} objects")
                
                # Log any errors
                if 'Errors' in response:
                    for error in response['Errors']:
                        logger.error(f"  ✗ Failed to delete {error['Key']}: {error['Message']}")
        
        logger.info(f"✅ R2 reset complete: Deleted {deleted_count} objects")
        
        return {
            "deleted": deleted_count,
            "skipped": False
        }
        
    except Exception as e:
        logger.error(f"❌ R2 reset failed: {e}", exc_info=True)
        raise


def reset_local_files():
    """Clean up local files (uploads, tiles, datasets, temp)"""
    logger.info("📁 Cleaning up local files...")
    
    dirs_to_clean = [
        settings.UPLOAD_DIR,
        settings.TILES_DIR,
        settings.DATASETS_DIR,
        settings.TEMP_DIR,
    ]
    
    total_deleted = 0
    
    for directory in dirs_to_clean:
        if not directory.exists():
            logger.info(f"  Skipping {directory.name}/ (doesn't exist)")
            continue
        
        # Count and delete files
        files = list(directory.rglob('*'))
        file_count = sum(1 for f in files if f.is_file())
        
        if file_count == 0:
            logger.info(f"  {directory.name}/ is already empty")
            continue
        
        logger.info(f"  Deleting {file_count} files from {directory.name}/...")
        
        for item in directory.iterdir():
            try:
                if item.is_file():
                    item.unlink()
                    total_deleted += 1
                elif item.is_dir():
                    import shutil
                    shutil.rmtree(item)
                    total_deleted += len(list(item.rglob('*')))
            except Exception as e:
                logger.warning(f"  Failed to delete {item}: {e}")
    
    logger.info(f"✅ Local cleanup complete: Deleted {total_deleted} files")
    return {"deleted": total_deleted}


def main():
    """Main reset function"""
    print("\n🚀 AstroPixel Production Reset Tool\n")
    
    # Confirmation
    if not confirm_reset():
        sys.exit(0)
    
    print("\n" + "=" * 70)
    print("Starting reset process...")
    print("=" * 70 + "\n")
    
    results = {}
    
    try:
        # Step 1: Reset database
        results['database'] = reset_database()
        
        # Step 2: Reset R2
        results['r2'] = reset_r2()
        
        # Step 3: Clean local files
        results['local'] = reset_local_files()
        
        # Summary
        print("\n" + "=" * 70)
        print("✅ RESET COMPLETE")
        print("=" * 70)
        print("\nSummary:")
        print(f"  Database:")
        print(f"    - Datasets: {results['database']['datasets']}")
        print(f"    - Users: {results['database']['users']}")
        print(f"    - Annotations: {results['database']['annotations']}")
        
        if results['r2']['skipped']:
            print(f"  R2 Storage: Skipped (disabled)")
        else:
            print(f"  R2 Storage: {results['r2']['deleted']} objects deleted")
        
        print(f"  Local Files: {results['local']['deleted']} files deleted")
        print("\n✨ System is now at ZERO state - ready for fresh start!\n")
        
    except Exception as e:
        print("\n" + "=" * 70)
        print("❌ RESET FAILED")
        print("=" * 70)
        print(f"\nError: {e}")
        print("\nThe system may be in an inconsistent state.")
        print("Check logs above for details.")
        sys.exit(1)


if __name__ == "__main__":
    main()
