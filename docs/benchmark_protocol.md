# Scientific Benchmark Protocol

## Scope

This protocol evaluates the agent on reproducible open-source Python bug scenarios using a hybrid benchmark:

- 70% historical real bugs
- 30% deterministic synthetic mutations

The benchmark is source-extensible by contract through `SourceAdapter`.

## Trial Contract

A trial is a tuple:

`(case_id, repo_url, base_commit, model, seed, max_steps, timeout_budget, verifier_commands)`

A run is valid only if:

- target tests fail before fixing (post-injection precondition),
- target tests pass after agent patching,
- regression suite does not add failures (if configured).
- run artifacts are isolated per run (or append explicitly requested) to avoid mixed-history analysis bias.
- planner loop performs in-loop target-test verification after edit/no-op edit and can terminate early on verified pass.

Current pilot operating mode:
- benchmark architecture remains hybrid-source capable,
- active pilot manifest is temporarily synthetic-only (4 deterministic local fixture cases),
- historical rows are intentionally set to 0 for this run window.

## Metrics

Primary metric:

- pass rate on target failing tests.

Secondary metrics:

- time-to-fix (wall clock),
- token usage (input/output),
- retry depth,
- patch size,
- regression failure rate.

## Statistical Analysis

- Pass-rate confidence: Wilson 95% interval.
- Model deltas: paired bootstrap (recommended in post-processing).
- Time/cost effect size: Cliff's delta (recommended in post-processing).
- Multiple-model comparisons: apply multiplicity correction before claims.

## Failure Taxonomy

- `localization_failure`: target tests still failing after run
- `invalid_patch`: patch cannot be applied or creates parse/runtime breakage
- `non_terminating_loop`: max steps or timeout reached without fix
- `test_regression`: target passes but regression suite fails
- `false_resolved`: model claims resolved but verifier fails
- `environment_error`: infrastructure/dependency/setup fault
- `invalid_benchmark_case`: injection did not produce a failing target test in preflight

## Acceptance Criteria

- Adapter swapping (`historical` <-> `synthetic`) requires no runner refactor.
- Manifest replay with same seed reproduces identical case hashes.
- Every reported resolution is verifier-backed by test exit codes.
- Result JSONL contains enough fields for independent audit.

## Pilot Plan (Two Repos)

Pilot repositories:

- `psf/requests`
- `pallets/click`

Phases:

1. Case-generation dry run and schema validation.
2. Injection reproducibility check and baseline fail verification.
3. Single-model sanity benchmark.
4. Multi-model benchmark with statistical report.
5. Expand case count and mutation operators while preserving contracts.
