import json
import os
from agent.memory import Memory


def make_patch(line_start=1, line_end=3, fix="return x\n"):
    return {
        "file": "buggy.py",
        "line_range": [line_start, line_end],
        "root_cause": "test",
        "proposed_fix": fix,
    }


def test_initial_state_is_empty():
    m = Memory()
    assert m.edit_history == []
    assert m.error_evolution == []
    assert len(m.dead_end_registry) == 0


def test_record_failed_attempt_adds_to_dead_end():
    m = Memory()
    patch = make_patch(fix="return str(x)\n")
    m.record_attempt(patch, traceback="AssertionError: ...", passed=False)
    assert m.is_dead_end(patch)


def test_record_passed_attempt_does_not_add_to_dead_end():
    m = Memory()
    patch = make_patch(fix="return x\n")
    m.record_attempt(patch, traceback="", passed=True)
    assert not m.is_dead_end(patch)


def test_whitespace_normalized_dead_end():
    m = Memory()
    patch1 = make_patch(fix="return str(x)\n")
    patch2 = make_patch(fix="  return str(x)  \n")
    m.record_attempt(patch1, traceback="err", passed=False)
    assert m.is_dead_end(patch2)


def test_get_summary_returns_string():
    m = Memory()
    patch = make_patch()
    m.record_attempt(patch, traceback="AssertionError", passed=False)
    summary = m.get_summary(max_tokens=500)
    assert isinstance(summary, str)
    assert "AssertionError" in summary


def test_get_summary_truncates_to_token_budget():
    m = Memory()
    for i in range(20):
        patch = make_patch(fix=f"return {i}\n")
        m.record_attempt(patch, traceback=f"error_{i}" * 50, passed=False)
    summary = m.get_summary(max_tokens=100)
    assert len(summary) < 800


def test_save_and_load(tmp_path):
    m = Memory()
    patch = make_patch()
    m.record_attempt(patch, traceback="err", passed=False)
    path = str(tmp_path / "memory.json")
    m.save(path)
    assert os.path.exists(path)
    with open(path) as f:
        data = json.load(f)
    assert len(data["edit_history"]) == 1
