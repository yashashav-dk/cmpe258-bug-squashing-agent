from models.base import BaseModel, ModelResponse


class MiniMaxModel(BaseModel):
    """Stub for MiniMax-M2.5 via HuggingFace/Together. Not yet implemented."""

    def complete(self, prompt: str) -> ModelResponse:
        raise NotImplementedError(
            "MiniMaxModel is not yet implemented. "
            "To implement: add API key to .env and wire the inference endpoint."
        )

    def name(self) -> str:
        return "minimax-m2.5"
