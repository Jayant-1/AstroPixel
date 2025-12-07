"""
Cloud Storage Service for Cloudflare R2 / AWS S3
Handles tile uploads and serving from cloud storage
"""

# LAZY IMPORTS: boto3 is only imported when actually needed to save ~50MB at startup
# import boto3
# from botocore.config import Config
# from botocore.exceptions import ClientError
from pathlib import Path
import logging
import os
from typing import Optional
import mimetypes
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from app.config import settings

logger = logging.getLogger(__name__)


class CloudStorage:
    """
    Cloud storage service for tiles using S3-compatible APIs (Cloudflare R2, AWS S3)
    Uses lazy initialization to speed up app startup and save memory
    """
    
    def __init__(self):
        self.enabled = settings.USE_S3
        self._client = None  # Lazy initialization
        self._boto3 = None  # Lazy import
        self.bucket_name = settings.AWS_BUCKET_NAME
        self.public_url = getattr(settings, 'R2_PUBLIC_URL', None) or ""
        self._initialized = False
        
        logger.info(f"CloudStorage config: USE_S3={settings.USE_S3}, bucket={self.bucket_name}")
    
    @property
    def client(self):
        """Lazy initialization of S3 client"""
        if self._client is None and self.enabled and not self._initialized:
            self._init_client()
        return self._client
    
    def _init_client(self):
        """Initialize S3/R2 client - imports boto3 only when needed"""
        try:
            # Lazy import boto3 to save memory at startup
            import boto3
            from botocore.config import Config
            
            # Get endpoint URL for R2 (not needed for AWS S3)
            endpoint_url = getattr(settings, 'S3_ENDPOINT_URL', None)
            
            config = Config(
                signature_version='s3v4',
                retries={'max_attempts': 3, 'mode': 'standard'}
            )
            
            client_kwargs = {
                'service_name': 's3',
                'aws_access_key_id': settings.AWS_ACCESS_KEY_ID,
                'aws_secret_access_key': settings.AWS_SECRET_ACCESS_KEY,
                'config': config,
            }
            
            # Add endpoint URL for Cloudflare R2
            if endpoint_url:
                client_kwargs['endpoint_url'] = endpoint_url
                client_kwargs['region_name'] = 'auto'
            else:
                client_kwargs['region_name'] = settings.AWS_REGION
            
            self._client = boto3.client(**client_kwargs)
            self._initialized = True
            logger.info(f"✅ Cloud storage initialized (bucket: {self.bucket_name})")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize cloud storage: {e}")
            self._initialized = True  # Mark as initialized to prevent retry loops
            self.enabled = False
    
    def upload_file(self, local_path: Path, remote_key: str, content_type: Optional[str] = None) -> bool:
        """
        Upload a file to cloud storage
        
        Args:
            local_path: Local file path
            remote_key: Remote object key (path in bucket)
            content_type: MIME type (auto-detected if not provided)
            
        Returns:
            True if successful
        """
        if not self.enabled:
            logger.debug(f"Cloud storage disabled, skipping upload of {local_path}")
            return False
        
        # Ensure client is initialized
        if self.client is None:
            logger.error(f"Cloud storage client not initialized when uploading {local_path}")
            return False
        
        try:
            if content_type is None:
                content_type, _ = mimetypes.guess_type(str(local_path))
                content_type = content_type or 'application/octet-stream'
            
            logger.debug(f"Uploading {local_path} → {remote_key} (type: {content_type})")
            
            # Use put_object instead of upload_file for better error handling with R2
            with open(local_path, 'rb') as file_data:
                self.client.put_object(
                    Bucket=self.bucket_name,
                    Key=remote_key,
                    Body=file_data,
                    ContentType=content_type,
                    CacheControl='public, max-age=31536000'  # 1 year cache for tiles
                )
            
            logger.info(f"✅ Uploaded {local_path.name} to R2: {remote_key}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to upload {local_path.name} to R2: {e}", exc_info=True)
            return False
    
    def upload_tiles_directory(self, local_dir: Path, dataset_id: int, 
                                progress_callback=None, max_workers: int = None) -> int:
        """
        Upload entire tiles directory to cloud storage using parallel uploads
        
        Args:
            local_dir: Local tiles directory (e.g., tiles/1/)
            dataset_id: Dataset ID for remote path prefix
            progress_callback: Optional callback(uploaded, total)
            max_workers: Number of parallel upload threads (default: 20)
            
        Returns:
            Number of files uploaded
        """
        if not self.enabled:
            logger.warning(f"Cloud storage disabled, skipping tile upload for dataset {dataset_id}")
            return 0
        
        if not local_dir.exists():
            logger.error(f"Tiles directory not found: {local_dir}")
            return 0
        
        # Collect all files to upload
        files = [f for f in local_dir.rglob('*') if f.is_file()]
        total_files = len(files)
        
        if total_files == 0:
            logger.warning(f"No files found in {local_dir}")
            return 0
        
        # Use configured max_workers or default to 20
        if max_workers is None:
            max_workers = settings.R2_UPLOAD_MAX_WORKERS
        
        logger.info(f"📤 Starting parallel tile upload: {total_files} files with {max_workers} workers for dataset {dataset_id}")
        start_time = time.time()
        
        uploaded = 0
        failed = 0
        
        def upload_single_tile(file_path: Path) -> tuple[bool, str]:
            """Upload a single tile and return (success, filename)"""
            try:
                relative_path = file_path.relative_to(local_dir)
                remote_key = f"tiles/{dataset_id}/{relative_path}".replace("\\", "/")
                success = self.upload_file(file_path, remote_key)
                return (success, file_path.name)
            except Exception as e:
                logger.error(f"Error uploading {file_path.name}: {e}")
                return (False, file_path.name)
        
        # Use ThreadPoolExecutor for parallel uploads
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all upload tasks
            future_to_file = {executor.submit(upload_single_tile, f): f for f in files}
            
            # Process completed uploads
            for future in as_completed(future_to_file):
                success, filename = future.result()
                if success:
                    uploaded += 1
                else:
                    failed += 1
                    logger.warning(f"Failed to upload tile: {filename}")
                
                # Report progress every 100 files or at key milestones
                if uploaded % 100 == 0 or uploaded == total_files:
                    elapsed = time.time() - start_time
                    rate = uploaded / elapsed if elapsed > 0 else 0
                    logger.info(f"Progress: {uploaded}/{total_files} tiles ({rate:.1f} tiles/sec)")
                    
                if progress_callback:
                    progress_callback(uploaded, total_files)
        
        elapsed_time = time.time() - start_time
        rate = uploaded / elapsed_time if elapsed_time > 0 else 0
        
        logger.info(f"✅ Uploaded {uploaded}/{total_files} tiles to R2 for dataset {dataset_id}")
        logger.info(f"⏱️  Upload completed in {elapsed_time:.1f}s ({rate:.1f} tiles/sec, {failed} failed)")
        
        return uploaded
    
    def get_tile_url(self, dataset_id: int, z: int, x: int, y: int, format: str = 'jpg') -> Optional[str]:
        """
        Get public URL for a tile
        
        Args:
            dataset_id: Dataset ID
            z, x, y: Tile coordinates
            format: Image format
            
        Returns:
            Public URL or None if not using cloud storage
        """
        if not self.enabled or not self.public_url:
            return None
        
        return f"{self.public_url}/tiles/{dataset_id}/{z}/{x}/{y}.{format}"
    
    def tile_exists(self, dataset_id: int, z: int, x: int, y: int, format: str = 'jpg') -> bool:
        """Check if a tile exists in cloud storage"""
        if not self.enabled:
            return False
        
        try:
            key = f"tiles/{dataset_id}/{z}/{x}/{y}.{format}"
            self.client.head_object(Bucket=self.bucket_name, Key=key)
            return True
        except Exception:
            return False
    
    def delete_dataset_tiles(self, dataset_id: int) -> int:
        """
        Delete all tiles for a dataset from cloud storage
        
        Returns:
            Number of objects deleted
        """
        if not self.enabled:
            return 0
        
        try:
            deleted = 0
            prefix = f"tiles/{dataset_id}/"
            
            # List and delete in batches
            paginator = self.client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' not in page:
                    continue
                
                objects = [{'Key': obj['Key']} for obj in page['Contents']]
                
                if objects:
                    self.client.delete_objects(
                        Bucket=self.bucket_name,
                        Delete={'Objects': objects}
                    )
                    deleted += len(objects)
            
            logger.info(f"Deleted {deleted} tiles for dataset {dataset_id}")
            return deleted
            
        except Exception as e:
            logger.error(f"Failed to delete tiles for dataset {dataset_id}: {e}")
            return 0
    
    def upload_preview(self, local_path: Path, dataset_id: int) -> Optional[str]:
        """
        Upload dataset preview image
        
        Returns:
            Public URL of the preview or None
        """
        if not self.enabled:
            logger.debug(f"Cloud storage disabled, skipping preview upload")
            return None
        
        if not local_path.exists():
            logger.warning(f"Preview file not found: {local_path}")
            return None
        
        remote_key = f"previews/{dataset_id}_preview.jpg"
        
        logger.info(f"📤 Uploading preview for dataset {dataset_id}")
        if self.upload_file(local_path, remote_key, 'image/jpeg'):
            if self.public_url:
                preview_url = f"{self.public_url}/{remote_key}"
                logger.info(f"✅ Preview uploaded: {preview_url}")
                return preview_url
        
        logger.error(f"Failed to upload preview for dataset {dataset_id}")
        return None

    def save_dataset_metadata(self, dataset_dict: dict) -> bool:
        """
        Save dataset metadata to R2 as JSON for persistence
        
        Args:
            dataset_dict: Dataset data as dictionary
            
        Returns:
            True if successful
        """
        if not self.enabled:
            return False
        
        try:
            import json
            import tempfile
            
            dataset_id = dataset_dict.get('id')
            if not dataset_id:
                return False
            
            # Save individual dataset metadata
            json_data = json.dumps(dataset_dict, default=str)
            
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=f"metadata/datasets/{dataset_id}.json",
                Body=json_data.encode('utf-8'),
                ContentType='application/json'
            )
            
            logger.info(f"✅ Saved metadata for dataset {dataset_id} to R2")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save dataset metadata: {e}")
            return False
    
    def load_all_datasets_metadata(self) -> list:
        """
        Load all dataset metadata from R2
        
        Returns:
            List of dataset dictionaries
        """
        if not self.enabled:
            return []
        
        try:
            import json
            
            datasets = []
            prefix = "metadata/datasets/"
            
            paginator = self.client.get_paginator('list_objects_v2')
            
            for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
                if 'Contents' not in page:
                    continue
                
                for obj in page['Contents']:
                    try:
                        response = self.client.get_object(
                            Bucket=self.bucket_name,
                            Key=obj['Key']
                        )
                        data = json.loads(response['Body'].read().decode('utf-8'))
                        datasets.append(data)
                    except Exception as e:
                        logger.error(f"Failed to load {obj['Key']}: {e}")
            
            logger.info(f"✅ Loaded {len(datasets)} datasets from R2 metadata")
            return datasets
            
        except Exception as e:
            logger.error(f"❌ Failed to load datasets metadata: {e}")
            return []
    
    def delete_dataset_metadata(self, dataset_id: int) -> bool:
        """Delete dataset metadata from R2"""
        if not self.enabled:
            return False
        
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=f"metadata/datasets/{dataset_id}.json"
            )
            logger.info(f"✅ Deleted metadata for dataset {dataset_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete dataset metadata: {e}")
            return False


# Global instance
cloud_storage = CloudStorage()
