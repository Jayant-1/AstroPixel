"""
Main FastAPI application for NASA Gigapixel Explorer
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.config import settings
from app.database import init_db, create_spatial_indexes
from app.routers import (
    datasets,
    tiles,
    search,
    health,
    annotations_simple,
)

# Configure Starlette to accept large uploads
import starlette.datastructures
starlette.datastructures.FormData._MAX_FORM_MEMORY_SIZE = settings.MAX_REQUEST_BODY_SIZE

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events
    """
    # Startup
    logger.info("Starting NASA Gigapixel Explorer API...")

    try:
        # Initialize database
        init_db()
        create_spatial_indexes()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

    yield

    # Shutdown
    logger.info("Shutting down NASA Gigapixel Explorer API...")


# Create FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    description="Backend API for exploring NASA's gigapixel imagery with advanced features",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "message": "Internal server error",
            "detail": str(exc) if settings.DEBUG else "An error occurred",
        },
    )


# Mount static files for tiles
try:
    app.mount("/tiles", StaticFiles(directory=str(settings.TILES_DIR)), name="tiles")
    logger.info(f"Mounted tiles directory: {settings.TILES_DIR}")
except Exception as e:
    logger.warning(f"Could not mount tiles directory: {e}")

# Mount static files for dataset previews
try:
    app.mount(
        "/datasets",
        StaticFiles(directory=str(settings.BASE_DIR / "datasets")),
        name="datasets",
    )
    logger.info(f"Mounted datasets directory: {settings.BASE_DIR / 'datasets'}")
except Exception as e:
    logger.warning(f"Could not mount datasets directory: {e}")


# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(datasets.router, prefix=settings.API_PREFIX, tags=["Datasets"])
app.include_router(tiles.router, prefix=settings.API_PREFIX, tags=["Tiles"])
app.include_router(
    annotations_simple.router, prefix=settings.API_PREFIX, tags=["Annotations"]
)
app.include_router(search.router, prefix=settings.API_PREFIX, tags=["Search"])


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "operational",
        "timestamp": datetime.utcnow().isoformat(),
        "documentation": "/docs",
        "endpoints": {
            "datasets": f"{settings.API_PREFIX}/datasets",
            "tiles": f"{settings.API_PREFIX}/tiles",
            "annotations": f"{settings.API_PREFIX}/annotations",
            "search": f"{settings.API_PREFIX}/search",
            "health": "/health",
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
        limit_request_fields=32768,
        limit_request_line=8190,
        limit_concurrency=100,
        # Keep connections alive longer to allow very large uploads to complete
        timeout_keep_alive=1800,  # 30 minutes
    )
