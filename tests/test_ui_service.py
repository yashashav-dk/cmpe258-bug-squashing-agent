import json
import os
from pathlib import Path
import subprocess

from benchmark import ui_service


def test_list_manifests_returns_jsonl_paths(tmp_path):
    manifests_dir = tmp_path / "benchmark" / "manifests"
    manifests_dir.mkdir(parents=True)
    (manifests_dir / "a.jsonl").write_text("", encoding="utf-8")
    (manifests_dir / "b.jsonl").write_text("", encoding="utf-8")
    (manifests_dir / "ignore.txt").write_text("", encoding="utf-8")

    manifests = ui_service.list_manifests(str(manifests_dir))

    assert manifests == sorted(
        [
            str(manifests_dir / "a.jsonl"),
            str(manifests_dir / "b.jsonl"),
        ]
    )


def test_run_pipeline_reads_report_and_returns_paths(tmp_path, monkeypatch):
    output = tmp_path / "logs" / "benchmark_results.jsonl"
    report = tmp_path / "logs" / "benchmark_report.json"
    report.parent.mkdir(parents=True)
    report.write_text(
        json.dumps({"gemma4": {"runs": 1, "resolved": 1}}, sort_keys=True),
        encoding="utf-8",
    )

    ok_proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="ok", stderr="")

    monkeypatch.setattr(ui_service, "run_matrix", lambda **_: ok_proc)
    monkeypatch.setattr(ui_service, "analyze", lambda **_: ok_proc)

    previous = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = ui_service.run_pipeline(
            manifest="benchmark/manifests/pilot_hybrid.jsonl",
            models="gemma4",
            output=str(output),
            report_output=str(report),
        )
    finally:
        os.chdir(previous)

    assert result.results_path.endswith("benchmark_results.jsonl")
    assert result.report_path.endswith("benchmark_report.json")
    assert result.report["gemma4"]["resolved"] == 1
