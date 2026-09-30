"""Port of ``bmad-architecture`` (Winston): the architecture spine.

Two-layer Reviewer Gate, same as the source skill:
1. ``lint_spine`` -- deterministic, no model call. Ports the spirit of
   ``skills/bmad-architecture/scripts/lint_spine.py``: catches placeholder
   text, duplicate AD ids, and AD blocks missing Binds/Prevents/Rule.
2. A rubric-walker LLM call for the judgment calls a linter can't make
   (does this actually resolve the PRD's hard parts?).
"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..artifacts import planning_dir, with_frontmatter, today, write_markdown
from ..llm import get_llm, get_structured_llm
from ..memlog import entry
from ..personas import WINSTON, system_prompt
from ..schemas import QualityGrade
from ..state import BmadState

DRAFT_TASK = """Write an architecture spine: the technical invariants that
keep independently-built units of this system consistent. Use exactly
these sections:

## Design Paradigm
One paragraph: the overall shape (e.g. modular monolith, service-oriented,
event-driven) and why.

## Invariants & Rules
One block per decision, format exactly:

### AD-1: <short name>
- Binds: <what this constrains>
- Prevents: <what divergence this rules out>
- Rule: <the enforceable rule itself, stated so a linter or reviewer could
  check it>

Number sequentially (AD-1, AD-2, ...) and never reuse a number.

## Consistency Conventions
Table: Concern | Convention -- cover naming, data & formats, state & cross-cutting concerns.

## Stack
Table: Name | Version -- pin every version, no "latest".

## Structural Seed
A mermaid diagram (```mermaid fenced) of the system/container structure,
plus a short source-tree sketch.

## Deferred
Decisions deliberately pushed down to implementation time, and why.
"""

REVIEW_TASK = """Review this architecture spine as a rubric walker. Check:
does it resolve the PRD's actual hard parts (not just restate obvious
choices)? Is every AD Rule concretely enforceable? Does Deferred avoid
hiding a real divergence risk? Is the stack genuinely current, not stale
defaults?

Grade Excellent/Good/Fair/Poor using the same bands as a PRD review:
Excellent = fully resolved, no gaps; Good = minor gaps; Fair = a real
open question left unresolved; Poor = the spine doesn't actually constrain
implementation.
"""

_AD_BLOCK = re.compile(r"^### AD-(\d+):", re.MULTILINE)
_PLACEHOLDER = re.compile(r"\{\{.*?\}\}|<short name>|<what this|<the enforceable")


def lint_spine(markdown: str) -> list[str]:
    """Deterministic structural lint -- port of ``lint_spine.py``'s checks."""
    errors: list[str] = []
    ad_ids = _AD_BLOCK.findall(markdown)
    if not ad_ids:
        errors.append("no AD-N invariant blocks found")
    duplicates = {i for i in ad_ids if ad_ids.count(i) > 1}
    if duplicates:
        errors.append(f"duplicate AD ids: {sorted(duplicates)}")
    for field in ("Binds:", "Prevents:", "Rule:"):
        if markdown.count(field) < len(ad_ids):
            errors.append(f"at least one AD block is missing a '{field}' line")
    if _PLACEHOLDER.search(markdown):
        errors.append("unresolved placeholder text left in the document")
    if "## Stack" not in markdown:
        errors.append("missing Stack section")
    if re.search(r"\|\s*latest\s*\|", markdown, re.IGNORECASE):
        errors.append("Stack pins a version as 'latest' instead of a concrete version")
    return errors


def architecture(state: BmadState) -> dict:
    context_parts = [f"Request: {state.get('human_input') or 'draft the architecture'}"]
    if state.get("prd"):
        context_parts.append(f"PRD:\n{state['prd']}")
    if state.get("ux_experience"):
        context_parts.append(f"UX experience spec:\n{state['ux_experience']}")
    context = "\n\n".join(context_parts)

    llm = get_llm(temperature=0.3)
    draft = llm.invoke(
        [SystemMessage(content=system_prompt(WINSTON, DRAFT_TASK)), HumanMessage(content=context)]
    ).content

    lint_errors = lint_spine(draft)
    if lint_errors:
        fix_note = "Fix these structural problems and re-emit the full document:\n" + "\n".join(
            f"- {e}" for e in lint_errors
        )
        draft = llm.invoke(
            [
                SystemMessage(content=system_prompt(WINSTON, DRAFT_TASK)),
                HumanMessage(content=context),
                AIMessage(content=draft),
                HumanMessage(content=fix_note),
            ]
        ).content
        lint_errors = lint_spine(draft)

    grader = get_structured_llm(QualityGrade)
    grade: QualityGrade = grader.invoke([SystemMessage(content=REVIEW_TASK), HumanMessage(content=draft)])

    doc = with_frontmatter(
        {"title": "Architecture Spine", "status": "final", "created": today(), "grade": grade.grade}, draft
    )
    path = write_markdown(Path(planning_dir(state["output_dir"])) / "architecture-spine.md", doc)

    decision_log = [
        entry("solutioning", "winston", "artifact", "Drafted architecture spine"),
        entry(
            "solutioning",
            "winston",
            "gate",
            f"Architecture Reviewer Gate: {grade.grade}; lint errors remaining: {lint_errors or 'none'}",
        ),
    ]

    return {
        "architecture_spine": draft,
        "architecture_grade": grade.grade,
        "messages": [AIMessage(content=f"{WINSTON.icon} Architecture spine written to {path} (grade: {grade.grade}).")],
        "decision_log": decision_log,
    }
