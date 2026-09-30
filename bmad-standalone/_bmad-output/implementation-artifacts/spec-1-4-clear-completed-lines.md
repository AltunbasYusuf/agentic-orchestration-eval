---
title: 'Clear Completed Lines'
type: 'feature'
created: '2026-09-07'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

## Review Triage Log

- **medium, patch** — `clearCompletedLines()` didn't surface how many rows it cleared, but `epic-1-context.md` explicitly documents Story 1.5 needing that count for scoring. Fixed: the function now returns `fullRows.length` (0 when nothing cleared). Verified directly (asserts 1 for a single-row clear, 2 for a simultaneous two-row clear).
- **medium, patch** — The real one: the flash overlay drew *after* the active piece with no occupancy check, so a freshly spawned piece landing on a just-flashed row (routine near the top of a tall stack, since most spawns occupy rows 0-1) got whited out for 150ms. Fixed by reordering `render()`: flash now draws after locked board cells (still visible over shifted content, the intended effect) but before the active piece, so the player's live piece is never obscured. Verified both behaviorally (state-level tests) and structurally (draw-order check against the actual source).
- **low, patch** — `FLASH_COLOR` was a bare hex literal, bypassing the CSS-custom-property convention every other color in the file follows. Added `--flash-color` to `:root` and read it via the existing `token()` helper.
- **low, patch** — Empty-row construction was duplicated with two different idioms (state init vs. the unshift loop). Extracted a shared `createEmptyRow()` helper.
- **false, rejected** — `state.flashRows`'s shape (`{row, timeRemaining}`) doesn't match `epic-1-context.md`'s paraphrase ("pre-clear row colors + frame count"). Disproof: the shipped shape is what the UX spec's "single flat-color flash, no particles" actually calls for — no per-cell color memory is needed for a flat overlay. The epic-context's prose was the imprecise one, not the code; not worth a full context regeneration over one paraphrase.


<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Pieces lock (Story 1.3) but full rows never clear — the board just fills up permanently, and nothing in `lockPiece()` checks for completed rows.

**Approach:** Extend `lockPiece()` (Story 1.3's identified extension point) to scan for fully-occupied rows immediately after writing the locked piece into `state.board`, and before `spawnPiece()` runs — matching FR-1's "spawns... after any resulting line clears resolve." Full rows are removed and empty rows unshifted at the top in the same synchronous pass (AD-9: the mutation is never delayed). A `state.flashRows` list (row index + remaining duration) drives a flat-color flash overlay in `render()`, decremented each `update()` tick — a render-layer-only effect, decoupled from the mutation per AD-9. No scoring here (FR-8/9 are Story 1.5); this story only clears and shifts.

The flash duration and color aren't specified upstream (Architecture explicitly defers the exact duration; the UX spec says "flat-color flash" without naming the color) — chosen as an implementation detail and recorded in Implementation Notes.

</frozen-after-approval>

## Implementation Notes

- Extended `lockPiece()` (Story 1.3's flagged extension point) with `clearCompletedLines()`, called after writing the piece into `state.board` and before `spawnPiece()`. Full rows detected via `every(cell => cell !== null)`, removed via `splice` and empty rows `unshift`ed at the top, entirely synchronous within the same call (AD-9).
- Added `state.flashRows` (`{row, timeRemaining}`), decremented every tick by a new `updateFlashRows(dt)` called at the top of `update()` (runs even when `activePiece` is null, so a flash from the piece that triggered the full-board stopgap still fades out). `render()` draws a flat white rectangle over each flashing row's full width, after the board/piece drawing, purely decorative — never affects `state.board`.
- Chose `FLASH_DURATION = 0.15s` and `FLASH_COLOR = '#ffffff'` — neither pinned upstream (Architecture defers the duration; UX names "flat-color flash" without a color). White for maximum contrast/visibility as a quick pop.
- Verification took two attempts. First: drove ~50 hard drops through blind gameplay (alternating far-left/center/far-right placement) and tracked total painted piece-cell count, expecting "grew slower than 4/drop" to prove a clear happened. This surfaced a real methodological problem, not a product bug: 3 discrete placement positions don't guarantee full 10-column row coverage, so rows never actually completed, the board jammed unevenly near the spawn columns, and a flawed "row < 5 means a fresh piece" heuristic masked the resulting null-`activePiece` stopgap as if pieces kept spawning. Diagnosed via added per-drop debug logging rather than assumed.
- Replaced with a direct, white-box approach: transform the extracted script text (string manipulation only, in this throwaway verification file — `tetris.html` itself is never touched) so the IIFE's own return value is captured through `new Function(...)()` , exposing `state`, `clearCompletedLines`, and `updateFlashRows` directly. This allows seeding `state.board` precisely and calling the real function against constructed scenarios: a single full row, a two-row simultaneous clear with an untouched partial row in between, and a no-op case. All verify the actual shipped logic, not a reimplementation. Also opened in the system default browser for a manual look. I have not personally read the live browser's console output (per the confirmed working approach for this project).

