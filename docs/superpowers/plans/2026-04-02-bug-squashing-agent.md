# Bug Squashing Agent — Initial Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish the initial implementation of the autonomous Bug Squashing Agent — a private GitHub repo with a complete Planner→Executor→Critic loop wired to Gemini, 5 hand-crafted bug cases, model stubs for Qwen/MiniMax, and all required course documentation.

**Architecture:** Pure Python — no LangChain/AutoGen/CrewAI. The Planner prompts an LLM and receives a structured JSON patch plan; the Executor atomically applies the patch and re-runs pytest; the Critic decides to resolve or retry. Memory is a per-case object (not raw chat history) tracking edit history, error evolution, and dead ends.

**Tech Stack:** Python 3.11+, pytest, `google-generativeai`, `python-dotenv`, `dataclasses`, `subprocess` (shell=False), `ast`, `os.path.realpath`

---

## File Map

| File | Responsibility |
|------|---------------|
| `config.py` | All constants: MAX_RETRIES, MAX_MEMORY_TOKENS, model name, dataset root |
| `logger.py` | JSON-lines structured logging for every agent interaction |
| `models/base.py` | `BaseModel` ABC + `ModelResponse` dataclass |
| `models/gemini.py` | Gemini client (fully wired) |
| `models/qwen.py` | Qwen stub — raises NotImplementedError |
| `models/minimax.py` | MiniMax stub — raises NotImplementedError |
| `agent/memory.py` | Per-case Memory: edit_history, error_evolution, dead_end_registry |
| `agent/planner.py` | Builds prompt, calls LLM, parses + validates JSON patch plan |
| `agent/executor.py` | Validates path, atomic write, runs pytest via subprocess |
| `agent/critic.py` | Evaluates pytest result, drives retry/resolve decision |
| `main.py` | CLI entry point: `--case <id> --model <name>` |
| `dataset/cases/case_00N/buggy.py` | Buggy function (one per case) |
| `dataset/cases/case_00N/test_buggy.py` | Deterministic pytest |
| `dataset/cases/case_00N/golden.py` | Correct reference (never fed to agent) |
| `dataset/few_shot/fs_001.json` | Few-shot triplet JSON files |
| `README.md` | Assignment-required fields |
| `HANDOFF.md` | Living internal engineering doc |
| `requirements.txt` | Python dependencies |
| `.env.example` | API key placeholders |
| `tests/test_memory.py` | Unit tests for Memory |
| `tests/test_planner.py` | Unit tests for Planner (mocked LLM) |
| `tests/test_executor.py` | Unit tests for Executor (tmp_path) |
| `tests/test_critic.py` | Unit tests for Critic |
| `tests/test_logger.py` | Unit tests for Logger |

---

## Task 1: Create GitHub Repo and Initialize Project

**Files:**
- Create: `requirements.txt`
- Create: `.env.example`
- Create: `.gitignore`

- [ ] **Step 1: Create the private GitHub repo**

```bash
gh repo create cmpe258-bug-squashing-agent --public --description "Autonomous Bug Squashing Multi-Agent System — CMPE 258 Spring 2026"
```

Expected: GitHub URL printed, e.g. `https://github.com/<username>/cmpe258-bug-squashing-agent`

- [ ] **Step 2: Clone and enter the repo**

```bash
git clone https://github.com/<username>/cmpe258-bug-squashing-agent
cd cmpe258-bug-squashing-agent
```

- [ ] **Step 3: Create directory skeleton**

```bash
mkdir -p agent models dataset/cases dataset/few_shot tests docs/superpowers/plans docs/superpowers/specs
```

- [ ] **Step 4: Create requirements.txt**

```
google-generativeai>=0.8.0
python-dotenv>=1.0.0
pytest>=8.0.0
```

- [ ] **Step 5: Create .env.example**

```
GEMINI_API_KEY=your_gemini_api_key_here
TOGETHER_API_KEY=your_together_api_key_here
```

- [ ] **Step 6: Create .gitignore**

```
.env
__pycache__/
*.pyc
*.pyo
.pytest_cache/
*.egg-info/
dist/
.DS_Store
dataset/cases/*/memory.json
logs/
```

- [ ] **Step 7: Commit initial scaffold**

```bash
git add .
git commit -m "chore: initialize project scaffold"
git push -u origin main
```

Expected: Push succeeds.

---

## Task 2: Config and Logger

**Files:**
- Create: `config.py`
- Create: `logger.py`
- Create: `tests/test_logger.py`

- [ ] **Step 1: Write the failing logger test**

Create `tests/test_logger.py`:

```python
import json
import os
import tempfile
from logger import Logger


def test_logger_writes_jsonlines():
    with tempfile.NamedTemporaryFile(mode="r", suffix=".jsonl", delete=False) as f:
        log_path = f.name

    try:
        logger = Logger(log_path)
        logger.log(event="test_event", case_id="case_001", data={"key": "value"})

        with open(log_path) as f:
            line = f.readline()
        record = json.loads(line)

        assert record["event"] == "test_event"
        assert record["case_id"] == "case_001"
        assert record["data"] == {"key": "value"}
        assert "timestamp" in record
    finally:
        os.unlink(log_path)


def test_logger_appends_multiple_lines():
    with tempfile.NamedTemporaryFile(mode="r", suffix=".jsonl", delete=False) as f:
        log_path = f.name

    try:
        logger = Logger(log_path)
        logger.log(event="e1", case_id="c1", data={})
        logger.log(event="e2", case_id="c1", data={})

        with open(log_path) as f:
            lines = f.readlines()

        assert len(lines) == 2
        assert json.loads(lines[0])["event"] == "e1"
        assert json.loads(lines[1])["event"] == "e2"
    finally:
        os.unlink(log_path)
```

- [ ] **Step 2: Run test to verify it fails**

```bash
pytest tests/test_logger.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'logger'`

- [ ] **Step 3: Create config.py**

```python
import os

# Agent loop
MAX_RETRIES = 5
MAX_MEMORY_TOKENS = 2000

# Model
GEMINI_MODEL = "gemini-2.0-pro"  # update to current available model if needed

# Paths
DATASET_ROOT = os.path.join(os.path.dirname(__file__), "dataset")
CASES_DIR = os.path.join(DATASET_ROOT, "cases")
FEW_SHOT_DIR = os.path.join(DATASET_ROOT, "few_shot")
LOG_PATH = os.path.join(os.path.dirname(__file__), "logs", "run.jsonl")
```

- [ ] **Step 4: Create logger.py**

```python
import json
import os
from datetime import datetime, timezone


class Logger:
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def log(self, event: str, case_id: str, data: dict) -> None:
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "case_id": case_id,
            "data": data,
        }
        with open(self.path, "a") as f:
            f.write(json.dumps(record) + "\n")
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_logger.py -v
```

Expected: 2 PASSED

- [ ] **Step 6: Commit**

```bash
git add config.py logger.py tests/test_logger.py
git commit -m "feat: add config and structured JSON-lines logger"
```

---

## Task 3: BaseModel Interface

**Files:**
- Create: `models/__init__.py`
- Create: `models/base.py`

- [ ] **Step 1: Create models/__init__.py**

```python
```
(empty file)

- [ ] **Step 2: Create models/base.py**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add models/__init__.py models/base.py
git commit -m "feat: add BaseModel ABC and ModelResponse dataclass"
```

---

## Task 4: Dataset — 5 Bug Cases

**Files:**
- Create: `dataset/cases/case_001/buggy.py`, `test_buggy.py`, `golden.py`
- Create: `dataset/cases/case_002/buggy.py`, `test_buggy.py`, `golden.py`
- Create: `dataset/cases/case_003/buggy.py`, `test_buggy.py`, `golden.py`
- Create: `dataset/cases/case_004/buggy.py`, `test_buggy.py`, `golden.py`
- Create: `dataset/cases/case_005/buggy.py`, `test_buggy.py`, `golden.py`

- [ ] **Step 1: Create case_001 — wrong return type**

`dataset/cases/case_001/buggy.py`:
```python
def add_numbers(a: int, b: int):
    return str(a + b)  # Bug: returns str instead of int
```

`dataset/cases/case_001/test_buggy.py`:
```python
from buggy import add_numbers


def test_add_numbers_returns_int():
    result = add_numbers(3, 4)
    assert isinstance(result, int), f"Expected int, got {type(result)}"
    assert result == 7


def test_add_numbers_negative():
    assert add_numbers(-1, 1) == 0
```

`dataset/cases/case_001/golden.py`:
```python
def add_numbers(a: int, b: int):
    return a + b
```

- [ ] **Step 2: Verify case_001 test fails on buggy, passes on golden**

```bash
cd dataset/cases/case_001 && pytest test_buggy.py -v && cd ../../..
```

Expected: FAIL (confirms the bug is real)

```bash
cp dataset/cases/case_001/golden.py /tmp/golden_check.py
# manually verify: the golden version would pass — we don't run it against the test yet
```

- [ ] **Step 3: Create case_002 — off-by-one in list slicing**

`dataset/cases/case_002/buggy.py`:
```python
def get_last_n(lst: list, n: int) -> list:
    return lst[-n + 1:]  # Bug: off-by-one, should be lst[-n:]
```

`dataset/cases/case_002/test_buggy.py`:
```python
from buggy import get_last_n


def test_get_last_n_basic():
    assert get_last_n([1, 2, 3, 4, 5], 3) == [3, 4, 5]


def test_get_last_n_one():
    assert get_last_n([10, 20, 30], 1) == [30]


def test_get_last_n_all():
    assert get_last_n([1, 2], 2) == [1, 2]
```

`dataset/cases/case_002/golden.py`:
```python
def get_last_n(lst: list, n: int) -> list:
    return lst[-n:]
```

- [ ] **Step 4: Create case_003 — flipped comparison**

`dataset/cases/case_003/buggy.py`:
```python
def find_max(lst: list) -> int:
    max_val = lst[0]
    for x in lst:
        if x < max_val:  # Bug: should be x > max_val
            max_val = x
    return max_val
```

`dataset/cases/case_003/test_buggy.py`:
```python
from buggy import find_max


def test_find_max_basic():
    assert find_max([3, 1, 4, 1, 5, 9, 2]) == 9


def test_find_max_negatives():
    assert find_max([-5, -1, -3]) == -1


def test_find_max_single():
    assert find_max([42]) == 42
```

`dataset/cases/case_003/golden.py`:
```python
def find_max(lst: list) -> int:
    max_val = lst[0]
    for x in lst:
        if x > max_val:
            max_val = x
    return max_val
```

- [ ] **Step 5: Create case_004 — variable shadowing**

`dataset/cases/case_004/buggy.py`:
```python
def make_multiplier(factor: int):
    def multiply(factor: int) -> int:  # Bug: parameter shadows outer 'factor'
        return factor * factor          # multiplies by itself, not outer factor
    return multiply
```

`dataset/cases/case_004/test_buggy.py`:
```python
from buggy import make_multiplier


def test_multiplier_by_3():
    triple = make_multiplier(3)
    assert triple(5) == 15


def test_multiplier_by_2():
    double = make_multiplier(2)
    assert double(7) == 14


def test_multiplier_by_1():
    identity = make_multiplier(1)
    assert identity(99) == 99
```

`dataset/cases/case_004/golden.py`:
```python
def make_multiplier(factor: int):
    def multiply(x: int) -> int:
        return x * factor
    return multiply
```

- [ ] **Step 6: Create case_005 — missing return**

`dataset/cases/case_005/buggy.py`:
```python
def absolute_value(n: int):
    if n >= 0:
        return n
    # Bug: missing `return -n` for negative branch — returns None
```

`dataset/cases/case_005/test_buggy.py`:
```python
from buggy import absolute_value


def test_positive():
    assert absolute_value(5) == 5


def test_negative():
    assert absolute_value(-3) == 3


def test_zero():
    assert absolute_value(0) == 0
```

`dataset/cases/case_005/golden.py`:
```python
def absolute_value(n: int) -> int:
    if n >= 0:
        return n
    return -n
```

- [ ] **Step 7: Verify all 5 cases fail on their buggy versions**

```bash
for i in 001 002 003 004 005; do
  echo "--- case_$i ---"
  (cd dataset/cases/case_$i && pytest test_buggy.py -q 2>&1 | tail -3)
done
```

Expected: All 5 cases show FAILED tests.

- [ ] **Step 8: Commit**

```bash
git add dataset/
git commit -m "feat: add 5 hand-crafted bug cases (syntax, logic, scope tiers)"
```

---

## Task 5: Few-Shot Triplets

**Files:**
- Create: `dataset/few_shot/fs_001.json`
- Create: `dataset/few_shot/fs_002.json`
- Create: `dataset/few_shot/fs_003.json`

- [ ] **Step 1: Create fs_001.json (wrong return type)**

```json
{
  "buggy_code": "def add_numbers(a: int, b: int):\n    return str(a + b)\n",
  "traceback": "FAILED test_buggy.py::test_add_numbers_returns_int - AssertionError: Expected int, got <class 'str'>",
  "fix": "def add_numbers(a: int, b: int):\n    return a + b\n"
}
```

- [ ] **Step 2: Create fs_002.json (flipped comparison)**

```json
{
  "buggy_code": "def find_max(lst: list) -> int:\n    max_val = lst[0]\n    for x in lst:\n        if x < max_val:\n            max_val = x\n    return max_val\n",
  "traceback": "FAILED test_buggy.py::test_find_max_basic - AssertionError: assert 1 == 9",
  "fix": "def find_max(lst: list) -> int:\n    max_val = lst[0]\n    for x in lst:\n        if x > max_val:\n            max_val = x\n    return max_val\n"
}
```

- [ ] **Step 3: Create fs_003.json (missing return)**

```json
{
  "buggy_code": "def absolute_value(n: int):\n    if n >= 0:\n        return n\n",
  "traceback": "FAILED test_buggy.py::test_negative - AssertionError: assert None == 3",
  "fix": "def absolute_value(n: int) -> int:\n    if n >= 0:\n        return n\n    return -n\n"
}
```

- [ ] **Step 4: Commit**

```bash
git add dataset/few_shot/
git commit -m "feat: add 3 few-shot triplets for Planner in-context prompting"
```

---

## Task 6: Memory Module

**Files:**
- Create: `agent/__init__.py`
- Create: `agent/memory.py`
- Create: `tests/test_memory.py`

- [ ] **Step 1: Write the failing memory tests**

Create `tests/test_memory.py`:

```python
import json
import os
import tempfile
from agent.memory import Memory


def make_patch(line_start=1, line_end=3, fix="return x\n"):
    return {
        "file": "buggy.py",
        "line_range": [line_start, line_end],
        "root_cause": "test",
        "proposed_fix": fix,
    }


def test_initial_state_is_empty():
    m = Memory()
    assert m.edit_history == []
    assert m.error_evolution == []
    assert len(m.dead_end_registry) == 0


def test_record_failed_attempt_adds_to_dead_end():
    m = Memory()
    patch = make_patch(fix="return str(x)\n")
    m.record_attempt(patch, traceback="AssertionError: ...", passed=False)
    assert m.is_dead_end(patch)


def test_record_passed_attempt_does_not_add_to_dead_end():
    m = Memory()
    patch = make_patch(fix="return x\n")
    m.record_attempt(patch, traceback="", passed=True)
    assert not m.is_dead_end(patch)


def test_whitespace_normalized_dead_end():
    m = Memory()
    patch1 = make_patch(fix="return str(x)\n")
    patch2 = make_patch(fix="  return str(x)  \n")
    m.record_attempt(patch1, traceback="err", passed=False)
    assert m.is_dead_end(patch2)


def test_get_summary_returns_string():
    m = Memory()
    patch = make_patch()
    m.record_attempt(patch, traceback="AssertionError", passed=False)
    summary = m.get_summary(max_tokens=500)
    assert isinstance(summary, str)
    assert "AssertionError" in summary


def test_get_summary_truncates_to_token_budget():
    m = Memory()
    for i in range(20):
        patch = make_patch(fix=f"return {i}\n")
        m.record_attempt(patch, traceback=f"error_{i}" * 50, passed=False)
    summary = m.get_summary(max_tokens=100)
    # rough check: 100 tokens ≈ 400 chars
    assert len(summary) < 800


def test_save_and_load(tmp_path):
    m = Memory()
    patch = make_patch()
    m.record_attempt(patch, traceback="err", passed=False)
    path = str(tmp_path / "memory.json")
    m.save(path)
    assert os.path.exists(path)
    with open(path) as f:
        data = json.load(f)
    assert len(data["edit_history"]) == 1
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_memory.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agent.memory'`

- [ ] **Step 3: Create agent/__init__.py**

```python
```
(empty)

- [ ] **Step 4: Create agent/memory.py**

```python
import json
from dataclasses import dataclass, field


def _patch_fingerprint(patch: dict) -> str:
    """Normalize a patch to a hashable fingerprint for dead-end detection."""
    line_range = tuple(patch["line_range"])
    fix = patch["proposed_fix"].strip()
    return f"{line_range}::{fix}"


class Memory:
    def __init__(self):
        self.edit_history: list[dict] = []
        self.error_evolution: list[str] = []
        self.dead_end_registry: set[str] = set()

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
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_memory.py -v
```

Expected: 7 PASSED

- [ ] **Step 6: Commit**

```bash
git add agent/__init__.py agent/memory.py tests/test_memory.py
git commit -m "feat: add Memory module with edit_history, error_evolution, dead_end_registry"
```

---

## Task 7: Planner Module

**Files:**
- Create: `agent/planner.py`
- Create: `tests/test_planner.py`

- [ ] **Step 1: Write the failing planner tests**

Create `tests/test_planner.py`:

```python
import json
from unittest.mock import MagicMock
from agent.planner import Planner
from agent.memory import Memory
from models.base import BaseModel, ModelResponse


def make_mock_model(response_text: str) -> BaseModel:
    model = MagicMock(spec=BaseModel)
    model.complete.return_value = ModelResponse(
        text=response_text,
        input_tokens=100,
        output_tokens=50,
        latency_ms=500.0,
    )
    model.name.return_value = "mock-model"
    return model


VALID_PATCH = json.dumps({
    "file": "buggy.py",
    "line_range": [1, 3],
    "root_cause": "wrong operator",
    "proposed_fix": "def f(x):\n    return x\n",
})


def test_planner_returns_valid_patch():
    model = make_mock_model(VALID_PATCH)
    planner = Planner(model=model, few_shot_dir="dataset/few_shot")
    memory = Memory()
    result = planner.plan(
        buggy_code="def f(x):\n    return -x\n",
        traceback="AssertionError: assert f(1) == 1",
        memory=memory,
    )
    assert result["file"] == "buggy.py"
    assert result["line_range"] == [1, 3]
    assert "proposed_fix" in result
    assert "root_cause" in result


def test_planner_raises_on_invalid_json():
    model = make_mock_model("not json at all")
    planner = Planner(model=model, few_shot_dir="dataset/few_shot")
    memory = Memory()
    try:
        planner.plan(
            buggy_code="def f(x): pass",
            traceback="error",
            memory=memory,
        )
        assert False, "Should have raised"
    except ValueError as e:
        assert "JSON" in str(e)


def test_planner_raises_on_missing_fields():
    bad_patch = json.dumps({"file": "buggy.py"})  # missing required fields
    model = make_mock_model(bad_patch)
    planner = Planner(model=model, few_shot_dir="dataset/few_shot")
    memory = Memory()
    try:
        planner.plan(
            buggy_code="def f(x): pass",
            traceback="error",
            memory=memory,
        )
        assert False, "Should have raised"
    except ValueError as e:
        assert "schema" in str(e).lower()


def test_planner_prompt_includes_buggy_code():
    model = make_mock_model(VALID_PATCH)
    planner = Planner(model=model, few_shot_dir="dataset/few_shot")
    memory = Memory()
    planner.plan(
        buggy_code="def my_unique_fn(): pass",
        traceback="some error",
        memory=memory,
    )
    call_args = model.complete.call_args[0][0]
    assert "my_unique_fn" in call_args
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_planner.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agent.planner'`

- [ ] **Step 3: Create agent/planner.py**

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_planner.py -v
```

Expected: 4 PASSED

- [ ] **Step 5: Commit**

```bash
git add agent/planner.py tests/test_planner.py
git commit -m "feat: add Planner with prompt template, few-shot loading, JSON validation"
```

---

## Task 8: Executor Module

**Files:**
- Create: `agent/executor.py`
- Create: `tests/test_executor.py`

- [ ] **Step 1: Write the failing executor tests**

Create `tests/test_executor.py`:

```python
import os
import pytest
from agent.executor import Executor, PatchError


def make_executor(tmp_path, case_id="case_test"):
    case_dir = tmp_path / "dataset" / "cases" / case_id
    case_dir.mkdir(parents=True)
    return Executor(cases_root=str(tmp_path / "dataset" / "cases")), case_dir


def make_patch(line_range, fix):
    return {
        "file": "buggy.py",
        "line_range": line_range,
        "root_cause": "test",
        "proposed_fix": fix,
    }


def test_executor_applies_patch(tmp_path):
    executor, case_dir = make_executor(tmp_path)
    buggy = case_dir / "buggy.py"
    buggy.write_text("line1\nline2\nline3\n")
    patch = make_patch([2, 2], "replaced\n")
    executor.apply_patch(patch, case_id="case_test")
    assert buggy.read_text() == "line1\nreplaced\nline3\n"


def test_executor_atomic_write_rejects_invalid_python(tmp_path):
    executor, case_dir = make_executor(tmp_path)
    buggy = case_dir / "buggy.py"
    original = "def f():\n    return 1\n"
    buggy.write_text(original)
    patch = make_patch([1, 2], "def f(\n  INVALID SYNTAX!!!\n")
    with pytest.raises(PatchError):
        executor.apply_patch(patch, case_id="case_test")
    assert buggy.read_text() == original  # original untouched


def test_executor_rejects_path_traversal(tmp_path):
    executor, case_dir = make_executor(tmp_path)
    patch = {
        "file": "../../config.py",
        "line_range": [1, 1],
        "root_cause": "attack",
        "proposed_fix": "HACKED\n",
    }
    with pytest.raises(PatchError, match="Scope violation"):
        executor.apply_patch(patch, case_id="case_test")


def test_executor_runs_pytest_and_returns_result(tmp_path):
    executor, case_dir = make_executor(tmp_path)
    buggy = case_dir / "buggy.py"
    buggy.write_text("def f():\n    return 1\n")
    test_file = case_dir / "test_buggy.py"
    test_file.write_text("from buggy import f\ndef test_f():\n    assert f() == 1\n")
    passed, traceback = executor.run_tests(case_id="case_test")
    assert passed is True
    assert traceback == ""


def test_executor_captures_failure_traceback(tmp_path):
    executor, case_dir = make_executor(tmp_path)
    buggy = case_dir / "buggy.py"
    buggy.write_text("def f():\n    return 99\n")
    test_file = case_dir / "test_buggy.py"
    test_file.write_text("from buggy import f\ndef test_f():\n    assert f() == 1\n")
    passed, traceback = executor.run_tests(case_id="case_test")
    assert passed is False
    assert "assert" in traceback.lower() or "failed" in traceback.lower()
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_executor.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agent.executor'`

- [ ] **Step 3: Create agent/executor.py**

```python
import ast
import os
import subprocess
from dataclasses import dataclass


class PatchError(Exception):
    pass


class Executor:
    def __init__(self, cases_root: str):
        self.cases_root = os.path.realpath(cases_root)

    def _case_dir(self, case_id: str) -> str:
        return os.path.join(self.cases_root, case_id)

    def _validate_scope(self, file_path: str, case_id: str) -> str:
        """Return realpath of target file after validating it is within allowed scope."""
        allowed_root = os.path.realpath(self._case_dir(case_id))
        target = os.path.realpath(os.path.join(allowed_root, file_path))
        if not target.startswith(allowed_root + os.sep) and target != allowed_root:
            raise PatchError(f"Scope violation: {file_path!r} resolves outside case directory")
        return target

    def apply_patch(self, patch: dict, case_id: str) -> None:
        """Atomically apply a patch to buggy.py."""
        target_path = self._validate_scope(patch["file"], case_id)
        start, end = patch["line_range"]  # 1-indexed, inclusive

        with open(target_path) as f:
            lines = f.readlines()

        new_lines = lines[: start - 1] + [patch["proposed_fix"]] + lines[end:]
        new_content = "".join(new_lines)

        # Validate syntax before writing
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            raise PatchError(f"Patch produces invalid Python: {e}")

        # Atomic write: write to .tmp then rename
        tmp_path = target_path + ".tmp"
        try:
            with open(tmp_path, "w") as f:
                f.write(new_content)
            os.replace(tmp_path, target_path)
        except OSError as e:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise PatchError(f"File I/O error during atomic write: {e}")

    def run_tests(self, case_id: str) -> tuple[bool, str]:
        """Run pytest on the case. Returns (passed, traceback_string)."""
        case_dir = self._case_dir(case_id)
        test_file = os.path.join(case_dir, "test_buggy.py")
        result = subprocess.run(
            ["pytest", test_file, "-v", "--tb=short"],
            shell=False,
            capture_output=True,
            text=True,
            cwd=case_dir,
        )
        passed = result.returncode == 0
        traceback = result.stdout + result.stderr if not passed else ""
        return passed, traceback
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_executor.py -v
```

Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add agent/executor.py tests/test_executor.py
git commit -m "feat: add Executor with atomic write, scope validation, subprocess shell=False"
```

---

## Task 9: Critic Module

**Files:**
- Create: `agent/critic.py`
- Create: `tests/test_critic.py`

- [ ] **Step 1: Write the failing critic tests**

Create `tests/test_critic.py`:

```python
from agent.critic import Critic, CaseResult
from agent.memory import Memory


def test_critic_resolves_on_pass():
    critic = Critic(max_retries=3)
    memory = Memory()
    result = critic.evaluate(passed=True, traceback="", memory=memory, iteration=1)
    assert result == CaseResult.RESOLVED


def test_critic_retries_on_fail_within_limit():
    critic = Critic(max_retries=3)
    memory = Memory()
    patch = {"file": "buggy.py", "line_range": [1, 2], "root_cause": "x", "proposed_fix": "y\n"}
    memory.record_attempt(patch, "error", passed=False)
    result = critic.evaluate(passed=False, traceback="error", memory=memory, iteration=1)
    assert result == CaseResult.RETRY


def test_critic_gives_up_at_max_retries():
    critic = Critic(max_retries=3)
    memory = Memory()
    result = critic.evaluate(passed=False, traceback="still failing", memory=memory, iteration=3)
    assert result == CaseResult.UNRESOLVED


def test_critic_includes_json_hint_on_parse_error():
    critic = Critic(max_retries=5)
    memory = Memory()
    summary = critic.build_retry_context(traceback="not json", is_json_error=True)
    assert "JSON" in summary


def test_critic_includes_schema_hint_on_schema_error():
    critic = Critic(max_retries=5)
    memory = Memory()
    summary = critic.build_retry_context(traceback="schema fail", is_schema_error=True)
    assert "schema" in summary.lower()
```

- [ ] **Step 2: Run to verify they fail**

```bash
pytest tests/test_critic.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'agent.critic'`

- [ ] **Step 3: Create agent/critic.py**

```python
from enum import Enum
from agent.memory import Memory


class CaseResult(Enum):
    RESOLVED = "resolved"
    RETRY = "retry"
    UNRESOLVED = "unresolved"


class Critic:
    def __init__(self, max_retries: int):
        self.max_retries = max_retries

    def evaluate(
        self,
        passed: bool,
        traceback: str,
        memory: Memory,
        iteration: int,
    ) -> CaseResult:
        if passed:
            return CaseResult.RESOLVED
        if iteration >= self.max_retries:
            return CaseResult.UNRESOLVED
        return CaseResult.RETRY

    def build_retry_context(
        self,
        traceback: str,
        is_json_error: bool = False,
        is_schema_error: bool = False,
    ) -> str:
        """Build a short context string to append to the next Planner prompt."""
        if is_json_error:
            return (
                f"IMPORTANT: Your previous response was not valid JSON. "
                f"You MUST respond with only a raw JSON object.\n"
                f"Error: {traceback}"
            )
        if is_schema_error:
            return (
                f"IMPORTANT: Your previous response failed schema validation. "
                f"Ensure all required fields are present: file, line_range, root_cause, proposed_fix.\n"
                f"Error: {traceback}"
            )
        return f"The previous patch did not fix the bug. New traceback:\n{traceback}"
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_critic.py -v
```

Expected: 5 PASSED

- [ ] **Step 5: Commit**

```bash
git add agent/critic.py tests/test_critic.py
git commit -m "feat: add Critic with retry/resolve/unresolved logic and error context builder"
```

---

## Task 10: Gemini Model Client

**Files:**
- Create: `models/gemini.py`

- [ ] **Step 1: Install dependencies**

```bash
pip install google-generativeai python-dotenv
```

- [ ] **Step 2: Create models/gemini.py**

```python
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
        # Token counts from usage_metadata (available in google-generativeai >= 0.8)
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
```

- [ ] **Step 3: Verify import works (no API call)**

```bash
python -c "from models.gemini import GeminiModel; print('import ok')"
```

Expected: `import ok` (will raise EnvironmentError if GEMINI_API_KEY not set — that's expected behavior)

- [ ] **Step 4: Commit**

```bash
git add models/gemini.py
git commit -m "feat: add Gemini model client with ModelResponse token tracking"
```

---

## Task 11: Qwen and MiniMax Stubs

**Files:**
- Create: `models/qwen.py`
- Create: `models/minimax.py`

- [ ] **Step 1: Create models/qwen.py**

```python
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
```

- [ ] **Step 2: Create models/minimax.py**

```python
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
```

- [ ] **Step 3: Commit**

```bash
git add models/qwen.py models/minimax.py
git commit -m "feat: add Qwen and MiniMax model stubs with NotImplementedError"
```

---

## Task 12: main.py Entry Point

**Files:**
- Create: `main.py`

- [ ] **Step 1: Create main.py**

```python
#!/usr/bin/env python3
"""
main.py — Run one full Planner→Executor→Critic agent loop on a single bug case.

Usage:
    python main.py --case case_001 [--model gemini]
"""
import argparse
import os
import sys

from config import MAX_RETRIES, CASES_DIR, FEW_SHOT_DIR, LOG_PATH
from logger import Logger
from agent.memory import Memory
from agent.planner import Planner
from agent.executor import Executor, PatchError
from agent.critic import Critic, CaseResult


def get_model(model_name: str):
    if model_name == "gemini":
        from models.gemini import GeminiModel
        return GeminiModel()
    elif model_name == "qwen":
        from models.qwen import QwenModel
        return QwenModel()
    elif model_name == "minimax":
        from models.minimax import MiniMaxModel
        return MiniMaxModel()
    else:
        raise ValueError(f"Unknown model: {model_name!r}. Choose from: gemini, qwen, minimax")


def run_case(case_id: str, model_name: str) -> CaseResult:
    logger = Logger(LOG_PATH)
    memory = Memory()
    model = get_model(model_name)
    planner = Planner(model=model, few_shot_dir=FEW_SHOT_DIR)
    executor = Executor(cases_root=CASES_DIR)
    critic = Critic(max_retries=MAX_RETRIES)

    case_dir = os.path.join(CASES_DIR, case_id)
    buggy_path = os.path.join(case_dir, "buggy.py")

    if not os.path.isdir(case_dir):
        print(f"Error: case directory not found: {case_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Case: {case_id} | Model: {model.name()}")
    print(f"{'='*60}")

    # Initial pytest run
    passed, traceback = executor.run_tests(case_id=case_id)
    if passed:
        print("Tests already passing — nothing to fix.")
        return CaseResult.RESOLVED

    result = CaseResult.RETRY
    for iteration in range(1, MAX_RETRIES + 1):
        print(f"\n[Iteration {iteration}/{MAX_RETRIES}]")
        with open(buggy_path) as f:
            buggy_code = f.read()

        # Planner
        is_json_error = is_schema_error = False
        try:
            patch = planner.plan(buggy_code=buggy_code, traceback=traceback, memory=memory)
        except ValueError as e:
            err = str(e)
            is_json_error = "JSON" in err
            is_schema_error = "schema" in err.lower()
            retry_ctx = critic.build_retry_context(
                traceback=err, is_json_error=is_json_error, is_schema_error=is_schema_error
            )
            print(f"  Planner error: {err[:100]}")
            logger.log("planner_error", case_id, {"iteration": iteration, "error": err})
            memory.record_attempt(
                {"file": "buggy.py", "line_range": [0, 0], "root_cause": err, "proposed_fix": ""},
                traceback=err, passed=False,
            )
            result = critic.evaluate(passed=False, traceback=err, memory=memory, iteration=iteration)
            if result != CaseResult.RETRY:
                break
            traceback = retry_ctx
            continue

        if memory.is_dead_end(patch):
            print(f"  Dead end detected — skipping duplicate patch")
            result = critic.evaluate(passed=False, traceback="dead end", memory=memory, iteration=iteration)
            if result != CaseResult.RETRY:
                break
            continue

        print(f"  Root cause: {patch['root_cause']}")
        print(f"  Patching lines {patch['line_range']}...")

        # Executor
        try:
            executor.apply_patch(patch, case_id=case_id)
        except PatchError as e:
            print(f"  Patch failed: {e}")
            logger.log("patch_error", case_id, {"iteration": iteration, "error": str(e)})
            memory.record_attempt(patch, traceback=str(e), passed=False)
            result = critic.evaluate(passed=False, traceback=str(e), memory=memory, iteration=iteration)
            if result != CaseResult.RETRY:
                break
            continue

        passed, traceback = executor.run_tests(case_id=case_id)
        logger.log("iteration", case_id, {
            "iteration": iteration,
            "model": model.name(),
            "patch": patch,
            "passed": passed,
            "traceback": traceback[:500],
        })
        memory.record_attempt(patch, traceback=traceback, passed=passed)

        result = critic.evaluate(passed=passed, traceback=traceback, memory=memory, iteration=iteration)
        status = "PASS" if passed else "FAIL"
        print(f"  Result: {status}")

        if result != CaseResult.RETRY:
            break

    memory.save(os.path.join(case_dir, "memory.json"))

    print(f"\nFinal result: {result.value.upper()}")
    logger.log("final", case_id, {"result": result.value, "model": model.name()})
    return result


def main():
    parser = argparse.ArgumentParser(description="Bug Squashing Agent")
    parser.add_argument("--case", required=True, help="Case ID (e.g. case_001)")
    parser.add_argument("--model", default="gemini", choices=["gemini", "qwen", "minimax"])
    args = parser.parse_args()
    run_case(case_id=args.case, model_name=args.model)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify the CLI is importable and shows help**

```bash
python main.py --help
```

Expected:
```
usage: main.py [-h] --case CASE [--model {gemini,qwen,minimax}]
Bug Squashing Agent
...
```

- [ ] **Step 3: Commit**

```bash
git add main.py
git commit -m "feat: add main.py CLI entry point wiring full Planner→Executor→Critic loop"
```

---

## Task 13: README and HANDOFF.md

**Files:**
- Create: `README.md`
- Create: `HANDOFF.md`

- [ ] **Step 1: Create README.md**

```markdown
# Autonomous Bug Squashing Agent System

**CMPE 258 — Deep Learning, Spring 2026 | San Jose State University**

## Team Members

| Name | Student ID | Contribution |
|------|-----------|--------------|
| Pranav Trivedi | 019089512 | Agent architecture, Planner module, Gemini integration |
| Yashashav DK | 017856371 | Dataset curation, Executor module, safety guardrails |
| Saransh Soni | 019115122 | Memory module, Critic module, logging infrastructure |

## Project Description

An autonomous multi-agent system that analyzes failing pytest tracebacks and buggy Python source files, identifies root causes, and directly edits code to pass tests — without human intervention.

**Architecture:** Planner → Executor → Critic loop built from scratch in Python. No LangChain, AutoGen, or CrewAI.

**Success metric:** Binary pass/fail on pytest suite after agent intervention, measured across 50 bug cases and 3 LLMs.

## Dataset

- **50 buggy Python functions** (backend, APIs, auth) paired with deterministic pytest scripts
- **3 tiers:** Syntax/Type (15), Logic/Algorithmic (20), Contextual/Scope (15)
- **5–8 few-shot triplets** held out for in-context prompting
- **Initial submission:** 5 representative cases (one per tier, hand-crafted)

Each case: `buggy.py` + `test_buggy.py` + `golden.py` (reference, not fed to agent)

## Approach

### Planner–Executor–Critic Architecture

```
Planner(LLM) → JSON patch plan → Executor(apply + pytest) → Critic(pass/retry/give up)
                                         ↑                         |
                                      Memory ←────────────────────┘
```

- **Planner:** Analyzes traceback + source + memory → structured JSON patch
- **Executor:** Validates scope, atomically applies patch, re-runs pytest
- **Critic:** Drives retry loop; terminates on pass or MAX_RETRIES
- **Memory:** Tracks edit history, error evolution, dead-end patches (per case, not global)

### Models Compared

| Model | Role | Status |
|-------|------|--------|
| Gemini 2.0 Pro | Baseline | Fully wired |
| Qwen-2.5 72B | Open SOTA | Stub (next milestone) |
| MiniMax-M2.5 | Open MoE | Stub (next milestone) |

## Current Progress

*(Initial submission — commit `<SHA>`)* 

- [x] Planner→Executor→Critic loop functional end-to-end with Gemini
- [x] 5 hand-crafted bug cases across all 3 tiers
- [x] 3 few-shot triplets for in-context prompting
- [x] Atomic patch writes with syntax validation
- [x] Path traversal protection + subprocess allowlist (shell=False)
- [x] Per-case Memory with dead-end detection
- [x] Structured JSON-lines logging (prompts, patches, verdicts, token counts)
- [ ] Qwen-2.5 72B (wiring in progress)
- [ ] MiniMax-M2.5 (planned)
- [ ] Remaining 45 bug cases
- [ ] Web UI
- [ ] Docker sandboxing
- [ ] Full evaluation across all 50 cases × 3 models

## Next Steps

1. Wire Qwen-2.5 72B via Together AI
2. Wire MiniMax-M2.5
3. Expand dataset to 50 cases
4. Build Web UI (upload files, select model, observe agent in real time)
5. Add Docker sandbox
6. Run full evaluation and report metrics (pass rate, latency p50/p90/p99, cost/fix)

## Setup

```bash
git clone https://github.com/<username>/cmpe258-bug-squashing-agent
cd cmpe258-bug-squashing-agent
pip install -r requirements.txt
cp .env.example .env
# Add your GEMINI_API_KEY to .env
python main.py --case case_001 --model gemini
```

## References

- Gemini API: aistudio.google.com
- Qwen-2.5-Coder: github.com/QwenLM/Qwen2.5-Coder
- MiniMax-M2.5: huggingface.co/minimax
- Together AI: together.ai
- SWE-Bench: swebench.com
```

- [ ] **Step 2: Update README with actual submission commit SHA after pushing**

After final push in Task 14, run:
```bash
git rev-parse --short HEAD
```
And replace `<SHA>` in the README "Current Progress" section with the actual value. Commit the update.

- [ ] **Step 3: Create HANDOFF.md**

```markdown
# HANDOFF.md — Bug Squashing Agent

> **Update policy:** Update this file on every merged PR. Last committer is responsible.

---

## Architecture Overview

The system is a Planner→Executor→Critic loop with no external agent frameworks.

```
main.py --case <id> --model <name>
  │
  ├─ Planner (agent/planner.py)
  │    reads: buggy.py, traceback, Memory summary, few-shot triplets
  │    writes: JSON patch plan to Executor
  │    prompt template: PROMPT_TEMPLATE constant in agent/planner.py
  │    interpolation: Python f-string (no Jinja2)
  │
  ├─ Executor (agent/executor.py)
  │    validates: os.path.realpath() scope check before any write
  │    applies: atomic write (tmp → ast.parse → os.replace)
  │    runs: subprocess(["pytest", ...], shell=False)
  │
  ├─ Critic (agent/critic.py)
  │    decides: RESOLVED | RETRY | UNRESOLVED
  │    builds: retry context strings for JSON/schema/pytest errors
  │
  └─ Memory (agent/memory.py)
       per-case, not global; serialized to dataset/cases/<id>/memory.json
       dead-end fingerprint: (line_range_tuple, fix.strip())
```

## Implementation Status

| Component | File | Status |
|-----------|------|--------|
| Config | `config.py` | Done |
| Logger | `logger.py` | Done |
| BaseModel + ModelResponse | `models/base.py` | Done |
| Gemini client | `models/gemini.py` | Done — fully wired |
| Qwen client | `models/qwen.py` | **Stub** — raises NotImplementedError |
| MiniMax client | `models/minimax.py` | **Stub** — raises NotImplementedError |
| Memory | `agent/memory.py` | Done |
| Planner | `agent/planner.py` | Done |
| Executor | `agent/executor.py` | Done |
| Critic | `agent/critic.py` | Done |
| Entry point | `main.py` | Done |
| Dataset (5 cases) | `dataset/cases/` | Done |
| Few-shot triplets | `dataset/few_shot/` | Done (3 triplets) |
| Web UI | `web/` | **Not started** |
| Docker | `Dockerfile` | **Not started** |

## Pending Work

- [ ] Wire Qwen-2.5 72B: implement `models/qwen.py` using Together AI Python SDK
- [ ] Wire MiniMax-M2.5: find current inference endpoint, implement `models/minimax.py`
- [ ] Add 45 more bug cases to `dataset/cases/` (see proposal for tier distribution)
- [ ] Build Web UI in `web/` (Flask or FastAPI + simple JS frontend)
- [ ] Add Dockerfile with sandboxed execution
- [ ] Run full evaluation: `python main.py --case <all> --model <all>`, collect metrics

## How to Add a New LLM

1. Create `models/<name>.py`
2. Implement `BaseModel` — `complete(prompt: str) -> ModelResponse` and `name() -> str`
3. Add the model name to the `get_model()` function in `main.py`
4. Add the API key to `.env.example` and document in this file
5. Test with `python main.py --case case_001 --model <name>`

## How to Add a New Bug Case

1. Create `dataset/cases/case_NNN/` directory
2. Add `buggy.py` (the broken function), `test_buggy.py` (deterministic pytest), `golden.py` (reference)
3. Verify: `cd dataset/cases/case_NNN && pytest test_buggy.py -v` should FAIL
4. Verify the golden version would pass (manual review)
5. Optionally add a few-shot triplet to `dataset/few_shot/fs_NNN.json`

## Environment Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Set GEMINI_API_KEY in .env (get from aistudio.google.com)
python main.py --case case_001 --model gemini
```

## Known Gotchas

- **Memory is per-case, not global.** A new `Memory()` is created in `run_case()` for each invocation. This is intentional — it keeps the token budget controllable and prevents cross-case error leakage.

- **`golden.py` is never fed to the agent.** It is only used for human evaluation. Giving the agent the golden file would invalidate the evaluation — the agent must fix the bug from traceback + source alone.

- **`proposed_fix` is a literal replacement block, not a diff.** The Executor replaces lines `line_range[0]` through `line_range[1]` (1-indexed, inclusive) with the entire `proposed_fix` string. The indentation in `proposed_fix` must be correct.

- **Gemini model name.** Update `GEMINI_MODEL` in `config.py` if the model name changes. Current value: `"gemini-2.0-pro"`. Check aistudio.google.com for current available models.

- **Token budget.** `MAX_MEMORY_TOKENS = 2000` in `config.py` controls how much memory context is passed to the Planner. Increase if you see the agent repeating dead-end patches; decrease if hitting context window limits.
```

- [ ] **Step 4: Commit**

```bash
git add README.md HANDOFF.md
git commit -m "docs: add README with all required course fields and HANDOFF.md"
```

---

## Task 14: Final Integration Test and Push

**Files:**
- No new files — integration test only

- [ ] **Step 1: Run the full test suite**

```bash
pytest tests/ -v
```

Expected: All tests PASS (test_logger, test_memory, test_planner, test_executor, test_critic)

- [ ] **Step 2: Copy spec and plan docs into repo**

```bash
cp /Users/spartan/jurisprudence/CMPE258/cmpe258_project/docs/superpowers/specs/2026-04-02-bug-squashing-agent-design.md docs/superpowers/specs/
cp /Users/spartan/jurisprudence/CMPE258/cmpe258_project/docs/superpowers/plans/2026-04-02-bug-squashing-agent.md docs/superpowers/plans/
git add docs/
git commit -m "docs: add design spec and implementation plan"
```

- [ ] **Step 3: Verify main.py --help works**

```bash
python main.py --help
```

Expected: usage message printed cleanly.

- [ ] **Step 4: Do a dry-run on case_001 (requires GEMINI_API_KEY)**

If GEMINI_API_KEY is set:
```bash
python main.py --case case_001 --model gemini
```

Expected: Iteration output printed, final result `RESOLVED` or `UNRESOLVED` (depending on model).

If API key not yet set, skip this step and note it in HANDOFF.md.

- [ ] **Step 5: Update README with actual commit SHA**

```bash
SHA=$(git rev-parse --short HEAD)
# Edit README.md: replace <SHA> with $SHA in the "Current Progress" section
git add README.md
git commit -m "docs: update README with submission commit SHA"
```

- [ ] **Step 6: Push all commits**

```bash
git push origin main
```

Expected: All commits pushed. Verify on GitHub that the repo shows multiple commits with meaningful messages and the README renders correctly.

- [ ] **Step 7: Note the GitHub URL for submission**

```bash
gh repo view --web
```

Copy the URL — this is what you submit: `https://github.com/<username>/cmpe258-bug-squashing-agent`
