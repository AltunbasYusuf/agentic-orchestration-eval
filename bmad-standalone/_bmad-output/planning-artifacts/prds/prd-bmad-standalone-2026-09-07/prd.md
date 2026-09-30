---
title: Browser Tetris (BMAD Workflow Test Fixture)
status: final
created: 2026-09-07
updated: 2026-09-07
---

# PRD: Browser Tetris (BMAD Workflow Test Fixture)

## 0. Document Purpose

This PRD is for whoever implements this fixture (self or a downstream build workflow) and for comparing the BMAD standalone and LangGraph-integrated workflows against each other. It builds directly on the finalized product brief (`briefs/brief-bmad-standalone-2026-09-07/brief.md`) — that brief established the fixture's purpose, audience, and technical constraints; this document does not repeat that reasoning, only the requirements it implies. Vocabulary is Glossary-anchored (§3); features are grouped with FRs nested and globally numbered (§4); inferred gaps are tagged `[ASSUMPTION]` inline and indexed in §9.

## 1. Vision

Browser Tetris is a single-player, single-HTML-file implementation of the classic falling-block game, built as a controlled test fixture rather than a product. Its purpose is to give two BMAD execution paths — the standalone skill-file workflow and a LangGraph-integrated workflow — an identical, unambiguous task to run end to end, so the *process* is what's being evaluated, not the *domain*. A game everyone already knows the rules to removes requirements ambiguity as a variable, isolating differences in how each workflow plans, builds, and reviews.

Success here isn't player adoption — it's a working, playable round with no console errors and no perceptible input lag, produced by whichever workflow is under test.

## 2. Target User

### 2.1 Jobs To Be Done
- *Functional:* As the builder running this experiment, I need a scoped task I can hand to each workflow and get a comparable, working artifact back.
- *Contextual:* The task needs to be small enough to finish in one sitting but real enough (state machine, input handling, rendering loop) to actually exercise a workflow's planning and build quality.

## 3. Glossary

- **Board** — the 10×20 grid cells occupy.
- **Tetromino** — a 4-cell falling piece (I, O, T, S, Z, J, L).
- **Line Clear** — removal of a fully-filled row.
- **Soft Drop / Hard Drop** — accelerated fall (held) vs. instant fall (single input).
- **Next-Piece Preview** — display of the tetromino queued after the active one.
- **Level** — the difficulty tier that governs fall speed; advances with lines cleared.
- **Game Over** — terminal state reached when a new tetromino cannot spawn.

## 4. Features

### 4.1 Core Gameplay Loop
**Description:** The falling-piece mechanic: pieces spawn, move, rotate, and drop under player control; completed rows clear before the next piece spawns. Full SRS wall-kick rotation is explicitly out of scope — rotation uses basic collision rejection only: a rotation that would place the piece out of bounds or overlapping an occupied cell is rejected outright, no kick offsets attempted.

#### FR-1: Piece Spawn
The system spawns a new tetromino at a fixed start position and orientation at game start and immediately after the previous piece locks (and any resulting line clears resolve).

**Consequences (testable):**
- A new piece appears within one frame of the previous piece locking.
- If the spawn cell(s) are already occupied, the system transitions to Game Over (FR-13) instead of spawning.

#### FR-2: Move
The player can move the active tetromino one cell left or right per Left/Right arrow-key press, held keys repeating at a fixed rate.

**Consequences (testable):**
- Movement is blocked at board edges and by occupied cells; the piece does not move if the target cells are invalid.

#### FR-3: Rotate
The player can rotate the active tetromino via the Up arrow key.

**Consequences (testable):**
- A rotation that would place the piece out of bounds or overlapping an occupied cell is rejected; the piece stays in its prior orientation. No wall-kick offset is attempted.

#### FR-4: Soft Drop
Holding the Down arrow accelerates the active piece's descent (faster than the current level's base fall speed) without locking it on contact.

#### FR-5: Hard Drop
A single Spacebar press instantly drops the active piece to the lowest valid position on its column(s) and locks it immediately.

#### FR-6: Lock
The active piece locks in place (becomes part of the board) when it cannot move down further, whether from natural fall, soft drop, or hard drop.

**Consequences (testable):**
- Lock triggers line-clear evaluation (FR-7) before the next spawn (FR-1).

#### FR-7: Line Clear
When one or more rows are fully occupied after a lock, the system clears those rows, shifts all rows above down by the number cleared, and awards score (FR-8).

### 4.2 Scoring & Progression
**Description:** Score and difficulty respond to lines cleared, using a classic tiered scoring formula and a level-every-10-lines curve.

#### FR-8: Score Counter
The system awards points when lines clear, scaled by how many lines cleared simultaneously and the current level.

**Consequences (testable):**
- Point values: 1 line = 100 × level, 2 lines = 300 × level, 3 lines = 500 × level, 4 lines ("tetris") = 800 × level.
- Score is visibly updated immediately after the clear resolves.

#### FR-9: Level / Speed Ramp
The system increases the level after every 10 lines cleared (cumulative), and fall speed increases with each level.

**Consequences (testable):**
- Level starts at 1; increments at 10, 20, 30... cumulative lines cleared.
- Fall speed is monotonically non-decreasing with level — exact curve is an implementation detail, no specific target required.

### 4.3 Session Control
**Description:** Everything around the core loop that lets a player start, pause, end, and restart a session, plus the look-ahead that lets them plan.

#### FR-10: Next-Piece Preview
The system displays the tetromino that will spawn after the currently active one, updated immediately when the active piece changes.

#### FR-11: Pause
The player can pause and resume the game via the "P" key.

**Consequences (testable):**
- While paused, no piece movement, timers, or input is processed other than the resume input.

#### FR-12: Restart
The player can restart the game via the "R" key, from either an active session or the Game Over screen.

**Consequences (testable):**
- Restart resets the board, score (to 0), and level (to 1) immediately — no confirmation prompt.

#### FR-13: Game Over
When a new piece cannot spawn (FR-1), the system stops accepting movement/rotation/drop input, displays a game-over screen showing the final score, and offers restart (FR-12).

## 5. Cross-Cutting NFRs

- **Performance:** smooth 60 FPS during normal play; no perceptible input lag on move/rotate/drop. Applies across all of §4.1's input-handling FRs, not any single one. Validated by SM-2 (§8).
- **Deployment / Runtime:** zero dependencies, no build tooling. Ships as a single HTML file, vanilla JavaScript (ES2020+), rendering via Canvas 2D. Must run fully offline, opened directly via `file://` — no server, bundler, or network fetch required at runtime.

## 6. Non-Goals (Explicit)

- Sound / music
- Mobile / touch controls
- High-score persistence (localStorage or otherwise)
- Hold-piece
- Full SRS wall-kick rotation system
- Multiplayer
- Automated test suite — verification is manual smoke test only (see §8)

## 7. MVP Scope

### 7.1 In Scope
See §4 Features — FR-1 through FR-13 constitute the full v1 scope; nothing beyond them is in for this fixture.

### 7.2 Out of Scope for MVP
See §6 Non-Goals — all items there are out for v1 and not planned for a later version within this fixture.

## 8. Success Metrics

**Primary**
- **SM-1**: Manual smoke test passes — a full round (spawn → play → clear at least one line → game over → restart) completes with zero console errors. Validates FR-1, FR-6, FR-7, FR-12, FR-13.

**Secondary**
- **SM-2**: Controls feel immediate — no perceptible input lag during normal play, smooth 60 FPS. Validates FR-2, FR-3, FR-4, FR-5.

**Counter-metrics:** None warranted at this scope — there's no optimization target here that a counter-metric would need to guard against.

## 9. Open Questions

None outstanding. The two genuine gaps found during discovery (key bindings beyond the core arrows, and the scoring/level formula) were resolved as confirmed assumptions — see §10.

## 10. Assumptions Index

- FR-5 — Hard drop bound to the Spacebar (no other key specified in the brief).
- §4.2 / FR-8 — Tiered line-clear scoring: 100/300/500/800 × level for 1/2/3/4 lines.
- §4.2 / FR-9 — Level increases every 10 cumulative lines cleared; fall-speed curve left as an implementation detail.
- FR-11 — Pause bound to the "P" key.
- FR-12 — Restart bound to the "R" key; restart is immediate with no confirmation prompt.
