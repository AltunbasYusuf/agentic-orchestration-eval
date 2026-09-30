# BMAD Agents vs. Plain Claude: A Tetris Case Study

Same small spec — *"a simple, self-contained, browser-based, single-player
Tetris with arrow-key controls, line clearing, score, increasing speed, and
game over/restart"* — built three different ways, to see whether the
[BMAD-METHOD](https://github.com/bmad-code-org/BMAD-METHOD) multi-agent
process actually changes the outcome, and whether porting it from
Claude-Code skills to a custom LangGraph orchestrator changes it further.

| | What it is | Process run for this test | Output |
| --- | --- | --- | --- |
| **A. [`bmad-standalone/`](bmad-standalone)** | BMAD-METHOD v6.12.0 installed as native Claude Code skills — five personas (Mary/John/Winston/Sally/Amelia) driving prose-based workflow files | Full pipeline: brief → PRD → architecture → UX → epics → 8 stories, each built and reviewed individually | [`results/bmad-standalone-tetris.html`](results/bmad-standalone-tetris.html) |
| **B. [`bmad-langgraph/`](bmad-langgraph)** | A custom Python port of the same BMAD personas/workflows into a stateful [LangGraph](https://github.com/langchain-ai/langgraph) `StateGraph`, with real conditional-edge gates instead of prose conventions | Routed directly to the `build` node for one request; its internal classifier judged the task small enough to skip the plan-approval checkpoint (BMAD's own "oneshot" path) — see [caveat](#caveat-the-langgraph-run-isnt-a-full-pipeline-run) | [`results/bmad-langgraph-tetris/`](results/bmad-langgraph-tetris) |
| **C. Plain Claude (web)** | A single message to a plain claude.ai chat — no agents, no skills, no framework | None — one request, one response | [`results/claude-web-tetris.html`](results/claude-web-tetris.html) |

All three were given equivalent framing of the same request and nothing
else (no shared code, no cross-contamination). (C) is the control: it shows
what "just ask the model" produces with zero process on top.

## Process & artifacts

| | A. bmad-standalone | B. bmad-langgraph | C. claude-web |
| --- | --- | --- | --- |
| Orchestration | Prose skill files + human-in-the-loop steps, run by Claude Code | [`orchestrator.py`](bmad-langgraph/src/bmad_langgraph/nodes/orchestrator.py): structured-output router + conditional graph edges | None |
| Phases actually run | Brief → PRD → Architecture → UX → Epics → 8 stories (each: spec → implement → review) | `build` only (oneshot path) | None |
| Planning artifacts produced | **22** files — brief, PRD, architecture spine (9 numbered architecture decisions), `DESIGN.md`, `EXPERIENCE.md`, epics, 8 per-story specs, `sprint-status.yaml`, 3 architecture review reports | **1** file — a single spec ([`runs/langgraph/implementation/spec-....md`](runs/langgraph/implementation)) | 0 |
| Gates | Prose convention — the model grades itself (e.g. a "Blind Hunter" adversarial review pass) | Real conditional edges: `QualityGrade` structured output, deterministic `lint_spine()`, review-triage buckets — see [bmad-langgraph's README](bmad-langgraph/README.md#gates) | None |
| Self-documented known gaps | Yes — [`deferred-work.md`](bmad-standalone/_bmad-output/implementation-artifacts/deferred-work.md) logs 3 evidence-backed gaps (e.g. no HiDPI canvas scaling) with why each was deferred | Not tracked (oneshot build has no deferred-work ledger) | Not tracked |
| Session resumability | Files on disk, re-readable by a fresh session | LangGraph checkpointer keyed by `thread_id` (swappable for a durable store) | None — stateless chat |
| Final code | 1 file, 883 lines / 30.6 KB | 3 files, 614 lines / 15.5 KB | 1 file, 614 lines / 16 KB |

### Caveat: the langgraph run isn't a full-pipeline run

`bmad-langgraph` implements the *same* 11 BMAD workflows as the standalone
skills, including the full brief → PRD → architecture → UX → epics →
sprint-planning pipeline with real quality gates (see its own
[README](bmad-langgraph/README.md)). For this particular test, though, the
request was routed straight to `build`, and `build`'s own oneshot-classifier
decided the task was small/reversible/unambiguous enough to skip the
plan-approval interrupt — exactly mirroring what the source BMAD skill would
do for a task this size. So column B here measures *"BMAD-on-LangGraph's
fast path,"* not *"BMAD-on-LangGraph's full ceremony."* A fair apples-to-apples
run would drive B through the same brief→...→epics pipeline A went through;
that's a natural follow-up, not something this snapshot claims to have done.

## Feature matrix (from reading each game's code)

| Feature | A. bmad-standalone | B. bmad-langgraph | C. claude-web |
| --- | --- | --- | --- |
| Rotation wall-kick | None — blocked outright | ±1 column | ±1, ±2 columns |
| Piece randomizer | Pure random per spawn (explicitly left unfixed — Architecture Decision AD-5) | 7-bag shuffle | 7-bag shuffle |
| Next-piece preview | Yes | No | Yes |
| Ghost piece (landing preview) | No | No | Yes |
| Soft-drop scoring | No | No | Yes (+1/row) |
| Hard drop (Space) | Yes | Yes | Yes |
| Pause | `P` key | Automatic only (window blur / tab visibility) | `P` key + on-screen button |
| Restart | `R` key | Button only | Button, or Space on game-over |
| Mobile / touch controls | No | No | Yes (on-screen d-pad, `pointer: coarse` media query) |
| Theming | Fixed dark "terminal" palette (CSS custom-property design tokens) | Fixed dark palette | Light/dark via `prefers-color-scheme`, responsive canvas sizing |
| UI language | English | English | Turkish |
| HiDPI canvas scaling | No — documented gap, see `deferred-work.md` | No | No |

All three pass a manual/static read for the core mechanics: collision
detection, gravity-correct line clearing (rows above a cleared line shift
down, rows below are untouched), the standard 100/300/500/800 × level
scoring table, and game-over on blocked spawn.

## Observations (n=1, anecdotal — not a controlled study)

- **The heaviest process was the most conservative, and the most honest
  about it.** bmad-standalone's output tracks its spec almost literally —
  no wall-kick, no ghost piece, no bag randomizer — because none of those
  were explicitly requested, and every place it consciously cut a corner
  (HiDPI scaling, the randomizer algorithm) is logged with a reason in
  `deferred-work.md` / the architecture spine, not silently missing.
- **Zero process didn't mean low quality here.** The plain claude-web
  chat — no PRD, no review gate, no persona — shipped the most
  feature-complete build of the three: ghost piece, mobile touch controls,
  soft-drop scoring, responsive light/dark theming. Tetris is a
  well-known, well-scoped problem the model has almost certainly seen many
  reference implementations of; that's likely doing a lot of the work
  process would otherwise need to do for a less-common spec.
- **B vs. A is not yet a fair comparison** — see the caveat above. What B
  does demonstrate is that moving BMAD's gates from prose convention to
  real structured-output branches and conditional edges is mechanically
  sound (its wall-kick and 7-bag randomizer, done with no spec asking for
  either, suggest the underlying model defaults leaked through the thinner
  process rather than any real gap in the LangGraph port).
- Bag-randomizer vs. pure-random is the most concrete functional delta
  across all three: A explicitly deferred picking one; B and C both landed
  on the standard 7-bag shuffle unprompted.

## Repository layout

```
bmad-standalone/     BMAD-METHOD v6.12.0 running as native Claude Code skills
  .agents/skills/      the installed skill pack (personas, workflows, templates)
  _bmad-output/        every planning + implementation artifact from this run
  tetris.html          final game (source of results/bmad-standalone-tetris.html)

bmad-langgraph/      Custom LangGraph port of the same BMAD personas/workflows
  src/bmad_langgraph/  graph, nodes, personas, schemas — see its own README
  README.md            architecture deep-dive: BMAD concept -> LangGraph equivalent

runs/langgraph/      A captured run of bmad-langgraph (spec + generated workspace)
  implementation/       source of results/bmad-langgraph-tetris/

results/             The three final games, side by side, ready to open directly
  bmad-standalone-tetris.html
  bmad-langgraph-tetris/  (index.html, script.js, style.css)
  claude-web-tetris.html
```

## Reproducing

- **A (standalone):** the full trail is already in
  `bmad-standalone/_bmad-output/` — read it phase by phase starting at
  `planning-artifacts/briefs/`.
- **B (langgraph):** see [`bmad-langgraph/README.md`](bmad-langgraph/README.md)
  for setup (`uv sync`, `.env`) and how to drive it through the full
  pipeline instead of straight to `build`.
- **C (claude-web):** no setup — it's a single prompt to claude.ai asking
  for the same spec described at the top of this file.
