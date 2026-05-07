# Hybrid Benchmark Toolkit

This directory contains an extensible benchmark pipeline for evaluating the bug-squashing agent on open-source Python repositories.

Current operating mode for the pilot manifest:
- hybrid architecture remains in code (`historical` + `synthetic` adapters),
- active `benchmark/manifests/pilot_hybrid.jsonl` is temporarily synthetic-only (4 deterministic local fixture cases).

## Components

- `manifest.py`: canonical `BenchmarkCase` schema and JSONL loader/writer.
- `adapters/`: source-specific case generators implementing a shared interface.
  - `HistoricalBugAdapter`: consumes curated historical bug rows.
  - `SyntheticMutationAdapter`: deterministically mutates templates.
- `build_manifest.py`: composes hybrid datasets (historical + synthetic).
- `injection.py`: deterministic bug injection into a workspace target.
- `runtime.py`: model/planner execution + verifier test command checks.
- `run_matrix.py`: orchestrates case x model x repetition and writes JSONL output.
- `analyze.py`: computes pass-rate statistics and summary reports.
- `protocol.py`: evaluation criteria, protocol defaults, failure taxonomy.

## Reproducible Workflow

1) Build hybrid manifest

```bash
python -m benchmark.build_manifest \
  --historical-source benchmark/data/historical_cases.sample.jsonl \
  --synthetic-source benchmark/data/synthetic_templates.sample.jsonl \
  --output benchmark/manifests/pilot_hybrid.jsonl \
  --target-count 30 \
  --historical-ratio 0.7 \
  --synthetic-ratio 0.3 \
  --seed 13
```

2) Run benchmark matrix

```bash
python -m benchmark.run_matrix \
  --manifest benchmark/manifests/pilot_hybrid.jsonl \
  --models gemma4 \
  --output logs/benchmark_results.jsonl \
  --repetitions 1 \
  --max-steps 15 \
  --timeout-s 180
```

Run-output hygiene behavior:
- if `--output` already exists, `run_matrix` now auto-writes to a unique timestamped file to avoid mixed run histories,
- event logs follow the same pattern (`benchmark_events_<output_stem>.jsonl`) when needed,
- latest artifact pointers are written to `logs/latest_results_path.txt` and `logs/latest_events_path.txt`,
- pass `--allow-append` to keep legacy append behavior.
- **Local `dataset/cases/case_*` workspaces** are copied to `logs/runs/<run_id>/workspaces/<attempt_id>` by default so the agent never overwrites committed `buggy.py`. Use `--dataset-in-place` only if you intentionally mutate the checkout; use `--keep-temp-workspaces` or `BENCHMARK_KEEP_WORKSPACE_COPY=1` to retain copies for debugging.

3) Analyze results

```bash
python -m benchmark.analyze \
  --input latest \
  --output logs/benchmark_report.json
```

4) Materialize UI DTO report

```bash
python -m benchmark.materialize_ui_report \
  --input latest \
  --manifest benchmark/manifests/pilot_hybrid.jsonl \
  --output logs/benchmark_ui_report.json
```

## Required Case Metadata

Each manifest row must include:

- reproducibility: `repo_url`, `base_commit`, `seed`, `python_version`
- execution: `install`, `test_command`, optional `regression_test_command`
- scope controls: `allowed_paths`, `target_file`
- injection artifact: `injection_patch` (+ metadata for replacement mode)
- runtime bridge: `metadata.workspace_dir` (local checked out repository path)

## Determinism Invariants

- same manifest + same seed => same selected case set and case hashes
- same workspace revision + same injection artifact => same injected state
- resolved status is derived from verifier exit codes, not model self-claims
- preflight gate: after injection, `test_command` must fail before planner execution; otherwise case is marked `invalid_benchmark_case`
- run output isolation: new runs avoid accidental append to prior JSONL outputs unless explicitly requested with `--allow-append`
- planner verifier-in-loop stop: after a successful/no-op edit, target test is auto-verified and the planner terminates early when it passes

## Frontend DTO Contract (README for UI Handoff)

`benchmark.run_matrix` now writes run-scoped artifacts:

- `logs/runs/<run_id>/results.jsonl`
- `logs/runs/<run_id>/events.jsonl`
- `logs/runs/<run_id>/ui_report.json` (via `run_pipeline`)

Latest pointers:

- `logs/latest_results_path.txt`
- `logs/latest_events_path.txt`
- `logs/latest_run_dir_path.txt`
- `logs/latest_run_id.txt`

### Terminal attempt record invariants (`results.jsonl`)

- each `(run_id, case_id, model, repetition)` has exactly:
  - one `row_type="start"` row with `status="started"`
  - one `row_type="terminal"` row with `status in {"completed","error"}`
- `attempt_id` is stable and join-safe
- legacy `run_case_id` is still emitted for compatibility

### `ui_report.json` schema

```json
{
  "run": {
    "run_id": "20260507T060102Z_ab12cd34",
    "results_path": "/abs/path/logs/runs/<run_id>/results.jsonl",
    "manifest_path": "/abs/path/benchmark/manifests/pilot_hybrid.jsonl"
  },
  "models": [
    {
      "model": "gemma4",
      "runs": 30,
      "resolved": 11,
      "unresolved": 19,
      "pass_rate": 0.3667,
      "error_runs": 2,
      "latency_ms": { "avg": 8123.4, "p50": 5222.0, "p90": 16220.0, "p99": 22800.0 },
      "failure_modes": { "none": 11, "localization_failure": 10, "environment_error": 2, "false_resolved": 7 }
    }
  ],
  "cases": [
    {
      "case_id": "case_048",
      "source_type": "synthetic",
      "difficulty": "medium",
      "tags": ["math", "off_by_one"]
    }
  ],
  "attempts": [
    {
      "attempt_id": "case_048__gemma4__rep0",
      "run_id": "20260507T060102Z_ab12cd34",
      "case_id": "case_048",
      "model": "gemma4",
      "repetition": 0,
      "status": "completed",
      "resolved": true,
      "failure_mode": "none",
      "wall_time_ms": 5211.0,
      "target_test_exit_code": 0,
      "regression_test_exit_code": 0,
      "planner_stats": { "steps": 2, "total_input_tokens": 300, "total_output_tokens": 140 },
      "source_type": "synthetic",
      "difficulty": "medium",
      "tags": ["math", "off_by_one"],
      "error": null
    }
  ],
  "matrix": {
    "gemma4": {
      "case_048": {
        "attempt_id": "case_048__gemma4__rep0",
        "status": "completed",
        "resolved": true,
        "failure_mode": "none"
      }
    }
  }
}
```

### DTO consumption guidance

- leaderboard: consume `models[]`
- case table per model: consume `matrix[model][case_id]`
- drill-down: lookup `attempts[]` by `attempt_id`
- case metadata chip/tag UI: consume `cases[]`
