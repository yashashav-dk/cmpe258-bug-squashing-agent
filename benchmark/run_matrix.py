import argparse
import json
import os
import random
import re
import shutil
import subprocess
from shutil import copyfile
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional
from uuid import uuid4

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


def make_run_id() -> str:
    return f"{_timestamp_suffix()}_{uuid4().hex[:8]}"


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
    return output_path.with_name("events.jsonl")


def persist_latest_run_artifacts(output_path: Path, event_log_path: Path, run_dir: Path) -> None:
    latest_results = Path("logs/latest_results_path.txt")
    latest_events = Path("logs/latest_events_path.txt")
    latest_run_dir = Path("logs/latest_run_dir_path.txt")
    latest_run_id = Path("logs/latest_run_id.txt")
    latest_results.parent.mkdir(parents=True, exist_ok=True)
    latest_results.write_text(str(output_path.resolve()), encoding="utf-8")
    latest_events.write_text(str(event_log_path.resolve()), encoding="utf-8")
    latest_run_dir.write_text(str(run_dir.resolve()), encoding="utf-8")
    latest_run_id.write_text(run_dir.name, encoding="utf-8")


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


def _is_dataset_case_workspace(workspace_dir: str) -> bool:
    if not workspace_dir or not workspace_dir.strip():
        return False
    return bool(re.search(r"dataset/cases/case_\d+", workspace_dir.replace("\\", "/")))


def _materialize_workspace_copy(repo_root: Path, manifest_workspace: str, dest: Path) -> None:
    src = (repo_root / manifest_workspace.lstrip("./")).resolve()
    if not src.is_dir():
        raise FileNotFoundError(f"workspace copy source missing: {src}")
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        src,
        dest,
        symlinks=False,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache", ".DS_Store"),
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
    parser.add_argument(
        "--dataset-in-place",
        action="store_true",
        help="Use dataset/cases paths in the repo directly (mutates files). Default copies each case to RUN_DIR/workspaces.",
    )
    parser.add_argument(
        "--keep-temp-workspaces",
        action="store_true",
        help="Keep per-attempt copies under RUN_DIR/workspaces after each case (default: delete).",
    )
    args = parser.parse_args()

    random.seed(args.seed)
    cases = load_manifest(args.manifest)
    models = parse_models(args.models)
    requested_output_path = Path(args.output).resolve()
    run_id = make_run_id()
    run_dir = Path("logs") / "runs" / run_id
    output_path = (run_dir / "results.jsonl").resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    event_log_path = resolve_event_log_path(
        output_path=output_path,
        explicit_path=args.event_log,
        allow_append=args.allow_append,
    ).resolve()
    persist_latest_run_artifacts(output_path=output_path, event_log_path=event_log_path, run_dir=run_dir)
    print(f"[run_matrix] RUN_ID={run_id}")
    print(f"[run_matrix] RUN_DIR={run_dir.resolve()}")
    print(f"[run_matrix] RESULTS_PATH={output_path.resolve()}")
    print(f"[run_matrix] EVENTS_PATH={event_log_path}")
    if not args.dataset_in_place:
        print(
            "[run_matrix] dataset/cases workspaces → per-attempt copy under RUN_DIR/workspaces "
            "(pass --dataset-in-place to write into the repo checkout)."
        )
    event_logger = Logger(str(event_log_path))
    runtime = AgentRuntime(max_steps=args.max_steps, timeout_s=args.timeout_s, logger=event_logger)

    repo_root = Path.cwd().resolve()

    for case, model, rep in iter_matrix(cases, models, args.repetitions):
        run_case_id = f"{case.case_id}__{model}__rep{rep}"
        manifest_workspace = case.metadata.get("workspace_dir", "")
        temp_workspace: Optional[Path] = None
        effective_workspace = manifest_workspace

        use_temp = (
            bool(manifest_workspace)
            and _is_dataset_case_workspace(manifest_workspace)
            and not args.dataset_in_place
        )
        if use_temp:
            temp_workspace = (run_dir / "workspaces" / run_case_id).resolve()
            _materialize_workspace_copy(repo_root, manifest_workspace, temp_workspace)
            effective_workspace = str(temp_workspace)

        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": run_id,
            "row_type": "start",
            "attempt_id": run_case_id,
            "run_case_id": run_case_id,
            "case_id": case.case_id,
            "model": model,
            "repetition": rep,
            "seed": case.seed + rep,
            "case_hash": case.content_hash(),
            "manifest_path": str(Path(args.manifest).resolve()),
            "workspace_dir": manifest_workspace,
            "source_type": case.source_type,
            "difficulty": case.difficulty,
            "tags": case.tags,
            "status": "started",
        }
        if use_temp:
            record["runner_workspace_dir"] = effective_workspace
        append_jsonl(output_path, record)
        terminal_record = dict(record)
        terminal_record["row_type"] = "terminal"
        terminal_record["timestamp"] = datetime.now(timezone.utc).isoformat()

        try:
            if not args.skip_injection:
                if effective_workspace and case.base_commit:
                    reset_workspace(workspace_dir=effective_workspace, base_commit=case.base_commit)
                apply_injection(case, workspace_dir=effective_workspace)
                preflight = run_preflight_test(
                    case.test_command, workspace_dir=effective_workspace, timeout_s=args.timeout_s
                )
                if preflight.returncode == 0:
                    output = (preflight.stdout + preflight.stderr).strip()
                    snippet = output[:500] if output else "<no output>"
                    raise InvalidBenchmarkCaseError(
                        "Injected target test did not fail preflight. "
                        f"test_command={case.test_command!r} output={snippet!r}"
                    )
            result = runtime.run_case(
                case,
                model_name=model,
                case_id=run_case_id,
                workspace_root=effective_workspace,
            )
            terminal_record.update(
                {
                    "status": "completed",
                    "resolved": result.resolved,
                    "failure_mode": result.failure_mode,
                    "target_test_exit_code": result.target_test_exit_code,
                    "regression_test_exit_code": result.regression_test_exit_code,
                    "wall_time_ms": result.wall_time_ms,
                    "planner_stats": result.planner_stats,
                    "model_text": result.model_text,
                }
            )
        except InvalidBenchmarkCaseError as exc:
            terminal_record.update(
                {
                    "status": "error",
                    "resolved": False,
                    "failure_mode": "invalid_benchmark_case",
                    "error": str(exc),
                }
            )
        except Exception as exc:
            terminal_record.update(
                {
                    "status": "error",
                    "resolved": False,
                    "failure_mode": "environment_error",
                    "error": str(exc),
                }
            )
        finally:
            keep = args.keep_temp_workspaces or os.environ.get(
                "BENCHMARK_KEEP_WORKSPACE_COPY", ""
            ).strip().lower() in ("1", "true", "yes")
            if temp_workspace is not None and temp_workspace.exists() and not keep:
                shutil.rmtree(temp_workspace, ignore_errors=True)

        append_jsonl(output_path, terminal_record)

    if output_path.resolve() != requested_output_path:
        requested_output_path.parent.mkdir(parents=True, exist_ok=True)
        copyfile(output_path, requested_output_path)
        print(f"[run_matrix] Synced latest results to requested output path: {requested_output_path}")


if __name__ == "__main__":
    main()
