from enum import Enum
from agent.memory import Memory


class CaseResult(Enum):
    RESOLVED = "resolved"
    RETRY = "retry"
    UNRESOLVED = "unresolved"


class Critic:
    def __init__(self, max_retries: int):
        self.max_retries = max_retries

    def evaluate(
        self,
        passed: bool,
        traceback: str,
        memory: Memory,
        iteration: int,
    ) -> CaseResult:
        if passed:
            return CaseResult.RESOLVED
        if iteration >= self.max_retries:
            return CaseResult.UNRESOLVED
        return CaseResult.RETRY

    def build_retry_context(
        self,
        traceback: str,
        is_json_error: bool = False,
        is_schema_error: bool = False,
    ) -> str:
        """Build a short context string to append to the next Planner prompt."""
        if is_json_error:
            return (
                f"IMPORTANT: Your previous response was not valid JSON. "
                f"You MUST respond with only a raw JSON object.\n"
                f"Error: {traceback}"
            )
        if is_schema_error:
            return (
                f"IMPORTANT: Your previous response failed schema validation. "
                f"Ensure all required fields are present: file, line_range, root_cause, proposed_fix.\n"
                f"Error: {traceback}"
            )
        return f"The previous patch did not fix the bug. New traceback:\n{traceback}"
