"""
Tests for TaskClassifier — Phase 1
"""

import pytest
from app.agent.task_classifier import TaskClassifier, TaskType
from app.agent.intent_classifier import IntentType


@pytest.fixture
def classifier():
    return TaskClassifier()


class TestTaskTypeClassification:
    def test_chat_intent_gives_chat_type(self, classifier):
        result = classifier.classify("Hello", IntentType.CHAT)
        assert result.task_type == TaskType.CHAT

    def test_coding_task(self, classifier):
        result = classifier.classify(
            "Write a Python function to sort a list of integers",
            IntentType.TASK
        )
        assert result.task_type == TaskType.CODING

    def test_research_task(self, classifier):
        result = classifier.classify(
            "Find top 10 VPS providers and compare prices",
            IntentType.TASK
        )
        assert result.task_type == TaskType.RESEARCH

    def test_analysis_task(self, classifier):
        result = classifier.classify(
            "Analyze the pros and cons of React versus Vue",
            IntentType.TASK
        )
        assert result.task_type == TaskType.ANALYSIS

    def test_writing_task(self, classifier):
        result = classifier.classify(
            "Write a blog post about machine learning trends",
            IntentType.TASK
        )
        assert result.task_type in (TaskType.WRITING, TaskType.ANALYSIS)

    def test_project_task(self, classifier):
        result = classifier.classify(
            "Build a full-stack SaaS application",
            IntentType.PROJECT
        )
        assert result.task_type == TaskType.PROJECT

    def test_workflow_task(self, classifier):
        result = classifier.classify(
            "Automate the data collection pipeline and then analyze results",
            IntentType.WORKFLOW
        )
        assert result.task_type in (TaskType.WORKFLOW, TaskType.ANALYSIS, TaskType.RESEARCH)

    def test_knowledge_question(self, classifier):
        result = classifier.classify(
            "What is machine learning?",
            IntentType.QUESTION
        )
        assert result.task_type == TaskType.KNOWLEDGE

    def test_has_confidence(self, classifier):
        result = classifier.classify("Build a website", IntentType.PROJECT)
        assert 0.0 <= result.confidence <= 1.0

    def test_command_gives_coding(self, classifier):
        result = classifier.classify(
            "run the deployment script",
            IntentType.COMMAND
        )
        assert result.task_type in (TaskType.CODING, TaskType.OTHER)
