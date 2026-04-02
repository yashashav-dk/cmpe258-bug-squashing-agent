import os
import time
import google.generativeai as genai
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
        self._client = genai.GenerativeModel(self._model_name)

    def complete(self, prompt: str) -> ModelResponse:
        start = time.monotonic()
        response = self._client.generate_content(prompt)
        latency_ms = (time.monotonic() - start) * 1000

        text = response.text
        usage = getattr(response, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", 0) if usage else 0
        output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0

        return ModelResponse(
            text=text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms,
        )

    def name(self) -> str:
        return self._model_name
