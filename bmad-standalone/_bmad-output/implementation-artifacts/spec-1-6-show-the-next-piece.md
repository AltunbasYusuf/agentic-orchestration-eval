---
title: 'Show the Next Piece'
type: 'feature'
created: '2026-09-07'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

## Review Triage Log

- **medium, patch** — No reusable queue-seeding function; Story 1.8's restart (AD-8) would have had to hand-duplicate the seed logic, risking drift. Extracted `seedNextQueue()`, used by both state init and available for restart. This also structurally closes the "no null-guard in renderPreview()" concern by removing the only realistic way the AD-5 invariant could break.
- **low, patch** (four) — Missing `display: block` on `#preview` (same baseline-gap issue `#board` already guards against); documented the deterministic centering bias for odd-vs-even shape/grid parity (T/S/Z/J/L sit flush left, I sits flush top — not a bug, whole-cell granularity can't do better); documented that the preview goes stale once the full-board stopgap freezes the game, consistent with already-documented behavior elsewhere; documented the bare `2px` margin as a deliberate below-token-granularity exception rather than inventing a new design token mid-implementation; removed a redundant `display: block` on a `<div>`.
- **false, rejected** — Adding a defensive null-guard to `renderPreview()` directly. Disproof: unreachable given the AD-5 invariant every current write path upholds, and better addressed at the root (the `seedNextQueue()` fix above) than symptom-guarded.
- **false, rejected** — Removing `#hud`'s fixed width "neuters" the Story 1.5 overflow-wrap defense. Disproof: this is a desktop-only fixture (narrow/mobile viewports are an explicit PRD/UX Non-Goal), and the panel is now wider (~122px, set by the preview canvas) than the old 96px — realistic score magnitudes fit comfortably without needing to wrap at all.

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `spawnPiece()` currently picks a random piece type directly at spawn time — there's no queue, so there's nothing to preview, and the HUD has no NEXT panel yet.

**Approach:** Add `state.nextQueue` (AD-5): seeded with one random piece type at state init, then on every `spawnPiece()` call, dequeue the front (`shift()`) as the piece that spawns and push one new random type onto the tail — queue length stays constant at 1, satisfying "length >= 1" always. Randomization stays uniform-random (Architecture explicitly defers the algorithm choice; this story only fixes the queue *interface*, per AD-5). Add a NEXT panel to the HUD: a small `<canvas id="preview">` (4x2 cells — the largest bounding box any piece needs at spawn rotation) inside a bordered/backgrounded DOM wrapper matching the HUD panel's existing DESIGN.md treatment, drawing the queue's head piece centered within its own actual bounding box, peeked read-only every frame from `render()` — never mutating the queue. `#hud`'s fixed width (flagged as too narrow in Story 1.5's review) is widened to fit-content instead of a hardcoded value.

</frozen-after-approval>

## Implementation Notes

- Added `state.nextQueue` (seeded with 1 random type at state init) and rewrote `spawnPiece()` to `shift()` the front as the spawning type and `push()` a fresh random type onto the tail — queue length invariant (constant at 1) holds regardless of whether the resulting spawn succeeds or hits the full-board stopgap.
- Added `<canvas id="preview">` (4x2 cells — the largest bounding box any piece needs at spawn rotation) inside a new `#preview-panel` DOM wrapper, styled identically to `#hud` itself. `renderPreview()` computes each piece's actual occupied bounding box and centers it within the 4x2 grid, rather than drawing at raw shape offsets (which would leave narrower pieces visually off-center) — peeks `nextQueue[0]` only, never mutates.
- Widened `#hud` from a hardcoded 96px to fit-content (removed the fixed `width`), resolving the gap flagged in Story 1.5's review.
- Verification: extended the white-box approach to test the queue invariant across 200 direct `spawnPiece()` calls (dequeued type always matches what was previously at the front, length never drifts from 1), type variety over 300 spawns (all 7 types observed), that `renderPreview()` never mutates the queue, and that every one of the 7 piece types paints exactly 4 cells fully within the 4x2 preview grid (proving the centering math doesn't clip any shape). One test-only bug caught and fixed along the way: reassigning the fill-call sink array with `= []` orphaned the mock's captured reference — fixed by clearing in place (`.length = 0`) instead. Also opened in the system default browser to look at the widened HUD and preview panel.
- Post-review fixes: extracted `seedNextQueue()` as the single reusable seeding function (state init now calls it too), directly serving Story 1.8's AD-8 reset requirement and removing the drift risk that would have made an unguarded queue-head read in `renderPreview()` reachable; added `display: block` to `#preview`; documented (rather than "fixed" — neither is achievable/needed) the deterministic centering bias and the preview's expected staleness once the full-board stopgap freezes the game; documented the bare `2px` margin as a deliberate below-token-granularity exception; removed a redundant `display: block` on a `<div>`.

