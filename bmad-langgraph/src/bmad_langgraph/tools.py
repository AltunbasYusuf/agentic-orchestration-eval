"""Sandboxed coding tools for the ``build`` node's implement step.

BMAD's dev agent (Amelia) implements against a real checkout using whatever
tools the host IDE exposes (Claude Code's Read/Write/Bash, etc.). This graph
has no host IDE, so it gives Amelia her own small, explicitly scoped
toolbox instead: every path is resolved under ``{output_dir}/implementation/
workspace/`` and cannot escape it, and shell commands run with that
directory as cwd.

This is the one place in the port that touches a real filesystem/process on
the model's behalf -- keep the scope narrow rather than widening it to the
whole project tree.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from langchain_core.tools import tool


def _resolve(workspace: Path, relative_path: str) -> Path:
    target = (workspace / relative_path).resolve()
    if workspace.resolve() not in target.parents and target != workspace.resolve():
        raise ValueError(f"path escapes workspace: {relative_path}")
    return target


def make_coding_tools(workspace: Path) -> list:
    """Build the four tools bound to one workspace directory. Called fresh
    per ``build`` invocation rather than defined at import time, since the
    workspace path depends on ``state['output_dir']``."""

    @tool
    def write_file(relative_path: str, content: str) -> str:
        """Write (create or overwrite) a file inside the project workspace."""
        path = _resolve(workspace, relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"wrote {len(content)} bytes to {relative_path}"

    @tool
    def read_file(relative_path: str) -> str:
        """Read a file's contents from the project workspace."""
        path = _resolve(workspace, relative_path)
        if not path.exists():
            return f"(no such file: {relative_path})"
        return path.read_text(encoding="utf-8")

    @tool
    def list_files(relative_dir: str = ".") -> str:
        """List files under a directory in the project workspace."""
        path = _resolve(workspace, relative_dir)
        if not path.exists():
            return f"(no such directory: {relative_dir})"
        base = workspace.resolve()
        return "\n".join(sorted(str(p.relative_to(base)) for p in path.rglob("*") if p.is_file())) or "(empty)"

    @tool
    def run_command(command: str) -> str:
        """Run a shell command with the project workspace as the working
        directory (e.g. a test runner). 30s timeout, output truncated to 4000 chars."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = f"$ {command}\n[exit {result.returncode}]\n{result.stdout}\n{result.stderr}"
        except subprocess.TimeoutExpired:
            output = f"$ {command}\n[timed out after 30s]"
        return output[:4000]

    return [write_file, read_file, list_files, run_command]
