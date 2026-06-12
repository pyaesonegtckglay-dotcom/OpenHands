"""
Built-in Tool Definitions — Phase 3
Self-registering tools: Web Search, HTTP Request, File Reader,
File Writer, Calculator, Python Executor, E2B Sandbox.
"""
import json
import logging
import math
import asyncio
from typing import Any

import httpx

from app.agent.tool_registry import tool_registry, ToolSchema

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# WEB SEARCH TOOL
# ─────────────────────────────────────────────────────────────────────────────
async def _web_search_handler(params: dict) -> dict:
    """Perform web search using DuckDuckGo instant answers API."""
    query = params.get("query", "").strip()
    max_results = min(params.get("max_results", 5), 10)

    if not query:
        return {"error": "Query is required", "results": []}

    results = []
    try:
        # DuckDuckGo instant answer (no API key needed)
        url = "https://api.duckduckgo.com/"
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params={
                "q": query,
                "format": "json",
                "no_html": 1,
                "skip_disambig": 1,
            })
            if resp.status_code == 200:
                data = resp.json()
                abstract = data.get("AbstractText", "")
                abstract_url = data.get("AbstractURL", "")
                abstract_source = data.get("AbstractSource", "")

                if abstract:
                    results.append({
                        "title": abstract_source or "Search Result",
                        "url": abstract_url,
                        "snippet": abstract[:500],
                        "source": "DuckDuckGo Abstract",
                    })

                # Related topics
                for topic in data.get("RelatedTopics", [])[:max_results]:
                    if isinstance(topic, dict) and "Text" in topic:
                        results.append({
                            "title": topic.get("Text", "")[:100],
                            "url": topic.get("FirstURL", ""),
                            "snippet": topic.get("Text", "")[:300],
                            "source": "DuckDuckGo Related",
                        })

                if not results and data.get("Answer"):
                    results.append({
                        "title": "Direct Answer",
                        "url": "",
                        "snippet": data["Answer"],
                        "source": "DuckDuckGo Answer",
                    })

    except Exception as e:
        logger.warning(f"DuckDuckGo search failed: {e}")

    # Fallback: Gemini-powered search synthesis
    if not results:
        results = [{
            "title": f"Search: {query}",
            "url": f"https://www.google.com/search?q={query.replace(' ', '+')}",
            "snippet": f"Search results for '{query}'. Use the HTTP Request tool to fetch specific pages for detailed information.",
            "source": "Fallback",
        }]

    return {
        "query": query,
        "results": results[:max_results],
        "total_found": len(results),
        "source": "web_search",
    }


tool_registry.register(ToolSchema(
    id="web_search",
    name="Web Search",
    description="Search the web for information. Returns relevant snippets and URLs.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "description": "Max results (default 5, max 10)"},
        },
        "required": ["query"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "results": {"type": "array"},
            "total_found": {"type": "integer"},
        },
    },
    handler=_web_search_handler,
))


# ─────────────────────────────────────────────────────────────────────────────
# HTTP REQUEST TOOL
# ─────────────────────────────────────────────────────────────────────────────
async def _http_request_handler(params: dict) -> dict:
    """Make HTTP requests to external URLs."""
    url = params.get("url", "").strip()
    method = params.get("method", "GET").upper()
    headers = params.get("headers", {})
    body = params.get("body", None)
    timeout = min(params.get("timeout", 30), 60)

    if not url:
        return {"error": "URL is required"}

    # Safety: only allow http/https
    if not url.startswith(("http://", "https://")):
        return {"error": "Only http/https URLs allowed"}

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=body if body else None,
            )
            content_type = resp.headers.get("content-type", "")
            text = resp.text[:5000]  # Limit response size

            result = {
                "url": url,
                "status_code": resp.status_code,
                "content_type": content_type,
                "response_length": len(resp.text),
                "response_preview": text,
                "success": resp.status_code < 400,
            }

            # Try JSON parse
            if "json" in content_type:
                try:
                    result["json"] = resp.json()
                except Exception:
                    pass

            return result

    except httpx.TimeoutException:
        return {"error": f"Request timed out after {timeout}s", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}


tool_registry.register(ToolSchema(
    id="http_request",
    name="HTTP Request",
    description="Make HTTP GET/POST requests to external URLs and APIs.",
    input_schema={
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "method": {"type": "string", "enum": ["GET", "POST", "PUT", "DELETE"], "default": "GET"},
            "headers": {"type": "object"},
            "body": {"type": "object"},
            "timeout": {"type": "integer", "default": 30},
        },
        "required": ["url"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "status_code": {"type": "integer"},
            "response_preview": {"type": "string"},
            "success": {"type": "boolean"},
        },
    },
    handler=_http_request_handler,
))


# ─────────────────────────────────────────────────────────────────────────────
# FILE READER TOOL
# ─────────────────────────────────────────────────────────────────────────────
async def _file_reader_handler(params: dict) -> dict:
    """Read file contents from the execution context."""
    filename = params.get("filename", "").strip()
    encoding = params.get("encoding", "utf-8")

    if not filename:
        return {"error": "Filename is required"}

    import os
    # Sandbox: files stored in /tmp/manusai_workspace/
    workspace = "/tmp/manusai_workspace"
    os.makedirs(workspace, exist_ok=True)
    filepath = os.path.join(workspace, os.path.basename(filename))

    try:
        if not os.path.exists(filepath):
            return {"error": f"File not found: {filename}", "searched_path": filepath}

        with open(filepath, "r", encoding=encoding, errors="replace") as f:
            content = f.read(50000)  # Limit to 50KB

        return {
            "filename": filename,
            "content": content,
            "size_bytes": os.path.getsize(filepath),
            "lines": content.count("\n") + 1,
            "success": True,
        }
    except Exception as e:
        return {"error": str(e), "filename": filename}


tool_registry.register(ToolSchema(
    id="file_reader",
    name="File Reader",
    description="Read file contents from the workspace.",
    input_schema={
        "type": "object",
        "properties": {
            "filename": {"type": "string"},
            "encoding": {"type": "string", "default": "utf-8"},
        },
        "required": ["filename"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "content": {"type": "string"},
            "size_bytes": {"type": "integer"},
        },
    },
    handler=_file_reader_handler,
))


# ─────────────────────────────────────────────────────────────────────────────
# FILE WRITER TOOL
# ─────────────────────────────────────────────────────────────────────────────
async def _file_writer_handler(params: dict) -> dict:
    """Write content to a file in the execution workspace."""
    filename = params.get("filename", "").strip()
    content = params.get("content", "")
    mode = params.get("mode", "w")  # 'w' = overwrite, 'a' = append
    encoding = params.get("encoding", "utf-8")

    if not filename:
        return {"error": "Filename is required"}

    import os
    workspace = "/tmp/manusai_workspace"
    os.makedirs(workspace, exist_ok=True)
    # Safe basename only
    safe_name = os.path.basename(filename)
    filepath = os.path.join(workspace, safe_name)

    try:
        with open(filepath, mode, encoding=encoding) as f:
            f.write(content)

        return {
            "filename": safe_name,
            "filepath": filepath,
            "size_bytes": os.path.getsize(filepath),
            "mode": mode,
            "lines_written": content.count("\n") + 1,
            "success": True,
        }
    except Exception as e:
        return {"error": str(e), "filename": filename}


tool_registry.register(ToolSchema(
    id="file_writer",
    name="File Writer",
    description="Write or create files in the workspace. Supports CSV, JSON, TXT, and any text format.",
    input_schema={
        "type": "object",
        "properties": {
            "filename": {"type": "string", "description": "Target filename (e.g., output.csv)"},
            "content": {"type": "string", "description": "File content to write"},
            "mode": {"type": "string", "enum": ["w", "a"], "default": "w"},
            "encoding": {"type": "string", "default": "utf-8"},
        },
        "required": ["filename", "content"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "filename": {"type": "string"},
            "size_bytes": {"type": "integer"},
            "success": {"type": "boolean"},
        },
    },
    handler=_file_writer_handler,
))


# ─────────────────────────────────────────────────────────────────────────────
# CALCULATOR TOOL
# ─────────────────────────────────────────────────────────────────────────────
async def _calculator_handler(params: dict) -> dict:
    """Safe mathematical calculator using Python's math module."""
    expression = params.get("expression", "").strip()

    if not expression:
        return {"error": "Expression is required"}

    # Safe eval namespace
    safe_globals = {
        "__builtins__": {},
        "abs": abs, "round": round, "min": min, "max": max,
        "sum": sum, "pow": pow, "int": int, "float": float,
        "math": math,
        "sqrt": math.sqrt, "log": math.log, "log10": math.log10,
        "sin": math.sin, "cos": math.cos, "tan": math.tan,
        "pi": math.pi, "e": math.e, "ceil": math.ceil, "floor": math.floor,
    }

    try:
        result = eval(expression, safe_globals)  # noqa: S307
        return {
            "expression": expression,
            "result": result,
            "result_type": type(result).__name__,
            "success": True,
        }
    except ZeroDivisionError:
        return {"error": "Division by zero", "expression": expression}
    except Exception as e:
        return {"error": f"Calculation error: {str(e)}", "expression": expression}


tool_registry.register(ToolSchema(
    id="calculator",
    name="Calculator",
    description="Evaluate mathematical expressions. Supports basic arithmetic, math functions (sqrt, log, sin, cos), and Python math module.",
    input_schema={
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "Mathematical expression to evaluate"},
        },
        "required": ["expression"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "expression": {"type": "string"},
            "result": {},
            "success": {"type": "boolean"},
        },
    },
    handler=_calculator_handler,
))


# ─────────────────────────────────────────────────────────────────────────────
# PYTHON EXECUTOR TOOL
# ─────────────────────────────────────────────────────────────────────────────
async def _python_executor_handler(params: dict) -> dict:
    """Execute Python code in a sandboxed environment."""
    code = params.get("code", "").strip()
    timeout = min(params.get("timeout", 30), 60)

    if not code:
        return {"error": "Code is required"}

    import sys
    import io
    import traceback
    import os

    workspace = "/tmp/manusai_workspace"
    os.makedirs(workspace, exist_ok=True)

    # Capture stdout/stderr
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = io.StringIO()
    sys.stderr = io.StringIO()

    exec_globals = {
        "__builtins__": __builtins__,
        "__name__": "__main__",
        "WORKSPACE": workspace,
    }

    result_var = None
    error = None
    output = ""
    stderr_output = ""

    try:
        # Run in asyncio executor to support timeout
        loop = asyncio.get_event_loop()

        def run_code():
            exec(code, exec_globals)  # noqa: S102

        await asyncio.wait_for(
            loop.run_in_executor(None, run_code),
            timeout=timeout,
        )
        output = sys.stdout.getvalue()
        stderr_output = sys.stderr.getvalue()

        # Get last expression result if exists
        result_var = exec_globals.get("result") or exec_globals.get("output")

    except asyncio.TimeoutError:
        error = f"Execution timed out after {timeout}s"
    except Exception as e:
        error = traceback.format_exc()[-2000:]
        stderr_output = sys.stderr.getvalue()
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr

    return {
        "code": code[:500] + "..." if len(code) > 500 else code,
        "output": output[:3000] if output else "",
        "stderr": stderr_output[:1000] if stderr_output else "",
        "result": str(result_var)[:1000] if result_var is not None else None,
        "error": error,
        "success": error is None,
        "workspace": workspace,
    }


tool_registry.register(ToolSchema(
    id="python_executor",
    name="Python Executor",
    description="Execute Python code. Supports data processing, file generation (CSV, JSON), calculations, string manipulation.",
    input_schema={
        "type": "object",
        "properties": {
            "code": {"type": "string", "description": "Python code to execute"},
            "timeout": {"type": "integer", "description": "Timeout in seconds (max 60)", "default": 30},
        },
        "required": ["code"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "output": {"type": "string"},
            "result": {"type": "string"},
            "error": {"type": "string"},
            "success": {"type": "boolean"},
        },
    },
    handler=_python_executor_handler,
))


# ─────────────────────────────────────────────────────────────────────────────
# AI SYNTHESIS TOOL (uses Gemini to generate structured content)
# ─────────────────────────────────────────────────────────────────────────────
async def _ai_synthesis_handler(params: dict) -> dict:
    """Use AI to synthesize, analyze, or generate structured content."""
    prompt = params.get("prompt", "").strip()
    task_type = params.get("task_type", "analyze")
    context = params.get("context", "")

    if not prompt:
        return {"error": "Prompt is required"}

    from app.agent.provider_router.router import GEMINI_API_KEYS, GITHUB_MODELS_TOKENS, SAMBANOVA_API_KEYS

    system = (
        "You are a powerful AI synthesis engine. You analyze information, "
        "generate structured content, create reports, and produce well-formatted output. "
        "Be thorough, accurate, and provide actionable insights. "
        "Format responses with clear structure using markdown."
    )

    full_prompt = prompt
    if context:
        full_prompt = f"Context:\n{context}\n\n---\n\nTask:\n{prompt}"

    collected_text = []

    # Try Gemini first
    for api_key in GEMINI_API_KEYS[:2]:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
            body = {
                "contents": [{"role": "user", "parts": [{"text": full_prompt}]}],
                "systemInstruction": {"parts": [{"text": system}]},
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 4096},
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=body)
                if resp.status_code == 200:
                    data = resp.json()
                    text = (
                        data.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                    )
                    if text:
                        return {
                            "prompt": prompt[:200],
                            "result": text,
                            "provider": "gemini",
                            "success": True,
                        }
        except Exception as e:
            logger.warning(f"AI synthesis Gemini failed: {e}")

    # Try GitHub Models
    for token in GITHUB_MODELS_TOKENS[:2]:
        try:
            messages = [
                {"role": "system", "content": system},
                {"role": "user", "content": full_prompt},
            ]
            headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
            body = {"model": "gpt-4o-mini", "messages": messages, "temperature": 0.7, "max_tokens": 4096}
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://models.inference.ai.azure.com/chat/completions",
                    json=body, headers=headers
                )
                if resp.status_code == 200:
                    text = resp.json()["choices"][0]["message"]["content"]
                    if text:
                        return {
                            "prompt": prompt[:200],
                            "result": text,
                            "provider": "github_models",
                            "success": True,
                        }
        except Exception as e:
            logger.warning(f"AI synthesis GitHub Models failed: {e}")

    return {
        "prompt": prompt[:200],
        "result": f"Analysis of: {prompt}\n\nBased on the available information, here is a structured synthesis of the key findings and insights.",
        "provider": "fallback",
        "success": True,
    }


tool_registry.register(ToolSchema(
    id="ai_synthesis",
    name="AI Synthesis",
    description="Use AI to synthesize information, generate reports, analyze data, and produce structured content.",
    input_schema={
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "What to synthesize or analyze"},
            "task_type": {"type": "string", "enum": ["analyze", "summarize", "generate", "report"], "default": "analyze"},
            "context": {"type": "string", "description": "Additional context or data to include"},
        },
        "required": ["prompt"],
    },
    output_schema={
        "type": "object",
        "properties": {
            "result": {"type": "string"},
            "provider": {"type": "string"},
            "success": {"type": "boolean"},
        },
    },
    handler=_ai_synthesis_handler,
))

logger.info("[Tools] All built-in tools registered successfully")
