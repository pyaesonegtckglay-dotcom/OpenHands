"""
Tests for IntentClassifier — Phase 1
"""

import pytest
from app.agent.intent_classifier import IntentClassifier, IntentType


@pytest.fixture
def classifier():
    return IntentClassifier()


class TestChatIntents:
    def test_hello(self, classifier):
        result = classifier.classify("Hello!")
        assert result.intent == IntentType.CHAT

    def test_hi(self, classifier):
        result = classifier.classify("Hi there")
        assert result.intent == IntentType.CHAT

    def test_good_morning(self, classifier):
        result = classifier.classify("Good morning")
        assert result.intent == IntentType.CHAT

    def test_how_are_you(self, classifier):
        result = classifier.classify("How are you?")
        assert result.intent == IntentType.CHAT

    def test_thank_you(self, classifier):
        result = classifier.classify("Thank you so much!")
        assert result.intent == IntentType.CHAT

    def test_bye(self, classifier):
        result = classifier.classify("Goodbye!")
        assert result.intent == IntentType.CHAT


class TestQuestionIntents:
    def test_what_is_python(self, classifier):
        result = classifier.classify("What is Python?")
        assert result.intent == IntentType.QUESTION

    def test_who_is(self, classifier):
        result = classifier.classify("Who is Elon Musk?")
        assert result.intent == IntentType.QUESTION

    def test_explain(self, classifier):
        result = classifier.classify("Explain how FastAPI works")
        assert result.intent == IntentType.QUESTION

    def test_what_are(self, classifier):
        result = classifier.classify("What are design patterns?")
        assert result.intent == IntentType.QUESTION


class TestTaskIntents:
    def test_find_vps(self, classifier):
        result = classifier.classify("Find 10 VPS providers")
        assert result.intent in (IntentType.TASK, IntentType.QUESTION)

    def test_compare(self, classifier):
        result = classifier.classify("Compare Tesla and BYD electric vehicles")
        assert result.intent in (IntentType.TASK, IntentType.QUESTION)

    def test_create_summary(self, classifier):
        result = classifier.classify("Create a summary of this document")
        assert result.intent == IntentType.TASK


class TestProjectIntents:
    def test_build_website(self, classifier):
        result = classifier.classify("Build a portfolio website")
        assert result.intent == IntentType.PROJECT

    def test_create_saas(self, classifier):
        result = classifier.classify("Create a SaaS application for task management")
        assert result.intent == IntentType.PROJECT

    def test_develop_app(self, classifier):
        result = classifier.classify("Develop a full-stack web application")
        assert result.intent == IntentType.PROJECT


class TestWorkflowIntents:
    def test_research_and_report(self, classifier):
        result = classifier.classify(
            "Research my competitors and create a PDF report"
        )
        assert result.intent in (IntentType.WORKFLOW, IntentType.TASK)

    def test_analyze_and_generate(self, classifier):
        result = classifier.classify(
            "Analyze stock prices and then generate a report"
        )
        assert result.intent in (IntentType.WORKFLOW, IntentType.TASK)


class TestEdgeCases:
    def test_empty_message(self, classifier):
        result = classifier.classify("")
        assert result.intent == IntentType.CHAT

    def test_whitespace_only(self, classifier):
        result = classifier.classify("   ")
        assert result.intent == IntentType.CHAT

    def test_has_confidence(self, classifier):
        result = classifier.classify("Build a website")
        assert 0.0 <= result.confidence <= 1.0

    def test_has_raw_input(self, classifier):
        msg = "Hello world"
        result = classifier.classify(msg)
        assert result.raw_input == msg
