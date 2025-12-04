"""
Cloud Storage Service for Cloudflare R2 / AWS S3
Handles tile uploads and serving from cloud storage
"""

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from pathlib import Path
import logging
import os
from typing import Optional
import mimetypes

from app.config import settings

logger = logging.getLogger(__name__)


class CloudStorage:
    """
    Cloud storage service for tiles using S3-compatible APIs (Cloudflare R2, AWS S3)
    Uses lazy initialization to speed up app startup
    """
    
    def __init__(self):
        self.enabled = settings.USE_S3
        self._client = None  # Lazy initialization
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
        """Initialize S3/R2 client"""
        try:
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
            return False
        
        try:
            if content_type is None:
                content_type, _ = mimetypes.guess_type(str(local_path))
                content_type = content_type or 'application/octet-stream'
            
            extra_args = {
                'ContentType': content_type,
                'CacheControl': 'public, max-age=31536000',  # 1 year cache for tiles
            }
            
            self.client.upload_file(
                str(local_path),
                self.bucket_name,
                remote_key,
                ExtraArgs=extra_args
            )
            
            logger.debug(f"Uploaded {local_path} to {remote_key}")
            return True
            
        except ClientError as e:
            logger.error(f"Failed to upload {local_path}: {e}")
            return False
    
    def upload_tiles_directory(self, local_dir: Path, dataset_id: int, 
                                progress_callback=None) -> int:
        """
        Upload entire tiles directory to cloud storage
        
        Args:
            local_dir: Local tiles directory (e.g., tiles/1/)
            dataset_id: Dataset ID for remote path prefix
            progress_callback: Optional callback(uploaded, total)
            
        Returns:
            Number of files uploaded
        """
        if not self.enabled:
            return 0
        
        uploaded = 0
        files = list(local_dir.rglob('*'))
        total_files = len([f for f in files if f.is_file()])
        
        for file_path in files:
            if file_path.is_file():
                # Create remote key: tiles/{dataset_id}/{z}/{x}/{y}.jpg
                relative_path = file_path.relative_to(local_dir)
                remote_key = f"tiles/{dataset_id}/{relative_path}"
                
                if self.upload_file(file_path, remote_key):
                    uploaded += 1
                    
                if progress_callback:
                    progress_callback(uploaded, total_files)
        
        logger.info(f"✅ Uploaded {uploaded}/{total_files} tiles to cloud storage")
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
        except ClientError:
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
            
        except ClientError as e:
            logger.error(f"Failed to delete tiles for dataset {dataset_id}: {e}")
            return 0
    
    def upload_preview(self, local_path: Path, dataset_id: int) -> Optional[str]:
        """
        Upload dataset preview image
        
        Returns:
            Public URL of the preview or None
        """
        if not self.enabled:
            return None
        
        remote_key = f"previews/{dataset_id}_preview.jpg"
        
        if self.upload_file(local_path, remote_key, 'image/jpeg'):
            if self.public_url:
                return f"{self.public_url}/{remote_key}"
        
        return None


# Global instance
cloud_storage = CloudStorage()
