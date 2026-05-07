import json

import pytest

from benchmark.manifest import case_from_payload, load_manifest, write_manifest


def make_payload():
    return {
        "case_id": "case_a",
        "source_type": "historical",
        "repo_url": "https://example.com/repo.git",
        "repo_name": "repo",
        "base_commit": "abc123",
        "python_version": "3.11",
        "install": ["pip install -e ."],
        "test_command": "pytest tests/test_a.py -q",
        "regression_test_command": "pytest tests -q",
        "allowed_paths": ["src/"],
        "target_file": "src/module.py",
        "injection_patch": "patch",
        "expected_failures": ["tests/test_a.py::test_one"],
        "tags": ["historical"],
        "difficulty": "medium",
        "seed": 1,
        "metadata": {"workspace_dir": "."},
    }


def test_case_from_payload_valid():
    case = case_from_payload(make_payload())
    assert case.case_id == "case_a"
    assert case.source_type == "historical"


def test_case_from_payload_invalid_source():
    payload = make_payload()
    payload["source_type"] = "unknown"
    with pytest.raises(ValueError, match="source_type"):
        case_from_payload(payload)


def test_manifest_round_trip(tmp_path):
    manifest = tmp_path / "manifest.jsonl"
    case = case_from_payload(make_payload())
    write_manifest(str(manifest), [case])

    rows = load_manifest(str(manifest))
    assert len(rows) == 1
    assert rows[0].content_hash() == case.content_hash()


def test_manifest_reports_line_error(tmp_path):
    manifest = tmp_path / "bad.jsonl"
    manifest.write_text(json.dumps(make_payload()) + "\n{bad-json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="line 2"):
        load_manifest(str(manifest))
