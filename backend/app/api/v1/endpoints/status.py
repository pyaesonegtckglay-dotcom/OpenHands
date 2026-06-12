"""
System status endpoint - Live health checks for all services.
"""
import asyncio
from fastapi import APIRouter

from app.database.connection import check_db_health
from app.cache.redis_client import check_redis_health
from app.sandbox.e2b_client import check_e2b_health

router = APIRouter(prefix="/status", tags=["System Status"])


@router.get("/health")
async def health_check():
    """Quick health check."""
    return {"status": "ok", "service": "ManusAI Backend", "phase": "0"}


@router.get("/services")
async def services_status():
    """Check live status of all infrastructure services."""
    results = await asyncio.gather(
        check_db_health(),
        check_redis_health(),
        check_e2b_health(),
        return_exceptions=True,
    )

    services = []
    for r in results:
        if isinstance(r, Exception):
            services.append({"status": "disconnected", "error": str(r)})
        else:
            services.append(r)

    all_connected = all(s.get("status") == "connected" for s in services)

    return {
        "overall": "healthy" if all_connected else "degraded",
        "services": {s["service"]: s for s in services},
    }
