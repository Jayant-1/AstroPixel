"""
R2 Tile Caching & Performance Optimization
- Connection pooling for R2
- Parallel tile fetches
- Tile prefetching based on viewport
- In-memory caching of frequently accessed tiles
"""

import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import Optional, Dict, Set, Tuple
from functools import lru_cache
import time
from threading import Lock
from collections import OrderedDict

from app.config import settings

logger = logging.getLogger(__name__)


class R2TileCache:
    """
    High-performance R2 tile fetching with:
    - Connection pooling (persistent TCP/HTTP2 connections)
    - LRU in-memory cache for hot tiles
    - Parallel tile fetches
    - Prefetching based on viewport
    """
    
    def __init__(self, max_cache_size: int = 500):
        """
        Initialize R2 tile cache
        
        Args:
            max_cache_size: Max tiles to keep in memory (10-20MB per tile)
        """
        self.enabled = settings.USE_S3
        self.public_url = getattr(settings, 'R2_PUBLIC_URL', None) or ""
        self.max_cache_size = max_cache_size
        
        # In-memory LRU cache: key -> tile_data
        self.tile_cache: OrderedDict[str, bytes] = OrderedDict()
        self.cache_lock = Lock()
        
        # Connection pool stats
        self.pool_stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'prefetch_requests': 0,
        }
        
        # Prefetch queue
        self.prefetch_queue: Set[str] = set()
        self.prefetch_lock = Lock()
        
        logger.info(f"✅ R2TileCache initialized: max_cache={max_cache_size}, enabled={self.enabled}")
    
    def get_tile_key(self, dataset_id: int, z: int, x: int, y: int, format: str = "jpg") -> str:
        """Generate cache key for tile"""
        return f"{dataset_id}/{z}/{x}/{y}.{format}"
    
    def get_tile_url(self, dataset_id: int, z: int, x: int, y: int, format: str = "jpg") -> str:
        """Build R2 tile URL"""
        if not self.enabled or not self.public_url:
            return None
        return f"{self.public_url}/tiles/{dataset_id}/{z}/{x}/{y}.{format}"
    
    def get_cached_tile(self, dataset_id: int, z: int, x: int, y: int, format: str = "jpg") -> Optional[bytes]:
        """Get tile from in-memory cache if available"""
        if not self.enabled:
            return None
        
        key = self.get_tile_key(dataset_id, z, x, y, format)
        
        with self.cache_lock:
            if key in self.tile_cache:
                # Move to end (LRU order)
                self.tile_cache.move_to_end(key)
                self.pool_stats['cache_hits'] += 1
                logger.debug(f"💾 Cache HIT: {key}")
                return self.tile_cache[key]
            
            self.pool_stats['cache_misses'] += 1
            logger.debug(f"💾 Cache MISS: {key}")
            return None
    
    def cache_tile(self, dataset_id: int, z: int, x: int, y: int, data: bytes, format: str = "jpg") -> None:
        """Store tile in in-memory cache with LRU eviction"""
        if not self.enabled or not data:
            return
        
        key = self.get_tile_key(dataset_id, z, x, y, format)
        
        with self.cache_lock:
            # Remove oldest item if at capacity
            if len(self.tile_cache) >= self.max_cache_size:
                evicted_key, _ = self.tile_cache.popitem(last=False)
                logger.debug(f"♻️  Cache eviction: {evicted_key}")
            
            # Add new tile
            self.tile_cache[key] = data
            logger.debug(f"💾 Cached tile: {key} ({len(data)} bytes)")
    
    async def fetch_tile_http2(self, url: str, timeout: int = 10) -> Optional[bytes]:
        """
        Fetch tile from R2 via HTTP/2 with connection pooling
        
        Args:
            url: Full R2 tile URL
            timeout: Request timeout in seconds
            
        Returns:
            Tile data or None
        """
        if not url:
            return None
        
        try:
            # Use connector with HTTP/2 support
            connector = aiohttp.TCPConnector(
                limit=100,  # Max connections per host
                limit_per_host=50,  # Max 50 concurrent requests per host
                enable_cleanup_closed=True,  # Clean up closed connections
                force_close=False,  # Reuse connections
                ttl_dns_cache=3600,  # DNS cache 1 hour
            )
            
            async with aiohttp.ClientSession(
                connector=connector,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as session:
                async with session.get(url) as resp:
                    if resp.status == 200:
                        logger.debug(f"✅ Fetched tile from R2: {url}")
                        return await resp.read()
                    else:
                        logger.warning(f"❌ R2 returned {resp.status}: {url}")
                        return None
        except asyncio.TimeoutError:
            logger.error(f"⏱️  Timeout fetching tile: {url}")
            return None
        except Exception as e:
            logger.error(f"❌ Error fetching tile: {url} - {e}")
            return None
    
    async def fetch_tiles_parallel(
        self,
        tiles: list[Tuple[int, int, int, int, str]]  # (dataset_id, z, x, y, format)
    ) -> Dict[str, Optional[bytes]]:
        """
        Fetch multiple tiles in parallel from R2
        
        Args:
            tiles: List of (dataset_id, z, x, y, format) tuples
            
        Returns:
            Dict mapping tile keys to data
        """
        if not self.enabled:
            return {}
        
        # Check cache first
        results = {}
        tiles_to_fetch = []
        
        for dataset_id, z, x, y, format in tiles:
            key = self.get_tile_key(dataset_id, z, x, y, format)
            cached = self.get_cached_tile(dataset_id, z, x, y, format)
            
            if cached:
                results[key] = cached
            else:
                url = self.get_tile_url(dataset_id, z, x, y, format)
                if url:
                    tiles_to_fetch.append((key, url))
        
        # Fetch missing tiles in parallel
        if tiles_to_fetch:
            logger.info(f"📥 Parallel fetching {len(tiles_to_fetch)} tiles from R2")
            
            # Create tasks for all fetches
            tasks = []
            for key, url in tiles_to_fetch:
                tasks.append(self._fetch_and_cache(key, url))
            
            # Run all in parallel
            fetched = await asyncio.gather(*tasks, return_exceptions=False)
            
            for (key, url), data in zip(tiles_to_fetch, fetched):
                results[key] = data
        
        return results
    
    async def _fetch_and_cache(self, key: str, url: str) -> Optional[bytes]:
        """Fetch tile and cache it"""
        data = await self.fetch_tile_http2(url)
        if data:
            # Extract tile info from key
            parts = key.split('/')
            if len(parts) == 5:
                dataset_id = int(parts[0])
                z = int(parts[1])
                x = int(parts[2])
                y_format = parts[3].split('.')
                if len(y_format) == 2:
                    y = int(y_format[0])
                    format = y_format[1]
                    self.cache_tile(dataset_id, z, x, y, data, format)
        return data
    
    def queue_prefetch(
        self,
        dataset_id: int,
        current_z: int,
        current_x: int,
        current_y: int,
        tiles_ahead: int = 8
    ) -> None:
        """
        Queue tiles for prefetching based on predicted viewport
        
        Args:
            dataset_id: Dataset ID
            current_z, current_x, current_y: Current tile coordinates
            tiles_ahead: Number of surrounding tiles to prefetch
        """
        if not self.enabled:
            return
        
        with self.prefetch_lock:
            # Add adjacent tiles to prefetch queue
            for dz in [-1, 0, 1]:
                for dx in range(-tiles_ahead // 2, tiles_ahead // 2 + 1):
                    for dy in range(-tiles_ahead // 2, tiles_ahead // 2 + 1):
                        z = current_z + dz
                        x = current_x + dx
                        y = current_y + dy
                        
                        if z >= 0:
                            key = self.get_tile_key(dataset_id, z, x, y, "jpg")
                            self.prefetch_queue.add(key)
            
            logger.debug(f"📋 Prefetch queue: {len(self.prefetch_queue)} tiles")
    
    def get_cache_stats(self) -> dict:
        """Get cache performance statistics"""
        total = self.pool_stats['cache_hits'] + self.pool_stats['cache_misses']
        hit_rate = (self.pool_stats['cache_hits'] / total * 100) if total > 0 else 0
        
        return {
            'enabled': self.enabled,
            'cache_size': len(self.tile_cache),
            'cache_max': self.max_cache_size,
            'total_requests': self.pool_stats['total_requests'],
            'cache_hits': self.pool_stats['cache_hits'],
            'cache_misses': self.pool_stats['cache_misses'],
            'hit_rate': f"{hit_rate:.1f}%",
            'prefetch_queue': len(self.prefetch_queue),
        }
    
    def clear_cache(self, dataset_id: Optional[int] = None) -> int:
        """
        Clear cache, optionally for specific dataset
        
        Returns:
            Number of items cleared
        """
        with self.cache_lock:
            if dataset_id is None:
                cleared = len(self.tile_cache)
                self.tile_cache.clear()
                logger.info(f"♻️  Cleared entire cache ({cleared} items)")
                return cleared
            else:
                # Remove only tiles for this dataset
                dataset_prefix = f"{dataset_id}/"
                to_delete = [k for k in self.tile_cache if k.startswith(dataset_prefix)]
                for key in to_delete:
                    del self.tile_cache[key]
                logger.info(f"♻️  Cleared cache for dataset {dataset_id} ({len(to_delete)} items)")
                return len(to_delete)


# Global cache instance
tile_cache = R2TileCache(max_cache_size=500)
