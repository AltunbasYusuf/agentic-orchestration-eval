---
title: 'Move and Rotate the Falling Piece'
type: 'feature'
created: '2026-09-07'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Story 1.1 renders a single spawned piece, but it's completely static — there's no input handling, no game loop, and the piece never moves. Nothing built so far has the loop or input infrastructure Story 1.2 needs.

**Approach:** Add a single `input` intent object (AD-7): booleans `left`/`right` toggled on keydown/keyup, and a one-shot `rotate` flag set on keydown and cleared by `update()` after consumption. Add a `requestAnimationFrame` + delta-time accumulator loop (AD-2) that calls `update(dt)` then `render()` every frame; the accumulator drives move-repeat at a fixed rate (not the browser's native key-repeat). `update()` is the only mutator (AD-1): it applies left/right movement (blocked by board edges or occupied cells) and rotation via `PIECE_SHAPES` (rejected outright — no wall-kick — if it would collide or leave bounds). `render()` moves from a one-time call to running every frame.

</frozen-after-approval>

## Implementation Notes

- Added the `input` object (AD-7): `left`/`right` booleans toggled by keydown/keyup, `rotate` as a one-shot flag guarded against the browser's native `e.repeat` auto-repeat (so holding Up doesn't spam rotations) and cleared by `update()` after consumption. `e.preventDefault()` on all three arrow keys to stop page scroll.
- Added the `requestAnimationFrame` + delta-time-accumulator loop (AD-2) in `main`, replacing the one-shot `spawnPiece(); render();` calls from Story 1.1. `update(dt)` runs before `render()` every frame.
- `update(dt)` (AD-1, sole mutator): rotate is edge-triggered and consumed once; movement uses a `dir` variable (left takes priority if both held) — a direction change or fresh press moves immediately, holding repeats every `MOVE_REPEAT_INTERVAL` (0.1s, an arbitrary implementation choice like Story 1.1's random spawn pick — not specified upstream).
- Added `isValidPosition`/`tryMove`/`tryRotate`, all reading the shared `PIECE_SHAPES` table (AD-4) and `state.board` for collision — reused as-is by future stories (drop/lock in 1.3, restart in 1.8).
- Verification: no browser automation tool available (same constraint as Story 1.1 — didn't install one). Built a Node harness that loads the *actual* inline script (regex-extracted from the shipped file, not a reimplementation) behind a minimal `document`/`window`/`requestAnimationFrame`/canvas shim, then drives it through simulated key events and frame timestamps. Confirmed: immediate move on fresh press, correct fixed-rate repeat timing, the piece never crosses the right boundary under sustained input, rotation stays in-bounds and repaints exactly 4 cells, a synthetic `repeat:true` keydown does not trigger a duplicate rotation, and (after the review fix) a `blur` event stops a held direction from continuing to drift the piece. Also opened the file in the system default browser twice (before and after fixes) for a real visual/manual check. I have not personally read the live browser's console output.
- Post-review fixes: added a `blur` listener clearing all `input` flags (stuck-key fix); changed the repeat-timer reset from `moveTimer = MOVE_REPEAT_INTERVAL` to `moveTimer += MOVE_REPEAT_INTERVAL` so cadence doesn't drift under frame lag.

## Review Triage Log

- **medium, patch** — No `blur`/focus-loss handling: `input.left`/`input.right` could get stuck `true` if the window loses focus while a key is held (browsers don't guarantee a matching `keyup`), causing indefinite unintended drift. Fixed: `blur` listener clears all three `input` flags. Verified with a dedicated regression check in the Node harness.
- **low, patch** — `moveTimer` reset discarded overshoot (`=` instead of `+=`), letting repeat cadence drift slightly under frame lag/throttling. Fixed to accumulate.
- **low, defer** — `tryMove`/`tryRotate` assume `state.activePiece` always exists (true today; not true once Story 1.3 introduces the gap between lock and respawn), and `moveTimer`/`movePrevDir`/`lastTimestamp`/`input` have no reset entry point for Story 1.8's restart. Real forward risk, not a defect in this story's actual scope — logged to `deferred-work.md` for Stories 1.3 and 1.8 to pick up.
- **false, rejected** — `lastTimestamp` not reset across pause. Disproof: no pause exists in this story's scope (unreachable today), and Architecture AD-2 plus Story 1.7's own acceptance criteria already fully specify the required reset-on-resume behavior — nothing new to track.
- **false, rejected** — `isValidPosition`'s occupied-cell branch is unverified this story (board is always empty). Disproof: the check is correct by inspection (`if (state.board[r][c]) return false;`); it will get real exercise and verification starting Story 1.3 once locking exists.
- **false, rejected** — Flat `if`/`else if` keydown chain will grow unwieldy. Disproof: three keys is not remotely unmanageable; refactoring to a lookup table now would be premature abstraction ahead of actual need.
- **false, rejected** — No `state.phase`/status field gating `update()` for pause/game-over. Disproof: that gate is explicitly Story 1.7's stated scope per `epics.md` ("no piece movement, timers, or input processed except resume"); adding an unused phase field now would be speculative.

