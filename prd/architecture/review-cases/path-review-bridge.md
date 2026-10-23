# Path ↔ Review Case Bridge Policy (successor of the GSD bridge)

**Lifecycle:** `[proposed]` process contract
**Authority companions:** ADR-0024 §9 / §9a,
`prd/architecture/review-cases/continuity-contract.md` (D153),
`prd/architecture/review-cases/gsd-review-bridge.md` (historical predecessor)
**Non-authority:** does not complete Path tasks, accept findings, close TSG
rows, or claim product readiness.

## 1. Succession

This contract is the delivery-intent vocabulary for work executed under
**GSD Path** (`.project/`). The GSD-Pi bridge (`gsd-review-bridge.md`) is
frozen historical state: its `delivery:gsd:<MID>` intents remain valid as
recorded history and are not rewritten. New accepting dispositions that
expect work record exactly one delivery intent from this table:

| Intent | Meaning | When to use |
|---|---|---|
| `delivery:path:<path-task-or-milestone-id>` | Work is planned to run under GSD Path | Normal path |
| `delivery:out-of-band` | Work runs outside Path tasks (hot-fix / review wave) | Exception; must name why |
| `delivery:none` | No implementation work (docs already_satisfied, duplicate, reject, defer park) | Terminal/process dispositions |

`execution_linked.to` remains an **opaque pointer** (ADR-0024): a
`path:…` reference cites the Path task; it never mutates Path state and never
proves that the Path task completed. The application layer
(`review_case/application.py`) keeps accepting any non-empty opaque string;
no schema change is required or allowed for this succession.

## 2. Unchanged separations

The three orthogonal lifecycles of `continuity-contract.md` are untouched:

- L_review (Review Case residual) — ADR-0024 packets;
- L_delivery (execution) — Path tasks/milestones (previously GSD attempts);
- L_capability — TSG register + owning ADR lifecycle.

Success on one lifecycle never implies success on another. Fabricating Path
completion (manual `.project/STATE.md` edits, fake dispatch records, or
bypassing native transitions) is forbidden for the same reason the GSD
bridge forbade fake Attempts: it recreates the registry corruption path
rejected in M161–M166.

## 3. Recording surfaces

Docs-first, as with the predecessor: disposition or execution rationale,
session triage, or the bridge register may carry the intent; the opaque
`execution_linked.to` may cite `path:…` as reference only. Human-owned events
are recorded only from real human decisions (M210/S02 checkpoint discipline).
