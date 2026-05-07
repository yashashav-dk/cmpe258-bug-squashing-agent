# Autonomous Bug Squashing Agent System
*(Targeting the Gemma 4 Good Kaggle Hackathon — Ollama & Future of Education Tracks)*

**CMPE 258 — Deep Learning, Spring 2026 | San Jose State University**

## Team Members

| Name | Student ID | Contribution |
|------|-----------|--------------|
| Pranav Trivedi | 019089512 | Agent architecture, Planner module, Gemini integration |
| Yashashav DK | 017856371 | Dataset curation, Executor module, safety guardrails |
| Saransh Soni | 019115122 | Memory module, Critic module, logging infrastructure |

## Project Description

An autonomous multi-agent system that analyzes failing `pytest` tracebacks and buggy Python source files, identifies root causes, and directly edits code to pass tests — without human intervention.

**Architecture:** Planner → Executor → Critic loop built from scratch in Python. No LangChain, AutoGen, or CrewAI.

**Success metric:** Binary pass/fail on pytest suite after agent intervention, measured across 50 bug cases and 3 LLMs.

## Dataset

- **50 buggy Python functions** (backend, APIs, auth) paired with deterministic pytest scripts
- **3 tiers:**
  - Syntax/Type (15 cases): missing colons, wrong types, off-by-one indexing
  - Logic/Algorithmic (20 cases): flipped conditionals, wrong operator precedence
  - Contextual/Scope (15 cases): variable shadowing, closure capture, wrong signatures
- **5–8 few-shot triplets** held out for in-context prompting
- **Initial submission:** 5 representative hand-crafted cases across all tiers

Each case: `buggy.py` + `test_buggy.py` + `golden.py` (reference, never fed to agent)

## Approach

### Planner–Executor–Critic Architecture

```
┌──── PEC outer loop (per case, attempt = 1..max_attempts) ────┐
│                                                              │
│   Planner (tool-loop) ─► edits buggy code via scoped tools   │
│        │                                                     │
│        ▼                                                     │
│   Executor.verify(target_test, regression_test)              │
│        │ subprocess (argv form, shell=False where parsable)  │
│        ▼                                                     │
│   Critic.evaluate(passed, traceback, memory, attempt)        │
│        │                                                     │
│        ├── RESOLVED → return                                 │
│        ├── RETRY    → augment objective with retry context   │
│        └── UNRESOLVED → return (budget exhausted)            │
└──────────────────────────────────────────────────────────────┘
```

Implementation: `benchmark/orchestrator.py` (`PECOrchestrator`, `BenchmarkExecutor`) + `agent/critic.py` (`Critic`, `CaseResult`). The `AgentRuntime` in `benchmark/runtime.py` instantiates and drives the loop.

- **Planner** (`agent/planner.py`): tool-loop over scoped benchmark tools (`run_target_test`, `run_regression_test`, `read_file`, `edit_file`, `list_dir`). Emits in-place edits and a final natural-language summary; not a structured patch object — kept as tool-loop because Executor verification is the truth source.
- **Executor** (`benchmark/orchestrator.py:BenchmarkExecutor`): runs target + regression tests independently of the Planner, returning ground-truth pass/fail. Uses argv form (`shell=False`) when commands are tokenizable; falls back to shell only for legacy compound commands.
- **Critic** (`agent/critic.py`): emits explicit `RESOLVED | RETRY | UNRESOLVED` per attempt. Builds retry context fed into next attempt's objective when budget remains.
- **Memory** (`agent/memory.py`): per-case state, dead-end fingerprints. Single instance per orchestrator run.

#### Proposal deltas

| Proposal claim | Implemented | Note |
|---|---|---|
| `Gemini 3.1 Pro` | `gemini-2.5-flash` (`config.py:8`) | New `google-genai` SDK; 3.x Pro not yet GA at scope-freeze |
| Planner emits structured JSON patch plan | Tool-loop with in-place edits | Functionally equivalent: Executor still owns verification; Critic still owns retry |
| Single-pass eval | Multi-attempt PEC outer loop (`--max-attempts`) | Default `max_attempts=1` preserves prior behavior; `>1` enables Critic-driven retry |

### Models Compared

| Model | Role | Status |
|-------|------|--------|
| Gemini 2.0 Flash | Baseline | ✅ Fully wired (new google-genai SDK) |
| Qwen-2.5 72B | Open SOTA | ✅ Implemented via Together AI |
| MiniMax-M2.5 | Open MoE | ✅ Implemented via Together AI |
| Gemma 4 | Local / Ollama | ✅ Implemented via Ollama |

## Benchmark Contract (final reporting)

Locked configuration used to generate the submission-grade report. Reproducing these numbers requires only the commands below.

| Field | Value |
|---|---|
| Manifest | `benchmark/manifests/pilot_synthetic_new4.jsonl` |
| Models | `gemini`, `gemma4` (Ollama local) |
| `--max-steps` | `15` |
| `--max-attempts` | `1` (Critic outer-loop budget; multi-attempt available) |
| `--timeout-s` | `180` |
| `--repetitions` | `1` |
| Random seed | `7` (manifest sampling), reproducible test injection |
| Pricing source | `benchmark/protocol.py:MODEL_PRICING_USD_PER_1M`, `PRICING_SOURCE` |

Reproduce:

```bash
# 1. ensure Ollama is running and gemma4 is pulled
ollama list | grep -E "^gemma4"   # expect a row

# 2. final matrix run
python -m benchmark.run_matrix \
  --manifest benchmark/manifests/pilot_synthetic_new4.jsonl \
  --models gemini,gemma4 \
  --output logs/final_results.jsonl \
  --max-steps 15 --max-attempts 1 \
  --timeout-s 180 --repetitions 1

# 3. analyze (emits per-model rows: pass_rate, latency p50/p90/p99,
#    retry-depth distribution, estimated cost, cost_per_successful_fix_usd)
python -m benchmark.analyze \
  --input logs/final_results.jsonl \
  --output logs/benchmark_report.json
```

## Current Progress

- [x] Planner → Executor → Critic outer loop with explicit state transitions (`benchmark/orchestrator.py`)
- [x] 50 bug cases across all 3 tiers with deterministic pytest scripts
- [x] 8 few-shot triplets for in-context prompting
- [x] Atomic patch writes with `ast.parse()` syntax validation
- [x] Path traversal protection + Executor uses argv form (`shell=False`) where tokenizable
- [x] Per-case Memory with dead-end detection and Dream consolidation
- [x] Structured JSON-lines logging (prompts, patches, verdicts, token counts, latency, PEC attempt records)
- [x] 51 unit tests, all passing
- [x] Gemini (`gemini-2.5-flash` via google-genai SDK)
- [x] Qwen-2.5 72B via Together AI
- [x] MiniMax-M2.5 via Together AI
- [x] Gemma 4 via Ollama (local, private)
- [x] Interactive Rich CLI (`main.py`)
- [x] Web UI for benchmark runs (`web/app.py`); live-stream UI is planned (see `docs/spec.md`)
- [x] Batch eval runner (`eval.py`) + report generator (`eval_report.py`)
- [x] Docker sandboxing (`Dockerfile`)

## Next Steps

1.  Run full 50-case × 4-model evaluation: `python3 eval.py`
2.  Review report: `python3 eval_report.py`
3.  Launch web UI: `uvicorn web.app:app --reload --port 8000`
4.  Deploy via Docker: `docker build -t bug-agent . && docker run -p 8000:8000 --env-file .env bug-agent`

## Setup

```bash
git clone https://github.com/yashashav-dk/cmpe258-bug-squashing-agent
cd cmpe258-bug-squashing-agent
pip install -r requirements.txt
cp .env.example .env
# Fill in GEMINI_API_KEY and/or TOGETHER_API_KEY in .env

# CLI mode
python3 main.py --case case_001 --model gemini

# Web UI
uvicorn web.app:app --reload --port 8000

# Batch eval (all 50 cases × all models)
python3 eval.py --models gemini
python3 eval_report.py
```

## Hybrid Benchmark (OSS + Injection)

The repository now includes an extensible benchmark stack under `benchmark/` for evaluating the agent on open-source repos with hybrid case generation:

- historical real bugs (curated commit-derived cases),
- deterministic synthetic mutations (operator-based),
- adapter contract so source strategy can be swapped without runner refactors.

### Build Hybrid Manifest

```bash
python -m benchmark.build_manifest \
  --historical-source benchmark/data/historical_cases.sample.jsonl \
  --synthetic-source benchmark/data/synthetic_templates.sample.jsonl \
  --output benchmark/manifests/pilot_hybrid.jsonl \
  --target-count 30 \
  --historical-ratio 0.7 \
  --synthetic-ratio 0.3
```

### Run Matrix (model × case)

```bash
python -m benchmark.run_matrix \
  --manifest benchmark/manifests/pilot_hybrid.jsonl \
  --models gemma4 \
  --output logs/benchmark_results.jsonl \
  --repetitions 1
```

### Analyze Results

```bash
python -m benchmark.analyze \
  --input logs/benchmark_results.jsonl \
  --output logs/benchmark_report.json
```

### Benchmark Report Metrics

`benchmark/analyze.py` now emits per-model metrics aligned to proposal reporting:

- pass-rate metrics: `runs`, `resolved`, `unresolved`, `pass_rate`, `pass_rate_wilson_95`
- latency metrics: `latency_ms.avg`, `latency_ms.p50`, `latency_ms.p90`, `latency_ms.p99`
- retry-depth proxy: `retry_depth.avg`, `retry_depth.max`, `retry_depth_distribution`
- token and cost metrics:
  - `token_usage.input_tokens`, `token_usage.output_tokens`
  - `estimated_cost_usd.input`, `estimated_cost_usd.output`, `estimated_cost_usd.total`
  - `cost_per_successful_fix_usd`
- `failure_modes` and `consistency_checks`

Cost is computed deterministically from token totals using model pricing assumptions in
`benchmark/protocol.py` (`MODEL_PRICING_USD_PER_1M`). Local `gemma4` defaults to zero API token cost.

### Reproducible Run -> Analyze Sequence

```bash
python -m benchmark.run_matrix \
  --manifest benchmark/manifests/pilot_hybrid.jsonl \
  --models gemini,qwen,minimax,gemma4 \
  --output logs/final_results.jsonl \
  --max-steps 15 \
  --timeout-s 180 \
  --repetitions 1

python -m benchmark.analyze \
  --input logs/final_results.jsonl \
  --output logs/benchmark_report.json
```

See `benchmark/README.md` and `docs/benchmark_protocol.md` for rigorous protocol details.

Recent runtime hardening:
- planner now validates malformed tool-call payloads and reports `Unknown tool` / invalid payload explicitly,
- repeated identical failing tool calls are skipped to reduce step/token waste,
- idempotent `edit_file` behavior treats already-applied patches as no-op success.

## Project Structure

```
├── main.py              # Entry point: --case <id> --model <name>
├── config.py            # MAX_RETRIES, MAX_MEMORY_TOKENS, model/path settings
├── logger.py            # JSON-lines structured logging
├── agent/
│   ├── planner.py       # LLM prompt + JSON patch plan
│   ├── executor.py      # Atomic patch apply + pytest runner
│   ├── critic.py        # Retry/resolve/unresolved decision
│   └── memory.py        # Per-case state tracking
├── models/
│   ├── base.py          # BaseModel ABC + ModelResponse dataclass
│   ├── gemini.py        # Gemini client (wired)
│   ├── qwen.py          # Qwen stub
│   └── minimax.py       # MiniMax stub
├── dataset/
│   ├── cases/           # Bug cases (buggy.py, test_buggy.py, golden.py)
│   └── few_shot/        # In-context prompting triplets (JSON)
├── benchmark/           # Hybrid OSS benchmark generation + execution + analysis
└── tests/               # Unit tests for all modules
```

## References

- Gemini API: [aistudio.google.com](https://aistudio.google.com)
- Qwen-2.5-Coder: [github.com/QwenLM/Qwen2.5-Coder](https://github.com/QwenLM/Qwen2.5-Coder)
- MiniMax-M2.5: [huggingface.co/minimax](https://huggingface.co/minimax)
- Together AI: [together.ai](https://together.ai)
- SWE-Bench: [swebench.com](https://swebench.com)
- pytest: [docs.pytest.org](https://docs.pytest.org)
