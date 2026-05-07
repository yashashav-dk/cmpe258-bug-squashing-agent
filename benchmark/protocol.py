from dataclasses import dataclass
from typing import Dict, List


FAILURE_TAXONOMY = [
    "localization_failure",
    "invalid_patch",
    "non_terminating_loop",
    "test_regression",
    "false_resolved",
    "environment_error",
]


ACCEPTANCE_CRITERIA = [
    "No source-adapter-specific logic in runner/runtime interfaces.",
    "Each run emits verifier-backed resolved/unresolved status.",
    "Each result row includes seed, commit, model, and timing/token stats.",
    "Manifest replay with same seed reproduces identical case hash.",
]

MODEL_PRICING_USD_PER_1M: Dict[str, Dict[str, float]] = {
    # Gemini 2.0 Flash public list price (input/output per 1M tokens).
    "gemini": {"input": 0.10, "output": 0.40},
    # OpenRouter list pricing for qwen/qwen-2.5-72b-instruct (USD per 1M tokens).
    "qwen": {"input": 0.36, "output": 0.40},
    # OpenRouter-routed models: same underlying pricing as their native equivalents.
    "qwen_or": {"input": 0.36, "output": 0.40},
    "gemini_or": {"input": 0.10, "output": 0.40},
    # Gemini 3 via native google-genai SDK (USD per 1M tokens, Google AI Studio list price).
    "gemini3flash": {"input": 0.10, "output": 0.40},
    "gemini3pro": {"input": 1.25, "output": 5.00},
    "minimax": {"input": 0.30, "output": 1.20},
    # Gemma 4 via OpenRouter (google/gemma-4-31b-it).
    "gemma4": {"input": 0.12, "output": 0.12},
    # Gemma 3 27B via OpenRouter (google/gemma-3-27b-it).
    "gemma3": {"input": 0.10, "output": 0.10},
    # Gemma 3 4B via OpenRouter (google/gemma-3-4b-it).
    "gemma3_4b": {"input": 0.03, "output": 0.03},
}

PRICING_SOURCE = (
    "Static benchmark assumptions in benchmark/protocol.py "
    "(USD per 1M input/output tokens)."
)


@dataclass(frozen=True)
class EvalProtocol:
    min_repetitions: int = 5
    require_regression_check: bool = True
    confidence_level: float = 0.95
    primary_metric: str = "pass_rate_target_tests"
    secondary_metrics: tuple = (
        "time_to_fix_ms",
        "input_tokens",
        "output_tokens",
        "retry_depth",
        "patch_size_chars",
        "regression_failure_rate",
    )


def protocol_summary() -> List[str]:
    return [
        "Controls: pinned commit, pinned dependencies, fixed seed, fixed timeout budget.",
        "Oracle: verifier exit code from target tests (and optional regression suite).",
        "Statistics: Wilson interval for pass rate; paired bootstrap for model deltas.",
        "Failure labels use shared taxonomy for post-hoc analysis.",
    ]
