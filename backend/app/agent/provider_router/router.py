"""
Provider Router
Abstracted AI provider routing with fallback chain.
Primary: Gemini → Fallback: GitHub Models → Fallback: SambaNova

No hardcoded provider logic in business logic — all routing is here.
"""

import os
import json
import logging
import httpx
from enum import Enum
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# ─── Provider Configuration (loaded from environment variables) ───────────────
# Keys are stored as comma-separated environment variables.
# Example env vars:
#   GEMINI_API_KEYS=key1,key2,key3
#   GITHUB_MODELS_TOKENS=token1,token2
#   SAMBANOVA_API_KEYS=key1,key2

def _load_keys(env_var: str) -> list[str]:
    """Load API keys from environment variable (comma-separated)."""
    raw = os.getenv(env_var, "")
    if raw.strip():
        return [k.strip() for k in raw.split(",") if k.strip()]
    return []


# Keys are loaded from environment variables on Render.
# Set these in the Render dashboard:
#   GEMINI_API_KEYS=key1,key2,...
#   GITHUB_MODELS_TOKENS=token1,token2,...
#   SAMBANOVA_API_KEYS=key1,key2,...
GEMINI_API_KEYS = _load_keys("GEMINI_API_KEYS")
GITHUB_MODELS_TOKENS = _load_keys("GITHUB_MODELS_TOKENS")
SAMBANOVA_API_KEYS = _load_keys("SAMBANOVA_API_KEYS")


class ProviderName(str, Enum):
    GEMINI = "gemini"
    GITHUB_MODELS = "github_models"
    SAMBANOVA = "sambanova"
    NONE = "none"


@dataclass
class ProviderResult:
    provider: ProviderName
    model: str
    content: str
    tokens_used: int = 0
    attempts: int = 1


# ─── Provider Implementations ────────────────────────────────────────────────

async def _call_gemini(prompt: str, system_prompt: str = "") -> str | None:
    """Call Gemini API with key rotation."""
    model = "gemini-1.5-flash"

    for api_key in GEMINI_API_KEYS:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:generateContent?key={api_key}"
        )
        body = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.3,
                "maxOutputTokens": 4096,
            },
        }
        if system_prompt:
            body["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts:
                            return parts[0].get("text", "")
                elif resp.status_code in (429, 503):
                    logger.warning(f"Gemini key exhausted, rotating...")
                    continue
                else:
                    logger.warning(f"Gemini error {resp.status_code}: {resp.text[:200]}")
                    continue
        except Exception as e:
            logger.warning(f"Gemini call failed: {e}")
            continue

    return None


async def _call_github_models(prompt: str, system_prompt: str = "") -> str | None:
    """Call GitHub Models API with token rotation."""
    url = "https://models.inference.ai.azure.com/chat/completions"
    model = "gpt-4o-mini"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    for token in GITHUB_MODELS_TOKENS:
        body = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=body, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
                elif resp.status_code in (429, 503):
                    logger.warning("GitHub Models token exhausted, rotating...")
                    continue
                else:
                    logger.warning(f"GitHub Models error {resp.status_code}")
                    continue
        except Exception as e:
            logger.warning(f"GitHub Models call failed: {e}")
            continue

    return None


async def _call_sambanova(prompt: str, system_prompt: str = "") -> str | None:
    """Call SambaNova API with key rotation."""
    url = "https://api.sambanova.ai/v1/chat/completions"
    model = "Meta-Llama-3.1-8B-Instruct"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    for api_key in SAMBANOVA_API_KEYS:
        body = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
            "max_tokens": 4096,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(url, json=body, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices", [])
                    if choices:
                        return choices[0].get("message", {}).get("content", "")
                elif resp.status_code in (429, 503):
                    logger.warning("SambaNova key exhausted, rotating...")
                    continue
                else:
                    logger.warning(f"SambaNova error {resp.status_code}")
                    continue
        except Exception as e:
            logger.warning(f"SambaNova call failed: {e}")
            continue

    return None


# ─── Router ──────────────────────────────────────────────────────────────────

class ProviderRouter:
    """
    Abstracted provider router.
    Tries: Gemini → GitHub Models → SambaNova
    No hardcoded provider logic outside this class.
    """

    async def complete(
        self, prompt: str, system_prompt: str = ""
    ) -> ProviderResult:
        """Execute prompt with fallback chain."""
        attempts = 0

        # 1. Try Gemini
        attempts += 1
        logger.info("Provider: trying Gemini...")
        result = await _call_gemini(prompt, system_prompt)
        if result:
            return ProviderResult(
                provider=ProviderName.GEMINI,
                model="gemini-1.5-flash",
                content=result,
                attempts=attempts,
            )

        # 2. Fallback: GitHub Models
        attempts += 1
        logger.info("Provider: Gemini failed, trying GitHub Models...")
        result = await _call_github_models(prompt, system_prompt)
        if result:
            return ProviderResult(
                provider=ProviderName.GITHUB_MODELS,
                model="gpt-4o-mini",
                content=result,
                attempts=attempts,
            )

        # 3. Fallback: SambaNova
        attempts += 1
        logger.info("Provider: GitHub Models failed, trying SambaNova...")
        result = await _call_sambanova(prompt, system_prompt)
        if result:
            return ProviderResult(
                provider=ProviderName.SAMBANOVA,
                model="Meta-Llama-3.1-8B-Instruct",
                content=result,
                attempts=attempts,
            )

        # All providers failed
        logger.error("All providers failed!")
        return ProviderResult(
            provider=ProviderName.NONE,
            model="none",
            content="",
            attempts=attempts,
        )
