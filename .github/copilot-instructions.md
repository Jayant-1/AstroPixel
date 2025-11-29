# AstroPixel - NASA Gigapixel Explorer Copilot Instructions

## Project Architecture

This is a **full-stack NASA imagery viewer** with tile-based gigapixel zooming similar to Google Maps. The system has two independent but integrated parts:

- **Backend**: FastAPI Python server that processes GeoTIFF files into tile pyramids using GDAL
- **Frontend**: React + Vite SPA that renders tiles using OpenSeadragon for smooth pan/zoom

### Key Data Flow

**Complete Upload-to-Visualization Pipeline:**

1. **User Upload** (`FileUploader.jsx`):

   - User selects .tif/.tiff file via drag-drop or click
   - Provides metadata: name (required), description (optional), category (earth/mars/space)
   - Component calls `api.uploadDataset(file, name, description, category)`

2. **Backend Processing** (`POST /api/datasets/upload`):

   - Validates file type and size
   - Saves to `uploads/` directory
   - `DatasetProcessor.process_dataset()` extracts metadata using GDAL
   - Creates database entry with `processing_status = "pending"`
   - `SimpleTileGenerator.generate_tiles()` creates tile pyramid in `tiles/{dataset_id}/`
   - Updates `processing_status = "completed"` or `"failed"`
   - Generates preview thumbnail in `datasets/{dataset_id}_preview.jpg`

3. **Status Polling** (Frontend):

   - After upload, polls `GET /api/datasets/{id}` every 5 seconds
   - Monitors `processing_status` field
   - Shows progress: "Uploading..." → "Processing tiles..." → "Completed"
   - Auto-navigates to viewer on success

4. **Tile Serving** (`GET /api/tiles/{dataset_id}/{z}/{x}/{y}.jpg`):

   - Backend serves pre-generated tiles from `tiles/{dataset_id}/{z}/{x}/{y}.jpg`
   - Returns blank tile for missing coordinates (edge cases)
   - Static mount at `/tiles` provides direct file access

5. **Visualization** (`ViewerCanvas.jsx`):
   - OpenSeadragon requests tiles via `getTileUrl(level, x, y)` callback
   - Dynamically calculates `maxLevel = Math.ceil(log2(max(width, height) / 256))`
   - Loads visible tiles based on viewport, supports smooth zoom/pan

## Critical Development Environment

### Backend (PowerShell on Windows)

```powershell
# ALWAYS activate conda environment first
conda activate astropixel

# Start server (or use ./start_server.ps1)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Environment Requirements:**

- Python 3.11+ via conda (environment: `astropixel`)
- **GDAL is MANDATORY** - core dependency for tile generation (`osgeo` module)
- SQLite database for development (PostgreSQL+PostGIS for production spatial features)

**Common Gotchas:**

- GDAL import errors = wrong Python environment (must use conda)
- Spatial index warnings = expected in SQLite mode, harmless
- Test with: `http://localhost:8000/docs` (Swagger UI)

### Frontend

```bash
cd Frontend
npm install
npm run dev  # Runs on http://localhost:5173
```

**Environment:**

- VITE_API_BASE_URL defaults to `http://localhost:8000`
- OpenSeadragon loads tiles dynamically, check browser Network tab for 404s

## Project-Specific Patterns

### Backend Patterns

**Database Models** (`app/models.py`):

- SQLite for dev, but models designed for PostgreSQL+PostGIS production
- `bounds` field disabled in SQLite, uses `bounds_json` instead
- Avoid reserved word `metadata` - use `extra_metadata`

**Tile Generation** (`app/services/tile_generator.py`):

- Uses GDAL `gdal2tiles.py` subprocess approach for performance
- Tiles organized as: `tiles/{dataset_id}/{z}/{x}/{y}.jpg`
- Returns blank tiles for missing coordinates (edge tiles)

**API Routing**:

- All API routes prefixed with `/api` (settings.API_PREFIX)
- Tiles served via static mount at `/tiles` AND dynamic endpoint `/api/tiles/{dataset_id}/{z}/{x}/{y}`
- Background processing uses FastAPI BackgroundTasks for async tile generation

**Config Pattern** (`app/config.py`):

- Uses Pydantic Settings with `.env` file
- CORS_ORIGINS accepts comma-separated string or list
- Validators transform strings to appropriate types (see `parse_cors_origins`)

### Frontend Patterns

**State Management**:

- Global state in `AppContext.jsx` using React Context (NOT Redux/Zustand)
- Access via `useApp()` hook anywhere in component tree
- Pattern: `const { datasets, selectedDataset, viewMode, setViewMode } = useApp()`

**OpenSeadragon Integration** (`components/viewer/ViewerCanvas.jsx`):

- Dynamically generates tile URLs via `getTileUrl` callback
- Critical: `maxLevel` calculated as `Math.ceil(Math.log2(max(width, height) / 256))`
- Viewer instance stored in ref, not state (prevents re-renders)

**API Client** (`services/api.js`):

- Axios instance with interceptors for centralized error handling
- Base URL from `import.meta.env.VITE_API_BASE_URL` (Vite env var)
- Fallback to demo data if API fails (see `loadDatasets` in AppContext)

**Routing**:

- React Router v6 with nested routes in `App.jsx`
- Dataset viewer at `/viewer/:datasetId`
- Uses `useParams()` to extract datasetId, then fetches from API

**Component Structure**:

- UI primitives in `components/ui/` (shadcn-style pattern)
- Viewer-specific components in `components/viewer/`
- Pages use composition: `<Viewer>` imports `<ViewerCanvas>`, `<AnnotationTools>`, etc.

## File Organization Conventions

**Backend**:

- `app/routers/` - FastAPI route handlers (thin layer)
- `app/services/` - Business logic (tile generation, dataset processing)
- `app/models.py` - SQLAlchemy ORM models
- `app/schemas.py` - Pydantic request/response schemas
- Database migrations NOT used (dev project, uses `Base.metadata.create_all`)

**Frontend**:

- `src/pages/` - Route components (Home, Viewer, NotFound)
- `src/components/` - Reusable components (layout, ui, viewer)
- `src/context/` - Global state providers
- `src/services/` - API clients and external integrations
- CSS via Tailwind utility classes (no CSS modules)

## Testing & Debugging

**Backend**:

- pytest configured but no tests written yet
- Manual testing via Swagger UI at `/docs`
- Check tile generation: `GET /api/tiles/1/0/0/0.jpg` should return image

**Frontend**:

- No test suite configured
- Debug tile loading via browser DevTools Network tab
- Console logs in `ViewerCanvas.jsx` show tile URLs being requested

## Common Workflows

**Upload and View New Dataset (Complete Flow)**:

1. **Start Backend** (PowerShell):

   ```powershell
   cd Backend
   conda activate astropixel
   .\start_server.ps1
   ```

2. **Start Frontend**:

   ```bash
   cd Frontend
   npm run dev
   ```

3. **Upload Dataset**:

   - Navigate to `http://localhost:5173`
   - Click upload area on home page
   - Select .tif/.tiff GeoTIFF file
   - Fill in name, description, category
   - Click "Upload & Process"
   - Wait for processing (status shows in UI)
   - Auto-redirects to viewer on completion

4. **Verify Tiles**:
   - Check `Backend/tiles/{dataset_id}/` for generated pyramid
   - Test tile endpoint: `http://localhost:8000/api/tiles/{dataset_id}/0/0/0.jpg`
   - Verify dataset in DB: `http://localhost:8000/api/datasets/{dataset_id}`

**Add new dataset manually (script)**:

```python
# Backend: Use process_nasa_files.py script
python process_nasa_files.py
```

**Database reset** (SQLite):

```bash
# Backend directory
rm nasa_explorer.db
# Restart server to recreate tables
```

**Fix CORS issues**:
Edit `Backend/.env` → `CORS_ORIGINS=http://localhost:5173,http://localhost:3000`

**Debugging tile loading issues**:

1. Check backend logs for tile generation errors
2. Open browser DevTools Network tab → filter by "tiles"
3. Verify tile URLs return 200 (not 404/500)
4. Check `ViewerCanvas.jsx` console logs for tile request info
5. Validate dataset `processing_status = "completed"` in database

## Deployment Considerations

- Currently dev-only setup (SQLite, local files)
- Production needs: PostgreSQL+PostGIS, Redis, S3/object storage for tiles
- Annotations feature disabled (requires PostGIS spatial types)
- No authentication/authorization implemented

## Dependencies to Preserve

**Backend Critical**:

- GDAL (via conda, not pip - system dependency)
- FastAPI 0.109.0
- SQLAlchemy with SQLite driver

**Frontend Critical**:

- OpenSeadragon 4.1+ (tile viewer core)
- React 18+ with Router v6
- Vite build tool (NOT Create React App)

# Don't create a useless files or folders like components that are not used.
