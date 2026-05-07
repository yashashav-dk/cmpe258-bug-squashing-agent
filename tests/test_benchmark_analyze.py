from pathlib import Path

from benchmark.analyze import summarize, wilson_interval, resolve_input_path


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
            "planner_stats": {"total_input_tokens": 10, "total_output_tokens": 5},
        },
        {
            "status": "completed",
            "model": "gemma4",
            "resolved": False,
            "wall_time_ms": 120.0,
            "failure_mode": "localization_failure",
            "planner_stats": {"total_input_tokens": 20, "total_output_tokens": 10},
        },
    ]
    summary = summarize(rows)
    assert summary["gemma4"]["total"] == 2
    assert summary["gemma4"]["resolved"] == 1


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
