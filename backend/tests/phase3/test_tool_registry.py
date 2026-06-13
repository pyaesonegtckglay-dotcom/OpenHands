"""
Phase 3 Tests: Tool Registry
Tests tool registration, lookup, enable/disable, and schema validation.
"""
import pytest
from app.agent.tool_registry.registry import ToolRegistry, ToolSchema


def make_schema(id: str, name: str = None, enabled: bool = True) -> ToolSchema:
    async def handler(params: dict) -> dict:
        return {"result": params}

    return ToolSchema(
        id=id,
        name=name or f"Tool {id}",
        description=f"Description for {id}",
        input_schema={"type": "object", "properties": {"q": {"type": "string"}}},
        output_schema={"type": "object", "properties": {"result": {}}},
        enabled=enabled,
        handler=handler,
    )


class TestToolRegistry:
    def setup_method(self):
        self.registry = ToolRegistry()

    def test_register_tool(self):
        schema = make_schema("test_tool")
        self.registry.register(schema)
        assert self.registry.get("test_tool") is not None

    def test_get_registered_tool(self):
        schema = make_schema("my_tool")
        self.registry.register(schema)
        result = self.registry.get("my_tool")
        assert result is not None
        assert result.id == "my_tool"
        assert result.name == "Tool my_tool"

    def test_get_missing_tool_returns_none(self):
        result = self.registry.get("nonexistent")
        assert result is None

    def test_list_tools(self):
        self.registry.register(make_schema("tool_a"))
        self.registry.register(make_schema("tool_b"))
        tools = self.registry.list_tools()
        ids = [t.id for t in tools]
        assert "tool_a" in ids
        assert "tool_b" in ids

    def test_list_enabled_only(self):
        self.registry.register(make_schema("enabled_tool", enabled=True))
        self.registry.register(make_schema("disabled_tool", enabled=False))
        enabled = self.registry.list_enabled()
        ids = [t.id for t in enabled]
        assert "enabled_tool" in ids
        assert "disabled_tool" not in ids

    def test_enable_tool(self):
        self.registry.register(make_schema("my_disabled", enabled=False))
        self.registry.enable("my_disabled")
        assert self.registry.get("my_disabled").enabled is True

    def test_disable_tool(self):
        self.registry.register(make_schema("my_enabled", enabled=True))
        self.registry.disable("my_enabled")
        assert self.registry.get("my_enabled").enabled is False

    def test_enable_nonexistent_is_noop(self):
        """Should not raise an error for nonexistent tool."""
        self.registry.enable("does_not_exist")  # no exception

    def test_disable_nonexistent_is_noop(self):
        """Should not raise an error for nonexistent tool."""
        self.registry.disable("does_not_exist")  # no exception

    def test_register_overwrites_existing(self):
        self.registry.register(make_schema("dup", name="First"))
        self.registry.register(make_schema("dup", name="Second"))
        result = self.registry.get("dup")
        assert result.name == "Second"  # Last one wins

    def test_to_dict_output(self):
        self.registry.register(make_schema("dict_tool"))
        dicts = self.registry.to_dict()
        assert len(dicts) >= 1
        keys = set(dicts[0].keys())
        assert "id" in keys
        assert "name" in keys
        assert "description" in keys
        assert "input_schema" in keys
        assert "output_schema" in keys
        assert "enabled" in keys
        # handler should not be in to_dict output
        assert "handler" not in keys

    def test_tool_schema_to_dict(self):
        schema = make_schema("schema_test")
        d = schema.to_dict()
        assert d["id"] == "schema_test"
        assert d["enabled"] is True
        assert "handler" not in d

    def test_multiple_registrations_count(self):
        for i in range(5):
            self.registry.register(make_schema(f"bulk_{i}"))
        all_tools = self.registry.list_tools()
        assert len(all_tools) == 5


class TestBuiltinTools:
    """Test that the built-in tools register correctly."""

    def test_builtin_tools_register(self):
        """Import tools and verify they self-register in the singleton."""
        # The global singleton should have tools after import
        import app.agent.tool_registry.tools  # noqa: F401
        from app.agent.tool_registry import tool_registry

        enabled = tool_registry.list_enabled()
        ids = [t.id for t in enabled]

        assert "web_search" in ids
        assert "http_request" in ids
        assert "file_reader" in ids
        assert "file_writer" in ids
        assert "calculator" in ids
        assert "python_executor" in ids
        assert "ai_synthesis" in ids

    def test_all_tools_have_handlers(self):
        """Each built-in tool must have a callable handler."""
        import app.agent.tool_registry.tools  # noqa: F401
        from app.agent.tool_registry import tool_registry

        for tool in tool_registry.list_tools():
            assert tool.handler is not None, f"Tool {tool.id} has no handler"
            assert callable(tool.handler), f"Tool {tool.id} handler is not callable"
