import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from agent.critic import Critic
from agent.planner import Planner
from agent.tools_impl import make_benchmark_tools
from benchmark.manifest import BenchmarkCase
from benchmark.orchestrator import (
    BenchmarkExecutor,
    OrchestratorResult,
    PECOrchestrator,
)
from logger import Logger


def _normalize_model_name(model_name: str) -> str:
    aliases = {
        "gemm4": "gemma4",
    }
    key = model_name.strip().lower()
    return aliases.get(key, key)


def get_model(model_name: str):
    normalized = _normalize_model_name(model_name)
    if normalized == "gemini":
        from models.gemini import GeminiModel

        return GeminiModel()
    if normalized == "qwen":
        from models.qwen import QwenModel

        return QwenModel()
    if normalized == "minimax":
        from models.minimax import MiniMaxModel

        return MiniMaxModel()
    if normalized == "gemma4":
        from models.gemma4 import Gemma4Model

        # Benchmark runtime should always target local Ollama unless explicitly overridden.
        endpoint = os.getenv("BENCHMARK_OLLAMA_ENDPOINT", "http://127.0.0.1:11434")
        return Gemma4Model(endpoint=endpoint)
    raise ValueError(f"Unknown model: {model_name}")


@dataclass
class RuntimeResult:
    resolved: bool
    model_text: str
    target_test_exit_code: int
    regression_test_exit_code: Optional[int]
    target_test_output: str
    regression_test_output: str
    wall_time_ms: float
    failure_mode: str
    planner_stats: Dict[str, float]
    critic_verdict: str = "unknown"
    critic_attempts: List[Dict[str, object]] = None


def _classify_failure(
    target_exit: int,
    regression_exit: Optional[int],
    model_text: str,
    critic_verdict: str,
) -> str:
    if target_exit == 0 and (regression_exit in (None, 0)):
        return "none"
    if target_exit != 0 and ("RESOLVED" in model_text or "All tests pass" in model_text):
        return "false_resolved"
    if regression_exit not in (None, 0) and target_exit == 0:
        return "test_regression"
    if target_exit != 0:
        if critic_verdict == "unresolved":
            return "localization_failure"
        return "localization_failure"
    return "environment_error"


@contextmanager
def _pushd(path: str):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


@contextmanager
def _temporary_env(key: str, value: Optional[str]):
    previous = os.environ.get(key)
    if value is None:
        os.environ.pop(key, None)
    else:
        os.environ[key] = value
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = previous


class AgentRuntime:
    def __init__(
        self,
        max_steps: int,
        timeout_s: int,
        logger: Optional[Logger] = None,
        max_attempts: int = 1,
    ):
        self.max_steps = max_steps
        self.timeout_s = timeout_s
        self.logger = logger
        self.max_attempts = max(1, int(max_attempts))

    def _log(self, case_id: str, event: str, data: Dict[str, object]) -> None:
        if self.logger:
            self.logger.log(event=event, case_id=case_id, data=data)

    def run_case(self, case: BenchmarkCase, model_name: str, case_id: str) -> RuntimeResult:
        workspace_dir = case.metadata.get("workspace_dir")
        if not workspace_dir:
            raise ValueError("case.metadata.workspace_dir is required for runtime execution")
        if not Path(workspace_dir).exists():
            raise FileNotFoundError(f"workspace_dir does not exist: {workspace_dir}")

        base_objective = case.metadata.get(
            "objective",
            f"Investigate and fix bug in {case.target_file}.",
        )
        objective = (
            f"{base_objective}\n"
            f"Run `{case.test_command}` in `{workspace_dir}` and resolve deterministically.\n"
            "Use run_target_test for verification and run_regression_test before final resolution."
        )

        model = get_model(model_name)
        benchmark_tools = make_benchmark_tools(
            workspace_root=workspace_dir,
            target_test_command=case.test_command,
            regression_test_command=case.regression_test_command,
        )
        planner = Planner(
            model=model,
            max_steps=self.max_steps,
            logger=self.logger,
            case_id=case_id,
            tools=benchmark_tools,
        )

        executor = BenchmarkExecutor(workspace_dir=workspace_dir, timeout_s=self.timeout_s)
        critic = Critic(max_retries=self.max_attempts)
        orchestrator = PECOrchestrator(
            executor=executor,
            critic=critic,
            max_attempts=self.max_attempts,
            log_event=lambda event, data: self._log(case_id, event, data),
        )

        def planner_runner(current_objective: str) -> str:
            with _temporary_env("BENCHMARK_WORKSPACE_ROOT", workspace_dir):
                with _pushd(workspace_dir):
                    return planner.run_autonomous_loop(current_objective)

        start = time.monotonic()
        orch_result: OrchestratorResult = orchestrator.run(
            planner_runner=planner_runner,
            objective=objective,
            target_command=case.test_command,
            regression_command=case.regression_test_command,
        )
        wall_time_ms = (time.monotonic() - start) * 1000

        outcome = orch_result.last_outcome
        failure_mode = _classify_failure(
            outcome.target_exit_code,
            outcome.regression_exit_code,
            orch_result.last_planner_text,
            orch_result.final_verdict,
        )
        return RuntimeResult(
            resolved=outcome.passed,
            model_text=orch_result.last_planner_text,
            target_test_exit_code=outcome.target_exit_code,
            regression_test_exit_code=outcome.regression_exit_code,
            target_test_output=outcome.target_output,
            regression_test_output=outcome.regression_output,
            wall_time_ms=wall_time_ms,
            failure_mode=failure_mode,
            planner_stats=planner.session_stats(),
            critic_verdict=orch_result.final_verdict,
            critic_attempts=[
                {
                    "attempt": a.attempt,
                    "verdict": a.verdict,
                    "target_exit_code": a.target_exit_code,
                    "regression_exit_code": a.regression_exit_code,
                }
                for a in orch_result.attempts
            ],
        )
