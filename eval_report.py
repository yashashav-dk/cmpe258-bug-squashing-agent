#!/usr/bin/env python3
"""
eval_report.py — Read logs/eval_results.jsonl and print a formatted report.

Usage:
    python3 eval_report.py
    python3 eval_report.py --file path/to/eval_results.jsonl
"""
import argparse
import json
import os
from collections import defaultdict

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

RESULTS_PATH = os.path.join(os.path.dirname(__file__), "logs", "eval_results.jsonl")


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
    model_table.add_column("p50 Latency", justify="right")
    model_table.add_column("p90 Latency", justify="right")

    for model, runs in sorted(by_model.items()):
        passed = sum(1 for r in runs if r["passed"])
        total = len(runs)
        pass_rate = f"{100*passed/total:.1f}%" if total else "N/A"
        steps = [r["steps"] for r in runs]
        avg_steps = f"{sum(steps)/len(steps):.1f}" if steps else "N/A"
        latencies = sorted(r["latency_ms"] for r in runs)
        avg_lat = f"{sum(latencies)/len(latencies)/1000:.1f}s" if latencies else "N/A"
        p50 = f"{latencies[len(latencies)//2]/1000:.1f}s" if latencies else "N/A"
        p90 = f"{latencies[int(len(latencies)*0.9)]/1000:.1f}s" if latencies else "N/A"
        model_table.add_row(model, str(total), str(passed), pass_rate, avg_steps, avg_lat, p50, p90)

    console.print(model_table)

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
