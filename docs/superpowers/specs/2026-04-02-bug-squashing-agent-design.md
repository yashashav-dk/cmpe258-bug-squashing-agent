# Bug Squashing Agent System — Design Spec
**Date:** 2026-04-02
**Project:** CMPE 258 — Deep Learning, Spring 2026 | SJSU
**Team:** Pranav Trivedi (019089512), Yashashav DK (017856371), Saransh Soni (019115122)

---

## 1. Problem

Build an autonomous multi-agent system that takes a buggy Python file and its failing pytest traceback, identifies the root cause, patches the code, and verifies the fix — without human intervention.

**Success metric:** Binary pass/fail on pytest suite after agent intervention, measured across 50 bug cases and 3 LLMs.

---

## 2. Repository

- **Name:** `cmpe258-bug-squashing-agent`
- **Visibility:** Public
- **Host:** GitHub (created via `gh` CLI)

---

## 3. Repository Structure

```
cmpe258-bug-squashing-agent/
├── README.md                # Public-facing project overview (required fields)
├── HANDOFF.md               # Living internal doc for LLM/developer continuity
├── main.py                  # Entry point: --case <id> runs one full agent loop
├── requirements.txt
├── .env.example             # API key placeholders (never commit real keys)
├── config.py                # MAX_RETRIES, MAX_MEMORY_TOKENS, model params, dataset paths
├── logger.py                # Structured JSON-lines logging for every interaction
├── agent/
│   ├── planner.py           # Analyzes traceback + source → JSON patch plan
│   ├── executor.py          # Applies patch atomically, re-runs pytest, returns result
│   ├── critic.py            # Evaluates result, decides retry or resolve
│   └── memory.py            # Shared state: edit_history, error_evolution, dead_end_registry
├── models/
│   ├── base.py              # BaseModel interface all LLM clients must implement
│   ├── gemini.py            # Gemini 3.1 Pro via AI Studio API (FULLY WIRED)
│   ├── qwen.py              # Qwen-2.5 72B via Together AI (STUB)
│   └── minimax.py           # MiniMax-M2.5 (STUB)
├── dataset/
│   ├── cases/
│   │   ├── case_001/        # Syntax/Type: wrong return type
│   │   ├── case_002/        # Logic: off-by-one in list slicing
│   │   ├── case_003/        # Logic: flipped comparison operator
│   │   ├── case_004/        # Contextual/Scope: variable shadowing
│   │   └── case_005/        # Syntax/Type: missing return in branch
│   └── few_shot/            # 2-3 triplets (buggy, traceback, fix) for Planner prompts
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-04-02-bug-squashing-agent-design.md
```

Each case directory contains:
- `buggy.py` — the broken function
- `test_buggy.py` — deterministic pytest (fails on buggy, passes on golden)
- `golden.py` — correct reference (evaluation only, never fed to agent)

**Scope constraint (initial submission):** All 5 cases are single-function, single-file bugs. This is an intentional simplification. Multi-file or multi-site patches are out of scope until the full 50-case dataset milestone; the patch schema will be revisited at that point.

---

## 4. Agent Loop & Data Flow

```
Load case: buggy.py + run pytest → capture traceback
        ↓
Planner(LLM) receives:
  - buggy source code
  - current pytest traceback
  - memory summary (edit history, error evolution, dead-ends)
  - few-shot examples
  → outputs JSON patch plan (see Patch Format below)
        ↓
Executor:
  - validates patch scope via os.path.realpath() (see Safety section)
  - atomically applies patch (write to .tmp, verify, rename — see Atomic Write below)
  - re-runs pytest via subprocess with shell=False
  - returns (pass/fail, new traceback)
        ↓
Critic:
  PASS → mark case resolved, log success metrics
  FAIL → summarize new error state, update Memory, re-prompt Planner
        ↓ (loop until PASS or MAX_RETRIES exceeded)
Logger writes full JSON-lines record:
  prompt, tool invocations, raw LLM output, patch plan,
  Critic verdict, memory mutations, latency, token count, cost estimate
```

**Retry ceiling:** Configurable via `config.py` (`MAX_RETRIES`, default 5).

### 4a. Patch Format

The Planner outputs a JSON object with this exact schema:

```json
{
  "file": "buggy.py",
  "line_range": [10, 14],
  "root_cause": "Human-readable explanation of the bug",
  "proposed_fix": "def my_func(x):\n    return x + 1\n"
}
```

- `file`: always `"buggy.py"` for the initial submission (single-file scope)
- `line_range`: 1-indexed, inclusive. `[10, 14]` means replace lines 10 through 14.
- `proposed_fix`: a complete replacement block for the lines in `line_range`, with correct indentation preserved. The Executor replaces exactly those lines with this string — no diff format, no `exec()`.

The Executor validates the parsed JSON against this schema before applying any patch. If validation fails, it is treated as a Planner failure (see Failure Paths below).

### 4b. Failure Paths

The following failure modes are explicitly handled before retrying or aborting:

| Failure | Handler |
|---------|---------|
| LLM returns non-JSON or partial JSON | Critic logs parse error, increments retry, re-prompts Planner with explicit JSON-only instruction |
| JSON parses but fails schema validation | Critic logs schema error, increments retry, re-prompts with schema reminder |
| Patch `line_range` out of bounds for file | Executor raises `PatchError`, Critic treats as failed patch, appends to dead_end_registry |
| Atomic write fails mid-write | `.tmp` file is left in place; original `buggy.py` is untouched; Critic logs file I/O error |
| pytest crashes (non-zero exit, no traceback) | Executor captures raw stdout/stderr; Critic logs as "crash" failure mode |
| MAX_RETRIES exceeded | Loop terminates; case marked as `unresolved`; full memory and logs persisted |

### 4c. Atomic Write (Executor)

To prevent corrupting `buggy.py` on a failed patch:

1. Read current `buggy.py` into memory.
2. Apply `line_range` replacement in memory.
3. Write result to `buggy.py.tmp` in the same directory.
4. Verify `buggy.py.tmp` is syntactically valid Python (`ast.parse()`).
5. If valid: `os.replace("buggy.py.tmp", "buggy.py")` (atomic on POSIX).
6. If invalid: delete `.tmp`, raise `PatchError` without touching `buggy.py`.

### 4d. Few-Shot Format

Each file in `dataset/few_shot/` is a JSON file with this structure:

```json
{
  "buggy_code": "def add(a, b):\n    return a - b\n",
  "traceback": "AssertionError: assert add(1, 2) == 3\n  where 3 = add(1, 2)\n",
  "fix": "def add(a, b):\n    return a + b\n"
}
```

The Planner template interpolates 2–3 of these as formatted examples before the current case. Template lives in `agent/planner.py` as a module-level constant `PROMPT_TEMPLATE` (f-string, no external templating library).

### 4e. Token Budget

`config.py` defines `MAX_MEMORY_TOKENS = 2000`. Before building the Planner prompt, the memory summary is truncated to fit within this budget (keep the most recent N entries). This prevents prompt bloat across retries from exceeding the model's context window.

---

## 5. Memory

`Memory` is a per-case object (not raw chat history). It is **not** global — a new `Memory` instance is created for each case run.

### Fields

| Field | Type | Description |
|-------|------|-------------|
| `edit_history` | `list[dict]` | Every patch applied, in order: `{iteration, patch_plan, result}` |
| `error_evolution` | `list[str]` | Traceback after each iteration |
| `dead_end_registry` | `set[str]` | Normalized patch fingerprints that failed (see below) |

### Patch Fingerprint (dead_end_registry)

Equality is defined as `(line_range_tuple, proposed_fix.strip())` — whitespace-normalized. This prevents the Planner from retrying semantically identical patches with trivial formatting differences.

### Interface

```python
class Memory:
    def record_attempt(self, patch_plan: dict, traceback: str, passed: bool) -> None: ...
    def get_summary(self, max_tokens: int) -> str: ...
    def is_dead_end(self, patch_plan: dict) -> bool: ...
    def save(self, path: str) -> None: ...  # serialize to JSON sidecar
```

Memory is serialized to `dataset/cases/<case_id>/memory.json` at the end of each run for inspection and logging.

**Design rationale:** Memory is per-case (not global chat history) because the Planner needs structured, summarized context — not raw conversation turns. This makes the memory token budget controllable and prevents error context from one case leaking into another.

---

## 6. Models

All LLM clients implement `BaseModel` (defined in `models/base.py`):

```python
class BaseModel:
    def complete(self, prompt: str) -> ModelResponse: ...
    def name(self) -> str: ...

@dataclass
class ModelResponse:
    text: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
```

Returning `ModelResponse` (not a raw string) allows the Logger to capture token counts and latency per call — required for the cost-per-fix metric in the full evaluation.

| Model | Role | Status | API |
|-------|------|--------|-----|
| Gemini 3.1 Pro | Baseline | Fully wired | AI Studio |
| Qwen-2.5 72B | Open SOTA | Stub | Together AI |
| MiniMax-M2.5 | Open MoE | Stub | HuggingFace/Together |

Stubs raise `NotImplementedError` with a clear message so the interface is exercisable but the gap is obvious.

---

## 7. Safety & Guardrails

### Path Validation (Scope Restriction)
The Executor resolves **both** the target path and the allowed root with `os.path.realpath()` before comparing — preventing path traversal attacks via `../` sequences:

```python
allowed_root = os.path.realpath(f"dataset/cases/{case_id}/")
target = os.path.realpath(patch["file"])
assert target.startswith(allowed_root), "Scope violation"
```

### Subprocess Safety
All subprocess calls use `shell=False` with explicit argument lists — no shell string interpolation:

```python
result = subprocess.run(
    ["pytest", test_file_path, "-v"],
    shell=False, capture_output=True, text=True
)
```

This prevents argument injection regardless of LLM output.

### Other Controls
- **Retry ceiling:** `MAX_RETRIES` in `config.py` (default 5) prevents runaway loops
- **No secrets in repo:** `.env.example` contains placeholders; real keys loaded via `python-dotenv`
- **User-supplied cases:** Until Docker sandboxing is added (future milestone), the system should only be run against the team's curated dataset — not arbitrary user-uploaded code
- **Docker:** Planned for a future milestone (not in initial submission scope)

---

## 8. README Required Fields

The README will include all fields required by the assignment:

- Project title & description
- Team members + student IDs + individual contribution breakdown
- Dataset description (50 cases, 3 tiers, structure)
- Approach (Planner→Executor→Critic, 3-model comparison)
- Current progress (what's implemented in this submission, with submission commit SHA)
- Next steps (remaining 45 cases, Qwen/MiniMax wiring, Web UI, Docker, full evaluation)

---

## 9. HANDOFF.md

A living document updated on every merged PR (last committer is responsible for updating it).

Contents:
- Architecture overview and key design decisions (including the rationale below)
- Prompt template location (`agent/planner.py::PROMPT_TEMPLATE`) and interpolation format
- Per-component implementation status with file locations
- Pending work (Qwen/MiniMax, Web UI, 50-case dataset, Docker, evaluation)
- How to add a new LLM (implement `BaseModel` + `ModelResponse`, register in `config.py`)
- How to add new bug cases (directory structure + naming convention)
- Environment setup (required API keys, how to run one case end-to-end)
- Known issues and non-obvious gotchas, pre-seeded with:
  - **Why Memory is per-case, not global:** Keeps token budget controllable; prevents cross-case error leakage
  - **Why `golden.py` is excluded from agent context:** Prevents data leakage into the evaluation; the agent must fix bugs using only the traceback and source, matching real-world conditions

---

## 10. Metrics (Full Evaluation — Later Milestone)

Per model across all 50 cases:
- Pass rate (bugs fixed / 50)
- Avg. latency (p50/p90/p99)
- Cost per successful fix (derived from `ModelResponse` token counts + published pricing)
- Retry depth distribution
- Failure mode taxonomy

---

## 11. What's Out of Scope for Initial Submission

- Web UI
- Docker sandboxing
- Qwen and MiniMax fully wired
- Full 50-case dataset (45 remaining cases)
- Multi-file or multi-site patches
- End-to-end multi-model evaluation
