import os
import time
import requests
import json
import inspect
from typing import List, Dict, Any, Optional

from models.base import BaseModel, ModelResponse


def _fn_to_ollama_tool(fn) -> dict:
    """Convert a Python function to an Ollama/OpenAI-style tool schema using inspect."""
    sig = inspect.signature(fn)
    doc = inspect.getdoc(fn) or ""

    # Parse per-arg descriptions from docstring "Args:" block
    arg_docs: Dict[str, str] = {}
    in_args = False
    for line in doc.splitlines():
        stripped = line.strip()
        if stripped == "Args:":
            in_args = True
            continue
        if in_args:
            if stripped and not stripped.startswith(" ") and stripped.endswith(":") and " " not in stripped:
                break
            if ":" in stripped:
                arg_name, _, arg_desc = stripped.partition(":")
                arg_docs[arg_name.strip()] = arg_desc.strip()

    properties: Dict[str, dict] = {}
    required: List[str] = []
    for param_name, param in sig.parameters.items():
        if param_name in ("self",):
            continue
        description = arg_docs.get(param_name, param_name)
        properties[param_name] = {"type": "string", "description": description}
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": doc.split("\n\n")[0].strip() if doc else fn.__name__,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
            },
        },
    }


class Gemma4Model(BaseModel):
    """
    Ollama integration for Gemma 4.
    Runs locally and targets the Kaggle Gemma 4 Good Hackathon (Ollama Track).
    """
    def __init__(self, model_name: str = "gemma4:latest", endpoint: str = None):
        self._model_name = model_name
        self.endpoint = endpoint or os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        self._session = requests.Session()
        self._session.trust_env = False

    def _convert_tools(self, tools: Optional[list]) -> list:
        if not tools:
            return []

        def _param_schema(param_name: str) -> Dict[str, Any]:
            hints = {
                "filepath": "Path to file relative to current workspace.",
                "command": "Shell command to execute.",
                "cwd": "Working directory for command execution.",
                "old_content": "Exact old text block to replace.",
                "new_content": "Replacement text block.",
            }
            return {"type": "string", "description": hints.get(param_name, f"Value for {param_name}.")}

        ollama_tools = []
        for tool in tools:
            signature = inspect.signature(tool)
            properties: Dict[str, Any] = {}
            required: List[str] = []
            for name, param in signature.parameters.items():
                properties[name] = _param_schema(name)
                if param.default is inspect._empty:
                    required.append(name)

            ollama_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.__name__,
                        "description": (tool.__doc__ or "").strip(),
                        "parameters": {
                            "type": "object",
                            "properties": properties,
                            "required": required,
                            "additionalProperties": False,
                        },
                    },
                }
            )
        return ollama_tools

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[list] = None, system_instruction: str = "") -> ModelResponse:
        start = time.monotonic()

        url = f"{self.endpoint}/api/chat"

        # Insert system instruction as first message if provided
        history = list(messages)
        if system_instruction:
            history.insert(0, {"role": "system", "content": system_instruction})

        payload: Dict[str, Any] = {
            "model": self._model_name,
            "messages": history,
            "stream": False,
        }

        if tools:
            payload["tools"] = self._convert_tools(tools)
            
        max_retries = int(os.getenv("OLLAMA_MAX_RETRIES", "5"))
        timeout_s = int(os.getenv("OLLAMA_TIMEOUT_S", "60"))
        backoff_s = float(os.getenv("OLLAMA_RETRY_BACKOFF_S", "2"))

        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                res = self._session.post(url, json=payload, timeout=timeout_s)
                res.raise_for_status()
                data = res.json()
                break
            except Exception as e:
                last_error = e
                if attempt == max_retries:
                    print(f"Ollama connection error (Ensure Ollama is running): {e}")
                    raise e
                time.sleep(backoff_s * attempt)

        latency_ms = (time.monotonic() - start) * 1000

        response_message = data.get("message", {})
        text = response_message.get("content", "") or ""

        # Extract <think>...</think> reasoning chain (Gemma3/4 thinking style)
        import re
        think_blocks = re.findall(r"<think>(.*?)</think>", text, re.DOTALL)
        thinking = "\n---\n".join(think_blocks).strip() if think_blocks else None
        if think_blocks:
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        # Parse tool calls formatted by Ollama
        tool_calls = []
        for tc in response_message.get("tool_calls") or []:
            fn = tc.get("function", {})
            args = fn.get("arguments", {})
            # Ollama may return args as a string; try to parse it
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append({
                "name": fn.get("name", ""),
                "arguments": args,
            })

        input_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)

        return ModelResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            tool_calls=tool_calls if tool_calls else None,
            thinking=thinking,
        )

    def name(self) -> str:
        return f"Ollama ({self._model_name})"
