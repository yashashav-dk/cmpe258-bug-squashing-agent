# Autonomous Bug Squashing Agent System

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
| Gemini 2.0 Pro | Baseline | Fully wired |
| Qwen-2.5 72B | Open SOTA | Stub (next milestone) |
| MiniMax-M2.5 | Open MoE | Stub (next milestone) |

## Current Progress

- [x] Planner→Executor→Critic loop functional end-to-end with Gemini
- [x] 5 hand-crafted bug cases across all 3 tiers with deterministic pytest scripts
- [x] 3 few-shot triplets for in-context prompting
- [x] Atomic patch writes with `ast.parse()` syntax validation
- [x] Path traversal protection + subprocess `shell=False` allowlist
- [x] Per-case Memory with dead-end detection and token budget
- [x] Structured JSON-lines logging (prompts, patches, verdicts, token counts, latency)
- [x] Full unit test suite (21 tests, all passing)
- [ ] Qwen-2.5 72B integration (next milestone)
- [ ] MiniMax-M2.5 integration (next milestone)
- [ ] Remaining 45 bug cases
- [ ] Web UI
- [ ] Docker sandboxing
- [ ] Full evaluation across all 50 cases × 3 models

## Next Steps

1. Wire Qwen-2.5 72B via Together AI (`models/qwen.py`)
2. Wire MiniMax-M2.5 (`models/minimax.py`)
3. Expand dataset to 50 cases across all 3 tiers
4. Build Web UI (upload files, select model, observe agent reasoning in real time)
5. Add Docker sandbox for safe execution
6. Run full evaluation and report metrics (pass rate, latency p50/p90/p99, cost/fix, retry depth)

## Setup

```bash
git clone https://github.com/yashashav-dk/cmpe258-bug-squashing-agent
cd cmpe258-bug-squashing-agent
pip install -r requirements.txt
cp .env.example .env
# Add your GEMINI_API_KEY to .env (get from aistudio.google.com)
python3 main.py --case case_001 --model gemini
```

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
└── tests/               # Unit tests for all modules
```

## References

- Gemini API: [aistudio.google.com](https://aistudio.google.com)
- Qwen-2.5-Coder: [github.com/QwenLM/Qwen2.5-Coder](https://github.com/QwenLM/Qwen2.5-Coder)
- MiniMax-M2.5: [huggingface.co/minimax](https://huggingface.co/minimax)
- Together AI: [together.ai](https://together.ai)
- SWE-Bench: [swebench.com](https://swebench.com)
- pytest: [docs.pytest.org](https://docs.pytest.org)
