"""Port of ``bmad-ux`` (Sally): DESIGN.md + EXPERIENCE.md.

Two documents, matching the source skill's split: ``DESIGN.md`` is visual
identity (tokens a design system would consume), ``EXPERIENCE.md`` is
information architecture and interaction behavior. Architecture and build
read both.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..artifacts import planning_dir, with_frontmatter, today, write_markdown
from ..llm import get_llm
from ..memlog import entry
from ..personas import SALLY, system_prompt
from ..state import BmadState

DESIGN_TASK = """Write DESIGN.md: the visual identity for this product.
Sections, in order, omit any that genuinely don't apply:

Brand & Style, Colors, Typography, Layout & Spacing, Elevation & Depth,
Shapes, Components, Do's and Don'ts.

Be concrete (named hex ranges, spacing scale, type ramp) rather than vague
("clean and modern") -- this feeds a design system, not a mood board.
"""

EXPERIENCE_TASK = """Write EXPERIENCE.md: information architecture and
interaction behavior for this product. Always include: Foundation,
Information Architecture, Voice and Tone, Component Patterns, State
Patterns, Interaction Primitives, Accessibility Floor, Key Flows. Add
Responsive & Platform only if the PRD implies multiple form factors.

Key Flows should name the user journeys from the PRD (if provided) and
walk each as a numbered step sequence with the state/error handling at
each step, not just the happy path.
"""


def ux(state: BmadState) -> dict:
    prd_text = state.get("prd") or state.get("human_input") or "No PRD yet -- infer a reasonable scope."
    llm = get_llm(temperature=0.6)

    design = llm.invoke(
        [SystemMessage(content=system_prompt(SALLY, DESIGN_TASK)), HumanMessage(content=f"PRD:\n{prd_text}")]
    ).content
    experience = llm.invoke(
        [SystemMessage(content=system_prompt(SALLY, EXPERIENCE_TASK)), HumanMessage(content=f"PRD:\n{prd_text}")]
    ).content

    out = planning_dir(state["output_dir"])
    design_path = write_markdown(
        Path(out) / "design.md", with_frontmatter({"title": "Design", "status": "final", "created": today()}, design)
    )
    experience_path = write_markdown(
        Path(out) / "experience.md",
        with_frontmatter({"title": "Experience", "status": "final", "created": today()}, experience),
    )

    return {
        "ux_design": design,
        "ux_experience": experience,
        "messages": [AIMessage(content=f"{SALLY.icon} UX specs written to {design_path} and {experience_path}.")],
        "decision_log": [entry("planning", "sally", "artifact", "Wrote DESIGN.md and EXPERIENCE.md")],
    }
