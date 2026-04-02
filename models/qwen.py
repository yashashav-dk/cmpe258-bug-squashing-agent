from models.base import BaseModel, ModelResponse


class QwenModel(BaseModel):
    """Stub for Qwen-2.5 72B via Together AI. Not yet implemented."""

    def complete(self, prompt: str) -> ModelResponse:
        raise NotImplementedError(
            "QwenModel is not yet implemented. "
            "To implement: add TOGETHER_API_KEY to .env, "
            "install together-python, and wire the Together AI inference API."
        )

    def name(self) -> str:
        return "qwen-2.5-72b"
