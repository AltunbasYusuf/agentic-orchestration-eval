"""Interactive driver.

BMAD is normally driven by typing skill names / menu codes in an IDE chat.
This is the closest equivalent for a standalone graph: a REPL that prints
whichever persona is speaking, surfaces every ``interrupt()`` as a
question, and resumes the graph with your answer via ``Command(resume=...)``.

Run with ``python -m bmad_langgraph`` or the ``bmad-langgraph`` console
script installed by ``pyproject.toml``.
"""

from __future__ import annotations

import sys
import uuid

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.types import Command
from rich.console import Console
from rich.markdown import Markdown

from .config import settings
from .graph import build_graph

# Persona replies are prefixed with an emoji icon (see personas.py). Legacy
# Windows consoles default to a codepage (e.g. cp1254) that can't encode
# those glyphs and would otherwise crash the REPL outright -- force UTF-8
# with a safe fallback instead of losing the whole session over one emoji.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

console = Console()

BANNER = """[bold]BMad Method on LangGraph[/bold]
Analyst -> PM -> Architect -> UX -> Dev, as a resumable graph instead of chat skills.
Type 'exit' to quit. Type 'status' anytime to see what's been produced so far.
"""


def _print_ai_messages(result: dict) -> None:
    for m in result.get("messages", []):
        if isinstance(m, AIMessage) and m.content:
            console.print(Markdown(str(m.content)))


def _drain_interrupts(graph, result: dict, config: dict) -> dict:
    """Resume the graph for every pending ``interrupt()`` until the run
    finishes normally. Each interrupt's payload is a dict with ``agent``
    and ``question`` -- see any node under ``nodes/`` for examples."""
    while "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        if isinstance(payload, dict):
            agent, question = payload.get("agent", ""), payload.get("question", str(payload))
        else:
            agent, question = "", str(payload)
        console.print(f"\n[bold yellow]({agent})[/bold yellow] {question}")
        answer = console.input("> ")
        result = graph.invoke(Command(resume=answer), config)
    return result


def _status(result: dict) -> None:
    fields = [
        ("Phase", result.get("phase")),
        ("PRD grade", result.get("prd_grade")),
        ("Architecture grade", result.get("architecture_grade")),
        ("Readiness verdict", result.get("readiness_verdict")),
        ("Retro verdict", result.get("retro_verdict")),
        ("Stories tracked", len(result.get("stories", []))),
    ]
    for label, value in fields:
        if value:
            console.print(f"  {label}: {value}")


def _read_command(project_name: str, last_result: dict) -> str | None:
    """Prompt for the next instruction. Handles meta-commands (`status`,
    `exit`) locally without spending a graph turn; returns None on exit."""
    while True:
        user_text = console.input(f"\n[{project_name}] > ").strip()
        if user_text.lower() in ("exit", "quit"):
            return None
        if user_text.lower() == "status":
            _status(last_result)
            continue
        return user_text


def main() -> None:
    console.print(BANNER)
    project_name = console.input("Project name: ").strip() or "project"
    idea = console.input("What are we building? (one line is enough) ").strip()

    thread_id = str(uuid.uuid4())
    graph = build_graph()
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": settings.recursion_limit}
    console.print(f"\n[dim]thread id: {thread_id} -- pass this to resume later[/dim]\n")

    turn_input: dict = {
        "project_name": project_name,
        "output_dir": settings.output_dir,
        "phase": "analysis",
        "human_input": idea,
        "messages": [HumanMessage(content=idea)],
    }

    last_result: dict = {}
    while True:
        result = graph.invoke(turn_input, config)
        result = _drain_interrupts(graph, result, config)
        _print_ai_messages(result)
        last_result = result

        if result.get("route") == "end":
            break

        user_text = _read_command(project_name, last_result)
        if user_text is None:
            break
        turn_input = {"human_input": user_text, "messages": [HumanMessage(content=user_text)]}

    console.print(f"\nArtifacts are under [bold]{settings.output_dir}[/bold]. See you next time.")


if __name__ == "__main__":
    main()
