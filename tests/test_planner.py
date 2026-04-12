from unittest.mock import MagicMock
from agent.planner import Planner
from agent.memory import Memory
from models.base import BaseModel, ModelResponse

def make_mock_model(response_text: str, tool_calls=None) -> BaseModel:
    model = MagicMock(spec=BaseModel)
    model.chat.return_value = ModelResponse(
        text=response_text,
        input_tokens=100,
        output_tokens=50,
        latency_ms=500.0,
        tool_calls=tool_calls
    )
    model.name.return_value = "mock-model"
    return model

def test_planner_returns_valid_patch_legacy():
    model = make_mock_model("RESOLVED")
    planner = Planner(model=model, few_shot_dir="dataset/few_shot")
    memory = Memory()
    
    result = planner.plan(
        buggy_code="def f(x):\n    return -x\n",
        traceback="AssertionError: assert f(1) == 1",
        memory=memory,
    )
    
    # legacy compatibility check
    assert result["file"] == "buggy.py"
    assert "proposed_fix" in result
    assert "root_cause" in result

def test_autonomous_loop_resolves():
    model = make_mock_model("I have fixed the issue. RESOLVED")
    planner = Planner(model=model, max_steps=2)
    
    output = planner.run_autonomous_loop("Fix this bug.")
    assert "RESOLVED" in output
    assert len(planner.history) > 1

def test_autonomous_loop_tool_calls():
    # Model returns a tool call
    model = make_mock_model("", tool_calls=[{"name": "read_file", "arguments": {"filepath": "buggy.py"}}])
    planner = Planner(model=model, max_steps=1)
    
    output = planner.run_autonomous_loop("Fix this bug.")
    
    # Needs at least one tool call sent
    model.chat.assert_called()
    assert "Max steps reached" in output # Because max_steps 1 limits the resolution

