import subprocess

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

import web.app as web_app


def test_manifests_endpoint_returns_list(monkeypatch):
    monkeypatch.setattr(web_app, "list_manifests", lambda: ["benchmark/manifests/pilot_hybrid.jsonl"])
    client = TestClient(web_app.app)

    response = client.get("/api/manifests")

    assert response.status_code == 200
    assert response.json()["manifests"] == ["benchmark/manifests/pilot_hybrid.jsonl"]


def test_build_manifest_endpoint(monkeypatch):
    proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="built", stderr="")
    monkeypatch.setattr(web_app, "build_manifest", lambda **_: proc)
    client = TestClient(web_app.app)

    response = client.post(
        "/api/build-manifest",
        data={
            "historical_source": "benchmark/data/historical_cases.sample.jsonl",
            "synthetic_source": "benchmark/data/synthetic_templates.sample.jsonl",
            "output": "benchmark/manifests/pilot_hybrid.jsonl",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is True
    assert body["returncode"] == 0


def test_run_manifest_endpoint(monkeypatch):
    class DummyResult:
        results_path = "/tmp/results.jsonl"
        report_path = "/tmp/report.json"
        run_stdout = "run"
        run_stderr = ""
        analyze_stdout = "analyze"
        analyze_stderr = ""
        report = {"gemma4": {"runs": 1, "resolved": 1}}

    monkeypatch.setattr(web_app, "run_pipeline", lambda **_: DummyResult())
    client = TestClient(web_app.app)

    response = client.post(
        "/api/run-manifest",
        data={
            "manifest": "benchmark/manifests/pilot_hybrid.jsonl",
            "models": "gemma4",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["ok"] is True
    assert body["report"]["gemma4"]["resolved"] == 1
