import os
import time
import json
import requests
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from models.base import BaseModel, ModelResponse

load_dotenv()

_TOGETHER_BASE_URL = "https://api.together.xyz/v1"


class MiniMaxModel(BaseModel):
    """MiniMax-M2.5 via Together AI's OpenAI-compatible chat completions API."""

    def __init__(self, model_name: str = None):
        from config import MINIMAX_MODEL
        self._model_name = model_name or MINIMAX_MODEL
        self._api_key = os.getenv("TOGETHER_API_KEY")
        if not self._api_key:
            raise EnvironmentError("TOGETHER_API_KEY not set in environment")

    def _convert_tools(self, tools: Optional[list]) -> list:
        if not tools:
            return []
        result = []
        for tool in tools:
            tool_name = tool.__name__
            desc = tool.__doc__ or ""
            result.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": desc.strip(),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Target file"},
                            "command": {"type": "string", "description": "Bash command"},
                            "old_content": {"type": "string"},
                            "new_content": {"type": "string"},
                        },
                    },
                },
            })
        return result

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
            payload["tools"] = self._convert_tools(tools)
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
            print(f"Together AI connection error (MiniMax): {e}")
            raise

        latency_ms = (time.monotonic() - start) * 1000

        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        text = message.get("content") or ""

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
        )

    def name(self) -> str:
        return self._model_name
