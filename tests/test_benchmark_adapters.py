import json

from benchmark.adapters.historical import HistoricalBugAdapter
from benchmark.adapters.synthetic import SyntheticMutationAdapter


def test_historical_adapter_builds_cases(tmp_path):
    source = tmp_path / "historical.jsonl"
    source.write_text(
        json.dumps(
            {
                "case_id": "hist_1",
                "source_type": "historical",
                "repo_url": "https://example.com/repo.git",
                "repo_name": "repo",
                "base_commit": "abc123",
                "python_version": "3.11",
                "install": ["pip install -e ."],
                "test_command": "pytest tests/test_a.py -q",
                "regression_test_command": "pytest tests -q",
                "allowed_paths": ["src/"],
                "target_file": "src/mod.py",
                "injection_patch": "patch",
                "expected_failures": ["tests/test_a.py::test_one"],
                "tags": ["historical"],
                "difficulty": "medium",
                "seed": 11,
                "metadata": {"workspace_dir": "."},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    rows = HistoricalBugAdapter(str(source)).build_cases()
    assert len(rows) == 1
    assert rows[0].case_id == "hist_1"


def test_synthetic_adapter_deterministic_operator(tmp_path):
    source = tmp_path / "synthetic.jsonl"
    source.write_text(
        json.dumps(
            {
                "template_id": "tmpl_1",
                "repo_url": "https://example.com/repo.git",
                "repo_name": "repo",
                "base_commit": "abc123",
                "python_version": "3.11",
                "install": ["pip install -e ."],
                "test_command": "pytest tests/test_a.py -q",
                "regression_test_command": "pytest tests -q",
                "allowed_paths": ["src/"],
                "target_file": "src/mod.py",
                "baseline_content": "def f(x):\n    return x > 0\n",
                "expected_failures": ["tests/test_a.py::test_one"],
                "seed": 7,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rows = SyntheticMutationAdapter(str(source)).build_cases()
    assert len(rows) == 1
    assert rows[0].source_type == "synthetic"
    assert rows[0].metadata["operator"]
    assert rows[0].injection_patch


def test_synthetic_adapter_supports_template_declared_mutation(tmp_path):
    source = tmp_path / "synthetic_declared.jsonl"
    source.write_text(
        json.dumps(
            {
                "template_id": "tmpl_declared",
                "repo_url": "local://dataset/cases",
                "repo_name": "local_dataset",
                "base_commit": "dataset-fixture-v1",
                "python_version": "3.11",
                "install": ["pip install -r requirements.txt"],
                "test_command": "python -m pytest test_buggy.py::test_one -q",
                "regression_test_command": "python -m pytest test_buggy.py -q",
                "allowed_paths": ["."],
                "target_file": "buggy.py",
                "baseline_content": "def f():\n    return 1\n",
                "expected_failures": ["test_buggy.py::test_one"],
                "seed": 301,
                "workspace_dir": "./dataset/cases/case_001",
                "objective": "Fix f().",
                "difficulty": "easy",
                "tags": ["synthetic", "local_fixture"],
                "mutation": {
                    "name": "force_declared",
                    "old_content": "return 1",
                    "new_content": "return 2",
                    "tags": ["declared_mutation"],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )

    rows = SyntheticMutationAdapter(str(source)).build_cases()
    assert len(rows) == 1
    assert rows[0].metadata["operator"] == "force_declared"
    assert rows[0].metadata["workspace_dir"] == "./dataset/cases/case_001"
    assert "return 1" in rows[0].injection_patch
    assert "return 2" in rows[0].injection_patch
