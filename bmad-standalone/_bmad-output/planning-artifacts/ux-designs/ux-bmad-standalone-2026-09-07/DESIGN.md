---
name: Browser Tetris
description: Retro arcade/terminal visual identity for the Browser Tetris workflow test fixture — flat, monospace, CRT-phosphor mood.
status: final
updated: 2026-09-07
colors:
  surface-bg: '#0b0d0c'
  surface-panel: '#121512'
  board-bg: '#000000'
  grid-line: '#173617'
  outline: '#33ff33'
  text-primary: '#33ff33'
  text-dim: '#1f7a1f'
  state-paused: '#ffb000'
  state-game-over: '#ff3333'
  piece-i-cyan: '#00f0f0'
  piece-o-yellow: '#f0f000'
  piece-t-purple: '#a000f0'
  piece-s-green: '#00f000'
  piece-z-red: '#f00000'
  piece-j-blue: '#0000f0'
  piece-l-orange: '#f0a000'
typography:
  display:
    fontFamily: "ui-monospace, 'Courier New', monospace"
    fontSize: 32px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: 0.02em
  heading:
    fontFamily: "ui-monospace, 'Courier New', monospace"
    fontSize: 16px
    fontWeight: '700'
    lineHeight: '1.3'
    letterSpacing: 0.05em
  body:
    fontFamily: "ui-monospace, 'Courier New', monospace"
    fontSize: 14px
    fontWeight: '400'
    lineHeight: '1.4'
  label-caps:
    fontFamily: "ui-monospace, 'Courier New', monospace"
    fontSize: 11px
    fontWeight: '700'
    lineHeight: '1.4'
    letterSpacing: 0.1em
rounded:
  sm: 0px
  DEFAULT: 0px
  md: 0px
  lg: 0px
  full: 9999px
spacing:
  unit: 8px
  cell: 24px
  gutter: 16px
  panel-padding: 12px
components:
  board:
    background: '{colors.board-bg}'
    border: '1px solid {colors.outline}'
    gridLine: '{colors.grid-line}'
  hud-panel:
    background: '{colors.surface-panel}'
    border: '1px solid {colors.outline}'
    padding: '{spacing.panel-padding}'
    labelType: '{typography.heading}'
    valueType: '{typography.body}'
  next-piece-preview:
    background: '{colors.surface-panel}'
    border: '1px solid {colors.outline}'
    padding: '{spacing.panel-padding}'
  overlay-pause:
    background: 'rgba(0,0,0,0.85)'
    text: '{colors.state-paused}'
    type: '{typography.display}'
  overlay-game-over:
    background: 'rgba(0,0,0,0.85)'
    text: '{colors.state-game-over}'
    type: '{typography.display}'
---

## Brand & Style

Arcade-cabinet terminal, not a modern game UI. The posture is functional and unadorned — a CRT phosphor glow rather than a polished product. Every visual choice should read as "1980s terminal running a game," not "web app that happens to look retro." No gradients, no drop shadows, no easing curves — flat fills and hard edges throughout. `[ASSUMPTION: this reading of "retro arcade/terminal" — brief named the mood, not the execution]`

## Colors

The base is near-black (`{colors.surface-bg}`, `{colors.board-bg}`) — the board itself is pure black, like an unlit CRT. UI chrome (borders, HUD text, labels) uses phosphor green (`{colors.outline}` / `{colors.text-primary}`) — the canonical terminal color, used for every non-piece visual element so the seven piece colors read as the only "loud" color in the frame. `{colors.text-dim}` is a darker green for de-emphasized text (e.g. a static label next to a live value). `{colors.grid-line}` is a barely-visible dark green, present only to help the eye track columns, never competing with locked pieces.

The seven tetromino colors (`piece-i-cyan` through `piece-l-orange`) are the standard Tetris Guideline palette — I-cyan, O-yellow, T-purple, S-green, Z-red, J-blue, L-orange, matching the brief exactly. These are the only saturated colors on screen; everything else is green-on-black. `[ASSUMPTION: exact hex values — brief named colors by name, not hex]`

State accents: `{colors.state-paused}` (amber) and `{colors.state-game-over}` (red) break from the green chrome deliberately — they're the only two moments the palette shifts, so a paused or ended game is unmistakable at a glance. `[ASSUMPTION]`

## Typography

One family throughout: a system monospace stack (`ui-monospace, 'Courier New', monospace`) — no web-font fetch, since the fixture must run offline via `file://` with zero dependencies. `[ASSUMPTION: font choice — the brief said "monospace," not which one; a system stack is the only option compatible with the zero-dependency/offline constraint]`

Four roles: `display` (PAUSED / GAME OVER, the only large text on screen), `heading` (HUD labels — SCORE, LEVEL, LINES, NEXT — tracked out per terminal convention), `body` (the live numeric values under each label), `label-caps` (any fine print). No italic, no serif — monospace is the entire type system.

## Layout & Spacing

Spacing scale is grid-cell-driven: `{spacing.cell}` (24px) is the board's cell size and the base rhythm everything else follows — `{spacing.unit}` (8px) for tight internal padding, `{spacing.gutter}` (16px) between the board and the HUD panel, `{spacing.panel-padding}` (12px) inside HUD/preview panels.

Layout is fixed, single arrangement: board on the left, HUD panel (score, level, lines, next-piece preview) stacked on the right — the classic Tetris arrangement. No responsive breakpoints; this is a desktop-only, keyboard-only fixture (see EXPERIENCE.md Foundation), so there is exactly one layout, not a range of them.

## Elevation & Depth

None. Flat throughout — no shadows, no tonal layering. Depth, where it exists at all, comes only from the 1px `{colors.outline}` borders separating the board from the HUD panel, and from the overlay scrims (`rgba(0,0,0,0.85)`) that dim the board on Pause and Game Over.

## Shapes

Square corners everywhere (`rounded.DEFAULT: 0px`) — board, panels, cells, overlays. `rounded.full` exists only in case a circular element is ever needed; nothing in this design currently uses it. A rounded corner would read as "modern UI," which is exactly the wrong note for a terminal aesthetic.

## Components

- **Board:** the 10×20 play grid, rendered on `<canvas>`. Pure black background, faint green grid lines, no border radius, 1px green outline around the whole board.
- **HUD panel:** fixed panel right of the board. Stacked label/value pairs (SCORE, LEVEL, LINES), each label in `heading` type, each value in `body` type directly beneath.
- **Next-Piece Preview:** small bordered panel within the HUD showing the next tetromino in its actual piece color, centered, no background pattern.
- **Pause overlay:** full-board scrim at 85% black, centered `display`-type "PAUSED" in amber, board content dimmed but still visible beneath.
- **Game-over overlay:** same scrim treatment, centered `display`-type "GAME OVER" in red, final score shown beneath in `heading` type.

→ Composition reference: `mockups/play-field.html` — renders all five components above across the Playing / Paused / Game Over states. Spine wins on conflict.

## Do's and Don'ts

- **Do** keep every surface flat, square-cornered, and monospace.
- **Do** reserve saturated color for the seven tetromino pieces; everything else stays green-on-black (or the state-accent amber/red).
- **Don't** add gradients, drop shadows, blur, or easing/motion beyond a simple line-clear flash (see EXPERIENCE.md State Patterns).
- **Don't** fetch external fonts or assets — everything must render from the single offline HTML file.
