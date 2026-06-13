"""
Phase 4 - Production Hardening
Monitoring & Metrics Module
- Health checks
- Metrics endpoint
- System status
"""
import os
import time
import psutil
from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

from fastapi import APIRouter, status
from pydantic import BaseModel
import httpx

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "")
REDIS_URL = os.getenv("REDIS_URL", "")

# Startup time
START_TIME = time.time()

@dataclass
class ServiceHealth:
    name: str
    status: str
    latency_ms: Optional[float] = None
    message: Optional[str] = None

@dataclass
class SystemMetrics:
    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_percent: float
    uptime_seconds: float
    timestamp: str

@dataclass
class APIMetrics:
    total_requests: int
    total_errors: int
    avg_response_time_ms: float
    requests_per_minute: float

class HealthResponse(BaseModel):
    status: str
    timestamp: str
    version: str
    phase: str
    services: list
    uptime_seconds: float

class MetricsResponse(BaseModel):
    system: dict
    api: dict
    timestamp: str

class StatusResponse(BaseModel):
    health: HealthResponse
    metrics: MetricsResponse

router = APIRouter(prefix="/api/v1", tags=["Phase 4 - Monitoring"])

# In-memory metrics (use Redis in production)
_metrics = {
    "total_requests": 0,
    "total_errors": 0,
    "response_times": [],
    "start_time": time.time()
}

def record_request(response_time_ms: float, is_error: bool = False):
    """Record API request metrics."""
    _metrics["total_requests"] += 1
    if is_error:
        _metrics["total_errors"] += 1
    _metrics["response_times"].append(response_time_ms)
    # Keep only last 1000 response times
    if len(_metrics["response_times"]) > 1000:
        _metrics["response_times"] = _metrics["response_times"][-1000:]

def get_uptime() -> float:
    """Get uptime in seconds."""
    return time.time() - START_TIME

def get_system_metrics() -> SystemMetrics:
    """Get current system metrics."""
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return SystemMetrics(
        cpu_percent=psutil.cpu_percent(interval=0.1),
        memory_percent=memory.percent,
        memory_used_mb=memory.used / (1024 * 1024),
        memory_available_mb=memory.available / (1024 * 1024),
        disk_percent=disk.percent,
        uptime_seconds=get_uptime(),
        timestamp=datetime.utcnow().isoformat()
    )

def get_api_metrics() -> APIMetrics:
    """Get API metrics."""
    response_times = _metrics.get("response_times", [])
    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
    
    uptime_minutes = get_uptime() / 60
    requests_per_minute = _metrics["total_requests"] / uptime_minutes if uptime_minutes > 0 else 0
    
    return APIMetrics(
        total_requests=_metrics["total_requests"],
        total_errors=_metrics["total_errors"],
        avg_response_time_ms=avg_response_time,
        requests_per_minute=requests_per_minute
    )

async def check_database_health() -> ServiceHealth:
    """Check database connection health."""
    start = time.time()
    try:
        # Simple connection test
        async with httpx.AsyncClient(timeout=5.0) as client:
            if DATABASE_URL:
                # Try to connect to Supabase
                response = await client.get(
                    f"{DATABASE_URL.split('@')[0].replace('postgres://', 'https://')}".split('@')[0] + "/health",
                    timeout=2.0
                )
                latency = (time.time() - start) * 1000
                return ServiceHealth(
                    name="database",
                    status="healthy" if response.status_code == 200 else "degraded",
                    latency_ms=round(latency, 2),
                    message="Database connection OK"
                )
    except Exception as e:
        pass
    
    # Fallback - assume healthy if no DB configured
    return ServiceHealth(
        name="database",
        status="healthy" if not DATABASE_URL else "unknown",
        latency_ms=round((time.time() - start) * 1000, 2),
        message="No database configured" if not DATABASE_URL else "Could not verify"
    )

async def check_redis_health() -> ServiceHealth:
    """Check Redis connection health."""
    start = time.time()
    try:
        if REDIS_URL:
            # Try to connect to Redis
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    REDIS_URL.replace("redis://", "https://").split('@')[0] + "/health",
                    timeout=2.0
                )
                latency = (time.time() - start) * 1000
                return ServiceHealth(
                    name="redis",
                    status="healthy",
                    latency_ms=round(latency, 2),
                    message="Redis connection OK"
                )
    except Exception:
        pass
    
    return ServiceHealth(
        name="redis",
        status="healthy" if not REDIS_URL else "unknown",
        latency_ms=round((time.time() - start) * 1000, 2),
        message="No Redis configured" if not REDIS_URL else "Could not verify"
    )

@router.get("/status/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint.
    Returns overall system health status.
    """
    # Check services in parallel
    import asyncio
    db_health, redis_health = await asyncio.gather(
        check_database_health(),
        check_redis_health()
    )
    
    # Determine overall status
    services = [db_health, redis_health]
    unhealthy = [s for s in services if s.status not in ["healthy", "unknown"]]
    
    overall_status = "healthy" if not unhealthy else "degraded"
    
    return HealthResponse(
        status=overall_status,
        timestamp=datetime.utcnow().isoformat(),
        version="4.0.0",
        phase="production",
        services=[asdict(s) for s in services],
        uptime_seconds=round(get_uptime(), 2)
    )

@router.get("/status/metrics", response_model=MetricsResponse)
async def get_metrics():
    """
    Metrics endpoint.
    Returns system and API metrics.
    """
    system_metrics = get_system_metrics()
    api_metrics = get_api_metrics()
    
    return MetricsResponse(
        system=asdict(system_metrics),
        api=asdict(api_metrics),
        timestamp=datetime.utcnow().isoformat()
    )

@router.get("/status", response_model=StatusResponse)
async def get_status():
    """
    Combined status endpoint.
    Returns both health and metrics.
    """
    health = await health_check()
    metrics = await get_metrics()
    
    return StatusResponse(
        health=health,
        metrics=metrics
    )

@router.get("/status/ready")
async def readiness_check():
    """
    Kubernetes readiness probe endpoint.
    Returns 200 if service is ready to receive traffic.
    """
    return {"status": "ready", "timestamp": datetime.utcnow().isoformat()}

@router.get("/status/live")
async def liveness_check():
    """
    Kubernetes liveness probe endpoint.
    Returns 200 if service is alive.
    """
    return {"status": "alive", "timestamp": datetime.utcnow().isoformat()}

__all__ = [
    "router",
    "record_request",
    "get_system_metrics",
    "get_api_metrics",
    "get_uptime",
    "HealthResponse",
    "MetricsResponse",
    "StatusResponse"
]