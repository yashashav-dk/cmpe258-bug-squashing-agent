import argparse
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List


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
            if not line.strip():
                continue
            rows.append(json.loads(line))
    return rows


def wilson_interval(successes: int, total: int, z: float = 1.96) -> Dict[str, float]:
    if total == 0:
        return {"low": 0.0, "high": 0.0}
    p = successes / total
    denom = 1 + (z * z / total)
    center = (p + (z * z) / (2 * total)) / denom
    margin = z * math.sqrt((p * (1 - p) / total) + (z * z / (4 * total * total))) / denom
    return {"low": max(0.0, center - margin), "high": min(1.0, center + margin)}


def summarize(rows: Iterable[dict]) -> Dict[str, dict]:
    by_model: Dict[str, dict] = defaultdict(
        lambda: {
            "total": 0,
            "resolved": 0,
            "wall_time_ms": [],
            "input_tokens": 0,
            "output_tokens": 0,
            "failure_mode_counts": defaultdict(int),
        }
    )
    for row in rows:
        if row.get("status") != "completed":
            continue
        model = canonicalize_model_name(row["model"])
        bucket = by_model[model]
        bucket["total"] += 1
        bucket["resolved"] += int(bool(row.get("resolved")))
        bucket["wall_time_ms"].append(float(row.get("wall_time_ms", 0.0)))
        stats = row.get("planner_stats", {})
        bucket["input_tokens"] += int(stats.get("total_input_tokens", 0))
        bucket["output_tokens"] += int(stats.get("total_output_tokens", 0))
        bucket["failure_mode_counts"][row.get("failure_mode", "unknown")] += 1
    return by_model


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze benchmark JSONL output")
    parser.add_argument(
        "--input",
        required=True,
        help="Path to benchmark results JSONL (or 'latest' to use logs/latest_results_path.txt).",
    )
    parser.add_argument("--output", default="logs/benchmark_report.json")
    args = parser.parse_args()

    input_path = resolve_input_path(args.input)
    rows = load_rows(input_path)
    summary = summarize(rows)

    report: Dict[str, dict] = {}
    for model, stats in summary.items():
        total = stats["total"]
        resolved = stats["resolved"]
        pass_rate = (resolved / total) if total else 0.0
        wall_times = sorted(stats["wall_time_ms"])
        p50 = wall_times[len(wall_times) // 2] if wall_times else 0.0
        p90_idx = int(max(0, math.ceil(0.9 * len(wall_times)) - 1)) if wall_times else 0
        p90 = wall_times[p90_idx] if wall_times else 0.0

        report[model] = {
            "runs": total,
            "resolved": resolved,
            "pass_rate": pass_rate,
            "pass_rate_wilson_95": wilson_interval(resolved, total),
            "latency_ms": {"p50": p50, "p90": p90},
            "token_usage": {
                "input_tokens": stats["input_tokens"],
                "output_tokens": stats["output_tokens"],
            },
            "failure_modes": dict(stats["failure_mode_counts"]),
        }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    latest_report_pointer = Path("logs/latest_report_path.txt")
    latest_report_pointer.parent.mkdir(parents=True, exist_ok=True)
    latest_report_pointer.write_text(str(output_path.resolve()), encoding="utf-8")
    print(f"[analyze] INPUT_PATH={Path(input_path).resolve()}")
    print(f"[analyze] REPORT_PATH={output_path.resolve()}")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
