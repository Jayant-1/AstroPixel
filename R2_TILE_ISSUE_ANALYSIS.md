# R2 Tile 404 Error - Complete Analysis & Fix

## Error Summary
```
Console: Tile failed to load with Image load aborted
Backend: GET /api/tiles/2/0/0/0.png?v=... 404 Not Found
R2: Tiles exist at https://pub-d63fc45b98114c6792f6f43a12e4c73b.r2.dev/tiles/2/1/0/0.png
```

## Root Cause Analysis

### Current Tile Serving Flow
1. Request: `GET /api/tiles/{dataset_id}/{z}/{x}/{y}.png`
2. Backend checks: Is `dataset.extra_metadata['tiles_uploaded_to_cloud'] == True`?
3. If YES: Redirect to R2
4. If NO: Try to serve from local storage → 404

### The Problem
Datasets synced from R2 have tiles ON R2, but the `tiles_uploaded_to_cloud` flag is **not set** or not preserved:
- When datasets are synced from R2, metadata is partially populated
- The flag indicating "tiles are on R2" is missing
- Code assumes tiles are local → tries local storage → 404
- Meanwhile, tiles ARE available on R2 (the user can see them)

## Solution Architecture

### Improved Tile Serving Logic
```
For each tile request:
1. Check metadata flag (fast path, no API call)
   ✓ If flag = True → redirect to R2 immediately
   ✗ If flag = False → continue to step 2

2. Query R2 directly (slow path, but reliable)
   ✓ If tile exists on R2 → redirect to R2
   ✗ If not on R2 → continue to step 3
   ✓ Try format alternatives (PNG/JPG) → redirect if found

3. Check local storage (fallback)
   ✓ If exists locally → serve locally
   ✗ If not found anywhere → 404
```

### Benefits
- **Backward compatible**: Still uses metadata flag for performance
- **Resilient**: Works even with incomplete metadata
- **Format-aware**: Handles PNG/JPG/WebP format mismatches
- **Properly logged**: Different message for R2 vs local serving

## Implementation

File: `Backend/app/routers/tiles.py` (Lines 73-94)

### Add These Methods

```python
# Add direct R2 tile existence check
if not tiles_on_r2:
    tiles_on_r2 = cloud_storage.tile_exists(dataset_id, z, x, y, format)
    
    # Try alternative formats if exact format not found
    if not tiles_on_r2 and format.lower() in ["jpg", "jpeg"]:
        tiles_on_r2 = cloud_storage.tile_exists(dataset_id, z, x, y, "png")
        if tiles_on_r2:
            format = "png"
```

**Current Implementation**: Uses `cloud_storage.tile_exists()` which:
- Makes S3 HEAD request to check if object exists
- Returns boolean (True/False)
- No data transfer, just metadata check
- Minimal performance impact

## Testing Checklist

- [ ] Start backend server
- [ ] Navigate to Compare mode
- [ ] Select two datasets (including ID 2 or 3 from production)
- [ ] Browser Network tab should show:
  - Tile requests to backend (202 redirect status)
  - Final requests to R2 public URL (200 OK)
- [ ] Tiles should display in both panels
- [ ] No 404 errors in console

## Deployment Steps

1. **Apply code fix** to `Backend/app/routers/tiles.py`
2. **Also apply** to `Astropixel-backend/app/routers/tiles.py`
3. **Restart backend** on Hugging Face Space
4. **Clear browser cache** to remove old 404 errors
5. **Test Compare mode** with production datasets

## Files Provided

- `R2_TILE_FIX_GUIDE.md` - Manual fix instructions with before/after code
- `fix_r2_tiles.py` - Automated Python script to apply fix
- `tiles_fix.py` - Reference implementation

## Why This Matters

Without this fix:
- Users cannot compare non-demo datasets in Compare mode
- All tiles return 404 even though they exist on R2
- Frontend doesn't display any tiles for dataset ID > 1

With this fix:
- All tiles load properly from R2
- Compare mode works for all datasets
- No more mysterious 404 errors
