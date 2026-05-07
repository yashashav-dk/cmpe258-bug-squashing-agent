import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def canonicalize_model_name(model: str) -> str:
    key = str(model).strip().lower()
    aliases = {
        "gemm4": "gemma4",
        "gemma-4": "gemma4",
    }
    return aliases.get(key, key)


def resolve_input_path(raw: str) -> str:
    if raw != "latest":
        return raw
    latest_pointer = Path("logs/latest_results_path.txt")
    if not latest_pointer.exists():
        raise FileNotFoundError("latest results pointer not found: logs/latest_results_path.txt")
    resolved = latest_pointer.read_text(encoding="utf-8").strip()
    if not resolved:
        raise FileNotFoundError("latest results pointer is empty: logs/latest_results_path.txt")
    return resolved


def load_rows(path: str) -> List[dict]:
    rows: List[dict] = []
    result_path = Path(path)
    if not result_path.exists():
        raise FileNotFoundError(path)
    with result_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            rows.append(json.loads(stripped))
    return rows


def _percentile(sorted_values: List[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = int(max(0, math.ceil(pct * len(sorted_values)) - 1))
    return sorted_values[idx]


def _safe_repetition(row: dict) -> int:
    try:
        return int(row.get("repetition", 0))
    except Exception:
        return 0


def _attempt_id(row: dict) -> str:
    return str(row.get("attempt_id") or row.get("run_case_id") or "")


def _build_cases(attempts: List[dict], manifest_cases: Dict[str, dict]) -> List[dict]:
    cases: Dict[str, dict] = {}
    for attempt in attempts:
        case_id = str(attempt.get("case_id", "")).strip()
        if not case_id:
            continue
        base = cases.setdefault(
            case_id,
            {
                "case_id": case_id,
                "source_type": attempt.get("source_type"),
                "difficulty": attempt.get("difficulty"),
                "tags": attempt.get("tags", []),
            },
        )
        if not base.get("tags") and attempt.get("tags"):
            base["tags"] = attempt.get("tags", [])

    for case_id, payload in manifest_cases.items():
        merged = cases.setdefault(
            case_id,
            {
                "case_id": case_id,
                "source_type": payload.get("source_type"),
                "difficulty": payload.get("difficulty"),
                "tags": payload.get("tags", []),
            },
        )
        for key in ("source_type", "difficulty", "tags"):
            if merged.get(key) in (None, "", []):
                merged[key] = payload.get(key)

    return sorted(cases.values(), key=lambda item: item["case_id"])


def _summarize_models(attempts: List[dict]) -> List[dict]:
    by_model: Dict[str, dict] = defaultdict(
        lambda: {
            "runs": 0,
            "resolved": 0,
            "error_runs": 0,
            "wall_time_ms": [],
            "failure_modes": Counter(),
        }
    )

    for attempt in attempts:
        model = canonicalize_model_name(str(attempt.get("model", "")))
        if not model:
            continue
        bucket = by_model[model]
        bucket["runs"] += 1
        bucket["resolved"] += int(bool(attempt.get("resolved")))
        if attempt.get("status") == "error":
            bucket["error_runs"] += 1
        wall_time = attempt.get("wall_time_ms")
        if isinstance(wall_time, (int, float)):
            bucket["wall_time_ms"].append(float(wall_time))
        bucket["failure_modes"][str(attempt.get("failure_mode", "unknown"))] += 1

    output: List[dict] = []
    for model, bucket in sorted(by_model.items()):
        runs = bucket["runs"]
        resolved = bucket["resolved"]
        unresolved = runs - resolved
        wall_times = sorted(bucket["wall_time_ms"])
        output.append(
            {
                "model": model,
                "runs": runs,
                "resolved": resolved,
                "unresolved": unresolved,
                "pass_rate": (resolved / runs) if runs else 0.0,
                "error_runs": bucket["error_runs"],
                "latency_ms": {
                    "avg": (sum(wall_times) / len(wall_times)) if wall_times else 0.0,
                    "p50": _percentile(wall_times, 0.5),
                    "p90": _percentile(wall_times, 0.9),
                    "p99": _percentile(wall_times, 0.99),
                },
                "failure_modes": dict(bucket["failure_modes"]),
            }
        )
    return output


def _build_matrix(attempts: Iterable[dict]) -> Dict[str, Dict[str, dict]]:
    matrix: Dict[str, Dict[str, dict]] = defaultdict(dict)
    for attempt in attempts:
        model = canonicalize_model_name(str(attempt.get("model", "")))
        case_id = str(attempt.get("case_id", ""))
        if not model or not case_id:
            continue
        matrix[model][case_id] = {
            "attempt_id": attempt.get("attempt_id"),
            "status": attempt.get("status"),
            "resolved": bool(attempt.get("resolved")),
            "failure_mode": attempt.get("failure_mode"),
        }
    return {model: cases for model, cases in sorted(matrix.items())}


def _load_manifest_case_lookup(manifest_path: Optional[str]) -> Dict[str, dict]:
    if not manifest_path:
        return {}
    path = Path(manifest_path)
    if not path.exists():
        return {}
    lookup: Dict[str, dict] = {}
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped:
                continue
            payload = json.loads(stripped)
            case_id = payload.get("case_id")
            if case_id:
                lookup[str(case_id)] = payload
    return lookup


def materialize_ui_report(results_path: str, manifest_path: Optional[str] = None) -> Dict[str, Any]:
    rows = load_rows(results_path)
    starts: Dict[str, dict] = {}
    terminals: Dict[str, dict] = {}

    for row in rows:
        row_type = row.get("row_type")
        status = row.get("status")
        attempt_id = _attempt_id(row)
        if not attempt_id:
            continue

        if row_type == "start" or status == "started":
            starts[attempt_id] = row
        elif row_type == "terminal" or status in {"completed", "error"}:
            terminals[attempt_id] = row

    attempts: List[dict] = []
    for attempt_id, terminal in sorted(terminals.items()):
        start = starts.get(attempt_id, {})
        merged = dict(start)
        merged.update(terminal)
        merged["attempt_id"] = attempt_id
        merged["model"] = canonicalize_model_name(str(merged.get("model", "")))
        merged["repetition"] = _safe_repetition(merged)
        attempts.append(
            {
                "attempt_id": attempt_id,
                "run_id": merged.get("run_id"),
                "case_id": merged.get("case_id"),
                "model": merged.get("model"),
                "repetition": merged.get("repetition"),
                "status": merged.get("status"),
                "resolved": bool(merged.get("resolved")),
                "failure_mode": merged.get("failure_mode"),
                "wall_time_ms": merged.get("wall_time_ms"),
                "target_test_exit_code": merged.get("target_test_exit_code"),
                "regression_test_exit_code": merged.get("regression_test_exit_code"),
                "planner_stats": merged.get("planner_stats", {}),
                "source_type": merged.get("source_type"),
                "difficulty": merged.get("difficulty"),
                "tags": merged.get("tags", []),
                "error": merged.get("error"),
            }
        )

    manifest_hint = manifest_path
    if not manifest_hint and rows:
        manifest_hint = rows[0].get("manifest_path")
    manifest_cases = _load_manifest_case_lookup(manifest_hint)

    run_id = ""
    if rows:
        run_id = str(rows[0].get("run_id", "")).strip()
    if not run_id:
        parent = Path(results_path).resolve().parent
        if parent.name:
            run_id = parent.name

    run_summary = {
        "run_id": run_id,
        "results_path": str(Path(results_path).resolve()),
        "manifest_path": str(Path(manifest_hint).resolve()) if manifest_hint else None,
    }
    return {
        "run": run_summary,
        "models": _summarize_models(attempts),
        "cases": _build_cases(attempts, manifest_cases),
        "attempts": attempts,
        "matrix": _build_matrix(attempts),
    }


def write_ui_report(report: Dict[str, Any], output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return str(path.resolve())


def main() -> None:
    parser = argparse.ArgumentParser(description="Materialize UI-friendly benchmark report JSON")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to benchmark results JSONL (or 'latest' to use logs/latest_results_path.txt).",
    )
    parser.add_argument(
        "--manifest",
        default="",
        help="Optional path to benchmark manifest JSONL to enrich case metadata.",
    )
    parser.add_argument("--output", required=True, help="Path to write ui_report JSON")
    args = parser.parse_args()

    input_path = resolve_input_path(args.input)
    report = materialize_ui_report(results_path=input_path, manifest_path=(args.manifest or None))
    output = write_ui_report(report, args.output)
    print(f"[materialize_ui_report] INPUT_PATH={Path(input_path).resolve()}")
    print(f"[materialize_ui_report] OUTPUT_PATH={output}")


if __name__ == "__main__":
    main()
