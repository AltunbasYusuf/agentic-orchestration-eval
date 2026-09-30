---
name: Browser Tetris
status: final
sources:
  - '{planning_artifacts}/prds/prd-bmad-standalone-2026-09-07/prd.md'
  - '{planning_artifacts}/briefs/brief-bmad-standalone-2026-09-07/brief.md'
updated: 2026-09-07
---

# Browser Tetris — Experience Spine

## Foundation

Single-surface web, desktop browser, keyboard-only — no touch/mobile input (explicit Non-Goal in the PRD). No UI system: raw Canvas 2D plus minimal HTML/CSS for HUD text. `DESIGN.md` is the visual identity reference; this spine covers behavior only. No dark/light mode toggle — the terminal aesthetic is the only mode.

## Information Architecture

There is exactly one surface — there's no navigation to model. The "screens" are states layered on that single surface:

| State | Reached from | Purpose |
|---|---|---|
| Playing (default) | Page load (file opened directly) or Restart | Active gameplay — board, HUD, and input all live |
| Paused | "P" key, from Playing | Freezes the session in place without losing it |
| Game Over | Blocked spawn (PRD FR-1/FR-13), from Playing | Ends the session, shows the result, offers restart |

No start screen: per PRD FR-1, the first piece spawns immediately at load — there's no "press to begin" gate. `[ASSUMPTION: confirms PRD's implicit behavior — flagging in case a start screen was actually wanted and just never got written into the PRD]`

→ Composition reference: `mockups/play-field.html` — all three states (Playing / Paused / Game Over) in one file. Spine wins on conflict.

## Voice and Tone

Minimal — this is a terminal, not a chatty app. All copy is short, all-caps where it's a state label, no punctuation flourish.

| Do | Don't |
|---|---|
| `PAUSED` | `Game paused — take a break!` |
| `GAME OVER` / `SCORE: 4200` | `Nice try! Final score: 4200 points` |
| `P: PAUSE  R: RESTART` (control hint, static) | Tooltips, onboarding tours, toasts |

## Component Patterns

Behavioral. Visual specs live in `DESIGN.md.Components`.

| Component | Use | Behavioral rules |
|---|---|---|
| Board (canvas) | Always visible | Redraws every frame; renders locked cells + active piece at its current position/orientation |
| HUD panel | Right of board, always visible | Score, Level, Lines update immediately on change (PRD FR-8, FR-9) |
| Next-Piece Preview | Inside HUD panel | Updates the instant a new piece spawns (PRD FR-10) |
| Pause overlay | Appears over board on Pause | Board dims but stays visible beneath; disappears on resume |
| Game-over overlay | Appears over board on Game Over | Board dims, shows final score; persists until Restart |

## State Patterns

| State | Trigger | Treatment |
|---|---|---|
| Playing | Load or Restart | Board active, HUD live, all input accepted |
| Soft drop | Down arrow held | Fall rate increases while held; no separate visual mode, just faster descent (PRD FR-4) |
| Line Clear | Row fully occupied (PRD FR-7) | Brief flash on the cleared row(s) before they shift out — one flat color flash, no particles or shake `[ASSUMPTION: flash treatment — PRD specifies the mechanic, not the visual feedback]` |
| Paused | "P" key (PRD FR-11) | Overlay per DESIGN.md; no piece movement, timers, or input processed except resume |
| Game Over | Blocked spawn (PRD FR-1/FR-13) | Overlay per DESIGN.md; all gameplay input stops except Restart |

## Interaction Primitives

- Keyboard only, no mouse or touch target anywhere on the surface.
- Left / Right arrow: move, repeats while held at a fixed rate (PRD FR-2).
- Up arrow: rotate, single press, no repeat (PRD FR-3).
- Down arrow (held): soft drop (PRD FR-4).
- Spacebar: hard drop, single press (PRD FR-5).
- "P": pause/resume (PRD FR-11). "R": restart, works from Playing or Game Over (PRD FR-12).
- **Banned:** any animation beyond the line-clear flash — no screen shake, no particle effects, no transition easing. Matches the flat DESIGN.md posture and the zero-dependency constraint (nothing here needs an animation library).

## Accessibility Floor

Behavioral; visual contrast lives in `DESIGN.md`.

- Keyboard-only interaction is the baseline, not an add-on — every action already has a keyboard binding by construction.
- `[NOTE FOR UX]` No colorblind-safe alternative (shape/pattern coding) for the seven piece colors in v1 — they're the standard Tetris Guideline palette, not verified for color-vision-deficiency distinguishability. Acceptable at this fixture's stakes (solo/hobby, no accessibility requirement raised in brief or PRD) but named here rather than silently dropped.
- No screen-reader support planned — this is a visual/keyboard-only game, consistent with the PRD's Non-Goals; not treated as a gap at this scope.

## Key Flows

### Flow 1 — Solo playtest session (you, checking the build right after it's implemented)

1. You open the HTML file directly in a browser via `file://`.
2. The board is already active — first piece falling, no start screen.
3. You move and rotate with the arrow keys, soft-drop by holding Down, hard-drop with Space.
4. A row fills; it flashes and clears, HUD score/level update immediately.
5. Play continues, fall speed ramping as the level increases (PRD FR-9).
6. Eventually a piece can't spawn — the Game Over overlay appears with your final score.
7. **Climax:** you check the browser console — zero errors — and confirm the controls felt lag-free the whole round. That's the entire point of the fixture: a clean pass here is the signal the workflow under test produced a working build (realizes PRD SM-1, SM-2).
8. You press "R" to run another round, or just close the tab.
