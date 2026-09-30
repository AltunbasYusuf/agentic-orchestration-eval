"""Port of ``bmad-brainstorming`` (Mary).

Simplification vs. the source skill: BMAD's brainstorming is a live,
technique-by-technique facilitation session logged to ``.memlog.md``, with
an optional HTML "keepsake" rendered at the end. This port collapses that
into one pass that still asks a clarifying question up front (an
``interrupt``, matching BMAD's "stop and wait for input" facilitator
stance) and then produces the one artifact every downstream workflow
actually consumes: a condensed brainstorming report.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from ..artifacts import planning_dir, with_frontmatter, today, write_markdown
from ..llm import get_llm
from ..memlog import entry
from ..personas import MARY, system_prompt
from ..state import BmadState

TASK = """Facilitate a short brainstorming session on the user's topic, then
write a brainstorming report.

Techniques to draw from as needed: "What if" provocation, first-principles
breakdown, analogical thinking (borrow a solution from an unrelated
domain), and reversal (list how to guarantee failure, then invert each).
You do not need to narrate technique names to the user.

Write the report with these sections:
- Topic & Goal
- Ideas Generated (grouped by theme)
- Non-Obvious Connections (patterns across otherwise unrelated ideas)
- Recommended Directions (the 2-4 ideas worth carrying into a product brief or PRD)
- Parking Lot (interesting but out of scope)
"""


def brainstorming(state: BmadState) -> dict:
    topic = state.get("human_input") or "the user's project idea"

    clarification = interrupt(
        {
            "agent": "mary",
            "question": (
                f"Before we brainstorm '{topic}': any constraint or goal I should "
                "aim ideas at (audience, timeframe, must-avoid)? Say 'none' to skip."
            ),
        }
    )

    llm = get_llm(temperature=0.9)
    prompt = system_prompt(MARY, TASK)
    response = llm.invoke(
        [
            SystemMessage(content=prompt),
            HumanMessage(content=f"Topic: {topic}\nConstraint/goal from the user: {clarification}"),
        ]
    )
    body = response.content

    doc = with_frontmatter({"title": "Brainstorming Report", "status": "final", "created": today()}, body)
    path = write_markdown(Path(planning_dir(state["output_dir"])) / "brainstorming-report.md", doc)

    return {
        "brainstorming_report": body,
        "messages": [AIMessage(content=f"{MARY.icon} Brainstorming report written to {path}.")],
        "decision_log": [entry("analysis", "mary", "artifact", f"Wrote brainstorming report ({path})")],
    }
