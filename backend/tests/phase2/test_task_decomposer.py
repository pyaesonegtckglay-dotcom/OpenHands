"""
Phase 2 Tests: Task Decomposer
"""
import pytest
from app.agent.task_decomposer import TaskDecomposer, AtomicTask, TaskStatus, TaskComplexity
from app.agent.task_decomposer.decomposer import _parse_tasks, _generate_fallback_tasks


class TestAtomicTask:
    def test_task_has_all_required_fields(self):
        task = AtomicTask(
            id="task_1",
            title="Test Task",
            description="A test description",
            expected_output="Test output",
            estimated_complexity=TaskComplexity.MEDIUM,
            estimated_duration="10-20 minutes",
            parent_task=None,
            child_tasks=[],
            dependencies=[],
            status=TaskStatus.PLANNED,
            order=0,
            parallelizable=True,
            is_blocking=False,
        )
        assert task.id == "task_1"
        assert task.status == TaskStatus.PLANNED
        assert task.parallelizable is True
        assert task.is_blocking is False

    def test_task_to_dict(self):
        task = AtomicTask(
            id="task_1",
            title="Test",
            description="desc",
            expected_output="output",
            estimated_complexity=TaskComplexity.LOW,
            estimated_duration="5 min",
            parent_task=None,
            child_tasks=["task_2"],
            dependencies=[],
            order=0,
        )
        d = task.to_dict()
        assert d["id"] == "task_1"
        assert d["status"] == "PLANNED"
        assert d["child_tasks"] == ["task_2"]
        assert d["estimated_complexity"] == "low"

    def test_task_status_values(self):
        assert TaskStatus.PLANNED.value == "PLANNED"
        assert TaskStatus.READY.value == "READY"
        assert TaskStatus.BLOCKED.value == "BLOCKED"
        assert TaskStatus.COMPLETED.value == "COMPLETED"

    def test_task_complexity_values(self):
        assert TaskComplexity.LOW.value == "low"
        assert TaskComplexity.MEDIUM.value == "medium"
        assert TaskComplexity.HIGH.value == "high"


class TestParseTasks:
    def test_parse_valid_json(self):
        json_content = """
        {
          "tasks": [
            {
              "id": "task_1",
              "title": "Find Website",
              "description": "Find the official website",
              "expected_output": "Website URL",
              "estimated_complexity": "low",
              "estimated_duration": "5 minutes",
              "parent_task": null,
              "child_tasks": [],
              "dependencies": [],
              "order": 0,
              "parallelizable": true,
              "is_blocking": false
            },
            {
              "id": "task_2",
              "title": "Extract Info",
              "description": "Extract company information",
              "expected_output": "Company data",
              "estimated_complexity": "medium",
              "estimated_duration": "15 minutes",
              "parent_task": null,
              "child_tasks": [],
              "dependencies": ["task_1"],
              "order": 1,
              "parallelizable": false,
              "is_blocking": true
            }
          ]
        }
        """
        tasks = _parse_tasks(json_content, "Research Tesla")
        assert len(tasks) == 2
        assert tasks[0].id == "task_1"
        assert tasks[0].status == TaskStatus.PLANNED
        assert tasks[1].dependencies == ["task_1"]
        assert tasks[1].is_blocking is True

    def test_parse_markdown_wrapped_json(self):
        json_content = """```json
        {
          "tasks": [
            {
              "id": "task_1",
              "title": "Task 1",
              "description": "desc",
              "expected_output": "output",
              "estimated_complexity": "low",
              "estimated_duration": "5 min",
              "parent_task": null,
              "child_tasks": [],
              "dependencies": [],
              "order": 0,
              "parallelizable": true,
              "is_blocking": false
            }
          ]
        }
        ```"""
        tasks = _parse_tasks(json_content, "Test goal")
        assert len(tasks) == 1
        assert tasks[0].title == "Task 1"

    def test_parse_invalid_json_returns_empty(self):
        tasks = _parse_tasks("not valid json at all", "goal")
        assert tasks == []

    def test_parse_empty_content_returns_empty(self):
        tasks = _parse_tasks("", "goal")
        assert tasks == []


class TestFallbackTasks:
    def test_generates_tasks_for_each_step(self):
        steps = [
            {"id": "step_1", "title": "Step One", "description": "Do step one", "expected_output": "Output one"},
            {"id": "step_2", "title": "Step Two", "description": "Do step two", "expected_output": "Output two"},
        ]
        tasks = _generate_fallback_tasks("Test goal", steps)
        # 2 steps × 2 subtasks = 4 tasks
        assert len(tasks) == 4

    def test_all_tasks_have_planned_status(self):
        steps = [{"id": "s1", "title": "T1", "description": "D", "expected_output": "O"}]
        tasks = _generate_fallback_tasks("goal", steps)
        for task in tasks:
            assert task.status == TaskStatus.PLANNED

    def test_tasks_have_unique_ids(self):
        steps = [
            {"id": "s1", "title": "T1", "description": "D", "expected_output": "O"},
            {"id": "s2", "title": "T2", "description": "D", "expected_output": "O"},
        ]
        tasks = _generate_fallback_tasks("goal", steps)
        ids = [t.id for t in tasks]
        assert len(ids) == len(set(ids))

    def test_empty_steps_returns_empty(self):
        tasks = _generate_fallback_tasks("goal", [])
        assert tasks == []
