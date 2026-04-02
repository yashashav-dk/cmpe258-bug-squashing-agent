from agent.critic import Critic, CaseResult
from agent.memory import Memory


def test_critic_resolves_on_pass():
    critic = Critic(max_retries=3)
    memory = Memory()
    result = critic.evaluate(passed=True, traceback="", memory=memory, iteration=1)
    assert result == CaseResult.RESOLVED


def test_critic_retries_on_fail_within_limit():
    critic = Critic(max_retries=3)
    memory = Memory()
    patch = {"file": "buggy.py", "line_range": [1, 2], "root_cause": "x", "proposed_fix": "y\n"}
    memory.record_attempt(patch, "error", passed=False)
    result = critic.evaluate(passed=False, traceback="error", memory=memory, iteration=1)
    assert result == CaseResult.RETRY


def test_critic_gives_up_at_max_retries():
    critic = Critic(max_retries=3)
    memory = Memory()
    result = critic.evaluate(passed=False, traceback="still failing", memory=memory, iteration=3)
    assert result == CaseResult.UNRESOLVED


def test_critic_includes_json_hint_on_parse_error():
    critic = Critic(max_retries=5)
    memory = Memory()
    summary = critic.build_retry_context(traceback="not json", is_json_error=True)
    assert "JSON" in summary


def test_critic_includes_schema_hint_on_schema_error():
    critic = Critic(max_retries=5)
    memory = Memory()
    summary = critic.build_retry_context(traceback="schema fail", is_schema_error=True)
    assert "schema" in summary.lower()
