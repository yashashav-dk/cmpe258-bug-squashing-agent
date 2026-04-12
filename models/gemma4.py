import os
import time
import requests
import json
from typing import List, Dict, Any, Optional

from models.base import BaseModel, ModelResponse

class Gemma4Model(BaseModel):
    """
    Ollama integration for Gemma 4.
    Runs locally and targets the Kaggle Gemma 4 Good Hackathon (Ollama Track).
    """
    def __init__(self, model_name: str = "gemma4:latest", endpoint: str = "http://localhost:11434"):
        self._model_name = model_name
        self.endpoint = endpoint

    def _convert_tools(self, tools: Optional[list]) -> list:
        if not tools:
            return []
        
        ollama_tools = []
        for tool in tools:
            # Simple conversion of a Python python function to an Ollama Schema
            # In a full implementation we'd reflect over signature. 
            # For this hackathon stub, we just map names.
            # We assume Ollama natively handles standard OpenAI-style tool schema.
            tool_name = tool.__name__
            desc = tool.__doc__ or ""
            ollama_tools.append({
                "type": "function",
                "function": {
                    "name": tool_name,
                    "description": desc.strip(),
                    # For a rigid schema, passing open parameter object
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {"type": "string", "description": "Target file"},
                            "command": {"type": "string", "description": "Bash command"},
                            "old_content": {"type": "string"},
                            "new_content": {"type": "string"}
                        }
                    }
                }
            })
        return ollama_tools

    def chat(self, messages: List[Dict[str, Any]], tools: Optional[list] = None, system_instruction: str = "") -> ModelResponse:
        start = time.monotonic()
        
        url = f"{self.endpoint}/api/chat"
        
        # Insert system instruction if provided
        history = list(messages)
        if system_instruction:
            history.insert(0, {"role": "system", "content": system_instruction})
            
        payload = {
            "model": self._model_name,
            "messages": history,
            "stream": False
        }
        
        if tools:
            payload["tools"] = self._convert_tools(tools)
            
        try:
            res = requests.post(url, json=payload, timeout=60)
            res.raise_for_status()
            data = res.json()
        except Exception as e:
            print(f"Ollama connection error (Ensure Ollama is running): {e}")
            raise e
            
        latency_ms = (time.monotonic() - start) * 1000
        
        response_message = data.get("message", {})
        text = response_message.get("content", "")
        
        # Parse tool calls formatted by Ollama
        tool_calls = []
        if response_message.get("tool_calls"):
            for tc in response_message["tool_calls"]:
                tool_calls.append({
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"]
                })
                
        # Parse prompt tokens if Ollama provides them in eval metrics
        input_tokens = data.get("prompt_eval_count", 0)
        output_tokens = data.get("eval_count", 0)

        return ModelResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
            tool_calls=tool_calls if tool_calls else None
        )

    def name(self) -> str:
        return f"Ollama ({self._model_name})"
