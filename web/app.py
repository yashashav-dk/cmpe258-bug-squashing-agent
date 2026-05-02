#!/usr/bin/env python3
"""
web/app.py — FastAPI backend for Bug Squashing Agent Web UI.

Endpoints:
  GET  /          → serve index.html
  GET  /api/cases → list available case IDs
  POST /api/run   → run agent on a case, stream SSE events
  POST /api/upload → run agent on uploaded buggy.py content, stream SSE events

Run:
    uvicorn web.app:app --reload --port 8000
"""
import asyncio
import json
import os
import sys
import time
import tempfile
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

# Add parent to path so we can import project modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import CASES_DIR
from agent.memory import Memory

app = FastAPI(title="Bug Squashing Agent", version="1.0.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def get_cases() -> list:
    if not os.path.isdir(CASES_DIR):
        return []
    return sorted(d for d in os.listdir(CASES_DIR) if os.path.isdir(os.path.join(CASES_DIR, d)))


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(STATIC_DIR, "index.html")) as f:
        return f.read()


@app.get("/api/cases")
async def list_cases():
    return {"cases": get_cases()}


@app.get("/api/case-code")
async def case_code(case_id: str):
    buggy_path = os.path.join(CASES_DIR, case_id, "buggy.py")
    if not os.path.exists(buggy_path):
        return {"error": "not found", "code": ""}
    with open(buggy_path) as f:
        return {"case_id": case_id, "code": f.read()}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_agent(buggy_code: str, case_id: str, case_dir: str, model_name: str):
    """Generator that yields SSE events while the agent runs."""
    try:
        from agent.planner import Planner, SYSTEM_PROMPT
        from agent.tools_impl import AGENT_TOOLS
    except ImportError as e:
        yield _sse("error", {"message": f"Import error: {e}"})
        return

    # Load model
    try:
        if model_name == "gemini":
            from models.gemini import GeminiModel
            model = GeminiModel()
        elif model_name == "qwen":
            from models.qwen import QwenModel
            model = QwenModel()
        elif model_name == "minimax":
            from models.minimax import MiniMaxModel
            model = MiniMaxModel()
        elif model_name == "gemma4":
            from models.gemma4 import Gemma4Model
            model = Gemma4Model()
        elif model_name.startswith("local:"):
            custom_model = model_name.split(":", 1)[1]
            from models.gemma4 import Gemma4Model
            model = Gemma4Model(model_name=custom_model)
        else:
            yield _sse("error", {"message": f"Unknown model: {model_name}"})
            return
    except Exception as e:
        yield _sse("error", {"message": f"Model init failed: {e}"})
        return

    yield _sse("started", {
        "model": model.name(),
        "case_id": case_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })

    planner = Planner(model=model, max_steps=15)
    memory = Memory()
    history = planner.history

    msg = (
        f"Investigate this bug in {case_id}:\n```python\n{buggy_code}\n```\n"
        f"Run `pytest test_buggy.py` in `{case_dir}`. Fix it using tools."
    )
    history.append({"role": "user", "content": msg})

    resolved = False
    for step in range(planner.max_steps):
        yield _sse("step_start", {"step": step + 1, "max_steps": planner.max_steps})
        await asyncio.sleep(0)  # yield control to event loop

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: model.chat(messages=history, tools=AGENT_TOOLS, system_instruction=SYSTEM_PROMPT)
            )
        except Exception as e:
            yield _sse("error", {"message": str(e)})
            return

        response_text = response.text or ""
        assistant_msg = {"role": "assistant", "content": response_text}
        if response.tool_calls:
            assistant_msg["tool_calls"] = response.tool_calls
        history.append(assistant_msg)

        if response_text:
            yield _sse("agent_text", {
                "step": step + 1,
                "text": response_text,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": round(response.latency_ms, 1),
            })

        if response.tool_calls:
            for tc in response.tool_calls:
                name = tc["name"]
                args = tc["arguments"]
                yield _sse("tool_call", {"step": step + 1, "name": name, "args": args})
                await asyncio.sleep(0)

                tool_result = f"Tool '{name}' not found."
                for tool_fn in AGENT_TOOLS:
                    if tool_fn.__name__ == name:
                        try:
                            tool_result = tool_fn(**args)
                        except Exception as e:
                            tool_result = f"Tool execution failed: {e}"
                        break

                yield _sse("tool_result", {
                    "step": step + 1,
                    "name": name,
                    "result": str(tool_result)[:1000],
                })
                history.append({"role": "tool", "name": name, "content": str(tool_result)})
        else:
            if "RESOLVED" in response_text or "All tests pass" in response_text:
                resolved = True
                break

    # Dream consolidation
    try:
        dream = await asyncio.get_event_loop().run_in_executor(
            None, lambda: memory.consolidate_dream(history, model)
        )
        yield _sse("dream", {"text": dream})
    except Exception:
        pass

    yield _sse("done", {
        "resolved": resolved,
        "steps": step + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


@app.post("/api/run")
async def run_case(
    case_id: str = Form(...),
    model: str = Form("gemini"),
):
    """Stream agent execution for a built-in case via SSE."""
    case_dir = os.path.join(CASES_DIR, case_id)
    buggy_path = os.path.join(case_dir, "buggy.py")
    if not os.path.exists(buggy_path):
        return {"error": f"Case {case_id} not found"}

    with open(buggy_path) as f:
        buggy_code = f.read()

    return StreamingResponse(
        _stream_agent(buggy_code, case_id, case_dir, model),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/upload")
async def run_upload(
    file: UploadFile = File(...),
    model: str = Form("gemini"),
):
    """Stream agent execution for an uploaded buggy.py via SSE."""
    content = await file.read()
    buggy_code = content.decode("utf-8", errors="replace")

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write the uploaded file so the agent can reference it
        buggy_path = os.path.join(tmpdir, "buggy.py")
        with open(buggy_path, "w") as f:
            f.write(buggy_code)
        case_id = "uploaded_file"

        return StreamingResponse(
            _stream_agent(buggy_code, case_id, tmpdir, model),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
