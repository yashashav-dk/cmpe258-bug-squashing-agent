import inspect
import os
import time
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from models.base import BaseModel, ModelResponse

load_dotenv()


def _fn_to_declaration(fn) -> types.FunctionDeclaration:
    """Convert a Python function to a Gemini FunctionDeclaration using its signature and docstring."""
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
                # New section
                break
            if ":" in stripped:
                arg_name, _, arg_desc = stripped.partition(":")
                arg_docs[arg_name.strip()] = arg_desc.strip()

    properties: Dict[str, types.Schema] = {}
    required: List[str] = []
    for param_name, param in sig.parameters.items():
        if param_name in ("self",):
            continue
        description = arg_docs.get(param_name, param_name)
        properties[param_name] = types.Schema(type="STRING", description=description)
        if param.default is inspect.Parameter.empty:
            required.append(param_name)

    return types.FunctionDeclaration(
        name=fn.__name__,
        description=doc.split("\n\n")[0].strip() if doc else fn.__name__,
        parameters=types.Schema(
            type="OBJECT",
            properties=properties,
            required=required,
        ),
    )


class GeminiModel(BaseModel):
    def __init__(self, model_name: str = None):
        from config import GEMINI_MODEL
        self._model_name = model_name or GEMINI_MODEL
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY not set in environment")
        self._client = genai.Client(api_key=api_key)

    def _build_contents(self, messages: List[Dict[str, Any]]) -> List[types.Content]:
        """Convert our internal message list into Gemini Content objects."""
        contents: List[types.Content] = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "system":
                # system handled via system_instruction separately
                continue

            parts: List[types.Part] = []

            # Function (tool) response → comes back as a user turn
            if role == "tool":
                parts.append(
                    types.Part.from_function_response(
                        name=msg.get("name", "function"),
                        response={"result": msg.get("content", "")},
                    )
                )
                contents.append(types.Content(role="user", parts=parts))
                continue

            # Assistant message that may contain function calls
            if role == "assistant":
                text_content = msg.get("content") or ""
                if text_content:
                    parts.append(types.Part.from_text(text=text_content))
                for tc in msg.get("tool_calls") or []:
                    parts.append(
                        types.Part.from_function_call(
                            name=tc["name"],
                            args=tc["arguments"],
                        )
                    )
                if parts:
                    contents.append(types.Content(role="model", parts=parts))
                continue

            # Regular user message
            content = msg.get("content") or ""
            if content:
                parts.append(types.Part.from_text(text=content))
            if parts:
                contents.append(types.Content(role="user", parts=parts))

        return contents

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[list] = None,
        system_instruction: str = "",
    ) -> ModelResponse:
        start = time.monotonic()

        # Build Gemini tool spec
        gemini_tools = None
        if tools:
            declarations = [_fn_to_declaration(fn) for fn in tools]
            gemini_tools = [types.Tool(function_declarations=declarations)]

        contents = self._build_contents(messages)

        config_kwargs: Dict[str, Any] = {}
        if system_instruction:
            config_kwargs["system_instruction"] = system_instruction
        if gemini_tools:
            config_kwargs["tools"] = gemini_tools

        generate_config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        try:
            response = self._client.models.generate_content(
                model=self._model_name,
                contents=contents,
                config=generate_config,
            )
        except Exception as e:
            print(f"Gemini API Error: {e}")
            raise

        latency_ms = (time.monotonic() - start) * 1000

        text = ""
        thinking = ""
        tool_calls: List[Dict[str, Any]] = []

        for candidate in response.candidates or []:
            for part in candidate.content.parts or []:
                # Gemini Flash Thinking marks reasoning with thought=True
                if getattr(part, "thought", False):
                    if part.text:
                        thinking += part.text
                elif part.text:
                    text += part.text
                if part.function_call:
                    fc = part.function_call
                    tool_calls.append({
                        "name": fc.name,
                        "arguments": dict(fc.args) if fc.args else {},
                    })

        # Also parse <think>...</think> blocks for models that embed CoT in text
        import re
        think_blocks = re.findall(r"<think>(.*?)</think>", text, re.DOTALL)
        if think_blocks:
            thinking = thinking + ("\n\n" if thinking else "") + "\n---\n".join(think_blocks)
            text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        usage = response.usage_metadata
        input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

        return ModelResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            tool_calls=tool_calls if tool_calls else None,
            thinking=thinking.strip() if thinking.strip() else None,
        )

    def name(self) -> str:
        return self._model_name
