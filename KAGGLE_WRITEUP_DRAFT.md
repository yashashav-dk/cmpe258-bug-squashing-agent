# CMPE 258 Auto-Bug-Squashing Agent (Gemma 4 Edition)
## An Autonomous AI Safety Net for the Future of Education

### Track
Special Technology Track: **Ollama**  
Impact Track: **Future of Education**

---

### Introduction: The Solitude of the Junior Developer

Every new programmer encounters a moment of deep frustration: a massive traceback that halts their progress. While experienced developers have built an intuition for interpreting raw stack traces, learners often resort to endless copy-pasting into Stack Overflow or chat interfaces, resulting in disjointed context and hallucinated, un-runnable code.

Our objective was to build a system that acts as a localized **AI Coding Tutor** powered by **Gemma 4** running locally via **Ollama** — an agent that can autonomously investigate a buggy Python file, reason about the failure, apply a targeted fix, and verify it with pytest, all without sending the student's code to a remote server.

---

### System Architecture

The CMPE 258 Bug Squashing Agent departs from typical deterministic loops or linear scripts. It features an **autonomous multi-turn Planner → Executor → Critic loop** built entirely from scratch in Python.

```
User submits buggy.py
        │
        ▼
┌─────────────────────────────────────────────────────┐
│                    Planner (LLM)                    │
│  Gemma 4 (Ollama) · Gemini · Qwen · MiniMax        │
│  Receives: code + traceback + memory summary        │
│  Emits: tool calls (read_file / edit_file / bash)   │
└────────────────────────┬────────────────────────────┘
                         │ tool calls
                         ▼
┌─────────────────────────────────────────────────────┐
│               Tool Executor (Sandbox)                │
│  read_file  · edit_file  · run_bash (shell=False)   │
│  Atomic writes + AST syntax validation               │
│  Path traversal protection (realpath scope check)   │
└────────────────────────┬────────────────────────────┘
                         │ pytest result
                         ▼
┌─────────────────────────────────────────────────────┐
│                     Critic                           │
│  Evaluates pass/fail · updates Memory               │
│  Dead-end prevention (patch fingerprint registry)   │
│  Dream Consolidation (durable learning extraction)  │
└─────────────────────────────────────────────────────┘
```

#### 1. Gemma 4 as the Core Local Reasoning Engine
We implemented a `Gemma4Model` class that routes all inference through `http://localhost:11434/api/chat` (the Ollama API). By keeping inference local, students can safely analyze proprietary homework code or exam submissions without transmitting sensitive material to external servers.

Gemma 4 receives a structured OpenAI-compatible tool schema built dynamically from Python function signatures using `inspect`, ensuring argument names and descriptions always match the actual tool implementations.

#### 2. Native Tool-Calling Loop
The Planner presents Gemma 4 with three tools:
- **`read_file(filepath)`** — reads the buggy file and any tests
- **`edit_file(filepath, old_content, new_content)`** — applies a targeted fix via exact-string replacement
- **`run_bash(command, cwd)`** — runs `pytest` to verify whether the fix works

The agent autonomously navigates the file system, forms hypotheses, tests them, and backtracks when a patch fails — exactly like a human engineer would.

#### 3. Memory & Dead-End Prevention
The `Memory` module maintains a **patch fingerprint registry** that prevents the agent from re-attempting a patch it already tried. It also provides a rolling summary of iteration history for the Planner's context window, keeping token usage bounded.

#### 4. The "Dream" Consolidation System
Drawing inspiration from advanced AI orchestration patterns, after a successful debug session the `Memory.consolidate_dream()` mechanism prompts Gemma 4 to extract a **durable learning** — identifying the root syntactic misunderstanding (e.g., off-by-one in `range()`) rather than just leaving the user with patched code. This transforms a bug fix into an educational moment.

#### 5. Dataset: 50 Bug Cases × 3 Difficulty Tiers
We curated a 50-case benchmark with fully deterministic pytest scripts:

| Tier | Cases | Bug Patterns |
|------|-------|-------------|
| Tier 1 — Syntax / Type | 001–018 | Wrong return type, integer division, `append` vs `extend`, missing type conversion, string vs list |
| Tier 2 — Logic / Algorithmic | 019–036 | Off-by-one in `range()`, wrong accumulator init, Fibonacci base case, flipped palindrome check, wrong operator, two-sum complement, Kadane's init, binary search `lo=mid` infinite loop |
| Tier 3 — Contextual / Scope | 037–050 | Mutable default argument, late-binding closure, missing `nonlocal`, class vs. instance attribute, generator exhaustion, list mutation during iteration, missing `super().__init__()`, wrong exception type |

#### 6. Multi-Model Benchmarking
The same agent loop runs against four models for direct comparison:
- **Gemma 4** (Ollama, local)
- **Gemini 2.0 Flash** (Google AI Studio)
- **Qwen-2.5 72B** (Together AI)
- **MiniMax-M2.5** (Together AI)

`eval.py` runs all 50 cases × all models and writes structured metrics (pass rate, steps, latency p50/p90, token usage) to `logs/eval_results.jsonl`. `eval_report.py` renders per-model and per-tier Rich tables.

#### 7. Real-Time Web Interface
A FastAPI backend streams agent reasoning steps to a dark-mode web UI via **Server-Sent Events (SSE)**. Students can watch every tool call, model response, and pytest result appear in real time — making the debugging process fully transparent and educational.

```
uvicorn web.app:app --reload --port 8000
```

---

### Why Gemma 4 and Ollama?

For an educational tool requiring strict data privacy, zero-latency feedback, and robust reasoning over deep tracebacks, running **Gemma 4 local-first via Ollama** is the natural choice:

- **Privacy** — Student code never leaves the machine
- **Latency** — No network round-trips; responses begin within seconds on consumer hardware
- **Capability** — Gemma 4's tool-calling capability proved immensely effective at maintaining context across multi-step debugging traces and generating precise `edit_file` patches
- **Accessibility** — A single `ollama pull gemma4` command enables any student to run the full agent with no API keys required

---

### Setup

```bash
git clone https://github.com/yashashav-dk/cmpe258-bug-squashing-agent
cd cmpe258-bug-squashing-agent
pip install -r requirements.txt
cp .env.example .env

# Option A: Local mode with Gemma 4 (no API key needed)
ollama pull gemma4
python3 main.py --case case_001 --model gemma4

# Option B: Cloud mode with Gemini
# Add GEMINI_API_KEY to .env
python3 main.py --case case_001 --model gemini

# Option C: Web UI
uvicorn web.app:app --reload --port 8000

# Option D: Full benchmark (requires API keys)
python3 eval.py --models gemma4 gemini
python3 eval_report.py
```

---

### Future Impact

By open-sourcing this tool, we give students a transparent window into professional debugging methodology. Instead of a black-box chatbot, they watch Gemma 4 **reason step by step** — reading files, forming hypotheses, running tests — in a rich interactive CLI or web UI. The Dream Consolidation system turns each fix into a reusable learning artifact.

Future work: per-student memory persistence across sessions, VS Code extension integration, and a leaderboard tracking debugging performance across all 50 cases × hardware configurations.

---

### Team

- **Pranav Trivedi** — Agent architecture, planner/critic loop, memory system
- **Yashashav DK** — Model integrations (Gemini, Qwen, MiniMax, Gemma 4), eval pipeline
- **Saransh Soni** — Dataset curation (50 cases × 3 tiers), web UI, Docker

---

### Media

- 🎥 **Demo Video**: *(link your YouTube demo here before submission)*
- 💻 **Code Repository**: https://github.com/yashashav-dk/cmpe258-bug-squashing-agent
