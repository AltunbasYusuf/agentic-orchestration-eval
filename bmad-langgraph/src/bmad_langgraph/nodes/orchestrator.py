"""The hub node -- BMAD's ``bmad-help`` skill and the agent menus
(``{agent.menu}`` in every ``customize.toml``) collapsed into one router.

Every graph run starts here (``START -> orchestrator``) and orchestrator
dispatches to exactly one workflow node for that turn via a conditional
edge keyed on ``state['route']``. Workflow nodes do not loop back to the
orchestrator -- they run to completion (or to an ``interrupt`` the CLI
resumes) and the run ends, exactly like BMAD: an agent replies, then waits
for the human's next instruction. The next human turn starts a fresh
``graph.invoke`` from the orchestrator again, so this function is what
"stays active and reads the menu" every time.
"""

from __future__ import annotations

from langchain_core.messages import AIMessage, SystemMessage

from ..llm import get_structured_llm
from ..memlog import entry
from ..personas import PERSONAS
from ..schemas import RouteDecision
from ..state import PHASE_BY_ROUTE, BmadState

ROUTING_PROMPT = """You are the BMad Method orchestrator. Route the user's
request to exactly one workflow node.

## Phases and workflows (BMad Method workflow map)

1. Analysis (optional): brainstorming -> product_brief
2. Planning: prd -> ux (optional, when UX matters)
3. Solutioning: architecture -> epics_stories -> sprint_planning (readiness gate)
4. Implementation: build (feature/fix/story) <-> code_review, retrospective
   (epic wrap-up), correct_course (major mid-sprint change)

Clear work can enter "build" directly without the earlier phases -- BMad
calls this the direct-intent path. Larger initiatives should follow the
phase order above so each document has the context the next one needs.

## Current project state

- Phase so far: {phase}
- Artifacts present: {artifacts}
- Last chosen route: {last_route}

## Routing rules

- If the user names a workflow or persona explicitly, honor it.
- If the user's message is small talk or a question about the process
  itself rather than a request to do something, pick the workflow that best
  continues where the project left off and explain why in `reason` --
  there is no standalone "chat" route.
- If nothing sensible remains (user is done, or explicitly says stop),
  route to "end".
- Prefer the earliest unmet phase when the user has not stated a preference.
"""


def _artifact_summary(state: BmadState) -> str:
    present = []
    for label, key in [
        ("brainstorming report", "brainstorming_report"),
        ("product brief", "product_brief"),
        ("PRD", "prd"),
        ("UX design", "ux_design"),
        ("architecture spine", "architecture_spine"),
        ("epics & stories", "epics_markdown"),
        ("sprint status", "sprint_status"),
        ("spec / build state", "spec"),
    ]:
        if state.get(key):
            present.append(label)
    return ", ".join(present) or "none yet"


def orchestrator(state: BmadState) -> dict:
    messages = state.get("messages", [])

    prompt = ROUTING_PROMPT.format(
        phase=state.get("phase", "analysis"),
        artifacts=_artifact_summary(state),
        last_route=state.get("route") or "none",
    )
    router = get_structured_llm(RouteDecision)
    # Last few turns give the router conversational context; state.human_input
    # is not re-injected here because the CLI already appended it to `messages`.
    decision: RouteDecision = router.invoke([SystemMessage(content=prompt), *messages[-6:]])

    if decision.next == "end":
        return {
            "route": "end",
            "messages": [AIMessage(content="Ending the session. Run again anytime to resume.")],
        }

    persona = PERSONAS[decision.agent]
    phase = PHASE_BY_ROUTE.get(decision.next, state.get("phase", "analysis"))
    greeting = f"{persona.icon} {persona.name}: {decision.reason}"

    return {
        "route": decision.next,
        "active_agent": decision.agent,
        "phase": phase,
        "messages": [AIMessage(content=greeting)],
        "decision_log": [entry(phase, decision.agent, "decision", f"Routed to {decision.next}: {decision.reason}")],
    }


def route_edge(state: BmadState) -> str:
    """Conditional-edge selector: reads the field ``orchestrator`` just set."""
    return state.get("route", "end")
