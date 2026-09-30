"""Structured-output contracts for every judgment call BMAD originally left
to prose convention (a menu code, a "PASS/CONCERNS/FAIL" heading the model
was trusted to spell correctly).

Porting these to ``pydantic`` models consumed via
``llm.with_structured_output`` is the main structural upgrade this port
makes over the source skills: gates become real conditional edges instead of
a human (or the model) having to notice a keyword in free text.
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal

Route = Literal[
    "brainstorming",
    "product_brief",
    "prd",
    "ux",
    "architecture",
    "epics_stories",
    "sprint_planning",
    "build",
    "code_review",
    "retrospective",
    "correct_course",
    "end",
]

Agent = Literal["mary", "john", "winston", "amelia", "sally"]
Grade = Literal["Excellent", "Good", "Fair", "Poor"]
Severity = Literal["critical", "high", "medium", "low"]
FindingVerdict = Literal["high", "medium", "low", "false", "maybe-false"]
Bucket = Literal["intent_gap", "bad_spec", "decision_needed", "patch", "defer"]


class RouteDecision(BaseModel):
    """Orchestrator output — the BMAD-help / agent-menu dispatch decision."""

    next: Route = Field(description="Which workflow node to run next.")
    agent: Agent = Field(description="Which persona is in character for that workflow.")
    reason: str = Field(description="One sentence: why this route fits the request and project state.")


class QualityGrade(BaseModel):
    """Shared shape for the PRD / UX / Architecture Reviewer Gate."""

    grade: Grade
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class ReadinessGate(BaseModel):
    """Sprint-planning implementation-readiness gate."""

    verdict: Literal["PASS", "CONCERNS", "FAIL"]
    gaps: list[str] = Field(default_factory=list)


class EpicPlanStory(BaseModel):
    number: int
    title: str
    as_a: str
    i_want: str
    so_that: str
    acceptance_criteria: list[str] = Field(
        description="Given/When/Then style bullets, one per acceptance criterion."
    )
    covers_frs: list[str] = Field(default_factory=list, description="FR ids this story satisfies, e.g. FR3.")


class EpicPlanEpic(BaseModel):
    number: int
    title: str
    goal: str
    stories: list[EpicPlanStory]


class EpicsPlan(BaseModel):
    fr_coverage_map: dict[str, str] = Field(
        default_factory=dict, description="FR id -> which epic.story satisfies it."
    )
    epics: list[EpicPlanEpic]


class ReviewFinding(BaseModel):
    layer: str
    severity: Severity
    verdict: FindingVerdict
    summary: str
    bucket: Bucket


class ReviewLayerOutput(BaseModel):
    findings: list[ReviewFinding] = Field(default_factory=list)


class RetroVerdict(BaseModel):
    verdict: Literal["accepted", "accepted-with-open-items", "rejected"]
    rationale: str


class ChangeScope(BaseModel):
    scope: Literal["minor", "moderate", "major"]
    approach: Literal["direct_adjustment", "potential_rollback", "mvp_review"]
    rationale: str
    routes_to: Agent = Field(description="Persona who should own the next step.")


class OneshotDecision(BaseModel):
    oneshot: bool = Field(
        description="True if this is small/reversible/unambiguous enough to skip the full plan->review loop."
    )
    rationale: str


class IOMatrixRow(BaseModel):
    scenario: str
    input_state: str
    expected: str
    error_handling: str


class SpecPlan(BaseModel):
    """Mirrors the ``<frozen-after-approval>`` block of BMAD's ``spec-template.md``."""

    problem: str
    approach: str
    always: list[str] = Field(default_factory=list, description="Boundaries the implementation must always respect.")
    never: list[str] = Field(default_factory=list, description="Boundaries the implementation must never cross.")
    io_matrix: list[IOMatrixRow] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)
    code_map: dict[str, str] = Field(default_factory=dict, description="file path -> role/relevance")
    tasks: list[str]
    acceptance: list[str] = Field(description="Given/When/Then acceptance criteria.")
    verification_commands: list[str] = Field(default_factory=list)
