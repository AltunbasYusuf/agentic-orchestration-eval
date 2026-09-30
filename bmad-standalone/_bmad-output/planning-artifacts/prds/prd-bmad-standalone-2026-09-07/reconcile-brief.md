# Input Reconciliation: brief.md vs prd.md

Source: `briefs/brief-bmad-standalone-2026-09-07/brief.md` (status: final)

## Coverage

| Brief section | PRD coverage |
|---|---|
| Context (purpose: workflow comparison fixture) | §0 Document Purpose, §1 Vision |
| What's Being Built | §1 Vision, §4 Features |
| Scope — In (8 items) | §4 FR-1..FR-13 (full mapping) |
| Scope — Out (6 items) | §6 Non-Goals |
| Definition of Done (manual smoke test, no console errors, no lag) | §8 Success Metrics (SM-1, SM-2), §6 Non-Goals (no automated test suite) |
| Technical Constraints (zero-dep, single file, vanilla JS ES2020+, Canvas 2D, no build tooling, offline via file://) | **Gap found — not in initial draft.** Fixed: added §5 Cross-Cutting NFRs. |
| Visual style preference (retro arcade/terminal, dark theme, monospace, classic piece colors) | **Not carried into PRD — see below.** |

## Gaps

1. **Technical Constraints (RESOLVED):** brief's deployment/runtime constraints were absent from the PRD draft. Added as §5 Cross-Cutting NFRs — Deployment/Runtime.
2. **Visual style preference (OPEN):** the brief's retro-arcade/dark-theme/monospace/classic-piece-color preference is explicitly non-binding ("preference, not a hard constraint") and qualitative — it doesn't map to a testable FR or NFR. Per PRD discipline, capabilities not implementation-level styling belong here only if load-bearing; since the brief itself marks it non-binding, recommend leaving it out of the PRD proper and letting it pass through to implementation via the brief (which remains the source of record for style) rather than restating it as a requirement. Flagging for the user to confirm this call rather than silently dropping it.
