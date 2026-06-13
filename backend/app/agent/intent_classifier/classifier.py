"""
Intent Classifier
Classifies user message intent without any LLM calls (rule-based + keyword matching).
No planning, no execution — classification only.
"""

import re
import logging
from enum import Enum
from dataclasses import dataclass

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    CHAT = "CHAT"
    QUESTION = "QUESTION"
    TASK = "TASK"
    PROJECT = "PROJECT"
    WORKFLOW = "WORKFLOW"
    COMMAND = "COMMAND"


@dataclass
class IntentResult:
    intent: IntentType
    confidence: float
    matched_patterns: list[str]
    raw_input: str


# ─── Pattern definitions ──────────────────────────────────────────────────────

CHAT_PATTERNS = [
    r"^(hello|hi|hey|howdy|hola|greetings|sup|yo)\b",
    r"^good\s+(morning|afternoon|evening|night|day)\b",
    r"^how are you(\b|[?!.])",
    r"^what('s| is) up(\b|[?!.])",
    r"^(thanks|thank you|ty|thx|cheers)(\b|[!.])",
    r"^(bye|goodbye|see you|cya|later|ttyl)(\b|[!.])",
    r"^(ok|okay|sure|alright|got it|cool|nice|great|awesome|perfect)(\b|[!.])",
    r"^(lol|haha|hehe|lmao|rofl)(\b|[!.])",
    r"^(yes|no|yeah|nope|yep|nah)(\b|[!.])",
    r"^(sorry|excuse me|pardon|apologies)(\b|[!.])",
    r"^(please|pls)\s+help",
    r"^\w{1,15}[!.?]?$",  # very short messages (single word)
]

QUESTION_PATTERNS = [
    r"^(what|who|when|where|which|whose)\s+(is|are|was|were|does|do|did|has|have)\b",
    r"^(what|who|when|where|which|whose)\s+\w+\s+(is|are|was|were)\b",
    r"^(explain|describe|tell me about|define|what is|what are)\s+\b",
    r"^(how\s+does|how\s+do|how\s+is|how\s+are|how\s+was|how\s+were)\b",
    r"^(why\s+does|why\s+do|why\s+is|why\s+are|why\s+was|why\s+were)\b",
    r"^(can you explain|can you describe|could you explain|could you describe)\b",
    r"^(what's the difference between|compare .+ and .+)\b",
    r"\?$",  # ends with question mark
]

PROJECT_PATTERNS = [
    r"\b(build|create|develop|make|design|architect|implement)\s+(a|an|the)?\s*(full[\s-]?stack|web\s*app|saas|platform|system|application|website|api|microservice|backend|frontend)\b",
    r"\b(build|create|develop|make|design|architect|implement)\s+(a|an|the)?\s*(portfolio|dashboard|e[\s-]?commerce|marketplace|blog|cms|crm|erp|app)\b",
    r"\b(launch|start|kickoff|bootstrap)\s+(a|an|the)?\s*(project|startup|product|service|app)\b",
    r"\b(full\s*project|complete\s*system|entire\s*application|production[\s-]?ready)\b",
    r"\b(build|create|develop|make)\s+(a|an|the)?\s*(complete|full|entire)\s+\w+\s*(application|system|platform|app|website|tool)\b",
    r"\b(build|create|develop)\s+(a|an|the)?\s*(complete|full|entire)\s+\w+\b",
]

WORKFLOW_PATTERNS = [
    r"\b(and\s+then|then|after\s+that|next|subsequently|followed by)\b.{10,}",
    r"\b(research|analyze|study|investigate)\s+.{5,}\s+(and|then)\s+(create|generate|write|make|produce|send|email)\b",
    r"\b(collect|gather|scrape|fetch)\s+.{5,}\s+(and|then)\s+(process|analyze|store|save|export)\b",
    r"\bmulti[\s-]?(step|phase|stage)\b",
    r"\b(automate|automation)\s+(the|a|an)?\s*\w+\s+(process|workflow|pipeline)\b",
    r"\bworkflow\b",
    r"\bpipeline\b",
    r"\bend[\s-]to[\s-]end\b",
]

TASK_PATTERNS = [
    r"\b(find|search|look up|locate|discover)\s+\b",
    r"\b(compare|contrast|evaluate|assess|review)\s+\b",
    r"\b(summarize|summarise|create a summary)\s+\b",
    r"\b(list|enumerate|show me)\s+\b",
    r"\b(translate|convert|transform)\s+\b",
    r"\b(write|draft|compose)\s+(a|an|the)?\s*(email|letter|message|document|report|essay|article|blog post)\b",
    r"\b(calculate|compute|solve|figure out)\s+\b",
    r"\b(analyze|analyse)\s+\b",
    r"\b(generate|produce|create)\s+(a|an|the)?\s*(list|report|summary|document|file)\b",
    r"\b(fix|debug|resolve|troubleshoot)\s+\b",
    r"\b(help me with|assist me with|do this for me)\b",
]

COMMAND_PATTERNS = [
    r"^(run|execute|start|stop|restart|kill|deploy|install|uninstall)\s+\b",
    r"^(git\s+\w+|npm\s+\w+|pip\s+\w+|docker\s+\w+|kubectl\s+\w+)\b",
    r"^\$\s+",
    r"^>+\s+",
]


def _normalize(text: str) -> str:
    """Normalize text for pattern matching."""
    return text.lower().strip()


def _match_patterns(text: str, patterns: list[str]) -> list[str]:
    """Return list of patterns that matched."""
    matched = []
    for pattern in patterns:
        if re.search(pattern, text, re.IGNORECASE):
            matched.append(pattern)
    return matched


class IntentClassifier:
    """
    Rule-based intent classifier.
    Classifies user input into structured intent types.
    No LLM calls. Fast and deterministic.
    """

    def classify(self, message: str) -> IntentResult:
        """Classify user message intent."""
        if not message or not message.strip():
            logger.warning("Empty message received for intent classification")
            return IntentResult(
                intent=IntentType.CHAT,
                confidence=0.5,
                matched_patterns=[],
                raw_input=message,
            )

        text = _normalize(message)
        logger.debug(f"Classifying intent for: {text[:100]}")

        # Order matters: most specific first
        # 1. COMMAND
        cmd_matches = _match_patterns(text, COMMAND_PATTERNS)
        if cmd_matches:
            return IntentResult(
                intent=IntentType.COMMAND,
                confidence=0.92,
                matched_patterns=cmd_matches,
                raw_input=message,
            )

        # 2. PROJECT (highest priority for complex tasks)
        proj_matches = _match_patterns(text, PROJECT_PATTERNS)
        if proj_matches:
            return IntentResult(
                intent=IntentType.PROJECT,
                confidence=0.88,
                matched_patterns=proj_matches,
                raw_input=message,
            )

        # 3. WORKFLOW (multi-step processes)
        wf_matches = _match_patterns(text, WORKFLOW_PATTERNS)
        if wf_matches:
            return IntentResult(
                intent=IntentType.WORKFLOW,
                confidence=0.85,
                matched_patterns=wf_matches,
                raw_input=message,
            )

        # 4. CHAT (short/social messages)
        chat_matches = _match_patterns(text, CHAT_PATTERNS)
        # Extra check: very short messages are chat
        word_count = len(text.split())
        if chat_matches and word_count <= 15:
            return IntentResult(
                intent=IntentType.CHAT,
                confidence=0.90,
                matched_patterns=chat_matches,
                raw_input=message,
            )

        # 5. QUESTION
        q_matches = _match_patterns(text, QUESTION_PATTERNS)
        if q_matches:
            return IntentResult(
                intent=IntentType.QUESTION,
                confidence=0.82,
                matched_patterns=q_matches,
                raw_input=message,
            )

        # 6. TASK
        task_matches = _match_patterns(text, TASK_PATTERNS)
        if task_matches:
            return IntentResult(
                intent=IntentType.TASK,
                confidence=0.78,
                matched_patterns=task_matches,
                raw_input=message,
            )

        # 7. Default: longer messages are tasks, short are chat
        if word_count <= 5:
            return IntentResult(
                intent=IntentType.CHAT,
                confidence=0.55,
                matched_patterns=["default_short_message"],
                raw_input=message,
            )
        elif word_count >= 20:
            return IntentResult(
                intent=IntentType.TASK,
                confidence=0.60,
                matched_patterns=["default_long_message"],
                raw_input=message,
            )
        else:
            return IntentResult(
                intent=IntentType.QUESTION,
                confidence=0.55,
                matched_patterns=["default_medium_message"],
                raw_input=message,
            )
