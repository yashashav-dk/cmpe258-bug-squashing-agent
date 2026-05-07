#!/usr/bin/env python3
"""
web/app.py — FastAPI backend for benchmark-manifest UI.
"""
import os
import sys

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

# Add parent to path so we can import project modules
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from benchmark.ui_service import (
    analyze,
    build_manifest,
    list_manifests,
    run_pipeline,
)

app = FastAPI(title="Bug Squashing Agent", version="1.0.0")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(STATIC_DIR, "index.html")) as f:
        return f.read()


@app.get("/api/manifests")
async def manifests():
    return {"manifests": list_manifests()}


@app.get("/api/case-code")
async def case_code(case_id: str):
    from config import CASES_DIR
    buggy_path = os.path.join(CASES_DIR, case_id, "buggy.py")
    if not os.path.exists(buggy_path):
        return {"error": "not found", "code": ""}
    with open(buggy_path) as f:
        return {"case_id": case_id, "code": f.read()}


def _sse(event: str, data: dict) -> str:
    import json
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def _stream_agent(buggy_code: str, case_id: str, case_dir: str, model_name: str):
    """Generator that yields SSE events while the agent runs."""
    import asyncio
    import json
    from datetime import datetime, timezone
    from agent.memory import Memory
    
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
        elif model_name in ("gemma4", "gemma3", "gemma3_4b", "gemini_or", "qwen_or",
                             "gemini3flash", "gemini3pro"):
            from benchmark.runtime import get_model
            model = get_model(model_name)
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

        # Emit reasoning chain if the model produced one
        if response.thinking:
            yield _sse("reasoning", {
                "step": step + 1,
                "thinking": response.thinking,
            })

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
    from fastapi.responses import StreamingResponse
    from config import CASES_DIR
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


async def _stream_repo_run(
    repo_url: str,
    commit_id: str,
    issue_id: str,
    target_file: str,
    test_command: str,
    regression_test_command: str,
    model_name: str,
    max_steps: int,
    timeout_s: int,
):
    import asyncio
    import subprocess
    import uuid
    from datetime import datetime, timezone
    from benchmark.manifest import BenchmarkCase
    from benchmark.runtime import AgentRuntime

    run_id   = uuid.uuid4().hex[:8]
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    clone_dir = os.path.join("logs", "runs", f"repo_{run_id}", repo_name)
    os.makedirs(os.path.dirname(clone_dir), exist_ok=True)

    yield _sse("status", {"phase": "clone", "message": f"Cloning {repo_url} …"})

    proc = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: subprocess.run(
            ["git", "clone", "--depth", "200", repo_url, clone_dir],
            capture_output=True, text=True,
        ),
    )
    if proc.returncode != 0:
        yield _sse("error", {"message": f"Clone failed: {proc.stderr[:500]}"})
        return
    yield _sse("status", {"phase": "clone", "message": "Clone complete."})

    if commit_id:
        yield _sse("status", {"phase": "checkout", "message": f"Checking out {commit_id[:8]} …"})
        proc = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                ["git", "-C", clone_dir, "checkout", commit_id],
                capture_output=True, text=True,
            ),
        )
        if proc.returncode != 0:
            yield _sse("error", {"message": f"Checkout failed: {proc.stderr[:300]}"})
            return
        yield _sse("status", {"phase": "checkout", "message": f"At commit {commit_id[:8]}."})

    yield _sse("status", {"phase": "preflight", "message": f"Preflight: {test_command}"})
    try:
        preflight = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: subprocess.run(
                test_command, shell=True,
                capture_output=True, text=True,
                cwd=clone_dir, timeout=60,
            ),
        )
        if preflight.returncode == 0:
            yield _sse("status", {
                "phase": "preflight",
                "message": "Tests already pass — running agent to verify no regression.",
            })
        else:
            yield _sse("status", {
                "phase": "preflight",
                "message": f"Tests fail (exit {preflight.returncode}) — bug confirmed, running agent.",
            })
    except Exception as e:
        yield _sse("status", {"phase": "preflight", "message": f"Preflight skipped: {e}"})

    case = BenchmarkCase(
        case_id=f"github_{run_id}",
        source_type="historical",
        repo_url=repo_url,
        repo_name=repo_name,
        base_commit=commit_id or "HEAD",
        python_version="3.11",
        install=["pip", "install", "-e", ".", "pytest"],
        test_command=test_command,
        regression_test_command=regression_test_command or None,
        allowed_paths=[target_file],
        target_file=target_file,
        injection_patch="# live issue — no injection",
        expected_failures=[],
        tags=["github", "live"],
        difficulty="medium",
        seed=0,
        metadata={"workspace_dir": clone_dir, "issue_id": issue_id},
    )

    yield _sse("status", {
        "phase": "agent",
        "message": f"Agent running — model: {model_name}, max steps: {max_steps} …",
    })

    runtime = AgentRuntime(max_steps=max_steps, timeout_s=timeout_s)
    try:
        result = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: runtime.run_case(
                case=case,
                model_name=model_name,
                case_id=f"github_{run_id}",
                workspace_root=clone_dir,
            ),
        )
        yield _sse("done", {
            "resolved":         result.resolved,
            "model_text":       result.model_text,
            "target_exit":      result.target_test_exit_code,
            "test_output":      (result.target_test_output or "")[:3000],
            "wall_time_ms":     round(result.wall_time_ms),
            "failure_mode":     result.failure_mode,
            "planner_stats":    result.planner_stats,
            "issue_id":         issue_id,
            "commit_id":        commit_id or "HEAD",
            "workspace":        clone_dir,
        })
    except Exception as exc:
        yield _sse("error", {"message": str(exc)})


@app.post("/api/run-repo")
async def run_repo_endpoint(
    repo_url: str = Form(...),
    commit_id: str = Form(""),
    issue_id: str = Form(""),
    target_file: str = Form(...),
    test_command: str = Form(...),
    regression_test_command: str = Form(""),
    model: str = Form("gemini3pro"),
    max_steps: int = Form(10),
    timeout_s: int = Form(300),
):
    from fastapi.responses import StreamingResponse

    return StreamingResponse(
        _stream_repo_run(
            repo_url=repo_url,
            commit_id=commit_id,
            issue_id=issue_id,
            target_file=target_file,
            test_command=test_command,
            regression_test_command=regression_test_command,
            model_name=model,
            max_steps=max_steps,
            timeout_s=timeout_s,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/build-manifest")
async def build_manifest_endpoint(
    historical_source: str = Form(...),
    synthetic_source: str = Form(...),
    output: str = Form("benchmark/manifests/pilot_hybrid.jsonl"),
    target_count: int = Form(30),
    historical_ratio: float = Form(0.7),
    synthetic_ratio: float = Form(0.3),
    seed: int = Form(13),
):
    proc = build_manifest(
        historical_source=historical_source,
        synthetic_source=synthetic_source,
        output=output,
        target_count=target_count,
        historical_ratio=historical_ratio,
        synthetic_ratio=synthetic_ratio,
        seed=seed,
    )
    return {
        "ok": proc.returncode == 0,
        "output_manifest": output,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "returncode": proc.returncode,
    }


@app.post("/api/run-manifest")
async def run_manifest_endpoint(
    manifest: str = Form(...),
    models: str = Form("gemma4"),
    output: str = Form("logs/benchmark_results.jsonl"),
    report_output: str = Form("logs/benchmark_report.json"),
    max_steps: int = Form(15),
    timeout_s: int = Form(180),
    repetitions: int = Form(1),
):
    try:
        result = run_pipeline(
            manifest=manifest,
            models=models,
            output=output,
            report_output=report_output,
            max_steps=max_steps,
            timeout_s=timeout_s,
            repetitions=repetitions,
        )
        return {
            "ok": True,
            "results_path": result.results_path,
            "report_path": result.report_path,
            "report": result.report,
            "run_stdout": result.run_stdout,
            "run_stderr": result.run_stderr,
            "analyze_stdout": result.analyze_stdout,
            "analyze_stderr": result.analyze_stderr,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


@app.post("/api/analyze")
async def analyze_endpoint(
    input_path: str = Form("latest"),
    output: str = Form("logs/benchmark_report.json"),
):
    proc = analyze(input_path=input_path, output=output)
    return {
        "ok": proc.returncode == 0,
        "output_report": output,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "returncode": proc.returncode,
    }
