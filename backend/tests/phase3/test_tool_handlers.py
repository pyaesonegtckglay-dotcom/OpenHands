"""
Phase 3 Tests: Built-in Tool Handlers
Tests each tool handler directly (no network needed for most).
Calculator, File Reader/Writer, Python Executor are fully deterministic.
Web Search and HTTP Request tests use mocking.
"""
import asyncio
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ─── Calculator ──────────────────────────────────────────────────────────────

class TestCalculatorTool:
    """Test the calculator tool handler directly."""

    def setup_method(self):
        import app.agent.tool_registry.tools  # noqa: F401
        from app.agent.tool_registry import tool_registry
        self.handler = tool_registry.get("calculator").handler

    def test_basic_addition(self):
        result = asyncio.run(self.handler({"expression": "2 + 3"}))
        assert result["success"] is True
        assert result["result"] == 5

    def test_basic_multiplication(self):
        result = asyncio.run(self.handler({"expression": "7 * 8"}))
        assert result["success"] is True
        assert result["result"] == 56

    def test_square_root(self):
        result = asyncio.run(self.handler({"expression": "sqrt(144)"}))
        assert result["success"] is True
        assert abs(result["result"] - 12.0) < 0.001

    def test_pi_constant(self):
        result = asyncio.run(self.handler({"expression": "pi"}))
        assert result["success"] is True
        assert abs(result["result"] - 3.14159265) < 0.0001

    def test_complex_expression(self):
        result = asyncio.run(self.handler({"expression": "round(sqrt(2) * 100) / 100"}))
        assert result["success"] is True
        assert result["result"] == 1.41

    def test_division_by_zero(self):
        result = asyncio.run(self.handler({"expression": "1 / 0"}))
        # Division by zero should return an error (not success=True)
        assert "error" in result
        assert result.get("success") is not True

    def test_empty_expression(self):
        result = asyncio.run(self.handler({"expression": ""}))
        assert "error" in result

    def test_missing_expression(self):
        result = asyncio.run(self.handler({}))
        assert "error" in result

    def test_power_function(self):
        result = asyncio.run(self.handler({"expression": "pow(2, 10)"}))
        assert result["success"] is True
        assert result["result"] == 1024

    def test_min_max(self):
        result = asyncio.run(self.handler({"expression": "max(3, 7, 1, 9, 2)"}))
        assert result["success"] is True
        assert result["result"] == 9

    def test_result_type_in_output(self):
        result = asyncio.run(self.handler({"expression": "42"}))
        assert "result_type" in result
        assert result["expression"] == "42"


# ─── File Writer ─────────────────────────────────────────────────────────────

class TestFileWriterTool:
    """Test file writer tool handler."""

    def setup_method(self):
        import app.agent.tool_registry.tools  # noqa: F401
        from app.agent.tool_registry import tool_registry
        self.handler = tool_registry.get("file_writer").handler

    def teardown_method(self):
        """Clean up test files."""
        import shutil
        workspace = "/tmp/manusai_workspace"
        for f in ["test_write.txt", "test_append.txt", "test_csv.csv"]:
            path = os.path.join(workspace, f)
            if os.path.exists(path):
                os.remove(path)

    def test_write_file(self):
        result = asyncio.run(self.handler({
            "filename": "test_write.txt",
            "content": "Hello, World!",
        }))
        assert result["success"] is True
        assert result["filename"] == "test_write.txt"
        assert result["size_bytes"] > 0

    def test_write_creates_workspace(self):
        result = asyncio.run(self.handler({
            "filename": "test_write.txt",
            "content": "content",
        }))
        assert os.path.exists("/tmp/manusai_workspace/test_write.txt")

    def test_write_csv_content(self):
        csv_content = "name,age\nAlice,30\nBob,25\n"
        result = asyncio.run(self.handler({
            "filename": "test_csv.csv",
            "content": csv_content,
            "mode": "w",
        }))
        assert result["success"] is True
        assert result["lines_written"] >= 3

    def test_append_mode(self):
        asyncio.run(self.handler({
            "filename": "test_append.txt",
            "content": "Line 1\n",
            "mode": "w",
        }))
        result = asyncio.run(self.handler({
            "filename": "test_append.txt",
            "content": "Line 2\n",
            "mode": "a",
        }))
        assert result["success"] is True
        # File should now contain both lines
        with open("/tmp/manusai_workspace/test_append.txt") as f:
            content = f.read()
        assert "Line 1" in content
        assert "Line 2" in content

    def test_missing_filename(self):
        result = asyncio.run(self.handler({"content": "text"}))
        assert "error" in result

    def test_path_traversal_prevention(self):
        """Filename with ../.. should be sanitized to basename only."""
        result = asyncio.run(self.handler({
            "filename": "../../etc/passwd",
            "content": "test",
        }))
        # Should use basename "passwd" inside workspace, not escape
        assert result["success"] is True
        assert result["filename"] == "passwd"


# ─── File Reader ─────────────────────────────────────────────────────────────

class TestFileReaderTool:
    """Test file reader tool handler."""

    def setup_method(self):
        import app.agent.tool_registry.tools  # noqa: F401
        from app.agent.tool_registry import tool_registry
        self.writer = tool_registry.get("file_writer").handler
        self.handler = tool_registry.get("file_reader").handler

    def test_read_existing_file(self):
        asyncio.run(self.writer({
            "filename": "read_test.txt",
            "content": "Test content for reading",
        }))
        result = asyncio.run(self.handler({"filename": "read_test.txt"}))
        assert result["success"] is True
        assert "Test content for reading" in result["content"]
        assert result["size_bytes"] > 0
        assert result["lines"] >= 1

    def test_read_nonexistent_file(self):
        result = asyncio.run(self.handler({"filename": "does_not_exist_xyz.txt"}))
        assert "error" in result

    def test_read_empty_filename(self):
        result = asyncio.run(self.handler({"filename": ""}))
        assert "error" in result

    def test_read_missing_filename(self):
        result = asyncio.run(self.handler({}))
        assert "error" in result

    def test_read_large_content_truncated(self):
        """Content over 50KB should be truncated."""
        large = "x" * 60000
        asyncio.run(self.writer({"filename": "large_test.txt", "content": large}))
        result = asyncio.run(self.handler({"filename": "large_test.txt"}))
        assert result["success"] is True
        assert len(result["content"]) <= 50000


# ─── Python Executor ─────────────────────────────────────────────────────────

class TestPythonExecutorTool:
    """Test python executor tool handler."""

    def setup_method(self):
        import app.agent.tool_registry.tools  # noqa: F401
        from app.agent.tool_registry import tool_registry
        self.handler = tool_registry.get("python_executor").handler

    def test_simple_print(self):
        result = asyncio.run(self.handler({"code": "print('hello world')"}))
        assert result["success"] is True
        assert "hello world" in result["output"]

    def test_math_computation(self):
        result = asyncio.run(self.handler({"code": "result = 2 ** 10\nprint(result)"}))
        assert result["success"] is True
        assert "1024" in result["output"]

    def test_json_output(self):
        code = "import json\ndata = {'key': 'value'}\nprint(json.dumps(data))"
        result = asyncio.run(self.handler({"code": code}))
        assert result["success"] is True
        assert "key" in result["output"]

    def test_syntax_error_caught(self):
        result = asyncio.run(self.handler({"code": "def broken(:\n    pass"}))
        assert result["success"] is False
        assert result["error"] is not None

    def test_runtime_error_caught(self):
        result = asyncio.run(self.handler({"code": "raise ValueError('test error')"}))
        assert result["success"] is False
        assert result["error"] is not None

    def test_empty_code(self):
        result = asyncio.run(self.handler({"code": ""}))
        assert "error" in result

    def test_missing_code(self):
        result = asyncio.run(self.handler({}))
        assert "error" in result

    def test_workspace_available(self):
        code = "import os\nprint(os.path.exists(WORKSPACE))"
        result = asyncio.run(self.handler({"code": code}))
        assert result["success"] is True
        assert "True" in result["output"]

    def test_code_truncated_in_output(self):
        """Long code input should be truncated in response."""
        long_code = "x = 1\n" * 200
        result = asyncio.run(self.handler({"code": long_code}))
        # Code field in response should be truncated to 500 chars
        assert len(result.get("code", "")) <= 505  # 500 + "..."
