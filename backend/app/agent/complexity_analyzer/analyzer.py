"""
Complexity Analyzer
Scores task complexity from 1-10 using heuristics.

Rules:
1-2   = Simple Chat / Greeting
3-4   = Simple Question / Informational
5-6   = Single Task
7-8   = Multi-Step Task
9-10  = Large Project / Complex System
"""

import re
import logging
from dataclasses import dataclass
from app.agent.intent_classifier import IntentType

logger = logging.getLogger(__name__)


@dataclass
class ComplexityResult:
    complexity: int  # 1-10
    complexity_level: str  # "trivial" | "simple" | "moderate" | "complex" | "enterprise"
    reasoning: list[str]


# Scoring signals
HIGH_COMPLEXITY_SIGNALS = [
    # System-level
    (r"\b(full[\s-]?stack|end[\s-]to[\s-]end|production[\s-]ready)\b", 3),
    (r"\b(saas|platform|marketplace|e[\s-]commerce)\b", 3),
    (r"\b(microservice|distributed|scalable|architecture)\b", 3),
    (r"\b(authentication|authorization|auth|login|security)\b", 2),
    (r"\b(database|sql|postgresql|mysql|mongodb|redis)\b", 1),
    (r"\b(deploy|deployment|ci[\s-]?cd|docker|kubernetes|aws|gcp|azure)\b", 2),
    (r"\b(api|rest|graphql|websocket)\b", 1),
    (r"\b(payment|stripe|billing)\b", 2),
    # Multi-step indicators
    (r"\b(and\s+then|followed by|after\s+that|additionally|furthermore)\b", 1),
    (r"\b(multiple|several|various|many)\s+\b", 1),
    (r"\b(step|phase|stage|component|module|service)\b", 1),
    # Project indicators
    (r"\b(build|create|develop|implement|design)\b", 1),
    (r"\b(system|application|product|solution|tool)\b", 1),
    (r"\b(dashboard|admin panel|cms|crm|erp)\b", 2),
    # Complexity multipliers
    (r"\b(realtime|real[\s-]time|live|streaming)\b", 2),
    (r"\b(test|testing|unit test|integration test)\b", 1),
    (r"\b(documentation|docs|readme)\b", 1),
    (r"\b(mobile|ios|android|responsive)\b", 1),
    (r"\b(ai|machine learning|ml|nlp|llm|gpt|model)\b", 2),
]

LOW_COMPLEXITY_SIGNALS = [
    (r"^(hello|hi|hey|thanks|ok|bye|sure|yes|no)\b", -5),
    (r"^(what is|who is|when is|where is)\s+\w+\s*\??$", -3),
    (r"^(explain|define|describe)\s+\w+\s*\??$", -2),
    (r"^how\s+(do|does|is|are)\s+\w+.*\?$", -2),
    (r"^list\s+(top|best)?\s*\d+\s+\w+$", -1),
]

# Base scores by intent
INTENT_BASE_SCORES = {
    IntentType.CHAT: 1,
    IntentType.QUESTION: 3,
    IntentType.TASK: 5,
    IntentType.PROJECT: 7,
    IntentType.WORKFLOW: 7,
    IntentType.COMMAND: 4,
}

COMPLEXITY_LEVELS = {
    (1, 2): "trivial",
    (3, 4): "simple",
    (5, 6): "moderate",
    (7, 8): "complex",
    (9, 10): "enterprise",
}


def _get_complexity_level(score: int) -> str:
    for (low, high), level in COMPLEXITY_LEVELS.items():
        if low <= score <= high:
            return level
    return "moderate"


class ComplexityAnalyzer:
    """
    Heuristic-based complexity analyzer.
    Scores tasks from 1 (trivial) to 10 (enterprise).
    """

    def analyze(
        self, message: str, intent: IntentType, keywords: list[str] | None = None
    ) -> ComplexityResult:
        """Calculate complexity score for a message given its intent."""
        text = message.lower().strip()
        reasoning = []
        total_score = INTENT_BASE_SCORES.get(intent, 5)
        reasoning.append(f"Base score from intent '{intent.value}': {total_score}")

        # Word count factor
        word_count = len(text.split())
        if word_count > 100:
            total_score += 2
            reasoning.append(f"Long message ({word_count} words): +2")
        elif word_count > 50:
            total_score += 1
            reasoning.append(f"Medium-long message ({word_count} words): +1")
        elif word_count < 5:
            total_score -= 1
            reasoning.append(f"Very short message ({word_count} words): -1")

        # Apply high-complexity signals
        high_score_added = 0
        for pattern, score in HIGH_COMPLEXITY_SIGNALS:
            if re.search(pattern, text, re.IGNORECASE):
                high_score_added += score
                reasoning.append(f"High-complexity pattern '{pattern[:30]}...': +{score}")

        # Cap signal contribution to prevent runaway scoring
        total_score += min(high_score_added, 6)

        # Apply low-complexity signals
        for pattern, score in LOW_COMPLEXITY_SIGNALS:
            if re.search(pattern, text, re.IGNORECASE):
                total_score += score  # score is negative
                reasoning.append(f"Low-complexity signal: {score}")

        # Keyword density bonus
        if keywords and len(keywords) > 10:
            total_score += 1
            reasoning.append(f"High keyword density ({len(keywords)} keywords): +1")

        # Count explicit steps/requirements
        step_patterns = [
            r"\d+\.\s+\w+",  # numbered lists
            r"\n[-*]\s+\w+",  # bullet points
            r"\b(step \d+|requirement \d+|feature \d+)\b",
        ]
        step_count = sum(
            len(re.findall(p, text, re.IGNORECASE)) for p in step_patterns
        )
        if step_count > 5:
            total_score += 2
            reasoning.append(f"Multiple explicit steps ({step_count}): +2")
        elif step_count > 2:
            total_score += 1
            reasoning.append(f"Some explicit steps ({step_count}): +1")

        # Clamp to 1-10
        final_score = max(1, min(10, total_score))
        reasoning.append(f"Final clamped score: {final_score}")

        return ComplexityResult(
            complexity=final_score,
            complexity_level=_get_complexity_level(final_score),
            reasoning=reasoning,
        )
