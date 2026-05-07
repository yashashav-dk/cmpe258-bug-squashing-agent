# Speaker Notes — CMPE 258 Bug-Squashing Agent

**Total target: ~6-7 min content + demo. ~40-50s per slide.**

Speaker split:
- **Pranav** — slides 1, 2, 3
- **Yash** — slides 4, 5, 6
- **Saransh** — slides 7, 8, 9, 10 (segue into live demo)

---

## Slide 1 — Title (Pranav)

> "Hi everyone, we're Pranav, Yash, and Saransh, and today we're presenting our autonomous bug-squashing agent for CMPE 258.
>
> The core question: can an LLM agent locate and fix Python bugs end-to-end without a human in the loop? Read the code, propose a patch, run pytest, and iterate until the tests go green.
>
> We evaluated this on two benchmarks — a synthetic dataset of 52 curated bugs, and three real defects we injected into the pallets/click library, tested across four LLMs.
>
> Three headline numbers up front: 57% pass on the synthetic dataset with Qwen 2.5 72B, 33% on real OSS bugs with Gemini 3 Pro, and a 3-to-3.4× token reduction with 2.5-to-2.7× latency improvement compared to the Gemini CLI baseline.
>
> I'll start with the architecture."

**Transition cue:** advance to slide 2.

---

## Slide 2 — Architecture (Pranav)

> "The agent is a Planner-Executor-Critic loop with a Memory.
>
> The Planner is the LLM. It has three tools: `read_file` to look at code in targeted ranges, `edit_file` to propose a patch by line range and replacement block, and `run_bash` to execute pytest as the oracle.
>
> The Executor takes a proposed patch, writes it atomically — write to a temp file, run `ast.parse` to catch syntax errors, then `os.replace`. It also enforces a path-traversal guard via `realpath` so the agent can't write outside the case sandbox.
>
> The Critic inspects test output and returns one of three verdicts: resolved, retry, or unresolved. On retry, it builds structured context — compact diff plus failure summary — and feeds that back to the Planner.
>
> The Memory tracks dead-end fingerprints. If a patch on the same line range was already proven to fail, the Planner skips it. That alone saves a meaningful chunk of tokens.
>
> One key invariant: the golden reference is never fed to the agent. It's only used post-hoc for evaluation. And memory is per-case — a fresh instance per run, no cross-case leakage."

**Transition cue:** "Let's look at how we evaluated this."

---

## Slide 3 — Two Benchmarks (Pranav)

> "We evaluated on two complementary benchmarks because each tells you something different.
>
> The synthetic dataset is 52 curated Python bugs we generated through algorithmic mutations — think off-by-ones, type errors, scope bugs, logic inversions. 49 of them passed our preflight gate, split into Easy and Medium tiers. We ran this against Qwen 2.5 72B over OpenRouter, with a 10-retry budget and a 180-second timeout.
>
> The synthetic side is controlled. It isolates the agent's capability from the messiness of real codebases.
>
> The OSS side is the opposite. We pinned pallets/click at v8.3.2 — a real CLI library with around 1,200 lines of source — and injected three deterministic, idempotent string-replace bugs. The oracle is the repository's own pytest suite, not something we wrote.
>
> Real complexity: large files, multi-module dependencies, semantic bugs that require understanding design intent.
>
> Yash will walk through the synthetic results."

**Transition:** "Yash, take it away." (Hand off.)

---

## Slide 4 — Synthetic Results (Yash)

> "Thanks Pranav. So on the synthetic dataset with Qwen 2.5 72B, we hit 57% overall pass rate across 49 valid cases, at an average of 32 seconds per case.
>
> But the breakdown is the interesting part: 65% on Easy, only 22% on Medium. That gap matters.
>
> Looking at the failure-mode doughnut on the right: 28 cases resolved, 17 are localization failures, 3 are false-resolved, and 1 environment error.
>
> Localization failure is our biggest blocker. The model sees the symptom — it knows there's a bug, often even names the right function — but it patches the wrong line. The off-by-one in the line range is the usual culprit.
>
> False-resolved is rarer but worth flagging: that's the agent declaring victory when the test didn't actually pass. We catch these because pytest is the oracle, but it shows you can't trust the model's self-report alone."

**Transition cue:** "Now let's look at real bugs in a real codebase."

---

## Slide 5 — OSS Bug Catalog (Yash)

> "We injected three bugs into pallets/click at three difficulty tiers.
>
> Easy: in `shell_completion.py`, we changed a token to `token.upper()`. Single-token mutation in a small function. Whoever's watching will see this come through cleanly.
>
> Medium: in `types.py`, we added one to a return value — `value` becomes `value + 1`. The bug only manifests on specific integer inputs, so the model has to actually trace what the test expects.
>
> Hard: in `parser.py`, we truncated the prefix set from `{"-", "--"}` to just `{"-"}`. This breaks long-option parsing across the entire CLI. It ripples through multiple files.
>
> Each case has a strict preflight contract: the test must FAIL after injection, and PASS after a correct fix. If a test passes both before and after, we mark it `invalid_benchmark_case` and skip. That preflight gate prevents false positives in the metrics.
>
> These three span the difficulty space — surface mutation, type-coercion logic, and architectural semantics."

**Transition cue:** "Here's how the four models did."

---

## Slide 6 — OSS Resolution Matrix (Yash)

> "Twelve total runs — four models times three cases. One pass.
>
> Gemini 3 Pro resolves the Easy case in 2 retries, 119 seconds. That's it. Every other cell on this grid is a fail.
>
> Importantly, look at the failure profile: 87% are pure localization failures. The agent identifies the right file, the right function, even the right symptom — but it doesn't pinpoint the exact line. We saw zero false-resolved on OSS and zero test regressions, which means every patch the agent applied was at least syntactically safe and didn't break anything else. The patches just didn't fix the bug.
>
> The Easy case Gemini Pro solved is meaningful — it shows the loop works. But the 0/3 across Flash, Qwen, and Gemma on the same cases tells you that on real-codebase complexity, scaffolding alone isn't enough. The model has to be capable of multi-hop reasoning to map a test traceback to the actual mutation site."

**Transition:** "Saransh will dig into where our agent does win — efficiency."

---

## Slide 7 — Efficiency vs Baseline (Saransh)

> "Thanks Yash. Even when our agent and the Gemini CLI baseline produce the same resolution outcome — same case pass, same case fail — the cost profile is dramatically different.
>
> Across all four models, we cut input tokens by 3.1× to 3.4×. Output tokens by 2.2× to 2.6×. And wall-clock latency by 2.5× to 2.7×.
>
> Concrete numbers: on Gemini 3 Pro, our agent uses 178K input tokens across the 3 cases, versus 588K for the CLI baseline. The output side is 3,343 tokens versus 8,124.
>
> The CLI baseline isn't doing anything wrong — it's just not optimized for repair loops. It dumps full files, repeats full tracebacks, doesn't track what it's already tried.
>
> Important caveat: this is at identical resolution outcomes. We're not buying speed at the cost of correctness. We're getting the same results for a third of the cost."

**Transition:** "So what actually drives these two different metrics?"

---

## Slide 8 — What Drives What (Saransh)

> "This is the takeaway slide. Two factors, two outcomes.
>
> Pass rate is driven by model reasoning depth. Same scaffolding, different model: Gemini Pro maps a traceback to a mutation in 2 steps; Gemini Flash on the same case burns all 10 retries and gives up. On synthetic, Qwen drops from 65% Easy to 22% Medium — same agent, harder reasoning. No amount of retry logic compensates for that.
>
> Efficiency, on the other hand, is purely architectural. Four things drive it:
>
> First, targeted tool calls — we read just the relevant function, not the entire file. Second, dead-end memory — we skip patches we've already proven to fail. Third, structured retry context — a compact diff and failure summary, not a re-sent traceback dump. Fourth, the planner persona primes the model to emit minimal JSON patch plans rather than verbose explanations.
>
> Same outcomes, much lower cost. That's the core engineering contribution here."

**Transition cue:** "Let me wrap with our findings and what's next."

---

## Slide 9 — Conclusion + Future Work (Saransh)

> "Three findings.
>
> One: model quality determines pass rate. The gap between Gemini Pro and Flash on the same scaffold dwarfs any agent-level optimization we tried.
>
> Two: agent design determines efficiency. We get 3-plus times input-token reduction and 2.5-times latency improvement at zero loss in resolution quality.
>
> Three: synthetic difficulty does not equal OSS difficulty. 57% on synth versus at most 33% on real bugs reveals that large-file localization and multi-module context are the real unsolved challenges.
>
> Four directions forward. AST-guided patch targeting would eliminate most of our line-offset localization errors. Longer retry budgets paired with curriculum difficulty scaling. Cross-file retrieval — RAG over the repo — for architectural bugs that span modules. And hard-tier synthetic cases to bridge the gap with OSS complexity.
>
> With that, let's switch to a live demo."

**Transition cue:** "Switching to the demo now." Advance to slide 10. Prepare to alt-tab or switch screen-mirror to terminal/UI.

---

## Slide 10 — Demo (Saransh)

> "We'll run the agent on a single case end-to-end so you can see the loop in action — Planner reads the buggy file, proposes a patch, Executor runs pytest, and we either land green or iterate. Let me bring up the UI."

**Action:** switch screen mirror from slides to demo UI (`uvicorn web.app:app --reload --port 8000` → `http://localhost:8000`).

**Demo checklist (have ready before talk starts):**
- Web UI running on `localhost:8000`
- A pre-loaded case to run (suggest: a Synthetic Easy case or the OSS `split_arg_upper` case for guaranteed pass)
- Logs visible in a second terminal pane
- API keys loaded in `.env` (Gemini)

**Backup plan if demo fails:**
- Pre-recorded screenshot or asciinema cast of a successful run
- Or fall back to terminal: `python3 main.py --case case_001 --model gemini`

---

## Timing notes

| Speaker | Slides | Target time |
|---|---|---|
| Pranav | 1-3 | ~2:00 |
| Yash | 4-6 | ~2:00 |
| Saransh | 7-9 + demo intro | ~2:00 + demo |

Aim for **40-45 seconds per content slide**. Demo: 2-3 minutes max.

## Q&A prep — likely questions

1. **"Why not use SWE-bench?"** — SWE-bench is the gold standard but takes weeks to set up per repo. We wanted controlled difficulty tiers we could iterate on quickly, plus one real OSS sample for grounding.
2. **"Why is Gemini Flash so much slower than Qwen here?"** — Flash burns retries on cases it can't solve. Higher per-retry latency × 10 retries = much higher wall time. Qwen also fails but its per-call latency is lower.
3. **"What about cost in dollars?"** — Token reductions translate roughly linearly to API cost. At Gemini Pro pricing, the 3.3× input cut is ~$X savings per 100 cases (do the math live if pressed).
4. **"How is this different from Devin / SWE-agent / Aider?"** — Comparable scaffolding category, but our contribution is the side-by-side benchmark with explicit token/latency accounting against a CLI baseline at identical resolution outcomes.
5. **"Why pallets/click specifically?"** — Pure-Python, well-tested, MIT-licensed, large enough to be non-trivial (1,200+ lines), small enough to inject + verify quickly. Good middle-ground.
