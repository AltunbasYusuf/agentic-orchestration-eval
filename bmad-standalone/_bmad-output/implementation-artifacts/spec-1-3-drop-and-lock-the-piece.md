---
title: 'Drop and Lock the Piece'
type: 'feature'
created: '2026-09-07'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

## Review Triage Log

- **medium, patch** — `fallTimer`/`moveTimer`/`movePrevDir` were only reset on hard-drop-triggered locks, not gravity- or soft-drop-triggered ones, so a newly spawned piece could inherit stale timing state from whatever piece locked before it. Fixed by moving the reset into `lockPiece()` itself, the single choke-point for every lock path. Verified with a targeted harness test (move, hard-drop-lock, confirm the new piece's next press is immediate).
- **low, patch** — `lockPiece()` had no null-guard of its own, unlike every other state-mutating function in the file, and it's exactly the function Story 1.4 is expected to extend next. Added `if (!piece) return;` for consistency, even though both current call sites already guard before calling it.
- **false, rejected** — Capturing an affected-rows list in `lockPiece()` now, ahead of Story 1.4's line-clear logic. Disproof: trivial for that story to derive from `piece.row`/`cells` when it's actually implementing the check; adding it now with no consumer would be speculative.
- **noted, not a code finding** — Verification for this story still can't include reading real browser console output (no automation tool installed, by deliberate choice — see Story 1.1/1.2 notes). Raised directly with the user rather than repeating the same caveat indefinitely, since this is the most state-machine-heavy story yet.

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The piece moves and rotates (Story 1.2) but never falls on its own, never locks, and never stops being the only piece in play — there's no gravity, no soft/hard drop, and no respawn cycle yet.

**Approach:** Add gravity: the active piece falls one row at a fixed base interval, driven by the same delta-time accumulator pattern as movement (AD-2). Holding Down (soft drop) uses a shorter interval than the base rate, without locking on contact. Spacebar (hard drop) repeatedly advances the piece to the lowest valid row and locks it immediately. Whenever the piece can't move down further — by gravity, soft drop, or hard drop — it locks into `state.board` and `spawnPiece()` runs again in the same `update()` pass (no line-clearing yet; that's Story 1.4). The exact base/soft-drop fall rates aren't specified upstream (same category of decision as Story 1.2's move-repeat interval) — chosen for a reasonable feel and recorded in Implementation Notes.

Because pieces now lock and accumulate on the board with no line-clearing yet, the board can genuinely fill to the top during a normal playtest of this story alone (nothing removes rows until Story 1.4). When `spawnPiece()` would spawn into an already-occupied cell, this story does not implement Game Over (that's Story 1.8) — it stops spawning and leaves `state.activePiece` `null`, a documented temporary stopgap. `tryMove`/`tryRotate`/gravity must therefore each no-op safely when `activePiece` is `null`, rather than throwing.

</frozen-after-approval>

## Implementation Notes

- Added `FALL_INTERVAL` (0.8s/row, base gravity) and `SOFT_DROP_INTERVAL` (0.05s/row while Down held) — both arbitrary implementation choices (PRD/Architecture explicitly leave the fall-speed curve unspecified), reusing the same accumulator pattern as Story 1.2's move-repeat.
- Added `input.down` (held) and `input.hardDrop` (edge-triggered, guarded against OS auto-repeat like `rotate`) plus their keydown/keyup/blur wiring.
- Added `stepDown()` (one gravity/soft-drop step; locks via `lockPiece()` if blocked), `hardDrop()` (loops `stepDown`'s move check to the floor, then locks immediately), and `lockPiece()` (writes the piece into `state.board`, clears `activePiece`, calls `spawnPiece()` in the same pass — no line-clearing yet, that's Story 1.4).
- Closed Story 1.2's deferred null-guard gap for real: `spawnPiece()` now checks `isValidPosition` at the spawn cell and leaves `activePiece` `null` if occupied (temporary stopgap — Game Over is Story 1.8). `tryMove`/`tryRotate`/`stepDown` all no-op safely against a null `activePiece`, so this is no longer a speculative guard against an unreachable state — the full-board case is genuinely reachable within a normal few-minute playtest of this story alone, since nothing clears lines yet.
- Interpretation of FR-4's "without locking on contact" vs FR-5's "locks immediately": lock is only ever triggered by a failed downward-step attempt (`stepDown`), identical for gravity and soft drop — soft drop just raises the attempt rate. Hard drop is the only path that locks synchronously within the same call that moved the piece. Documented since it wasn't explicit upstream.
- Verification: extended the Node harness (same approach as Stories 1.1/1.2 — loads the actual shipped script, no reimplementation) to drive gravity over simulated time, hard drop, soft drop, and lock+respawn, and to stress-test 60 consecutive hard drops to fill the board and confirm no exception is thrown, including movement/rotation input against a possibly-null `activePiece` afterward. Ran 8 times to exercise different random spawn types. Also opened in the system default browser for a manual look. I have not personally read the live browser's console output.
- Post-review fix: moved `fallTimer`/`moveTimer`/`movePrevDir` resets into `lockPiece()` itself (single choke-point for every lock, regardless of trigger), removing the hard-drop-only reset that previously left gravity/soft-drop-triggered locks leaking stale timing state into the next piece. Added a null-guard to `lockPiece()` for consistency with every other mutator in the file.
- Added a targeted harness test proving the fix: move left once, hard-drop (locks + respawns), then confirm a fresh Right press on the new piece moves immediately rather than waiting out inherited `moveTimer`/`movePrevDir`. First attempt at this test had a test-only bug (comparing `Math.min` column across *all* painted piece cells, which picked up the separately-locked piece sitting near the bottom instead of isolating the active piece) — not a product defect; fixed by filtering to cells near the top before comparing.

