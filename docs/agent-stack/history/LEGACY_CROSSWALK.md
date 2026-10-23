# Legacy GSD-Pi crosswalk (frozen snapshot 2026-10-23)

**Status:** migration artifact (MIGRATION.md §7.1)
**Source:** frozen GSD-Pi snapshot `/root/.gsd/projects/3495c0714df3`
(consistent DB snapshot + STATE.md + journal), private backup id
`3a691ee67857bf153ceaa0cf93d23757ee2330cfcd70b4444247a6800a433d50`.
**Non-authority:** this crosswalk records observed delivery state only. It
does not complete Path tasks, accept Review Case findings, promote
requirements, or convert legacy done into new done. New Path tasks are created
only through native Path planning with their own IDs; legacy IDs stay legacy.

## Active obligations observed in the frozen snapshot

| Legacy identity | Observed state | Remaining work | Dependencies / approvals | New mapping |
|---|---|---|---|---|
| M225-qrwdfv (Reference knowledge layer in Rust: ADR-0031 port with byte parity) | 🔄 active, phase `blocked`; milestone validation returned `needs-attention` (journal 2026-10-18 11:10, orchestrator stop `pause`) | Resolve the M225 validation attention (re-run `gsd_validate_milestone` with current structured evidence or record the honest remediation), then closeout; S03 plan D788 lists T01–T07 with T06 battery JSON already on disk (commit 12599fd6) | Owner validation decision; no running Attempt at freeze | **unmapped** — carry as the first active obligation; re-plan natively in Path after bootstrap |
| M208-wrz6fg (Грамматика изменений и доказательная temporal вертикаль) | ⏸ paused (queue) | Full milestone; see DECISIONS.md D-records in the frozen snapshot | Unknown from projection — inspect snapshot before planning | **unmapped** |
| M217-kbike0 (Материализация graph-vector с crash consistency и citation contract) | ⏸ paused (queue) | Full milestone | Depends on M216 lineage (completed); citation contract gates | **unmapped** |
| M218-xnkwf0 (Типизированный KnowQL и безопасность генерируемого Cypher) | ⏸ paused (queue) | Full milestone | Depends on graph-vector materialization | **unmapped** |
| M219-2erzz3 (Границы доступа и доказательство полномочий) | ⏸ paused (queue) | Full milestone | Unknown from projection | **unmapped** |
| M220-djlrxl (Доказательные границы ODT и пересмотр парсерных гейтов) | ⏸ paused (queue) | Full milestone | Garant ODT corpus availability | **unmapped** |

## Historical rows with accepted blockers (not auto-transferred)

Eleven task rows across M204/M206/M207/M208/M209 hold `blocker-accepted` or
`skipped` status with recorded blocker provenance (e.g. M204/S23/T04, T06,
T09; M206/S01/T01; M207/S02/T07, S03/T06; M208/S01/T01; M209/S02/T02).
These are **historical evidence of accepted blockers**, not open work. Any
resumption is a new decision with its own scope; do not import them as
pending Path tasks.

## Human-authority gates that do not transfer (M210/S02)

`prd/architecture/m210-s02-adoption-checkpoint.md` records
`admission: not-adopted`, `owner_admission_ref: none`, `f13_status: hold`,
`runtime_stop` active, 0 Review Case events, 0 requirements promoted, with a
byte-bound source pin. The workflow migration grants nothing here: bounded
normative IR implementation, §3 glossary edits, requirement promotion and
S03 stay blocked until a separate human owner decision on its own surface.

## Requirement projection (state only)

Frozen STATE.md header: 15 active · 45 validated · 9 deferred · 6 out of
scope. These are GSD-Pi projection numbers, not product truth; product truth
lives in `prd/ARCHITECTURE.md` + owning ADRs.

## Import rules (from MIGRATION.md §7.1)

- Legacy done is historical fact, not automatic Path done.
- An existing code commit does not prove the old Attempt completed and does
  not close a Review Case.
- Pending/deferred/hold/unknown/not-adopted never become approved by import.
- No raw Pi DB/STATE rows are copied into `.project/`; Path creates its own
  IDs and this file keeps the legacy references.
- Missing/contradictory dependencies become explicit blockers; independent
  technical work continues separately.
- L_delivery / L_review / L_capability stay separate (continuity-contract.md).
