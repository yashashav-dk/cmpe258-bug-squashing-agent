import inspect
import json
import os
import re
import time
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

from models.base import BaseModel, ModelResponse

load_dotenv()

_OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# Model shortcuts exposed to get_model()
OPENROUTER_MODELS = {
    "gemini_or": "google/gemini-2.5-flash",
    "qwen_or": "qwen/qwen-2.5-72b-instruct",
    "gemma4": "google/gemma-4-31b-it:free",
    "gemma3": "google/gemma-3-27b-it",
    "gemma3_4b": "google/gemma-3-4b-it",
}


def _fn_to_openai_tool(fn) -> dict:
    sig = inspect.signature(fn)
    doc = inspect.getdoc(fn) or ""
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
        properties[param_name] = {"type": "string", "description": arg_docs.get(param_name, param_name)}
        if param.default is inspect.Parameter.empty:
            required.append(param_name)
    return {
        "type": "function",
        "function": {
            "name": fn.__name__,
            "description": doc.split("\n\n")[0].strip() if doc else fn.__name__,
            "parameters": {"type": "object", "properties": properties, "required": required},
        },
    }


class OpenRouterModel(BaseModel):
    """Any model available on OpenRouter via its OpenAI-compatible chat completions API."""

    def __init__(self, model_name: str):
        self._model_name = model_name
        self._api_key = os.getenv("OPENROUTER_API_KEY")
        if not self._api_key:
            raise EnvironmentError("OPENROUTER_API_KEY not set in environment")

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

        payload: Dict[str, Any] = {"model": self._model_name, "messages": history}
        if tools:
            payload["tools"] = [_fn_to_openai_tool(fn) for fn in tools]
            payload["tool_choice"] = "auto"

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/yashashav-dk/cmpe258-bug-squashing-agent",
            "X-Title": "CMPE258 Bug Squashing Agent",
        }

        try:
            res = requests.post(
                f"{_OPENROUTER_BASE_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=180,
            )
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"OpenRouter connection error ({self._model_name}): {e}")
            raise

        latency_ms = (time.monotonic() - start) * 1000
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        text = message.get("content") or ""

        # Strip <think> blocks (Gemini / Qwen reasoning traces)
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
        return ModelResponse(
            text=text,
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
            tool_calls=tool_calls if tool_calls else None,
            thinking=thinking,
        )

    def name(self) -> str:
        return self._model_name
