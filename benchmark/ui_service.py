import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class BenchmarkRunResult:
    results_path: str
    report_path: str
    run_stdout: str
    run_stderr: str
    analyze_stdout: str
    analyze_stderr: str
    report: Dict[str, dict]


def list_manifests(manifests_dir: str = "benchmark/manifests") -> List[str]:
    root = Path(manifests_dir)
    if not root.exists():
        return []
    return sorted(str(path) for path in root.glob("*.jsonl"))


def _run_cli(command: List[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )


def build_manifest(
    historical_source: str,
    synthetic_source: str,
    output: str,
    target_count: int = 30,
    historical_ratio: float = 0.7,
    synthetic_ratio: float = 0.3,
    seed: int = 13,
) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        "-m",
        "benchmark.build_manifest",
        "--historical-source",
        historical_source,
        "--synthetic-source",
        synthetic_source,
        "--output",
        output,
        "--target-count",
        str(target_count),
        "--historical-ratio",
        str(historical_ratio),
        "--synthetic-ratio",
        str(synthetic_ratio),
        "--seed",
        str(seed),
    ]
    return _run_cli(cmd)


def run_matrix(
    manifest: str,
    models: str,
    output: str,
    max_steps: int = 15,
    timeout_s: int = 180,
    repetitions: int = 1,
    allow_append: bool = False,
    event_log: str = "",
) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        "-m",
        "benchmark.run_matrix",
        "--manifest",
        manifest,
        "--models",
        models,
        "--output",
        output,
        "--max-steps",
        str(max_steps),
        "--timeout-s",
        str(timeout_s),
        "--repetitions",
        str(repetitions),
    ]
    if allow_append:
        cmd.append("--allow-append")
    if event_log:
        cmd.extend(["--event-log", event_log])
    return _run_cli(cmd)


def analyze(input_path: str, output: str) -> subprocess.CompletedProcess:
    cmd = [
        sys.executable,
        "-m",
        "benchmark.analyze",
        "--input",
        input_path,
        "--output",
        output,
    ]
    return _run_cli(cmd)


def run_pipeline(
    manifest: str,
    models: str,
    output: str = "logs/benchmark_results.jsonl",
    report_output: str = "logs/benchmark_report.json",
    max_steps: int = 15,
    timeout_s: int = 180,
    repetitions: int = 1,
    allow_append: bool = False,
    event_log: str = "",
) -> BenchmarkRunResult:
    run_proc = run_matrix(
        manifest=manifest,
        models=models,
        output=output,
        max_steps=max_steps,
        timeout_s=timeout_s,
        repetitions=repetitions,
        allow_append=allow_append,
        event_log=event_log,
    )
    if run_proc.returncode != 0:
        raise RuntimeError(f"run_matrix failed:\n{run_proc.stdout}\n{run_proc.stderr}")

    analyze_proc = analyze(input_path=output, output=report_output)
    if analyze_proc.returncode != 0:
        raise RuntimeError(f"analyze failed:\n{analyze_proc.stdout}\n{analyze_proc.stderr}")

    report_path = Path(report_output)
    report = {}
    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))

    return BenchmarkRunResult(
        results_path=str(Path(output).resolve()),
        report_path=str(report_path.resolve()),
        run_stdout=run_proc.stdout,
        run_stderr=run_proc.stderr,
        analyze_stdout=analyze_proc.stdout,
        analyze_stderr=analyze_proc.stderr,
        report=report,
    )
