"""
Redis (Upstash) cache client for ManusAI Phase 0.
Uses redis-py with TLS support for Upstash Redis.
"""
import logging
from typing import Optional
import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[aioredis.Redis] = None


def get_redis() -> aioredis.Redis:
    """Get or create the Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=10,
            socket_timeout=10,
        )
    return _redis_client


async def close_redis():
    """Close Redis connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


async def check_redis_health() -> dict:
    """Check Redis connectivity."""
    try:
        client = get_redis()
        await client.ping()
        return {"status": "connected", "service": "redis_upstash"}
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        return {"status": "disconnected", "service": "redis_upstash", "error": str(e)}
