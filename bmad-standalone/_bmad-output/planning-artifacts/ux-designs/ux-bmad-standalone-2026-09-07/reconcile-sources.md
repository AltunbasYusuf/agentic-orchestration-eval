# Input Reconciliation: brief.md + prd.md vs DESIGN.md/EXPERIENCE.md

## Coverage

| Source item | UX coverage |
|---|---|
| Brief: retro arcade/terminal, dark theme, monospace, classic piece colors | DESIGN.md Brand & Style, Colors, Typography |
| Brief/PRD: zero-dependency, offline `file://`, no build tooling | DESIGN.md Typography (system-font rationale), Do's and Don'ts |
| PRD Glossary (Board, Tetromino, Line Clear, Soft/Hard Drop, Next-Piece Preview, Level, Game Over) | Used verbatim throughout EXPERIENCE.md after casing fix (Line Clear, Next-Piece Preview) |
| PRD FR-1..FR-13 | Mapped into Component Patterns / State Patterns / Interaction Primitives with inline FR citations |
| PRD §7.1 (no start screen implied by FR-1) | Called out explicitly in EXPERIENCE.md IA as `[ASSUMPTION]`, not silently assumed |
| PRD Non-Goals (mobile/touch, sound, multiplayer, etc.) | Reflected as Foundation ("no touch/mobile") and Interaction Primitives ("Banned" list) |

## Gaps found and resolved

1. **Naming drift (RESOLVED):** DESIGN.md used "piece-preview" / "Piece preview"; EXPERIENCE.md and the PRD Glossary both use "Next-Piece Preview." Renamed in DESIGN.md to match exactly.
2. **Casing drift (RESOLVED):** EXPERIENCE.md's State Patterns table had "Line clear" (lowercase c); PRD Glossary defines "Line Clear." Fixed.

## Qualitative ideas check

Nothing from the brief's "build notes" framing or the PRD's workflow-comparison purpose got silently dropped — both spines' Brand & Style / Foundation sections carry that context forward rather than treating this as a generic game UI. No qualitative tone/voice content was volunteered beyond what's already reflected in Voice and Tone.
