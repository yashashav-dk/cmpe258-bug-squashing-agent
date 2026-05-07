"""
Planner -> Executor -> Critic orchestration for the benchmark runtime.

The Planner runs an autonomous tool-loop that may apply patches in-place. After
the Planner returns, the Executor independently re-runs the deterministic
target test (and optional regression test) to obtain ground-truth pass/fail.
The Critic then emits an explicit RESOLVED / RETRY / UNRESOLVED verdict per
attempt. When the Critic returns RETRY and budget remains, the orchestrator
augments the next attempt's objective with retry context built by the Critic.
"""
import shlex
import subprocess
import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Tuple

from agent.critic import CaseResult, Critic
from agent.memory import Memory


@dataclass
class ExecutorOutcome:
    passed: bool
    target_exit_code: int
    target_output: str
    regression_exit_code: Optional[int]
    regression_output: str


@dataclass
class AttemptRecord:
    attempt: int
    verdict: str
    target_exit_code: int
    regression_exit_code: Optional[int]
    planner_text: str


@dataclass
class OrchestratorResult:
    final_verdict: str
    last_outcome: ExecutorOutcome
    attempts: List[AttemptRecord] = field(default_factory=list)
    last_planner_text: str = ""


def _split_command(command: str) -> List[str]:
    return shlex.split(command, posix=True)


class BenchmarkExecutor:
    """Runs target / regression test commands with shell=False where possible.

    Falls back to shell execution only if shlex.split cannot tokenize the
    command, preserving operability for legacy compound commands.
    """

    def __init__(self, workspace_dir: str, timeout_s: int):
        self.workspace_dir = workspace_dir
        self.timeout_s = timeout_s

    def _run(self, command: str) -> subprocess.CompletedProcess:
        try:
            argv = _split_command(command)
        except ValueError:
            argv = None
        if argv:
            return subprocess.run(
                argv,
                shell=False,
                capture_output=True,
                text=True,
                cwd=self.workspace_dir,
                timeout=self.timeout_s,
            )
        return subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            cwd=self.workspace_dir,
            timeout=self.timeout_s,
        )

    def verify(self, target_command: str, regression_command: Optional[str]) -> ExecutorOutcome:
        target = self._run(target_command)
        regression_exit: Optional[int] = None
        regression_output = ""
        if regression_command:
            regression = self._run(regression_command)
            regression_exit = regression.returncode
            regression_output = regression.stdout + regression.stderr
        passed = target.returncode == 0 and (regression_exit in (None, 0))
        return ExecutorOutcome(
            passed=passed,
            target_exit_code=target.returncode,
            target_output=target.stdout + target.stderr,
            regression_exit_code=regression_exit,
            regression_output=regression_output,
        )


class PECOrchestrator:
    """Drives Planner -> Executor -> Critic with explicit state transitions.

    The Planner is invoked as a tool-loop sub-routine. The Executor and Critic
    are first-class roles owning verification and retry decisions respectively.
    """

    def __init__(
        self,
        executor: BenchmarkExecutor,
        critic: Critic,
        max_attempts: int = 1,
        log_event: Optional[Callable[[str, dict], None]] = None,
    ):
        self.executor = executor
        self.critic = critic
        self.max_attempts = max(1, int(max_attempts))
        self._log_event = log_event or (lambda event, data: None)

    def run(
        self,
        planner_runner: Callable[[str], str],
        objective: str,
        target_command: str,
        regression_command: Optional[str],
    ) -> OrchestratorResult:
        memory = Memory()
        attempts: List[AttemptRecord] = []
        last_text = ""
        last_outcome: Optional[ExecutorOutcome] = None
        current_objective = objective

        for attempt in range(1, self.max_attempts + 1):
            self._log_event("pec_attempt_start", {"attempt": attempt, "max_attempts": self.max_attempts})
            last_text = planner_runner(current_objective)
            outcome = self.executor.verify(target_command, regression_command)
            verdict = self.critic.evaluate(
                passed=outcome.passed,
                traceback=outcome.target_output,
                memory=memory,
                iteration=attempt,
            )
            attempts.append(
                AttemptRecord(
                    attempt=attempt,
                    verdict=verdict.value,
                    target_exit_code=outcome.target_exit_code,
                    regression_exit_code=outcome.regression_exit_code,
                    planner_text=last_text,
                )
            )
            self._log_event(
                "pec_attempt_end",
                {
                    "attempt": attempt,
                    "verdict": verdict.value,
                    "target_exit_code": outcome.target_exit_code,
                    "regression_exit_code": outcome.regression_exit_code,
                },
            )
            last_outcome = outcome
            if verdict == CaseResult.RESOLVED or verdict == CaseResult.UNRESOLVED:
                break
            retry_context = self.critic.build_retry_context(traceback=outcome.target_output)
            current_objective = f"{objective}\n\n{retry_context}"

        assert last_outcome is not None
        final = attempts[-1].verdict if attempts else CaseResult.UNRESOLVED.value
        return OrchestratorResult(
            final_verdict=final,
            last_outcome=last_outcome,
            attempts=attempts,
            last_planner_text=last_text,
        )
