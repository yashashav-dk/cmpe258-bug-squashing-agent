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

3) Analyze results

```bash
python -m benchmark.analyze \
  --input latest \
  --output logs/benchmark_report.json
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
