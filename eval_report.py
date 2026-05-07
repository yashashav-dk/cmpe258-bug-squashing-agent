#!/usr/bin/env python3
"""
eval_report.py — Read logs/eval_results.jsonl and print a formatted report.

Usage:
    python3 eval_report.py
    python3 eval_report.py --file path/to/eval_results.jsonl
"""
from __future__ import annotations

import argparse
import json
import math
import os
from collections import defaultdict

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "logs", "eval_results.jsonl")


def _percentile(sorted_vals: list[float], q: float) -> float | None:
    """q in [0,1]; linear interpolation between closest ranks."""
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


def load_results(path: str) -> list:
    results = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                results.append(json.loads(line))
    return results


def main():
    parser = argparse.ArgumentParser(description="Bug Squashing Agent — Eval Report")
    parser.add_argument("--file", default=RESULTS_PATH, help="Path to eval_results.jsonl")
    args = parser.parse_args()

    console = Console()

    if not os.path.exists(args.file):
        console.print(f"[red]Results file not found: {args.file}[/red]")
        console.print("[dim]Run eval.py first to generate results.[/dim]")
        return

    results = load_results(args.file)
    if not results:
        console.print("[yellow]No results found in file.[/yellow]")
        return

    console.print(Panel.fit(
        f"[bold blue]📊 Bug Squashing Agent — Evaluation Report[/bold blue]\n"
        f"[dim]Source: {args.file} | {len(results)} runs[/dim]"
    ))

    # === Per-model summary ===
    by_model = defaultdict(list)
    for r in results:
        by_model[r["model"]].append(r)

    model_table = Table(title="Per-Model Summary", box=box.ROUNDED, show_lines=True)
    model_table.add_column("Model", style="magenta", no_wrap=True)
    model_table.add_column("Cases Run", justify="right")
    model_table.add_column("Passed", justify="right", style="green")
    model_table.add_column("Pass Rate", justify="right")
    model_table.add_column("Avg Steps", justify="right")
    model_table.add_column("Avg Latency", justify="right")
    model_table.add_column("p50", justify="right")
    model_table.add_column("p90", justify="right")
    model_table.add_column("p95", justify="right")
    model_table.add_column("p99", justify="right")
    model_table.add_column("Tokens In/Out", justify="right")
    model_table.add_column("Est. USD*", justify="right")

    blend_rate = os.environ.get("EVAL_USD_PER_MILLION_TOKENS", "").strip()

    for model, runs in sorted(by_model.items()):
        passed = sum(1 for r in runs if r["passed"])
        total = len(runs)
        pass_rate = f"{100*passed/total:.1f}%" if total else "N/A"
        steps = [r["steps"] for r in runs]
        avg_steps = f"{sum(steps)/len(steps):.1f}" if steps else "N/A"
        latencies = sorted(float(r["latency_ms"]) for r in runs)

        def fmt_p(q: float) -> str:
            v = _percentile(latencies, q)
            return f"{v / 1000:.1f}s" if v is not None else "N/A"

        avg_lat = f"{sum(latencies) / len(latencies) / 1000:.1f}s" if latencies else "N/A"
        p50 = fmt_p(0.50)
        p90 = fmt_p(0.90)
        p95 = fmt_p(0.95)
        p99 = fmt_p(0.99)

        tin = sum(int(r.get("input_tokens", 0)) for r in runs)
        tout = sum(int(r.get("output_tokens", 0)) for r in runs)
        tok_str = f"{tin:,}/{tout:,}"

        if blend_rate:
            try:
                rate = float(blend_rate)
                usd = rate * (tin + tout) / 1_000_000.0
                usd_str = f"${usd:.4f}"
            except ValueError:
                usd_str = "bad EVAL_*"
        else:
            usd_str = "—"

        model_table.add_row(
            model, str(total), str(passed), pass_rate, avg_steps, avg_lat, p50, p90, p95, p99, tok_str, usd_str
        )

    console.print(model_table)
    console.print(
        "[dim]* Est. USD = (input+output tokens)/1e6 × $EVAL_USD_PER_MILLION_TOKENS when set "
        "(blended placeholder; omit for local/Ollama).[/dim]"
    )

    # === Per-tier summary ===
    def tier_for(case_id: str) -> str:
        num = int(case_id.split("_")[1])
        if num <= 5:
            return "existing"
        elif num <= 18:
            return "Tier 1 – Syntax/Type"
        elif num <= 36:
            return "Tier 2 – Logic/Algorithmic"
        else:
            return "Tier 3 – Contextual/Scope"

    by_tier = defaultdict(list)
    for r in results:
        by_tier[tier_for(r["case_id"])].append(r)

    tier_table = Table(title="Per-Tier Pass Rate", box=box.ROUNDED, show_lines=True)
    tier_table.add_column("Tier", style="cyan")
    tier_table.add_column("Cases", justify="right")
    tier_table.add_column("Passed", justify="right", style="green")
    tier_table.add_column("Pass Rate", justify="right")

    tier_order = ["existing", "Tier 1 – Syntax/Type", "Tier 2 – Logic/Algorithmic", "Tier 3 – Contextual/Scope"]
    for tier in tier_order:
        runs = by_tier.get(tier, [])
        if not runs:
            continue
        passed = sum(1 for r in runs if r["passed"])
        total = len(runs)
        tier_table.add_row(tier, str(total), str(passed), f"{100*passed/total:.1f}%")

    console.print(tier_table)

    # === Full case breakdown ===
    detail_table = Table(title="Full Case Breakdown", box=box.SIMPLE, show_lines=False)
    detail_table.add_column("Case", style="dim cyan", no_wrap=True)
    detail_table.add_column("Tier", style="dim")
    for model in sorted(by_model.keys()):
        detail_table.add_column(model, justify="center")

    cases = sorted(set(r["case_id"] for r in results))
    result_map = {(r["model"], r["case_id"]): r for r in results}

    for case_id in cases:
        row = [case_id, tier_for(case_id)]
        for model in sorted(by_model.keys()):
            r = result_map.get((model, case_id))
            if r is None:
                row.append("[dim]-[/dim]")
            elif r["passed"]:
                row.append("[green]✅[/green]")
            else:
                row.append("[red]❌[/red]")
        detail_table.add_row(*row)

    console.print(detail_table)

    total_passed = sum(1 for r in results if r["passed"])
    console.print(f"\n[bold]Overall pass rate: [green]{total_passed}[/green]/[cyan]{len(results)}[/cyan] ({100*total_passed//len(results) if results else 0}%)[/bold]\n")


if __name__ == "__main__":
    main()
