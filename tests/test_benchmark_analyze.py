from pathlib import Path

from benchmark.analyze import (
    build_report,
    resolve_input_path,
    summarize,
    wilson_interval,
)


def test_wilson_interval_bounds():
    interval = wilson_interval(5, 10)
    assert 0.0 <= interval["low"] <= interval["high"] <= 1.0


def test_summarize_groups_by_model():
    rows = [
        {
            "status": "completed",
            "model": "gemma4",
            "resolved": True,
            "wall_time_ms": 100.0,
            "failure_mode": "none",
            "planner_stats": {"total_input_tokens": 10, "total_output_tokens": 5, "steps": 2},
        },
        {
            "status": "completed",
            "model": "gemma4",
            "resolved": False,
            "wall_time_ms": 120.0,
            "failure_mode": "localization_failure",
            "planner_stats": {"total_input_tokens": 20, "total_output_tokens": 10, "steps": 4},
        },
    ]
    summary = summarize(rows)
    assert summary["gemma4"]["total"] == 2
    assert summary["gemma4"]["resolved"] == 1
    assert summary["gemma4"]["retry_depths"] == [2, 4]


def test_build_report_contains_new_metric_fields():
    summary = {
        "gemini": {
            "total": 3,
            "resolved": 2,
            "wall_time_ms": [100.0, 200.0, 300.0],
            "input_tokens": 3000,
            "output_tokens": 6000,
            "retry_depths": [1, 2, 2],
            "failure_mode_counts": {"none": 2, "localization_failure": 1},
        }
    }
    report = build_report(summary)
    row = report["gemini"]
    assert row["latency_ms"]["avg"] == 200.0
    assert row["latency_ms"]["p99"] == 300.0
    assert row["retry_depth_distribution"] == {"1": 1, "2": 2}
    assert row["retry_depth"]["max"] == 2
    assert row["estimated_cost_usd"]["total"] > 0.0
    assert row["cost_per_successful_fix_usd"] is not None
    assert row["consistency_checks"]["resolved_plus_unresolved_equals_runs"] is True


def test_build_report_zero_success_has_null_cost_per_fix():
    summary = {
        "qwen": {
            "total": 2,
            "resolved": 0,
            "wall_time_ms": [100.0, 200.0],
            "input_tokens": 1000,
            "output_tokens": 500,
            "retry_depths": [3, 4],
            "failure_mode_counts": {"localization_failure": 2},
        }
    }
    report = build_report(summary)
    row = report["qwen"]
    assert row["cost_per_successful_fix_usd"] is None
    assert row["unresolved"] == 2


def test_resolve_input_path_latest_pointer(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    result_file = logs / "results.jsonl"
    result_file.write_text("", encoding="utf-8")
    (logs / "latest_results_path.txt").write_text(str(result_file.resolve()), encoding="utf-8")

    previous = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)
        resolved = resolve_input_path("latest")
    finally:
        import os
        os.chdir(previous)

    assert resolved.endswith("results.jsonl")
