# Annotation User ID Schema Fix

## Problem
The production PostgreSQL database has `annotations.user_id` defined as `INTEGER` with a Foreign Key to the `users` table, but the frontend sends demo annotations with `user_id: "demo-user"` (a string), causing a 500 error:

```
invalid input syntax for type integer: "demo-user"
```

## Solution
Changed the data model to support **string user IDs** for demo/anonymous users.

## What Changed

### 1. Database Schema
`Annotation.user_id` column:
- **Before**: `INTEGER` Foreign Key to `users.id`
- **After**: `VARCHAR(255)` with default `'anonymous'`

**Files Updated:**
- `Backend/app/models.py` - Removed Foreign Key relationship
- `Astropixel-backend/app/models.py` - Removed Foreign Key relationship

### 2. Application Code
- Removed `User` → `Annotation` relationship from the model
- Supports string user IDs (demo-user, anonymous, or any user identifier)

## Production Deployment Steps

### Step 1: Apply Database Migration (IMMEDIATE - before redeploying)
Run the SQL migration on the production PostgreSQL database:

```bash
# From Backend directory
python fix_production_db.py
```

This script will:
1. Drop the foreign key constraint on `annotations.user_id`
2. Alter the column type from `INTEGER` to `VARCHAR(255)`
3. Set default value to `'anonymous'`

**This must be done BEFORE the code deployment**, as existing code will still try to insert integer values.

### Step 2: Deploy Updated Code
Deploy the updated `Backend/app/models.py` with the string user_id support.

## Local Development

### Option A: Fresh Database (Recommended)
```bash
cd Backend
rm nasa_explorer.db  # Delete SQLite database
# Restart server - tables will be recreated with new schema
```

### Option B: Migrate Existing SQLite Database
```bash
python migrate_user_id.py
```

## Testing Annotation Creation

After deployment, test creating an annotation:

```bash
curl -X POST http://localhost:8000/api/annotations \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": 1,
    "user_id": "demo-user",
    "geometry": {"type": "Rectangle", "coordinates": [[0, 0], [100, 100]]},
    "annotation_type": "rectangle",
    "label": "Test",
    "description": "Test annotation",
    "confidence": 1.0,
    "properties": {"color": "#10b981"}
  }'
```

## Files Added
- `Backend/migrate_user_id.py` - Generic migration for both SQLite and PostgreSQL
- `Backend/fix_production_db.py` - Direct SQL fix for production database
- `Astropixel-backend/migrate_user_id.py` - Same migration for alternate backend

## Rollback (if needed)
If you need to revert, you would need to:
1. Add Foreign Key constraint back
2. Migrate string user_ids back to integers
3. Restore old code

This is complex, so make sure to test the migration first in a staging environment.
