# Spec — Proposal Closure Status

Source proposals: `docs/proposal_closure_todo.md`, `docs/benchmark_todo.md`, `HANDOFF.md`, `README.md`.
Generated: 2026-05-06. Status against HEAD `ebf7e37`.

Legend: ✅ met · 🟡 partial · ❌ pending · — n/a

---

## 1. Top-Level Definition of Done

| # | Item | Status | Evidence / Gap |
|---|------|--------|----------------|
| 1 | Reproducible non-empty end-to-end report | ❌ | `logs/benchmark_report.json` parses to `{}` (no per-model rows). `logs/final_results.jsonl` missing. Need Phase 1 run. |
| 2 | Report has pass rate, latency p50/p90/p99, retry depth, failure modes, cost/fix | ✅ schema · ❌ data | Schema implemented in `benchmark/analyze.py:113-141`. No populated artifact yet. |
| 3 | Architecture narrative matches implementation | ❌ | `README.md:18,36-39` claims formal Planner→Executor→Critic. Runtime is planner tool-loop (`agent/planner.py`). No legacy/deprecated labels. |
| 4 | UI/demo path supports proposal-level workflow | ❌ | `web/app.py` exposes only POST `/api/run-manifest`. No SSE/streaming, no file upload, no live step output. |
| 5 | Proposal-to-code traceability doc | ❌ | `docs/proposal_traceability.md` missing. |

---

## 2. Phase Status

### Phase 0 — Scope and Claims

| Task | Status | Evidence |
|------|--------|----------|
| T0.1 freeze manifest | ❌ | No README "benchmark contract" section. |
| T0.2 freeze model matrix | ❌ | Same. |
| T0.3 freeze runtime knobs | ❌ | Same. |
| T0.4 README contract section | ❌ | Missing. |
| T0.5 model delta (Gemini 3.1→2.5-flash) | ❌ | `config.py:8` uses `gemini-2.5-flash`; no delta doc. |
| T0.6 architecture delta (loop vs PEC) | ❌ | Not documented. |
| T0.7 claim consistency check | ❌ | Conflicts present (see §1.3). |

### Phase 1 — Benchmark Artifacts

| Task | Status | Evidence |
|------|--------|----------|
| T1.1 preflight model connectivity | ❌ | No preflight script wired. |
| T1.2 execute final matrix | ❌ | `logs/final_results.jsonl` absent. |
| T1.3 results integrity | ❌ | Cannot validate without artifact. |
| T1.4 latest pointer check | 🟡 | `logs/latest_results_path.txt` exists; target empty. |
| T1.5 generate analysis | ❌ | Report empty. |
| T1.6 non-empty schema rows | ❌ | `{}`. |
| T1.7 record run metadata | ❌ | None recorded. |

### Phase 2 — Metrics Parity (analyzer)

| Task | Status | Evidence |
|------|--------|----------|
| T2.1 p99 latency | ✅ | `analyze.py:115`. |
| T2.2 retry depth distribution | ✅ | `analyze.py:117-127`. |
| T2.3 patch size metric | ❌ | No `patch_size` in analyzer or runtime logs. |
| T2.4 model pricing table | ✅ | `benchmark/protocol.py:22 MODEL_PRICING_USD_PER_1M`. |
| T2.5 estimated cost | ✅ | `analyze.py:133`. |
| T2.6 cost per successful fix | ✅ | `analyze.py:138`. |
| T2.7 failure mode aggregation | 🟡 | `failure_mode_counts` aggregated (`analyze.py:64,79,144`); no taxonomy enforcement (`localization_failure`, `false_resolved`, etc.) — falls through to `unknown`. |
| T2.8 schema doc | ❌ | No schema reference in docs. |

### Phase 3 — Architecture Alignment

| Task | Status | Evidence |
|------|--------|----------|
| T3.1 strategy decision (A vs B) | ❌ | Not recorded. |
| T3.2 update README diagram | ❌ | Diagram still implies formal PEC. |
| T3.3 mark legacy components | ❌ | `run_case_legacy` named legacy in code only; not flagged in README. |
| T3.4 runtime path consistency check | ❌ | Not performed. |
| T3.5 optional PEC refactor | ❌ | Not done. |

### Phase 4 — UI Parity

| Task | Status | Evidence |
|------|--------|----------|
| T4.1 mode contract (benchmark vs single-case) | ❌ | Single benchmark form only. |
| T4.2 case input workflow | ❌ | No upload/select for buggy.py + test. |
| T4.3 live run streaming | ❌ | No SSE; only post-hoc JSON dump (`web/static/app.js`). README §"Web UI with real-time SSE streaming" overclaims. |
| T4.4 backend event hooks | ❌ | No `StreamingResponse` route. |
| T4.5 e2e UI validation | ❌ | Cannot run; live mode absent. |
| T4.6 claim-safe labeling | ❌ | UI labels not audited. |

### Phase 5 — Guardrails & Infra

| Task | Status | Evidence |
|------|--------|----------|
| T5.1 command allowlist policy | 🟡 | Benchmark runtime uses scoped tools (`benchmark/README.md:80`); no formal allowlist module. |
| T5.2 reduce `shell=True` | ❌ | 4 hits remain: `benchmark/runtime.py:62`, `benchmark/run_matrix.py:108`, `agent/tools_impl.py:193,209`. README claims `shell=False` everywhere. |
| T5.3 path scope enforcement | ✅ | `os.path.realpath` checks in executor (per HANDOFF). |
| T5.4 verify containerized execution | ❌ | No tested run record. |
| T5.5 publish container runbook | 🟡 | One-line `docker build/run` in `README.md:82`. Not validated. |
| T5.6 sync guardrail claims | ❌ | Mismatch with §T5.2 above. |

### Phase 6 — Traceability & Bundle

| Task | Status | Evidence |
|------|--------|----------|
| T6.1 traceability matrix | ❌ | `docs/proposal_traceability.md` absent. |
| T6.2 claim→code mapping | ❌ | — |
| T6.3 claim→artifact mapping | ❌ | — |
| T6.4 technical evidence review | ❌ | — |
| T6.5 artifact integrity audit | ❌ | — |
| T6.6 reproducibility block | ❌ | No "How to reproduce final numbers" block. |
| T6.7 submission readiness summary | ❌ | — |

---

## 3. Benchmark Hardening (`docs/benchmark_todo.md`)

| Item | Status | Evidence |
|------|--------|----------|
| Verifier-in-loop hard stop | ✅ | Per file. |
| Phase guardrails for repeated no-op | ✅ | `agent/planner.py:273`. |
| Internal tool-result classification | ✅ | Per file. |
| Deterministic output/report coupling | ✅ | `latest_results_path.txt` pointer. |
| Specialized tools (`run_target_test`, `run_regression_test`, `list_dir`) | ✅ | Per file. |
| `run_id` isolation in result rows + analyzer grouping | ❌ | No `run_id` in `benchmark/`. |
| Efficiency telemetry (no-op count, skip count, full-pytest count) | ❌ | Not emitted. |

---

## 4. README/HANDOFF Claim Audit

| Claim | Reality | Action |
|-------|---------|--------|
| "Web UI with real-time SSE streaming" (`README.md:74`) | Post-hoc JSON only | Implement SSE or rewrite claim. |
| "subprocess `shell=False`" (`README.md`) | 4 `shell=True` call sites | Remove or qualify. |
| "Planner → Executor → Critic loop" (`README.md:18,36`) | Tool-loop planner; Executor/Critic legacy paths | Update diagram or wire PEC. |
| HANDOFF "Pending Work: only eval + demo video" | Multiple Phase 0–6 tasks open | Sync HANDOFF with `proposal_closure_todo.md`. |
| `Gemini 2.0 Flash` (HANDOFF/README) | `config.py` = `gemini-2.5-flash` | Reconcile. |

---

## 5. Pending — Priority Stack

### P0 (blocks submission)
1. Run final matrix → produce `logs/final_results.jsonl` and non-empty `benchmark_report.json` (Phase 1).
2. Add benchmark contract section + proposal deltas to README (T0.1–T0.6).
3. Architecture diagram correction or PEC refactor (T3.1–T3.3).

### P1 (strongly recommended)
4. UI live-stream + upload workflow (T4.2–T4.4) **or** rewrite SSE/upload claims.
5. Replace remaining `shell=True` (`benchmark/runtime.py:62`, `benchmark/run_matrix.py:108`, `agent/tools_impl.py:193,209`).
6. Validated Docker run command (T5.4–T5.5).
7. `docs/proposal_traceability.md` (T6.1–T6.3).
8. Reproducibility block in README (T6.6).

### P2 (nice-to-have)
9. `patch_size` metric (T2.3).
10. Failure-mode taxonomy enforcement (T2.7).
11. `run_id` isolation + analyzer grouping (benchmark P1).
12. Efficiency telemetry counters (benchmark P1).
13. Schema doc (T2.8).

---

## 6. Quick Repro Commands (current state)

```bash
# matrix run (will populate logs/final_results.jsonl)
python -m benchmark.run_matrix \
  --manifest benchmark/manifests/pilot_hybrid.jsonl \
  --models gemini,qwen,minimax,gemma4 \
  --output logs/final_results.jsonl \
  --max-steps 15 --timeout-s 180 --repetitions 1

# analyze
python -m benchmark.analyze \
  --input logs/final_results.jsonl \
  --output logs/benchmark_report.json
```
