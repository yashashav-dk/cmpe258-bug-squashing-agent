#!/usr/bin/env python3
"""
main.py — Run one full Planner→Executor→Critic agent loop on a single bug case.

Usage:
    python3 main.py --case case_001 [--model gemini]
"""
import argparse
import os
import sys

from config import MAX_RETRIES, CASES_DIR, FEW_SHOT_DIR, LOG_PATH
from logger import Logger
from agent.memory import Memory
from agent.planner import Planner
from agent.executor import Executor, PatchError
from agent.critic import Critic, CaseResult


def get_model(model_name: str):
    if model_name == "gemini":
        from models.gemini import GeminiModel
        return GeminiModel()
    elif model_name == "qwen":
        from models.qwen import QwenModel
        return QwenModel()
    elif model_name == "minimax":
        from models.minimax import MiniMaxModel
        return MiniMaxModel()
    else:
        raise ValueError(f"Unknown model: {model_name!r}. Choose from: gemini, qwen, minimax")


def run_case(case_id: str, model_name: str) -> CaseResult:
    logger = Logger(LOG_PATH)
    memory = Memory()
    model = get_model(model_name)
    planner = Planner(model=model, few_shot_dir=FEW_SHOT_DIR)
    executor = Executor(cases_root=CASES_DIR)
    critic = Critic(max_retries=MAX_RETRIES)

    case_dir = os.path.join(CASES_DIR, case_id)
    buggy_path = os.path.join(case_dir, "buggy.py")

    if not os.path.isdir(case_dir):
        print(f"Error: case directory not found: {case_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"\n{'='*60}")
    print(f"Case: {case_id} | Model: {model.name()}")
    print(f"{'='*60}")

    # Initial pytest run
    passed, traceback = executor.run_tests(case_id=case_id)
    if passed:
        print("Tests already passing — nothing to fix.")
        return CaseResult.RESOLVED

    result = CaseResult.RETRY
    for iteration in range(1, MAX_RETRIES + 1):
        print(f"\n[Iteration {iteration}/{MAX_RETRIES}]")
        with open(buggy_path) as f:
            buggy_code = f.read()

        # Planner
        is_json_error = is_schema_error = False
        try:
            patch = planner.plan(buggy_code=buggy_code, traceback=traceback, memory=memory)
        except ValueError as e:
            err = str(e)
            is_json_error = "JSON" in err
            is_schema_error = "schema" in err.lower()
            retry_ctx = critic.build_retry_context(
                traceback=err, is_json_error=is_json_error, is_schema_error=is_schema_error
            )
            print(f"  Planner error: {err[:100]}")
            logger.log("planner_error", case_id, {"iteration": iteration, "error": err})
            memory.record_attempt(
                {"file": "buggy.py", "line_range": [0, 0], "root_cause": err, "proposed_fix": ""},
                traceback=err, passed=False,
            )
            result = critic.evaluate(passed=False, traceback=err, memory=memory, iteration=iteration)
            if result != CaseResult.RETRY:
                break
            traceback = retry_ctx
            continue

        if memory.is_dead_end(patch):
            print(f"  Dead end detected — skipping duplicate patch")
            result = critic.evaluate(passed=False, traceback="dead end", memory=memory, iteration=iteration)
            if result != CaseResult.RETRY:
                break
            continue

        print(f"  Root cause: {patch['root_cause']}")
        print(f"  Patching lines {patch['line_range']}...")

        # Executor
        try:
            executor.apply_patch(patch, case_id=case_id)
        except PatchError as e:
            print(f"  Patch failed: {e}")
            logger.log("patch_error", case_id, {"iteration": iteration, "error": str(e)})
            memory.record_attempt(patch, traceback=str(e), passed=False)
            result = critic.evaluate(passed=False, traceback=str(e), memory=memory, iteration=iteration)
            if result != CaseResult.RETRY:
                break
            continue

        passed, traceback = executor.run_tests(case_id=case_id)
        logger.log("iteration", case_id, {
            "iteration": iteration,
            "model": model.name(),
            "patch": patch,
            "passed": passed,
            "traceback": traceback[:500],
        })
        memory.record_attempt(patch, traceback=traceback, passed=passed)

        result = critic.evaluate(passed=passed, traceback=traceback, memory=memory, iteration=iteration)
        status = "PASS ✓" if passed else "FAIL ✗"
        print(f"  Result: {status}")

        if result != CaseResult.RETRY:
            break

    memory.save(os.path.join(case_dir, "memory.json"))

    print(f"\nFinal result: {result.value.upper()}")
    logger.log("final", case_id, {"result": result.value, "model": model.name()})
    return result


def main():
    parser = argparse.ArgumentParser(description="Bug Squashing Agent")
    parser.add_argument("--case", required=True, help="Case ID (e.g. case_001)")
    parser.add_argument("--model", default="gemini", choices=["gemini", "qwen", "minimax"])
    args = parser.parse_args()
    run_case(case_id=args.case, model_name=args.model)


if __name__ == "__main__":
    main()
