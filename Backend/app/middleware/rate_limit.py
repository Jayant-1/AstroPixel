"""
Rate limiting middleware for production-grade API protection
Implements sliding window rate limiting with Redis-like in-memory storage
"""

import time
import logging
from typing import Callable, Dict, Tuple
from collections import defaultdict, deque
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class RateLimitStore:
    """
    In-memory rate limit storage with automatic cleanup
    For production, replace with Redis for distributed rate limiting
    """
    
    def __init__(self):
        self._store: Dict[str, deque] = defaultdict(deque)
        self._last_cleanup = time.time()
    
    def add_request(self, key: str, timestamp: float):
        """Add a request timestamp for the given key"""
        self._store[key].append(timestamp)
        
        # Periodic cleanup to prevent memory leaks
        if time.time() - self._last_cleanup > 300:  # Every 5 minutes
            self.cleanup()
    
    def get_requests(self, key: str, window_seconds: int) -> int:
        """Get number of requests within the time window"""
        now = time.time()
        cutoff = now - window_seconds
        
        # Remove old requests
        while self._store[key] and self._store[key][0] < cutoff:
            self._store[key].popleft()
        
        return len(self._store[key])
    
    def cleanup(self):
        """Remove entries with no recent requests"""
        now = time.time()
        keys_to_remove = []
        
        for key, timestamps in self._store.items():
            # Remove timestamps older than 1 hour
            while timestamps and timestamps[0] < now - 3600:
                timestamps.popleft()
            
            # Remove empty keys
            if not timestamps:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self._store[key]
        
        self._last_cleanup = now
        logger.info(f"Rate limit store cleanup: removed {len(keys_to_remove)} keys")


# Global rate limit store
rate_limit_store = RateLimitStore()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware with tiered limits:
    - Upload endpoints: 5 requests per hour per IP
    - Auth endpoints: 10 requests per 15 minutes per IP
    - Other endpoints: 100 requests per minute per IP
    """
    
    # Rate limit configurations (requests, window_seconds)
    # NOTE: Chunked uploads can send hundreds of requests; keep generous limits here.
    RATE_LIMITS = {
        "/api/datasets/upload/chunk": (2000, 3600),  # allow ~2000 chunks per hour per IP
        "/api/datasets/upload/init": (50, 3600),     # init calls are rare
        "/api/datasets/upload": (20, 3600),          # metadata/finalize calls
        "/api/auth/register": (3, 900),              # 3 registrations per 15 minutes
        "/api/auth/login": (10, 900),                # 10 login attempts per 15 minutes
        "default": (100, 60),                        # 100 requests per minute for all other endpoints
    }
    
    EXEMPT_PATHS = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/api/health",
        "/tiles/",  # Tile serving should be fast
        "/datasets/",  # Static file serving
    ]
    
    async def dispatch(self, request: Request, call_next: Callable):
        """Process rate limiting for each request"""
        
        # Skip rate limiting for exempt paths
        path = request.url.path
        if any(path.startswith(exempt) for exempt in self.EXEMPT_PATHS):
            return await call_next(request)
        
        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"
        
        # Determine rate limit for this endpoint
        limit, window = self._get_rate_limit(path, request.method)
        
        # Create unique key for this client + endpoint
        rate_key = f"{client_ip}:{path}"
        
        # Check current request count
        current_requests = rate_limit_store.get_requests(rate_key, window)
        
        if current_requests >= limit:
            # Rate limit exceeded
            logger.warning(
                f"Rate limit exceeded: {client_ip} on {path} "
                f"({current_requests}/{limit} requests in {window}s)"
            )
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {limit} requests per {self._format_window(window)}",
                    "retry_after": window,
                },
                headers={"Retry-After": str(window)}
            )
        
        # Add this request to the store
        rate_limit_store.add_request(rate_key, time.time())
        
        # Add rate limit headers to response
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(limit - current_requests - 1)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + window))
        
        return response
    
    def _get_rate_limit(self, path: str, method: str) -> Tuple[int, int]:
        """Get rate limit configuration for a specific path"""
        
        # Check for exact path match
        if path in self.RATE_LIMITS:
            return self.RATE_LIMITS[path]
        
        # Check for partial matches (e.g., /api/datasets/chunk/*)
        for pattern, (limit, window) in self.RATE_LIMITS.items():
            if pattern != "default" and path.startswith(pattern):
                return (limit, window)
        
        # Return default rate limit
        return self.RATE_LIMITS["default"]
    
    def _format_window(self, seconds: int) -> str:
        """Format time window in human-readable form"""
        if seconds >= 3600:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''}"
        elif seconds >= 60:
            minutes = seconds // 60
            return f"{minutes} minute{'s' if minutes > 1 else ''}"
        else:
            return f"{seconds} second{'s' if seconds > 1 else ''}"
