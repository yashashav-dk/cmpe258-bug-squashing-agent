#!/usr/bin/env python3
"""
main.py — Benchmark-first interactive CLI.
"""
import argparse
import os

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status

from benchmark.ui_service import (
    analyze,
    build_manifest,
    list_manifests,
    run_pipeline,
)
from config import CASES_DIR, LOG_PATH
from agent.case_runtime import run_case_with_pec
from logger import Logger


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
    elif model_name in ("gemini_or", "qwen_or"):
        from models.openrouter import OpenRouterModel, OPENROUTER_MODELS
        return OpenRouterModel(OPENROUTER_MODELS[model_name])
    else:
        raise ValueError(f"Unknown model: {model_name!r}. Choose from: gemini, qwen, minimax, gemma4, gemini_or, qwen_or")


def run_case(case_id: str, model_name: str, console: Console, max_steps: int = 15):
    """Case-level execution path (Planner->Executor->Critic)."""
    model = get_model(model_name)
    run_logger = Logger(LOG_PATH)
    run_logger.log(
        event="run_start",
        case_id=case_id,
        data={"model": model_name, "mode": "run_case"},
    )
    console.print(f"[dim]Model initialized: {model.name()}[/dim]")
    case_dir = os.path.join(CASES_DIR, case_id)
    buggy_path = os.path.join(case_dir, "buggy.py")

    if not os.path.isdir(case_dir):
        console.print(f"[red]Error: case directory not found: {case_dir}[/red]")
        return

    if not os.path.exists(buggy_path):
        console.print(f"[red]Error: buggy.py not found for case {case_id}[/red]")
        return

    console.print(f"\n[bold cyan]Case: {case_id} | Model: {model.name()}[/bold cyan]")
    console.print("[bold cyan]Starting Planner->Executor->Critic loop...[/bold cyan]\n")

    run_result = None
    with Status("[bold green]Agent is thinking...", spinner="dots", console=console) as status:
        run_result = run_case_with_pec(
            case_id=case_id,
            model=model,
            cases_root=CASES_DIR,
            max_steps=max_steps,
            logger=run_logger,
        )

    console.print(f"\n[bold green]Final Result:[/bold green]\n{run_result.summary_text}")
    if run_result.timeline:
        console.print(
            Panel(
                "\n".join(f"- {line}" for line in run_result.timeline),
                title="PEC Loop Trace",
                border_style="cyan",
            )
        )
    run_logger.log(
        event="run_end",
        case_id=case_id,
        data={
            "model": model_name,
            "result_preview": run_result.summary_text[:300],
            "planner_stats": run_result.planner_stats,
            "resolved": run_result.resolved,
            "iterations": run_result.iterations,
        },
    )

    if run_result.final_traceback:
        console.print(Panel(run_result.final_traceback[:1200], title="Final Traceback", border_style="yellow"))


def _print_report(console: Console, report: dict, report_path: str) -> None:
    if not report:
        console.print(f"[yellow]No report rows found in {report_path}[/yellow]")
        return
    lines = []
    for model, stats in report.items():
        lines.append(
            f"- {model}: runs={stats.get('runs', 0)} "
            f"resolved={stats.get('resolved', 0)} pass_rate={stats.get('pass_rate', 0.0):.2f}"
        )
    console.print(Panel("\n".join(lines), title=f"Benchmark Report ({report_path})", border_style="green"))


def _run_manifest_pipeline(
    console: Console,
    manifest_path: str,
    models: str,
    output_path: str,
    report_output: str,
    max_steps: int,
    timeout_s: int,
    repetitions: int,
) -> None:
    with Status("[bold green]Running benchmark matrix + analyze...", spinner="dots", console=console):
        result = run_pipeline(
            manifest=manifest_path,
            models=models,
            output=output_path,
            report_output=report_output,
            max_steps=max_steps,
            timeout_s=timeout_s,
            repetitions=repetitions,
        )
    console.print(f"[green]Results:[/green] {result.results_path}")
    console.print(f"[green]Report:[/green] {result.report_path}")
    console.print(f"[green]UI Report:[/green] {result.ui_report_path}")
    _print_report(console, result.report, result.report_path)


def interactive_mode(model_name: str, max_steps: int, timeout_s: int, repetitions: int):
    """REPL-style benchmark workflow."""
    console = Console()
    console.print(Panel.fit(
        "[bold blue]🤖 CMPE 258 Bug Squashing Agent[/bold blue]\n"
        "[green]Benchmark Manifest Mode[/green]"
    ))

    while True:
        try:
            choice = Prompt.ask(
                "\n[bold]Options[/bold]: [1] Run manifest  [2] Build+Run  [3] Analyze latest  [4] List manifests  [q] Quit",
                choices=["1", "2", "3", "4", "q"],
                default="1",
            )
        except KeyboardInterrupt:
            console.print("\n[dim]Exiting.[/dim]")
            break

        if choice == "q":
            break

        if choice == "4":
            manifests = list_manifests()
            if manifests:
                console.print("[dim]Available manifests:[/dim]")
                for path in manifests:
                    console.print(f"[dim]- {path}[/dim]")
            else:
                console.print("[yellow]No manifests found under benchmark/manifests[/yellow]")
            continue

        if choice == "3":
            report_out = Prompt.ask("Report output", default="logs/benchmark_report.json")
            proc = analyze(input_path="latest", output=report_out)
            if proc.returncode != 0:
                console.print(f"[red]Analyze failed[/red]\n{proc.stdout}\n{proc.stderr}")
                continue
            console.print(proc.stdout.strip())
            continue

        if choice == "2":
            historical = Prompt.ask(
                "Historical source",
                default="benchmark/data/historical_cases.sample.jsonl",
            )
            synthetic = Prompt.ask(
                "Synthetic source",
                default="benchmark/data/synthetic_templates.sample.jsonl",
            )
            manifest_out = Prompt.ask(
                "Manifest output",
                default="benchmark/manifests/pilot_hybrid.jsonl",
            )
            build = build_manifest(
                historical_source=historical,
                synthetic_source=synthetic,
                output=manifest_out,
            )
            if build.returncode != 0:
                console.print(f"[red]Manifest build failed[/red]\n{build.stdout}\n{build.stderr}")
                continue
            console.print(build.stdout.strip())
            manifest = manifest_out
        else:
            manifests = list_manifests()
            default_manifest = manifests[0] if manifests else "benchmark/manifests/pilot_hybrid.jsonl"
            manifest = Prompt.ask("Manifest path", default=default_manifest)

        output_path = Prompt.ask("Results output", default="logs/benchmark_results.jsonl")
        report_output = Prompt.ask("Report output", default="logs/benchmark_report.json")
        models = Prompt.ask("Models (comma separated)", default=model_name)
        try:
            _run_manifest_pipeline(
                console=console,
                manifest_path=manifest,
                models=models,
                output_path=output_path,
                report_output=report_output,
                max_steps=max_steps,
                timeout_s=timeout_s,
                repetitions=repetitions,
            )
        except Exception as exc:
            console.print(f"[red]Benchmark run failed:[/red] {exc}")


def main():
    parser = argparse.ArgumentParser(description="Bug Squashing Agent Benchmark CLI")
    parser.add_argument("--case", required=False, help="Case ID for case-folder mode (Planner->Executor->Critic).")
    parser.add_argument("--manifest", required=False, help="Run benchmark directly for one manifest and exit.")
    parser.add_argument("--model", default="gemma4", help="Default model/model-list for benchmark execution.")
    parser.add_argument("--output", default="logs/benchmark_results.jsonl", help="Benchmark results JSONL path.")
    parser.add_argument("--report-output", default="logs/benchmark_report.json", help="Benchmark report output path.")
    parser.add_argument(
        "--max-steps",
        type=int,
        default=15,
        help="PEC max iterations (case-folder mode and benchmark planner).",
    )
    parser.add_argument("--timeout-s", type=int, default=180, help="Timeout used by benchmark runtime (seconds).")
    parser.add_argument("--repetitions", type=int, default=1, help="Benchmark repetitions.")
    args = parser.parse_args()

    console = Console()
    console.print(Panel.fit(
        "[bold blue]🤖 CMPE 258 Bug Squashing Agent[/bold blue]\n"
        "[green]Autonomous Resolution Mode[/green]"
    ))

    if args.case:
        run_case(case_id=args.case, model_name=args.model, console=console, max_steps=args.max_steps)
        return

    if args.manifest:
        _run_manifest_pipeline(
            console=console,
            manifest_path=args.manifest,
            models=args.model,
            output_path=args.output,
            report_output=args.report_output,
            max_steps=args.max_steps,
            timeout_s=args.timeout_s,
            repetitions=args.repetitions,
        )
        return

    interactive_mode(
        model_name=args.model,
        max_steps=args.max_steps,
        timeout_s=args.timeout_s,
        repetitions=args.repetitions,
    )


if __name__ == "__main__":
    main()
