---
title: 'Track Score and Level'
type: 'feature'
created: '2026-09-07'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

## Review Triage Log

- **medium, patch** — DESIGN.md's own Typography/Components prose named `heading` type for HUD labels (stated twice) while its YAML `hud-panel.labelType` token said `label-caps` — an internal inconsistency I introduced during the UX phase, followed literally when implementing. Fixed both the CSS and the source token to `heading`.
- **low, patch** — Stale comment on `FALL_INTERVAL` still said "Story 1.5 will scale this," even though 1.5 is the story doing it. Updated.
- **low, patch** — No `overflow-wrap` on `.hud-value`; scores have no cap. Added, trivial and free even though unlikely to matter at this project's realistic play-session length.
- **low, patch** — Score-vs-level ordering on a clear that crosses the 10-line threshold (scores at the pre-level-up level) was an implicit choice from code order, undocumented and untested. Documented with a comment and added a boundary-crossing test proving it.
- **low, patch** — `SCORE_TABLE[clearedCount]` has no fallback for an out-of-range key; unreachable given the standard piece set (max 4-row clear) but undocumented. Added a comment recording the invariant rather than dead defensive code.
- **low, patch** — Initial static HUD markup (0/1/0) duplicates `state`'s defaults by hand with nothing keeping them in sync. Added a comment rather than restructuring (the values are overwritten on the first frame regardless).
- **false, rejected** — Null-guarding the three `getElementById` HUD lookups. Disproof: same precedent as prior rejected speculative guards — the IDs are authored and verified together in this same story (Test 6 confirms the wiring), not a state anything currently reachable would trigger.
- **false, rejected** — Widening `#hud` now for Story 1.6's not-yet-built next-piece preview. Real and concrete, but exactly the kind of forward work that belongs to the story that actually needs it — logged to `deferred-work.md` for Story 1.6 instead.
- **false, rejected** — Adding ARIA live-region semantics to the HUD. Disproof: EXPERIENCE.md's Accessibility Floor explicitly states "no screen-reader support planned... not treated as a gap at this scope" — this is a recorded product decision, not an oversight.

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Lines clear (Story 1.4) but nothing tracks score or level, fall speed never increases, and there's no visible HUD at all yet — the canvas is the entire page.

**Approach:** Add `state.score`, `state.level` (starts at 1), `state.linesCleared` (cumulative). In `lockPiece()`, use `clearCompletedLines()`'s now-available return value (closed as part of Story 1.4's review) to award score (100/300/500/800 x level for 1/2/3/4 lines) and update `linesCleared`/`level` (level = 1 + floor(linesCleared / 10)) in the same pass. Add the first DOM UI: an `<div id="hud">` panel (SCORE/LEVEL/LINES label+value pairs) styled from DESIGN.md's tokens, laid out board-left/HUD-right per DESIGN.md's Layout & Spacing section — requires wrapping the page body in a flex container alongside the existing canvas.

Fall speed scaling by level isn't specified upstream (Architecture explicitly defers the exact curve) — implemented as `FALL_INTERVAL * 0.9^(level-1)`, floored at 0.1s/row, monotonically non-increasing per AD-9. Documented in Implementation Notes.

</frozen-after-approval>

## Implementation Notes

- Added `state.score`/`level`/`linesCleared`. Scoring hooked into `lockPiece()` right after `clearCompletedLines()` (using its return value, closed in Story 1.4's review), before `spawnPiece()`.
- Added the first DOM UI: `<div id="hud">` with SCORE/LEVEL/LINES label+value pairs, styled entirely from DESIGN.md tokens (`--surface-panel`, `--outline`, `--spacing-*`, `--typography-label-caps-*`, `--typography-body-*`). `body` already used flex layout (Story 1.1), so board-left/HUD-right just needed a `gap`.
- `updateHud()` writes `state.score/level/linesCleared` into the DOM via `textContent`, called once per frame from the end of `render()` — keeps the update/render split intact (update mutates, render only reflects, whether to canvas or DOM).
- `currentFallInterval()`: `FALL_INTERVAL * 0.9^(level-1)`, floored at `MIN_FALL_INTERVAL` (0.1s/row). Not pinned upstream (Architecture explicitly defers the curve); chosen for a smooth, monotonically non-increasing ramp per AD-9. Soft drop's `SOFT_DROP_INTERVAL` is unaffected by level (already well under any level's base interval).
- Verification: extended the white-box instrumentation approach from Story 1.4 (expose internals via a return-value transform on the extracted script, seed state directly, call the real functions) to test initial state, a single-line clear's score/lines effect, score scaling by level, the level-up threshold at 10 cumulative lines, the fall-interval curve's monotonicity and floor, that `render()` actually writes the HUD DOM text nodes, and (added post-review) a level-crossing clear scoring at the pre-level-up level. Also opened in the system default browser to look at the new layout.
- Post-review fixes: corrected `.hud-label` to use `heading` typography tokens (DESIGN.md's prose said this twice; its own YAML component token had a stray `label-caps` reference — fixed both the code and DESIGN.md itself); refreshed the stale `FALL_INTERVAL` comment; added `overflow-wrap` to `.hud-value`; documented (rather than silently relying on) the SCORE_TABLE range invariant and the deliberate pre-level-up scoring order on a threshold-crossing clear, plus a comment tying the static HTML defaults to `state`'s initial values.

