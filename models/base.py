from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ModelResponse:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: float


class BaseModel(ABC):
    @abstractmethod
    def complete(self, prompt: str) -> ModelResponse:
        """Send prompt to the LLM and return a ModelResponse."""

    @abstractmethod
    def name(self) -> str:
        """Return the human-readable model name."""
