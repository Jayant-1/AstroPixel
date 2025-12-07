# Compare Section Bug Fixes - Complete Summary

## Bugs Identified & Fixed

### 🐛 Bug 1: Canvas Loading Tiles from Previous Dataset

**Problem:** When switching between datasets in comparison mode, the canvas continued to display tiles from the previous dataset, causing visual overlap and confusion.

**Root Cause:** OpenSeadragon was caching tile requests without a cache-busting mechanism. When the same tile coordinates were requested for a different dataset, the browser cache returned the old tiles.

**Solution:** Added a version parameter (`cacheBust`) to all tile URLs using the dataset's `updated_at` or `created_at` timestamp:

```javascript
// Before: /api/tiles/{id}/{z}/{x}/{y}.png
// After:  /api/tiles/{id}/{z}/{x}/{y}.png?v={timestamp}
```

**Files Modified:** `ComparisonView.jsx`

---

### 🐛 Bug 2: Select Dataset Doesn't Show Other Datasets

**Problem:** The dataset dropdown was empty - users couldn't see available datasets to compare.

**Root Cause:**

1. Missing placeholder/default option
2. No visual feedback for dataset options
3. Selection validation issue

**Solution:**

1. Added placeholder option: `<option value="">-- Select a dataset --</option>`
2. Added validation to prevent selecting the same dataset as the primary
3. Only datasets different from the primary are shown in dropdown

**Files Modified:** `ComparisonControls.jsx`

---

### 🐛 Bug 3: Overlay Not Working Properly

**Problem:** When switching to overlay mode, sometimes old tiles from previous datasets were visible, or overlay didn't update when switching compare datasets.

**Root Cause:**

1. Overlay was reused if it already existed instead of being recreated
2. Old overlay wasn't removed when switching datasets
3. Tile source wasn't updated for the overlay

**Solution:**

1. Always remove existing overlay before adding a new one when in overlay mode
2. Create fresh overlay tile source with correct dataset ID every time
3. Added dataset ID to dependency array to trigger recreation

**Before Logic:**

```javascript
// Only add if doesn't exist
if (itemCount === 1) {
  // Add overlay
} else if (itemCount > 1) {
  // Just update opacity
}
```

**After Logic:**

```javascript
// Always remove old overlay if exists
if (itemCount > 1) {
  removeItem(overlayItem);
}
// Always add fresh overlay
addTiledImage({ tileSource: createTileSource(secondDataset) });
```

**Files Modified:** `ComparisonView.jsx`

---

## Additional Improvements

### Viewer.jsx Enhancements

- Added logic to clear `secondDataset` when base dataset changes
- Prevents tile/data leakage between dataset switches

### ComparisonControls.jsx Enhancements

- Added dataset ID validation in onChange handler
- Prevents selecting same dataset for comparison

### Cache Busting Strategy

- Generates unique URL parameter based on dataset timestamp
- Prevents browser cache collisions across datasets
- Each dataset modification updates the cache key

---

## Testing Checklist

- [ ] Switch between datasets - canvas should show new tiles (not old ones)
- [ ] Select dataset dropdown shows available options
- [ ] Cannot select same dataset as primary dataset
- [ ] Overlay mode loads correct overlay tiles
- [ ] Switching between overlay and side-by-side works smoothly
- [ ] Opacity slider works in overlay mode
- [ ] Synchronization works in side-by-side mode
- [ ] Switching datasets clears overlay properly

---

## Files Changed

```
Frontend/src/components/viewer/ComparisonView.jsx      (+68 lines)
Frontend/src/components/viewer/ComparisonControls.jsx  (+10 lines)
Frontend/src/pages/Viewer.jsx                          (+2 lines)
```

## Commit Info

- **Commit:** `1ab0a0b`
- **Branch:** `main` (pushed to GitHub)

---

## Performance Impact

- ✅ Minimal: Only added URL parameters for cache busting
- ✅ No additional API calls
- ✅ Tile removal/addition only on mode changes (not every render)
- ✅ Uses existing OpenSeadragon APIs efficiently
