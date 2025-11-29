"""
Health check and monitoring endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from app.database import get_db
from app.schemas import HealthResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint

    Returns:
        Health status of the API and dependencies
    """
    database_healthy = False
    redis_healthy = False

    # Check database
    try:
        db.execute("SELECT 1")
        database_healthy = True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")

    # Check Redis (if configured)
    try:
        # Import here to avoid dependency if Redis is not used
        from redis import Redis
        from app.config import settings

        redis_client = Redis.from_url(settings.REDIS_URL)
        redis_client.ping()
        redis_healthy = True
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        redis_healthy = False

    status = "healthy" if database_healthy else "unhealthy"

    return HealthResponse(
        status=status,
        timestamp=datetime.utcnow(),
        database=database_healthy,
        redis=redis_healthy,
    )


@router.get("/metrics")
async def metrics(db: Session = Depends(get_db)):
    """
    Prometheus-compatible metrics endpoint

    Returns:
        Metrics in Prometheus format
    """
    from app.models import Dataset, Annotation
    
    try:
        # Get actual counts
        total_datasets = db.query(Dataset).count()
        completed_datasets = db.query(Dataset).filter(Dataset.processing_status == "completed").count()
        total_annotations = db.query(Annotation).count()
        
        metrics_data = f"""# HELP nasa_datasets_total Total number of datasets
# TYPE nasa_datasets_total gauge
nasa_datasets_total {total_datasets}

# HELP nasa_datasets_completed Total number of completed datasets
# TYPE nasa_datasets_completed gauge
nasa_datasets_completed {completed_datasets}

# HELP nasa_annotations_total Total number of annotations
# TYPE nasa_annotations_total gauge
nasa_annotations_total {total_annotations}
"""
        return metrics_data
        
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return "# Error generating metrics\n"
