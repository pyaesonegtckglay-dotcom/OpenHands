"""
Tests for GoalExtractor — Phase 1
"""

import pytest
from app.agent.goal_extractor import GoalExtractor, GoalResult


@pytest.fixture
def extractor():
    return GoalExtractor()


class TestGoalExtraction:
    def test_basic_goal(self, extractor):
        result = extractor.extract("Build a portfolio website")
        assert result.goal
        assert len(result.goal) > 0

    def test_removes_prefix(self, extractor):
        result = extractor.extract("Please build a portfolio website for me")
        assert "please" not in result.goal.lower()

    def test_domain_web_development(self, extractor):
        result = extractor.extract("Build a React web application with FastAPI backend")
        assert result.domain == "web_development"

    def test_domain_data_science(self, extractor):
        result = extractor.extract("Analyze this dataset and create visualizations with matplotlib")
        assert result.domain == "data_science"

    def test_domain_software_engineering(self, extractor):
        result = extractor.extract("Implement a sorting algorithm in Python")
        assert result.domain == "software_engineering"

    def test_domain_business(self, extractor):
        result = extractor.extract("Create a business plan for a startup")
        assert result.domain == "business"

    def test_desired_output_code(self, extractor):
        result = extractor.extract("Write a Python function to sort a list")
        assert result.desired_output == "code"

    def test_desired_output_report(self, extractor):
        result = extractor.extract("Generate a report on market trends")
        assert result.desired_output == "report"

    def test_keywords_extracted(self, extractor):
        result = extractor.extract("Build a portfolio website using React and FastAPI")
        assert len(result.keywords) > 0

    def test_empty_message(self, extractor):
        result = extractor.extract("")
        assert result.goal == "Unknown goal"
        assert result.domain == "general"

    def test_result_is_goal_result(self, extractor):
        result = extractor.extract("Build something")
        assert isinstance(result, GoalResult)

    def test_long_message_truncated(self, extractor):
        long_msg = "Build " + "a " * 200 + "website"
        result = extractor.extract(long_msg)
        assert len(result.goal) <= 210
