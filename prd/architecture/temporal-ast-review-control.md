# Temporal AST review control (2026-08-28)

**Lifecycle:** `[proposed]` process inventory  
**Authority companions:** `prd/ARCHITECTURE.md`, ADR-0016 / ADR-0017 / ADR-0018,
`prd/temporal-legal-model.md` §3, `prd/architecture/model-crystal.md`  
**Non-authority:** this file does not close TSG rows, mint Rust types, promote
lifecycle, adopt SHACL/SPARQL as runtime, or replace the glossary. Informal
session label **CSM** is not a third tree: the crystal contour is CST (green
source tree) plus AST (red semantic tree). Machine catalog:
`prd/architecture/temporal-ast-review-control.yaml` (`authoritative: false`).
Governor consumption is the existing check `kb-ontology-draft` (D272: no new
`check_id`).

## 1. What was reviewed

The executable temporal assembly of one normative act (`assembly_fsm` →
`S_ready_bounded`) versus the crystal compiler formula (ledger +
MicroOperation → LegislativeEffect + bitemporal checkout). Sources: Review 9
(`doc/review/review-20-08-2026.md`), ADR-0009/0013/0016–0023, the TSG register,
KBO requirements, and runtime `ln-temporal` / `ln-kb-ontology`.

Canon remains `AST(t) = fold(events ≤ t)`. An EditionOracle is a checksum, not
history. Three L2 canons plus force stay uncollapsed.

## 2. Findings D-01..D-14

| ID | Class | Finding | Status | Honest next |
|---|---|---|---|---|
| D-01 | process-logic | 44-ФЗ registry snapshot (edition-0118) treated as the CC universe | open-bounded | `grow_identity` TDD on synthetic snapshots; not C0; not 118 XML; inspect still uses 0118 lookup |
| D-02 | ontology | Runtime `force_status_values` members differed from ADR-0018 `written_statuses` | closed-bounded | bounded enum alignment landed (M188 member match); not interval algebra |
| D-03 | design-vs-code | Crystal compiler types absent from `src/` | open-bounded | bounded three-canon event log + point fold landed (M190, `ln-temporal`); ledger/MicroOperation/checkout still absent; do not mint from YAML |
| D-04 | docs-drift | MC-SEL historical list still names `ForRelationsAfter` as a selector | open-honesty | living overlay only |
| D-05 | process | `S_ready_bounded` ≠ readiness O-state | documented | keep two FSMs |
| D-06 | docs | living vs historical plane names | documented | no third name layer |
| D-07 | homonym | `EvidenceSpan` vs `ln-decode::EvidenceAnchor` | documented | keep pinned qualifier |
| D-08 | overclaim | coverage % ≠ CoverageCertificate | documented | INV-22 |
| D-09 | process | C1 files on disk ≠ `legislative` events | open | overlay after WALK-I; 484 ≠ R070 |
| D-10 | honesty | edition-0001 ≠ proven C0 | documented | Coverage into the past is Unknown |
| D-11 | false-green | closed-vocab subset can pass on the wrong six members | open-honesty | observe member mismatch in `kb-ontology-draft` |
| D-12 | evidence | TL-GC 19 vs GC-001..040 | documented | count separately |
| D-13 | architecture | `ln-kb-ontology` has no hexagon ports | open | before O4 writes |
| D-14 | dependency | parser G1 vs assembly S3 | documented | S4 needs decode quality |

## 3. Recursion verdict

Three orthogonal walks (Review 9). Mixing them is the same class of error as
collapsing the three L2 canons.

| Walk | Over | Runtime today |
|---|---|---|
| WALK-T | edition chain of one Work | two named pairs only (0001→0002 text; 0080→0081 structure) |
| WALK-S | markers of one snapshot | partial: YAML `recursive` + `max_depth` + propose rank |
| WALK-I | first appearance of a marker key | **not executed**; identity still projected from the latest snapshot |

Recursive *design* is WALK-T: `build(chain[0..k-1]); step(chain[k])`. Recursive
*runtime history of the Work* is not landed. Marker nesting is not identity.

## 4. SHACL + SPARQL verdict

**Anti-runtime.** SHACL validates instance shape of an already materialized
RDF graph. SPARQL queries that graph. Neither grows WALK-I, proves INV-01
replay hashes, nor encodes fail-closed `Unknown` as a typed refusal.
Open-world absence ≠ our `Unknown`. Encoding current YAML force members into
shapes would cement D-02.

de Martim holds ontology by **reifying** Temporal Versions and events in
LRMoo, not by a SHACL runtime. law-nexus keeps Work stable (TV is not a new
Work; Review 4 / ADR-0016). RDF+SHACL may appear later only as a D046 L6
compatibility export, `authoritative: false`, after WALK-I and force-set
alignment. Archive ACP/git-lex RDF (R066) is not a return path.

## 5. Next-wave order (product, not process leftover)

```text
WALK-I from earliest oracle
  → durable three-canon event log (landed M190, bounded)
  → align force-status members (D-02; landed M188)
  → C1 legislative overlay (P9 macro/micro)
  → only then crystal ledger / compiler / checkout
forbidden now: SHACL runtime, Applicable product, RuVector as ontology canon,
  0118-as-CC-universe, CSM as a third tree
```

Process leftover (CID-A durable adapters, G1 blocked, R070 named-open, G2 vs
P2 human-gated) remains valid and orthogonal. `current_milestone` stays
M185 until M186 complete-milestone. No new Governor `check_id` (D272).

## 6. Governor consumption (existing check)

`kb-ontology-draft` observes:

- review-control catalog present with `authoritative: false` and findings D-01..D-14;
- runtime `force_status_values` versus living `written_statuses` compared **by member**, not by length;
- while members differ, required honesty fragment
  `a cardinality match is not a member match` must appear on the YAML catalog
  and the force-interval contract;
- since M188 the runtime members align (snake_case) to the living
  `written_statuses`, so the member-compare observes a match and the fragment
  is no longer required on the data surfaces; it stays in `honesty_fragments`
  as the unconditional catalog row the check always requires.

Missing honesty while members differ → advisory warn on the **existing**
check. Member match → PASS `observed` records `force_set_honesty=ok`.
Fixture roots without the review-control file skip the overlay.

## 7. Non-claims

- Not TSG S6, not O3, not Applicable, not RuVector product.
- Not a SHACL/SPARQL runtime plan.
- Not a rewrite of historical MC-SEL / ADR-0009 seven-name lists.
- Not R070 closure. Not 484-ФЗ legislative evidence class.
