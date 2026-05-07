"""
Integration tests for memory persistence across PEC loop iterations.
"""
import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from agent.case_runtime import run_case_with_pec
from agent.memory import Memory
from models.base import BaseModel, ModelResponse


def _mock_model_bad_patch(fix: str = "    return 98\n") -> BaseModel:
    """Returns a model that always proposes a syntactically valid but wrong patch.

    The fix must be indented correctly so ast.parse() accepts it, but the test
    assertion (f() == 1) still fails — ensuring memory.record_attempt() is reached.
    """
    model = MagicMock(spec=BaseModel)
    patch_json = json.dumps({
        "file": "buggy.py",
        "line_range": [2, 2],
        "root_cause": "mock root cause",
        "proposed_fix": fix,
    })
    model.chat.return_value = ModelResponse(
        text=patch_json,
        input_tokens=100,
        output_tokens=50,
        latency_ms=200.0,
        tool_calls=None,
    )
    model.name.return_value = "mock-bad-model"
    return model


@pytest.fixture
def simple_case(tmp_path):
    """Create a minimal failing case: buggy.py returns wrong value, test expects correct."""
    case_id = "case_mem_test"
    case_dir = tmp_path / case_id
    case_dir.mkdir()
    (case_dir / "buggy.py").write_text("def f():\n    return 99\n")
    (case_dir / "test_buggy.py").write_text(
        "from buggy import f\ndef test_f():\n    assert f() == 1\n"
    )
    return tmp_path, case_id, case_dir


def test_memory_json_written_after_pec_loop(simple_case):
    """memory.json must exist on disk after run_case_with_pec completes."""
    cases_root, case_id, case_dir = simple_case
    model = _mock_model_bad_patch()

    result = run_case_with_pec(
        case_id=case_id,
        model=model,
        cases_root=str(cases_root),
        max_steps=2,
    )

    assert not result.resolved
    assert result.memory_path is not None
    assert os.path.exists(result.memory_path), "memory.json was not written to disk"


def test_memory_json_contains_edit_history(simple_case):
    """memory.json edit_history must have one entry per iteration."""
    cases_root, case_id, case_dir = simple_case
    model = _mock_model_bad_patch()
    max_steps = 3

    run_case_with_pec(
        case_id=case_id,
        model=model,
        cases_root=str(cases_root),
        max_steps=max_steps,
    )

    memory_path = case_dir / "memory.json"
    with open(memory_path) as f:
        data = json.load(f)

    assert "edit_history" in data
    assert len(data["edit_history"]) >= 1
    entry = data["edit_history"][0]
    assert "patch_plan" in entry
    assert "traceback" in entry
    assert entry["passed"] is False


def test_memory_json_contains_dead_end_registry(simple_case):
    """Dead-end patches must be recorded in dead_end_registry on disk."""
    cases_root, case_id, case_dir = simple_case
    model = _mock_model_bad_patch(fix="    return 0\n")

    run_case_with_pec(
        case_id=case_id,
        model=model,
        cases_root=str(cases_root),
        max_steps=2,
    )

    memory_path = case_dir / "memory.json"
    with open(memory_path) as f:
        data = json.load(f)

    assert len(data["dead_end_registry"]) >= 1


def test_memory_load_roundtrip(tmp_path):
    """Memory.load() must restore all state written by Memory.save()."""
    m = Memory()
    patch = {
        "file": "buggy.py",
        "line_range": [1, 3],
        "root_cause": "wrong return type",
        "proposed_fix": "return str(x)\n",
    }
    m.record_attempt(patch, traceback="AssertionError: expected int", passed=False)
    m.record_attempt(patch, traceback="AssertionError: expected int", passed=False)

    path = str(tmp_path / "memory.json")
    m.save(path)

    loaded = Memory.load(path)
    assert len(loaded.edit_history) == 2
    assert len(loaded.error_evolution) == 2
    assert loaded.is_dead_end(patch)
    assert loaded.edit_history[0]["iteration"] == 1
    assert loaded.edit_history[1]["iteration"] == 2


def test_memory_load_dead_end_blocks_retry(tmp_path):
    """A loaded Memory with a dead-end must report is_dead_end for that patch."""
    m = Memory()
    bad_patch = {
        "file": "buggy.py",
        "line_range": [2, 2],
        "root_cause": "typo",
        "proposed_fix": "return WRONG\n",
    }
    m.record_attempt(bad_patch, traceback="fail", passed=False)

    path = str(tmp_path / "memory.json")
    m.save(path)

    fresh = Memory.load(path)
    assert fresh.is_dead_end(bad_patch)

    good_patch = {
        "file": "buggy.py",
        "line_range": [2, 2],
        "root_cause": "different fix",
        "proposed_fix": "return CORRECT\n",
    }
    assert not fresh.is_dead_end(good_patch)
