#!/usr/bin/env python3
"""
main.py — Bug Squashing Agent (Interactive CLI)
Inspired by Claude Code's interface.
"""
import argparse
import os
import sys
import time

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.status import Status
from rich.markdown import Markdown
from rich.text import Text

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
    else:
        raise ValueError(f"Unknown model: {model_name!r}. Choose from: gemini, qwen, minimax")


def interactive_mode(model_name: str):
    console = Console()
    console.print(Panel.fit("[bold blue]🤖 CMPE 258 Bug Squashing Agent[/bold blue]\n[green]Interactive Mode via Claude Code architecture[/green]"))
    
    model = get_model(model_name)
    console.print(f"[dim]Model initialized: {model.name()}[/dim]")
    
    planner = Planner(model=model, max_steps=20)
    memory = Memory()

    while True:
        try:
            choice = Prompt.ask("\nChoose an option", choices=["1", "2", "3", "q"], default="1")
        except KeyboardInterrupt:
            break
            
        if choice == "q":
            break
            
        case_id = Prompt.ask("Enter case ID (e.g. case_001)")
        case_dir = os.path.join(CASES_DIR, case_id)
        if not os.path.isdir(case_dir):
            console.print(f"[red]Case {case_id} not found in {CASES_DIR}[/red]")
            continue
            
        buggy_path = os.path.join(case_dir, "buggy.py")
        if not os.path.exists(buggy_path):
            console.print(f"[red]buggy.py not found for case {case_id}[/red]")
            continue
            
        with open(buggy_path) as f:
            buggy_code = f.read()

        msg = f"Investigate this bug in {case_id}:\n```python\n{buggy_code}\n```\nRun tests and fix it via tools."
        
        console.print("\n[bold cyan]Starting Autonomous Resolution Loop...[/bold cyan]")
        
        # Override planner's history for a fresh start or continued execution
        planner.history.append({"role": "user", "content": msg})
        
        with Status("[bold green]Agent is thinking...", spinner="dots") as status:
            for step in range(planner.max_steps):
                status.update(f"[bold green]Agent Step {step+1}/{planner.max_steps}...[/bold green]")
                
                response = planner.model.chat(
                    messages=planner.history,
                    tools=planner.model.chat.__defaults__[0] if hasattr(planner.model.chat, '__defaults__') else None,
                    system_instruction=planner.model.chat.__code__.co_consts[0] if False else "" 
                )
                
                # In main we are just delegating back to the Planner autonomous loop technically, 
                # but doing it here directly allows rich integration.
                # Actually, let's just let planner run and optionally yield / print.
                break # We will just use the planner autonomous loop directly to keep it clean.
                
        # To make it beautiful, we'll patch the planner's print locally or just capture output.
        # For simplicity, we just use the planner.run_autonomous_loop.
        from utils_stub import run_with_rich
        run_with_rich(planner, msg, console)
        
        # Dream system consolidation
        console.print("\n[bold purple]Consolidating Memory / Dreaming...[/bold purple]")
        dream_text = memory.consolidate_dream(planner.history, planner.model)
        console.print(Panel(dream_text, title="Dream Consolidation", border_style="purple"))

def run_case_interactive(case_id: str, model_name: str):
    console = Console()
    console.print(Panel.fit("[bold blue]🤖 CMPE 258 Bug Squashing Agent[/bold blue]\n[green]Autonomous Mode via Claude Code architecture[/green]"))
    
    model = get_model(model_name)
    planner = Planner(model=model, max_steps=15)
    memory = Memory()
    
    case_dir = os.path.join(CASES_DIR, case_id)
    buggy_path = os.path.join(case_dir, "buggy.py")
    if not os.path.isdir(case_dir):
        console.print(f"[red]Error: case directory not found: {case_dir}[/red]")
        sys.exit(1)
        
    with open(buggy_path) as f:
        buggy_code = f.read()

    msg = f"Investigate this bug in {case_id}: \n```python\n{buggy_code}\n```\nRun `pytest test_buggy.py` in `{case_dir}`. Fix it using tools."
    
    console.print(f"[bold cyan]Case: {case_id} | Model: {model.name()}[/bold cyan]")
    
    with Status("[bold green]Agent is thinking...", spinner="dots") as status:
        # Instead of `run_autonomous_loop` printing directly, we could capture stdout but we'll let it print.
        result = planner.run_autonomous_loop(msg)
        
    console.print(f"\n[bold green]Final Result:[/bold green]\n{result}")
    
    # Dream consolidation
    console.print("\n[bold purple]Consolidating Memory / Dreaming...[/bold purple]")
    dream_text = memory.consolidate_dream(planner.history, planner.model)
    console.print(Panel(dream_text, title="Dream Consolidation", border_style="purple"))

def main():
    parser = argparse.ArgumentParser(description="Bug Squashing Agent Interactive CLI")
    parser.add_argument("--case", required=False, help="Case ID (e.g. case_001) or empty for REPL")
    parser.add_argument("--model", default="gemini", choices=["gemini", "qwen", "minimax"])
    args = parser.parse_args()
    
    if args.case:
        run_case_interactive(case_id=args.case, model_name=args.model)
    else:
        # Provide interactive REPL
        run_case_interactive(case_id="case_001", model_name=args.model)

if __name__ == "__main__":
    main()
