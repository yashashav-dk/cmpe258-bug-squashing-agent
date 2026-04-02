import os
import pytest
from agent.executor import Executor, PatchError


def make_executor(tmp_path, case_id="case_test"):
    case_dir = tmp_path / "dataset" / "cases" / case_id
    case_dir.mkdir(parents=True)
    return Executor(cases_root=str(tmp_path / "dataset" / "cases")), case_dir


def make_patch(line_range, fix):
    return {
        "file": "buggy.py",
        "line_range": line_range,
        "root_cause": "test",
        "proposed_fix": fix,
    }


def test_executor_applies_patch(tmp_path):
    executor, case_dir = make_executor(tmp_path)
    buggy = case_dir / "buggy.py"
    buggy.write_text("line1\nline2\nline3\n")
    patch = make_patch([2, 2], "replaced\n")
    executor.apply_patch(patch, case_id="case_test")
    assert buggy.read_text() == "line1\nreplaced\nline3\n"


def test_executor_atomic_write_rejects_invalid_python(tmp_path):
    executor, case_dir = make_executor(tmp_path)
    buggy = case_dir / "buggy.py"
    original = "def f():\n    return 1\n"
    buggy.write_text(original)
    patch = make_patch([1, 2], "def f(\n  INVALID SYNTAX!!!\n")
    with pytest.raises(PatchError):
        executor.apply_patch(patch, case_id="case_test")
    assert buggy.read_text() == original  # original untouched


def test_executor_rejects_path_traversal(tmp_path):
    executor, case_dir = make_executor(tmp_path)
    patch = {
        "file": "../../config.py",
        "line_range": [1, 1],
        "root_cause": "attack",
        "proposed_fix": "HACKED\n",
    }
    with pytest.raises(PatchError, match="Scope violation"):
        executor.apply_patch(patch, case_id="case_test")


def test_executor_runs_pytest_and_returns_result(tmp_path):
    executor, case_dir = make_executor(tmp_path)
    buggy = case_dir / "buggy.py"
    buggy.write_text("def f():\n    return 1\n")
    test_file = case_dir / "test_buggy.py"
    test_file.write_text("from buggy import f\ndef test_f():\n    assert f() == 1\n")
    passed, traceback = executor.run_tests(case_id="case_test")
    assert passed is True
    assert traceback == ""


def test_executor_captures_failure_traceback(tmp_path):
    executor, case_dir = make_executor(tmp_path)
    buggy = case_dir / "buggy.py"
    buggy.write_text("def f():\n    return 99\n")
    test_file = case_dir / "test_buggy.py"
    test_file.write_text("from buggy import f\ndef test_f():\n    assert f() == 1\n")
    passed, traceback = executor.run_tests(case_id="case_test")
    assert passed is False
    assert "assert" in traceback.lower() or "failed" in traceback.lower()
