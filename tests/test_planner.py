import json
from unittest.mock import MagicMock
from agent.planner import Planner
from agent.memory import Memory
from models.base import BaseModel, ModelResponse


def make_mock_model(response_text: str) -> BaseModel:
    model = MagicMock(spec=BaseModel)
    model.complete.return_value = ModelResponse(
        text=response_text,
        input_tokens=100,
        output_tokens=50,
        latency_ms=500.0,
    )
    model.name.return_value = "mock-model"
    return model


VALID_PATCH = json.dumps({
    "file": "buggy.py",
    "line_range": [1, 3],
    "root_cause": "wrong operator",
    "proposed_fix": "def f(x):\n    return x\n",
})


def test_planner_returns_valid_patch():
    model = make_mock_model(VALID_PATCH)
    planner = Planner(model=model, few_shot_dir="dataset/few_shot")
    memory = Memory()
    result = planner.plan(
        buggy_code="def f(x):\n    return -x\n",
        traceback="AssertionError: assert f(1) == 1",
        memory=memory,
    )
    assert result["file"] == "buggy.py"
    assert result["line_range"] == [1, 3]
    assert "proposed_fix" in result
    assert "root_cause" in result


def test_planner_raises_on_invalid_json():
    model = make_mock_model("not json at all")
    planner = Planner(model=model, few_shot_dir="dataset/few_shot")
    memory = Memory()
    try:
        planner.plan(
            buggy_code="def f(x): pass",
            traceback="error",
            memory=memory,
        )
        assert False, "Should have raised"
    except ValueError as e:
        assert "JSON" in str(e)


def test_planner_raises_on_missing_fields():
    bad_patch = json.dumps({"file": "buggy.py"})
    model = make_mock_model(bad_patch)
    planner = Planner(model=model, few_shot_dir="dataset/few_shot")
    memory = Memory()
    try:
        planner.plan(
            buggy_code="def f(x): pass",
            traceback="error",
            memory=memory,
        )
        assert False, "Should have raised"
    except ValueError as e:
        assert "schema" in str(e).lower()


def test_planner_prompt_includes_buggy_code():
    model = make_mock_model(VALID_PATCH)
    planner = Planner(model=model, few_shot_dir="dataset/few_shot")
    memory = Memory()
    planner.plan(
        buggy_code="def my_unique_fn(): pass",
        traceback="some error",
        memory=memory,
    )
    call_args = model.complete.call_args[0][0]
    assert "my_unique_fn" in call_args
