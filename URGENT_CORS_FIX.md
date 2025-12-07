# URGENT: Fix CORS Error for Tile Loading

## Current Issue

Tiles are failing to load with CORS error:

```
Access to image at 'https://pub-d63fc45b98114c6792f6f43a12e4c73b.r2.dev/tiles/2/2/0/2.png'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present
```

## Root Cause

The R2 bucket `pub-d63fc45b98114c6792f6f43a12e4c73b` does NOT have CORS configured, so browser blocks access.

## IMMEDIATE FIX (Required)

### ✅ CORS Policy Applied - But Browser Cache Issue

Your CORS policy is **CORRECT** and **ACTIVE** (verified via curl). The issue is browser cache.

**Your Current CORS Config** (Confirmed Working):

```json
[
  {
    "AllowedOrigins": [
      "https://astro-pixel.vercel.app",
      "https://timevolt-astropixel-backend.hf.space",
      "http://localhost:5173",
      "http://localhost:3000"
    ],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": [
      "ETag",
      "Content-Type",
      "Content-Length",
      "Cache-Control"
    ],
    "MaxAgeSeconds": 86400
  }
]
```

### Clear Browser Cache (REQUIRED)

The browser cached the old CORS-blocked responses. You MUST:

1. **Hard Refresh** (clears page cache):

   - Windows/Linux: `Ctrl + Shift + R` or `Ctrl + F5`
   - Mac: `Cmd + Shift + R`

2. **Or Clear All Cache**:

   - Chrome: `Ctrl + Shift + Delete` → Clear "Cached images and files"
   - Firefox: `Ctrl + Shift + Delete` → Clear "Cache"
   - Edge: `Ctrl + Shift + Delete` → Clear "Cached images and files"

3. **Or Use Incognito/Private Mode** to test without cache

4. **Disable Cache in DevTools** (Recommended for Testing):

   - Open DevTools (F12)
   - Go to Network tab
   - Check "Disable cache" checkbox
   - Keep DevTools open and refresh

5. **Emergency: Force Reload Viewer** (Run in Browser Console):

   ```javascript
   // Open browser console (F12) and paste this:
   window.location.reload(true); // Hard reload

   // Or force clear service workers:
   navigator.serviceWorker.getRegistrations().then(function (registrations) {
     for (let registration of registrations) {
       registration.unregister();
     }
   });
   window.location.reload(true);
   ```

### Option 2: Use Cloudflare Worker Proxy (Alternative - 10 minutes)

Create a Cloudflare Worker to proxy R2 requests and add CORS headers:

```javascript
export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    // Proxy to R2
    const r2Url = `https://pub-d63fc45b98114c6792f6f43a12e4c73b.r2.dev${url.pathname}${url.search}`;
    const response = await fetch(r2Url);

    // Clone response and add CORS headers
    const newResponse = new Response(response.body, response);
    newResponse.headers.set("Access-Control-Allow-Origin", "*");
    newResponse.headers.set("Access-Control-Allow-Methods", "GET, HEAD");
    newResponse.headers.set("Access-Control-Allow-Headers", "*");
    newResponse.headers.set("Cross-Origin-Resource-Policy", "cross-origin");

    return newResponse;
  },
};
```

Then update backend `.env`:

```
R2_PUBLIC_URL=https://your-worker.workers.dev
```

## Verification ✅

CORS is **CONFIRMED WORKING**. Test result:

```bash
curl -I -H "Origin: https://astro-pixel.vercel.app" \
  https://pub-d63fc45b98114c6792f6f43a12e4c73b.r2.dev/tiles/1/0/0/0.png

# Response includes:
Access-Control-Allow-Origin: https://astro-pixel.vercel.app
Access-Control-Expose-Headers: ETag,Content-Type,Content-Length,Cache-Control
Vary: Origin
```

✅ R2 CORS is configured correctly
⚠️ Issue is browser cache - clear cache to fix

## Why This Error Persists Even After CORS Fix

1. **Initial State**: R2 had no CORS → Browser cached failed CORS responses
2. **After Fix**: R2 now has CORS headers (confirmed working)
3. **Browser Still Errors**: Browser serves cached CORS-blocked responses
4. **Solution**: Clear browser cache to fetch fresh responses with CORS headers

### Technical Details

- Browser caches not just the image, but also the **CORS preflight result**
- Failed CORS checks are cached for the `MaxAgeSeconds` duration
- Even though R2 now returns correct headers, browser doesn't re-check
- Clearing cache forces browser to make fresh requests and see new CORS headers

## Production Setup (After Testing)

For production, restrict CORS to specific origins:

```json
[
  {
    "AllowedOrigins": [
      "https://astro-pixel.vercel.app",
      "https://timevolt-astropixel-backend.hf.space"
    ],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "ExposeHeaders": [
      "ETag",
      "Content-Type",
      "Content-Length",
      "Cache-Control"
    ],
    "MaxAgeSeconds": 3600
  }
]
```
