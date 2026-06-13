"""
System status endpoint - Live health checks for all services.
Phase 4: Production Hardening - Enhanced monitoring and metrics.
"""
import asyncio
import time
import os
from datetime import datetime
from fastapi import APIRouter, HTTPException, Request

from app.database.connection import check_db_health
from app.cache.redis_client import check_redis_health
from app.sandbox.e2b_client import check_e2b_health

router = APIRouter(prefix="/status", tags=["System Status"])

# Startup time
START_TIME = time.time()

# In-memory metrics
_metrics = {
    "total_requests": 0,
    "total_errors": 0,
    "response_times": [],
    "start_time": time.time()
}

# Try to import psutil for system metrics
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


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


# ===================== PHASE 4: PRODUCTION HARDENING =====================

@router.get("/")
async def status():
    """Combined status endpoint with health and metrics."""
    health = await services_status()
    metrics = await get_metrics()
    
    return {
        "health": health,
        "metrics": metrics,
        "version": "4.0.0",
        "phase": "production"
    }


@router.get("/metrics")
async def get_metrics():
    """Get system and API metrics."""
    uptime_seconds = time.time() - START_TIME
    
    response_times = _metrics.get("response_times", [])
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    uptime_minutes = uptime_seconds / 60
    requests_per_minute = _metrics["total_requests"] / uptime_minutes if uptime_minutes > 0 else 0
    
    system_info = {}
    if HAS_PSUTIL:
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            system_info = {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": memory.percent,
                "memory_used_mb": round(memory.used / (1024 * 1024), 2),
                "memory_available_mb": round(memory.available / (1024 * 1024), 2),
                "disk_percent": disk.percent,
            }
        except Exception:
            system_info = {"error": "Failed to get system info"}
    
    return {
        "system": system_info,
        "api": {
            "total_requests": _metrics["total_requests"],
            "total_errors": _metrics["total_errors"],
            "avg_response_time_ms": round(avg_response_time, 2),
            "requests_per_minute": round(requests_per_minute, 2)
        },
        "uptime_seconds": round(uptime_seconds, 2),
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
async def readiness_check():
    """Kubernetes readiness probe."""
    return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}


@router.get("/live")
async def liveness_check():
    """Kubernetes liveness probe."""
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}


# ===================== PHASE 4: AUTH ENDPOINTS =====================

@router.post("/auth/refresh")
async def refresh_token(request: Request):
    """Phase 4: Refresh access token using refresh token."""
    from app.core.security import decode_token
    import jwt
    
    try:
        body = await request.json()
        refresh_token_str = body.get("refresh_token")
        if not refresh_token_str:
            raise HTTPException(status_code=400, detail="refresh_token required")
        
        # Decode without verification to get payload
        payload = jwt.decode(refresh_token_str, options={"verify_signature": False})
        if payload.get("token_type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        # Create new tokens
        from app.core.security import create_access_token
        
        new_access_token = create_access_token({
            "sub": payload["sub"],
            "email": payload.get("email", ""),
            "username": payload.get("username", "")
        })
        
        return {
            "access_token": new_access_token,
            "refresh_token": refresh_token_str,  # Reuse refresh token
            "token_type": "bearer",
            "expires_in": 1800
        }
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid refresh token: {str(e)}")


@router.post("/auth/api-keys")
async def create_api_key(request: Request):
    """Phase 4: Create API key for user."""
    from app.core.security import decode_token
    
    try:
        body = await request.json()
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authorization required")
        
        token = auth_header.replace("Bearer ", "")
        payload = decode_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        # Create API key
        from app.auth.security import create_api_key as create_key
        
        key = create_key(
            user_id=user_id,
            name=body.get("name", "default"),
            expires_in_days=body.get("expires_in_days"),
            rate_limit=body.get("rate_limit", 100)
        )
        
        return key
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))


@router.get("/auth/api-keys")
async def list_api_keys(request: Request):
    """Phase 4: List user's API keys."""
    from app.core.security import decode_token
    from app.auth.security import api_keys
    
    try:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authorization required")
        
        token = auth_header.replace("Bearer ", "")
        payload = decode_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user_keys = [
            {
                "key_id": k["key_id"],
                "name": k["name"],
                "created_at": k["created_at"].isoformat(),
                "expires_at": k["expires_at"].isoformat() if k.get("expires_at") else None,
                "rate_limit": k["rate_limit"],
                "last_used": k.get("last_used").isoformat() if k.get("last_used") else None
            }
            for k in api_keys.values()
            if k["user_id"] == user_id
        ]
        
        return {"keys": user_keys, "total": len(user_keys)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
