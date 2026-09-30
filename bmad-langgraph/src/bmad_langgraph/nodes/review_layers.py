"""Shared review-layer subgraph, used by both ``build`` (step-04-review)
and ``code_review``.

BMAD runs each review layer as a parallel subagent over the same diff and
then triages the combined findings. That is a textbook LangGraph
map-reduce: a dispatch node fans out one ``Send`` per active layer, each
runs independently, and their ``findings`` land in the same reducer-backed
list for the triage node to read. This is one compiled subgraph invoked
with ``.invoke()`` from the parent node rather than wired into the main
graph, so it can be reused unchanged by both callers with different
``bucket_options``/layer sets.
"""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from ..llm import get_structured_llm
from ..schemas import ReviewLayerOutput


def _append(existing: list | None, new: list | None) -> list:
    return [*(existing or []), *(new or [])]


class ReviewState(TypedDict, total=False):
    diff_text: str
    spec_context: str | None
    accepted_context: str | None
    active_layers: list[str]
    bucket_options: list[str]
    layer: str  # set per-branch by Send
    findings: Annotated[list[dict], _append]


LAYER_PROMPTS: dict[str, str] = {
    "blind_hunter": (
        "You are the Blind Hunter. You get no spec, no story, no claims -- only "
        "the raw diff/artifact. Read it cold and list every issue that looks "
        "wrong on its own merits: unclear naming, dead code, inconsistent "
        "error handling, missing null/empty checks, anything a reviewer with "
        "zero context would flag. Aim for at least a handful of findings; "
        "shallow review defeats the point of this layer."
    ),
    "edge_case_hunter": (
        "You are the Edge Case Hunter. Given the diff/artifact, enumerate "
        "inputs and states the implementation likely mishandles: empty/null/"
        "huge inputs, concurrent access, partial failure, boundary values, "
        "unicode/encoding, retries and idempotency. For each, state whether "
        "the code visibly handles it or not."
    ),
    "verification_gap": (
        "You are the Verification Gap Reviewer. Compare what the commit "
        "message / claims say was done against what the diff actually shows. "
        "Flag any claim ('added tests', 'handles X') that the diff does not "
        "substantiate, and any acceptance criterion implied but not covered "
        "by a visible test."
    ),
    "acceptance_auditor": (
        "You are the Acceptance Auditor. You are given the spec's acceptance "
        "criteria and constraints alongside the diff. Check each acceptance "
        "criterion off as met/not-met against the actual diff, and flag any "
        "constraint ('Always'/'Never' boundaries) the diff violates."
    ),
}


def _run_layer(state: ReviewState) -> dict:
    layer = state["layer"]
    bucket_options = state.get("bucket_options", ["patch", "defer"])
    llm = get_structured_llm(ReviewLayerOutput, temperature=0.3)
    system = (
        LAYER_PROMPTS[layer]
        + "\n\nFor each finding, set `bucket` to one of: " + ", ".join(bucket_options) + "."
        + " Use verdict 'false' for anything you convinced yourself is not "
        "actually a problem after considering it -- do not include those as findings."
    )
    context = f"Diff / artifact under review:\n{state['diff_text']}"
    if state.get("spec_context"):
        context += f"\n\nSpec / acceptance criteria:\n{state['spec_context']}"
    if state.get("accepted_context"):
        context += (
            "\n\nThe following points have already been explicitly decided or "
            "accepted by a human reviewer in a prior round. Do NOT raise them "
            "again as findings, even if you would otherwise notice them -- "
            "only raise them if the diff now contradicts the human's actual "
            f"decision:\n{state['accepted_context']}"
        )

    result: ReviewLayerOutput = llm.invoke([SystemMessage(content=system), HumanMessage(content=context)])
    findings = [{**f.model_dump(), "layer": layer} for f in result.findings if f.verdict != "false"]
    return {"findings": findings}


def _dispatch(state: ReviewState) -> list[Send]:
    return [
        Send(
            "run_layer",
            {
                "layer": layer,
                "diff_text": state["diff_text"],
                "spec_context": state.get("spec_context"),
                "accepted_context": state.get("accepted_context"),
                "bucket_options": state.get("bucket_options", ["patch", "defer"]),
            },
        )
        for layer in state.get("active_layers", ["blind_hunter"])
    ]


def _triage(state: ReviewState) -> dict:
    return {"findings": state.get("findings", [])}


def _build_review_graph():
    builder = StateGraph(ReviewState)
    builder.add_node("run_layer", _run_layer)
    builder.add_node("triage", _triage)
    builder.add_conditional_edges(START, _dispatch, ["run_layer"])
    builder.add_edge("run_layer", "triage")
    builder.add_edge("triage", END)
    return builder.compile()


review_layers_graph = _build_review_graph()


def run_review(
    diff_text: str,
    active_layers: list[str],
    bucket_options: list[str],
    spec_context: str | None = None,
    accepted_context: str | None = None,
) -> list[dict]:
    """Convenience wrapper: run the subgraph, return the flat findings list.

    ``accepted_context`` is prior human decisions/deferrals the caller wants
    the layers to respect instead of re-raising -- see ``build.py``'s
    ``accepted_notes`` accumulator, which is what actually closes the loop
    (this function is stateless; the caller owns the memory)."""
    result = review_layers_graph.invoke(
        {
            "diff_text": diff_text,
            "spec_context": spec_context,
            "accepted_context": accepted_context,
            "active_layers": active_layers,
            "bucket_options": bucket_options,
        }
    )
    return result.get("findings", [])
