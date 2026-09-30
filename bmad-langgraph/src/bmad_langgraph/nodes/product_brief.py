"""Port of ``bmad-product-brief`` (Mary): strategic-vision capture.

Section list matches ``skills/bmad-product-brief/assets/brief-template.md``
in the source repo.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from ..artifacts import planning_dir, with_frontmatter, today, write_markdown
from ..llm import get_llm
from ..memlog import entry
from ..personas import MARY, system_prompt
from ..state import BmadState

TASK = """Write a product brief capturing the strategic vision for this
project. Use exactly these sections, each 2-6 sentences or a short bullet
list -- terse and decision-useful, not padded:

- Executive Summary
- The Problem
- The Solution
- What Makes This Different
- Who This Serves
- Success Criteria
- Scope
- Vision

Ground every claim in what the user actually told you or in the
brainstorming report if one is provided. Mark any inference you are making
beyond that with `[ASSUMPTION]`.
"""


def product_brief(state: BmadState) -> dict:
    idea = state.get("human_input") or "the user's project idea"
    upstream = state.get("brainstorming_report")

    llm = get_llm(temperature=0.5)
    prompt = system_prompt(MARY, TASK)
    context = f"Project idea / request: {idea}"
    if upstream:
        context += f"\n\nBrainstorming report to draw from:\n{upstream}"

    response = llm.invoke([SystemMessage(content=prompt), HumanMessage(content=context)])
    body = response.content

    doc = with_frontmatter({"title": "Product Brief", "status": "final", "created": today()}, body)
    path = write_markdown(Path(planning_dir(state["output_dir"])) / "product-brief.md", doc)

    return {
        "product_brief": body,
        "messages": [AIMessage(content=f"{MARY.icon} Product brief written to {path}.")],
        "decision_log": [entry("analysis", "mary", "artifact", f"Wrote product brief ({path})")],
    }
