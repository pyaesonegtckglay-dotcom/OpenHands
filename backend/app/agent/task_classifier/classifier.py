"""
Task Classifier
Maps intent + message to fine-grained task types:
CHAT, KNOWLEDGE, RESEARCH, ANALYSIS, CODING, WRITING, PROJECT, WORKFLOW, OTHER
"""

import re
import logging
from enum import Enum
from dataclasses import dataclass
from app.agent.intent_classifier import IntentType

logger = logging.getLogger(__name__)


class TaskType(str, Enum):
    CHAT = "CHAT"
    KNOWLEDGE = "KNOWLEDGE"
    RESEARCH = "RESEARCH"
    ANALYSIS = "ANALYSIS"
    CODING = "CODING"
    WRITING = "WRITING"
    PROJECT = "PROJECT"
    WORKFLOW = "WORKFLOW"
    OTHER = "OTHER"


@dataclass
class TaskClassificationResult:
    task_type: TaskType
    confidence: float
    secondary_type: TaskType | None = None


# Task type keyword patterns
TASK_TYPE_PATTERNS = {
    TaskType.CODING: [
        r"\b(code|coding|program|programming|script|function|class|module)\b",
        r"\b(implement|build|develop|create)\s+(a|an)?\s*(function|class|api|endpoint|backend|app)\b",
        r"\b(debug|fix|refactor|optimize|test)\s+(the|this|my)?\s*(code|function|script|program)\b",
        r"\b(python|javascript|typescript|java|rust|go|c\+\+|react|vue|angular|node)\b",
        r"\b(algorithm|data structure|complexity|big[\s-]o)\b",
    ],
    TaskType.RESEARCH: [
        r"\b(research|investigate|explore|study|find out|look into)\b",
        r"\b(find|search|look up|discover)\s+\d+\s+(results|items|examples|providers|companies)\b",
        r"\b(top\s+\d+|best\s+\d+|leading|popular)\s+\b",
        r"\b(compare|vs|versus)\s+.{3,}\s+and\s+\b",
        r"\b(gather|collect|compile)\s+(information|data|facts|details)\b",
        r"\b(vps|hosting|provider|vendor|competitor|alternative)\b",
    ],
    TaskType.ANALYSIS: [
        r"\b(analyze|analyse|analysis|analytical)\b",
        r"\b(evaluate|assess|review|critique|examine)\b",
        r"\b(pros and cons|advantages|disadvantages|tradeoffs|trade-offs)\b",
        r"\b(compare|contrast|difference between|similarities)\b",
        r"\b(metrics|statistics|data|trends|patterns|insights)\b",
        r"\b(performance|benchmark|profiling)\b",
    ],
    TaskType.WRITING: [
        r"\b(write|draft|compose|create|generate)\s+(a|an|the)?\s*(email|letter|message|post|article|essay)\b",
        r"\b(blog\s*post|content|copy|description|documentation|readme|report)\b",
        r"\b(summarize|summarise|paraphrase|rewrite|edit|proofread)\b",
        r"\b(cover\s*letter|resume|cv|proposal|pitch)\b",
    ],
    TaskType.PROJECT: [
        r"\b(build|create|develop|implement|architect)\s+(a|an|the)?\s*(full[\s-]?stack|web\s*app|saas|platform|system)\b",
        r"\b(launch|start|bootstrap)\s+(a|an)?\s*(project|startup|product|service)\b",
        r"\b(complete|entire|full)\s+(application|system|product|solution)\b",
    ],
    TaskType.WORKFLOW: [
        r"\b(workflow|pipeline|automation|automate)\b",
        r"\b(and\s+then|then\s+|followed\s+by|next\s+step)\b.{10,}",
        r"\b(multi[\s-]step|multi[\s-]phase|sequential|iterative)\b",
        r"\b(schedule|trigger|cron|batch|recurring)\b",
    ],
    TaskType.KNOWLEDGE: [
        r"^(what|who|when|where|how|why|which)\s+(is|are|was|were|does|do|did)\b",
        r"\b(explain|describe|define|tell me about|what is|what are)\b",
        r"\b(meaning|definition|concept|theory|history|overview)\b",
        r"\?$",
    ],
    TaskType.CHAT: [
        r"^(hello|hi|hey|howdy|greetings|sup)\b",
        r"^(thanks|thank you|ty|bye|goodbye|see you)\b",
        r"^(how are you|what's up|good morning|good night)\b",
    ],
}

# Intent to task_type direct mappings (as fallback)
INTENT_TO_TASK_MAP = {
    IntentType.CHAT: TaskType.CHAT,
    IntentType.QUESTION: TaskType.KNOWLEDGE,
    IntentType.PROJECT: TaskType.PROJECT,
    IntentType.WORKFLOW: TaskType.WORKFLOW,
    IntentType.COMMAND: TaskType.CODING,
}


class TaskClassifier:
    """
    Fine-grained task type classifier.
    Combines intent + keyword analysis for classification.
    """

    def classify(
        self, message: str, intent: IntentType
    ) -> TaskClassificationResult:
        """Classify the task type."""
        text = message.lower().strip()
        logger.debug(f"Classifying task type for intent={intent.value}")

        # Direct CHAT mapping
        if intent == IntentType.CHAT:
            return TaskClassificationResult(
                task_type=TaskType.CHAT,
                confidence=0.95,
            )

        # Score each task type
        scores: dict[TaskType, int] = {}
        for task_type, patterns in TASK_TYPE_PATTERNS.items():
            score = 0
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    score += 1
            if score > 0:
                scores[task_type] = score

        if scores:
            # Get top two
            sorted_types = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            top_type = sorted_types[0][0]
            top_score = sorted_types[0][1]
            total = sum(scores.values())
            confidence = min(0.95, (top_score / total) * 1.2)

            secondary = None
            if len(sorted_types) > 1:
                secondary = sorted_types[1][0]

            return TaskClassificationResult(
                task_type=top_type,
                confidence=confidence,
                secondary_type=secondary,
            )

        # Fallback to intent mapping
        fallback = INTENT_TO_TASK_MAP.get(intent, TaskType.OTHER)
        return TaskClassificationResult(
            task_type=fallback,
            confidence=0.60,
        )
