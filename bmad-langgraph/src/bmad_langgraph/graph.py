"""Compiles the top-level graph.

Shape: ``START -> orchestrator -> (conditional) -> exactly one workflow
node -> END``. Every workflow node runs to completion (pausing on
``interrupt()`` as needed) and the graph run ends -- matching how a BMAD
agent replies once and waits for the human's next menu choice. The next
human turn calls ``.invoke()`` again, which re-enters at ``orchestrator``
with the accumulated state from the checkpointer, so "staying in
character" across turns falls out of persistence rather than a loop.
"""

from __future__ import annotations

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from .nodes.architecture import architecture
from .nodes.brainstorming import brainstorming
from .nodes.build import build
from .nodes.code_review import code_review
from .nodes.correct_course import correct_course
from .nodes.epics_stories import epics_stories
from .nodes.orchestrator import orchestrator, route_edge
from .nodes.product_brief import product_brief
from .nodes.prd import prd
from .nodes.retrospective import retrospective
from .nodes.sprint_planning import sprint_planning
from .nodes.ux import ux
from .state import BmadState

WORKFLOW_NODES = {
    "brainstorming": brainstorming,
    "product_brief": product_brief,
    "prd": prd,
    "ux": ux,
    "architecture": architecture,
    "epics_stories": epics_stories,
    "sprint_planning": sprint_planning,
    "build": build,
    "code_review": code_review,
    "retrospective": retrospective,
    "correct_course": correct_course,
}


def build_graph(checkpointer: BaseCheckpointSaver | None = None):
    """Compile the BMad-on-LangGraph graph.

    Pass a durable checkpointer (e.g. ``langgraph.checkpoint.sqlite.SqliteSaver``)
    to resume sessions across process restarts; defaults to in-memory, which
    only resumes within the same Python process.
    """
    builder = StateGraph(BmadState)
    builder.add_node("orchestrator", orchestrator)
    for name, fn in WORKFLOW_NODES.items():
        builder.add_node(name, fn)
        builder.add_edge(name, END)

    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges(
        "orchestrator",
        route_edge,
        {**{name: name for name in WORKFLOW_NODES}, "end": END},
    )

    return builder.compile(checkpointer=checkpointer or MemorySaver())
