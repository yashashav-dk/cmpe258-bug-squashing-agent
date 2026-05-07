from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

@dataclass
class ModelResponse:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    tool_calls: Optional[List[Dict[str, Any]]] = None
    thinking: Optional[str] = None  # Chain-of-thought / reasoning trace


class BaseModel(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict[str, Any]], tools: Optional[list] = None, system_instruction: str = "") -> ModelResponse:
        """Send message history to the LLM and return a ModelResponse."""

    @abstractmethod
    def name(self) -> str:
        """Return the human-readable model name."""
