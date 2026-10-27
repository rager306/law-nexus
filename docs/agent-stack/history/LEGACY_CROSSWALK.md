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
| M225-qrwdfv (Reference knowledge layer in Rust: ADR-0031 port with byte parity) | 🔄 active, phase `blocked`; milestone validation returned `needs-attention` (journal 2026-10-18 11:10, orchestrator stop `pause`). **The code is NOT missing** — see the note below | ✅ residual CLOSED 2026-10-26 by native Path task T004 of milestone `001-native-workflow-acceptance`: `tested_source_revision` filled (full 40-hex `61effa6efe68df1efff2c71f4bd39c4b701e434c`), pin re-bound, honest re-run recorded in `prd/migration/rust-evidence/m225-validation-rerun-m001.json`, verdict `hermetic-pass-parity-unproven` — hermetic fixture-based pass only; **corpus parity remains unproven** (44-ФЗ corpus absent from the re-run environment; no byte-parity PASS claimed). Do NOT re-implement S02 | Closed residual; no outstanding validation demand from this row | **closed by T004 (M001)** — carried obligation discharged with corpus parity explicitly unproven |
| M208-wrz6fg (Грамматика изменений и доказательная temporal вертикаль) | ⏸ paused (queue) | Full milestone; see DECISIONS.md D-records in the frozen snapshot | Unknown from projection — inspect snapshot before planning | **unmapped** |
| M217-kbike0 (Материализация graph-vector с crash consistency и citation contract) | ⏸ paused (queue) | Full milestone | Depends on M216 lineage (completed); citation contract gates | **unmapped** |
| M218-xnkwf0 (Типизированный KnowQL и безопасность генерируемого Cypher) | ⏸ paused (queue) | Full milestone | Depends on graph-vector materialization | **unmapped** |
| M219-2erzz3 (Границы доступа и доказательство полномочий) | ⏸ paused (queue) | Full milestone | Unknown from projection | **unmapped** |
| M220-djlrxl (Доказательные границы ODT и пересмотр парсерных гейтов) | ⏸ paused (queue) | Full milestone | Garant ODT corpus availability | **unmapped** |

### M225: implementation exists, the projection is stale

Three projections say "nothing is implemented" and all three are out of date.
The code is on this tree:

| Evidence | Fact |
|---|---|
| `crates/ln-consultant-parser/src/reference_layer.rs` | 94 890 bytes; `references_document`, `build_pageindex`, `pageindex_document` all present |
| `crates/ln-consultant-parser/tests/reference_layer_*.rs` | five suites, including `pageindex_document_is_byte_identical_to_the_python_reference` and `reference_layer_parity` |
| local `cargo test --workspace` (2026-10-25) | 463 suites, 3264 passed, 0 failed |

And the projections that disagree with it:

- `prd/project-state/data/roadmap.json` `current_milestone.goal` still says
  "в GSD у M225 запланировано 0 задач (S01-S03)";
- ADR-0031 carries a similar stale claim;
- the battery's own `tested_source_revision` is `pending-fill-by-validate-unit`.

Update (2026-10-27): that one narrow thing is done. Native Path task T004 of
milestone `001-native-workflow-acceptance` filled `tested_source_revision`
(full 40-hex `61effa6efe68df1efff2c71f4bd39c4b701e434c`), re-bound the pin, and
re-ran the validation surface; the receipt
`prd/migration/rust-evidence/m225-validation-rerun-m001.json` records verdict
`hermetic-pass-parity-unproven` — a hermetic, fixture-based pass at that HEAD.
Corpus parity remains unproven: the 44-ФЗ corpus was absent from the re-run
environment, corpus-bound checks are recorded `skipped-corpus-absent`, and no
byte-parity PASS is claimed.

Explicitly **not** the task: re-implementing the S02 port. A new agent handed
this crosswalk without this note would rebuild 95 KB of working, parity-tested
code.

## Historical rows with accepted blockers (not auto-transferred)

Eleven task rows across M204/M206/M207/M208/M209 hold `blocker-accepted` or
`skipped` status with recorded blocker provenance (e.g. M204/S23/T04, T06,
T09; M206/S01/T01; M207/S02/T07, S03/T06; M208/S01/T01; M209/S02/T02).
These are **historical evidence of accepted blockers**, not open work. Any
resumption is a new decision with its own scope; do not import them as
pending Path tasks.

## M210/S02 and M210/S03 — an owner decision that IS in force

**Correction (2026-10-25).** An earlier revision of this crosswalk carried only
v1 and therefore reported "no owner decision exists". That was wrong and would
have made the owner re-decide something already decided. Both checkpoints are
on this tree:

| Document | State | Standing |
|---|---|---|
| `prd/architecture/m210-s02-adoption-checkpoint.md` (v1) | `admission: not-adopted`, `owner_admission_ref: none`, `f13_status: hold` | **historical** — superseded, byte-identical, not rewritten |
| `prd/architecture/m210-s02-adoption-checkpoint-v2.md` (v2) | **`admission: granted`**, variant **C `abstention_first_candidates_only`**, `f13_status: deferred-explicit` | **in force** — the owner's authenticated interactive decision |
| `prd/architecture/m210-s03-runtime-admission.md` | **`admission: granted`**, derived from v2; explicitly states no repeat owner decision is required | **in force** |
| `prd/architecture/m210-s03-runtime-activation-delta.json` | `grant_recorded: true`, `applied: false`, `implementation_present: false`, `readiness: not-ready` | **in force** — the honest gap |

What the grant covers, exactly (v2 §Scope): source-bound candidate emission with
explicit Unknown or Conflict verdicts, i.e. candidates, source anchors,
classification hypotheses and provenance. What it does **not** cover: rule
composition, precedence resolution, facet defaults, case applicability, the
final normative-rule format, and anything in §3 of
`prd/temporal-legal-model.md`.

What the migration may therefore carry forward:

- the decision is **made**; a new agent must not re-ask it;
- the **implementation and activation are not** (`applied: false`,
  `implementation_present: false`, `readiness: not-ready`);
- F13 is `deferred-explicit`, not `hold`: amendment operations stay deferred and
  the owning slice reopens F13 with a fresh rebind before any bounded temporal
  replay relies on it.

`f13_status` and the activation delta are the two fields that keep this honest.
Neither the migration nor a Path task may raise `applied`, declare readiness, or
widen the variant beyond C. Requirement promotion and Review Case events remain
0 in both checkpoints.

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
