"""Port of ``bmad-correct-course`` (John): the mid-sprint change handler.

BMAD's own decision framework is the scope classification
(Minor/Moderate/Major) driving a handoff routing table, plus a
Recommended-Approach trichotomy (Direct Adjustment / Potential Rollback /
MVP Review). Both come back as one structured ``ChangeScope`` call here
instead of a six-step interactive checklist walk -- the checklist's
purpose (surface every angle before proposing a fix) is preserved as an
explicit instruction list in the prompt rather than as separate turns.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from ..artifacts import planning_dir, today, with_frontmatter, write_markdown
from ..llm import get_llm, get_structured_llm
from ..memlog import entry
from ..personas import JOHN, system_prompt
from ..schemas import ChangeScope
from ..state import BmadState

ROUTE_LABEL = {
    "minor": "Developer (direct implementation via `build`)",
    "moderate": "Product Manager / Developer (backlog reorganization via `epics_stories` + `sprint_planning`)",
    "major": "Product Manager / Architect (replan via `prd` + `architecture`)",
}

ANALYSIS_TASK = """A significant change or issue has surfaced mid-sprint.
Analyze its ripple effects across the PRD, epics/stories, and architecture
(when present):

- Epic Impact: which epics does this touch, and how
- Story Impact: which stories need to change, be added, or be dropped
- Artifact Conflicts: where does this contradict what's already written
- Technical Impact: architecture implications, if any

Then recommend one approach: Direct Adjustment (modify/add stories in
place), Potential Rollback (revert completed work that the change
invalidates), or MVP Review (reduce scope / change goals). Justify it.
"""

PROPOSAL_TASK = """Write the "Sprint Change Proposal" document. Sections,
in order:

1. Issue Summary (problem statement, discovery context, evidence)
2. Impact Analysis (Epic Impact, Story Impact, Artifact Conflicts, Technical Impact)
3. Recommended Approach (the one you chose, with rationale, effort, risk, timeline)
4. Detailed Change Proposals (grouped by artifact type, before/after + justification)
5. Implementation Handoff (state the scope classification and who owns it)
"""


def correct_course(state: BmadState) -> dict:
    if not state.get("prd") or not state.get("epics_markdown"):
        return {
            "messages": [
                AIMessage(
                    content=f"{JOHN.icon} I can't assess cross-artifact impact without a PRD and an epics/stories "
                    "listing -- get those in place first."
                )
            ],
            "decision_log": [entry("implementation", "john", "note", "correct_course blocked: missing PRD or epics")],
        }

    issue = state.get("human_input") or "(no explicit description given -- infer from recent conversation)"
    context_parts = [f"Issue: {issue}", f"PRD:\n{state['prd']}", f"Epics & stories:\n{state['epics_markdown']}"]
    if state.get("architecture_spine"):
        context_parts.append(f"Architecture spine:\n{state['architecture_spine']}")
    context = "\n\n".join(context_parts)

    llm = get_llm(temperature=0.4)
    analysis = llm.invoke([SystemMessage(content=system_prompt(JOHN, ANALYSIS_TASK)), HumanMessage(content=context)]).content

    scope_llm = get_structured_llm(ChangeScope)
    scope: ChangeScope = scope_llm.invoke(
        [SystemMessage(content="Classify the scope of this change: minor/moderate/major."), HumanMessage(content=analysis)]
    )

    proposal_body = llm.invoke(
        [
            SystemMessage(content=system_prompt(JOHN, PROPOSAL_TASK)),
            HumanMessage(
                content=f"{context}\n\nAnalysis:\n{analysis}\n\nScope: {scope.scope} ({scope.approach}) -- {scope.rationale}"
            ),
        ]
    ).content

    approval = interrupt(
        {
            "agent": "john",
            "question": (
                f"Sprint Change Proposal drafted -- scope: **{scope.scope}**, approach: **{scope.approach}**.\n\n"
                f"Handoff: {ROUTE_LABEL[scope.scope]}.\n\nReply 'approve' to finalize, or describe changes."
            ),
        }
    )
    if str(approval).strip().lower() not in ("approve", "approved", "yes"):
        proposal_body = llm.invoke(
            [
                SystemMessage(content=system_prompt(JOHN, PROPOSAL_TASK)),
                HumanMessage(content=f"{context}\n\nPrevious draft:\n{proposal_body}\n\nRequested changes:\n{approval}"),
            ]
        ).content

    doc = with_frontmatter({"title": "Sprint Change Proposal", "scope": scope.scope, "created": today()}, proposal_body)
    path = write_markdown(Path(planning_dir(state["output_dir"])) / f"sprint-change-proposal-{today()}.md", doc)

    return {
        "sprint_change_proposal": proposal_body,
        "messages": [
            AIMessage(
                content=f"{JOHN.icon} Sprint change proposal written to {path}. "
                f"Scope **{scope.scope}** -> hand off to {ROUTE_LABEL[scope.scope]}."
            )
        ],
        "decision_log": [
            entry("implementation", "john", "artifact", f"Wrote sprint-change-proposal ({path})"),
            entry("implementation", "john", "decision", f"Scope: {scope.scope}, approach: {scope.approach}"),
        ],
    }
