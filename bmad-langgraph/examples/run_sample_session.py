"""Scripted end-to-end walk through every phase, answering every
``interrupt()`` with a naive auto-pilot instead of a human.

This is not a test (LLM output isn't asserted against fixed expectations)
and not how you'd normally use the graph -- it exists to (a) prove the
whole pipeline runs start to finish without a human at the keyboard, and
(b) serve as a second, more explicit usage example alongside the README
(each human turn below names its workflow directly, e.g. "create the
PRD", so routing doesn't depend on the orchestrator inferring intent).

Run with: `uv run python examples/run_sample_session.py`
Requires ANTHROPIC_API_KEY (or your configured BMAD_MODEL's key) in the
environment -- every step below makes real model calls.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from langgraph.types import Command  # noqa: E402

from bmad_langgraph.config import settings  # noqa: E402
from bmad_langgraph.graph import build_graph  # noqa: E402

SCRIPT = [
    "A tool that turns a grocery receipt photo into a categorized budget entry.",
    "create the PRD",
    "design the UX",
    "design the architecture",
    "create the epics and stories",
    "check implementation readiness",
    "implement the first story",
    "run a code review",
    "run a retrospective on epic 1",
]


def autopilot_answer(question: str) -> str:
    q = question.lower()
    if "constraint" in q or "goal i should aim" in q:
        return "none"
    if "checkpoint" in q or "reply 'continue'" in q:
        return "continue"
    if "reviewer gate" in q or "grade" in q:
        return "accept"
    if "approve" in q:
        return "approve"
    if "concerns" in q:
        return "yes"
    if "confirm" in q or "verdict" in q:
        return "confirm"
    return "yes"


def run_turn(graph, turn_input: dict, config: dict) -> dict:
    result = graph.invoke(turn_input, config)
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        question = payload.get("question", str(payload)) if isinstance(payload, dict) else str(payload)
        answer = autopilot_answer(question)
        print(f"  [interrupt] {question[:120]}...\n  [auto-answer] {answer}")
        result = graph.invoke(Command(resume=answer), config)
    for m in result.get("messages", []):
        if isinstance(m, AIMessage) and m.content:
            print(f"  {m.content[:300]}")
    return result


def main() -> None:
    graph = build_graph()
    config = {"configurable": {"thread_id": str(uuid.uuid4())}, "recursion_limit": settings.recursion_limit}

    for i, step_text in enumerate(SCRIPT):
        print(f"\n>>> {step_text}")
        turn_input: dict = {"human_input": step_text, "messages": [HumanMessage(content=step_text)]}
        if i == 0:
            turn_input.update(project_name="receipt-budgeter", output_dir=settings.output_dir, phase="analysis")
        run_turn(graph, turn_input, config)

    print(f"\nDone. Artifacts under {settings.output_dir}")


if __name__ == "__main__":
    main()
