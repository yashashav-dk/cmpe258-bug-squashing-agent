import os
import subprocess
from typing import Dict, Any, Tuple

def read_file(filepath: str) -> str:
    """Read the contents of a file.
    
    Args:
        filepath: The path to the file to read.
    """
    if not os.path.exists(filepath):
        return f"Error: File {filepath} does not exist."
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
        result = subprocess.run(
            shlex.split(command),
            shell=False,
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=60,
        )
        out = ""
        if result.stdout:
            out += "STDOUT:\n" + result.stdout + "\n"
        if result.stderr:
            out += "STDERR:\n" + result.stderr + "\n"
        out += f"Exit Code: {result.returncode}"
        return out
    except Exception as e:
        return f"Error executing bash command: {e}"

# The list of tools exposed to the agent
AGENT_TOOLS = [read_file, edit_file, run_bash]
