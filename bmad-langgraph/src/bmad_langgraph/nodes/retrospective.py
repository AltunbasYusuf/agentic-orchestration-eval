"""Port of ``bmad-retrospective`` (Amelia): evidence-based epic wrap-up.

The source skill's most important rule is structural, not stylistic: an
epic with unfinished stories cannot be silently accepted, even in headless
mode, and a human decision always overrides the machine's own verdict. Both
rules are enforced here as plain Python (``pending_stories`` forces
``rejected`` before any model is asked anything), not as prompt
instructions the model could quietly drop under pressure.
"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from ..artifacts import (
    implementation_dir,
    planning_dir,
    read_workspace_diff,
    today,
    with_frontmatter,
    workspace_dir,
    write_markdown,
    write_yaml,
)
from ..llm import get_structured_llm
from ..memlog import entry
from ..personas import AMELIA
from ..schemas import RetroVerdict
from ..state import BmadState
from .review_layers import run_review

VERDICT_TASK = """Given the findings and epic summary below, propose a
retrospective verdict: 'accepted' (criteria demonstrably met, nothing
blocking open), 'accepted-with-open-items' (criteria met, but named
findings are tracked as deferred), or 'rejected' (criteria not met, or a
blocking finding is unresolved)."""


def _epic_number(human_input: str | None, sprint_status: dict | None) -> int:
    if human_input:
        m = re.search(r"epic\s*(\d+)", human_input, re.IGNORECASE)
        if m:
            return int(m.group(1))
    if sprint_status:
        epic_keys = [k for k in sprint_status.get("development_status", {}) if re.fullmatch(r"epic-\d+", k)]
        if epic_keys:
            return min(int(k.split("-")[1]) for k in epic_keys)
    return 1


def _pending_stories(epic: int, sprint_status: dict | None) -> list[str]:
    if not sprint_status:
        return []
    pending = []
    for key, status in sprint_status.get("development_status", {}).items():
        if key.startswith(f"{epic}-") and status != "done":
            pending.append(key)
    return pending


def retrospective(state: BmadState) -> dict:
    sprint_status = state.get("sprint_status")
    epic = _epic_number(state.get("human_input"), sprint_status)
    pending = _pending_stories(epic, sprint_status)

    workspace = workspace_dir(state["output_dir"])
    diff_text = read_workspace_diff(workspace)
    findings = run_review(diff_text, ["blind_hunter", "verification_gap"], ["patch", "defer", "decision_needed"])
    blocking = [f for f in findings if f["bucket"] == "decision_needed"]
    deferred = [f for f in findings if f["bucket"] == "defer"]

    if pending:
        machine_verdict = "rejected"
        rationale = f"Epic {epic} has unfinished stories: {pending}."
    else:
        verdict_llm = get_structured_llm(RetroVerdict)
        context = (
            f"Epic {epic}. Pending stories: none. Blocking findings: {[f['summary'] for f in blocking]}. "
            f"Deferred findings: {[f['summary'] for f in deferred]}."
        )
        proposal: RetroVerdict = verdict_llm.invoke([SystemMessage(content=VERDICT_TASK), HumanMessage(content=context)])
        machine_verdict, rationale = proposal.verdict, proposal.rationale

    human_answer = interrupt(
        {
            "agent": "amelia",
            "question": (
                f"Machine verdict for Epic {epic}: **{machine_verdict}** -- {rationale}\n\n"
                "Reply 'confirm' to accept this verdict, or state your own "
                "(accepted / accepted-with-open-items / rejected) with a reason -- "
                "a human call always overrides the machine's."
            ),
        }
    )
    final_verdict = machine_verdict
    human_norm = str(human_answer).strip().lower()
    for candidate in ("accepted-with-open-items", "accepted", "rejected"):
        if candidate in human_norm:
            final_verdict = candidate
            break

    action_items = [{"epic": epic, "action": f["summary"], "owner": "unassigned", "status": "open"} for f in deferred]

    findings_lines = [f"- ({f['layer']}) {f['summary']}" for f in findings] or ["(none)"]
    action_lines = [f"- {a['action']} (owner: {a['owner']}, status: {a['status']})" for a in action_items] or ["(none)"]

    doc_body = "\n".join(
        [
            f"## Epic {epic} Summary",
            "",
            f"Pending stories at review time: {pending or 'none'}.",
            "",
            "## Findings",
            "",
            *findings_lines,
            "",
            "## Action Items",
            "",
            *action_lines,
            "",
            "## Acceptance Verdict",
            "",
            f"**{final_verdict}** -- {rationale}" + (" (human override applied)" if final_verdict != machine_verdict else ""),
        ]
    )
    doc = with_frontmatter(
        {"epic": epic, "date": today(), "verdict": final_verdict, "criteria": "profiled", "headless": "false"}, doc_body
    )
    path = write_markdown(Path(implementation_dir(state["output_dir"])) / f"epic-{epic}-retro-{today()}.md", doc)

    if sprint_status:
        sprint_status.setdefault("development_status", {})[f"epic-{epic}-retrospective"] = "done"
        sprint_status.setdefault("action_items", []).extend(action_items)
        write_yaml(Path(planning_dir(state["output_dir"])) / "sprint-status.yaml", sprint_status)

    return {
        "retro_verdict": final_verdict,
        "sprint_status": sprint_status,
        "messages": [AIMessage(content=f"{AMELIA.icon} Epic {epic} retrospective: **{final_verdict}**. Written to {path}.")],
        "decision_log": [entry("implementation", "amelia", "gate", f"Retro epic {epic}: {final_verdict}")],
    }
