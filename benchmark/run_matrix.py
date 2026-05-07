import argparse
import json
import random
import subprocess
from shutil import copyfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List

from benchmark.injection import apply_injection
from benchmark.manifest import BenchmarkCase, load_manifest
from benchmark.runtime import AgentRuntime
from logger import Logger


def canonicalize_model_name(model: str) -> str:
    key = model.strip().lower()
    aliases = {
        "gemm4": "gemma4",
        "gemma-4": "gemma4",
    }
    return aliases.get(key, key)


def parse_models(raw: str) -> List[str]:
    return [canonicalize_model_name(item) for item in raw.split(",") if item.strip()]


def iter_matrix(cases: Iterable[BenchmarkCase], models: List[str], repetitions: int):
    for case in cases:
        for model in models:
            for rep in range(repetitions):
                yield case, model, rep


def append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


class InvalidBenchmarkCaseError(Exception):
    pass


def _timestamp_suffix() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve_output_path(path: Path, allow_append: bool) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if allow_append or not path.exists():
        return path
    unique = path.with_name(f"{path.stem}_{_timestamp_suffix()}{path.suffix}")
    print(f"[run_matrix] Output exists; using unique path: {unique}")
    return unique


def resolve_event_log_path(output_path: Path, explicit_path: str, allow_append: bool) -> Path:
    if explicit_path:
        return resolve_output_path(Path(explicit_path), allow_append=allow_append)
    default_path = Path("logs/benchmark_events.jsonl")
    if allow_append or not default_path.exists():
        return default_path
    inferred = default_path.with_name(f"benchmark_events_{output_path.stem}.jsonl")
    print(f"[run_matrix] Event log exists; using unique path: {inferred}")
    return inferred


def persist_latest_run_artifacts(output_path: Path, event_log_path: Path) -> None:
    latest_results = Path("logs/latest_results_path.txt")
    latest_events = Path("logs/latest_events_path.txt")
    latest_results.parent.mkdir(parents=True, exist_ok=True)
    latest_results.write_text(str(output_path.resolve()), encoding="utf-8")
    latest_events.write_text(str(event_log_path.resolve()), encoding="utf-8")


def _is_git_workspace(workspace_dir: str) -> bool:
    return (Path(workspace_dir) / ".git").exists()


def _restore_local_fixture(workspace_dir: str) -> None:
    workspace = Path(workspace_dir)
    golden = workspace / "golden.py"
    buggy = workspace / "buggy.py"
    if golden.exists() and buggy.exists():
        copyfile(golden, buggy)
        return
    raise FileNotFoundError(
        f"Non-git workspace requires golden.py and buggy.py for reset: {workspace_dir}"
    )


def reset_workspace(workspace_dir: str, base_commit: str) -> None:
    if _is_git_workspace(workspace_dir):
        subprocess.run(["git", "-C", workspace_dir, "reset", "--hard"], check=True)
        subprocess.run(["git", "-C", workspace_dir, "clean", "-fd"], check=True)
        if base_commit:
            subprocess.run(["git", "-C", workspace_dir, "checkout", base_commit], check=True)
        return
    _restore_local_fixture(workspace_dir)


def run_preflight_test(test_command: str, workspace_dir: str, timeout_s: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        test_command,
        shell=True,
        capture_output=True,
        text=True,
        cwd=workspace_dir,
        timeout=timeout_s,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run benchmark matrix for bug-squashing agent")
    parser.add_argument("--manifest", required=True, help="Path to benchmark manifest JSONL")
    parser.add_argument("--models", required=True, help="Comma-separated model names")
    parser.add_argument("--output", default="logs/benchmark_results.jsonl")
    parser.add_argument("--max-steps", type=int, default=15)
    parser.add_argument("--timeout-s", type=int, default=120)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--max-attempts", type=int, default=1, help="Critic-driven retry attempts per case (PEC outer loop).")
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--skip-injection", action="store_true")
    parser.add_argument(
        "--allow-append",
        action="store_true",
        help="Append to existing output/event logs instead of creating unique files.",
    )
    parser.add_argument(
        "--event-log",
        default="",
        help="Optional path for benchmark event JSONL. Defaults to logs/benchmark_events*.jsonl",
    )
    args = parser.parse_args()

    random.seed(args.seed)
    cases = load_manifest(args.manifest)
    models = parse_models(args.models)
    requested_output_path = Path(args.output).resolve()
    output_path = resolve_output_path(requested_output_path, allow_append=args.allow_append)

    event_log_path = resolve_event_log_path(
        output_path=output_path,
        explicit_path=args.event_log,
        allow_append=args.allow_append,
    ).resolve()
    persist_latest_run_artifacts(output_path=output_path, event_log_path=event_log_path)
    print(f"[run_matrix] RESULTS_PATH={output_path.resolve()}")
    print(f"[run_matrix] EVENTS_PATH={event_log_path}")
    event_logger = Logger(str(event_log_path))
    runtime = AgentRuntime(
        max_steps=args.max_steps,
        timeout_s=args.timeout_s,
        logger=event_logger,
        max_attempts=args.max_attempts,
    )

    for case, model, rep in iter_matrix(cases, models, args.repetitions):
        run_case_id = f"{case.case_id}__{model}__rep{rep}"
        workspace_dir = case.metadata.get("workspace_dir", "")
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_case_id": run_case_id,
            "case_id": case.case_id,
            "model": model,
            "seed": case.seed + rep,
            "case_hash": case.content_hash(),
            "workspace_dir": workspace_dir,
            "source_type": case.source_type,
            "difficulty": case.difficulty,
            "tags": case.tags,
            "status": "started",
        }
        append_jsonl(output_path, record)

        try:
            if not args.skip_injection:
                if workspace_dir and case.base_commit:
                    reset_workspace(workspace_dir=workspace_dir, base_commit=case.base_commit)
                apply_injection(case, workspace_dir=workspace_dir)
                preflight = run_preflight_test(case.test_command, workspace_dir=workspace_dir, timeout_s=args.timeout_s)
                if preflight.returncode == 0:
                    output = (preflight.stdout + preflight.stderr).strip()
                    snippet = output[:500] if output else "<no output>"
                    raise InvalidBenchmarkCaseError(
                        "Injected target test did not fail preflight. "
                        f"test_command={case.test_command!r} output={snippet!r}"
                    )
            result = runtime.run_case(case, model_name=model, case_id=run_case_id)
            record.update(
                {
                    "status": "completed",
                    "resolved": result.resolved,
                    "failure_mode": result.failure_mode,
                    "target_test_exit_code": result.target_test_exit_code,
                    "regression_test_exit_code": result.regression_test_exit_code,
                    "wall_time_ms": result.wall_time_ms,
                    "planner_stats": result.planner_stats,
                    "model_text": result.model_text,
                    "critic_verdict": result.critic_verdict,
                    "critic_attempts": result.critic_attempts or [],
                }
            )
        except InvalidBenchmarkCaseError as exc:
            record.update(
                {
                    "status": "error",
                    "resolved": False,
                    "failure_mode": "invalid_benchmark_case",
                    "error": str(exc),
                }
            )
        except Exception as exc:
            record.update(
                {
                    "status": "error",
                    "resolved": False,
                    "failure_mode": "environment_error",
                    "error": str(exc),
                }
            )
        append_jsonl(output_path, record)

    if output_path.resolve() != requested_output_path:
        requested_output_path.parent.mkdir(parents=True, exist_ok=True)
        copyfile(output_path, requested_output_path)
        print(f"[run_matrix] Synced latest results to requested output path: {requested_output_path}")
        persist_latest_run_artifacts(output_path=requested_output_path, event_log_path=event_log_path)


if __name__ == "__main__":
    main()
