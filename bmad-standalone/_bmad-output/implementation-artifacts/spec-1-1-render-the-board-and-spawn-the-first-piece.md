---
title: 'Render the Board and Spawn the First Piece'
type: 'feature'
created: '2026-09-07'
status: 'done'
route: 'oneshot'
review_loop_iteration: 0
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** The project has no code yet — there is no HTML file to open, no board rendered, and no piece visible. Story 1.1 of Epic 1 (Play a Complete Round of Tetris) is the first implementation story.

**Approach:** Create `tetris.html` as the project's single file. Render the 10x20 board on a `<canvas>` (black background, faint green grid lines, 1px green border, square corners), apply the DESIGN.md token set as CSS custom properties in the `<style>` block, and spawn one tetromino at the fixed start position/orientation using a shared `PIECE_SHAPES` constant table, drawn in its correct piece color. Everything lives in one inline IIFE `<script>` block with separated state/input/update/render/main sections, per the architecture's paradigm — this story only needs the state and render sections plus a minimal spawn-once `main`, since movement, timing, and the game loop proper arrive in later stories.

</frozen-after-approval>

## Implementation Notes

- Created `tetris.html` at project root: full DESIGN.md token set as CSS custom properties in `:root` (flattened nested typography tokens to `--typography-{role}-{property}`), a 240x480 `<canvas id="board">` styled via CSS border/background, and one inline IIFE `<script>` with state/render sections (input/update sections deliberately left as comments-only — arrive in Stories 1.2/1.3).
- Defined `PIECE_SHAPES`: all 7 tetromino types x 4 rotation states x [row,col] cell offsets, in a 4-row bounding box, matching AD-4 (single shared table for spawn/rotate/render).
- Spawn: since no piece queue/randomization exists yet (that's Story 1.6/AD-5), picked a uniform-random piece type at spawn — a "choice the user wouldn't notice" per Boundaries; Story 1.6 will layer the real queue on top without changing this story's behavior.
- Board border rendered via CSS (`border: 1px solid var(--outline)` on the canvas element) rather than drawn inside the canvas bitmap — cleaner pixel alignment, and exercises the CSS-custom-property mechanism the AC asks for directly.
- Verification: no `chromium-cli` or cached Playwright install was available in this environment, and installing one would pull a network dependency for a project whose whole point is zero-dependency/offline — did not install one unprompted. Instead: (1) extracted the exact inline script and ran it under Node with a mocked canvas context — confirms no runtime exceptions on spawn+render, and asserts all 28 piece/rotation combinations have exactly 4 cells and stay in-bounds at the spawn position; (2) opened the file in the system default browser via `Start-Process` for a real, visible render the user can glance at, twice (before and after the review-driven fixes). I have not personally read the live browser's console output — flagging this limit rather than claiming a browser-verified console check I didn't actually perform.
- Post-review fixes: derived `canvas.width`/`canvas.height` from `CELL` instead of hardcoding matching HTML attributes; replaced hardcoded hex color literals with values read live from the CSS custom properties via `getComputedStyle` (single source of truth now matches DESIGN.md); added viewport meta tag, canvas fallback text, a "temporary" comment on `spawnPiece()`'s random pick, and removed dead `box-sizing: border-box` CSS.

## Review Triage Log

- **medium, patch** — Dimensions hardcoded in three independent places (JS `CELL`, HTML canvas width/height attrs, CSS `--spacing-cell`), nothing deriving one from another. Fixed: `canvas.width`/`height` now computed from `BOARD_COLS * CELL` / `BOARD_ROWS * CELL` in JS.
- **medium, patch** — Colors duplicated between CSS custom properties and JS (`PIECE_COLORS`, hardcoded grid/board hex), contradicting the single-source-of-truth principle the code states for `PIECE_SHAPES`. Fixed: colors now read live via `getComputedStyle` from the `:root` tokens.
- **low, patch** — No `<meta name="viewport">`. Added (zero cost, though mobile is an explicit PRD non-goal).
- **low, patch** — `<canvas>` had no fallback content for non-rendering browsers/assistive tech. Added fallback text.
- **low, patch** — `spawnPiece()`'s random-selection line lacked a "temporary, replaced by Story 1.6" comment, unlike the input/update sections which already flag their own future stories. Added.
- **low, patch** — Dead `box-sizing: border-box` on `#board` (no CSS width/height set, so it had no effect). Removed.
- **low, defer** — No devicePixelRatio/HiDPI scaling (canvas will render blurry on retina displays). Real, but not a simple fix and nothing in the PRD/Architecture requires it. Logged to `deferred-work.md`.
- **false, rejected** — `ctx` from `canvas.getContext('2d')` is never null-checked. Disproof: failing loudly (an immediate `TypeError`) on a browser state nothing in this project's target environment shows is reachable is correct behavior, not a bug, per this review process's own stated stance.
- **false, rejected** — The Node verification harness used during implementation isn't committed to the repo. Disproof: the PRD explicitly lists "Automated test suite" as a Non-Goal — verification is manual smoke test only. Committing the harness would contradict that recorded product decision; it was correctly treated as a throwaway implementation-time aid.

