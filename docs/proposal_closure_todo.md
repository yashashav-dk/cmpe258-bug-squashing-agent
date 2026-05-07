# Proposal Closure TODO

## Goal

Close the gap between the CMPE 258 proposal claims and the current repository state so final reporting is evidence-backed and reproducible.

## Definition of Done (Top-Level)

- [ ] End-to-end benchmark report is non-empty and reproducible from committed commands.
- [ ] Report includes pass rate, latency percentiles, retry-depth distribution, failure modes, and cost per successful fix.
- [ ] Architecture narrative matches implementation (or implementation is aligned to narrative).
- [ ] UI/demo path supports proposal-level workflow claims.
- [ ] Proposal-to-code traceability document is complete and auditable.

## Team Split (3-Person Logical Ownership)

### Ownership model
- **Pranav (Architecture + Runtime + Metrics):** core runtime correctness, analyzer parity, protocol/report integrity.
- **Yash (Benchmark Ops + Guardrails + Infra):** reproducible runs, manifests/artifacts, safety policy, Docker path validation.
- **Saransh (Docs + UI + Traceability):** proposal alignment narrative, UI parity, final documentation bundle.

### Primary owner by phase
- **Phase 0:** Saransh (docs/claims), Pranav (technical claim validation), Yash (run config freeze).
- **Phase 1:** Yash (execute benchmark runs), Pranav (debug runtime failures), Saransh (record artifact metadata).
- **Phase 2:** Pranav (analyzer code), Yash (pricing inputs + validation), Saransh (report schema documentation).
- **Phase 3:** Pranav (architecture truth/alignment decision), Saransh (README architecture edits), Yash (runtime checks).
- **Phase 4:** Saransh (UI implementation + labels), Pranav (event stream hooks), Yash (integration checks).
- **Phase 5:** Yash (guardrail hardening + Docker validation), Pranav (code path changes), Saransh (safety claim docs).
- **Phase 6:** Saransh (traceability + reproducibility docs), Pranav (technical evidence), Yash (artifact integrity).

### Execution rules
- One **DRI** per task (single accountable owner), others as reviewers.
- No phase marked complete without acceptance checks and reviewer sign-off.
- Daily handoff note: changed files, commands run, artifact paths, open blockers.

## Named Task Registry (All Tasks Assigned)

Task naming format: `T<phase>.<index>_<short_name>`

### Phase 0 - Scope and Claims
- [ ] `T0.1_freeze_manifest_scope` - **Owner:** Yash - Select and freeze final manifest.
- [ ] `T0.2_freeze_model_matrix` - **Owner:** Yash - Lock model list for final comparison.
- [ ] `T0.3_freeze_runtime_knobs` - **Owner:** Yash - Lock `max_steps`, `timeout_s`, `repetitions`, seed policy.
- [ ] `T0.4_define_benchmark_contract_doc` - **Owner:** Saransh - Add README benchmark contract section.
- [ ] `T0.5_document_model_delta` - **Owner:** Saransh - Document Gemini proposal-vs-implementation delta.
- [ ] `T0.6_document_architecture_delta` - **Owner:** Saransh - Document planner-loop vs formal PEC delta.
- [ ] `T0.7_validate_claim_consistency` - **Owner:** Pranav - Verify docs do not contradict runtime behavior.

### Phase 1 - Benchmark Artifact Generation
- [ ] `T1.1_preflight_model_connectivity` - **Owner:** Yash - Validate API keys/Ollama/connectivity.
- [ ] `T1.2_execute_final_matrix_run` - **Owner:** Yash - Run benchmark matrix with fixed output.
- [ ] `T1.3_validate_results_integrity` - **Owner:** Yash - Confirm started/completed coverage for all pairs.
- [ ] `T1.4_publish_latest_pointer_check` - **Owner:** Yash - Verify `latest_results_path` points to intended file.
- [ ] `T1.5_generate_analysis_report` - **Owner:** Pranav - Run analyzer for benchmark report generation.
- [ ] `T1.6_verify_report_non_empty` - **Owner:** Pranav - Validate report schema has per-model rows.
- [ ] `T1.7_record_run_metadata` - **Owner:** Saransh - Capture commands, timestamps, artifact paths.

### Phase 2 - Metrics Parity
- [ ] `T2.1_add_latency_p99` - **Owner:** Pranav - Add p99 latency metric in analyzer.
- [ ] `T2.2_add_retry_depth_distribution` - **Owner:** Pranav - Add retry-depth distribution metric.
- [ ] `T2.3_add_patch_size_metric` - **Owner:** Pranav - Add patch-size metric (or instrument if missing).
- [ ] `T2.4_add_model_pricing_table` - **Owner:** Yash - Provide deterministic per-model token pricing inputs.
- [ ] `T2.5_add_estimated_cost_fields` - **Owner:** Pranav - Compute and emit estimated cost fields.
- [ ] `T2.6_add_cost_per_successful_fix` - **Owner:** Pranav - Emit cost/fix metric in report.
- [ ] `T2.7_harden_failure_mode_aggregation` - **Owner:** Pranav - Ensure all failed rows are categorized.
- [ ] `T2.8_metric_schema_documentation` - **Owner:** Saransh - Document final report schema in docs.

### Phase 3 - Architecture Alignment
- [ ] `T3.1_choose_alignment_strategy` - **Owner:** Pranav - Decide Option A (truthful docs) vs Option B (refactor).
- [ ] `T3.2_update_architecture_diagram` - **Owner:** Saransh - Update README control-flow diagram.
- [ ] `T3.3_mark_legacy_components` - **Owner:** Saransh - Label legacy/deprecated paths explicitly.
- [ ] `T3.4_runtime_path_consistency_check` - **Owner:** Yash - Validate documented flow matches execution.
- [ ] `T3.5_optional_pec_refactor` - **Owner:** Pranav - If Option B, wire Planner->Executor->Critic orchestration.

### Phase 4 - UI Parity
- [ ] `T4.1_define_ui_mode_contract` - **Owner:** Saransh - Define benchmark mode vs single-case mode boundaries.
- [ ] `T4.2_add_case_input_workflow` - **Owner:** Saransh - Add upload/select workflow (or explicit equivalent).
- [ ] `T4.3_add_live_run_streaming` - **Owner:** Saransh - Surface live step/tool output instead of only post-hoc JSON.
- [ ] `T4.4_integrate_event_stream_hooks` - **Owner:** Pranav - Expose required backend event hooks.
- [ ] `T4.5_ui_integration_validation` - **Owner:** Yash - Validate end-to-end UI run behavior.
- [ ] `T4.6_claim_safe_ui_labeling` - **Owner:** Saransh - Ensure UI wording does not over-claim capabilities.

### Phase 5 - Guardrails and Infra Hardening
- [ ] `T5.1_command_allowlist_policy` - **Owner:** Yash - Define and enforce allowed command policy.
- [ ] `T5.2_reduce_shell_true_surfaces` - **Owner:** Pranav - Replace avoidable `shell=True` paths.
- [ ] `T5.3_validate_path_scope_enforcement` - **Owner:** Yash - Confirm read/edit tooling remains workspace-scoped.
- [ ] `T5.4_verify_containerized_execution` - **Owner:** Yash - Validate Docker benchmark/UI execution path.
- [ ] `T5.5_publish_container_runbook` - **Owner:** Yash - Add tested Docker commands to README.
- [ ] `T5.6_update_guardrail_claims` - **Owner:** Saransh - Sync docs with enforced guardrails.

### Phase 6 - Final Traceability and Submission Bundle
- [ ] `T6.1_create_traceability_matrix` - **Owner:** Saransh - Add `docs/proposal_traceability.md`.
- [ ] `T6.2_map_claims_to_code_evidence` - **Owner:** Saransh - Fill claim->file evidence mapping.
- [ ] `T6.3_map_claims_to_artifacts` - **Owner:** Saransh - Link claims to report/results artifacts.
- [ ] `T6.4_technical_evidence_review` - **Owner:** Pranav - Validate technical correctness of mappings.
- [ ] `T6.5_artifact_integrity_audit` - **Owner:** Yash - Verify immutability/completeness of result bundle.
- [ ] `T6.6_publish_reproducibility_block` - **Owner:** Saransh - Add exact repro commands + environment notes.
- [ ] `T6.7_submission_readiness_check` - **Owner:** Saransh - Final met/partial/not-met summary.

---

## Phase 0 - Freeze Scope and Claims (Day 0)

### 0.1 Lock evaluation scope
- [ ] Freeze one manifest for final results (recommended: `benchmark/manifests/pilot_hybrid.jsonl` or `benchmark/manifests/hard_multifile_051_052.jsonl` for pilot).
- [ ] Freeze model list for final comparison (`gemini`, `qwen`, `minimax`, `gemma4`) and document substitutions vs proposal text.
- [ ] Freeze runtime knobs: `max_steps`, `timeout_s`, `repetitions`, random seed policy.

Acceptance:
- [ ] A single markdown section in README declares final benchmark contract (manifest, models, knobs, date).

### 0.2 Resolve proposal drift explicitly
- [ ] Add a short “proposal deltas” section:
  - [ ] Gemini 3.1 Pro -> Gemini 2.0 Flash (or switch back if required).
  - [ ] Current runtime is planner tool-loop; document Executor/Critic role truthfully.
  - [ ] Hybrid architecture vs current active pilot composition.

Acceptance:
- [ ] No claim in README/proposal addendum contradicts current code behavior.

---

## Phase 1 - Generate Valid Benchmark Artifacts (Day 1)

### 1.1 Produce clean run outputs
- [ ] Ensure local model/API dependencies are reachable before run (Ollama + API keys).
- [ ] Run matrix with fixed output path and no stale mixed history.
- [ ] Confirm `logs/latest_results_path.txt` points to the intended output.

Suggested command:
```bash
python -m benchmark.run_matrix \
  --manifest benchmark/manifests/pilot_hybrid.jsonl \
  --models gemini,qwen,minimax,gemma4 \
  --output logs/final_results.jsonl \
  --max-steps 15 \
  --timeout-s 180 \
  --repetitions 1
```

Acceptance:
- [ ] Results JSONL has `started` + `completed/error` records for every case/model pair.
- [ ] No empty results file.

### 1.2 Generate non-empty analysis report
- [ ] Run analyzer against the produced results file.
- [ ] Verify `logs/benchmark_report.json` is non-empty and parseable.

Suggested command:
```bash
python -m benchmark.analyze --input logs/final_results.jsonl --output logs/benchmark_report.json
```

Acceptance:
- [ ] `logs/benchmark_report.json` contains per-model entries with runs/resolved/pass_rate.

---

## Phase 2 - Metric Parity With Proposal (Day 1-2)

### 2.1 Add missing metrics in analyzer
- [ ] Add `p99` latency in `benchmark/analyze.py`.
- [ ] Add retry-depth distribution from `planner_stats.steps` (or explicit retry field if introduced).
- [ ] Add patch-size metric (if available in logs; otherwise add instrumentation first).
- [ ] Add cost estimate + `cost_per_successful_fix`.

Implementation notes:
- Token totals already exist (`planner_stats.total_input_tokens`, `planner_stats.total_output_tokens`).
- Add pricing table by model in config-level constants for deterministic cost computation.

Acceptance:
- [ ] Report schema includes:
  - [ ] `latency_ms.p50`
  - [ ] `latency_ms.p90`
  - [ ] `latency_ms.p99`
  - [ ] `retry_depth_distribution`
  - [ ] `token_usage`
  - [ ] `estimated_cost`
  - [ ] `cost_per_successful_fix`

### 2.2 Strengthen failure-mode accounting
- [ ] Ensure failed runs are categorized consistently (`localization_failure`, `false_resolved`, `test_regression`, `environment_error`, `invalid_benchmark_case`, etc.).
- [ ] Verify all non-completed rows are represented in summary counts.

Acceptance:
- [ ] Sum of failure buckets + resolved count == total valid runs per model.

---

## Phase 3 - Architecture Truthfulness or Alignment (Day 2-3)

### Option A (recommended for timeline): document truthfully
- [ ] Update README architecture diagram to reflect current runtime path.
- [ ] Keep Executor/Critic as modules but mark current active orchestration path clearly.
- [ ] Add explicit “legacy/deprecated” labels where needed.

Acceptance:
- [ ] Any new contributor can infer real control flow from README without reading source.

### Option B (if strict proposal parity required): enforce formal Planner->Executor->Critic loop
- [ ] Wire `Executor` and `Critic` into benchmark runtime loop.
- [ ] Make Planner output structured patch plan object consumed by Executor.
- [ ] Critic decides retry/stop with explicit state transitions.

Acceptance:
- [ ] Runtime path uses all three components as first-class orchestration roles.

---

## Phase 4 - UI Parity With Proposal (Day 3)

### 4.1 Minimal proposal-parity UI features
- [ ] Add upload/select workflow for buggy file(s) + test script(s) (or manifest-backed equivalent with clear wording).
- [ ] Add live execution stream (step/tool output updates instead of post-hoc JSON dump).
- [ ] Add model selector and run controls already present; keep as primary panel.

Acceptance:
- [ ] Demo can show user input -> real-time reasoning/tool actions -> verifier outcome.

### 4.2 Keep benchmark UI and case-run UI separated
- [ ] Clarify two modes:
  - [ ] Benchmark mode (manifest matrix)
  - [ ] Single-case interactive mode (upload/select)

Acceptance:
- [ ] UI labels avoid claiming unsupported behavior.

---

## Phase 5 - Safety/Guardrail Parity (Day 3-4)

### 5.1 Command execution policy hardening
- [ ] Replace broad shell execution paths with explicit allowlisted commands where proposal claims require it.
- [ ] Avoid `shell=True` where not required; use argv execution with fixed commands.
- [ ] Keep scoped filesystem checks enforced for read/edit tools.

Acceptance:
- [ ] Guardrail behavior is enforceable in code, not only documented.

### 5.2 Docker execution claim validation
- [ ] Verify documented run path actually executes benchmark/UI in containerized mode.
- [ ] Add one reproducible container run command to README and confirm it works.

Acceptance:
- [ ] “Sandboxed execution” claim has a tested command path.

---

## Phase 6 - Final Reporting and Traceability (Day 4)

### 6.1 Proposal-to-code traceability doc
- [ ] Add `docs/proposal_traceability.md` with table:
  - [ ] Proposal claim
  - [ ] Code/file evidence
  - [ ] Metric artifact
  - [ ] Status (met/partial/not met)
  - [ ] Notes

Acceptance:
- [ ] Every major proposal section maps to concrete evidence.

### 6.2 Final benchmark bundle
- [ ] Preserve immutable run artifacts:
  - [ ] Results JSONL
  - [ ] Events JSONL
  - [ ] Report JSON
  - [ ] Exact commands + environment notes
- [ ] Add one concise “How to reproduce final numbers” block.

Acceptance:
- [ ] Teammate can reproduce reported numbers with no hidden steps.

---

## Priority Backlog (If Time-Constrained)

### P0 (must-have before submission/demo)
- [ ] Non-empty final run + report artifacts.
- [ ] Analyzer metric parity: p99 + cost/fix + retry depth.
- [ ] README claim corrections for architecture/model drift.

### P1 (strongly recommended)
- [ ] Live stream UI improvements.
- [ ] Guardrail hardening to match strict proposal language.
- [ ] Proposal traceability doc.

### P2 (nice-to-have)
- [ ] Full formal Planner->Executor->Critic orchestration refactor.
- [ ] Expanded statistical post-processing (paired bootstrap, effect sizes).

---

## Execution Checklist (Quick Runbook)

- [ ] Step 1: Freeze manifest/models/config.
- [ ] Step 2: Run matrix and verify complete artifact set.
- [ ] Step 3: Extend analyzer schema; regenerate report.
- [ ] Step 4: Align README claims to code reality.
- [ ] Step 5: Patch UI wording/features for parity.
- [ ] Step 6: Produce traceability doc and final reproducibility block.
- [ ] Step 7: Final sanity pass on all docs and commands.

---

## Risks and Mitigations

- [ ] **Risk:** API/local model instability causes empty/incomplete results.  
      **Mitigation:** preflight health checks + retry + partial-run resume policy.
- [ ] **Risk:** metric additions require new logging fields.  
      **Mitigation:** add backward-compatible defaults in analyzer.
- [ ] **Risk:** proposal wording over-claims implemented behavior.  
      **Mitigation:** tighten wording to verified behavior and mark future work explicitly.

---

## Person-wise Task Board

### Pranav - Core System and Evaluation Logic
- [ ] Decide and document Phase 3 path (truthful docs vs strict Planner->Executor->Critic alignment).
- [ ] Implement analyzer metric parity in `benchmark/analyze.py` (`p99`, retry-depth distribution, cost/fix).
- [ ] Ensure runtime exposes required stats fields consistently (`planner_stats`, failure semantics).
- [ ] Validate final report schema and metric math with one dry run + one final run.
- [ ] Co-review traceability evidence for all architecture/runtime claims.

Deliverables:
- [ ] PR for analyzer/runtime changes.
- [ ] Verified `logs/benchmark_report.json` with required metric keys.

### Yash - Benchmark Operations, Guardrails, and Reproducibility
- [ ] Freeze manifest/models/knobs and publish canonical run command set.
- [ ] Execute matrix runs, maintain clean artifacts, and verify `latest_*_path.txt` pointers.
- [ ] Triage/resolve infra failures (API/Ollama timeouts, environment failures, flaky setup).
- [ ] Harden command execution policy (allowlist posture, reduce `shell=True` where feasible).
- [ ] Validate Docker run path for benchmark/UI and provide tested commands.

Deliverables:
- [ ] Final results JSONL + events JSONL artifact set.
- [ ] Reproducible runbook commands confirmed on local/container path.

### Saransh - Proposal Alignment, UI Parity, and Final Documentation
- [ ] Add/maintain proposal-delta narrative (model substitutions, architecture drift, pilot composition).
- [ ] Implement UI parity updates (mode clarity, live output framing, claim-safe labeling).
- [ ] Create `docs/proposal_traceability.md` mapping claims -> code -> artifacts -> status.
- [ ] Add final README benchmark contract + reproducibility section.
- [ ] Produce final submission-ready summary (met/partial/not-met with evidence links/paths).

Deliverables:
- [ ] Updated docs (`README.md`, `docs/proposal_traceability.md`).
- [ ] UI wording/features aligned with supported behavior.

