"""
API Routers package
"""

from app.routers import (
    datasets,
    tiles,
    search,
    health,
    annotations_simple,
    auth,
    admin,
    contact,
)

__all__ = ["datasets", "tiles", "search", "health", "annotations_simple", "auth", "admin", "contact"]

