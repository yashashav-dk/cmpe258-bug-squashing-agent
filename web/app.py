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
    models: str = Form("gemini"),
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
