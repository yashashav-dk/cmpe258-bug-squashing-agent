# Benchmark Hardening TODO

This file tracks benchmark architecture and runtime hardening tasks.

## Completed (P0)

- [x] Verifier-in-loop hard stop after `edit_file` success/no-op.
- [x] Planner phase guardrails for repeated no-op and repeated identical failing calls.
- [x] Structured internal tool-result classification for planner decisions.
- [x] Deterministic output/report coupling with latest artifact pointers.

## Pending (P1)

- [x] Add specialized benchmark-mode tools:
  - `run_target_test`
  - `run_regression_test`
  - `list_dir`
- [ ] Add `run_id` isolation in result rows and analyzer grouping.
- [ ] Add efficiency telemetry:
  - no-op edit count
  - repeated tool-call skip count
  - unnecessary full-pytest invocation count

## Notes

- Active benchmark operating mode is synthetic-only (4 local deterministic cases) while keeping hybrid architecture in code.
- Preflight validity contract is enforced: injected target test must fail before planner execution.
- Benchmark runtime exposes strict scoped tools and does not expose ad-hoc `run_bash`.
