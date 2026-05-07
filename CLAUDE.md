# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Venv uses Python 3.11 (required for click 8.x in external/)
python3.11 -m venv venv && venv/bin/pip install -r requirements.txt
cp .env.example .env   # then fill in API keys

# Run all unit tests
python3 -m pytest tests/ -v

# Run a single test file
python3 -m pytest tests/test_memory.py -v

# Run a single test by name
python3 -m pytest tests/test_planner.py::TestPlanner::test_foo -v

# Run agent on one case (case-folder PEC mode)
python3 main.py --case case_001 --model gemini

# Run benchmark matrix (manifest × models)
python -m benchmark.run_matrix \
  --manifest benchmark/manifests/pilot_hybrid.jsonl \
  --models gemma4 \
  --output logs/benchmark_results.jsonl \
  --max-steps 15 --timeout-s 180

# Analyze benchmark results
python -m benchmark.analyze --input latest --output logs/benchmark_report.json

# Build hybrid manifest (historical + synthetic)
python -m benchmark.build_manifest \
  --historical-source benchmark/data/historical_cases.sample.jsonl \
  --synthetic-source benchmark/data/synthetic_templates.sample.jsonl \
  --output benchmark/manifests/pilot_hybrid.jsonl \
  --target-count 30 --historical-ratio 0.7 --synthetic-ratio 0.3

# Materialize UI report
python -m benchmark.materialize_ui_report \
  --input latest --manifest benchmark/manifests/pilot_hybrid.jsonl \
  --output logs/benchmark_ui_report.json

# Launch web UI
uvicorn web.app:app --reload --port 8000

# Interactive benchmark REPL
python3 main.py   # (no --case flag)

# Docker
docker build -t bug-agent . && docker run -p 8000:8000 --env-file .env bug-agent
```

Required env vars: `GEMINI_API_KEY` (aistudio.google.com), `OPENROUTER_API_KEY` (Qwen via OpenRouter), `TOGETHER_API_KEY` (MiniMax via Together AI). Gemma4 is local via Ollama — no key needed.

## Architecture

### Planner → Executor → Critic Loop

```
Planner(LLM) → JSON patch plan → Executor(apply + pytest) → Critic(pass/retry/give up)
                                         ↑                          |
                                      Memory ←─────────────────────┘
```

The loop lives in `agent/case_runtime.py::run_case_with_pec()`. Each component is stateless except `Memory`, which is instantiated fresh per case — never shared across runs.

- **Planner** (`agent/planner.py`): maintains a `history` list of tool calls for multi-turn LLM conversation. Supports two modes: tool-calling (investigates via `read_file`, `edit_file`, `run_bash`) and legacy JSON-patch-plan mode. Skips repeated identical failing tool calls to reduce token waste.
- **Executor** (`agent/executor.py`): path-traversal-guarded writes (`os.path.realpath()` scope check), atomic patch apply (write to `.tmp` → `ast.parse()` → `os.replace()`), runs pytest as `subprocess([sys.executable, "-m", "pytest", ...], shell=False)`.
- **Critic** (`agent/critic.py`): returns `RESOLVED | RETRY | UNRESOLVED`. Builds structured retry context strings for JSON/schema/pytest failures.
- **Memory** (`agent/memory.py`): dead-end fingerprint is `(line_range_tuple, proposed_fix.strip())`. Prevents re-trying identical patches. `get_summary()` truncates to `MAX_MEMORY_TOKENS * 4` chars. Can be saved/loaded via `memory.json` inside each case directory (gitignored).

### Models (`models/`)

All models implement `BaseModel` ABC from `models/base.py`:
- `complete(prompt: str) -> ModelResponse` — returns text + token counts + latency
- `name() -> str`

| Name | Class | Backend |
|------|-------|---------|
| `gemini` | `GeminiModel` | google-genai SDK, `GEMINI_MODEL` in `config.py` |
| `qwen` | `QwenModel` | OpenRouter REST |
| `minimax` | `MiniMaxModel` | Together AI REST |
| `gemma4` | `Gemma4Model` | Ollama local (`BENCHMARK_OLLAMA_ENDPOINT`, default `http://127.0.0.1:11434`) |

To add a new model: implement `BaseModel`, wire it into `get_model()` in both `main.py` and `benchmark/runtime.py`.

### Dataset (`dataset/`)

- `dataset/cases/case_NNN/`: three files per case — `buggy.py` (broken), `test_buggy.py` (must FAIL on buggy, PASS after fix), `golden.py` (reference — **never fed to agent**).
- `dataset/few_shot/fs_NNN.json`: few-shot triplets for in-context prompting.
- 50 cases across 3 tiers: syntax/type (15), logic/algorithmic (20), contextual/scope (15).

### Benchmark Stack (`benchmark/`)

The benchmark pipeline evaluates the agent against a manifest of cases (internal dataset or external OSS repos):

1. **`manifest.py`** — `BenchmarkCase` dataclass schema + JSONL loader/writer.
2. **`injection.py`** — deterministically injects bugs into workspace files. Two modes: `"replace"` (old/new metadata) and synthetic patch (`@@\n-` / `\n+` format). Idempotent.
3. **`runtime.py`** — orchestrates one case execution: preflight check (test must FAIL after injection), runs planner, captures target + regression test exit codes.
4. **`run_matrix.py`** — iterates case × model × repetition, writes JSONL. Auto-timestamps output to avoid overwriting prior runs; `--allow-append` opts back to legacy behavior. Workspaces are copied to `logs/runs/<run_id>/workspaces/<attempt_id>` by default to prevent mutating committed `buggy.py`.
5. **`analyze.py`** — computes pass rates (with Wilson CI), latency percentiles, token/cost metrics, failure modes from a results JSONL.
6. **`build_manifest.py`** — composes hybrid manifests from `HistoricalBugAdapter` and `SyntheticMutationAdapter`.

Latest run artifacts are pointed to by `logs/latest_results_path.txt`, `logs/latest_events_path.txt`, `logs/latest_run_dir_path.txt`. Pass `--input latest` to `analyze` to resolve automatically.

### Web UI (`web/app.py`)

FastAPI app with SSE streaming for real-time agent output. Served via `uvicorn`.

### Logging (`logger.py`)

Structured JSON-lines logging. All events go to `LOG_PATH` (`logs/run.jsonl` by default). Each event has `event`, `case_id`, `data` fields.

## Key Invariants

- **`golden.py` is never fed to the agent** — only for human/automated evaluation after the fact.
- **Memory is per-case**: a new `Memory()` is created per `run_case_with_pec()` call. Cross-case state leakage is a bug.
- **`proposed_fix` is a literal replacement block**, not a diff — the Executor replaces lines `line_range[0]..line_range[1]` (1-indexed, inclusive) with the full string. Indentation must be correct; `ast.parse()` catches syntax errors only.
- **Preflight gate**: in benchmark mode, `test_command` must fail *after* injection. Cases where the test already passes are marked `invalid_benchmark_case`.
- **Token budget**: `MAX_MEMORY_TOKENS = 2000` in `config.py` controls memory context size passed to Planner.
