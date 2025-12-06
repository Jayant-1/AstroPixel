#!/usr/bin/env python
"""
Test script to verify R2 upload configuration and connectivity
Run this to diagnose R2 upload issues
"""

import os
import sys
from pathlib import Path

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from app.services.storage import cloud_storage

def test_r2_configuration():
    """Test if R2 is properly configured"""
    print("\n" + "="*70)
    print("🔍 R2 UPLOAD CONFIGURATION TEST")
    print("="*70 + "\n")
    
    print("1️⃣  Configuration from .env:")
    print(f"   USE_S3: {settings.USE_S3}")
    print(f"   Bucket: {settings.AWS_BUCKET_NAME}")
    print(f"   Region: {settings.AWS_REGION}")
    print(f"   Endpoint: {settings.S3_ENDPOINT_URL}")
    print(f"   Public URL: {settings.R2_PUBLIC_URL}")
    print(f"   Access Key ID: {settings.AWS_ACCESS_KEY_ID[:10]}{'*'*20 if settings.AWS_ACCESS_KEY_ID else 'NOT SET'}")
    print(f"   Secret Key: {'SET' if settings.AWS_SECRET_ACCESS_KEY else 'NOT SET'}\n")
    
    print("2️⃣  Cloud Storage Service Status:")
    print(f"   Enabled: {cloud_storage.enabled}")
    print(f"   Bucket Name: {cloud_storage.bucket_name}")
    print(f"   Public URL: {cloud_storage.public_url}")
    print(f"   Client Initialized: {cloud_storage._client is not None}")
    print(f"   Service Initialized: {cloud_storage._initialized}\n")
    
    # Test connection
    if cloud_storage.enabled and cloud_storage.client:
        print("3️⃣  Testing R2 Connection...")
        try:
            # Try to list objects
            response = cloud_storage.client.list_objects_v2(
                Bucket=cloud_storage.bucket_name,
                MaxKeys=1
            )
            print(f"   ✅ Successfully connected to R2 bucket")
            print(f"   Objects in bucket: {response.get('KeyCount', 0)}\n")
            return True
        except Exception as e:
            print(f"   ❌ Failed to connect to R2: {e}\n")
            return False
    else:
        print("3️⃣  R2 Service Not Enabled\n")
        return False

def test_upload_small_file():
    """Test uploading a small test file"""
    if not cloud_storage.enabled:
        print("⚠️  Cloud storage not enabled, skipping upload test\n")
        return False
    
    import tempfile
    import time
    
    print("4️⃣  Testing File Upload...")
    
    # Create a small test file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        test_file = Path(f.name)
        f.write("🧪 Test file for R2 upload verification")
    
    try:
        # Upload test file
        test_key = f"test/test-{int(time.time())}.txt"
        success = cloud_storage.upload_file(test_file, test_key, 'text/plain')
        
        if success:
            print(f"   ✅ Upload successful")
            if cloud_storage.public_url:
                print(f"   Public URL: {cloud_storage.public_url}/{test_key}\n")
            return True
        else:
            print(f"   ❌ Upload failed\n")
            return False
    finally:
        test_file.unlink()

def main():
    """Run all tests"""
    print("\n" + "🔧 " + "="*66 + " 🔧")
    print("  R2 TILE UPLOAD DIAGNOSTIC TOOL")
    print("🔧 " + "="*66 + " 🔧\n")
    
    config_ok = test_r2_configuration()
    upload_ok = test_upload_small_file() if config_ok else False
    
    print("="*70)
    print("RESULTS:")
    print("="*70)
    print(f"Configuration:  {'✅ PASS' if config_ok else '❌ FAIL'}")
    print(f"Upload Test:    {'✅ PASS' if upload_ok else '⏭️  SKIPPED' if not config_ok else '❌ FAIL'}\n")
    
    if config_ok and upload_ok:
        print("✅ All tests passed! R2 tile uploads should work.\n")
        return 0
    else:
        print("⚠️  Some tests failed. Check configuration and credentials.\n")
        return 1

if __name__ == "__main__":
    exit(main())
