"""Turn-by-turn driver for driving the LangGraph BMAD port across separate
process invocations (one per Bash tool call), using a durable SQLite
checkpointer so state survives between calls.

Usage:
  uv run python driver.py start "<project_name>" "<idea text>"
  uv run python driver.py send "<message text>"
  uv run python driver.py resume "<answer text>"

Prints AI messages, then either:
  STATUS: interrupt
  QUESTION: <agent> | <question text>
or:
  STATUS: waiting_for_input
or:
  STATUS: done
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

from langchain_core.messages import AIMessage, HumanMessage  # noqa: E402
from langgraph.checkpoint.sqlite import SqliteSaver  # noqa: E402
from langgraph.types import Command  # noqa: E402

from bmad_langgraph.config import settings  # noqa: E402
from bmad_langgraph.graph import build_graph  # noqa: E402

DB_PATH = Path(__file__).parent / "driver_state.sqlite"
THREAD_FILE = Path(__file__).parent / "driver_thread_id.txt"


def _print_ai_messages(result: dict) -> None:
    for m in result.get("messages", []):
        if isinstance(m, AIMessage) and m.content:
            print(str(m.content))
            print("---")


def main() -> None:
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    with SqliteSaver.from_conn_string(str(DB_PATH)) as checkpointer:
        graph = build_graph(checkpointer=checkpointer)

        if cmd == "start":
            project_name = sys.argv[2]
            idea = sys.argv[3]
            thread_id = str(uuid.uuid4())
            THREAD_FILE.write_text(thread_id, encoding="utf-8")
            config = {"configurable": {"thread_id": thread_id}, "recursion_limit": settings.recursion_limit}
            turn_input = {
                "project_name": project_name,
                "output_dir": settings.output_dir,
                "phase": "analysis",
                "human_input": idea,
                "messages": [HumanMessage(content=idea)],
            }
            print(f"THREAD_ID: {thread_id}")
            result = graph.invoke(turn_input, config)
        elif cmd in ("send", "resume"):
            thread_id = THREAD_FILE.read_text(encoding="utf-8").strip()
            config = {"configurable": {"thread_id": thread_id}, "recursion_limit": settings.recursion_limit}
            text = sys.argv[2]
            if cmd == "send":
                result = graph.invoke({"human_input": text, "messages": [HumanMessage(content=text)]}, config)
            else:
                result = graph.invoke(Command(resume=text), config)
        else:
            print("usage: driver.py start|send|resume ...")
            sys.exit(1)

        _print_ai_messages(result)

        if "__interrupt__" in result:
            payload = result["__interrupt__"][0].value
            if isinstance(payload, dict):
                agent, question = payload.get("agent", ""), payload.get("question", str(payload))
            else:
                agent, question = "", str(payload)
            print("STATUS: interrupt")
            print(f"QUESTION: {agent} | {question}")
        elif result.get("route") == "end":
            print("STATUS: done")
        else:
            print("STATUS: waiting_for_input")


if __name__ == "__main__":
    main()
