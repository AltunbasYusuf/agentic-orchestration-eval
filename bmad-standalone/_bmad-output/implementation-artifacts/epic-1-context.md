# Epic 1 Context: Play a Complete Round of Tetris

<!-- Compiled from planning artifacts. Edit freely. Regenerate with compile-epic-context if planning docs change. -->

## Goal

Deliver a complete, playable round of browser Tetris in a single offline HTML file: spawn and control falling tetrominoes, clear lines, track score and level, preview the next piece, and pause, lose, or restart — all with the retro-terminal visual treatment. This is the only epic in the project; it covers the entire functional scope end to end.

## Stories

- Story 1.1: Render the Board and Spawn the First Piece
- Story 1.2: Move and Rotate the Falling Piece
- Story 1.3: Drop and Lock the Piece
- Story 1.4: Clear Completed Lines
- Story 1.5: Track Score and Level
- Story 1.6: Show the Next Piece
- Story 1.7: Pause and Resume
- Story 1.8: Restart and Handle Game Over

## Requirements & Constraints

- Board is 10 columns x 20 rows. Piece spawns at a fixed start position/orientation; if the spawn cell(s) are occupied, the game goes straight to Game Over.
- Left/Right arrow moves one cell per press; held keys repeat at a fixed rate (not the browser's native key-repeat). Movement/rotation blocked by edges or occupied cells.
- Up arrow rotates; a rotation that would collide or leave bounds is rejected outright — no wall-kick, no SRS.
- Down arrow (held) soft-drops (faster fall, no lock-on-contact); Spacebar hard-drops instantly and locks immediately.
- Locking (natural fall, soft drop, or hard drop) triggers line-clear evaluation before the next spawn.
- Line clear: full rows are removed and rows above shift down; partially-filled rows are untouched. Scoring: 1/2/3/4 lines = 100/300/500/800 x current level, applied immediately.
- Level increments every 10 cumulative lines cleared (starts at 1); fall speed increases monotonically with level (exact curve is an implementation detail, unspecified).
- Next-piece preview always shows exactly the piece that will spawn next, updated the instant a new piece spawns.
- "P" pauses/resumes: while paused, no movement/timers/input processed except resume. "R" restarts from Playing or Game Over, no confirmation, resetting board/score/level/lines together.
- Game Over triggers when a new piece can't spawn: gameplay input stops, final score shown, restart offered.
- Performance: smooth 60 FPS, no perceptible input lag on move/rotate/drop.
- Runtime: zero dependencies, no build tooling, single HTML file, vanilla ES2020+ JS, Canvas 2D rendering, must run fully offline via `file://`.
- Definition of done: a full round (spawn -> play -> clear a line -> game over -> restart) completes with zero browser console errors.
- Explicit non-goals: sound/music, touch/mobile input, high-score persistence, hold-piece, full SRS wall-kicks, multiplayer, automated tests (manual smoke test only).

## Technical Decisions

- Paradigm: Game Loop + Finite State Machine with exactly three FSM states — Playing, Paused, GameOver. Soft drop and line clear are sub-behaviors within Playing, not separate states.
- Single mutator rule: only `update(dt)` writes to shared `state`; `render()` and input handlers only read it. Scoring, line-clear, and level-up all happen inline in the same `update` pass — no event bus.
- Loop timing: `requestAnimationFrame` + delta-time accumulator drives fall, soft-drop rate, and move-repeat — none use native key-repeat. Entering Paused stops the accumulator itself (no game-time elapses while paused); resuming resets its reference timestamp to that instant.
- `state.board` is a row-major 2D array, `board[row][col]`, 20 rows x 10 cols, row 0 = top. Cells are `null` or a piece-color key (`I`/`O`/`T`/`S`/`Z`/`J`/`L`).
- One shared constant table `PIECE_SHAPES` (7 piece types x 4 rotations x occupied-cell offsets) is read by spawn, rotation collision-check, and render alike — no duplicated shape data.
- `state.nextQueue` is an array (length >= 1); spawn logic dequeues the front and refills the tail; the preview renderer only peeks index 0, never mutates it. Randomization algorithm for refilling is intentionally unfixed/deferred.
- Everything lives in one inline IIFE `<script>` block with clearly separated sections: state, input, update, render, main. No modules, no external `.js` files.
- Keydown/keyup handlers only set/clear fields on a single `input` object, never touch `state` directly. Held intents (`left`/`right`/`down`) are booleans; edge-triggered intents (`rotate`/`hardDrop`/`pause`/`restart`) are one-shot flags cleared by `update()` after consumption.
- Restart replaces `state.board`, `activePiece`, `nextQueue`, `score`, `level`, and `linesCleared` together in one `update()` pass — nothing survives from the prior session.
- Line clear mutates `state.board` synchronously in the same pass that detected it. The visual flash is a separate render-layer echo (`state.flashRows`: pre-clear row colors + frame count, decremented each tick by `update()`, drawn by `render()`) — it never delays the underlying mutation.
- Naming: JS identifiers use `camelCase` for variables/functions, `UPPER_SNAKE_CASE` for constant tables (`PIECE_SHAPES`, `SCORE_TABLE`). No IDs/dates/network envelopes anywhere in this scope.

## UX & Interaction Patterns

- Visual identity: retro arcade/terminal — flat fills, hard/square edges (no rounding, no gradients, no shadows), system monospace font throughout, applied via CSS custom properties in the single `<style>` block.
- Board (canvas): pure black background, faint dark-green grid lines, 1px green border. Locked cells and the active piece render in their piece color from the shared color set (I-cyan, O-yellow, T-purple, S-green, Z-red, J-blue, L-orange).
- HUD is a DOM panel (not canvas) to the right of the board: stacked SCORE / LEVEL / LINES label+value pairs, updating immediately on change.
- Next-Piece Preview is a bordered DOM panel inside the HUD, showing the queued tetromino centered in its actual color, updated the instant a new piece spawns.
- Pause overlay (DOM, absolutely positioned over the canvas): 85%-black scrim, centered amber "PAUSED" in the display type role, "P: RESUME" hint; board stays dimly visible beneath.
- Game-Over overlay: same scrim treatment, centered red "GAME OVER" in display type, final score in heading type, "R: RESTART" hint; persists until restart.
- Line-clear feedback is a single flat-color flash on the cleared row(s) only — no particles, no shake, no easing/motion anywhere beyond this.
- Microcopy: all-caps state labels, terse, no punctuation flourish; a persistent static control hint "P: PAUSE  R: RESTART".
- No start screen — the first piece spawns immediately on page load.
- Keyboard-only surface, no mouse/touch targets; every action already has a keyboard binding by construction. No colorblind-alternative piece coding and no screen-reader support are explicit non-goals, not gaps.
- Composition reference for exact layout/spacing exists (`mockups/play-field.html`) but the architecture and design specs win on any conflict with it.

## Cross-Story Dependencies

- Story 1.1 (board render + spawn + `PIECE_SHAPES`) underpins every later story: movement/rotation (1.2), locking (1.3), and rendering all read the same shape table and board structure.
- Story 1.3's lock behavior is the trigger for Story 1.4's line-clear evaluation, which must complete (including scoring) before Story 1.1's spawn logic runs again for the next piece.
- Story 1.4's line-clear count feeds directly into Story 1.5's score and level updates within the same `update()` pass.
- Story 1.6's next-piece preview depends on the same `nextQueue` that Story 1.1's spawn logic writes to — the preview must only read it.
- Story 1.7 (pause) and Story 1.8 (restart/game over) both depend on the FSM and accumulator behavior established for the core loop (1.1-1.3): pausing must halt the same accumulator driving fall/move-repeat, and restart must reset every piece of state touched by Stories 1.1-1.6 in one pass.
