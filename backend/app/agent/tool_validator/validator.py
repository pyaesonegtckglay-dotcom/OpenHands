"""
Tool Validator — Phase 3
Validates tool input parameters before execution.
"""
import logging
from app.agent.tool_registry import tool_registry

logger = logging.getLogger(__name__)


class ToolValidator:
    """Validates tool parameters against the tool's input schema."""

    def validate(self, tool_id: str, params: dict) -> tuple[bool, list[str]]:
        """
        Validate params for a given tool.
        Returns (is_valid, error_messages)
        """
        tool = tool_registry.get(tool_id)
        if not tool:
            return False, [f"Tool '{tool_id}' not found"]

        if not tool.enabled:
            return False, [f"Tool '{tool_id}' is disabled"]

        errors = []
        schema = tool.input_schema
        required = schema.get("required", [])
        properties = schema.get("properties", {})

        # Check required fields
        for field in required:
            if field not in params or params[field] is None or params[field] == "":
                errors.append(f"Required field '{field}' is missing or empty")

        # Basic type checking for provided fields
        for field, value in params.items():
            if field in properties:
                expected_type = properties[field].get("type")
                if expected_type and value is not None:
                    if expected_type == "string" and not isinstance(value, str):
                        errors.append(f"Field '{field}' should be a string")
                    elif expected_type == "integer" and not isinstance(value, int):
                        try:
                            params[field] = int(value)
                        except (ValueError, TypeError):
                            errors.append(f"Field '{field}' should be an integer")
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        errors.append(f"Field '{field}' should be a number")

        return len(errors) == 0, errors
