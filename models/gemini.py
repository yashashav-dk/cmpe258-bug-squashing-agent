import os
import time
from typing import List, Dict, Any, Optional
import google.generativeai as genai
from google.generativeai.types import content_types
from dotenv import load_dotenv
from models.base import BaseModel, ModelResponse

load_dotenv()


class GeminiModel(BaseModel):
    def __init__(self, model_name: str = None):
        from config import GEMINI_MODEL
        self._model_name = model_name or GEMINI_MODEL
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise EnvironmentError("GEMINI_API_KEY not set in environment")
        genai.configure(api_key=api_key)
        self._base_client = genai.GenerativeModel(self._model_name)

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        gemini_msgs = []
        for msg in messages:
            role = "user"
            if msg["role"] == "assistant":
                role = "model"
            elif msg["role"] == "system":
                # system instructions handled separately
                continue
            
            parts = []
            if "content" in msg and msg["content"] is not None:
                parts.append(msg["content"])
                
            # Handle tool call responses
            if msg["role"] == "tool" or msg.get("name"):
                 # Gemini expects a specific format for function responses
                 role = "user" # Function responses come from user
                 parts = [content_types.Part.from_function_response(
                     name=msg.get("name", "function"),
                     response={"result": msg["content"]}
                 )]
            
            # Handle assistant tool calls in history
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    # We would ideally reconstruct the function_call part here, 
                    # but for simplicity if we are just re-playing history, we might skip it or handle it.
                    pass

            if parts:
                gemini_msgs.append({"role": role, "parts": parts})
        return gemini_msgs

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[list] = None, system_instruction: str = "") -> ModelResponse:
        start = time.monotonic()
        
        # In Gemini, system_instruction or tools requires re-initializing the GenerativeModel instance
        kwargs = {}
        if system_instruction:
            kwargs["system_instruction"] = system_instruction
        if tools:
            kwargs["tools"] = tools
            
        client = genai.GenerativeModel(self._model_name, **kwargs) if kwargs else self._base_client
        
        contents = self._convert_messages(messages)
        
        try:
            response = client.generate_content(contents)
        except Exception as e:
            # Fallback or error logging
            print(f"Gemini API Error: {e}")
            raise e

        latency_ms = (time.monotonic() - start) * 1000

        text = ""
        tool_calls = []
        
        if hasattr(response, "parts") and response.parts:
            for part in response.parts:
                if hasattr(part, "text") and part.text:
                    text += part.text
                if hasattr(part, "function_call") and part.function_call:
                    args = {k: v for k, v in part.function_call.args.items()}
                    tool_calls.append({
                        "name": part.function_call.name,
                        "arguments": args
                    })

        # Fallback if no parts but text exists
        if not text and hasattr(response, "text"):
            try:
                text = response.text
            except Exception:
                pass

        usage = getattr(response, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

        return ModelResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            tool_calls=tool_calls if tool_calls else None
        )

    def name(self) -> str:
        return self._model_name

