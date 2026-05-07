import ast
import os
import subprocess
import sys


class PatchError(Exception):
    pass


class Executor:
    def __init__(self, cases_root: str):
        self.cases_root = os.path.realpath(cases_root)

    def _case_dir(self, case_id: str) -> str:
        return os.path.join(self.cases_root, case_id)

    def _validate_scope(self, file_path: str, case_id: str) -> str:
        """Return realpath of target file after validating it is within allowed scope."""
        allowed_root = os.path.realpath(self._case_dir(case_id))
        target = os.path.realpath(os.path.join(allowed_root, file_path))
        if not target.startswith(allowed_root + os.sep) and target != allowed_root:
            raise PatchError(f"Scope violation: {file_path!r} resolves outside case directory")
        return target

    def apply_patch(self, patch: dict, case_id: str) -> None:
        """Atomically apply a patch to buggy.py."""
        target_path = self._validate_scope(patch["file"], case_id)
        start, end = patch["line_range"]  # 1-indexed, inclusive

        if not os.path.exists(target_path):
            raise PatchError(f"Target file not found for patch: {patch['file']}")

        try:
            with open(target_path) as f:
                lines = f.readlines()
        except OSError as e:
            raise PatchError(f"Failed reading target file {patch['file']!r}: {e}")

        new_lines = lines[: start - 1] + [patch["proposed_fix"]] + lines[end:]
        new_content = "".join(new_lines)

        # Validate syntax before writing
        try:
            ast.parse(new_content)
        except SyntaxError as e:
            raise PatchError(f"Patch produces invalid Python: {e}")

        # Atomic write: write to .tmp then rename
        tmp_path = target_path + ".tmp"
        try:
            with open(tmp_path, "w") as f:
                f.write(new_content)
            os.replace(tmp_path, target_path)
        except OSError as e:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
            raise PatchError(f"File I/O error during atomic write: {e}")

    def run_tests(self, case_id: str) -> tuple:
        """Run pytest on the case. Returns (passed, traceback_string)."""
        case_dir = self._case_dir(case_id)
        test_file = os.path.join(case_dir, "test_buggy.py")
        result = subprocess.run(
            [sys.executable, "-m", "pytest", test_file, "-v", "--tb=short"],
            shell=False,
            capture_output=True,
            text=True,
            cwd=case_dir,
        )
        passed = result.returncode == 0
        traceback = result.stdout + result.stderr if not passed else ""
        return passed, traceback
