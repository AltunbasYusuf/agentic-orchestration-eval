# BMad Method on LangGraph

A port of [BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD)'s
analyst → PM → architect → UX designer → dev pipeline from Claude-Code
"skill" prompts to a single, stateful, resumable **LangGraph**
`StateGraph`.

The source project (in `../Bmad` next to this folder) is a set of markdown
prompt files an AI coding assistant reads to role-play five personas —
Mary (Analyst), John (PM), Winston (Architect), Sally (UX Designer), Amelia
(Dev) — through four delivery phases: Analysis → Planning → Solutioning →
Implementation. Every phase produces a document the next phase consumes
(brief → PRD → architecture → epics/stories → code), and "gates" between
phases (a PRD review grade, an implementation-readiness check, a code
review triage, a retrospective verdict) are conventions the model is
trusted to follow correctly in prose.

This port keeps the personas, the documents, and the phase order, but
moves the parts that were prose convention into things LangGraph can
actually enforce:

| BMAD concept | This port |
| --- | --- |
| A skill file the assistant reads on activation | A node function in [`nodes/`](src/bmad_langgraph/nodes) |
| Agent persona (`customize.toml`: role/identity/style/principles) | [`personas.py`](src/bmad_langgraph/personas.py) — transcribed verbatim, used to build each node's system prompt |
| Agent menu (`BP`, `CB`, `PRD`, `CA`, `BD`, ...) | The [`orchestrator`](src/bmad_langgraph/nodes/orchestrator.py) node — a structured-output router with a conditional edge per menu item |
| `.memlog.md` append-only decision log | `state["decision_log"]`, a reducer-backed list riding on the LangGraph checkpointer |
| "Stop and wait for input" / elicitation | [`langgraph.types.interrupt`](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/) |
| A rubric the model grades itself against in prose (PASS/CONCERNS/FAIL, Excellent/Good/Fair/Poor) | A `pydantic` schema in [`schemas.py`](src/bmad_langgraph/schemas.py) consumed via `.with_structured_output(...)`, branching a real conditional edge |
| Parallel "review layer" subagents | A `Send`-based map-reduce subgraph, [`nodes/review_layers.py`](src/bmad_langgraph/nodes/review_layers.py) |
| Session resume via files on disk | Thread-scoped state via the LangGraph checkpointer (swap `MemorySaver` for `SqliteSaver`/`PostgresSaver` for durability across restarts) |
| BMAD's own filesystem output (`{planning_artifacts}`, `{implementation_artifacts}`) | `{output_dir}/planning/` and `{output_dir}/implementation/`, see [Output layout](#output-layout) |

If you already know BMAD, the fastest way to read this codebase is the
table above plus the module docstring at the top of each file in `nodes/`
— every one opens by naming exactly which BMAD skill it ports and what,
if anything, was simplified.

## Scope

This port implements the 11 workflows that make up BMAD's core delivery
spine (see the source repo's `docs/cs/reference/workflow-map.md`):

- **Phase 1 — Analysis (optional):** `brainstorming`, `product_brief`
- **Phase 2 — Planning:** `prd`, `ux`
- **Phase 3 — Solutioning:** `architecture`, `epics_stories`, `sprint_planning`
- **Phase 4 — Implementation:** `build`, `code_review`, `retrospective`, `correct_course`

Peripheral BMAD workflows (deep-recon, PRFAQ, party-mode, project-context,
QA/E2E test generation, the brainstorming HTML "keepsake", advanced
elicitation techniques) are not ported — the [Extending](#extending) section
below shows where to add them following the same pattern.

## Installation

Requires Python ≥3.11 and an Anthropic API key (or another
[`init_chat_model`](https://python.langchain.com/docs/how_to/chat_models_universal_init/)-supported
provider).

```bash
cd Bmad-Langgraph
uv sync                        # or: pip install -e .
cp .env.example .env           # then fill in ANTHROPIC_API_KEY
```

`.env` (see `.env.example`):

```bash
ANTHROPIC_API_KEY=sk-ant-...
BMAD_MODEL=anthropic:claude-sonnet-5     # any init_chat_model string
BMAD_OUTPUT_DIR=./_bmad-output
```

### Troubleshooting: `ModuleNotFoundError: No module named 'bmad_langgraph'`

If this happens right after `uv sync`/`pip install -e .` even though the
install reported success, it's almost always a non-ASCII character
somewhere in the project's path (e.g. a folder named "Yeni klasör")
combined with a non-UTF-8 system codepage (e.g. Turkish Windows' cp1254):
the editable-install `.pth` file is UTF-8, but the interpreter's `site`
module can read `.pth` files using the OS codepage, so the entry silently
fails to load. Confirmed on this exact setup during development. Workarounds,
easiest first:

1. Run with `PYTHONPATH` set explicitly: `PYTHONPATH=src uv run bmad-langgraph` (bash) or `$env:PYTHONPATH="src"; uv run bmad-langgraph` (PowerShell).
2. Switch the OS/terminal codepage to UTF-8 (`chcp 65001` in `cmd`/PowerShell) before creating the venv.
3. Move the project to a path with only ASCII characters.

## Quick start

```bash
uv run bmad-langgraph
# or: uv run python -m bmad_langgraph
```

```
BMad Method on LangGraph
Project name: receipt-budgeter
What are we building? (one line is enough) A tool that turns a grocery
receipt photo into a categorized budget entry.

thread id: 7f2a1e3c-... -- pass this to resume later

📊 Mary: Let's ground this in a quick brainstorm before locking scope...
(agent) Before we brainstorm 'receipt photo budgeting': any constraint or
goal I should aim ideas at (audience, timeframe, must-avoid)? Say 'none' to skip.
> none
📊 Brainstorming report written to _bmad-output/planning/brainstorming-report.md.

[receipt-budgeter] > create the PRD
📋 John: Drafting the PRD from the brainstorming report...
...
```

From here, drive it the way you'd drive BMAD's agent menus — either name a
workflow directly ("design the architecture", "check implementation
readiness", "implement the receipt-parsing story", "run a retrospective on
epic 1"), or leave it open-ended and the orchestrator recommends the next
unmet phase, the same way `bmad-help` does. Type `status` anytime for a
one-line summary of what's been produced; `exit` to quit (the thread id
stays valid — see [Resuming a session](#resuming-a-session)).

See [`examples/run_sample_session.py`](examples/run_sample_session.py) for
a scripted, non-interactive walk through every phase (it answers every
`interrupt()` itself, so it's also the fastest way to smoke-test a fresh
setup end to end):

```bash
uv run python examples/run_sample_session.py
```

## How the graph is shaped

```
START -> orchestrator -> (conditional edge on state["route"]) -> one workflow node -> END
                              |
     brainstorming  product_brief  prd  ux  architecture  epics_stories
     sprint_planning  build  code_review  retrospective  correct_course
```

Every `graph.invoke()` call runs the orchestrator once and dispatches into
exactly one workflow node, which runs to completion or to an `interrupt()`.
This mirrors BMAD's own turn-taking: an agent responds, then waits. The
next human message starts a fresh `invoke()` from `orchestrator`, which
re-reads the accumulated state (which documents exist, which phase you're
in) and routes again — there is no separate "menu" data structure to keep
in sync, because the router is just another structured LLM call over the
current state.

Workflow nodes do not edge back to `orchestrator` themselves; the CLI (or
your own driver) closes that loop by calling `invoke()` again. If you're
embedding this graph in something else (a web backend, a Slack bot), your
driver plays the same role `cli.py` does — see
[`nodes/orchestrator.py`](src/bmad_langgraph/nodes/orchestrator.py) and
[`cli.py`](src/bmad_langgraph/cli.py) together for the full contract.

### Gates

Three real gates exist as conditional branches, not prose:

- **PRD / Architecture Reviewer Gate** (`prd.py`, `architecture.py`) — a
  `QualityGrade` structured call (Excellent/Good/Fair/Poor). Fair/Poor
  pauses on an `interrupt()` asking accept-as-is or revise.
  Architecture additionally runs a deterministic `lint_spine()` (no model
  call) for structural checks a linter should own outright: duplicate
  `AD-N` ids, missing Binds/Prevents/Rule fields, an unpinned `Stack`
  version, leftover placeholder text.
- **Sprint Planning readiness gate** (`sprint_planning.py`) — PASS
  generates `sprint-status.yaml`; CONCERNS asks whether to proceed anyway;
  FAIL stops outright. Missing PRD/epics short-circuits to FAIL before any
  model call — no point asking a model to grade documents that don't exist.
- **Review triage** (`review_layers.py`, used by `build` and
  `code_review`) — every finding gets a `bucket` (`intent_gap`/`bad_spec`/
  `patch`/`defer`, or `decision_needed`/`patch`/`defer` for standalone code
  review) that actually determines what happens next, not just a label in
  a report.

The **retrospective**'s core rule — an epic with unfinished stories cannot
be silently accepted, and a human's call always overrides the machine's —
is enforced in plain Python (`retrospective.py`) before any model is
consulted, rather than left to the model to remember under pressure.

### Human-in-the-loop

Every pause point uses
[`langgraph.types.interrupt`](https://langchain-ai.github.io/langgraph/concepts/human_in_the_loop/),
which suspends the run and returns control to the caller with the
interrupt's payload; you resume by invoking again with
`Command(resume=<your answer>)` against the same `thread_id`. `cli.py`'s
`_drain_interrupts` is a ~10-line reference implementation:

```python
result = graph.invoke(turn_input, config)
while "__interrupt__" in result:
    question = result["__interrupt__"][0].value["question"]
    answer = ask_the_user(question)
    result = graph.invoke(Command(resume=answer), config)
```

### Resuming a session

State lives in the checkpointer, keyed by `thread_id`. The default
`MemorySaver` only survives within one Python process. For a session that
survives a restart, swap it for a durable checkpointer:

```python
from langgraph.checkpoint.sqlite import SqliteSaver

with SqliteSaver.from_conn_string("bmad.sqlite") as checkpointer:
    graph = build_graph(checkpointer=checkpointer)
    # reuse the same thread_id across process runs to resume
```

(`langgraph-checkpoint-sqlite` isn't a dependency by default — add it with
`uv add langgraph-checkpoint-sqlite` if you want this.)

## Output layout

Mirrors BMAD's `{planning_artifacts}` / `{implementation_artifacts}` split:

```
{output_dir}/
  planning/
    brainstorming-report.md
    product-brief.md
    prd.md
    design.md                    # UX visual identity
    experience.md                # UX information architecture / flows
    architecture-spine.md
    epics.md
    sprint-status.yaml
    sprint-change-proposal-{date}.md
  implementation/
    spec-{slug}.md                # one per build() run; frontmatter status is the lifecycle state
    code-review-findings.md
    epic-{n}-retro-{date}.md
    workspace/                     # sandboxed root for build()'s coding tools -- see tools.py
```

## Extending

**Add a workflow node.** Copy the shape of an existing node in `nodes/`:
build a task prompt, call `get_llm()` or `get_structured_llm(YourSchema)`,
write the artifact via `artifacts.write_markdown`/`write_yaml`, return a
state-update dict (`messages`, `decision_log`, plus whatever fields the
artifact belongs in — add new fields to `state.py` if needed). Register it
in `graph.WORKFLOW_NODES` and give the orchestrator a reason to route to it
by adding it to the `Route` literal in `schemas.py` and mentioning it in
`orchestrator.ROUTING_PROMPT`.

**Add a persona.** Add a `Persona(...)` to `personas.py` (role/identity/
communication_style/principles, copied from a BMAD `customize.toml` if
you're porting one) and reference it from your new node's `system_prompt`.

**Split `build` into real graph nodes.** `build.py`'s docstring explains
why its five BMAD steps (clarify/plan/implement/review/present) currently
live inside one Python function with a bounded loop rather than as five
graph nodes: it's simpler to keep the loop-back/cap logic correct that
way, at the cost of re-running earlier steps when an `interrupt()` inside
it is resumed (LangGraph replays a node from the top on resume). For
production use, promote each step to its own node connected by real edges
so resuming only re-enters the step that paused.

**Swap the model or add a provider.** Change `BMAD_MODEL` in `.env` — it's
passed straight to `langchain.chat_models.init_chat_model`. Non-Anthropic
providers need their own `langchain-*` package installed
(e.g. `uv add langchain-openai` for `openai:gpt-4.1`).

**Use a Claude Code subscription instead of an API key.** Set
`BMAD_MODEL=claude-code:sonnet` (or `claude-code:opus`, or bare
`claude-code` for the CLI's default model) instead of an
`anthropic:...` string. This routes every model call through
[`claude_code_llm.ClaudeCodeChatModel`](src/bmad_langgraph/claude_code_llm.py),
which shells out to the `claude` CLI's headless mode (`claude -p
--output-format json`) rather than calling the Anthropic API directly —
so it's billed against a Claude Code / claude.ai subscription, not a
separate pay-per-token key, and needs no `ANTHROPIC_API_KEY` (just a
`claude` CLI that's already logged in). Every call is stateless
(`--no-session-persistence`); the model's `_generate` flattens the message
list into one prompt per call, since every node already builds its own
context string rather than relying on multi-turn session memory.
Structured-output gates (`RouteDecision`, `QualityGrade`, ...) use the
CLI's native `--json-schema` validation. `build.py`'s `create_react_agent`
coding loop (`bind_tools`) is emulated: each turn asks the model to pick
one bound tool or answer directly via a small routing JSON schema, which
gets translated into an `AIMessage.tool_calls` entry so LangGraph's
prebuilt `ToolNode` executes it like any other tool-calling model. All
three paths (plain generation, structured output, tool-calling loop) were
smoke-tested directly against `nodes/orchestrator.py`'s `RouteDecision`
call, `nodes/build.py`'s `SpecPlan` call, and its `_implement` tool loop.

## Known simplifications vs. the source BMAD skills

- **No live git integration.** `build`'s "diff" and `code_review`'s review
  target are approximated as "every file currently in
  `implementation/workspace/`" (`artifacts.read_workspace_diff`), not a
  real `git diff`. Point `workspace_dir` at a real checkout and swap that
  helper for an actual git call if you need this to be precise.
- **`build`'s coding tools are sandboxed and minimal** (`tools.py`:
  read/write/list file, run a shell command) rather than a full IDE tool
  surface. This is the intended extension point if you want it to do more.
- **Brainstorming** collapses BMAD's live, technique-by-technique
  facilitation + optional HTML "keepsake" into one pass plus a single
  clarifying `interrupt()`.
- **PRD's "adapt-in" section clusters** (enterprise/regulated/embedded
  product sections) are omitted from the default template; add them as
  extra instructions in `prd.DRAFT_TASK` if your project needs them.
- Everything under [Extending](#extending) is a deliberate seam, not a bug
  — the goal was a faithful, working core, not a byte-for-byte port of
  every BMAD reference file.

## Repository layout

```
pyproject.toml
.env.example
src/bmad_langgraph/
  config.py         Settings from environment variables
  state.py           BmadState -- the single object threaded through the graph
  schemas.py         Structured-output contracts for every gate/route decision
  personas.py         Mary/John/Winston/Amelia/Sally, transcribed from BMAD
  llm.py              Provider-agnostic model access (init_chat_model)
  artifacts.py         Filesystem layout + markdown/YAML/frontmatter helpers
  memlog.py            Decision-log helpers (the .memlog.md equivalent)
  tools.py              Sandboxed coding tools for build()'s implement step
  graph.py               Compiles the StateGraph
  cli.py                  Interactive driver
  nodes/
    orchestrator.py        Router (bmad-help + every agent menu, collapsed)
    brainstorming.py, product_brief.py, prd.py, ux.py, architecture.py,
    epics_stories.py, sprint_planning.py, build.py, code_review.py,
    retrospective.py, correct_course.py
    review_layers.py       Shared Send-based parallel review subgraph
examples/
  run_sample_session.py   Scripted, non-interactive full-pipeline demo
```
