"""
Tool Router — Phase 3
Automatically routes tasks to appropriate tools.
Decision based on: Task Type, Expected Output, Required Capability, Confidence Score.
"""
import logging
import re
from dataclasses import dataclass

from app.agent.tool_registry import tool_registry

logger = logging.getLogger(__name__)


@dataclass
class ToolRouteDecision:
    """Result of tool routing decision."""
    tool_id: str
    tool_name: str
    confidence: float
    reason: str
    params: dict


ROUTING_RULES = [
    # (keywords, tool_id, confidence, param_extractor_hint)
    # Web Search patterns
    (
        r"\b(search|find|lookup|research|investigate|google|browse|web)\b",
        "web_search", 0.92,
        "query"
    ),
    (
        r"\b(tesla|company|company info|stock|market|news|article|website)\b",
        "web_search", 0.85,
        "query"
    ),
    # HTTP Request patterns
    (
        r"\b(fetch|request|api|endpoint|url|http|https|get|post|curl|download)\b",
        "http_request", 0.88,
        "url"
    ),
    # File Write patterns
    (
        r"\b(create|write|generate|make|save|export|produce)\b.*(csv|json|txt|file|report|document|spreadsheet)\b",
        "file_writer", 0.90,
        "filename"
    ),
    (
        r"\b(csv|json|txt|excel|spreadsheet)\b.*\b(create|write|generate|make|save)\b",
        "file_writer", 0.88,
        "filename"
    ),
    # File Read patterns
    (
        r"\b(read|open|load|parse|view)\b.*(file|csv|json|txt|document)\b",
        "file_reader", 0.88,
        "filename"
    ),
    # Calculator patterns
    (
        r"\b(calculate|compute|math|formula|equation|percentage|revenue|profit|roi|sum|average|mean|total)\b",
        "calculator", 0.90,
        "expression"
    ),
    (
        r"[\d\s\+\-\*\/\(\)\^]{5,}",  # Mathematical expressions
        "calculator", 0.85,
        "expression"
    ),
    # Python execution patterns
    (
        r"\b(python|code|script|execute|run|program|algorithm|sort|process|generate.*code)\b",
        "python_executor", 0.88,
        "code"
    ),
    # AI synthesis patterns
    (
        r"\b(analyze|synthesize|summarize|explain|describe|understand|interpret|assess|evaluate|report)\b",
        "ai_synthesis", 0.85,
        "prompt"
    ),
    (
        r"\b(compare|contrast|review|examine|investigate|study)\b",
        "ai_synthesis", 0.80,
        "prompt"
    ),
]

# Task title → tool mapping (high confidence direct maps)
TITLE_MAPS = {
    "search": "web_search",
    "research": "web_search",
    "find information": "web_search",
    "web search": "web_search",
    "browse": "web_search",
    "create csv": "file_writer",
    "generate csv": "file_writer",
    "write csv": "file_writer",
    "create file": "file_writer",
    "generate file": "file_writer",
    "calculate": "calculator",
    "compute": "calculator",
    "run code": "python_executor",
    "execute code": "python_executor",
    "write python": "python_executor",
    "analyze": "ai_synthesis",
    "synthesize": "ai_synthesis",
    "generate report": "ai_synthesis",
    "summarize": "ai_synthesis",
    "fetch url": "http_request",
    "http request": "http_request",
    "api call": "http_request",
}


class ToolRouter:
    """
    Automatically routes tasks to the right tool.
    Uses pattern matching + keyword scoring to determine the best tool.
    """

    def route(self, task_title: str, task_description: str = "", expected_output: str = "") -> ToolRouteDecision:
        """
        Route a task to the appropriate tool.

        Returns:
            ToolRouteDecision with tool_id, confidence, reason, and params
        """
        combined = f"{task_title} {task_description} {expected_output}".lower()

        # 1. Check title direct maps (highest priority)
        for phrase, tool_id in TITLE_MAPS.items():
            if phrase in combined:
                tool = tool_registry.get(tool_id)
                if tool and tool.enabled:
                    params = self._build_params(tool_id, task_title, task_description, expected_output)
                    return ToolRouteDecision(
                        tool_id=tool_id,
                        tool_name=tool.name,
                        confidence=0.95,
                        reason=f"Direct task type match: '{phrase}' → {tool.name}",
                        params=params,
                    )

        # 2. Pattern-based scoring
        scores: dict[str, float] = {}
        reasons: dict[str, str] = {}

        for pattern, tool_id, confidence, hint in ROUTING_RULES:
            tool = tool_registry.get(tool_id)
            if not tool or not tool.enabled:
                continue
            if re.search(pattern, combined, re.IGNORECASE):
                if tool_id not in scores or scores[tool_id] < confidence:
                    scores[tool_id] = confidence
                    reasons[tool_id] = f"Pattern match: {pattern[:40]}…"

        if scores:
            best_tool_id = max(scores, key=lambda k: scores[k])
            tool = tool_registry.get(best_tool_id)
            params = self._build_params(best_tool_id, task_title, task_description, expected_output)
            return ToolRouteDecision(
                tool_id=best_tool_id,
                tool_name=tool.name,
                confidence=scores[best_tool_id],
                reason=reasons[best_tool_id],
                params=params,
            )

        # 3. Default: AI synthesis for any reasoning/analysis task
        tool = tool_registry.get("ai_synthesis")
        if tool:
            return ToolRouteDecision(
                tool_id="ai_synthesis",
                tool_name=tool.name,
                confidence=0.70,
                reason="Default: AI synthesis for general tasks",
                params=self._build_params("ai_synthesis", task_title, task_description, expected_output),
            )

        # Last resort: web_search
        tool = tool_registry.get("web_search")
        return ToolRouteDecision(
            tool_id="web_search",
            tool_name=tool.name if tool else "web_search",
            confidence=0.50,
            reason="Last resort: general web search",
            params={"query": task_title},
        )

    def _build_params(self, tool_id: str, title: str, description: str, expected_output: str) -> dict:
        """Build tool-specific parameters from task info."""
        combined = f"{title}: {description}"
        if tool_id == "web_search":
            return {"query": title, "max_results": 5}

        elif tool_id == "http_request":
            # Extract URL from description if present
            urls = re.findall(r"https?://[^\s]+", description)
            return {"url": urls[0] if urls else f"https://www.google.com/search?q={title}", "method": "GET"}

        elif tool_id == "file_writer":
            # Determine filename from description
            fname_match = re.search(r"(\w+\.(csv|json|txt|md|html|py))", combined, re.IGNORECASE)
            filename = fname_match.group(1) if fname_match else "output.txt"
            return {"filename": filename, "content": f"# {title}\n\nGenerated by ManusAI\n"}

        elif tool_id == "file_reader":
            fname_match = re.search(r"(\w+\.(csv|json|txt|md|html|py))", combined, re.IGNORECASE)
            return {"filename": fname_match.group(1) if fname_match else "output.txt"}

        elif tool_id == "calculator":
            # Extract mathematical expression
            expr_match = re.search(r"[\d\s\+\-\*\/\(\)\^\.]{3,}", combined)
            return {"expression": expr_match.group(0).strip() if expr_match else "1 + 1"}

        elif tool_id == "python_executor":
            return {
                "code": f"# Task: {title}\n# Description: {description}\nprint('Executing: {title}')\nresult = '{title} completed'",
                "timeout": 30,
            }

        elif tool_id == "ai_synthesis":
            return {
                "prompt": combined,
                "task_type": "analyze",
                "context": expected_output or "",
            }

        return {"input": combined}
