import json
import os
import re
from typing import List, Dict, Any
from agent.memory import Memory
from models.base import BaseModel
from agent.tools_impl import AGENT_TOOLS
from logger import Logger

SYSTEM_PROMPT = """\
You are an autonomous expert Python debugging agent. Your goal is to investigate buggy code, write fixes, and ensure tests pass.
You have access to tools that allow you to read files, edit files, and run bash commands (such as running pytest).
If specialized verifier tools are available (run_target_test, run_regression_test), use them instead of ad-hoc shell test commands.
Investigate the error, use tools to explore the codebase and apply a fix, and verify it with pytest.
When the tests pass, output a summary of what you did and say 'RESOLVED'.
"""

PATCH_PLAN_SYSTEM_PROMPT = """\
You are the Planner in a Planner-Executor-Critic bug-fixing loop.
Return ONLY a raw JSON object with keys:
- file: string (relative path to modify; when the user names an exact path, use that path verbatim)
- line_range: [start_line, end_line] (1-indexed inclusive; both integers)
- root_cause: string
- proposed_fix: string (replacement text for the range)
Do not include markdown fences or any extra text.
"""

class Planner:
    def __init__(
        self,
        model: BaseModel,
        few_shot_dir: str = "",
        max_steps: int = 15,
        logger: Logger = None,
        case_id: str = "unknown_case",
        tools=None,
        tool_registry=None,
    ):
        self.model = model
        self.max_steps = max_steps
        self.history: List[Dict[str, Any]] = []
        self.logger = logger
        self.case_id = case_id
        self._tools = tools if tools is not None else AGENT_TOOLS
        self._tool_registry = (
            dict(tool_registry)
            if tool_registry is not None
            else {tool_fn.__name__: tool_fn for tool_fn in self._tools}
        )
        self._session_stats: Dict[str, float] = {
            "steps": 0,
            "tool_calls": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_latency_ms": 0.0,
        }
        self._last_tool_signature = None
        self._last_tool_result = ""
        self._target_test_command = ""
        self._phase = "investigate"
        self._consecutive_noop_edits = 0
        self._repeated_failing_skips = 0
        self._max_consecutive_noop_edits = 3
        self._max_repeated_failing_skips = 3

    def _log(self, event: str, data: Dict[str, Any]) -> None:
        if self.logger:
            self.logger.log(event=event, case_id=self.case_id, data=data)

    def session_stats(self) -> Dict[str, float]:
        return dict(self._session_stats)

    @staticmethod
    def _is_tool_failure(result: str) -> bool:
        prefixes = ("Error:", "Tool execution failed:", "Unknown tool:")
        return any(str(result).startswith(prefix) for prefix in prefixes)

    @staticmethod
    def _extract_target_test_command(objective: str) -> str:
        match = re.search(r"Run `([^`]+)`", objective)
        return match.group(1).strip() if match else ""

    @staticmethod
    def _exit_code_from_tool_output(output: str) -> int:
        match = re.search(r"Exit Code:\s*(-?\d+)", output)
        if not match:
            return -1
        return int(match.group(1))

    @staticmethod
    def _classify_tool_result(name: str, content: str) -> Dict[str, Any]:
        status = "error"
        kind = "error"
        if str(content).startswith("File updated successfully."):
            status = "ok"
            kind = "edit_applied"
        elif str(content).startswith("No-op:"):
            status = "ok"
            kind = "edit_noop"
        elif name == "run_bash":
            status = "ok" if Planner._exit_code_from_tool_output(content) == 0 else "error"
            kind = "command_result"
        elif not Planner._is_tool_failure(content):
            status = "ok"
            kind = "tool_result"
        return {"status": status, "kind": kind, "content": str(content)}

    @staticmethod
    def _extract_json_object(raw: str) -> str:
        text = (raw or "").strip()
        if text.startswith("{") and text.endswith("}"):
            return text
        fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
        if fenced:
            return fenced.group(1).strip()
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("Planner response is not valid JSON object text")
        return text[start : end + 1]

    @staticmethod
    def _validate_patch_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
        required = ("file", "line_range", "root_cause", "proposed_fix")
        for key in required:
            if key not in plan:
                raise ValueError(f"Missing required patch key: {key}")
        if not isinstance(plan["file"], str) or not plan["file"].strip():
            raise ValueError("patch.file must be non-empty string")
        line_range = plan["line_range"]
        if (
            not isinstance(line_range, list)
            or len(line_range) != 2
            or not all(isinstance(v, int) for v in line_range)
        ):
            raise ValueError("patch.line_range must be [start:int, end:int]")
        if line_range[0] <= 0 or line_range[1] < line_range[0]:
            raise ValueError("patch.line_range must be positive and start<=end")
        if not isinstance(plan["root_cause"], str) or not plan["root_cause"].strip():
            raise ValueError("patch.root_cause must be non-empty string")
        if not isinstance(plan["proposed_fix"], str) or not plan["proposed_fix"]:
            raise ValueError("patch.proposed_fix must be non-empty string")
        return {
            "file": plan["file"].strip(),
            "line_range": [int(line_range[0]), int(line_range[1])],
            "root_cause": plan["root_cause"].strip(),
            "proposed_fix": plan["proposed_fix"],
        }

    def propose_patch_plan(
        self,
        buggy_code: str,
        traceback: str,
        memory: Memory,
        retry_context: str = "",
        patch_file: str = "",
    ) -> Dict[str, Any]:
        memory_summary = memory.get_summary(max_tokens=400) if memory else ""
        user_prompt = (
            "Analyze the failing Python file and traceback, then output one JSON patch plan.\n\n"
        )
        if patch_file.strip():
            user_prompt += f'Set JSON "file" exactly to "{patch_file.strip()}" (relative path).\n\n'
        user_prompt += (
            f"Buggy code:\n```python\n{buggy_code}\n```\n\n"
            f"Traceback:\n{traceback}\n\n"
            f"Memory summary:\n{memory_summary or '(none)'}\n"
        )
        if retry_context:
            user_prompt += f"\nRetry guidance:\n{retry_context}\n"

        response = self.model.chat(
            messages=[{"role": "user", "content": user_prompt}],
            system_instruction=PATCH_PLAN_SYSTEM_PROMPT,
        )
        self._session_stats["steps"] += 1
        self._session_stats["total_input_tokens"] += response.input_tokens
        self._session_stats["total_output_tokens"] += response.output_tokens
        self._session_stats["total_latency_ms"] += response.latency_ms
        self._log(
            "planner_patch_plan_response",
            {
                "text_preview": (response.text or "")[:400],
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "latency_ms": response.latency_ms,
            },
        )

        payload = self._extract_json_object(response.text or "")
        parsed = json.loads(payload)
        return self._validate_patch_plan(parsed)

    def plan(self, buggy_code: str, traceback: str, memory: Memory) -> dict:
        """
        Legacy entry point for compatibility if needed. It triggers the Autonomous loop.
        In the new architecture, we prefer `run_autonomous_loop()`.
        """
        return self.propose_patch_plan(buggy_code=buggy_code, traceback=traceback, memory=memory)

    def run_autonomous_loop(self, user_objective: str) -> str:
        self._target_test_command = self._extract_target_test_command(user_objective)
        self.history.append({"role": "user", "content": user_objective})
        self._log("planner_start", {"objective": user_objective, "max_steps": self.max_steps})
        
        for step in range(self.max_steps):
            response = self.model.chat(
                messages=self.history,
                tools=self._tools,
                system_instruction=SYSTEM_PROMPT
            )
            self._session_stats["steps"] += 1
            self._session_stats["total_input_tokens"] += response.input_tokens
            self._session_stats["total_output_tokens"] += response.output_tokens
            self._session_stats["total_latency_ms"] += response.latency_ms
            self._log(
                "model_response",
                {
                    "step": step + 1,
                    "text_preview": response.text[:300],
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "latency_ms": response.latency_ms,
                    "tool_calls_count": len(response.tool_calls or []),
                },
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
                    if not isinstance(tool_call, dict):
                        tool_result = f"Invalid tool call payload type: {type(tool_call).__name__}"
                        self.history.append({"role": "tool", "name": "<invalid>", "content": tool_result})
                        self._log(
                            "tool_call",
                            {
                                "step": step + 1,
                                "name": "<invalid>",
                                "arguments": {},
                                "result_preview": tool_result[:300],
                            },
                        )
                        continue
                    name = tool_call.get("name", "")
                    args = tool_call.get("arguments", {})
                    if not isinstance(name, str) or not name:
                        tool_result = f"Invalid tool call payload: missing/invalid name in {tool_call}"
                        self.history.append({"role": "tool", "name": "<invalid>", "content": tool_result})
                        self._log(
                            "tool_call",
                            {
                                "step": step + 1,
                                "name": "<invalid>",
                                "arguments": {},
                                "result_preview": tool_result[:300],
                            },
                        )
                        continue
                    if not isinstance(args, dict):
                        tool_result = f"Invalid tool call payload: arguments must be an object for tool {name}"
                        self.history.append({"role": "tool", "name": name, "content": tool_result})
                        self._log(
                            "tool_call",
                            {
                                "step": step + 1,
                                "name": name,
                                "arguments": {},
                                "result_preview": tool_result[:300],
                            },
                        )
                        continue
                    self._session_stats["tool_calls"] += 1
                    
                    print(f"  [Tool Call]: {name}({args})")
                    
                    tool_result = ""
                    signature = (name, json.dumps(args, sort_keys=True, default=str))
                    if (
                        signature == self._last_tool_signature
                        and self._is_tool_failure(self._last_tool_result)
                    ):
                        self._repeated_failing_skips += 1
                        tool_result = (
                            "Tool execution skipped: repeated identical failing call. "
                            f"Previous result: {self._last_tool_result[:180]}"
                        )
                    else:
                        self._repeated_failing_skips = 0
                        # Dispatch to corresponding python function
                        tool_fn = self._tool_registry.get(name)
                        if tool_fn:
                            try:
                                tool_result = tool_fn(**args)
                            except Exception as e:
                                tool_result = f"Tool execution failed: {e}"
                        else:
                            tool_result = f"Unknown tool: {name}"
                    tool_meta = self._classify_tool_result(name, str(tool_result))
                    if name == "edit_file":
                        self._phase = "patching"
                        if tool_meta["kind"] == "edit_noop":
                            self._consecutive_noop_edits += 1
                        else:
                            self._consecutive_noop_edits = 0
                    else:
                        self._consecutive_noop_edits = 0

                    should_verify = name == "edit_file" and tool_meta["status"] == "ok" and self._target_test_command
                    if should_verify:
                        run_target_test = self._tool_registry.get("run_target_test")
                        run_bash = self._tool_registry.get("run_bash")
                        self._phase = "verify"
                        verify_result = ""
                        if run_target_test:
                            verify_result = run_target_test()
                        elif run_bash:
                            verify_result = run_bash(command=self._target_test_command)
                        if verify_result:
                            verify_exit = self._exit_code_from_tool_output(verify_result)
                            if verify_exit == 0:
                                verify_note = (
                                    "Auto-verification succeeded after edit. "
                                    f"Target test `{self._target_test_command}` passed."
                                )
                                print(f"  [Tool Output]:\\n{verify_note[:200]}...")
                                self.history.append(
                                    {
                                        "role": "tool",
                                        "name": name,
                                        "content": verify_note,
                                    }
                                )
                                self._log(
                                    "planner_end",
                                    {
                                        "status": "resolved_verified",
                                        "step": step + 1,
                                        "session_stats": self.session_stats(),
                                        "target_test_command": self._target_test_command,
                                    },
                                )
                                return (
                                    "Applied fix and verifier passed. "
                                    f"Target test `{self._target_test_command}` succeeded.\nRESOLVED"
                                )
                            tool_result = (
                                f"{tool_result}\nAuto-verification (`{self._target_test_command}`) still failing."
                            )
                            tool_meta = self._classify_tool_result(name, str(tool_result))

                    if self._consecutive_noop_edits >= self._max_consecutive_noop_edits:
                        tool_result = (
                            "Too many consecutive no-op edits. "
                            "Stop editing and run target tests before proposing another patch."
                        )
                    if self._repeated_failing_skips >= self._max_repeated_failing_skips:
                        tool_result = (
                            "Repeated identical failing tool calls exceeded threshold. "
                            "Choose a different investigation strategy."
                        )
                    self._last_tool_signature = signature
                    self._last_tool_result = str(tool_result)
                    self._log(
                        "tool_call",
                        {
                            "step": step + 1,
                            "name": name,
                            "arguments": args,
                            "result_preview": str(tool_result)[:300],
                        },
                    )
                    
                    print(f"  [Tool Output]:\n{str(tool_result)[:200]}...")
                    self.history.append({
                        "role": "tool",
                        "name": name,
                        "content": str(tool_result)
                    })
            else:
                if "RESOLVED" in response_text or "All tests pass" in response_text:
                    self._log(
                        "planner_end",
                        {
                            "status": "resolved",
                            "step": step + 1,
                            "session_stats": self.session_stats(),
                        },
                    )
                    return response_text
        
        self._log(
            "planner_end",
            {
                "status": "max_steps_reached",
                "step": self.max_steps,
                "session_stats": self.session_stats(),
            },
        )
        return "Max steps reached without resolving the bug."


