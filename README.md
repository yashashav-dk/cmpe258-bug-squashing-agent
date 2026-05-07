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
Planner(LLM) → JSON patch plan → Executor(apply + pytest) → Critic(pass/retry/give up)
                                         ↑                          |
                                      Memory ←─────────────────────┘
```

- **Planner:** Analyzes traceback + source + memory → structured JSON patch plan
- **Executor:** Validates scope via `os.path.realpath()`, atomically applies patch (`ast.parse` + `os.replace`), re-runs pytest via `subprocess` with `shell=False`
- **Critic:** Drives retry loop; terminates on PASS or `MAX_RETRIES`
- **Memory:** Tracks edit history, error evolution, and dead-end patches per case (not global chat history)

### Models Compared

| Model | Role | Status |
|-------|------|--------|
| Gemini 2.0 Flash | Baseline | ✅ Fully wired (new google-genai SDK) |
| Qwen-2.5 72B | Open SOTA | ✅ Implemented via Together AI |
| MiniMax-M2.5 | Open MoE | ✅ Implemented via Together AI |
| Gemma 4 | Local / Ollama | ✅ Implemented via Ollama |

## Current Progress

- [x] Planner→Executor→Critic autonomous loop (tool-calling, multi-step)
- [x] 50 bug cases across all 3 tiers with deterministic pytest scripts
- [x] 8 few-shot triplets for in-context prompting
- [x] Atomic patch writes with `ast.parse()` syntax validation
- [x] Path traversal protection + subprocess `shell=False`
- [x] Per-case Memory with dead-end detection and Dream consolidation
- [x] Structured JSON-lines logging (prompts, patches, verdicts, token counts, latency)
- [x] 22 unit tests, all passing
- [x] Gemini 2.0 Flash (new google-genai SDK)
- [x] Qwen-2.5 72B via Together AI
- [x] MiniMax-M2.5 via Together AI
- [x] Gemma 4 via Ollama (local, private)
- [x] Interactive Rich CLI (`main.py`)
- [x] Web UI with real-time SSE streaming (`web/app.py`)
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
