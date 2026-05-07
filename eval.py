#!/usr/bin/env python3
"""
eval.py — Batch evaluation runner.

Runs all cases × all specified models, writing results to logs/eval_results.jsonl.

Usage:
    python3 eval.py                              # all models, all cases
    python3 eval.py --models gemini              # specific model
    python3 eval.py --cases case_001 case_002   # specific cases
    python3 eval.py --models gemini --cases case_001 case_002
"""
import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timezone

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich import box

from config import CASES_DIR
from agent.case_runtime import run_case_with_pec

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "logs", "eval_results.jsonl")
ALL_MODELS = ["gemini", "qwen", "minimax", "gemma4"]


def _percentile(sorted_vals: list[float], q: float) -> float | None:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * (pos - lo)


def get_model(model_name: str):
    if model_name == "gemini":
        from models.gemini import GeminiModel
        return GeminiModel()
    elif model_name == "qwen":
        from models.qwen import QwenModel
        return QwenModel()
    elif model_name == "minimax":
        from models.minimax import MiniMaxModel
        return MiniMaxModel()
    elif model_name == "gemma4":
        from models.gemma4 import Gemma4Model
        return Gemma4Model()
    else:
        raise ValueError(f"Unknown model: {model_name!r}")


def list_all_cases() -> list:
    if not os.path.isdir(CASES_DIR):
        return []
    selected = []
    for d in os.listdir(CASES_DIR):
        if not os.path.isdir(os.path.join(CASES_DIR, d)):
            continue
        match = re.fullmatch(r"case_(\d+)", d)
        if not match:
            continue
        selected.append((int(match.group(1)), d))
    return [name for _, name in sorted(selected, key=lambda item: item[0])]


def run_single_case(case_id: str, model_name: str, console: Console) -> dict:
    """Run the agent on a single case. Returns a result dict."""
    case_dir = os.path.join(CASES_DIR, case_id)
    buggy_path = os.path.join(case_dir, "buggy.py")
    test_path = os.path.join(case_dir, "test_buggy.py")

    if not os.path.exists(buggy_path):
        return {
            "case_id": case_id, "model": model_name,
            "passed": False, "error": "buggy.py not found",
            "steps": 0, "input_tokens": 0, "output_tokens": 0, "latency_ms": 0,
        }

    try:
        model = get_model(model_name)
    except Exception as e:
        return {
            "case_id": case_id, "model": model_name,
            "passed": False, "error": f"Model init failed: {e}",
            "steps": 0, "input_tokens": 0, "output_tokens": 0, "latency_ms": 0,
        }

    t0 = time.monotonic()
    try:
        run_result = run_case_with_pec(
            case_id=case_id,
            model=model,
            cases_root=CASES_DIR,
            max_steps=10,
        )
        result_text = run_result.summary_text
        passed = run_result.resolved
        planner_stats = run_result.planner_stats
    except Exception as e:
        result_text = str(e)
        passed = False
        planner_stats = {
            "steps": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
        }
    elapsed_ms = (time.monotonic() - t0) * 1000

    total_input = int(planner_stats.get("total_input_tokens", 0))
    total_output = int(planner_stats.get("total_output_tokens", 0))
    steps = int(planner_stats.get("steps", 0))

    # Also verify against pytest ground truth
    import subprocess
    test_result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "-q", "--tb=no"],
        capture_output=True, text=True, cwd=case_dir
    )
    passed = test_result.returncode == 0

    return {
        "case_id": case_id,
        "model": model_name,
        "passed": passed,
        "steps": steps,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "latency_ms": round(elapsed_ms, 1),
        "agent_output": result_text[:500],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def write_result(result: dict):
    os.makedirs(os.path.dirname(RESULTS_PATH), exist_ok=True)
    with open(RESULTS_PATH, "a") as f:
        f.write(json.dumps(result) + "\n")


def print_summary_table(results: list, console: Console):
    table = Table(title="Evaluation Results", box=box.ROUNDED, show_lines=True)
    table.add_column("Case", style="cyan", no_wrap=True)
    table.add_column("Model", style="magenta")
    table.add_column("Passed", justify="center")
    table.add_column("Steps", justify="right")
    table.add_column("Latency (s)", justify="right")
    table.add_column("Error / Note", style="dim", max_width=40)

    for r in results:
        passed_str = "✅" if r["passed"] else "❌"
        latency = f"{r['latency_ms']/1000:.1f}s"
        error = r.get("error", "")
        table.add_row(r["case_id"], r["model"], passed_str, str(r["steps"]), latency, error)

    console.print(table)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    console.print(f"\n[bold]Pass rate: [green]{passed}[/green]/[cyan]{total}[/cyan] ({100*passed//total if total else 0}%)[/bold]")
    console.print(f"[dim]Results written to: {RESULTS_PATH}[/dim]")


def print_aggregate_metrics(results: list, console: Console) -> None:
    from collections import defaultdict

    if not results:
        return
    by_model: dict[str, list] = defaultdict(list)
    for r in results:
        by_model[r["model"]].append(r)

    tbl = Table(title="Aggregate latency & tokens (this run)", box=box.ROUNDED)
    tbl.add_column("Model", style="magenta")
    tbl.add_column("n", justify="right")
    for q in ("p50", "p90", "p95", "p99"):
        tbl.add_column(q, justify="right")
    tbl.add_column("Σ in/out tok", justify="right")

    blend = os.environ.get("EVAL_USD_PER_MILLION_TOKENS", "").strip()
    if blend:
        tbl.add_column("Est. USD*", justify="right")

    for model in sorted(by_model.keys()):
        runs = by_model[model]
        lat = sorted(float(x["latency_ms"]) for x in runs)
        row = [
            model,
            str(len(runs)),
        ]
        for q in (0.50, 0.90, 0.95, 0.99):
            v = _percentile(lat, q)
            row.append(f"{v / 1000:.1f}s" if v is not None else "—")
        tin = sum(int(x.get("input_tokens", 0)) for x in runs)
        tout = sum(int(x.get("output_tokens", 0)) for x in runs)
        row.append(f"{tin:,}/{tout:,}")
        if blend:
            try:
                row.append(f"${float(blend) * (tin + tout) / 1e6:.4f}")
            except ValueError:
                row.append("—")
        tbl.add_row(*row)

    console.print(tbl)
    console.print(
        "[dim]Full report: python eval_report.py  |  "
        "optional cost: EVAL_USD_PER_MILLION_TOKENS=0.075 python eval.py[/dim]"
    )


def main():
    parser = argparse.ArgumentParser(description="Bug Squashing Agent — Batch Evaluator")
    parser.add_argument("--models", nargs="+", default=ALL_MODELS,
                        choices=ALL_MODELS, help="Models to evaluate")
    parser.add_argument("--cases", nargs="+", default=None,
                        help="Case IDs to run (default: all)")
    parser.add_argument("--dry-run", action="store_true",
                        help="List what would run, without executing")
    args = parser.parse_args()

    console = Console()
    console.print(Panel.fit(
        "[bold blue]🔬 Bug Squashing Agent — Batch Evaluator[/bold blue]\n"
        "[dim]Runs all cases × models and writes metrics to logs/eval_results.jsonl[/dim]"
    ))

    cases = args.cases or list_all_cases()
    if not cases:
        console.print("[red]No cases found in dataset/cases/[/red]")
        sys.exit(1)

    total_runs = len(cases) * len(args.models)
    console.print(f"\n[bold]Plan:[/bold] {len(cases)} cases × {len(args.models)} models = [cyan]{total_runs}[/cyan] runs")
    console.print(f"Cases: {', '.join(cases)}")
    console.print(f"Models: {', '.join(args.models)}\n")

    if args.dry_run:
        console.print("[yellow]--dry-run: exiting without running.[/yellow]")
        return

    results = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("[green]Evaluating...", total=total_runs)

        for model_name in args.models:
            for case_id in cases:
                progress.update(task, description=f"[green]{model_name}[/green] / [cyan]{case_id}[/cyan]")
                result = run_single_case(case_id, model_name, console)
                results.append(result)
                write_result(result)
                status = "✅" if result["passed"] else "❌"
                console.print(
                    f"  {status} {model_name:10s}  {case_id}  "
                    f"{result['latency_ms']/1000:.1f}s  "
                    f"steps={result['steps']}"
                    + (f"  error={result.get('error', '')[:50]}" if result.get("error") else "")
                )
                progress.advance(task)

    console.print()
    print_summary_table(results, console)
    print_aggregate_metrics(results, console)


if __name__ == "__main__":
    main()
