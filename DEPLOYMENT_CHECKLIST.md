# Production Deployment Checklist

## Pre-Deployment ✅ (Already Done)

- [x] Identified root cause: `user_id` INTEGER vs string "demo-user"
- [x] Updated models: Changed `user_id` to `String(255)` in both Backend directories
- [x] Created migration scripts: `fix_production_db.py` and `migrate_user_id.py`
- [x] Committed changes to GitHub
- [x] Code is ready for deployment

## Production Deployment (TO DO)

- [ ] **Step 1: SSH into Hugging Face Space or use Terminal**

  - Navigate to your HF Space settings
  - Click Terminal button
  - Run the database fix

- [ ] **Step 2: Run Database Migration**
      Choose one:

  **Option A (Recommended - 1 command):**

  ```bash
  cd /home/user/app && python fix_production_db.py
  ```

  **Option B (Direct SQL):**

  ```bash
  psql $DATABASE_URL << EOF
  ALTER TABLE annotations DROP CONSTRAINT IF EXISTS annotations_user_id_fkey CASCADE;
  ALTER TABLE annotations ALTER COLUMN user_id TYPE VARCHAR(255) USING CAST(user_id AS VARCHAR);
  ALTER TABLE annotations ALTER COLUMN user_id SET DEFAULT 'anonymous';
  EOF
  ```

- [ ] **Step 3: Verify Database Fix**

  ```bash
  psql $DATABASE_URL << EOF
  SELECT column_name, data_type FROM information_schema.columns
  WHERE table_name='annotations' AND column_name='user_id';
  EOF
  ```

  Expected output: `user_id | character varying`

- [ ] **Step 4: Rebuild Backend Space**

  - Go to Space settings
  - Click "Restart this space" or
  - If using GitHub sync: Make a dummy commit to trigger auto-build

- [ ] **Step 5: Test Annotation Creation**
  - Go to https://timevolt-astropixel-frontend.hf.space (or your frontend URL)
  - Select a dataset
  - Draw a rectangle annotation
  - Check browser Network tab: should see `201 Created` response (not 500)
  - Annotation should appear on canvas

## Troubleshooting

### If Database Fix Fails

- [ ] Check if `annotations` table exists: `SELECT * FROM annotations LIMIT 1;`
- [ ] Verify PostgreSQL connection: `psql $DATABASE_URL -c "SELECT 1;"`
- [ ] Check table structure: `\d annotations` (in psql)

### If Annotations Still Fail After Fix

- [ ] Check backend logs in HF Space console
- [ ] Verify code was redeployed (check git commit hash)
- [ ] Try restarting the space again
- [ ] Check if dataset exists: `GET /api/datasets/{dataset_id}`

### If Need to Rollback

```bash
# Restore from backup or revert schema
# This is complex - contact database admin
```

## Verification Checklist

After deployment is complete:

- [ ] Database migration succeeded (user_id is VARCHAR)
- [ ] Backend redeployed with new code
- [ ] Can create rectangle annotations without 500 error
- [ ] Annotations appear on canvas
- [ ] Annotation API returns 201 Created status
- [ ] Multiple demo annotations can be created

## Time Estimate

- Database fix: 2-5 minutes
- Code rebuild: 2-5 minutes
- Testing: 5-10 minutes
- **Total: ~15 minutes**

## Documentation References

- **Quick Start:** See `PRODUCTION_FIX_GUIDE.md`
- **Technical Details:** See `SCHEMA_MIGRATION.md`
- **Code Changes:** See commit `3384ad2` on GitHub
- **Summary:** See `ANNOTATION_FIX_SUMMARY.md`

---

**Status:** Code deployed to GitHub ✅ | Waiting for production database migration ⏳
