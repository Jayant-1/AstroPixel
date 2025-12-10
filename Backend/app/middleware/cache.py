"""
Response caching middleware for API endpoints
Improves performance of frequently accessed endpoints
"""

from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
import hashlib
import json
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# In-memory cache with TTL
response_cache = {}

# Cache configuration: endpoint paths and their TTL in seconds
CACHE_CONFIG = {
    "/api/datasets": 300,  # 5 minutes for dataset list
    "/api/health": 60,  # 1 minute for health check
}


class CacheMiddleware(BaseHTTPMiddleware):
    """Middleware for caching GET responses"""

    async def dispatch(self, request: Request, call_next):
        # Only cache GET requests
        if request.method != "GET":
            return await call_next(request)

        # Check if this path should be cached
        should_cache = False
        cache_ttl = 0
        
        for path, ttl in CACHE_CONFIG.items():
            if request.url.path.startswith(path):
                should_cache = True
                cache_ttl = ttl
                break

        if not should_cache:
            return await call_next(request)

        # Generate cache key from path and query params
        cache_key = self._generate_cache_key(request)

        # Check if we have a valid cached response
        if cache_key in response_cache:
            cached_data = response_cache[cache_key]
            if datetime.now() < cached_data["expires_at"]:
                logger.debug(f"Cache hit for {request.url.path}")
                return Response(
                    content=cached_data["body"],
                    status_code=cached_data["status_code"],
                    headers=dict(cached_data["headers"]),
                    media_type=cached_data["media_type"],
                )
            else:
                # Cache expired, remove it
                del response_cache[cache_key]
                logger.debug(f"Cache expired for {request.url.path}")

        # Not cached or expired, get fresh response
        response = await call_next(request)

        # Cache successful responses only
        if response.status_code == 200 and "application/json" in response.headers.get(
            "content-type", ""
        ):
            try:
                body = b""
                async for chunk in response.body_iterator:
                    body += chunk

                response_cache[cache_key] = {
                    "body": body,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "media_type": response.media_type,
                    "expires_at": datetime.now() + timedelta(seconds=cache_ttl),
                }
                logger.debug(f"Cached response for {request.url.path} (TTL: {cache_ttl}s)")

                # Return cached response
                return Response(
                    content=body,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                    media_type=response.media_type,
                )
            except Exception as e:
                logger.warning(f"Failed to cache response: {e}")
                return response

        return response

    @staticmethod
    def _generate_cache_key(request: Request) -> str:
        """Generate cache key from request path and query params"""
        key_parts = [request.url.path]
        
        # Include relevant query params in cache key
        if request.url.query:
            # Sort params for consistent cache keys
            params = sorted(request.url.query.split("&"))
            key_parts.extend(params)

        key_string = "|".join(key_parts)
        return hashlib.md5(key_string.encode()).hexdigest()
