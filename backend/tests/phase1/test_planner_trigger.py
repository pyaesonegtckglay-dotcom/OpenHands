"""
Tests for PlannerTrigger — Phase 1
"""

import pytest
from app.agent.planner_trigger import PlannerTrigger, PlanDepth
from app.agent.intent_classifier import IntentType
from app.agent.task_classifier import TaskType


@pytest.fixture
def trigger():
    return PlannerTrigger()


class TestPlannerDecisions:
    def test_chat_no_planning(self, trigger):
        decision = trigger.decide(IntentType.CHAT, TaskType.CHAT, complexity=2)
        assert decision.planning_required is False

    def test_question_no_planning(self, trigger):
        decision = trigger.decide(IntentType.QUESTION, TaskType.KNOWLEDGE, complexity=3)
        assert decision.planning_required is False

    def test_project_always_plans(self, trigger):
        decision = trigger.decide(IntentType.PROJECT, TaskType.PROJECT, complexity=8)
        assert decision.planning_required is True

    def test_workflow_always_plans(self, trigger):
        decision = trigger.decide(IntentType.WORKFLOW, TaskType.WORKFLOW, complexity=7)
        assert decision.planning_required is True

    def test_task_conditional_low_complexity(self, trigger):
        decision = trigger.decide(IntentType.TASK, TaskType.RESEARCH, complexity=3)
        assert decision.planning_required is False

    def test_task_conditional_high_complexity(self, trigger):
        decision = trigger.decide(IntentType.TASK, TaskType.RESEARCH, complexity=7)
        assert decision.planning_required is True


class TestPlanDepths:
    def test_low_complexity_shallow_or_none(self, trigger):
        decision = trigger.decide(IntentType.PROJECT, TaskType.PROJECT, complexity=3)
        assert decision.plan_depth in (PlanDepth.NONE, PlanDepth.SHALLOW)

    def test_medium_complexity_medium_depth(self, trigger):
        decision = trigger.decide(IntentType.PROJECT, TaskType.PROJECT, complexity=6)
        assert decision.plan_depth == PlanDepth.MEDIUM

    def test_high_complexity_deep(self, trigger):
        decision = trigger.decide(IntentType.PROJECT, TaskType.PROJECT, complexity=9)
        assert decision.plan_depth == PlanDepth.DEEP

    def test_step_ranges_shallow(self, trigger):
        decision = trigger.decide(IntentType.PROJECT, TaskType.PROJECT, complexity=4)
        if decision.planning_required and decision.plan_depth == PlanDepth.SHALLOW:
            assert 3 <= decision.min_steps <= decision.max_steps <= 5

    def test_step_ranges_deep(self, trigger):
        decision = trigger.decide(IntentType.PROJECT, TaskType.PROJECT, complexity=10)
        if decision.planning_required and decision.plan_depth == PlanDepth.DEEP:
            assert decision.min_steps >= 10
            assert decision.max_steps <= 30

    def test_no_planning_zero_steps(self, trigger):
        decision = trigger.decide(IntentType.CHAT, TaskType.CHAT, complexity=1)
        assert decision.min_steps == 0
        assert decision.max_steps == 0

    def test_has_reason(self, trigger):
        decision = trigger.decide(IntentType.PROJECT, TaskType.PROJECT, complexity=8)
        assert decision.reason
        assert len(decision.reason) > 0
