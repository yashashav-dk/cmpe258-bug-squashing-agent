import json
import os
from agent.memory import Memory
from models.base import BaseModel

REQUIRED_FIELDS = {"file", "line_range", "root_cause", "proposed_fix"}

PROMPT_TEMPLATE = """\
You are an expert Python debugger. Your task is to analyze a buggy Python function and a failing pytest traceback, then output a JSON patch plan to fix the bug.

## Few-Shot Examples
{few_shot_block}

## Current Task

### Buggy Code
```python
{buggy_code}
```

### Failing Traceback
```
{traceback}
```

### Memory (previous attempts)
{memory_summary}

## Instructions
- Respond with ONLY a valid JSON object — no explanation, no markdown fences.
- The JSON must have exactly these fields:
  - "file": always "buggy.py"
  - "line_range": [start_line, end_line] (1-indexed, inclusive)
  - "root_cause": short string explaining the bug
  - "proposed_fix": complete replacement Python code for the given line range, with correct indentation
- Do NOT repeat a fix that appears in the memory above.

Respond now with only the JSON:
"""


def _load_few_shots(few_shot_dir: str) -> str:
    if not os.path.isdir(few_shot_dir):
        return "(no few-shot examples available)"
    examples = []
    for fname in sorted(os.listdir(few_shot_dir)):
        if not fname.endswith(".json"):
            continue
        with open(os.path.join(few_shot_dir, fname)) as f:
            ex = json.load(f)
        examples.append(
            f"Buggy:\n```python\n{ex['buggy_code']}```\n"
            f"Traceback: {ex['traceback']}\n"
            f"Fix:\n```python\n{ex['fix']}```"
        )
    return "\n\n---\n\n".join(examples) if examples else "(no few-shot examples available)"


def _validate_patch(patch: dict) -> None:
    missing = REQUIRED_FIELDS - patch.keys()
    if missing:
        raise ValueError(f"Patch schema validation failed — missing fields: {missing}")
    if not isinstance(patch["line_range"], list) or len(patch["line_range"]) != 2:
        raise ValueError("Patch schema validation failed — line_range must be [int, int]")


class Planner:
    def __init__(self, model: BaseModel, few_shot_dir: str):
        self.model = model
        self.few_shot_block = _load_few_shots(few_shot_dir)

    def plan(self, buggy_code: str, traceback: str, memory: Memory) -> dict:
        prompt = PROMPT_TEMPLATE.format(
            few_shot_block=self.few_shot_block,
            buggy_code=buggy_code,
            traceback=traceback,
            memory_summary=memory.get_summary(max_tokens=500),
        )
        response = self.model.complete(prompt)
        text = response.text.strip()

        try:
            patch = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(f"LLM returned invalid JSON: {e}\nRaw output: {text[:300]}")

        _validate_patch(patch)
        return patch
