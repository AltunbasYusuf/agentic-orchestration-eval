"""Port of ``bmad-build`` (Amelia): the spec lifecycle that turns a request
into implemented, reviewed code.

BMAD implements this as five step-files rendered in sequence
(clarify-and-route, plan, implement, review, present) with loopback edges
between plan/implement/review capped at 5 iterations. This port keeps that
exact lifecycle and cap but runs it as one Python state machine inside a
single graph node rather than five separate graph nodes -- the loopback
logic (which BMAD's own docs describe as step files re-rendering each
other) is simpler to keep correct as a bounded ``for`` loop than as graph
edges with a manual iteration counter. The externally visible contract is
identical: a ``spec`` dict whose ``status`` field is the same state machine
BMAD's frontmatter drives (draft -> ready-for-dev -> in-progress ->
in-review -> done), persisted in graph state so a resumed thread continues
from wherever it stopped.

The one interrupt in the default path is BMAD's "Checkpoint 1" (approve
the plan before code gets written). The oneshot route (small, reversible,
unambiguous changes) skips it, exactly like the source skill.

CAVEAT (LangGraph node-replay semantics): when a node calls ``interrupt()``
and is later resumed, LangGraph re-runs the *entire node function* from the
top -- earlier ``interrupt()`` calls in that run just return their cached
answer immediately, but any LLM calls or tool calls before/between them
run again. Because this node does its planning and implementation work
inline around two interrupt points, resuming after either one re-invokes
the planner and (if past Checkpoint 1) the coding agent again. For a
demo/single-user tool this is a cost/latency trade-off, not a correctness
bug -- but for production use, split ``clarify_and_route`` / ``plan`` /
``implement`` / ``review`` / ``present`` into five separate graph nodes
(edges instead of a Python loop) so replay only re-enters the node that
was actually interrupted. See the README's "Extending" section.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import interrupt

from ..artifacts import (
    implementation_dir,
    read_workspace_diff,
    slugify,
    today,
    with_frontmatter,
    workspace_dir,
    write_markdown,
)
from ..config import settings
from ..llm import get_llm, get_structured_llm
from ..memlog import entry
from ..personas import AMELIA, system_prompt
from ..schemas import OneshotDecision, SpecPlan
from ..state import BmadState
from ..tools import make_coding_tools
from .review_layers import run_review

PLAN_TASK = """Plan a single-goal implementation spec for this request.
One user-facing goal only -- if the request bundles several, cover just
the first and note the rest as follow-up in `open_questions`.

Fill every field: `problem`/`approach` (what and why), `always`/`never`
(hard boundaries), an `io_matrix` covering the edge cases that matter,
`open_questions` for anything genuinely undecided, a `code_map` of the
files you expect to touch and why, ordered `tasks`, Given/When/Then
`acceptance` criteria, and `verification_commands` to prove it works
(e.g. a test runner invocation).
"""

ONESHOT_TASK = """Judge whether this request is small enough to implement
directly without a full plan/checkpoint cycle: no ambiguous intent, no
irreversible action (schema/data migration, deleting user data, public
API change), small footprint (roughly one file or a tightly related few).
"""

IMPLEMENT_TASK = """Implement the tasks below against the project
workspace using your tools (write_file, read_file, list_files,
run_command). Work through tasks in order. Use run_command to run the
verification commands from the spec once you believe you are done, and
fix anything that fails before finishing. When finished, reply with a
short summary of what you changed and the verification result -- do not
add commentary about the process itself."""


def _new_spec(request: str) -> dict:
    return {
        "title": request[:80],
        "type": "feature",
        "created": today(),
        "status": "draft",
        "route": None,
        "review_loop_iteration": 0,
        "context": [],
    }


def _plan(spec: dict, state: BmadState) -> dict:
    context_parts = [f"Request: {state.get('human_input') or spec['title']}"]
    for label, key in (("PRD", "prd"), ("Architecture spine", "architecture_spine"), ("Epics & stories", "epics_markdown")):
        if state.get(key):
            context_parts.append(f"{label}:\n{state[key]}")
    context = "\n\n".join(context_parts)

    oneshot_llm = get_structured_llm(OneshotDecision)
    oneshot: OneshotDecision = oneshot_llm.invoke([SystemMessage(content=ONESHOT_TASK), HumanMessage(content=context)])

    planner = get_structured_llm(SpecPlan, temperature=0.3)
    plan: SpecPlan = planner.invoke([SystemMessage(content=PLAN_TASK), HumanMessage(content=context)])

    spec.update(
        route="oneshot" if oneshot.oneshot else "dispatch",
        intent={"problem": plan.problem, "approach": plan.approach},
        boundaries={"always": plan.always, "never": plan.never},
        io_matrix=[row.model_dump() for row in plan.io_matrix],
        open_questions=plan.open_questions,
        code_map=plan.code_map,
        tasks=plan.tasks,
        acceptance=plan.acceptance,
        verification_commands=plan.verification_commands,
        implementation_notes=[],
        spec_change_log=[],
        review_triage_log=[],
        status="ready-for-dev",
    )
    return spec


def _bulleted(items: list[str], empty: str = "(none)") -> list[str]:
    """List a section's bullets, materialized eagerly so an empty list falls
    back to `empty` -- a generator's truthiness would otherwise ignore the
    fallback even when it yields nothing."""
    rendered = [f"- {item}" for item in items]
    return rendered or [empty]


def _render_spec_markdown(spec: dict) -> str:
    lines: list[str] = []
    lines.append(f"## Intent\n\n**Problem:** {spec['intent']['problem']}\n\n**Approach:** {spec['intent']['approach']}\n")

    lines.append("## Boundaries & Constraints\n")
    lines.append("**Always:**")
    lines.extend(_bulleted(spec["boundaries"]["always"], "(none recorded)"))
    lines.append("\n**Never:**")
    lines.extend(_bulleted(spec["boundaries"]["never"], "(none recorded)"))

    lines.append("\n## I/O & Edge-Case Matrix\n")
    lines.append("| Scenario | Input/State | Expected | Error Handling |")
    lines.append("| --- | --- | --- | --- |")
    for r in spec["io_matrix"]:
        lines.append(f"| {r['scenario']} | {r['input_state']} | {r['expected']} | {r['error_handling']} |")

    lines.append("\n## Open Questions\n")
    lines.extend(_bulleted(spec["open_questions"]))

    lines.append("\n## Code Map\n")
    lines.extend(_bulleted([f"`{f}`: {role}" for f, role in spec["code_map"].items()]))

    lines.append("\n## Tasks & Acceptance\n")
    lines.append("**Tasks:**")
    lines.extend(_bulleted(spec["tasks"], "(none)"))
    lines.append("\n**Acceptance Criteria:**")
    lines.extend(_bulleted(spec["acceptance"], "(none)"))

    lines.append("\n## Implementation Notes\n")
    lines.extend(spec.get("implementation_notes") or ["(pending)"])

    lines.append("\n## Review Triage Log\n")
    lines.extend(spec.get("review_triage_log") or ["(pending)"])

    lines.append("\n## Verification\n")
    lines.extend(_bulleted([f"`{c}`" for c in spec["verification_commands"]], "(none specified)"))

    return "\n".join(str(line) for line in lines)


def _implement(spec: dict, tools: list, feedback: str | None = None) -> str:
    agent = create_react_agent(get_llm(temperature=0.2), tools)
    instructions = IMPLEMENT_TASK + "\n\nTasks:\n" + "\n".join(f"- {t}" for t in spec["tasks"])
    if feedback:
        instructions += f"\n\nAddress this review feedback too:\n{feedback}"
    result = agent.invoke(
        {"messages": [SystemMessage(content=system_prompt(AMELIA, instructions))]},
        {"recursion_limit": 25},
    )
    return result["messages"][-1].content


def _layer_set(route: str) -> tuple[str, ...]:
    base = ("blind_hunter", "edge_case_hunter", "verification_gap")
    return (*base, "acceptance_auditor") if route == "dispatch" else base


def build(state: BmadState) -> dict:
    request = state.get("human_input") or "Implement the next ready story."
    spec = state.get("spec")
    resuming_in_review = bool(spec) and spec.get("status") not in (None, "draft", "done")
    if not spec or spec.get("status") == "done":
        spec = _new_spec(request)
    decision_log = []

    if spec["status"] == "draft":
        spec = _plan(spec, state)
        decision_log.append(entry("implementation", "amelia", "decision", f"Planned as route={spec['route']}"))

        if spec["route"] == "dispatch":
            answer = interrupt(
                {
                    "agent": "amelia",
                    "question": (
                        "Checkpoint 1 -- spec ready for review:\n\n"
                        + _render_spec_markdown(spec)
                        + "\n\nReply 'continue' to implement, 'stop' to pause here, "
                        "or describe changes to the plan."
                    ),
                }
            )
            answer_norm = str(answer).strip().lower()
            if answer_norm in ("stop", "pause"):
                path = write_markdown(
                    Path(implementation_dir(state["output_dir"])) / f"spec-{slugify(spec['title'])}.md",
                    with_frontmatter({k: spec[k] for k in ("title", "type", "created", "status", "route")}, _render_spec_markdown(spec)),
                )
                return {
                    "spec": spec,
                    "spec_markdown": _render_spec_markdown(spec),
                    "messages": [AIMessage(content=f"{AMELIA.icon} Spec saved at {path}, paused before implementation.")],
                    "decision_log": decision_log,
                }
            if answer_norm not in ("continue", "yes", "go", "approve"):
                spec = _plan({**spec, "status": "draft"}, {**state, "human_input": f"{request}\n\nRevision requested: {answer}"})
                decision_log.append(entry("implementation", "amelia", "decision", "Revised plan per human feedback"))

    workspace = workspace_dir(state["output_dir"])
    tools = make_coding_tools(workspace)
    bucket_options = (
        ["intent_gap", "bad_spec", "patch", "defer"] if spec["route"] == "dispatch" else ["patch", "defer", "decision_needed"]
    )

    # A follow-up human turn on an already in-progress/in-review spec (as
    # opposed to a brand-new spec's first implement pass) carries its
    # instructions in state.human_input -- feed those in as the first
    # iteration's feedback, or they'd otherwise never reach _implement().
    feedback = state.get("human_input") if resuming_in_review else None
    deferred: list[str] = list(spec.get("deferred") or [])
    # Findings the review layers must stop re-raising: prior "defer" verdicts
    # and, more importantly, whatever a human actually decided at a
    # decision_needed interrupt. Without this, run_review() re-derives
    # findings from scratch every iteration with no memory of earlier
    # rounds -- including rounds from a *previous* build() call on the same
    # spec -- so the loop never converges even when a human keeps accepting
    # the same tradeoff. Seeded from spec so it survives across separate
    # build() invocations on the same in-review spec, not just this call's loop.
    accepted_notes: list[str] = list(spec.get("accepted_decisions") or [])
    for iteration in range(1, settings.review_loop_cap + 1):
        spec["status"] = "in-progress"
        notes = _implement(spec, tools, feedback)
        spec.setdefault("implementation_notes", []).append(f"Iteration {iteration}: {notes}")

        spec["status"] = "in-review"
        diff_text = read_workspace_diff(workspace)
        acceptance_text = "\n".join(spec["acceptance"])
        accepted_context = "\n".join(f"- {n}" for n in accepted_notes) or None
        findings = run_review(
            diff_text,
            list(_layer_set(spec["route"])),
            bucket_options,
            spec_context=acceptance_text,
            accepted_context=accepted_context,
        )
        spec["review_loop_iteration"] = iteration

        blocking = [f for f in findings if f["bucket"] in ("intent_gap", "bad_spec", "decision_needed")]
        patchable = [f for f in findings if f["bucket"] == "patch"]
        newly_deferred = [f["summary"] for f in findings if f["bucket"] == "defer"]
        deferred += newly_deferred
        accepted_notes += newly_deferred
        spec["accepted_decisions"] = accepted_notes

        for f in findings:
            spec.setdefault("review_triage_log", []).append(f"[{f['bucket']}/{f['verdict']}] {f['summary']}")

        if not blocking and not patchable:
            spec["status"] = "done"
            break

        if blocking:
            joined = "\n".join(f"- ({b['bucket']}) {b['summary']}" for b in blocking)
            answer = interrupt(
                {
                    "agent": "amelia",
                    "question": f"Review found issues needing a decision:\n{joined}\n\nHow should I proceed?",
                }
            )
            accepted_notes.append(f"Decided: {joined}\n  Human's answer: {answer}")
            spec["accepted_decisions"] = accepted_notes
            feedback = f"{answer}\n" + "\n".join(f"- {p['summary']}" for p in patchable)
        else:
            feedback = "\n".join(f"- {p['summary']}" for p in patchable)
    else:
        deferred.append(f"Review loop hit the {settings.review_loop_cap}-iteration cap; remaining findings need human follow-up.")
        spec["status"] = "in-review"

    spec["deferred"] = deferred
    story_status = "review" if spec["status"] == "done" else spec["status"]

    spec_markdown = _render_spec_markdown(spec)
    path = write_markdown(
        Path(implementation_dir(state["output_dir"])) / f"spec-{slugify(spec['title'])}.md",
        with_frontmatter({k: spec[k] for k in ("title", "type", "created", "status", "route")}, spec_markdown),
    )

    sprint_status = state.get("sprint_status")
    story_key = state.get("current_story_key")
    if sprint_status and story_key and story_key in sprint_status.get("development_status", {}):
        sprint_status["development_status"][story_key] = story_status

    decision_log.append(entry("implementation", "amelia", "artifact", f"Spec {spec['status']} at {path}"))
    summary = f"{AMELIA.icon} Build finished with status **{spec['status']}** (route={spec['route']}). Spec: {path}."
    if deferred:
        summary += f"\nDeferred: {len(deferred)} item(s) -- see deferred-work notes."

    return {
        "spec": spec,
        "spec_markdown": spec_markdown,
        "sprint_status": sprint_status,
        "deferred_work": deferred,
        "messages": [AIMessage(content=summary)],
        "decision_log": decision_log,
    }
