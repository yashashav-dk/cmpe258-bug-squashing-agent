from rich.console import Console
from rich.panel import Panel
from rich.status import Status

def run_with_rich(planner, msg: str, console: Console):
    """
    Simulates the rich interactive stream of the agent reasoning.
    """
    planner.history.append({"role": "user", "content": msg})
    
    with Status("[bold green]Agent starting reasoning...", spinner="dots") as status:
        for step in range(planner.max_steps):
            status.update(f"[bold green]Agent Step {step+1}/{planner.max_steps}...[/bold green]")
            
            response = planner.model.chat(
                messages=planner.history,
                tools=planner.model.chat.__defaults__[0] if hasattr(planner.model.chat, '__defaults__') else None,
                system_instruction=planner.model.chat.__code__.co_consts[0] if False else "" 
            )
            
            assistant_msg = {
                "role": "assistant",
                "content": response.text,
            }
            if response.tool_calls:
                assistant_msg["tool_calls"] = response.tool_calls
                
            planner.history.append(assistant_msg)

            if response.text:
                console.print(f"\n[bold cyan]Assistant:[/bold cyan] {response.text}")
                
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    name = tool_call["name"]
                    args = tool_call["arguments"]
                    
                    console.print(f"[bold yellow]🔧 Tool Call:[/bold yellow] {name}({args})")
                    
                    tool_result = ""
                    from agent.tools_impl import AGENT_TOOLS
                    for tool_fn in AGENT_TOOLS:
                        if tool_fn.__name__ == name:
                            try:
                                tool_result = tool_fn(**args)
                            except Exception as e:
                                tool_result = f"Tool execution failed: {e}"
                            break
                    
                    console.print(Panel(str(tool_result)[:300] + "...", title=f"{name} output", border_style="yellow"))
                    planner.history.append({
                        "role": "tool",
                        "name": name,
                        "content": str(tool_result)
                    })
            else:
                if "RESOLVED" in response.text or "All tests pass" in response.text:
                    console.print("\n[bold green]✅ Agent successfully resolved the bug![/bold green]")
                    return response.text
                    
    console.print("\n[bold red]❌ Agent failed to resolve within max steps.[/bold red]")
    return "Failed."
