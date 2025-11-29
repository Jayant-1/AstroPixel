# Frontend Deployment (Vercel)

This document describes how to deploy the frontend to Vercel and configure the `VITE_API_BASE_URL` environment variable so the single-page app talks to your backend.

## Local build & test

```pwsh
cd "E:\Code\Work Station\Hackathon\AstroPixel\Frontend"
npm ci
npm run build
# Optional quick preview
npx serve dist -l 5173
```

## Deploy to Vercel

1. Sign in to Vercel and click **New Project** → **Import Git Repository** → select the `AstroPixel` repo.

2. **Project Settings**

   - **Root Directory**: `Frontend` (so Vercel builds only the frontend folder)
   - **Framework Preset**: Vite (auto-detected)
   - **Install Command**: `npm ci`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

3. **Environment Variables** (Vercel → Project → Settings → Environment Variables)

   - `VITE_API_BASE_URL` = `https://<your-backend-domain>`
     - This is injected at build time by Vite. Set appropriate values for `Production` and `Preview`.

4. Deploy: click **Deploy**. Vercel will build the app and publish at `https://<project>.vercel.app`.

## Common checks after deploy

- Open the Vercel URL and watch the DevTools Network tab to ensure API requests go to the backend domain set in `VITE_API_BASE_URL`.
- If CORS errors appear, add your Vercel domain to the backend `CORS_ORIGINS` env var.

## Notes

- `VITE_` prefixed env vars are embedded at build-time. If you change `VITE_API_BASE_URL` in Vercel after a deployment, re-deploy to pick up the change.
- For local development, the frontend reads values from `.env` files or `import.meta.env`.

---

Last updated: 2025-11-29
