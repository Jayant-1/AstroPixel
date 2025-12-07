# Cloudflare R2 CORS Configuration - CRITICAL

⚠️ **IMPORTANT**: Without proper R2 CORS configuration, tiles will fail to load with CORS errors!

The backend redirects tile requests to R2 for performance, but R2 must have CORS headers configured to allow browser access from your frontend domain.

## Steps to Configure R2 CORS

1. **Go to Cloudflare Dashboard**

   - Navigate to R2 Object Storage
   - Select your bucket (pub-d63fc45b98114c6792f6f43a12e4c73b)

2. **Add CORS Policy**
   - Click on "Settings" tab
   - Scroll to "CORS Policy"
   - Add the following JSON configuration:

```json
[
  {
    "AllowedOrigins": ["*"],
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

3. **For Production (Recommended)**
   - Replace `"*"` with your actual frontend domains:

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
      "Cache-Control",
      "Access-Control-Allow-Origin"
    ],
    "MaxAgeSeconds": 3600
  }
]
```

4. **Save and Test**
   - Save the CORS policy
   - Wait 1-2 minutes for propagation
   - Test the export feature in your application

## Alternative: Using Cloudflare Workers (Advanced)

If you need more control, you can use a Cloudflare Worker to proxy requests and add CORS headers:

```javascript
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const bucketUrl = `https://YOUR_BUCKET_ID.r2.dev${url.pathname}`;

    const response = await fetch(bucketUrl);
    const newResponse = new Response(response.body, response);

    // Add CORS headers
    newResponse.headers.set("Access-Control-Allow-Origin", "*");
    newResponse.headers.set("Access-Control-Allow-Methods", "GET, HEAD");
    newResponse.headers.set("Cross-Origin-Resource-Policy", "cross-origin");

    return newResponse;
  },
};
```

## Verify CORS Configuration

Test if CORS is working:

```bash
curl -I -H "Origin: http://localhost:5173" \
  https://YOUR_R2_PUBLIC_URL/tiles/1/0/0/0.png
```

You should see these headers in the response:

```
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, HEAD
```

## Backend Changes Applied

The backend has been updated to:

1. Add CORS headers to local tile responses
2. Add CORS headers to R2 redirect responses
3. Configure OpenSeadragon with `crossOriginPolicy: "Anonymous"`

## Troubleshooting

### Common Error: "No 'Access-Control-Allow-Origin' header is present"

If you see this error in the console:

```
Access to image at 'https://pub-xxx.r2.dev/tiles/2/2/0/2.png' from origin 'https://astro-pixel.vercel.app'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the requested resource.
```

**Solution**: You MUST configure CORS on your R2 bucket (see steps above). The backend redirect cannot add CORS headers to R2 responses.

### Steps to Fix:

1. **Configure R2 CORS** (see JSON configuration above) - THIS IS MANDATORY
2. Wait 1-2 minutes for CORS changes to propagate
3. Clear browser cache (Ctrl+Shift+Delete or Cmd+Shift+Delete)
4. Hard refresh the page (Ctrl+F5 or Cmd+Shift+R)
5. Test tile loading in browser DevTools Network tab

### Additional Checks:

1. Verify R2 bucket is publicly accessible (Custom Domain should be set up)
2. Ensure R2_PUBLIC_URL in backend .env matches your R2 public domain
3. Check that bucket name is correct in configuration
4. Test CORS with curl:
   ```bash
   curl -I -H "Origin: https://astro-pixel.vercel.app" \
     https://pub-d63fc45b98114c6792f6f43a12e4c73b.r2.dev/tiles/2/2/0/0.png
   ```
   Should return: `Access-Control-Allow-Origin: *`

### If CORS Still Not Working:

Use Cloudflare Workers as a proxy (see Alternative section above) to manually add CORS headers.
