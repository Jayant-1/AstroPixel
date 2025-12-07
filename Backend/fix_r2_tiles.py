#!/usr/bin/env python3
"""
Automatic fix for R2 tile serving 404 issue
Run this script to update the tile serving logic
"""

import re
from pathlib import Path

def fix_tiles_router():
    tiles_py = Path("app/routers/tiles.py")
    
    if not tiles_py.exists():
        print(f"❌ {tiles_py} not found")
        return False
    
    content = tiles_py.read_text()
    
    # Find and replace the old R2 check logic
    old_pattern = r"""    # If cloud storage \(R2\) is enabled, check if tiles have been uploaded
    # Only redirect to R2 if tiles are confirmed to be there
    if cloud_storage\.enabled and cloud_storage\.public_url:
        # Check if tiles have been uploaded to R2 \(metadata flag\)
        tiles_on_r2 = \(
            dataset\.extra_metadata and 
            dataset\.extra_metadata\.get\('tiles_uploaded_to_cloud'\) == True
        \)
        
        if tiles_on_r2:
            # Generate R2 public URL and redirect
            tile_url = cloud_storage\.get_tile_url\(dataset_id, z, x, y, format, cache_bust\)
            if tile_url:
                logger\.debug\(f"Redirecting to R2: \{tile_url\}"\)
                return RedirectResponse\(
                    url=tile_url,
                    status_code=302,
                    headers=\{
                        "Cache-Control": "public, max-age=31536000",
                        "Access-Control-Allow-Origin": "\*",
                    \}
                \)
        else:
            logger\.debug\(f"Tiles not yet uploaded to R2 for dataset \{dataset_id\}, serving from local"\)"""
    
    new_code = """    # If cloud storage (R2) is enabled, check if tiles have been uploaded
    # Try metadata flag first, then check R2 directly for datasets synced from cloud
    if cloud_storage.enabled and cloud_storage.public_url:
        # Check if tiles have been uploaded to R2 (metadata flag)
        tiles_on_r2 = (
            dataset.extra_metadata and 
            dataset.extra_metadata.get('tiles_uploaded_to_cloud') == True
        )
        
        # If flag not set, check R2 directly (for datasets synced from cloud)
        if not tiles_on_r2:
            tiles_on_r2 = cloud_storage.tile_exists(dataset_id, z, x, y, format)
            
            # If exact format not found, try alternatives
            if not tiles_on_r2:
                if format.lower() in ["jpg", "jpeg"]:
                    tiles_on_r2 = cloud_storage.tile_exists(dataset_id, z, x, y, "png")
                    if tiles_on_r2:
                        format = "png"
                elif format.lower() == "png":
                    tiles_on_r2 = cloud_storage.tile_exists(dataset_id, z, x, y, "jpg")
                    if tiles_on_r2:
                        format = "jpg"
        
        if tiles_on_r2:
            # Generate R2 public URL and redirect
            tile_url = cloud_storage.get_tile_url(dataset_id, z, x, y, format, cache_bust)
            if tile_url:
                logger.info(f"🔗 Serving tile from R2: {dataset_id}/{z}/{x}/{y}.{format}")
                return RedirectResponse(
                    url=tile_url,
                    status_code=302,
                    headers={
                        "Cache-Control": "public, max-age=31536000",
                        "Access-Control-Allow-Origin": "*",
                    }
                )

        # If we get here and cloud storage is enabled, log that we're falling back to local
        if cloud_storage.enabled:
            logger.debug(f"Tile not found on R2 for dataset {dataset_id}, checking local storage")"""
    
    if old_pattern in content:
        content = content.replace(old_pattern, new_code)
        tiles_py.write_text(content)
        print(f"✅ Successfully fixed {tiles_py}")
        return True
    else:
        print(f"⚠️  Could not find exact pattern to replace")
        print("Manual fix needed - see R2_TILE_FIX_NEEDED.txt")
        return False

if __name__ == "__main__":
    fix_tiles_router()
