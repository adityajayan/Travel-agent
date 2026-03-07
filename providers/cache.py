"""Redis caching layer for provider search results (M8).

Gracefully degrades when Redis is unavailable — all operations become no-ops.
Cache keys are namespaced: concierge:{domain}:{provider}:{param_hash}
Default TTL: 15 minutes.
"""
import hashlib
import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ProviderCache:
    """Async Redis cache for provider search results."""

    def __init__(self, redis_url: Optional[str] = None, ttl_seconds: int = 900):
        self._ttl = ttl_seconds
        self._redis = None
        if redis_url:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(redis_url)
            except Exception as exc:
                logger.warning("Redis connection failed: %s — caching disabled", exc)

    @property
    def enabled(self) -> bool:
        return self._redis is not None

    def _cache_key(self, domain: str, provider: str, params: dict) -> str:
        """Generate a deterministic cache key from domain + provider + params."""
        serialized = json.dumps(params, sort_keys=True, default=str)
        param_hash = hashlib.sha256(serialized.encode()).hexdigest()[:12]
        return f"concierge:{domain}:{provider}:{param_hash}"

    async def get(self, domain: str, provider: str, params: dict) -> Optional[list[dict]]:
        """Retrieve cached search results. Returns None on miss or error."""
        if not self._redis:
            return None
        try:
            key = self._cache_key(domain, provider, params)
            data = await self._redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as exc:
            logger.debug("Cache get error: %s", exc)
            return None

    async def set(self, domain: str, provider: str, params: dict, results: list[dict]) -> None:
        """Store search results in cache with TTL."""
        if not self._redis:
            return
        try:
            key = self._cache_key(domain, provider, params)
            serialized = json.dumps(results, default=str)
            await self._redis.set(key, serialized, ex=self._ttl)
        except Exception as exc:
            logger.debug("Cache set error: %s", exc)

    async def invalidate(self, domain: str, provider: str, params: dict) -> None:
        """Remove a cached entry."""
        if not self._redis:
            return
        try:
            key = self._cache_key(domain, provider, params)
            await self._redis.delete(key)
        except Exception as exc:
            logger.debug("Cache invalidate error: %s", exc)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            try:
                await self._redis.close()
            except Exception:
                pass
