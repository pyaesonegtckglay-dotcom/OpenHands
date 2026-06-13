"""
Goal Extractor
Extracts: goal, domain, desired_output from user message.
Uses keyword analysis and structural extraction.
"""

import re
import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class GoalResult:
    goal: str
    domain: str
    desired_output: str
    keywords: list[str] = field(default_factory=list)


# Domain keyword mapping
DOMAIN_KEYWORDS = {
    "web_development": [
        "website", "web app", "frontend", "backend", "html", "css", "javascript",
        "react", "vue", "angular", "next.js", "fastapi", "django", "flask",
        "rest api", "graphql", "spa", "pwa"
    ],
    "data_science": [
        "data", "dataset", "analysis", "analytics", "visualization", "chart",
        "graph", "statistics", "csv", "excel", "pandas", "numpy", "matplotlib",
        "machine learning", "ml", "ai", "model", "prediction", "forecast",
        "regression", "classification", "clustering"
    ],
    "software_engineering": [
        "code", "programming", "function", "class", "module", "library",
        "algorithm", "debug", "refactor", "test", "unit test", "api",
        "microservice", "architecture", "design pattern", "database", "sql",
        "docker", "kubernetes", "ci/cd", "deployment"
    ],
    "business": [
        "business", "startup", "saas", "product", "market", "customer",
        "revenue", "sales", "marketing", "strategy", "plan", "report",
        "analysis", "competitor", "industry", "finance", "budget", "roi",
        "kpi", "growth", "user", "client"
    ],
    "research": [
        "research", "study", "investigate", "find", "search", "discover",
        "compare", "evaluate", "review", "analyze", "information", "facts",
        "source", "reference", "academic", "paper", "article", "topic"
    ],
    "writing": [
        "write", "draft", "compose", "create", "essay", "article", "blog",
        "post", "email", "letter", "report", "document", "content",
        "copy", "text", "summary", "description"
    ],
    "automation": [
        "automate", "script", "workflow", "pipeline", "schedule", "trigger",
        "process", "batch", "cron", "task", "job", "bot", "agent"
    ],
    "devops": [
        "deploy", "deployment", "server", "cloud", "aws", "gcp", "azure",
        "docker", "kubernetes", "infrastructure", "ci/cd", "github actions",
        "pipeline", "monitoring", "logging"
    ],
    "general": []
}

# Output type detection patterns
OUTPUT_PATTERNS = {
    "code": [
        r"\b(code|script|function|class|module|program|app|application)\b",
        r"\b(implement|build|create|write)\s+(a|an)?\s*(function|class|module|script)\b",
    ],
    "report": [
        r"\b(report|analysis|summary|document|presentation|pdf|doc)\b",
        r"\b(generate|produce|create)\s+(a|an)?\s*(report|analysis|summary)\b",
    ],
    "list": [
        r"\b(list|enumerate|catalog|inventory|collection)\b",
        r"\b(find|search|get)\s+\d+\s+(items|results|examples|options)\b",
    ],
    "plan": [
        r"\b(plan|roadmap|strategy|blueprint|architecture|design)\b",
        r"\b(how to|steps to|guide|tutorial)\b",
    ],
    "comparison": [
        r"\b(compare|contrast|vs|versus|difference between|similarities)\b",
        r"\b(better|worse|pros|cons|advantages|disadvantages)\b",
    ],
    "answer": [
        r"\?([\s]*)$",
        r"\b(what|who|when|where|how|why|explain|describe|tell me)\b",
    ],
    "website": [
        r"\b(website|web\s*app|frontend|ui|interface|page|landing\s*page)\b",
    ],
    "api": [
        r"\b(api|endpoint|rest|graphql|backend|service)\b",
    ],
    "general": []
}


def _detect_domain(text: str) -> str:
    """Detect the domain from the text."""
    text_lower = text.lower()
    domain_scores: dict[str, int] = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        if domain == "general":
            continue
        score = sum(1 for kw in keywords if kw in text_lower)
        if score > 0:
            domain_scores[domain] = score

    if not domain_scores:
        return "general"

    return max(domain_scores, key=lambda d: domain_scores[d])


def _detect_output(text: str) -> str:
    """Detect expected output type."""
    text_lower = text.lower()

    for output_type, patterns in OUTPUT_PATTERNS.items():
        if output_type == "general":
            continue
        for pattern in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return output_type

    return "general"


def _extract_goal(message: str) -> str:
    """Extract a clean goal statement from the message."""
    # Clean up the message
    goal = message.strip()

    # Remove common prefixes
    prefixes_to_remove = [
        r"^(can you|could you|please|i want you to|i need you to|help me to|help me)\s+",
        r"^(i want|i need|i would like|i'd like)\s+(to|you to)?\s*",
        r"^(your task is to|your job is to|you should|you must)\s+",
    ]
    for prefix in prefixes_to_remove:
        goal = re.sub(prefix, "", goal, flags=re.IGNORECASE).strip()

    # Truncate very long goals to 200 chars
    if len(goal) > 200:
        # Find a good break point
        truncated = goal[:200]
        last_space = truncated.rfind(" ")
        if last_space > 100:
            goal = truncated[:last_space] + "..."
        else:
            goal = truncated + "..."

    return goal if goal else message[:200]


def _extract_keywords(text: str) -> list[str]:
    """Extract key terms from the message."""
    # Remove common stop words
    stop_words = {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "shall", "can", "need", "dare", "ought",
        "used", "to", "and", "or", "but", "for", "of", "in", "on", "at",
        "by", "from", "with", "about", "against", "between", "into", "through",
        "during", "before", "after", "above", "below", "this", "that", "these",
        "those", "i", "me", "my", "myself", "we", "our", "you", "your",
        "he", "she", "it", "they", "them", "what", "which", "who", "when",
        "where", "why", "how", "all", "each", "every", "both", "few", "more",
        "most", "other", "some", "such", "no", "nor", "not", "only", "own",
        "same", "so", "than", "too", "very", "just", "please", "help",
    }

    words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_-]{2,}\b', text.lower())
    keywords = [w for w in words if w not in stop_words]

    # Deduplicate while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique_keywords.append(kw)

    return unique_keywords[:15]  # Return top 15 keywords


class GoalExtractor:
    """
    Extracts structured goal information from user message.
    No LLM calls. Keyword and pattern-based extraction.
    """

    def extract(self, message: str) -> GoalResult:
        """Extract goal, domain, and desired output from a message."""
        if not message or not message.strip():
            return GoalResult(
                goal="Unknown goal",
                domain="general",
                desired_output="general",
                keywords=[],
            )

        logger.debug(f"Extracting goal from: {message[:100]}")

        goal = _extract_goal(message)
        domain = _detect_domain(message)
        desired_output = _detect_output(message)
        keywords = _extract_keywords(message)

        result = GoalResult(
            goal=goal,
            domain=domain,
            desired_output=desired_output,
            keywords=keywords,
        )

        logger.debug(f"Extracted goal: {goal[:60]}, domain: {domain}, output: {desired_output}")
        return result
