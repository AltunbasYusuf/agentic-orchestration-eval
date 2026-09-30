---
title: Product Brief - Browser Tetris (BMAD Workflow Test Fixture)
status: final
created: 2026-09-07
updated: 2026-09-07
---

# Product Brief: Browser Tetris (BMAD Workflow Test Fixture)

## Context

This is not a product — it's a technical test fixture. It exists to give the BMAD standalone (skill-file) workflow and a LangGraph-integrated BMAD workflow an identical, fully-scoped small task to run side by side for comparison. Tetris was chosen because its scope is universally understood and holds no ambiguity.

## What's Being Built

A single-player, browser-based Tetris clone: the classic falling-blocks game, playable start to finish in one continuous session. Mechanics are itemized in Scope below.

## Scope

**In (v1):**
- Arrow-key move and rotate
- Soft drop and hard drop
- Line clearing
- Score counter
- Level/speed ramp as play continues
- Pause and restart
- Next-piece preview
- Game-over screen

**Out (deliberate, not just deferred):**
- Sound/music
- Mobile/touch controls
- High-score persistence (localStorage)
- Hold-piece
- Full SRS wall-kick rotation system
- Multiplayer

## Definition of Done

A full round — spawn, play, clear at least one line, reach game over, restart — completes with no console errors. Controls feel immediate, with no perceptible input lag (target: smooth 60 FPS). Verified by manual smoke test: open the file, play a round, check the console. No automated test suite is expected.

## Technical Constraints

- Zero dependencies, no build tooling
- Single HTML file
- Vanilla JavaScript (ES2020+)
- Canvas 2D for rendering
- Must run fully offline via `file://`

**Visual style (preference, not a hard constraint):** retro arcade/terminal feel — dark theme, monospace font, classic piece colors (I-cyan, O-yellow, T-purple, S-green, Z-red, J-blue, L-orange).
