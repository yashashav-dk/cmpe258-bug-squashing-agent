import inspect
import os
import time
import requests
import json
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

    def __init__(self, model_name: str = "gemma4:latest", endpoint: str = "http://localhost:11434"):
        self._model_name = model_name
        self.endpoint = endpoint

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[list] = None,
        system_instruction: str = "",
    ) -> ModelResponse:
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
            payload["tools"] = [_fn_to_ollama_tool(fn) for fn in tools]

        try:
            res = requests.post(url, json=payload, timeout=120)
            res.raise_for_status()
            data = res.json()
        except requests.exceptions.ConnectionError as e:
            print(f"Ollama connection error (Ensure Ollama is running with 'ollama serve'): {e}")
            raise
        except Exception as e:
            print(f"Ollama request error: {e}")
            raise

        latency_ms = (time.monotonic() - start) * 1000

        response_message = data.get("message", {})
        text = response_message.get("content", "") or ""

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
        )

    def name(self) -> str:
        return f"Ollama ({self._model_name})"
