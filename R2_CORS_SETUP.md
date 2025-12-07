# Cloudflare R2 CORS Configuration

To allow canvas export functionality, you need to configure CORS on your Cloudflare R2 bucket.

## Steps to Configure R2 CORS

1. **Go to Cloudflare Dashboard**

   - Navigate to R2 Object Storage
   - Select your bucket

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
      "https://yourdomain.com",
      "https://www.yourdomain.com",
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

If export still fails:

1. Clear browser cache
2. Check browser console for CORS errors
3. Verify R2 bucket is publicly accessible
4. Ensure R2_PUBLIC_URL in .env is correct
5. Test with browser DevTools Network tab to see actual headers
