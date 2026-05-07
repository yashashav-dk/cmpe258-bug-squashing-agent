import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from agent.critic import CaseResult, Critic
from agent.executor import Executor, PatchError
from agent.memory import Memory
from agent.planner import Planner
from logger import Logger
from models.base import BaseModel


@dataclass
class CaseRuntimeResult:
    resolved: bool
    summary_text: str
    final_traceback: str
    planner_stats: Dict[str, float]
    iterations: int
    timeline: List[str]
    memory_path: Optional[str] = None


def run_case_with_pec(
    *,
    case_id: str,
    model: BaseModel,
    cases_root: str,
    max_steps: int,
    logger: Optional[Logger] = None,
) -> CaseRuntimeResult:
    case_dir = Path(cases_root) / case_id
    buggy_path = case_dir / "buggy.py"
    if not case_dir.exists():
        raise FileNotFoundError(f"case directory not found: {case_dir}")
    if not buggy_path.exists():
        raise FileNotFoundError(f"buggy.py not found for case: {case_id}")

    planner = Planner(
        model=model,
        max_steps=max_steps,
        logger=logger,
        case_id=case_id,
    )
    executor = Executor(cases_root=cases_root)
    critic = Critic(max_retries=max_steps)
    memory = Memory()
    memory_path = str(case_dir / "memory.json")

    prev_cwd = os.getcwd()
    os.chdir(str(case_dir))
    try:
        passed, traceback = executor.run_tests(case_id=case_id)
        timeline: List[str] = []
        if passed:
            timeline.append("Preflight: target test already passing; no patch needed.")
            return CaseRuntimeResult(
                resolved=True,
                summary_text="Target test already passing before planner execution. RESOLVED",
                final_traceback="",
                planner_stats=planner.session_stats(),
                iterations=0,
                timeline=timeline,
            )

        retry_context = ""
        summary_text = ""
        timeline.append("Preflight: target test failing; entering Planner->Executor->Critic loop.")
        for iteration in range(1, max_steps + 1):
            buggy_code = buggy_path.read_text(encoding="utf-8")
            timeline.append(f"Iteration {iteration}: planner invoked.")
            try:
                patch_plan = planner.propose_patch_plan(
                    buggy_code=buggy_code,
                    traceback=traceback,
                    memory=memory,
                    retry_context=retry_context,
                    patch_file="buggy.py",
                )
                planned_file = str(patch_plan.get("file", "")).strip()
                if planned_file in ("", "."):
                    planned_file = "buggy.py"
                planned_path = case_dir / planned_file
                fallback_used = not planned_path.exists()
                patch_plan["file"] = planned_file if not fallback_used else "buggy.py"
                if fallback_used:
                    timeline.append(
                        f"Iteration {iteration}: planner proposed missing file '{planned_file}', fallback to 'buggy.py'."
                    )
                else:
                    timeline.append(
                        f"Iteration {iteration}: applying patch to '{patch_plan['file']}' lines {patch_plan['line_range']}."
                    )
                executor.apply_patch(patch_plan, case_id=case_id)
                passed, traceback = executor.run_tests(case_id=case_id)
                memory.record_attempt(
                    patch_plan=patch_plan,
                    traceback=traceback,
                    passed=passed,
                )
                memory.save(memory_path)
                verdict = critic.evaluate(
                    passed=passed,
                    traceback=traceback,
                    memory=memory,
                    iteration=iteration,
                )
                summary_text = f"Iteration {iteration}: applied patch plan for {patch_plan['file']}."
                if verdict == CaseResult.RESOLVED:
                    timeline.append(f"Iteration {iteration}: critic verdict=RESOLVED.")
                    summary_text += " RESOLVED"
                    return CaseRuntimeResult(
                        resolved=True,
                        summary_text=summary_text,
                        final_traceback=traceback,
                        planner_stats=planner.session_stats(),
                        iterations=iteration,
                        timeline=timeline,
                        memory_path=memory_path,
                    )
                if verdict == CaseResult.UNRESOLVED:
                    timeline.append(f"Iteration {iteration}: critic verdict=UNRESOLVED.")
                    summary_text += " UNRESOLVED"
                    break
                timeline.append(f"Iteration {iteration}: critic verdict=RETRY.")
                retry_context = critic.build_retry_context(traceback=traceback)
            except (json.JSONDecodeError, ValueError) as exc:
                traceback = str(exc)
                summary_text = f"Planner patch-plan parse failure: {exc}"
                timeline.append(f"Iteration {iteration}: planner parse/schema failure -> retry.")
                verdict = critic.evaluate(
                    passed=False,
                    traceback=traceback,
                    memory=memory,
                    iteration=iteration,
                )
                if verdict == CaseResult.UNRESOLVED:
                    break
                retry_context = critic.build_retry_context(
                    traceback=traceback,
                    is_json_error=True,
                )
            except PatchError as exc:
                traceback = str(exc)
                summary_text = f"Executor patch apply failure: {exc}"
                timeline.append(f"Iteration {iteration}: executor patch failure -> retry.")
                verdict = critic.evaluate(
                    passed=False,
                    traceback=traceback,
                    memory=memory,
                    iteration=iteration,
                )
                if verdict == CaseResult.UNRESOLVED:
                    break
                retry_context = critic.build_retry_context(
                    traceback=traceback,
                    is_schema_error=True,
                )

        return CaseRuntimeResult(
            resolved=False,
            summary_text=summary_text or "Max retries reached without resolution.",
            final_traceback=traceback,
            planner_stats=planner.session_stats(),
            iterations=max_steps,
            timeline=timeline,
            memory_path=memory_path,
        )
    finally:
        os.chdir(prev_cwd)
