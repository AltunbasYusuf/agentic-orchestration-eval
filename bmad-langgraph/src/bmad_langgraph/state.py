"""Shared graph state.

This is the single object threaded through every node via the LangGraph
checkpointer. It plays the role BMAD's on-disk artifacts + ``.memlog.md``
play in the original skill system: whatever a node (or a resumed session,
days later) needs to pick up where things left off lives here, not in
node-local variables.

Every field is optional (``total=False``) because a fresh project starts
with almost all of them empty — BMAD's phases are progressive, not
all-or-nothing, and this graph is meant to be enterable at any point (e.g.
you can skip straight to ``build`` with nothing but an idea, exactly like
BMAD's "direct intent" build path).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal, TypedDict

from langgraph.graph.message import add_messages

Phase = Literal["analysis", "planning", "solutioning", "implementation", "done"]

ReadinessVerdict = Literal["PASS", "CONCERNS", "FAIL"]
Grade = Literal["Excellent", "Good", "Fair", "Poor"]


def _append(existing: list | None, new: list | None) -> list:
    """Reducer: concatenate instead of overwrite, for append-only logs."""
    return [*(existing or []), *(new or [])]


def _last_wins(_existing: Any, new: Any) -> Any:
    """Reducer: explicit last-write-wins, used where None must be able to
    clear a field (plain TypedDict assignment already does this; kept as a
    named reducer for fields where that intent should be documented)."""
    return new


class DecisionLogEntry(TypedDict):
    """One line of the memlog equivalent (`decision_log`)."""

    phase: str
    agent: str
    kind: str  # idea | decision | gate | question | artifact | note
    content: str


class StoryRef(TypedDict):
    epic: int
    story: int
    id: str  # "{epic}.{story}"
    key: str  # sprint-status.yaml key: "{epic}-{story}-{slug}"
    title: str
    status: str  # backlog | ready-for-dev | in-progress | review | done


class BmadState(TypedDict, total=False):
    # --- conversation / control -------------------------------------------------
    messages: Annotated[list, add_messages]
    project_name: str
    output_dir: str
    phase: Phase
    active_agent: str  # persona key currently "in character": mary/john/winston/amelia/sally
    route: str | None  # node the orchestrator picked this turn
    human_input: str | None  # raw human turn the orchestrator routes on

    # --- decision log (memlog equivalent) ---------------------------------------
    decision_log: Annotated[list[DecisionLogEntry], _append]

    # --- Phase 1: Analysis --------------------------------------------------------
    brainstorming_report: str | None
    product_brief: str | None

    # --- Phase 2: Planning ---------------------------------------------------------
    prd: str | None
    prd_status: Literal["draft", "final"] | None
    prd_grade: Grade | None
    ux_design: str | None
    ux_experience: str | None

    # --- Phase 3: Solutioning --------------------------------------------------------
    architecture_spine: str | None
    architecture_grade: Grade | None
    epics_markdown: str | None
    stories: Annotated[list[StoryRef], _append]
    sprint_status: dict[str, Any] | None
    readiness_verdict: ReadinessVerdict | None

    # --- Phase 4: Implementation ----------------------------------------------------
    current_story_key: str | None
    spec: dict[str, Any] | None  # mirrors spec-*.md frontmatter + body sections
    spec_markdown: str | None
    review_findings: Annotated[list[dict[str, Any]], _append]
    review_loop_iteration: int
    deferred_work: Annotated[list[str], _append]
    retro_verdict: str | None
    sprint_change_proposal: str | None


PHASE_BY_ROUTE: dict[str, Phase] = {
    "brainstorming": "analysis",
    "product_brief": "analysis",
    "prd": "planning",
    "ux": "planning",
    "architecture": "solutioning",
    "epics_stories": "solutioning",
    "sprint_planning": "solutioning",
    "build": "implementation",
    "code_review": "implementation",
    "retrospective": "implementation",
    "correct_course": "implementation",
}

AGENT_BY_ROUTE: dict[str, str] = {
    "brainstorming": "mary",
    "product_brief": "mary",
    "prd": "john",
    "ux": "sally",
    "architecture": "winston",
    "epics_stories": "john",
    "sprint_planning": "john",
    "build": "amelia",
    "code_review": "amelia",
    "retrospective": "amelia",
    "correct_course": "john",
}
