"""Port of ``bmad-create-epics-and-stories`` (John), condensed from the
source skill's four steps (validate-prerequisites, design-epics,
create-stories, final-validation) into: structured generation -> FR
coverage check -> human approval -> deterministic markdown render.

The FR coverage check is deterministic (regex over the PRD + the model's
own ``covers_frs`` claims) rather than trusted to the model's diligence --
this is the step BMAD's step-04 spends the most words on, and it is exactly
the kind of check code does more reliably than a prompt.
"""

from __future__ import annotations

import re
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from ..artifacts import planning_dir, slugify, with_frontmatter, today, write_markdown
from ..llm import get_structured_llm
from ..memlog import entry
from ..schemas import EpicsPlan
from ..state import BmadState, StoryRef

TASK = """Break this PRD and architecture into epics and stories.

Rules:
- Group stories by user value, not by technical layer (no "backend epic" /
  "frontend epic" split).
- Every epic must be independently shippable -- no epic may depend on a
  later epic.
- Every story must be sized for one development session, phrased as
  `As a <user_type>, I want <capability>, so that <value>`, with
  Given/When/Then acceptance criteria.
- No story may depend on a later story in the same epic.
- Cover every functional requirement (FR<n>) in the PRD; list which FRs
  each story covers in `covers_frs`, and fill `fr_coverage_map` with every
  FR id you found in the PRD mapped to the "<epic>.<story>" that covers it.
"""


def _find_fr_ids(text: str) -> set[str]:
    return set(re.findall(r"\bFR\d+\b", text))


def epics_stories(state: BmadState) -> dict:
    prd_text = state.get("prd")
    if not prd_text:
        return {
            "messages": [
                AIMessage(content="📋 John: I need a PRD before I can carve out epics and stories. Run `prd` first.")
            ],
            "decision_log": [entry("solutioning", "john", "note", "Blocked: no PRD present")],
        }

    context = f"PRD:\n{prd_text}"
    if state.get("architecture_spine"):
        context += f"\n\nArchitecture spine:\n{state['architecture_spine']}"

    planner = get_structured_llm(EpicsPlan, temperature=0.3)
    plan: EpicsPlan = planner.invoke([SystemMessage(content=TASK), HumanMessage(content=context)])

    required_frs = _find_fr_ids(prd_text)
    covered_frs = set(plan.fr_coverage_map.keys()) | {
        fr for epic in plan.epics for story in epic.stories for fr in story.covers_frs
    }
    missing = sorted(required_frs - covered_frs, key=lambda x: int(x[2:]))

    epic_summary = "\n".join(f"- Epic {e.number}: {e.title} ({len(e.stories)} stories)" for e in plan.epics)
    approval = interrupt(
        {
            "agent": "john",
            "question": (
                f"Proposed epics:\n{epic_summary}\n\n"
                + (f"⚠ FRs with no covering story: {missing}\n\n" if missing else "All FRs covered.\n\n")
                + "Reply 'approve' to lock this in, or describe changes."
            ),
        }
    )
    if str(approval).strip().lower() not in ("approve", "approved", "yes", "lgtm"):
        context += f"\n\nRequested changes to the epic breakdown:\n{approval}"
        plan = planner.invoke([SystemMessage(content=TASK), HumanMessage(content=context)])
        covered_frs = set(plan.fr_coverage_map.keys()) | {
            fr for epic in plan.epics for story in epic.stories for fr in story.covers_frs
        }
        missing = sorted(required_frs - covered_frs, key=lambda x: int(x[2:]))

    markdown, stories = _render(plan, required_frs, missing)
    doc = with_frontmatter({"title": "Epics & Stories", "status": "final", "created": today()}, markdown)
    path = write_markdown(Path(planning_dir(state["output_dir"])) / "epics.md", doc)

    return {
        "epics_markdown": markdown,
        "stories": stories,
        "messages": [AIMessage(content=f"📋 John: Epics & stories written to {path} ({len(stories)} stories).")],
        "decision_log": [
            entry("solutioning", "john", "artifact", f"Wrote epics.md ({len(plan.epics)} epics, {len(stories)} stories)"),
            entry(
                "solutioning",
                "john",
                "gate",
                f"FR coverage: {len(required_frs) - len(missing)}/{len(required_frs)}" if required_frs else "no numbered FRs found in PRD",
            ),
        ],
    }


def _render(plan: EpicsPlan, required_frs: set[str], missing: list[str]) -> tuple[str, list[StoryRef]]:
    lines: list[str] = ["## Overview", "", "## FR Coverage Map", ""]
    lines.append("| FR | Covered by |")
    lines.append("| --- | --- |")
    for fr in sorted(required_frs, key=lambda x: int(x[2:])) if required_frs else []:
        lines.append(f"| {fr} | {plan.fr_coverage_map.get(fr, '**MISSING**' if fr in missing else '')} |")
    lines.append("")
    lines.append("## Epic List")
    lines.append("")

    stories: list[StoryRef] = []
    for epic in plan.epics:
        lines.append(f"## Epic {epic.number}: {epic.title}")
        lines.append("")
        lines.append(f"**Goal:** {epic.goal}")
        lines.append("")
        for story in epic.stories:
            lines.append(f"### Story {epic.number}.{story.number}: {story.title}")
            lines.append("")
            lines.append(f"As a {story.as_a}, I want {story.i_want}, so that {story.so_that}.")
            lines.append("")
            lines.append("**Acceptance Criteria**")
            for ac in story.acceptance_criteria:
                lines.append(f"- {ac}")
            lines.append("")
            slug = slugify(story.title)
            stories.append(
                {
                    "epic": epic.number,
                    "story": story.number,
                    "id": f"{epic.number}.{story.number}",
                    "key": f"{epic.number}-{story.number}-{slug}",
                    "title": story.title,
                    "status": "backlog",
                }
            )
    return "\n".join(lines), stories
