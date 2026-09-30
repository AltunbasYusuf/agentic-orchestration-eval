"""Port of ``bmad-prd`` (John): requirements definition + Reviewer Gate.

Section list matches the "Essential Spine" of
``skills/bmad-prd/assets/prd-template.md`` in the source repo (the adapt-in
menu clusters for enterprise/regulated/embedded products are omitted here
for scope; add them as extra prompt instructions if your project needs
them -- see the README "Extending" section).

The Reviewer Gate is the first real gate in this port: BMAD's rubric
walker (7 dimensions -> strong/adequate/thin/broken -> Excellent/Good/Fair/
Poor) becomes a structured ``QualityGrade`` call. Fair/Poor pauses on an
``interrupt`` for a human revise-or-accept call, matching BMAD's own rule
that a low grade does not auto-block -- it surfaces gaps and asks.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from ..artifacts import planning_dir, with_frontmatter, today, write_markdown
from ..llm import get_llm, get_structured_llm
from ..memlog import entry
from ..personas import JOHN, system_prompt
from ..schemas import QualityGrade
from ..state import BmadState

DRAFT_TASK = """Write a Product Requirements Document. Use exactly these
sections:

0. Document Purpose
1. Vision
2. Target User
   2.1 Jobs To Be Done
   2.2 Key User Journeys (UJ-1, UJ-2, ... each: Persona & context / Entry
       state / Path / Climax / Resolution)
3. Glossary
4. Features (for each: Description, then Functional Requirements as
   `FR<n>: <requirement>` with Consequences and Out of Scope notes)
5. Non-Goals (Explicit)
6. MVP Scope (6.1 In Scope, 6.2 Out of Scope for MVP)
7. Success Metrics (Primary / Secondary / Counter-metrics as `SM<n>`)
8. Open Questions
9. Assumptions Index

Number every FR and SM globally and consistently (FR1, FR2, ... SM1, SM2,
...) -- ``epics_stories`` and the readiness gate later trace requirements
by these ids. Tag any inference beyond what was stated with `[ASSUMPTION]`.
"""

REVIEW_TASK = """You are reviewing a draft PRD against BMad's PRD rubric.
Grade across: clarity of vision, testability of requirements, FR/NFR
numbering discipline, scope discipline (MVP vs non-goals), user-journey
coverage, success-metric quality, and internal consistency.

Grade bands:
- Excellent: every dimension strong or adequate, no high/critical gaps.
- Good: at most one thin dimension, no critical gaps.
- Fair: multiple thin dimensions, or any high-severity gap.
- Poor: any broken dimension, or any critical gap.
"""


def prd(state: BmadState) -> dict:
    context_parts = [f"Request: {state.get('human_input') or 'draft the PRD'}"]
    if state.get("product_brief"):
        context_parts.append(f"Product brief:\n{state['product_brief']}")
    if state.get("brainstorming_report"):
        context_parts.append(f"Brainstorming report:\n{state['brainstorming_report']}")
    context = "\n\n".join(context_parts)

    llm = get_llm(temperature=0.4)
    draft = llm.invoke(
        [SystemMessage(content=system_prompt(JOHN, DRAFT_TASK)), HumanMessage(content=context)]
    ).content

    grader = get_structured_llm(QualityGrade)
    grade: QualityGrade = grader.invoke(
        [SystemMessage(content=REVIEW_TASK), HumanMessage(content=draft)]
    )

    decision_log = [
        entry("planning", "john", "artifact", "Drafted PRD"),
        entry("planning", "john", "gate", f"PRD Reviewer Gate: {grade.grade} -- gaps: {grade.gaps or 'none'}"),
    ]

    if grade.grade in ("Fair", "Poor"):
        gaps = "\n".join(f"- {g}" for g in grade.gaps) or "(no specific gaps listed)"
        answer = interrupt(
            {
                "agent": "john",
                "question": (
                    f"PRD Reviewer Gate came back **{grade.grade}**. Gaps:\n{gaps}\n\n"
                    "Reply 'accept' to ship it as-is, or describe what to fix and I'll revise."
                ),
            }
        )
        if str(answer).strip().lower() not in ("accept", "accept as-is", "ship it", "yes"):
            revise_context = f"{context}\n\nPrevious draft:\n{draft}\n\nRequested changes:\n{answer}"
            draft = llm.invoke(
                [SystemMessage(content=system_prompt(JOHN, DRAFT_TASK)), HumanMessage(content=revise_context)]
            ).content
            grade = grader.invoke([SystemMessage(content=REVIEW_TASK), HumanMessage(content=draft)])
            decision_log.append(entry("planning", "john", "gate", f"PRD revised -- new grade: {grade.grade}"))

    doc = with_frontmatter(
        {"title": "Product Requirements Document", "status": "final", "created": today(), "grade": grade.grade},
        draft,
    )
    path = write_markdown(Path(planning_dir(state["output_dir"])) / "prd.md", doc)

    return {
        "prd": draft,
        "prd_status": "final",
        "prd_grade": grade.grade,
        "messages": [AIMessage(content=f"{JOHN.icon} PRD written to {path} (grade: {grade.grade}).")],
        "decision_log": decision_log,
    }
