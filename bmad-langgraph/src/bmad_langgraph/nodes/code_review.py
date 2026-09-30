"""Port of ``bmad-code-review`` (Amelia), standalone from ``build``.

Same review-layer subgraph as ``build``'s step-04, but usable on its own --
BMAD supports invoking a review independent of an active spec ("no-spec
mode"). Buckets differ slightly from ``build``'s (``decision_needed``
instead of the split ``intent_gap``/``bad_spec``) matching the source
skill's own bucket set for this workflow.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from ..artifacts import implementation_dir, read_workspace_diff, workspace_dir, write_markdown
from ..memlog import entry
from ..personas import AMELIA
from ..state import BmadState
from .review_layers import run_review

BUCKET_OPTIONS = ["decision_needed", "patch", "defer"]


def code_review(state: BmadState) -> dict:
    workspace = workspace_dir(state["output_dir"])
    diff_text = read_workspace_diff(workspace)
    if diff_text.startswith("(no files"):
        return {
            "messages": [AIMessage(content=f"{AMELIA.icon} Nothing in the workspace to review yet -- run `build` first.")],
            "decision_log": [entry("implementation", "amelia", "note", "code_review: empty workspace")],
        }

    spec = state.get("spec")
    review_mode = "full" if spec and spec.get("acceptance") else "no-spec"
    layers = ["blind_hunter", "edge_case_hunter", "verification_gap"]
    spec_context = None
    if review_mode == "full":
        layers.append("acceptance_auditor")
        spec_context = "\n".join(spec["acceptance"])

    findings = run_review(diff_text, layers, BUCKET_OPTIONS, spec_context=spec_context)

    if not findings:
        return {
            "messages": [AIMessage(content=f"{AMELIA.icon} ✅ Clean review -- no findings across {len(layers)} layers.")],
            "decision_log": [entry("implementation", "amelia", "gate", "Code review: clean")],
        }

    decision_needed = [f for f in findings if f["bucket"] == "decision_needed"]
    patch = [f for f in findings if f["bucket"] == "patch"]
    defer = [f for f in findings if f["bucket"] == "defer"]

    if decision_needed:
        joined = "\n".join(f"- {f['summary']}" for f in decision_needed)
        interrupt(
            {
                "agent": "amelia",
                "question": f"Code review found {len(decision_needed)} item(s) needing a decision:\n{joined}",
            }
        )

    report_lines = ["# Code Review Findings\n"]
    for label, bucket in (("Needs a decision", decision_needed), ("Patch", patch), ("Deferred", defer)):
        if bucket:
            report_lines.append(f"## {label}\n")
            report_lines.extend(f"- ({f['layer']}/{f['severity']}) {f['summary']}" for f in bucket)
            report_lines.append("")
    report = "\n".join(report_lines)

    path = write_markdown(Path(implementation_dir(state["output_dir"])) / "code-review-findings.md", report)

    sprint_status = state.get("sprint_status")
    story_key = state.get("current_story_key")
    new_story_status = "in-progress" if (decision_needed or patch) else "done"
    if sprint_status and story_key and story_key in sprint_status.get("development_status", {}):
        sprint_status["development_status"][story_key] = new_story_status

    return {
        "sprint_status": sprint_status,
        "deferred_work": [f["summary"] for f in defer],
        "messages": [
            AIMessage(
                content=(
                    f"{AMELIA.icon} Review done: {len(decision_needed)} decision-needed, "
                    f"{len(patch)} patch, {len(defer)} deferred. Findings at {path}."
                )
            )
        ],
        "decision_log": [entry("implementation", "amelia", "gate", f"Code review: {len(findings)} findings")],
    }
