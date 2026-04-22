from rich.console import Console
from rich.panel import Panel
from rich.status import Status

from agent.tools_impl import AGENT_TOOLS
from agent.planner import SYSTEM_PROMPT


def run_with_rich(planner, msg: str, console: Console) -> str:
    """
    Run the planner's autonomous loop with Rich UI rendering.
    NOTE: Assumes the user message has NOT yet been appended to planner.history.
    """
    planner.history.append({"role": "user", "content": msg})

    with Status("[bold green]Agent starting reasoning...", spinner="dots", console=console) as status:
        for step in range(planner.max_steps):
            status.update(f"[bold green]Agent Step {step+1}/{planner.max_steps}...[/bold green]")

            response = planner.model.chat(
                messages=planner.history,
                tools=AGENT_TOOLS,
                system_instruction=SYSTEM_PROMPT,
            )

            response_text = response.text or ""

            assistant_msg = {
                "role": "assistant",
                "content": response_text,
            }
            if response.tool_calls:
                assistant_msg["tool_calls"] = response.tool_calls

            planner.history.append(assistant_msg)

            if response_text:
                console.print(f"\n[bold cyan]Assistant:[/bold cyan] {response_text}")

            if response.tool_calls:
                for tool_call in response.tool_calls:
                    name = tool_call["name"]
                    args = tool_call["arguments"]

                    console.print(f"[bold yellow]🔧 Tool Call:[/bold yellow] {name}({args})")

                    tool_result = ""
                    for tool_fn in AGENT_TOOLS:
                        if tool_fn.__name__ == name:
                            try:
                                tool_result = tool_fn(**args)
                            except Exception as e:
                                tool_result = f"Tool execution failed: {e}"
                            break

                    preview = str(tool_result)[:300]
                    if len(str(tool_result)) > 300:
                        preview += "..."
                    console.print(Panel(preview, title=f"{name} output", border_style="yellow"))
                    planner.history.append({
                        "role": "tool",
                        "name": name,
                        "content": str(tool_result),
                    })
            else:
                if "RESOLVED" in response_text or "All tests pass" in response_text:
                    console.print("\n[bold green]✅ Agent successfully resolved the bug![/bold green]")
                    return response_text

    console.print("\n[bold red]❌ Agent failed to resolve within max steps.[/bold red]")
    return "Failed."
