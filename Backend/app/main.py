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
import threading

from app.config import settings
from app.database import init_db, create_spatial_indexes
from app.routers import (
    datasets,
    tiles,
    search,
    health,
    annotations_simple,
    auth,
    admin,
)
from app.routers.datasets import preview_router
from app.middleware.rate_limit import RateLimitMiddleware
from app.services.cleanup import cleanup_scheduler

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
    
    # Log R2/Cloud Storage configuration
    logger.info(f"Cloud Storage (R2) Configuration:")
    logger.info(f"  USE_S3: {settings.USE_S3}")
    logger.info(f"  Bucket: {settings.AWS_BUCKET_NAME}")
    logger.info(f"  Region: {settings.AWS_REGION}")
    logger.info(f"  Endpoint: {settings.S3_ENDPOINT_URL}")
    logger.info(f"  Public URL: {settings.R2_PUBLIC_URL}")

    try:
        # Initialize database
        init_db()
        create_spatial_indexes()
        logger.info("Database initialized successfully")
        
        # Start cleanup scheduler in background thread (it handles its own event loop)
        def run_cleanup_scheduler():
            """Run cleanup scheduler in a separate thread with its own event loop"""
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(cleanup_scheduler())
            finally:
                loop.close()
        
        cleanup_thread = threading.Thread(target=run_cleanup_scheduler, daemon=True)
        cleanup_thread.start()
        logger.info("Cleanup scheduler started (runs every hour)")
        
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

# Rate limiting middleware (add BEFORE CORS)
app.add_middleware(RateLimitMiddleware)

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

# Include preview router BEFORE static mount so it can intercept preview requests
app.include_router(preview_router, tags=["Previews"])

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
app.include_router(health.router, prefix="/api", tags=["Health"])
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"])
app.include_router(admin.router, prefix=settings.API_PREFIX, tags=["Admin"])
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
            "auth": f"{settings.API_PREFIX}/auth",
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
