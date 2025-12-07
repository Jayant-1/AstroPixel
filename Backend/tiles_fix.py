# REPLACEMENT CODE FOR tiles.py - R2 tile serving fix
# Replace the R2 check section (lines 73-94) with this improved version

# If cloud storage (R2) is enabled, check if tiles have been uploaded
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
    logger.debug(f"Tile not found on R2 for dataset {dataset_id}, checking local storage")
