import pytest

from buggy import evaluate


def test_recent_high_priority_title_normalization_and_scoring():
    payload = {"title": "  AEon  ", "priority": "HIGH", "age_days": 2}
    assert evaluate(payload) == 37


def test_stale_medium_priority_penalty_applied():
    payload = {"title": "orbit", "priority": "medium", "age_days": 30}
    assert evaluate(payload) == 22


def test_invalid_priority_rejected():
    with pytest.raises(ValueError):
        evaluate({"title": "ok", "priority": "urgent", "age_days": 1})
