---
title: 'Pause and Resume'
type: 'feature'
created: '2026-09-07'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

## Review Triage Log

- **high, patch** — Real, easily-reachable bug: `input.rotate`/`input.hardDrop` are set by the keydown listener regardless of phase, and `update()` returned before ever reaching the code that clears them while paused, so a Space or Up press made *while* paused survived and fired the instant "P" resumed — an unwanted hard-drop or rotation on a frame the player took no such action on. Fixed by clearing both flags inside the paused early-return. Verified with a dedicated regression test.
- **medium, patch** — The pause toggle (`phase === 'paused' ? 'playing' : 'paused'`) treated any non-paused phase as pausable — harmless today, but would silently hijack Story 1.8's `'gameover'` phase into `'paused'` the moment it exists. Replaced with an explicit two-way check. Not a speculative guard — a strict simplification with no added complexity, just correct now.
- **low, patch** (two) — Added a comment marking the "placed before the early return, so it runs even while paused" pattern, since Story 1.8's Paused→Playing "R" edge must follow it or silently never fire; removed a dead `line-height: 0` rule whose comment claimed it collapsed an inline-canvas gap that doesn't exist here (`#board` is already `display: block`).
- **false, rejected** — `updateOverlay()` needing restructuring for Story 1.8. Disproof: the current `if (paused) {...} else {hide}` shape is already trivially extensible with an `else if ('gameover')` branch; no rework needed.
- **false, rejected** — The blur-vs-pending-pause-press race. Disproof: the same pre-existing, already-accepted characteristic of the blur-clearing pattern shared by every edge-triggered input since Story 1.2, not something new introduced here; the race window is negligible.
- **false, rejected** — Skipping `render()` while paused as a performance optimization. Disproof: no stated requirement or observed problem motivates it; continuous rendering of static content at 60 FPS is not a performance issue at this scale.
- **false, rejected** — Auto-pausing on window blur. Disproof: not requested anywhere in the PRD/EXPERIENCE.md/this story's AC (which only specifies the "P" key) — would be scope creep beyond FR-11.
- **false, rejected** — ARIA/screen-reader hooks on the overlay. Disproof: same as Story 1.5 — EXPERIENCE.md's Accessibility Floor explicitly states no screen-reader support is planned; a recorded decision, not an oversight.

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** There's no FSM state at all yet — the game is always "playing," with no way to freeze it, and no overlay mechanism exists (Architecture's Structural Seed calls for one shared `<div id="overlay">` reused by both Pause and the still-unbuilt Game Over).

**Approach:** Add `state.phase` ('playing' | 'paused'). Wire "P" as an edge-triggered `input.pause` flag (guarded against OS auto-repeat, like `rotate`/`hardDrop`). In `update(dt)`, the pause toggle is checked first (so "P" always works as the resume key too); when `phase === 'paused'`, `update()` returns immediately after that check — no movement, rotation, drop, gravity, or flash-timer decay runs, satisfying "no movement, timers, or input processed except resume."

Accumulator reset (AD-2's "reference timestamp resets on resume, no time-spike") is satisfied without literally resetting anything: the `requestAnimationFrame` loop keeps ticking through a pause (so `lastTimestamp` never goes stale), and `update()`'s early return simply freezes `fallTimer`/`moveTimer` in place rather than letting them advance — resuming continues from exactly where they left off, with no discarded progress and no large catch-up `dt`. This satisfies AD-2's intent through a different (arguably cleaner) mechanism than a literal timestamp reset; documented in Implementation Notes since it's a deliberate deviation from the spine's literal wording.

Add the overlay DOM (wrapping the canvas in a positioned `#board-wrap` so it can sit absolutely over the board): 85%-black scrim, `display` typography, PAUSED in `--state-paused` (amber), a "P: RESUME" hint — built as one reusable element per Architecture's Structural Seed, since Story 1.8's Game Over overlay shares the same mechanism.

</frozen-after-approval>

## Implementation Notes

- Added `state.phase` ('playing'/'paused'), `input.pause` (edge-triggered, `e.repeat`-guarded, cleared on blur). `update(dt)` checks the pause toggle first (unconditionally, so "P" doubles as resume), then returns immediately if paused — nothing else in `update()` runs.
- Wrapped `#board` in `#board-wrap` (`position: relative`) so `#overlay` (`position: absolute; inset: 0`) sits exactly over the canvas. Built as one shared, reusable overlay element per Architecture's Structural Seed — `updateOverlay()` currently only branches on `phase === 'paused'`; Story 1.8 adds a `'gameover'` branch to the same function rather than a second overlay.
- Documented deviation from AD-2's literal wording ("resets the reference timestamp on resume"): the `requestAnimationFrame` loop never stops during pause, so `lastTimestamp` never goes stale — `update()`'s early return simply freezes `fallTimer`/`moveTimer` in place, and they resume counting from exactly where they left off. Satisfies the same intent (no time-spike, no game-time during pause) without discarding any partial progress a literal reset would.
- Verification: built a full loop-driven harness (mocking DOM including the overlay's classList/textContent/style, keyboard listeners, and `requestAnimationFrame`) proving: initial phase is playing with the overlay hidden; "P" pauses, shows the overlay with the correct text and the `--state-paused` token color; gravity and held-movement are completely frozen through 1.6s of simulated real time while paused; a second "P" resumes and hides the overlay; and the first frame after resuming advances by 0-1 rows, not a multi-row time-spike. Also opened in the system default browser to look at the pause overlay.
- Post-review fixes: clear `input.rotate`/`input.hardDrop` inside the paused early-return, so a Space or Up press made *while* paused can no longer survive to fire the instant "P" resumes (real, easily-reachable bug — added a dedicated regression test proving a stale Space-while-paused press no longer causes a hard-drop on the resume frame); replaced the pause-toggle ternary with an explicit `playing→paused`/`paused→playing` check, so a future `'gameover'` phase (Story 1.8) can't be silently hijacked into `'paused'` by a stray "P" press; added a comment marking the "runs even while paused" placement pattern for Story 1.8's Paused→Playing "R" edge; removed a dead, misleadingly-commented `line-height: 0` rule (no inline content exists in `#board-wrap` for it to act on).

