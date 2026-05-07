import json
import os
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from agent.critic import CaseResult, Critic
from agent.executor import Executor, PatchError
from agent.memory import Memory
from agent.planner import Planner
from agent.tools_impl import make_benchmark_tools
from benchmark.manifest import BenchmarkCase
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
    if normalized in ("gemma4", "gemma3", "gemma3_4b"):
        from models.openrouter import OpenRouterModel, OPENROUTER_MODELS

        return OpenRouterModel(OPENROUTER_MODELS[normalized])
    if normalized in ("gemini_or", "qwen_or"):
        from models.openrouter import OpenRouterModel, OPENROUTER_MODELS

        return OpenRouterModel(OPENROUTER_MODELS[normalized])
    if normalized in ("gemini3flash", "gemini3pro"):
        from models.gemini import GeminiModel

        model_map = {
            "gemini3flash": "gemini-3-flash-preview",
            "gemini3pro": "gemini-3-pro-preview",
        }
        return GeminiModel(model_name=model_map[normalized])
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


def _run_command(command: str, cwd: str, timeout_s: int) -> subprocess.CompletedProcess:
    return subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout_s,
    )


def _classify_failure(target_exit: int, regression_exit: Optional[int], model_text: str) -> str:
    if target_exit == 0 and (regression_exit in (None, 0)):
        return "none"
    if target_exit != 0 and ("RESOLVED" in model_text or "All tests pass" in model_text):
        return "false_resolved"
    if target_exit != 0:
        return "localization_failure"
    if regression_exit not in (None, 0):
        return "test_regression"
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
    def __init__(self, max_steps: int, timeout_s: int, logger: Optional[Logger] = None):
        self.max_steps = max_steps
        self.timeout_s = timeout_s
        self.logger = logger

    def run_case(
        self,
        case: BenchmarkCase,
        model_name: str,
        case_id: str,
        *,
        workspace_root: Optional[str] = None,
    ) -> RuntimeResult:
        workspace_dir = workspace_root or case.metadata.get("workspace_dir")
        if not workspace_dir:
            raise ValueError(
                "workspace_dir required: set case.metadata['workspace_dir'] or pass workspace_root="
            )
        workspace_root = Path(workspace_dir).resolve()
        if not workspace_root.exists():
            raise FileNotFoundError(f"workspace_dir does not exist: {workspace_dir}")
        # Absolute path required: `_pushd` changes cwd while loop uses Path(workspace_dir) / target_file.
        workspace_dir = str(workspace_root)

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
        executor = Executor(cases_root=workspace_dir)
        critic = Critic(max_retries=self.max_steps)
        memory = Memory()
        start = time.monotonic()
        model_text = ""
        target = _run_command(case.test_command, cwd=workspace_dir, timeout_s=self.timeout_s)
        latest_traceback = target.stdout + target.stderr
        retry_context = ""
        if target.returncode == 0:
            model_text = "Target test already passing before planner execution. RESOLVED"

        if target.returncode != 0:
            # Enforce case workspace as process cwd so tool paths resolve to the target repo.
            with _temporary_env("BENCHMARK_WORKSPACE_ROOT", workspace_dir):
                with _pushd(workspace_dir):
                    for iteration in range(1, self.max_steps + 1):
                        target_file_path = Path(workspace_dir) / case.target_file
                        if not target_file_path.exists():
                            raise FileNotFoundError(
                                f"target_file does not exist in workspace: {target_file_path}"
                            )
                        buggy_code = target_file_path.read_text(encoding="utf-8")

                        try:
                            patch_plan = planner.propose_patch_plan(
                                buggy_code=buggy_code,
                                traceback=latest_traceback,
                                memory=memory,
                                retry_context=retry_context,
                                patch_file=case.target_file,
                            )
                            planned_file = str(patch_plan.get("file", "")).strip()
                            if planned_file in ("", "."):
                                planned_file = case.target_file
                            if planned_file == "buggy.py" and case.target_file != "buggy.py":
                                planned_file = case.target_file
                            planned_path = Path(workspace_dir) / planned_file
                            patch_plan["file"] = planned_file if planned_path.exists() else case.target_file
                            executor.apply_patch(patch_plan, case_id="")
                            target = _run_command(case.test_command, cwd=workspace_dir, timeout_s=self.timeout_s)
                            latest_traceback = target.stdout + target.stderr
                            passed = target.returncode == 0
                            memory.record_attempt(
                                patch_plan=patch_plan,
                                traceback=latest_traceback,
                                passed=passed,
                            )
                            verdict = critic.evaluate(
                                passed=passed,
                                traceback=latest_traceback,
                                memory=memory,
                                iteration=iteration,
                            )
                            model_text = (
                                f"Iteration {iteration}: applied patch plan for {patch_plan['file']}."
                            )
                            if verdict == CaseResult.RESOLVED:
                                model_text += " RESOLVED"
                                break
                            if verdict == CaseResult.UNRESOLVED:
                                model_text += " UNRESOLVED"
                                break
                            retry_context = critic.build_retry_context(traceback=latest_traceback)
                        except (json.JSONDecodeError, ValueError) as exc:
                            latest_traceback = str(exc)
                            retry_context = critic.build_retry_context(
                                traceback=latest_traceback,
                                is_json_error=True,
                            )
                            model_text = f"Planner patch-plan parse failure: {exc}"
                            verdict = critic.evaluate(
                                passed=False,
                                traceback=latest_traceback,
                                memory=memory,
                                iteration=iteration,
                            )
                            if verdict == CaseResult.UNRESOLVED:
                                break
                        except PatchError as exc:
                            latest_traceback = str(exc)
                            retry_context = critic.build_retry_context(
                                traceback=latest_traceback,
                                is_schema_error=True,
                            )
                            model_text = f"Executor patch apply failure: {exc}"
                            verdict = critic.evaluate(
                                passed=False,
                                traceback=latest_traceback,
                                memory=memory,
                                iteration=iteration,
                            )
                            if verdict == CaseResult.UNRESOLVED:
                                break

        regression_exit: Optional[int] = None
        regression_output = ""

        if case.regression_test_command:
            regression = _run_command(case.regression_test_command, cwd=workspace_dir, timeout_s=self.timeout_s)
            regression_exit = regression.returncode
            regression_output = regression.stdout + regression.stderr

        wall_time_ms = (time.monotonic() - start) * 1000
        failure_mode = _classify_failure(target.returncode, regression_exit, model_text)
        resolved = target.returncode == 0 and (regression_exit in (None, 0))

        return RuntimeResult(
            resolved=resolved,
            model_text=model_text,
            target_test_exit_code=target.returncode,
            regression_test_exit_code=regression_exit,
            target_test_output=target.stdout + target.stderr,
            regression_test_output=regression_output,
            wall_time_ms=wall_time_ms,
            failure_mode=failure_mode,
            planner_stats=planner.session_stats(),
        )
