---
title: 'Restart and Handle Game Over'
type: 'feature'
created: '2026-09-07'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

## Review Triage Log

- **high, patch** — No `dt` clamp on the `requestAnimationFrame` loop: a backgrounded/refocused tab produces one large `dt`, and since only one `stepDown()` fires per frame, the excess drains as a rapid burst of consecutive drops over the following frames — a common, easily-reachable scenario (ordinary alt-tabbing) that would confusingly fast-forward or end a game the player didn't cause. Fixed with `MAX_DT = 0.1s`; the lost real time is dropped, not caught up. Verified with a dedicated test simulating a 60-second single-frame gap.
- **high, patch** — The persistent "P: PAUSE  R: RESTART" control hint was never implemented anywhere across all 8 stories, despite being an explicit, already-recorded requirement (UX-DR8 / EXPERIENCE.md's Voice and Tone table specifies it as *static and persistent*, not just inside the overlays). Caught only on this final-pass, whole-file review. Added to the HUD.
- **medium, patch** — The Paused overlay's hint only said "P: RESUME," with no on-screen indication that "R" also restarts from Paused (a real, working feature per the FSM diagram and `update()`'s check ordering). Updated the hint text.
- **low, patch** (three) — `updateOverlay()` re-queried `getComputedStyle` for the state colors every frame, unlike every other color in the file (cached once at init); flash-row timers froze (harmlessly, fully hidden behind the opaque overlay) when Game Over interrupted an in-progress flash (moved the decay to run unconditionally); the `restart()` comment's "nothing survives from the prior session" was imprecise about *game* state vs. deliberately-preserved held-key input state — clarified.
- **false, rejected** — Adding a restart confirmation guard. Disproof: directly contradicts PRD FR-12's explicit "no confirmation prompt" — an already-recorded product decision, not a gap.
- **false, rejected** — Clearing held movement keys (`left`/`right`/`down`) in `restart()`. Disproof: correct behavior, not a bug — a still-held key legitimately continues to apply to the new piece, same reasoning as Story 1.7's pause fix. Comment clarified instead of behavior changed.
- **false, rejected** — ARIA/screen-reader hooks. Disproof: same as Stories 1.5/1.7 — EXPERIENCE.md's Accessibility Floor explicitly states no screen-reader support is planned; a recorded decision, not an oversight.
- **false, rejected** — Showing level/lines (not just score) in the Game Over summary. Disproof: matches the DESIGN.md/EXPERIENCE.md spec exactly as written (final score only) — would be a scope addition beyond what was actually specified.

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `spawnPiece()`'s full-board stopgap (Story 1.3) just freezes the game silently — there's no Game Over state, no way to see the final score, and no restart. This is the last story: it closes the loop the PRD's Definition of Done requires (spawn -> play -> clear -> game over -> restart).

**Approach:** Add `state.phase = 'gameover'`, set by `spawnPiece()`'s existing stopgap branch instead of leaving the game silently stuck. Extend `updateOverlay()` (built reusable in Story 1.7 for exactly this) with a `'gameover'` branch: "GAME OVER" in `--state-game-over` (red), a new subtitle showing the final score, and an "R: RESTART" hint. Add `input.restart` ("R", edge-triggered) checked *first* in `update()` — before the pause toggle, before any phase gate — so it works from Playing, Paused, or Game Over alike, per the FSM diagram's three `"R"` edges. `restart()` resets board/`activePiece`/`nextQueue`/score/level/linesCleared/flashRows/the fall-and-move timers together in one pass (AD-8), sets `phase = 'playing'`, and clears `rotate`/`hardDrop` (the same stale-edge-trigger leak Story 1.7 fixed for pause applies here too, if either was pressed during Game Over).

</frozen-after-approval>

## Implementation Notes

- `spawnPiece()`'s existing full-board stopgap (Story 1.3) now sets `state.phase = 'gameover'` instead of just leaving `activePiece` null — the "temporary" comment is gone, this is the real Game Over trigger.
- Added `restart()`: resets board/flashRows/score/level/linesCleared/nextQueue/fallTimer/moveTimer/movePrevDir together, clears `rotate`/`hardDrop`, sets `phase = 'playing'`, spawns fresh (always succeeds against an empty board).
- `input.restart` ("R") is checked first in `update()`, before even the pause toggle — works from Playing, Paused, or Game Over, per the FSM diagram's three "R" edges (the story's own AC only names Playing/Game Over; Paused->Playing via R is Architecture's more complete spec, honored as the superset).
- `updateOverlay()` gained the `'gameover'` branch it was built for in Story 1.7: "GAME OVER" in `--state-game-over` (red), a new `#overlay-subtitle` showing `SCORE: {state.score}`, "R: RESTART" hint.
- Verification: full loop-driven harness (same approach as 1.7) — filled the board via repeated hard drops to trigger real Game Over, confirmed overlay content (title/color/score/hint), confirmed gameplay input has zero effect during Game Over, confirmed restart resets every field together and works from all three phases (Playing self-loop, Paused->Playing, GameOver->Playing), a dedicated regression test for the stale-rotate-leaking-past-restart class of bug (same one Story 1.7 fixed for pause), and (added post-review) a dt-clamp test proving a simulated 60-second single-frame gap advances the active piece by at most one row. One test-only bug caught along the way: an earlier test pressed ArrowLeft during a game-over check and never released it — the held key legitimately kept affecting the next piece after restart (correct behavior, not a product bug), just contaminated a later assertion; fixed by releasing it. Also opened in the system default browser to look at the Game Over overlay and play a full round through restart.
- This is the epic's final story — treated the Blind Hunter pass as whole-file, not just this story's diff, per the "last story" framing.
- Post-review fixes: added a `dt` clamp (`MAX_DT = 0.1s`) to the `requestAnimationFrame` loop — without it, a backgrounded/refocused tab would produce one huge `dt`, and since only one `stepDown()` fires per frame, the excess would drain as a rapid burst of consecutive drops over the following frames (a real, easily-reachable scenario via ordinary alt-tabbing, not an edge case). Added the persistent "P: PAUSE  R: RESTART" control hint to the HUD — this was an explicit, already-recorded requirement (UX-DR8 / EXPERIENCE.md's Voice and Tone table specifies it as *static and persistent*) that had never actually been implemented anywhere across all 8 stories, caught only on this final-pass review. Updated the Paused overlay's hint to also mention "R: RESTART" (a real, working feature with no prior on-screen affordance). Cached `--state-paused`/`--state-game-over` as `STATE_PAUSED_COLOR`/`STATE_GAME_OVER_COLOR` at init, matching the file's established token-caching convention (`updateOverlay()` had been re-querying `getComputedStyle` every frame). Moved `updateFlashRows(dt)` to run unconditionally regardless of phase, so a flash triggered by the same lock that causes Game Over no longer freezes mid-animation. Clarified the `restart()` comment: held movement keys are deliberately *not* cleared (a still-held key legitimately continues to apply), only game state and one-shot edge-triggered flags are reset.

