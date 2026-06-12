"""
E2B Sandbox abstraction layer.
"""
import logging
from typing import Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


async def check_e2b_health() -> dict:
    """Check E2B API connectivity."""
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://api.e2b.dev/health",
                headers={"X-API-Key": settings.E2B_API_KEY},
            )
            if response.status_code in (200, 204, 401):
                # 401 means API key exists but unauthorized - still reachable
                return {"status": "connected", "service": "e2b_sandbox"}
            return {
                "status": "connected",
                "service": "e2b_sandbox",
                "http_status": response.status_code,
            }
    except Exception as e:
        logger.error(f"E2B health check failed: {e}")
        return {"status": "disconnected", "service": "e2b_sandbox", "error": str(e)}


class E2BSandboxManager:
    """Abstraction layer for E2B sandbox operations."""

    def __init__(self):
        self.api_key = settings.E2B_API_KEY
        self._sandboxes: Dict[str, Any] = {}

    async def create_sandbox(self, session_id: str) -> Optional[str]:
        """Create a new E2B sandbox for a session. Phase 1+ implementation."""
        logger.info(f"E2B sandbox creation requested for session: {session_id}")
        # Phase 1 will implement actual sandbox creation
        return None

    async def execute_code(self, sandbox_id: str, code: str) -> dict:
        """Execute code in a sandbox. Phase 1+ implementation."""
        logger.info(f"E2B code execution requested in sandbox: {sandbox_id}")
        return {"status": "not_implemented", "phase": "1+"}

    async def destroy_sandbox(self, sandbox_id: str) -> bool:
        """Destroy a sandbox. Phase 1+ implementation."""
        logger.info(f"E2B sandbox destruction requested: {sandbox_id}")
        return True


sandbox_manager = E2BSandboxManager()
