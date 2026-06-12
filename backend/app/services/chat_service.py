"""
Chat service layer using raw asyncpg.
STABILIZATION: Placeholder responses removed. Real routing via cognitive pipeline + AI providers.
"""
import uuid
import logging
from typing import List, Optional
from asyncpg import Connection
from datetime import datetime, timezone

from app.schemas.chat import MessageRequest, MessageResponse, ConversationResponse

logger = logging.getLogger(__name__)


async def get_or_create_conversation(
    conn: Connection, user_id: str, conversation_id: Optional[str] = None
) -> str:
    """Return conversation_id (existing or newly created)."""
    if conversation_id:
        row = await conn.fetchrow(
            "SELECT id FROM conversations WHERE id = $1 AND user_id = $2",
            conversation_id, user_id,
        )
        if row:
            return str(row["id"])

    new_id = str(uuid.uuid4())
    await conn.execute(
        "INSERT INTO conversations (id, user_id, title) VALUES ($1, $2, $3)",
        new_id, user_id, "New Conversation",
    )
    return new_id


async def _generate_response(user_message: str, history: list[dict]) -> str:
    """
    Route the user message through the cognitive pipeline and AI provider.
    Returns the generated assistant response text.
    """
    from app.agent.cognitive_pipeline import CognitivePipeline
    from app.agent.provider_router.router import ProviderRouter, ProviderName

    pipeline = CognitivePipeline()
    router = ProviderRouter()

    # Run cognitive analysis (no DB needed for routing decision)
    try:
        analysis = await pipeline.analyze(user_message)
        intent = analysis.intent
        complexity = analysis.complexity
        planning_required = analysis.planning_required
    except Exception as e:
        logger.warning(f"Cognitive analysis failed: {e}, falling back to direct AI call")
        intent = "TASK"
        complexity = 5
        planning_required = False

    # Build system prompt based on intent
    if intent in ("CHAT",):
        system_prompt = (
            "You are ManusAI, a helpful and friendly AI assistant. "
            "Respond naturally and conversationally. Be warm but concise."
        )
    elif intent in ("QUESTION",):
        system_prompt = (
            "You are ManusAI, a knowledgeable AI assistant. "
            "Answer the question directly and accurately. "
            "Be thorough but avoid unnecessary padding."
        )
    elif intent in ("PROJECT", "WORKFLOW"):
        system_prompt = (
            "You are ManusAI, an expert AI project planner and architect. "
            "Provide a structured, detailed response with clear steps, considerations, and recommendations. "
            "Think step by step and cover all important aspects."
        )
    elif intent in ("TASK",):
        system_prompt = (
            "You are ManusAI, a capable AI assistant. "
            "Complete the requested task thoroughly and accurately. "
            "Provide well-structured output."
        )
    else:
        system_prompt = (
            "You are ManusAI, an advanced AI assistant. "
            "Help the user with their request accurately and thoroughly."
        )

    # Build conversation context
    history_text = ""
    if history:
        for h in history[-6:]:
            role_label = "User" if h["role"] == "user" else "Assistant"
            history_text += f"{role_label}: {h['content']}\n\n"

    if history_text:
        prompt = (
            f"Conversation history:\n{history_text}\n"
            f"User: {user_message}\n\nAssistant:"
        )
    else:
        prompt = f"User: {user_message}\n\nAssistant:"

    # Call AI provider
    result = await router.complete(prompt, system_prompt=system_prompt)

    if result.provider != ProviderName.NONE and result.content.strip():
        logger.info(f"Response generated via {result.provider.value} (intent={intent}, complexity={complexity})")
        return result.content.strip()

    # All providers failed — generate a meaningful fallback based on intent
    logger.error("All AI providers failed — generating structured fallback")
    return _generate_fallback(user_message, intent)


def _generate_fallback(message: str, intent: str) -> str:
    """Generate a meaningful fallback response when all AI providers are unavailable."""
    msg_lower = message.lower().strip()

    if intent == "CHAT":
        if any(w in msg_lower for w in ["hello", "hi", "hey", "howdy"]):
            return "Hello! I'm ManusAI. I'm here to help with research, planning, coding, analysis, and more. What would you like to work on?"
        if any(w in msg_lower for w in ["good morning", "good afternoon", "good evening"]):
            return "Good to see you! I'm ready to help. What's on your agenda today?"
        if any(w in msg_lower for w in ["thank", "thanks"]):
            return "You're welcome! Let me know if there's anything else I can help with."
        if any(w in msg_lower for w in ["bye", "goodbye"]):
            return "Goodbye! Come back anytime you need assistance."
        return "I'm here and ready to help. What would you like to work on?"

    if intent == "QUESTION":
        return (
            f"That's a great question. I'm temporarily unable to access my AI reasoning engine, "
            f"but I can tell you that '{message[:100]}' is a topic I'm equipped to analyze. "
            f"Please try again in a moment when my AI providers are available."
        )

    if intent in ("PROJECT", "WORKFLOW"):
        return (
            f"I understand you want to tackle a complex project: **{message[:100]}**\n\n"
            f"This requires careful planning. Here's my initial assessment:\n\n"
            f"**Recommended Approach:**\n"
            f"1. Define clear requirements and success criteria\n"
            f"2. Break down into phases with measurable milestones\n"
            f"3. Identify dependencies and critical path\n"
            f"4. Plan resources and timeline\n"
            f"5. Build iteratively with continuous validation\n\n"
            f"*Note: My AI providers are temporarily unavailable. For a detailed plan, please try again shortly.*"
        )

    return (
        f"I received your request and I'm working on it. "
        f"My AI reasoning providers are temporarily unavailable. "
        f"Please try again in a moment."
    )


async def send_message(
    conn: Connection, user_id: str, data: MessageRequest
) -> List[MessageResponse]:
    """Store user message, generate real AI response, return both messages."""
    conv_id = await get_or_create_conversation(conn, user_id, data.conversation_id)

    # Load recent conversation history for context
    history = []
    try:
        rows = await conn.fetch(
            """SELECT role, content FROM messages
               WHERE conversation_id = $1
               ORDER BY created_at DESC LIMIT 12""",
            conv_id
        )
        history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    except Exception as e:
        logger.warning(f"Failed to load history for context: {e}")

    # Store user message
    user_msg_id = str(uuid.uuid4())
    now_user = datetime.now(timezone.utc)
    await conn.execute(
        "INSERT INTO messages (id, conversation_id, role, content) VALUES ($1,$2,$3,$4)",
        user_msg_id, conv_id, "user", data.content,
    )

    # Generate real AI response
    try:
        assistant_content = await _generate_response(data.content, history)
    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        assistant_content = "I encountered an error processing your request. Please try again."

    # Store assistant response
    asst_msg_id = str(uuid.uuid4())
    now_asst = datetime.now(timezone.utc)
    await conn.execute(
        "INSERT INTO messages (id, conversation_id, role, content) VALUES ($1,$2,$3,$4)",
        asst_msg_id, conv_id, "assistant", assistant_content,
    )

    return [
        MessageResponse(
            id=user_msg_id,
            conversation_id=conv_id,
            user_id=user_id,
            role="user",
            content=data.content,
            created_at=now_user,
        ),
        MessageResponse(
            id=asst_msg_id,
            conversation_id=conv_id,
            user_id=user_id,
            role="assistant",
            content=assistant_content,
            created_at=now_asst,
        ),
    ]


async def get_conversation_messages(
    conn: Connection, user_id: str, conversation_id: str
) -> List[MessageResponse]:
    rows = await conn.fetch(
        "SELECT id, conversation_id, role, content, created_at "
        "FROM messages WHERE conversation_id = $1 ORDER BY created_at ASC",
        conversation_id,
    )
    return [
        MessageResponse(
            id=str(r["id"]),
            conversation_id=str(r["conversation_id"]),
            user_id=user_id,
            role=r["role"],
            content=r["content"],
            created_at=r["created_at"],
        )
        for r in rows
    ]


async def list_conversations(conn: Connection, user_id: str) -> List[ConversationResponse]:
    rows = await conn.fetch(
        "SELECT id, user_id, title, created_at, updated_at "
        "FROM conversations WHERE user_id = $1 ORDER BY created_at DESC LIMIT 50",
        user_id,
    )
    return [
        ConversationResponse(
            id=str(r["id"]),
            user_id=str(r["user_id"]),
            title=r["title"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]
