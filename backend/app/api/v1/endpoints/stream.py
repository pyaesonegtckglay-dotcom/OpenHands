"""
Streaming Chat Endpoint — Phase 2 (Enhanced v2)
POST /api/v1/stream/chat

Provides token-by-token SSE streaming response from AI providers.
Provider chain: Gemini 2.0/1.5 Flash → GitHub Models (gpt-4o-mini) → SambaNova LLaMA 3.3

Features:
- Zero-buffer token forwarding (asyncio.sleep(0) between tokens)
- Keepalive pings every 15s to prevent Render/Vercel proxy timeouts
- Client disconnect detection — stops generation cleanly
- Tab-friendly JSON escaping that preserves all unicode
- Gemini 2.0 Flash primary for fastest Time-To-First-Token
- Full conversation history support (last 10 messages)
- Intent-aware system prompts
"""

import uuid
import json
import logging
import asyncio
import httpx
from typing import Optional, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from asyncpg import Connection

from app.database.connection import get_db
from app.core.security import get_current_user
from app.agent.provider_router.router import (
    GEMINI_API_KEYS,
    GITHUB_MODELS_TOKENS,
    SAMBANOVA_API_KEYS,
)
from app.services.chat_service import get_or_create_conversation

logger = logging.getLogger(__name__)

stream_router = APIRouter(prefix="/stream", tags=["Streaming"])

CHAT_SYSTEM_PROMPT = (
    "You are ManusAI, an advanced AI assistant. You help users with research, "
    "planning, coding, analysis, and any task they need. You are helpful, accurate, "
    "and thorough. When asked complex questions, you reason step by step.\n"
    "For conversational messages: respond naturally and warmly.\n"
    "For questions: give direct, accurate answers with clear structure.\n"
    "For tasks, projects, and workflows: provide structured, detailed responses with "
    "clear reasoning, numbered steps, and actionable output.\n"
    "Use markdown formatting: **bold** for emphasis, `code` for inline code, "
    "```language for code blocks, ## for headings, - for lists.\n"
    "Never expose backend internals. Focus entirely on helping the user."
)

INTENT_SYSTEM_PROMPTS = {
    "CHAT": (
        "You are ManusAI, a friendly and helpful AI assistant. "
        "Respond naturally and conversationally. Be warm but concise. "
        "Use markdown when it enhances clarity."
    ),
    "QUESTION": (
        "You are ManusAI, a knowledgeable AI assistant. "
        "Answer the question directly, accurately, and thoroughly. "
        "Use clear markdown structure when explaining complex topics. "
        "Include **bold** for key terms, numbered lists for steps, "
        "and code blocks for any code examples."
    ),
    "TASK": (
        "You are ManusAI, a capable AI assistant. "
        "Complete the requested task thoroughly and accurately. "
        "Provide well-structured, actionable output with markdown formatting."
    ),
    "PROJECT": (
        "You are ManusAI, an expert AI architect and project planner. "
        "Analyze the project goal deeply. Provide structured planning with:\n"
        "- ## Phase headings\n"
        "- **Bold** for key concepts\n"
        "- Code blocks for technical details\n"
        "- Numbered lists for sequential steps\n"
        "Think comprehensively and strategically."
    ),
    "WORKFLOW": (
        "You are ManusAI, an expert AI workflow designer. "
        "Break down the workflow into clear sequential steps with markdown. "
        "Identify dependencies, automation opportunities, and success criteria."
    ),
    "COMMAND": (
        "You are ManusAI, a technical AI assistant. "
        "Interpret and execute the command precisely. "
        "Provide results with proper code blocks and clear explanation."
    ),
}

# Gemini models to try in order (fastest TTFT first)
GEMINI_MODELS = [
    "gemini-2.0-flash",
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
]


class StreamChatRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    conversation_id: Optional[str] = None


def _make_token_event(text: str) -> str:
    """Encode a token as a JSON SSE event — safely escapes for JSON string."""
    # json.dumps handles ALL escape cases correctly (unicode, newlines, quotes, backslashes)
    payload = json.dumps({"type": "token", "text": text})
    return f"data: {payload}\n\n"


def _make_json_event(obj: dict) -> str:
    """Encode a dict as an SSE data line."""
    return f"data: {json.dumps(obj)}\n\n"


KEEPALIVE = "data: [KEEPALIVE]\n\n"


async def _stream_gemini(
    message: str,
    history: list[dict],
    system_prompt: str = "",
) -> AsyncGenerator[str, None]:
    """
    Stream tokens from Gemini API — yields raw text chunks.
    Tries each key × each model until one succeeds.
    """
    active_prompt = system_prompt or CHAT_SYSTEM_PROMPT

    for api_key in GEMINI_API_KEYS:
        for model in GEMINI_MODELS:
            try:
                url = (
                    f"https://generativelanguage.googleapis.com/v1beta/models/"
                    f"{model}:streamGenerateContent?key={api_key}&alt=sse"
                )
                # Build conversation contents (last 10 messages for context)
                contents = []
                for h in history[-10:]:
                    role = "user" if h["role"] == "user" else "model"
                    contents.append({"role": role, "parts": [{"text": h["content"]}]})
                contents.append({"role": "user", "parts": [{"text": message}]})

                body = {
                    "contents": contents,
                    "systemInstruction": {"parts": [{"text": active_prompt}]},
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 4096,
                        "topP": 0.95,
                    },
                }
                yielded_any = False

                async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                    async with client.stream("POST", url, json=body) as resp:
                        if resp.status_code == 429:
                            # Rate limited — try next key
                            logger.debug(f"Gemini {model} rate limited, rotating key...")
                            break
                        if resp.status_code != 200:
                            logger.debug(f"Gemini {model} returned {resp.status_code}")
                            continue
                        async for line in resp.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data = line[6:].strip()
                            if data == "[DONE]":
                                if yielded_any:
                                    return
                                break
                            try:
                                chunk = json.loads(data)
                                # Check for finish reason
                                candidate = chunk.get("candidates", [{}])[0]
                                finish_reason = candidate.get("finishReason", "")
                                if finish_reason in ("STOP", "MAX_TOKENS"):
                                    if yielded_any:
                                        return
                                    break
                                text = (
                                    candidate.get("content", {})
                                    .get("parts", [{}])[0]
                                    .get("text", "")
                                )
                                if text:
                                    yielded_any = True
                                    yield text
                            except (json.JSONDecodeError, IndexError, KeyError):
                                continue

                if yielded_any:
                    return  # Success — exit provider loop

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.warning(f"Gemini {model} timeout/connect error: {e}")
                continue
            except Exception as e:
                logger.warning(f"Gemini {model} stream error: {type(e).__name__}: {e}")
                continue


async def _stream_github_models(
    message: str,
    history: list[dict],
    system_prompt: str = "",
) -> AsyncGenerator[str, None]:
    """Stream tokens from GitHub Models (OpenAI-compatible SSE API)."""
    active_prompt = system_prompt or CHAT_SYSTEM_PROMPT

    for token in GITHUB_MODELS_TOKENS:
        try:
            messages = [{"role": "system", "content": active_prompt}]
            for h in history[-10:]:
                messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": message})

            body = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 4096,
            }
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }
            yielded_any = False

            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
                async with client.stream(
                    "POST",
                    "https://models.inference.ai.azure.com/chat/completions",
                    json=body,
                    headers=headers,
                ) as resp:
                    if resp.status_code == 429:
                        logger.debug("GitHub Models rate limited, rotating token...")
                        continue
                    if resp.status_code != 200:
                        logger.debug(f"GitHub Models returned {resp.status_code}")
                        continue
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:].strip()
                        if data == "[DONE]":
                            if yielded_any:
                                return
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            finish = chunk["choices"][0].get("finish_reason")
                            if delta:
                                yielded_any = True
                                yield delta
                            if finish in ("stop", "length"):
                                if yielded_any:
                                    return
                                break
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

            if yielded_any:
                return

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(f"GitHub Models timeout/connect: {e}")
            continue
        except Exception as e:
            logger.warning(f"GitHub Models stream error: {type(e).__name__}: {e}")
            continue


async def _stream_sambanova(
    message: str,
    history: list[dict],
    system_prompt: str = "",
) -> AsyncGenerator[str, None]:
    """Stream tokens from SambaNova API (OpenAI-compatible)."""
    active_prompt = system_prompt or CHAT_SYSTEM_PROMPT

    for api_key in SAMBANOVA_API_KEYS:
        try:
            messages = [{"role": "system", "content": active_prompt}]
            for h in history[-6:]:
                messages.append({"role": h["role"], "content": h["content"]})
            messages.append({"role": "user", "content": message})

            body = {
                "model": "Meta-Llama-3.3-70B-Instruct",
                "messages": messages,
                "stream": True,
                "temperature": 0.7,
                "max_tokens": 4096,
            }
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            yielded_any = False

            async with httpx.AsyncClient(timeout=httpx.Timeout(90.0, connect=10.0)) as client:
                async with client.stream(
                    "POST",
                    "https://api.sambanova.ai/v1/chat/completions",
                    json=body,
                    headers=headers,
                ) as resp:
                    if resp.status_code == 429:
                        logger.debug("SambaNova rate limited, rotating key...")
                        continue
                    if resp.status_code != 200:
                        logger.debug(f"SambaNova returned {resp.status_code}")
                        continue
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        data = line[6:].strip()
                        if data == "[DONE]":
                            if yielded_any:
                                return
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            finish = chunk["choices"][0].get("finish_reason")
                            if delta:
                                yielded_any = True
                                yield delta
                            if finish in ("stop", "length"):
                                if yielded_any:
                                    return
                                break
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue

            if yielded_any:
                return

        except (httpx.TimeoutException, httpx.ConnectError) as e:
            logger.warning(f"SambaNova timeout/connect: {e}")
            continue
        except Exception as e:
            logger.warning(f"SambaNova stream error: {type(e).__name__}: {e}")
            continue


async def _get_ai_stream(
    message: str,
    history: list[dict],
    system_prompt: str = "",
) -> AsyncGenerator[str, None]:
    """
    Provider chain: Gemini → GitHub Models → SambaNova → structured fallback.
    Yields text tokens from the first successful provider.
    """
    # 1. Gemini (fastest TTFT with 2.0 Flash)
    if GEMINI_API_KEYS:
        collected = False
        try:
            async for token in _stream_gemini(message, history, system_prompt):
                collected = True
                yield token
            if collected:
                return
        except Exception as e:
            logger.warning(f"Gemini provider chain failed: {e}")

    # 2. GitHub Models (gpt-4o-mini)
    if GITHUB_MODELS_TOKENS:
        collected = False
        try:
            async for token in _stream_github_models(message, history, system_prompt):
                collected = True
                yield token
            if collected:
                return
        except Exception as e:
            logger.warning(f"GitHub Models provider chain failed: {e}")

    # 3. SambaNova (LLaMA 3.3 70B)
    if SAMBANOVA_API_KEYS:
        collected = False
        try:
            async for token in _stream_sambanova(message, history, system_prompt):
                collected = True
                yield token
            if collected:
                return
        except Exception as e:
            logger.warning(f"SambaNova provider chain failed: {e}")

    # 4. Structured fallback (when all providers are down)
    logger.error("All AI providers failed — using structured fallback")
    try:
        from app.services.chat_service import _generate_fallback
        from app.agent.intent_classifier import IntentClassifier
        classifier = IntentClassifier()
        intent_result = classifier.classify(message)
        intent = intent_result.intent.value
    except Exception:
        intent = "TASK"
        from app.services.chat_service import _generate_fallback

    fallback = _generate_fallback(message, intent)
    # Stream fallback with natural typing feel
    chunk_sizes = [1, 1, 2, 2, 3, 4]
    i = 0
    ci = 0
    while i < len(fallback):
        size = chunk_sizes[ci % len(chunk_sizes)]
        yield fallback[i: i + size]
        i += size
        ci += 1
        await asyncio.sleep(0.012)


@stream_router.post("/chat")
async def stream_chat(
    data: StreamChatRequest,
    request: Request,
    conn: Connection = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Stream AI chat response token-by-token via SSE.

    Returns: text/event-stream
    Event types:
      - {type: "start", conversation_id, message_id, intent}
      - {type: "token", text: "<chunk>"}
      - {type: "done", message_id, conversation_id}
      - {type: "error", message: "<error>"}
      - [KEEPALIVE] (every 15s to prevent proxy timeouts)
    """
    user_id = current_user["user_id"]
    content = data.content.strip()

    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")

    # Classify intent for better system prompt selection
    detected_intent = "TASK"
    try:
        from app.agent.intent_classifier import IntentClassifier
        classifier = IntentClassifier()
        intent_result = classifier.classify(content)
        detected_intent = intent_result.intent.value
        logger.info(
            f"Stream intent: {detected_intent} (confidence={intent_result.confidence:.2f})"
        )
    except Exception as e:
        logger.warning(f"Intent classification failed: {e}")

    active_system_prompt = INTENT_SYSTEM_PROMPTS.get(detected_intent, CHAT_SYSTEM_PROMPT)

    # Get or create conversation
    conv_id = await get_or_create_conversation(conn, user_id, data.conversation_id)

    # Load recent conversation history
    history: list[dict] = []
    try:
        rows = await conn.fetch(
            """SELECT role, content FROM messages
               WHERE conversation_id = $1
               ORDER BY created_at DESC LIMIT 20""",
            conv_id,
        )
        history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]
    except Exception as e:
        logger.warning(f"Failed to load history: {e}")

    # Store user message
    user_msg_id = str(uuid.uuid4())
    try:
        await conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content) VALUES ($1,$2,$3,$4)",
            user_msg_id, conv_id, "user", content,
        )
    except Exception as e:
        logger.error(f"Failed to store user message: {e}")

    async def event_generator():
        full_response: list[str] = []
        last_keepalive = asyncio.get_event_loop().time()

        try:
            # Emit start event immediately (signals frontend generation is starting)
            yield _make_json_event({
                "type": "start",
                "conversation_id": conv_id,
                "message_id": user_msg_id,
                "intent": detected_intent,
            })

            async for text_chunk in _get_ai_stream(content, history, active_system_prompt):
                # Detect client disconnect before each chunk
                if await request.is_disconnected():
                    logger.info("Client disconnected — aborting stream")
                    return

                full_response.append(text_chunk)
                yield _make_token_event(text_chunk)

                # Yield control to event loop = immediate HTTP flush (no buffering)
                await asyncio.sleep(0)

                # Send keepalive every 15s to prevent Render/Vercel proxy timeout
                now = asyncio.get_event_loop().time()
                if now - last_keepalive > 15:
                    yield KEEPALIVE
                    last_keepalive = now

            # Persist complete assistant response to DB
            response_text = "".join(full_response)
            asst_msg_id = str(uuid.uuid4())
            try:
                await conn.execute(
                    "INSERT INTO messages (id, conversation_id, role, content) VALUES ($1,$2,$3,$4)",
                    asst_msg_id, conv_id, "assistant", response_text,
                )
            except Exception as e:
                logger.error(f"Failed to store assistant message: {e}")

            # Signal completion
            yield _make_json_event({
                "type": "done",
                "message_id": asst_msg_id,
                "conversation_id": conv_id,
            })

        except asyncio.CancelledError:
            logger.info("Stream cancelled by client")
        except Exception as e:
            logger.error(f"Stream generator error: {type(e).__name__}: {e}")
            yield _make_json_event({"type": "error", "message": "Stream error occurred. Please retry."})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "X-Accel-Buffering": "no",       # Disable nginx/Render proxy buffering
            "Connection": "keep-alive",
            "Transfer-Encoding": "chunked",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
            "Access-Control-Allow-Methods": "POST, OPTIONS",
        },
    )
