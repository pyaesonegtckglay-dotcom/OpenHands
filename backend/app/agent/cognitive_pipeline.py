"""
Cognitive Pipeline
Orchestrates the full cognitive decision-making process.

Pipeline:
1. IntentClassifier   → classify intent
2. GoalExtractor      → extract goal
3. ComplexityAnalyzer → score complexity
4. TaskClassifier     → fine-grained task type
5. PlannerTrigger     → decide if planning needed
6. PlanGenerator      → generate plan (if required)
7. PlanValidator      → validate plan
8. PlanStorage        → persist plan

This is PHASE 1 — COGNITIVE ONLY. No execution.
"""

import logging
from dataclasses import dataclass, asdict
from typing import Any

from app.agent.intent_classifier import IntentClassifier, IntentResult
from app.agent.goal_extractor import GoalExtractor, GoalResult
from app.agent.complexity_analyzer import ComplexityAnalyzer, ComplexityResult
from app.agent.task_classifier import TaskClassifier, TaskClassificationResult
from app.agent.planner_trigger import PlannerTrigger, PlannerDecision
from app.agent.planner import PlanGenerator, PlanObject
from app.agent.plan_validator import PlanValidator, ValidationResult
from app.agent.plan_storage import PlanStorage

logger = logging.getLogger(__name__)


@dataclass
class CognitiveAnalysisResult:
    """Result of cognitive analysis (no plan generation)."""
    intent: str
    intent_confidence: float
    goal: str
    domain: str
    desired_output: str
    complexity: int
    complexity_level: str
    task_type: str
    planning_required: bool
    plan_depth: str
    reason: str
    keywords: list[str]


@dataclass
class CognitivePipelineResult:
    """Full result including plan (if generated)."""
    analysis: CognitiveAnalysisResult
    plan: dict | None = None
    validation: dict | None = None
    plan_id: str | None = None
    provider_used: str | None = None
    model_used: str | None = None
    error: str | None = None


class CognitivePipeline:
    """
    Full cognitive pipeline.
    Phase 1: Determines intent, extracts goals, scores complexity,
    classifies task type, decides if planning is needed, generates
    and validates plans. Persists plans to database.
    """

    def __init__(self):
        self.intent_classifier = IntentClassifier()
        self.goal_extractor = GoalExtractor()
        self.complexity_analyzer = ComplexityAnalyzer()
        self.task_classifier = TaskClassifier()
        self.planner_trigger = PlannerTrigger()
        self.plan_generator = PlanGenerator()
        self.plan_validator = PlanValidator()
        self.plan_storage = PlanStorage()

    async def analyze(self, message: str) -> CognitiveAnalysisResult:
        """
        Run cognitive analysis pipeline (no plan generation).
        Returns intent, complexity, task type, and planning decision.
        """
        logger.info(f"Cognitive analysis started for: {message[:80]}...")

        # Step 1: Classify intent
        intent_result: IntentResult = self.intent_classifier.classify(message)
        logger.debug(f"Intent: {intent_result.intent.value} (confidence={intent_result.confidence})")

        # Step 2: Extract goal
        goal_result: GoalResult = self.goal_extractor.extract(message)
        logger.debug(f"Goal: {goal_result.goal[:60]}, domain: {goal_result.domain}")

        # Step 3: Analyze complexity
        complexity_result: ComplexityResult = self.complexity_analyzer.analyze(
            message, intent_result.intent, goal_result.keywords
        )
        logger.debug(f"Complexity: {complexity_result.complexity} ({complexity_result.complexity_level})")

        # Step 4: Classify task type
        task_result: TaskClassificationResult = self.task_classifier.classify(
            message, intent_result.intent
        )
        logger.debug(f"Task type: {task_result.task_type.value}")

        # Step 5: Planner trigger decision
        planner_decision: PlannerDecision = self.planner_trigger.decide(
            intent_result.intent,
            task_result.task_type,
            complexity_result.complexity,
        )
        logger.debug(f"Planning required: {planner_decision.planning_required}, depth: {planner_decision.plan_depth.value}")

        return CognitiveAnalysisResult(
            intent=intent_result.intent.value,
            intent_confidence=intent_result.intent_confidence if hasattr(intent_result, 'intent_confidence') else intent_result.confidence,
            goal=goal_result.goal,
            domain=goal_result.domain,
            desired_output=goal_result.desired_output,
            complexity=complexity_result.complexity,
            complexity_level=complexity_result.complexity_level,
            task_type=task_result.task_type.value,
            planning_required=planner_decision.planning_required,
            plan_depth=planner_decision.plan_depth.value,
            reason=planner_decision.reason,
            keywords=goal_result.keywords,
        )

    async def run_full_pipeline(
        self,
        message: str,
        conn=None,
        user_id: str | None = None,
    ) -> CognitivePipelineResult:
        """
        Run the full cognitive pipeline including plan generation and storage.
        """
        try:
            # Step 1-5: Analysis
            analysis = await self.analyze(message)

            result = CognitivePipelineResult(analysis=analysis)

            # Step 6: Generate plan if needed
            if not analysis.planning_required:
                logger.info(f"No planning needed. Reason: {analysis.reason}")
                return result

            from app.agent.planner_trigger import PlanDepth
            depth = PlanDepth(analysis.plan_depth)
            min_s, max_s = self.planner_trigger.decide(
                self.intent_classifier.classify(message).intent,
                self.task_classifier.classify(message, self.intent_classifier.classify(message).intent).task_type,
                analysis.complexity,
            ).min_steps, self.planner_trigger.decide(
                self.intent_classifier.classify(message).intent,
                self.task_classifier.classify(message, self.intent_classifier.classify(message).intent).task_type,
                analysis.complexity,
            ).max_steps

            logger.info(f"Generating plan: depth={depth.value}, steps={min_s}-{max_s}")
            plan: PlanObject = await self.plan_generator.generate(
                goal=analysis.goal,
                depth=depth,
                min_steps=min_s,
                max_steps=max_s,
            )

            # Step 7: Validate plan
            validation: ValidationResult = self.plan_validator.validate(plan)
            logger.debug(f"Plan validation: valid={validation.is_valid}, errors={validation.errors}")

            # Step 8: Store plan
            if conn and validation.is_valid:
                try:
                    await self.plan_storage.save_plan(
                        conn=conn,
                        plan_id=plan.plan_id,
                        goal=analysis.goal,
                        intent=analysis.intent,
                        task_type=analysis.task_type,
                        complexity=analysis.complexity,
                        planning_required=analysis.planning_required,
                        plan_depth=analysis.plan_depth,
                        provider_used=plan.provider_used,
                        model_used=plan.model_used,
                        error_message=plan.error,
                        user_id=user_id,
                    )
                    if plan.steps:
                        await self.plan_storage.save_plan_steps(
                            conn=conn,
                            plan_id=plan.plan_id,
                            steps=[
                                {
                                    "id": s.id,
                                    "title": s.title,
                                    "description": s.description,
                                    "expected_output": s.expected_output,
                                    "dependencies": s.dependencies,
                                    "status": s.status,
                                }
                                for s in plan.steps
                            ],
                        )
                    logger.info(f"Plan {plan.plan_id} stored successfully")
                except Exception as e:
                    logger.error(f"Failed to store plan: {e}")

            result.plan = {
                "plan_id": plan.plan_id,
                "goal": plan.goal,
                "steps": [
                    {
                        "id": s.id,
                        "title": s.title,
                        "description": s.description,
                        "expected_output": s.expected_output,
                        "dependencies": s.dependencies,
                        "status": s.status,
                    }
                    for s in plan.steps
                ],
                "plan_depth": plan.plan_depth,
                "error": plan.error,
            }
            result.plan_id = plan.plan_id
            result.provider_used = plan.provider_used
            result.model_used = plan.model_used
            result.validation = {
                "is_valid": validation.is_valid,
                "errors": validation.errors,
                "warnings": validation.warnings,
                "step_count": validation.step_count,
            }

            return result

        except Exception as e:
            logger.exception(f"Cognitive pipeline error: {e}")
            return CognitivePipelineResult(
                analysis=CognitiveAnalysisResult(
                    intent="TASK",
                    intent_confidence=0.5,
                    goal=message[:200],
                    domain="general",
                    desired_output="general",
                    complexity=5,
                    complexity_level="moderate",
                    task_type="OTHER",
                    planning_required=False,
                    plan_depth="none",
                    reason="Pipeline error",
                    keywords=[],
                ),
                error=str(e),
            )
