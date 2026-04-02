import json
from dataclasses import dataclass, field


def _patch_fingerprint(patch: dict) -> str:
    """Normalize a patch to a hashable fingerprint for dead-end detection."""
    line_range = tuple(patch["line_range"])
    fix = patch["proposed_fix"].strip()
    return f"{line_range}::{fix}"


class Memory:
    def __init__(self):
        self.edit_history: list = []
        self.error_evolution: list = []
        self.dead_end_registry: set = set()

    def record_attempt(self, patch_plan: dict, traceback: str, passed: bool) -> None:
        entry = {
            "iteration": len(self.edit_history) + 1,
            "patch_plan": patch_plan,
            "traceback": traceback,
            "passed": passed,
        }
        self.edit_history.append(entry)
        self.error_evolution.append(traceback)
        if not passed:
            self.dead_end_registry.add(_patch_fingerprint(patch_plan))

    def is_dead_end(self, patch_plan: dict) -> bool:
        return _patch_fingerprint(patch_plan) in self.dead_end_registry

    def get_summary(self, max_tokens: int) -> str:
        """Return a summary of memory state, truncated to approximately max_tokens."""
        char_budget = max_tokens * 4  # rough approximation: 1 token ≈ 4 chars
        lines = []
        for entry in reversed(self.edit_history):
            line = (
                f"[Iteration {entry['iteration']}] "
                f"passed={entry['passed']} | "
                f"traceback: {entry['traceback'][:200]}"
            )
            lines.append(line)
        summary = "\n".join(reversed(lines))
        return summary[-char_budget:] if len(summary) > char_budget else summary

    def save(self, path: str) -> None:
        data = {
            "edit_history": self.edit_history,
            "error_evolution": self.error_evolution,
            "dead_end_registry": list(self.dead_end_registry),
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
