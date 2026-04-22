# HANDOFF.md — Bug Squashing Agent

> **Update policy:** Update this file on every merged PR. Last committer is responsible.

---

## Architecture Overview

The system is a Planner→Executor→Critic loop with no external agent frameworks.

```
python3 main.py --case <id> --model <name>
  │
  ├─ Planner (agent/planner.py)
  │    reads: buggy.py, traceback, Memory summary, few-shot triplets
  │    outputs: JSON patch plan to Executor
  │    prompt template: PROMPT_TEMPLATE constant in agent/planner.py (f-string, no Jinja2)
  │
  ├─ Executor (agent/executor.py)
  │    validates: os.path.realpath() scope check before any write
  │    applies: atomic write (write to .tmp → ast.parse() → os.replace())
  │    runs: subprocess([sys.executable, "-m", "pytest", ...], shell=False)
  │
  ├─ Critic (agent/critic.py)
  │    decides: RESOLVED | RETRY | UNRESOLVED
  │    builds: retry context strings for JSON/schema/pytest errors
  │
  └─ Memory (agent/memory.py)
       per-case, not global — new Memory() per run_case() call
       dead-end fingerprint: (line_range_tuple, proposed_fix.strip())
       serialized to: dataset/cases/<id>/memory.json (gitignored)
```

## Implementation Status

| Component | File | Status |
|-----------|------|--------|
| Config | `config.py` | Done |
| Logger | `logger.py` | Done |
| BaseModel + ModelResponse | `models/base.py` | Done |
| Gemini client | `models/gemini.py` | Done — google-genai SDK, inspect-based schema |
| Qwen client | `models/qwen.py` | Done — Together AI REST API |
| MiniMax client | `models/minimax.py` | Done — Together AI REST API |
| Gemma 4 client | `models/gemma4.py` | Done — Ollama local |
| Memory | `agent/memory.py` | Done |
| Planner | `agent/planner.py` | Done |
| Executor | `agent/executor.py` | Done |
| Critic | `agent/critic.py` | Done |
| Entry point | `main.py` | Done |
| Dataset (50 cases) | `dataset/cases/` | Done — all 50 cases, 3 tiers |
| Few-shot triplets | `dataset/few_shot/` | Done — 8 triplets |
| Unit tests | `tests/` | Done — 22 tests, all passing |
| Batch evaluator | `eval.py` | Done |
| Eval report | `eval_report.py` | Done |
| Web UI | `web/` | Done — FastAPI + SSE + dark-mode frontend |
| Docker | `Dockerfile` | Done — non-root sandboxed build |

## Pending Work

All major items are complete. The only remaining work is:
- [ ] **Evaluation:** run `python3 eval.py --models gemini --cases case_001 case_002` (requires API keys)
- [ ] **Demo video:** record a walkthrough for the Kaggle submission
- [ ] Add more dataset cases beyond 50 if needed for final benchmarking

## How to Add a New LLM

1. Create `models/<name>.py`
2. Implement `BaseModel`:
   - `complete(prompt: str) -> ModelResponse` — call the API, return text + token counts + latency
   - `name() -> str` — return the model identifier string
3. Add the model name to the `get_model()` function in `main.py`
4. Add the API key to `.env.example` and document it in this HANDOFF.md
5. Test: `python3 main.py --case case_001 --model <name>`

## How to Add a New Bug Case

1. Create `dataset/cases/case_NNN/` directory
2. Add three files:
   - `buggy.py` — the broken function (one function, one file for now)
   - `test_buggy.py` — deterministic pytest that FAILS on `buggy.py`
   - `golden.py` — the correct reference (never fed to agent; evaluation only)
3. Verify: `cd dataset/cases/case_NNN && python3 -m pytest test_buggy.py -v` → should FAIL
4. Optionally add a few-shot triplet to `dataset/few_shot/fs_NNN.json`

## Environment Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# Set GEMINI_API_KEY in .env (get from aistudio.google.com)
python3 main.py --case case_001 --model gemini
```

Required environment variables:
| Variable | Used by | Where to get |
|----------|---------|-------------|
| `GEMINI_API_KEY` | `models/gemini.py` | aistudio.google.com |
| `TOGETHER_API_KEY` | `models/qwen.py` (when implemented) | together.ai |

## Running Tests

```bash
python3 -m pytest tests/ -v
```

All 21 tests should pass with no API calls needed (Planner tests use mocked LLM).

## Known Gotchas

- **Memory is per-case, not global.** A new `Memory()` is created in `run_case()` for each invocation. This is intentional — keeps the token budget controllable and prevents cross-case error leakage.

- **`golden.py` is never fed to the agent.** It is only for human evaluation. Feeding it would invalidate the benchmark — the agent must fix bugs from traceback + source alone, matching real-world conditions.

- **`proposed_fix` is a literal replacement block, not a diff.** The Executor replaces lines `line_range[0]` through `line_range[1]` (1-indexed, inclusive) with the entire `proposed_fix` string. Correct indentation in `proposed_fix` is required — `ast.parse()` will catch syntax errors but not indentation logic errors.

- **pytest is invoked as `sys.executable -m pytest`.** This ensures the correct Python environment is used regardless of PATH. Do not change to bare `pytest` without verifying it resolves correctly on the target system.

- **Gemini model name.** Update `GEMINI_MODEL` in `config.py` if the model name changes. Current value: `"gemini-2.0-pro"`. Check aistudio.google.com for available models.

- **Token budget.** `MAX_MEMORY_TOKENS = 2000` in `config.py` controls memory context passed to the Planner. Increase if the agent repeats dead-end patches; decrease if hitting context window limits.

- **Single-file/function scope.** All 5 initial cases are single-function, single-file bugs. The patch schema (`line_range` + `proposed_fix`) is intentionally simple for this scope. Multi-file patches will require schema revision when expanding to the full 50-case dataset.
