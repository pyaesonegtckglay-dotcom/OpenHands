"""
Cognitive Layer API Endpoints — Phase 1
POST /api/v1/cognitive/analyze
POST /api/v1/planner/create
GET  /api/v1/planner/{plan_id}
GET  /api/v1/planner/list
"""

import logging
from asyncpg import Connection
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Any

from app.database.connection import get_db
from app.core.security import get_current_user, get_optional_user
from app.agent.cognitive_pipeline import CognitivePipeline
from app.agent.plan_storage import PlanStorage
from app.agent.intent_classifier import IntentClassifier
from app.agent.goal_extractor import GoalExtractor
from app.agent.complexity_analyzer import ComplexityAnalyzer
from app.agent.task_classifier import TaskClassifier
from app.agent.planner_trigger import PlannerTrigger, PlanDepth
from app.agent.planner import PlanGenerator

logger = logging.getLogger(__name__)

cognitive_router = APIRouter(prefix="/cognitive", tags=["Cognitive Layer"])
planner_router = APIRouter(prefix="/planner", tags=["Planner"])

# Singletons
_pipeline = CognitivePipeline()
_plan_storage = PlanStorage()


# ─── Request / Response Models ───────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000, description="User message to analyze")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        return v


class AnalyzeResponse(BaseModel):
    intent: str
    intent_confidence: float
    complexity: int
    complexity_level: str
    task_type: str
    planning_required: bool
    plan_depth: str
    goal: str
    domain: str
    desired_output: str
    reason: str
    keywords: List[str]


class CreatePlanRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=5000, description="Goal to plan for")
    depth: Optional[str] = Field(None, description="Plan depth: shallow, medium, deep")

    @field_validator("goal")
    @classmethod
    def validate_goal(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Goal cannot be empty")
        return v


class PlanStepResponse(BaseModel):
    id: str
    title: str
    description: str
    expected_output: str
    dependencies: List[str]
    status: str


class CreatePlanResponse(BaseModel):
    plan_id: str
    goal: str
    steps: List[PlanStepResponse]
    plan_depth: str
    provider_used: str
    model_used: str
    step_count: int
    is_valid: bool
    validation_errors: List[str]
    validation_warnings: List[str]


class PlanDetailResponse(BaseModel):
    plan_id: str
    goal: str
    intent: Optional[str]
    task_type: Optional[str]
    complexity: Optional[int]
    planning_required: Optional[bool]
    plan_depth: Optional[str]
    provider_used: Optional[str]
    model_used: Optional[str]
    created_at: Optional[str]
    steps: List[PlanStepResponse]


class PlanListItem(BaseModel):
    plan_id: str
    goal: str
    intent: Optional[str]
    task_type: Optional[str]
    complexity: Optional[int]
    planning_required: Optional[bool]
    plan_depth: Optional[str]
    provider_used: Optional[str]
    status: Optional[str]
    created_at: Optional[str]


class PlanListResponse(BaseModel):
    plans: List[PlanListItem]
    total: int


# ─── Cognitive Endpoints ─────────────────────────────────────────────────────

@cognitive_router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_message(
    data: AnalyzeRequest,
):
    """
    Analyze user message and return cognitive decision.
    No planning is generated — only classification and routing decisions.

    Input:  { "message": "Build a portfolio website" }
    Output: { "intent": "PROJECT", "complexity": 8, "task_type": "PROJECT", "planning_required": true, ... }
    """
    logger.info(f"Cognitive analyze: {data.message[:60]}...")

    try:
        analysis = await _pipeline.analyze(data.message)

        logger.info(
            f"Analysis result: intent={analysis.intent}, "
            f"complexity={analysis.complexity}, "
            f"planning_required={analysis.planning_required}"
        )

        return AnalyzeResponse(
            intent=analysis.intent,
            intent_confidence=analysis.intent_confidence,
            complexity=analysis.complexity,
            complexity_level=analysis.complexity_level,
            task_type=analysis.task_type,
            planning_required=analysis.planning_required,
            plan_depth=analysis.plan_depth,
            goal=analysis.goal,
            domain=analysis.domain,
            desired_output=analysis.desired_output,
            reason=analysis.reason,
            keywords=analysis.keywords,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Cognitive analysis error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Cognitive analysis failed",
        )


# ─── Planner Endpoints ────────────────────────────────────────────────────────

@planner_router.post("/create", response_model=CreatePlanResponse)
async def create_plan(
    data: CreatePlanRequest,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Generate a structured plan for a given goal.
    Uses AI providers (Gemini → GitHub Models → SambaNova) with fallback.
    Plan is stored in the database.

    Input:  { "goal": "Build a portfolio website" }
    Output: { "plan_id": "...", "steps": [...], ... }
    """
    logger.info(f"Creating plan for goal: {data.goal[:60]}...")

    # Determine depth from goal analysis if not provided
    depth = PlanDepth.MEDIUM
    min_steps = 5
    max_steps = 10

    if data.depth:
        try:
            depth = PlanDepth(data.depth.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid depth '{data.depth}'. Use: shallow, medium, deep",
            )
    else:
        # Auto-determine depth from goal analysis
        intent_cls = IntentClassifier()
        complexity_cls = ComplexityAnalyzer()
        task_cls = TaskClassifier()
        trigger = PlannerTrigger()

        intent_result = intent_cls.classify(data.goal)
        complexity_result = complexity_cls.analyze(data.goal, intent_result.intent)
        task_result = task_cls.classify(data.goal, intent_result.intent)
        decision = trigger.decide(intent_result.intent, task_result.task_type, complexity_result.complexity)
        depth = decision.plan_depth
        min_steps = decision.min_steps or 3
        max_steps = decision.max_steps or 10

    if depth == PlanDepth.NONE:
        depth = PlanDepth.MEDIUM
        min_steps = 5
        max_steps = 10

    try:
        generator = PlanGenerator()
        from app.agent.plan_validator import PlanValidator

        plan = await generator.generate(
            goal=data.goal,
            depth=depth,
            min_steps=min_steps,
            max_steps=max_steps,
        )

        validator = PlanValidator()
        validation = validator.validate(plan)

        # Store plan
        user_id = current_user.get("user_id")
        try:
            await _plan_storage.save_plan(
                conn=conn,
                plan_id=plan.plan_id,
                goal=plan.goal,
                intent="TASK",
                task_type="PROJECT",
                complexity=7,
                planning_required=True,
                plan_depth=depth.value,
                provider_used=plan.provider_used,
                model_used=plan.model_used,
                error_message=plan.error,
                user_id=user_id,
            )
            if plan.steps:
                await _plan_storage.save_plan_steps(
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
            logger.info(f"Plan {plan.plan_id} stored for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to store plan: {e}")

        return CreatePlanResponse(
            plan_id=plan.plan_id,
            goal=plan.goal,
            steps=[
                PlanStepResponse(
                    id=s.id,
                    title=s.title,
                    description=s.description,
                    expected_output=s.expected_output,
                    dependencies=s.dependencies,
                    status=s.status,
                )
                for s in plan.steps
            ],
            plan_depth=plan.plan_depth,
            provider_used=plan.provider_used or "unknown",
            model_used=plan.model_used or "unknown",
            step_count=len(plan.steps),
            is_valid=validation.is_valid,
            validation_errors=validation.errors,
            validation_warnings=validation.warnings,
        )
    except Exception as e:
        logger.exception(f"Plan creation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Plan creation failed: {str(e)}",
        )


@planner_router.get("/list", response_model=PlanListResponse)
async def list_plans(
    limit: int = 20,
    offset: int = 0,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List plans for the current user."""
    user_id = current_user.get("user_id")
    try:
        plans = await _plan_storage.list_plans(conn, user_id=user_id, limit=limit, offset=offset)
        return PlanListResponse(
            plans=[PlanListItem(**p) for p in plans],
            total=len(plans),
        )
    except Exception as e:
        logger.error(f"Failed to list plans: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plans",
        )


@planner_router.get("/{plan_id}", response_model=PlanDetailResponse)
async def get_plan(
    plan_id: str,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Get full plan details including all steps."""
    try:
        plan = await _plan_storage.get_plan(conn, plan_id)
        if not plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Plan '{plan_id}' not found",
            )
        return PlanDetailResponse(
            plan_id=plan["plan_id"],
            goal=plan["goal"],
            intent=plan.get("intent"),
            task_type=plan.get("task_type"),
            complexity=plan.get("complexity"),
            planning_required=plan.get("planning_required"),
            plan_depth=plan.get("plan_depth"),
            provider_used=plan.get("provider_used"),
            model_used=plan.get("model_used"),
            created_at=plan.get("created_at"),
            steps=[
                PlanStepResponse(**s) for s in plan.get("steps", [])
            ],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get plan {plan_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve plan",
        )
