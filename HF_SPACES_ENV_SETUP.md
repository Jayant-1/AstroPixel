# HF Spaces Environment Variables Setup Guide

## 🚨 CRITICAL: Production is Failing Because Environment Variables Not Set

**Problem**: HF Spaces doesn't have access to your `.env` file (it's gitignored).  
**Result**: `USE_S3` defaults to `False`, R2 credentials are empty, tiles don't upload.

---

## ✅ SOLUTION: Set Environment Variables in HF Spaces

### Step 1: Go to HF Spaces Settings

1. Navigate to: https://huggingface.co/spaces/Timevolt/Astropixel-backend
2. Click **⚙️ Settings** tab (top right)
3. Scroll to **"Repository secrets"** section

### Step 2: Add These Environment Variables

**Click "Add a new secret" for each:**

#### 🔐 Database (Neon PostgreSQL)

```
Name:  DATABASE_URL
Value: postgresql://neondb_owner:npg_EyAmX9YpNq8l@ep-patient-sky-ah05n60d-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require
```

#### ☁️ Cloudflare R2 Storage (CRITICAL for tile uploads)

```
Name:  USE_S3
Value: true
```

```
Name:  AWS_ACCESS_KEY_ID
Value: 374b1e15b15a36db5b0e66485164db26
```

```
Name:  AWS_SECRET_ACCESS_KEY
Value: 8a9de3ca4ddd9a7bdea031c7f7a0a04f8659df8eb23b5da4015f33d9e0d893da
```

```
Name:  AWS_BUCKET_NAME
Value: astropixel-tiles
```

```
Name:  AWS_REGION
Value: auto
```

```
Name:  S3_ENDPOINT_URL
Value: https://034fdaa2967c7dbaf1855ab1ef540b44.r2.cloudflarestorage.com
```

```
Name:  R2_PUBLIC_URL
Value: https://pub-d63fc45b98114c6792f6f43a12e4c73b.r2.dev
```

#### 🔒 Security (Optional but Recommended)

```
Name:  SECRET_KEY
Value: your-secret-key-here-change-in-production
```

#### 🌐 CORS (If needed)

```
Name:  CORS_ORIGINS
Value: http://localhost:3000,http://localhost:5173,https://astro-pixel.vercel.app
```

---

## 📋 Quick Copy-Paste List (All Variables)

```bash
# DATABASE
DATABASE_URL=postgresql://neondb_owner:npg_EyAmX9YpNq8l@ep-patient-sky-ah05n60d-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require

# R2 STORAGE (MUST HAVE FOR TILE UPLOADS)
USE_S3=true
AWS_ACCESS_KEY_ID=374b1e15b15a36db5b0e66485164db26
AWS_SECRET_ACCESS_KEY=8a9de3ca4ddd9a7bdea031c7f7a0a04f8659df8eb23b5da4015f33d9e0d893da
AWS_BUCKET_NAME=astropixel-tiles
AWS_REGION=auto
S3_ENDPOINT_URL=https://034fdaa2967c7dbaf1855ab1ef540b44.r2.cloudflarestorage.com
R2_PUBLIC_URL=https://pub-d63fc45b98114c6792f6f43a12e4c73b.r2.dev

# OPTIONAL
SECRET_KEY=your-secret-key-here-change-in-production
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://astro-pixel.vercel.app
```

---

## 🔍 How to Verify After Setup

### 1. Check Startup Logs

After adding secrets, HF Space will auto-restart. Check logs for:

```
✅ Cloud Storage (R2) Configuration:
   USE_S3: true  ← Should be True, not False!
   Bucket: astropixel-tiles
   Endpoint: https://034fdaa2967c7dbaf...
   Public URL: https://pub-d63fc45b98114c6...
```

### 2. Upload Test Dataset

- Upload via Frontend: https://astro-pixel.vercel.app
- Check HF logs for: `✅ Successfully uploaded X tiles to R2`

### 3. Verify in R2 Console

- Go to: https://dash.cloudflare.com → R2 → astropixel-tiles
- Look for: `tiles/{dataset_id}/` folders

---

## ⚠️ Common Issues

### Issue: "USE_S3: False" in logs (even after setting secrets)

**Cause**: Secrets not saved or Space didn't restart  
**Fix**:

1. Re-check secrets are saved in HF Settings
2. Manually restart Space (⚙️ Settings → Factory reboot)

### Issue: "Cloud storage client not initialized"

**Cause**: Missing R2 credentials (AWS_ACCESS_KEY_ID, etc.)  
**Fix**: Add ALL 7 R2 variables listed above

### Issue: "Failed to connect to R2"

**Cause**: Wrong endpoint URL or credentials  
**Fix**: Double-check S3_ENDPOINT_URL and credentials match your R2 setup

---

## 📝 Step-by-Step Video Guide

### Adding Secrets in HF Spaces:

1. **Go to Space**: https://huggingface.co/spaces/Timevolt/Astropixel-backend
2. **Click Settings** (top navigation)
3. **Scroll down** to "Repository secrets"
4. **Click "+ New secret"**
5. **Add Name** (e.g., `USE_S3`)
6. **Add Value** (e.g., `true`)
7. **Click "Add secret"**
8. **Repeat for all variables** (7 R2 variables + 1 database)
9. **Space auto-restarts** after each secret is added

---

## ✅ Checklist

After setting up secrets, verify:

- [ ] Added `DATABASE_URL` secret
- [ ] Added `USE_S3=true` secret ⚠️ CRITICAL
- [ ] Added `AWS_ACCESS_KEY_ID` secret
- [ ] Added `AWS_SECRET_ACCESS_KEY` secret
- [ ] Added `AWS_BUCKET_NAME` secret
- [ ] Added `AWS_REGION=auto` secret
- [ ] Added `S3_ENDPOINT_URL` secret
- [ ] Added `R2_PUBLIC_URL` secret
- [ ] HF Space restarted (check logs)
- [ ] Logs show `USE_S3: true` (not False)
- [ ] Test upload works
- [ ] Tiles appear in R2 bucket

---

## 🆘 If Still Not Working

1. **Check HF Logs**: https://huggingface.co/spaces/Timevolt/Astropixel-backend/logs
2. **Look for errors** containing "R2", "boto3", "cloud storage"
3. **Verify secrets** are actually showing in HF Settings (sometimes they don't save)
4. **Factory reboot** Space if needed (⚙️ Settings → Factory reboot)
5. **Run diagnostic**: Add temporary logging in main.py to print env vars (remove after)

---

## 📌 Why This Matters

**Without these secrets**:

- ❌ `USE_S3 = False` (defaults to False in config.py)
- ❌ R2 credentials empty
- ❌ Tiles never uploaded
- ❌ Frontend can't display images (no tile URLs)
- ✅ Database works (but dataset shows as completed without tiles)

**With secrets configured**:

- ✅ `USE_S3 = True`
- ✅ R2 credentials loaded
- ✅ Tiles uploaded automatically
- ✅ Frontend displays images from R2 URLs
- ✅ Full end-to-end working!

---

**Last Updated**: December 7, 2025  
**Next Action**: Add secrets to HF Spaces, then verify with test upload
