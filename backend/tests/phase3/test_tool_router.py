"""
Phase 3 Tests: Tool Router
Tests tool routing logic - which tool gets selected for which task type.
"""
import pytest
from app.agent.tool_router.router import ToolRouter


class TestToolRouter:
    def setup_method(self):
        # Ensure tools are registered
        import app.agent.tool_registry.tools  # noqa: F401
        self.router = ToolRouter()

    def test_research_task_routes_to_web_search(self):
        """Tasks about searching/researching should route to web_search."""
        route = self.router.route(
            task_title="Research Tesla electric vehicles",
            task_description="Search for information about Tesla",
            expected_output="Key findings about Tesla",
        )
        assert route.tool_id in ("web_search", "ai_synthesis")

    def test_calculation_task_routes_to_calculator(self):
        """Math/calculation tasks should route to calculator."""
        route = self.router.route(
            task_title="Calculate market cap",
            task_description="Calculate the market capitalization: 1000000 * 250",
            expected_output="Numeric result",
        )
        assert route.tool_id in ("calculator", "python_executor")

    def test_file_creation_task_routes_to_file_writer(self):
        """File creation tasks should route to file_writer."""
        route = self.router.route(
            task_title="Create CSV file of companies",
            task_description="Write a CSV file containing company data",
            expected_output="A CSV file",
        )
        assert route.tool_id in ("file_writer", "python_executor")

    def test_api_call_routes_to_http_request(self):
        """HTTP/API tasks should route to http_request."""
        route = self.router.route(
            task_title="Fetch data from API endpoint",
            task_description="Make HTTP GET request to retrieve data",
            expected_output="API response",
        )
        assert route.tool_id in ("http_request", "web_search")

    def test_analysis_routes_to_ai_synthesis(self):
        """Analysis and synthesis tasks should route to ai_synthesis."""
        route = self.router.route(
            task_title="Analyze and summarize findings",
            task_description="Synthesize all collected data into a summary report",
            expected_output="Comprehensive analysis report",
        )
        assert route.tool_id in ("ai_synthesis", "python_executor", "web_search")

    def test_python_code_task_routes_to_python_executor(self):
        """Python/code tasks should route to python_executor."""
        route = self.router.route(
            task_title="Execute Python script",
            task_description="Run Python code to process the data",
            expected_output="Script output",
        )
        assert route.tool_id in ("python_executor", "calculator")

    def test_route_returns_confidence(self):
        """Route should include a confidence score."""
        route = self.router.route(
            task_title="Search for news",
            task_description="Find latest news",
            expected_output="News articles",
        )
        assert hasattr(route, "confidence")
        assert 0.0 <= route.confidence <= 1.0

    def test_route_returns_params(self):
        """Route should include parameters for the tool."""
        route = self.router.route(
            task_title="Search Tesla news",
            task_description="Find articles about Tesla",
            expected_output="Articles",
        )
        assert hasattr(route, "params")
        assert isinstance(route.params, dict)

    def test_route_always_returns_valid_tool(self):
        """Every route result should reference a registered tool."""
        from app.agent.tool_registry import tool_registry
        import app.agent.tool_registry.tools  # noqa: F401

        valid_ids = {t.id for t in tool_registry.list_tools()}

        test_cases = [
            ("Generic task", "Do something useful", "A result"),
            ("", "", ""),
            ("XYZ task", "Unknown type task", "Some output"),
        ]

        for title, desc, expected in test_cases:
            route = self.router.route(title, desc, expected)
            assert route.tool_id in valid_ids


class TestToolRouterEdgeCases:
    def setup_method(self):
        import app.agent.tool_registry.tools  # noqa: F401
        self.router = ToolRouter()

    def test_empty_title_and_description(self):
        """Empty input should still return a valid route."""
        route = self.router.route("", "", "")
        assert route is not None
        assert route.tool_id

    def test_very_long_input(self):
        """Very long text should be handled without crashing."""
        long_text = "Research " * 200
        route = self.router.route(long_text, long_text, long_text)
        assert route is not None
        assert route.tool_id

    def test_special_characters(self):
        """Special characters should not crash the router."""
        route = self.router.route(
            "Task with !@#$%^&*() chars",
            "Description with <>&\"'",
            "Output",
        )
        assert route is not None

    def test_multiple_routing_calls_consistent(self):
        """Same input should consistently return same tool."""
        title = "Calculate fibonacci sequence"
        desc = "Use math to calculate fibonacci numbers"
        expected = "Numeric sequence"

        route1 = self.router.route(title, desc, expected)
        route2 = self.router.route(title, desc, expected)
        assert route1.tool_id == route2.tool_id
