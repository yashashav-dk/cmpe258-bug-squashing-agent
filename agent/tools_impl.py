import os
from pathlib import Path
import subprocess
from typing import Callable, List, Optional, Tuple

def read_file(filepath: str) -> str:
    """Read the contents of a file.
    
    Args:
        filepath: The path to the file to read.
    """
    if not os.path.exists(filepath):
        return f"Error: File {filepath} does not exist."
    if os.path.isdir(filepath):
        return f"Error: {filepath} is a directory. Use run_bash with `ls -F {filepath}` to inspect directory contents."
    try:
        with open(filepath, "r") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

def edit_file(filepath: str, old_content: str, new_content: str) -> str:
    """Replace content in a file. Must provide the exact old_content to be replaced.
    
    Args:
        filepath: The path to the file to edit.
        old_content: The exact string block to replace.
        new_content: The new text block to insert.
    """
    if not os.path.exists(filepath):
        return f"Error: File {filepath} does not exist."
    try:
        with open(filepath, "r") as f:
            content = f.read()
        if old_content not in content:
            # Idempotency guard: if new content already exists, treat as success.
            if new_content in content:
                return "No-op: requested new_content is already present. File already updated."
            return "Error: old_content not found in the file. Ensure you pass the exact string including whitespace."
        content = content.replace(old_content, new_content)
        with open(filepath, "w") as f:
            f.write(content)
        return "File updated successfully."
    except Exception as e:
        return f"Error editing file: {e}"

def run_bash(command: str, cwd: str = ".") -> str:
    """Run a bash command and get the output. Use this to run pytest.
    
    Args:
        command: The bash command to run (e.g., 'pytest test_buggy.py')
        cwd: Current working directory optionally.
    """
    import shlex
    try:
        workspace_root = os.getenv("BENCHMARK_WORKSPACE_ROOT", "").strip()
        if workspace_root:
            resolved_cwd, cwd_error = _resolve_scoped_cwd(workspace_root=workspace_root, cwd=cwd)
            if cwd_error:
                return cwd_error
            cwd = resolved_cwd
        result = subprocess.run(
            shlex.split(command),
            shell=False,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=60,
        )
        return _format_command_output(result)
    except Exception as e:
        return f"Error executing bash command: {e}"


def _format_command_output(result: subprocess.CompletedProcess) -> str:
    out = ""
    if result.stdout:
        out += "STDOUT:\n" + result.stdout + "\n"
    if result.stderr:
        out += "STDERR:\n" + result.stderr + "\n"
    out += f"Exit Code: {result.returncode}"
    return out


def _resolve_scoped_cwd(workspace_root: str, cwd: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    try:
        root = Path(workspace_root).resolve()
    except Exception as e:
        return None, f"Error: invalid workspace_root: {e}"
    if not root.exists() or not root.is_dir():
        return None, f"Error: workspace_root does not exist: {workspace_root}"

    requested = (cwd or ".").strip() or "."
    requested_path = Path(requested)
    is_relative = not requested_path.is_absolute()

    # Reject nested relative attempts that re-anchor from a scoped case workspace.
    if is_relative:
        normalized = requested_path.as_posix().lstrip("./")
        if normalized.startswith("dataset/cases/"):
            return None, (
                "Error: invalid cwd for scoped workspace. "
                "Do not pass nested dataset/cases paths when already scoped to a case workspace."
            )

    candidate = (root / requested_path).resolve() if is_relative else requested_path.resolve()
    if candidate != root and root not in candidate.parents:
        return None, (
            "Error: invalid cwd outside scoped workspace. "
            f"workspace_root={root}, cwd={requested}, resolved={candidate}"
        )
    if not candidate.exists() or not candidate.is_dir():
        return None, f"Error: cwd does not exist or is not a directory: {candidate}"
    return str(candidate), None


def _resolve_scoped_file(workspace_root: str, filepath: str) -> Tuple[Optional[str], Optional[str]]:
    try:
        root = Path(workspace_root).resolve()
    except Exception as e:
        return None, f"Error: invalid workspace_root: {e}"
    requested = Path(filepath)
    candidate = (root / requested).resolve() if not requested.is_absolute() else requested.resolve()
    if candidate != root and root not in candidate.parents:
        return None, (
            "Error: file path outside scoped workspace. "
            f"workspace_root={root}, filepath={filepath}, resolved={candidate}"
        )
    return str(candidate), None


def make_benchmark_tools(
    workspace_root: str,
    target_test_command: str,
    regression_test_command: Optional[str] = None,
) -> List[Callable]:
    workspace_root = str(Path(workspace_root).resolve())

    def read_file(filepath: str) -> str:
        """Read a file within the scoped benchmark workspace."""
        resolved, path_error = _resolve_scoped_file(workspace_root=workspace_root, filepath=filepath)
        if path_error:
            return path_error
        if not os.path.exists(resolved):
            return f"Error: File {filepath} does not exist."
        if os.path.isdir(resolved):
            return f"Error: {filepath} is a directory. Use list_dir to inspect directory contents."
        try:
            with open(resolved, "r") as f:
                return f.read()
        except Exception as e:
            return f"Error reading file: {e}"

    def edit_file(filepath: str, old_content: str, new_content: str) -> str:
        """Replace exact content in a file within the scoped benchmark workspace."""
        resolved, path_error = _resolve_scoped_file(workspace_root=workspace_root, filepath=filepath)
        if path_error:
            return path_error
        if not os.path.exists(resolved):
            return f"Error: File {filepath} does not exist."
        try:
            with open(resolved, "r") as f:
                content = f.read()
            if old_content not in content:
                if new_content in content:
                    return "No-op: requested new_content is already present. File already updated."
                return "Error: old_content not found in the file. Ensure you pass the exact string including whitespace."
            content = content.replace(old_content, new_content)
            with open(resolved, "w") as f:
                f.write(content)
            return "File updated successfully."
        except Exception as e:
            return f"Error editing file: {e}"

    def list_dir(path: str = ".") -> str:
        """List directory entries under the scoped benchmark workspace."""
        resolved_cwd, cwd_error = _resolve_scoped_cwd(workspace_root=workspace_root, cwd=path)
        if cwd_error:
            return cwd_error
        try:
            entries = sorted(os.listdir(resolved_cwd))
            if not entries:
                return f"Directory is empty: {path}"
            return "\n".join(entries)
        except Exception as e:
            return f"Error listing directory: {e}"

    def run_target_test() -> str:
        """Run the benchmark target test command in the scoped workspace."""
        try:
            result = subprocess.run(
                target_test_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=workspace_root,
            )
            return _format_command_output(result)
        except Exception as e:
            return f"Error executing target test: {e}"

    def run_regression_test() -> str:
        """Run the benchmark regression test command in the scoped workspace."""
        if not regression_test_command:
            return "STDOUT:\nNo regression test configured.\nExit Code: 0"
        try:
            result = subprocess.run(
                regression_test_command,
                shell=True,
                capture_output=True,
                text=True,
                cwd=workspace_root,
            )
            return _format_command_output(result)
        except Exception as e:
            return f"Error executing regression test: {e}"

    return [read_file, edit_file, run_target_test, run_regression_test, list_dir]


# The list of tools exposed to the agent
AGENT_TOOLS = [read_file, edit_file, run_bash]
