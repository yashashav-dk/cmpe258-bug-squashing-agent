from dataclasses import dataclass
from typing import List


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
