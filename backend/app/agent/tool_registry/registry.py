"""
Tool Registry — Phase 3
Dynamic tool registration system. No hardcoded tool calls.
Every tool must register itself via ToolRegistry.register().
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)


@dataclass
class ToolSchema:
    """Schema definition for a registered tool."""
    id: str
    name: str
    description: str
    input_schema: dict
    output_schema: dict
    enabled: bool = True
    handler: Optional[Any] = None  # async callable

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "enabled": self.enabled,
        }


class ToolRegistry:
    """
    Central tool registry.
    All tools self-register on import.
    """
    def __init__(self):
        self._tools: dict[str, ToolSchema] = {}
        logger.info("[ToolRegistry] Initialized")

    def register(self, schema: ToolSchema) -> None:
        """Register a tool."""
        self._tools[schema.id] = schema
        logger.info(f"[ToolRegistry] Registered tool: {schema.id} ({schema.name})")

    def get(self, tool_id: str) -> Optional[ToolSchema]:
        """Get a tool by ID."""
        return self._tools.get(tool_id)

    def list_tools(self) -> list[ToolSchema]:
        """List all registered tools."""
        return list(self._tools.values())

    def list_enabled(self) -> list[ToolSchema]:
        """List only enabled tools."""
        return [t for t in self._tools.values() if t.enabled]

    def enable(self, tool_id: str) -> None:
        if tool_id in self._tools:
            self._tools[tool_id].enabled = True

    def disable(self, tool_id: str) -> None:
        if tool_id in self._tools:
            self._tools[tool_id].enabled = False

    def to_dict(self) -> list[dict]:
        return [t.to_dict() for t in self._tools.values()]


# Singleton global registry
tool_registry = ToolRegistry()
