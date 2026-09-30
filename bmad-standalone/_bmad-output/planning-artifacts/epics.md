---
stepsCompleted: [1, 2, 3]
inputDocuments:
  - '{planning_artifacts}/prds/prd-bmad-standalone-2026-09-07/prd.md'
  - '{planning_artifacts}/architecture/architecture-bmad-standalone-2026-09-07/ARCHITECTURE-SPINE.md'
  - '{planning_artifacts}/ux-designs/ux-bmad-standalone-2026-09-07/DESIGN.md'
  - '{planning_artifacts}/ux-designs/ux-bmad-standalone-2026-09-07/EXPERIENCE.md'
---

# Browser Tetris (BMAD Workflow Test Fixture) - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for Browser Tetris, decomposing the requirements from the PRD, UX Design, and Architecture into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: The system spawns a new tetromino at a fixed start position/orientation at game start and immediately after the previous piece locks (and any resulting line clears resolve). If the spawn cell(s) are occupied, transitions to Game Over instead.
FR2: The player can move the active tetromino one cell left or right per Left/Right arrow-key press, held keys repeating at a fixed rate; blocked by edges/occupied cells.
FR3: The player can rotate the active tetromino via the Up arrow key; a rotation that would collide or leave bounds is rejected outright (no wall-kick).
FR4: Holding the Down arrow accelerates the active piece's descent without locking it on contact.
FR5: A single Spacebar press instantly drops the active piece to the lowest valid position and locks it immediately.
FR6: The active piece locks in place when it cannot move down further (natural fall, soft drop, or hard drop); triggers line-clear evaluation before the next spawn.
FR7: When one or more rows are fully occupied after a lock, the system clears those rows, shifts rows above down, and awards score.
FR8: The system awards points when lines clear, scaled by lines cleared simultaneously and current level (1=100x, 2=300x, 3=500x, 4=800x level); score updates immediately.
FR9: The system increases the level after every 10 cumulative lines cleared; fall speed increases monotonically with level (no specific curve required).
FR10: The system displays the tetromino queued after the active one, updated immediately on every spawn.
FR11: The player can pause/resume via the "P" key; while paused, no movement/timers/input processed except resume.
FR12: The player can restart via the "R" key, from an active session or the Game Over screen; resets board, score, and level immediately, no confirmation prompt.
FR13: When a new piece cannot spawn, the system stops accepting gameplay input, displays a game-over screen with final score, and offers restart.

### NonFunctional Requirements

NFR1: Performance - smooth 60 FPS during normal play; no perceptible input lag on move/rotate/drop.
NFR2: Deployment/Runtime - zero dependencies, no build tooling; ships as a single HTML file, vanilla JavaScript (ES2020+), Canvas 2D rendering; must run fully offline via `file://` (no server, bundler, or network fetch at runtime).

### Additional Requirements

- **No starter template.** Architecture explicitly rules one out (AD-6, zero-dependency constraint) - Epic 1/Story 1 begins from a single blank HTML file, not a scaffolding tool.
- **Paradigm (AD's 1-9, binding across all epics):** Game Loop + Finite State Machine (Playing/Paused/GameOver). Single `update(dt)` is the only mutator of shared `state` (AD-1); `requestAnimationFrame` + delta-time accumulator drives fall/soft-drop/move-repeat, resetting its reference timestamp on resume (AD-2); `state.board` is a row-major 2D array, 20x10, row 0 = top (AD-3); one shared `PIECE_SHAPES` constant table (7 types x 4 rotations) read by spawn/rotate/render (AD-4); `state.nextQueue` is a shared array (length >= 1), written only by spawn logic, peeked read-only by the preview renderer - randomization algorithm is unfixed/deferred (AD-5); one inline IIFE `<script>` with state/input/update/render/main sections (AD-6); keydown/keyup only set/clear fields on a single `input` object, held vs. edge-triggered, consumed only by `update()` (AD-7); Restart resets board + activePiece + nextQueue + score + level + linesCleared together, in one pass (AD-8); line-clear mutates `state.board` synchronously in the same pass that detected it - the visual flash is a separate `state.flashRows` render-layer echo, never delaying the mutation (AD-9).
- **No infrastructure/deployment requirements** - static file opened via `file://`, no environments, no CI/CD.
- **No integration requirements** - no external systems, no network calls.
- **No data migration/setup, no monitoring/logging** - the only operational requirement is a clean browser console (zero errors) per the PRD's Definition of Done.
- **No API/versioning/security implementation requirements** - none apply at this scope.

### UX Design Requirements

UX-DR1: Implement the full DESIGN.md token set (colors, typography, spacing, `rounded: 0`) as CSS custom properties, applied via the single file's `<style>` block.
UX-DR2: Board render: black (`board-bg`) canvas background, faint green (`grid-line`) grid lines, 1px green (`outline`) border, square corners throughout.
UX-DR3: HUD panel as a DOM element (not canvas), right of the board: stacked SCORE / LEVEL / LINES label+value pairs per DESIGN.md's HUD component spec.
UX-DR4: Next-Piece Preview as a bordered DOM panel inside the HUD, showing the queued tetromino centered in its actual piece color.
UX-DR5: Pause overlay (DOM, absolutely positioned over the canvas per Architecture's Structural Seed): 85%-black scrim, centered amber "PAUSED" in `display` type, "P: RESUME" hint.
UX-DR6: Game-Over overlay (DOM, same treatment): 85%-black scrim, centered red "GAME OVER" in `display` type, final score in `heading` type, "R: RESTART" hint.
UX-DR7: Line-clear flash: a single flat-color flash on the cleared row(s), no particles/shake, implemented via Architecture AD-9's `state.flashRows` render-layer echo.
UX-DR8: Voice/tone microcopy: all-caps state labels, short copy, no punctuation flourish; persistent control hint "P: PAUSE  R: RESTART" per EXPERIENCE.md's Voice and Tone table.
UX-DR9: Accessibility floor: every action already has a keyboard binding by construction (no separate a11y work needed); no colorblind-alternative piece coding and no screen-reader support are explicit, documented non-goals at this scope, not gaps to close.
UX-DR10: `mockups/play-field.html` is the composition reference for board/HUD/overlay layout and the three-state visual treatment; the spines win on any conflict with it.

### FR Coverage Map

FR1: Epic 1 - Piece spawn (and the spawn-blocked -> Game Over trigger)
FR2: Epic 1 - Move left/right
FR3: Epic 1 - Rotate (reject-on-collision)
FR4: Epic 1 - Soft drop
FR5: Epic 1 - Hard drop
FR6: Epic 1 - Lock
FR7: Epic 1 - Line clear
FR8: Epic 1 - Score counter
FR9: Epic 1 - Level / speed ramp
FR10: Epic 1 - Next-piece preview
FR11: Epic 1 - Pause
FR12: Epic 1 - Restart
FR13: Epic 1 - Game Over

## Epic List

### Epic 1: Play a Complete Round of Tetris
Players can play a full round of browser Tetris end to end — spawn and control falling pieces, clear lines, watch score and difficulty progress, and pause, lose, or restart — entirely offline from a single HTML file, with the retro-terminal presentation from the UX spines.
**FRs covered:** FR1, FR2, FR3, FR4, FR5, FR6, FR7, FR8, FR9, FR10, FR11, FR12, FR13

## Epic 1: Play a Complete Round of Tetris

Players can play a full round of browser Tetris end to end — spawn and control falling pieces, clear lines, watch score and difficulty progress, and pause, lose, or restart — entirely offline from a single HTML file, with the retro-terminal presentation from the UX spines.

### Story 1.1: Render the Board and Spawn the First Piece

As a player,
I want to see the game board and my first falling piece the moment I open the file,
So that I know the game has started.

**Acceptance Criteria:**

**Given** the HTML file is opened directly in a browser via `file://`
**When** the page loads
**Then** a 10x20 black board renders with faint green grid lines and a 1px green border, and a tetromino appears at the fixed spawn position in its correct piece color (per the shared `PIECE_SHAPES` table)
**And** the browser console shows zero errors
**And** all DESIGN.md tokens (colors, typography, spacing) are applied via CSS custom properties from the single `<style>` block

### Story 1.2: Move and Rotate the Falling Piece

As a player,
I want to move the falling piece left/right and rotate it with the arrow keys,
So that I can position it where I want.

**Acceptance Criteria:**

**Given** a piece is actively falling
**When** I press Left or Right
**Then** it moves one cell in that direction, unless blocked by the board edge or an occupied cell
**And** holding Left or Right repeats the move at a fixed rate via the delta-time accumulator (not the browser's native key-repeat)
**When** I press Up
**Then** the piece rotates to its next orientation per `PIECE_SHAPES`, or stays put if that rotation would collide or leave the board (no wall-kick)

### Story 1.3: Drop and Lock the Piece

As a player,
I want to speed up or instantly drop the falling piece and have it lock into the board,
So that I can place pieces quickly.

**Acceptance Criteria:**

**Given** a piece is actively falling
**When** I hold Down
**Then** it descends faster than the level's base fall speed without locking on contact
**When** I press Spacebar
**Then** it instantly drops to the lowest valid position and locks immediately
**And** whenever the piece can no longer move down (natural fall, soft drop, or hard drop), it locks in place and becomes part of the board with the correct color

### Story 1.4: Clear Completed Lines

As a player,
I want completed rows to clear and the board to collapse downward,
So that I can keep playing without the board filling up.

**Acceptance Criteria:**

**Given** a piece just locked
**When** one or more rows are fully occupied
**Then** those rows are removed and all rows above shift down, within the same `update()` pass that detected the lock (no multi-tick delay)
**And** the cleared row(s) show a brief flat-color flash (via `state.flashRows`) that does not delay the underlying board mutation
**And** partially-filled rows are left untouched

### Story 1.5: Track Score and Level

As a player,
I want to see my score and level increase as I clear lines,
So that I have a sense of progress and challenge.

**Acceptance Criteria:**

**Given** the HUD panel is visible
**When** lines clear
**Then** score increases immediately per the tiered formula (100/300/500/800 x level for 1/2/3/4 lines) and the HUD's SCORE value updates
**When** cumulative lines cleared crosses a multiple of 10
**Then** level increments and fall speed increases accordingly
**And** gameplay stays at a smooth 60 FPS with no perceptible input lag as speed increases

### Story 1.6: Show the Next Piece

As a player,
I want to see which piece is coming next,
So that I can plan my placement.

**Acceptance Criteria:**

**Given** the HUD's NEXT panel is visible
**When** a new piece spawns
**Then** the panel immediately shows the new upcoming piece, centered, in its correct piece color
**And** `nextQueue` always holds at least one upcoming piece; the preview only reads it, never mutates it

### Story 1.7: Pause and Resume

As a player,
I want to pause and resume the game,
So that I can step away without losing progress.

**Acceptance Criteria:**

**Given** I am actively playing
**When** I press "P"
**Then** the game freezes (no movement, timers, or input processed), a dimmed overlay shows "PAUSED" with a "P: RESUME" hint
**When** I press "P" again
**Then** play resumes with the accumulator's reference timestamp reset to that instant — no leftover pause time or time-spike affects fall speed

### Story 1.8: Restart and Handle Game Over

As a player,
I want the game to end cleanly when I top out, and to restart at any time,
So that I can play again without reloading the page.

**Acceptance Criteria:**

**Given** a new piece cannot spawn because the spawn cell is occupied
**When** that happens
**Then** gameplay input stops, a dimmed overlay shows "GAME OVER" with the final score and an "R: RESTART" hint
**Given** I am in Playing or Game Over
**When** I press "R"
**Then** board, active piece, next-piece queue, score, level, and lines-cleared all reset together in one pass — nothing carries over from the prior session
**And** a full round (spawn -> play -> clear a line -> game over -> restart) completes with zero console errors
