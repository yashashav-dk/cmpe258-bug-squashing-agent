import os
from benchmark.run_matrix import (
    run_preflight_test,
    reset_workspace,
    resolve_output_path,
    resolve_event_log_path,
    persist_latest_run_artifacts,
)


def test_reset_workspace_restores_local_fixture(tmp_path):
    workspace = tmp_path / "case_local"
    workspace.mkdir(parents=True)
    (workspace / "golden.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    (workspace / "buggy.py").write_text("def f():\n    return 2\n", encoding="utf-8")

    reset_workspace(str(workspace), base_commit="dataset-fixture-v1")

    assert (workspace / "buggy.py").read_text(encoding="utf-8") == (
        workspace / "golden.py"
    ).read_text(encoding="utf-8")


def test_run_preflight_test_reports_command_status(tmp_path):
    workspace = tmp_path / "case_local"
    workspace.mkdir(parents=True)
    (workspace / "test_buggy.py").write_text(
        "def test_fail():\n    assert False\n",
        encoding="utf-8",
    )

    result = run_preflight_test(
        "python -m pytest test_buggy.py::test_fail -q",
        workspace_dir=str(workspace),
        timeout_s=30,
    )

    assert result.returncode != 0


def test_resolve_output_path_uses_unique_when_file_exists(tmp_path):
    output = tmp_path / "results.jsonl"
    output.write_text("existing\n", encoding="utf-8")

    resolved = resolve_output_path(output, allow_append=False)

    assert resolved != output
    assert resolved.name.startswith("results_")
    assert resolved.suffix == ".jsonl"


def test_resolve_event_log_path_infers_unique_from_output(tmp_path):
    output = tmp_path / "results_abc.jsonl"
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    default_event = logs / "benchmark_events.jsonl"
    default_event.write_text("existing\n", encoding="utf-8")

    previous = os.getcwd()
    try:
        os.chdir(tmp_path)
        resolved = resolve_event_log_path(
            output_path=output,
            explicit_path="",
            allow_append=False,
        )
    finally:
        os.chdir(previous)

    assert "benchmark_events_results_abc" in resolved.name


def test_persist_latest_run_artifacts_writes_pointers(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir(parents=True)
    output = logs / "results.jsonl"
    events = logs / "events.jsonl"
    output.write_text("", encoding="utf-8")
    events.write_text("", encoding="utf-8")

    previous = os.getcwd()
    try:
        os.chdir(tmp_path)
        persist_latest_run_artifacts(output_path=output, event_log_path=events)
    finally:
        os.chdir(previous)

    latest_results = (logs / "latest_results_path.txt").read_text(encoding="utf-8").strip()
    latest_events = (logs / "latest_events_path.txt").read_text(encoding="utf-8").strip()
    assert latest_results.endswith("results.jsonl")
    assert latest_events.endswith("events.jsonl")
