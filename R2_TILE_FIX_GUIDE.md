# FIX FOR R2 TILE 404 ERRORS - MANUAL APPLICATION GUIDE

## Problem

Tiles on R2 return 404 because tile serving code only checks metadata flag, not R2 directly.

## Location

File: `Backend/app/routers/tiles.py`
Lines: 73-94 (the entire R2 check block)

## Current Code (Remove This)

```python
    # If cloud storage (R2) is enabled, check if tiles have been uploaded
    # Only redirect to R2 if tiles are confirmed to be there
    if cloud_storage.enabled and cloud_storage.public_url:
        # Check if tiles have been uploaded to R2 (metadata flag)
        tiles_on_r2 = (
            dataset.extra_metadata and
            dataset.extra_metadata.get('tiles_uploaded_to_cloud') == True
        )

        if tiles_on_r2:
            # Generate R2 public URL and redirect
            tile_url = cloud_storage.get_tile_url(dataset_id, z, x, y, format, cache_bust)
            if tile_url:
                logger.debug(f"Redirecting to R2: {tile_url}")
                return RedirectResponse(
                    url=tile_url,
                    status_code=302,
                    headers={
                        "Cache-Control": "public, max-age=31536000",
                        "Access-Control-Allow-Origin": "*",
                    }
                )
        else:
            logger.debug(f"Tiles not yet uploaded to R2 for dataset {dataset_id}, serving from local")
```

## Replacement Code (Add This)

```python
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
```

## Why This Works

1. **Metadata flag check**: Fast path for recently uploaded datasets (no API call)
2. **Direct R2 query**: For datasets synced from R2, queries S3/R2 directly using `tile_exists()`
3. **Format fallback**: If PNG requested but JPG exists on R2, uses JPG
4. **Proper logging**: Logs which source (R2 vs local) serves each tile

## Testing

After applying this fix:

1. Try loading a dataset in Compare mode
2. Check browser Network tab - tiles should load from R2 public URL redirect
3. Check backend logs for "Serving tile from R2" messages

## Files to Also Check

- Both `Backend/app/routers/tiles.py` and `Astropixel-backend/app/routers/tiles.py` need this fix
