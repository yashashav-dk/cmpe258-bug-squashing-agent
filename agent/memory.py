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

    @classmethod
    def load(cls, path: str) -> "Memory":
        m = cls()
        with open(path) as f:
            data = json.load(f)
        m.edit_history = data.get("edit_history", [])
        m.error_evolution = data.get("error_evolution", [])
        m.dead_end_registry = set(data.get("dead_end_registry", []))
        return m

    def consolidate_dream(self, history: list, model) -> str:
        """
        Similar to Claude-Code's 'Dream' system, this reviews the interaction history
        to generate durable guidelines/learnings for this session.
        """
        dream_prompt = "Review the following agent tool-calling history and summarize key learnings in 3 sentences."
        # Using a very basic format to send to the model
        history_text = "\n".join([f"{msg.get('role')}: {msg.get('content', '...tool...')}" for msg in history])
        messages = [
            {"role": "system", "content": "You are a memory consolidation module. Extract durable learnings from the history."},
            {"role": "user", "content": f"{dream_prompt}\n\nHistory:\n{history_text[-2000:]}"}
        ]
        response = model.chat(messages=messages)
        print(f"\n[DREAM CONSOLIDATION]\n{response.text}\n")
        return response.text
