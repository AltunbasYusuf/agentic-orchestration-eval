"""Port of ``bmad-sprint-planning``: the implementation-readiness gate plus
``sprint-status.yaml`` generation.

The gate has a cheap deterministic guard before any model call (mirrors
BMAD's "HALT if PRD/Epics missing") and an LLM judgment call for the parts
that need it (are decisions actually recorded, or merely assumed?).
``sprint-status.yaml`` is built by plain code from ``state['stories']`` --
BMAD's own field structure (see ``sprint-status-template.yaml`` in the
source skill) is reproduced exactly, so downstream tooling that expects
that shape keeps working.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from ..artifacts import now, planning_dir, write_yaml
from ..llm import get_structured_llm
from ..memlog import entry
from ..schemas import ReadinessGate
from ..state import BmadState

GATE_TASK = """You are the BMad Method implementation-readiness gate.
Judge: could a developer implement this without inventing any decision
that should have been made in planning? Check for:
- requirements that trace forward to a story and back to a PRD FR (no orphans)
- epics that each deliver user value with no forward dependency
- architecture/UX decisions that are recorded, not merely assumed
- conflicts between the PRD, architecture, and epics

Verdict PASS only if a developer could start immediately. CONCERNS if gaps
exist but work could start with them tracked. FAIL if starting now would
mean inventing product or architecture decisions.
"""


def sprint_planning(state: BmadState) -> dict:
    prd_text = state.get("prd")
    epics_text = state.get("epics_markdown")

    if not prd_text or not epics_text:
        missing = [n for n, v in (("PRD", prd_text), ("epics & stories", epics_text)) if not v]
        return {
            "readiness_verdict": "FAIL",
            "messages": [
                AIMessage(
                    content=f"📋 John: Readiness gate is a hard FAIL -- missing: {', '.join(missing)}. "
                    "Run those workflows first."
                )
            ],
            "decision_log": [entry("solutioning", "john", "gate", f"Readiness FAIL: missing {missing}")],
        }

    context = f"PRD:\n{prd_text}\n\nEpics & stories:\n{epics_text}"
    if state.get("architecture_spine"):
        context += f"\n\nArchitecture spine:\n{state['architecture_spine']}"

    gate = get_structured_llm(ReadinessGate)
    verdict: ReadinessGate = gate.invoke([SystemMessage(content=GATE_TASK), HumanMessage(content=context)])

    decision_log = [entry("solutioning", "john", "gate", f"Readiness gate: {verdict.verdict} -- {verdict.gaps}")]

    if verdict.verdict == "FAIL":
        return {
            "readiness_verdict": "FAIL",
            "messages": [
                AIMessage(content="📋 John: Readiness gate FAILED:\n" + "\n".join(f"- {g}" for g in verdict.gaps))
            ],
            "decision_log": decision_log,
        }

    if verdict.verdict == "CONCERNS":
        answer = interrupt(
            {
                "agent": "john",
                "question": (
                    "Readiness gate came back CONCERNS:\n"
                    + "\n".join(f"- {g}" for g in verdict.gaps)
                    + "\n\nProceed to generate the sprint plan anyway? (yes/no)"
                ),
            }
        )
        if str(answer).strip().lower() not in ("yes", "y", "proceed", "go"):
            return {
                "readiness_verdict": "CONCERNS",
                "messages": [AIMessage(content="📋 John: Holding off on sprint planning until those gaps are fixed.")],
                "decision_log": decision_log,
            }

    stories = state.get("stories", [])
    epics = sorted({s["epic"] for s in stories})
    development_status: dict[str, str] = {}
    for epic in epics:
        development_status[f"epic-{epic}"] = "backlog"
    for s in stories:
        development_status[s["key"]] = s.get("status", "backlog")

    sprint_status = {
        "generated": now(),
        "last_updated": now(),
        "project": state.get("project_name", "project"),
        "project_key": (state.get("project_name", "proj")[:8]).upper(),
        "tracking_system": "bmad-langgraph",
        "story_location": "implementation/stories",
        "development_status": development_status,
        "action_items": [],
    }
    path = write_yaml(Path(planning_dir(state["output_dir"])) / "sprint-status.yaml", sprint_status)

    return {
        "readiness_verdict": verdict.verdict,
        "sprint_status": sprint_status,
        "messages": [
            AIMessage(
                content=f"📋 John: Readiness gate {verdict.verdict}. Sprint status written to {path} "
                f"({len(stories)} stories across {len(epics)} epics)."
            )
        ],
        "decision_log": decision_log + [entry("solutioning", "john", "artifact", f"Wrote sprint-status.yaml ({path})")],
    }
