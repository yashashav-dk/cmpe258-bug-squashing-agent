#!/usr/bin/env python3
"""
main.py — Bug Squashing Agent (Interactive CLI)
Inspired by Claude Code's interface.
"""
import argparse
import os
import sys

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status
from rich.markdown import Markdown

from config import CASES_DIR, LOG_PATH
from logger import Logger
from agent.memory import Memory
from agent.planner import Planner


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
        raise ValueError(f"Unknown model: {model_name!r}. Choose from: gemini, qwen, minimax, gemma4")


def run_case(case_id: str, model_name: str, console: Console):
    """Run the agent on a single case."""
    case_dir = os.path.join(CASES_DIR, case_id)
    buggy_path = os.path.join(case_dir, "buggy.py")

    if not os.path.isdir(case_dir):
        console.print(f"[red]Error: case directory not found: {case_dir}[/red]")
        return

    if not os.path.exists(buggy_path):
        console.print(f"[red]Error: buggy.py not found for case {case_id}[/red]")
        return

    with open(buggy_path) as f:
        buggy_code = f.read()

    model = get_model(model_name)
    console.print(f"[dim]Model initialized: {model.name()}[/dim]")

    planner = Planner(model=model, max_steps=15)
    memory = Memory()

    msg = (
        f"Investigate this bug in {case_id}:\n```python\n{buggy_code}\n```\n"
        f"Run `pytest test_buggy.py` in `{case_dir}`. Fix it using tools."
    )

    console.print(f"\n[bold cyan]Case: {case_id} | Model: {model.name()}[/bold cyan]")
    console.print("[bold cyan]Starting Autonomous Resolution Loop...[/bold cyan]\n")

    result = ""
    with Status("[bold green]Agent is thinking...", spinner="dots", console=console) as status:
        # We run in the same thread but let planner print its own output.
        # Status will be briefly suspended by direct prints, which is acceptable.
        result = planner.run_autonomous_loop(msg)

    console.print(f"\n[bold green]Final Result:[/bold green]\n{result}")

    # Dream system consolidation
    console.print("\n[bold purple]Consolidating Memory / Dreaming...[/bold purple]")
    try:
        dream_text = memory.consolidate_dream(planner.history, planner.model)
        console.print(Panel(dream_text, title="Dream Consolidation", border_style="purple"))
    except Exception as e:
        console.print(f"[yellow]Dream consolidation skipped: {e}[/yellow]")


def interactive_mode(model_name: str):
    """REPL-style interactive loop to pick and run cases."""
    console = Console()
    console.print(Panel.fit(
        "[bold blue]🤖 CMPE 258 Bug Squashing Agent[/bold blue]\n"
        "[green]Interactive Mode via Claude Code architecture[/green]"
    ))

    while True:
        try:
            choice = Prompt.ask(
                "\n[bold]Options[/bold]: [1] Run a case  [q] Quit",
                choices=["1", "q"],
                default="1",
            )
        except KeyboardInterrupt:
            console.print("\n[dim]Exiting.[/dim]")
            break

        if choice == "q":
            break

        # List available cases
        if os.path.isdir(CASES_DIR):
            cases = sorted(os.listdir(CASES_DIR))
            console.print(f"[dim]Available cases: {', '.join(cases)}[/dim]")

        case_id = Prompt.ask("Enter case ID (e.g. case_001)")
        run_case(case_id, model_name, console)


def main():
    parser = argparse.ArgumentParser(description="Bug Squashing Agent Interactive CLI")
    parser.add_argument("--case", required=False, help="Case ID (e.g. case_001). Omit for interactive REPL.")
    parser.add_argument("--model", default="gemma4", choices=["gemini", "qwen", "minimax", "gemma4"])
    args = parser.parse_args()

    console = Console()
    console.print(Panel.fit(
        "[bold blue]🤖 CMPE 258 Bug Squashing Agent[/bold blue]\n"
        "[green]Autonomous Mode via Claude Code architecture[/green]"
    ))

    if args.case:
        run_case(case_id=args.case, model_name=args.model, console=console)
    else:
        interactive_mode(model_name=args.model)


if __name__ == "__main__":
    main()
