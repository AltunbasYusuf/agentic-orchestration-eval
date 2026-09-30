"""Filesystem layout and small render helpers.

Mirrors BMAD's ``{planning_artifacts}`` / ``{implementation_artifacts}``
split (see ``docs/cs/reference/workflow-map.md`` in the source repo):

    {output_dir}/
      planning/        PRD, UX, architecture spine, epics, sprint-status.yaml
      implementation/  specs, retros, sprint-change-proposals, workspace/

``workspace/`` under ``implementation/`` is where the build node's coding
tools (see ``tools.py``) are sandboxed to read and write.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml


def planning_dir(output_dir: str) -> Path:
    p = Path(output_dir) / "planning"
    p.mkdir(parents=True, exist_ok=True)
    return p


def implementation_dir(output_dir: str) -> Path:
    p = Path(output_dir) / "implementation"
    p.mkdir(parents=True, exist_ok=True)
    return p


def workspace_dir(output_dir: str) -> Path:
    p = implementation_dir(output_dir) / "workspace"
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_markdown(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def write_yaml(path: Path, data: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return path


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def frontmatter(fields: dict[str, Any]) -> str:
    """Deterministic YAML frontmatter, written by code rather than trusted
    to the model -- BMAD documents key their whole lifecycle (``status:
    draft|final`` etc.) off this block, so it must parse correctly every
    time, not most of the time."""
    lines = ["---"]
    for k, v in fields.items():
        lines.append(f"{k}: {v}")
    lines.append("---\n")
    return "\n".join(lines)


def with_frontmatter(fields: dict[str, Any], body: str) -> str:
    return frontmatter(fields) + "\n" + body.strip() + "\n"


def slugify(text: str, max_words: int = 6) -> str:
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())[:max_words]
    return "-".join(words) or "untitled"


def read_workspace_diff(workspace: Path, max_chars: int = 20000) -> str:
    """Stand-in for ``git diff``: this port has no git integration, so
    "what changed" is approximated as "everything currently in the
    workspace". Good enough for a from-scratch build; if you point
    ``workspace_dir`` at a real checkout, swap this for an actual
    ``git diff`` call."""
    files = sorted(p for p in workspace.rglob("*") if p.is_file())
    if not files:
        return "(no files in workspace yet)"
    chunks = [f"--- {p.relative_to(workspace)} ---\n{p.read_text(encoding='utf-8', errors='replace')}" for p in files]
    return "\n\n".join(chunks)[:max_chars]


def today() -> str:
    return date.today().isoformat()


def now() -> str:
    return datetime.now().strftime("%m-%d-%Y %H:%M")
