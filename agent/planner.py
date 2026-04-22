import json
import os
from typing import List, Dict, Any
from agent.memory import Memory
from models.base import BaseModel
from agent.tools_impl import AGENT_TOOLS

SYSTEM_PROMPT = """\
You are an autonomous expert Python debugging agent. Your goal is to investigate buggy code, write fixes, and ensure tests pass.
You have access to tools that allow you to read files, edit files, and run bash commands (such as running pytest).
Investigate the error, use tools to explore the codebase and apply a fix, and verify it with pytest.
When the tests pass, output a summary of what you did and say 'RESOLVED'.
"""

class Planner:
    def __init__(self, model: BaseModel, few_shot_dir: str = "", max_steps: int = 15):
        self.model = model
        self.max_steps = max_steps
        self.history: List[Dict[str, Any]] = []

    def plan(self, buggy_code: str, traceback: str, memory: Memory) -> dict:
        """
        Legacy entry point for compatibility if needed. It triggers the Autonomous loop.
        In the new architecture, we prefer `run_autonomous_loop()`.
        """
        msg = f"Buggy Code:\n```python\n{buggy_code}\n```\nTraceback:\n{traceback}\nFix the bug."
        self.run_autonomous_loop(msg)
        # Mocking legacy patch response format
        return {"file": "buggy.py", "line_range": [0,0], "root_cause": "Fixed autonomously", "proposed_fix": "Applied via tools"}

    def run_autonomous_loop(self, user_objective: str) -> str:
        self.history.append({"role": "user", "content": user_objective})
        
        for step in range(self.max_steps):
            response = self.model.chat(
                messages=self.history,
                tools=AGENT_TOOLS,
                system_instruction=SYSTEM_PROMPT
            )
            
            response_text = response.text or ""

            assistant_msg: Dict[str, Any] = {
                "role": "assistant",
                "content": response_text,
            }
            if response.tool_calls:
                assistant_msg["tool_calls"] = response.tool_calls
                
            self.history.append(assistant_msg)

            if response_text:
                print(f"[Agent]: {response_text}")
                
            if response.tool_calls:
                for tool_call in response.tool_calls:
                    name = tool_call["name"]
                    args = tool_call["arguments"]
                    
                    print(f"  [Tool Call]: {name}({args})")
                    
                    tool_result = ""
                    # Dispatch to corresponding python function
                    for tool_fn in AGENT_TOOLS:
                        if tool_fn.__name__ == name:
                            try:
                                tool_result = tool_fn(**args)
                            except Exception as e:
                                tool_result = f"Tool execution failed: {e}"
                            break
                    
                    print(f"  [Tool Output]:\n{str(tool_result)[:200]}...")
                    self.history.append({
                        "role": "tool",
                        "name": name,
                        "content": str(tool_result)
                    })
            else:
                if "RESOLVED" in response_text or "All tests pass" in response_text:
                    return response_text
        
        return "Max steps reached without resolving the bug."


