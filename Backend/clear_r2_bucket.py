"""
Clear all objects from Cloudflare R2 bucket
WARNING: This will permanently delete all files in the bucket!
"""

import boto3
from botocore.config import Config
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# R2 Configuration from .env
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME")
S3_ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")

print("🗑️  Cloudflare R2 Bucket Cleanup")
print("=" * 50)
print(f"Bucket: {AWS_BUCKET_NAME}")
print(f"Endpoint: {S3_ENDPOINT_URL}")
print()

# Confirm deletion
confirm = input("⚠️  WARNING: This will DELETE ALL FILES in the bucket!\nType 'DELETE' to confirm: ")

if confirm != "DELETE":
    print("❌ Cancelled. No files were deleted.")
    exit(0)

# Create S3 client for R2
s3_client = boto3.client(
    "s3",
    endpoint_url=S3_ENDPOINT_URL,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    config=Config(signature_version="s3v4"),
    region_name="auto"
)

try:
    print("\n🔍 Listing all objects in bucket...")
    
    # List all objects
    paginator = s3_client.get_paginator('list_objects_v2')
    pages = paginator.paginate(Bucket=AWS_BUCKET_NAME)
    
    deleted_count = 0
    total_size = 0
    
    for page in pages:
        if 'Contents' not in page:
            print("✅ Bucket is already empty!")
            break
            
        objects = page['Contents']
        print(f"📋 Found {len(objects)} objects in this batch...")
        
        # Prepare objects for deletion
        delete_keys = [{'Key': obj['Key']} for obj in objects]
        
        # Calculate size
        batch_size = sum(obj['Size'] for obj in objects)
        total_size += batch_size
        
        # Delete objects in batch
        response = s3_client.delete_objects(
            Bucket=AWS_BUCKET_NAME,
            Delete={'Objects': delete_keys}
        )
        
        if 'Deleted' in response:
            deleted_count += len(response['Deleted'])
            print(f"✅ Deleted {len(response['Deleted'])} objects")
            
        if 'Errors' in response:
            print(f"❌ Errors occurred:")
            for error in response['Errors']:
                print(f"   - {error['Key']}: {error['Message']}")
    
    # Convert size to human readable
    if total_size < 1024:
        size_str = f"{total_size} B"
    elif total_size < 1024 * 1024:
        size_str = f"{total_size / 1024:.2f} KB"
    elif total_size < 1024 * 1024 * 1024:
        size_str = f"{total_size / (1024 * 1024):.2f} MB"
    else:
        size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"
    
    print("\n" + "=" * 50)
    print(f"✨ Cleanup Complete!")
    print(f"📊 Total objects deleted: {deleted_count}")
    print(f"💾 Total size freed: {size_str}")
    print("=" * 50)
    
except Exception as e:
    print(f"\n❌ Error occurred: {str(e)}")
    print("Check your R2 credentials and bucket name in .env file")
