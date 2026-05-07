import inspect
import json
import os
import time
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from models.base import BaseModel, ModelResponse

load_dotenv()

_TOGETHER_BASE_URL = "https://api.together.xyz/v1"


def _fn_to_openai_tool(fn) -> dict:
    """Convert a Python function to an OpenAI-compatible tool schema using inspect."""
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
        if param_name == "self":
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


class QwenModel(BaseModel):
    """Qwen-2.5 72B via Together AI's OpenAI-compatible chat completions API."""

    def __init__(self, model_name: str = None):
        from config import QWEN_MODEL
        self._model_name = model_name or QWEN_MODEL
        self._api_key = os.getenv("TOGETHER_API_KEY")
        if not self._api_key:
            raise EnvironmentError("TOGETHER_API_KEY not set in environment")

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[list] = None,
        system_instruction: str = "",
    ) -> ModelResponse:
        start = time.monotonic()

        history = list(messages)
        if system_instruction:
            history.insert(0, {"role": "system", "content": system_instruction})

        payload: Dict[str, Any] = {
            "model": self._model_name,
            "messages": history,
        }
        if tools:
            payload["tools"] = [_fn_to_openai_tool(fn) for fn in tools]
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        try:
            res = requests.post(
                f"{_TOGETHER_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=120,
            )
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"Together AI connection error (Qwen): {e}")
            raise

        latency_ms = (time.monotonic() - start) * 1000

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        text = message.get("content") or ""

        # Extract <think>...</think> reasoning chain (Qwen-R1 style)
        import re
        think_blocks = re.findall(r"<think>(.*?)</think>", text, re.DOTALL)
        thinking = "\n---\n".join(think_blocks).strip() if think_blocks else None
        if think_blocks:
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        tool_calls = []
        for tc in message.get("tool_calls") or []:
            fn = tc.get("function", {})
            raw_args = fn.get("arguments", "{}")
            try:
                arguments = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                arguments = {"raw": raw_args}
            tool_calls.append({"name": fn.get("name", ""), "arguments": arguments})

        usage = data.get("usage", {})
        input_tokens = usage.get("prompt_tokens", 0)
        output_tokens = usage.get("completion_tokens", 0)

        return ModelResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            tool_calls=tool_calls if tool_calls else None,
            thinking=thinking,
        )

    def name(self) -> str:
        return self._model_name
