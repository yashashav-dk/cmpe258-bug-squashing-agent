import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, Iterable, List

from benchmark.protocol import MODEL_PRICING_USD_PER_1M, PRICING_SOURCE


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
            "retry_depths": [],
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
        bucket["retry_depths"].append(int(stats.get("steps", 0)))
        bucket["failure_mode_counts"][row.get("failure_mode", "unknown")] += 1
    return by_model


def _percentile(sorted_values: List[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    idx = int(max(0, math.ceil(pct * len(sorted_values)) - 1))
    return sorted_values[idx]


def build_report(summary: Dict[str, dict]) -> Dict[str, dict]:
    report: Dict[str, dict] = {}
    for model, stats in summary.items():
        total = stats["total"]
        resolved = stats["resolved"]
        unresolved = total - resolved
        pass_rate = (resolved / total) if total else 0.0
        wall_times = sorted(stats["wall_time_ms"])
        retry_depths = stats["retry_depths"]
        retry_hist = Counter(retry_depths)
        pricing = MODEL_PRICING_USD_PER_1M.get(model, {"input": 0.0, "output": 0.0})
        input_cost = (stats["input_tokens"] / 1_000_000.0) * float(pricing["input"])
        output_cost = (stats["output_tokens"] / 1_000_000.0) * float(pricing["output"])
        total_cost = input_cost + output_cost

        report[model] = {
            "runs": total,
            "resolved": resolved,
            "unresolved": unresolved,
            "pass_rate": pass_rate,
            "pass_rate_wilson_95": wilson_interval(resolved, total),
            "latency_ms": {
                "avg": (sum(wall_times) / len(wall_times)) if wall_times else 0.0,
                "p50": _percentile(wall_times, 0.5),
                "p90": _percentile(wall_times, 0.9),
                "p99": _percentile(wall_times, 0.99),
            },
            "retry_depth": {
                "avg": (sum(retry_depths) / len(retry_depths)) if retry_depths else 0.0,
                "max": max(retry_depths) if retry_depths else 0,
            },
            "retry_depth_distribution": {
                str(depth): count for depth, count in sorted(retry_hist.items())
            },
            "token_usage": {
                "input_tokens": stats["input_tokens"],
                "output_tokens": stats["output_tokens"],
            },
            "pricing_assumptions": {
                "input_usd_per_1m": float(pricing["input"]),
                "output_usd_per_1m": float(pricing["output"]),
                "source": PRICING_SOURCE,
            },
            "estimated_cost_usd": {
                "input": input_cost,
                "output": output_cost,
                "total": total_cost,
            },
            "cost_per_successful_fix_usd": (
                (total_cost / resolved) if resolved > 0 else None
            ),
            "consistency_checks": {
                "resolved_plus_unresolved_equals_runs": (resolved + unresolved) == total,
            },
            "failure_modes": dict(stats["failure_mode_counts"]),
        }
    return report


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
    report = build_report(summary)

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
