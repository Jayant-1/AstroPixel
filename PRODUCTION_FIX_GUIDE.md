# URGENT: Production Annotation Fix - Deployment Guide

## Executive Summary

Annotation creation is failing on production with a 500 error because the PostgreSQL database expects `user_id` to be an integer, but the frontend sends string values like `"demo-user"`.

**Status:** Model code updated ✅ | Database schema still needs update ❌

## Immediate Action Required

### 1. Fix Production Database (DO THIS FIRST!)

The production Hugging Face database needs a schema migration. You have two options:

#### Option A: Direct SQL via Hugging Face Terminal (FASTEST)

1. Go to https://huggingface.co/spaces/timevolt/astropixel-backend (or your space URL)
2. Open the Terminal tab
3. Run these commands:

```bash
cd /home/user/app

# Connect to PostgreSQL and fix the schema
python -c "
from app.database import SessionLocal
from sqlalchemy import text

db = SessionLocal()
try:
    # Drop foreign key
    db.execute(text('ALTER TABLE annotations DROP CONSTRAINT IF EXISTS annotations_user_id_fkey CASCADE;'))
    db.commit()
    print('✅ Dropped foreign key constraint')
except:
    db.rollback()

try:
    # Change column type
    db.execute(text('ALTER TABLE annotations ALTER COLUMN user_id TYPE VARCHAR(255) USING CAST(user_id AS VARCHAR);'))
    db.commit()
    print('✅ Changed user_id to VARCHAR(255)')
except Exception as e:
    db.rollback()
    print(f'Error: {e}')

try:
    # Set default
    db.execute(text('ALTER TABLE annotations ALTER COLUMN user_id SET DEFAULT \'anonymous\';'))
    db.commit()
    print('✅ Set default value to anonymous')
except:
    pass

db.close()
"
```

#### Option B: Via Migration Script (If Direct SQL Fails)

```bash
cd /home/user/app
python fix_production_db.py
```

### 2. Redeploy Backend Code

After the database is fixed:

1. Push updated code to GitHub (`git push`)
2. Rebuild Hugging Face Space:
   - Go to Space settings
   - Click "Restart this space" or
   - Make a dummy commit to trigger auto-rebuild

## What Was Changed

### Code Changes

✅ **Already committed:**

- `Backend/app/models.py` - Changed `user_id` from `Integer` FK to `String(255)`
- `Astropixel-backend/app/models.py` - Same change

### Database Migration

🚀 **Scripts provided:**

- `Backend/fix_production_db.py` - One-click fix for production
- `Backend/migrate_user_id.py` - Generic migration for SQLite or PostgreSQL
- `Backend/SCHEMA_MIGRATION.md` - Detailed documentation

## Testing After Fix

Test annotation creation in browser console:

```javascript
// In browser console on viewer page
const response = await fetch(
  "https://timevolt-astropixel-backend.hf.space/api/annotations",
  {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dataset_id: 1,
      user_id: "demo-user",
      geometry: {
        type: "Rectangle",
        coordinates: [
          [0, 0],
          [100, 100],
        ],
      },
      annotation_type: "rectangle",
      label: "Test",
      description: "test annotation",
      confidence: 1,
      properties: { color: "#10b981" },
    }),
  }
);
console.log(await response.json());
```

Expected: `200 Created` with annotation data (not 500 error)

## Troubleshooting

### Still Getting 500 Error After Fix?

1. Verify database fix worked - check `user_id` column type:

   ```sql
   SELECT column_name, data_type FROM information_schema.columns
   WHERE table_name='annotations' AND column_name='user_id';
   ```

   Should show: `user_id | character varying`

2. Restart the backend Space after database fix

3. Check logs for other errors

### Migration Script Errors?

Run with verbose logging:

```bash
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
exec(open('fix_production_db.py').read())
"
```

## Local Testing (Before Production)

To test locally with the same PostgreSQL-like behavior:

```bash
# Use PostgreSQL locally
export DATABASE_URL=postgresql://user:password@localhost/astropixel

# Or migrate SQLite
python migrate_user_id.py
```

Then test annotation creation locally to ensure it works before production deployment.

## Questions?

- Check `SCHEMA_MIGRATION.md` for detailed documentation
- Review the model changes in `app/models.py`
- Check Hugging Face Space logs for detailed error messages

---

**Timeline:**

- ⏰ Database fix: ~5 minutes
- ⏰ Code redeploy: ~2-5 minutes (automatic if using GitHub auto-rebuild)
- ⏰ Total: ~10 minutes
