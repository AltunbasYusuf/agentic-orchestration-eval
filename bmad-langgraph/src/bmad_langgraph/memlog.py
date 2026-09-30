"""The ``.memlog.md`` equivalent.

BMAD's brainstorming/brief/PRD/architecture/UX workflows all keep an
append-only decision log on disk (``.memlog.md``) that survives a session
restart and is what "resume where I left off" is built on. Here that log is
just a state field (``decision_log``, reduced with append-only semantics --
see ``state.py``) that rides on the LangGraph checkpointer, so resuming a
thread *is* resuming the memlog, with no separate file to keep in sync.

``render`` turns it back into the human-readable markdown BMAD would have
written, for when you want to inspect or export it.
"""

from __future__ import annotations

from .state import DecisionLogEntry


def entry(phase: str, agent: str, kind: str, content: str) -> DecisionLogEntry:
    return {"phase": phase, "agent": agent, "kind": kind, "content": content}


def render(decision_log: list[DecisionLogEntry]) -> str:
    lines = ["# Decision Log", ""]
    for e in decision_log:
        lines.append(f"- **[{e['phase']}/{e['agent']}/{e['kind']}]** {e['content']}")
    return "\n".join(lines) + "\n"
