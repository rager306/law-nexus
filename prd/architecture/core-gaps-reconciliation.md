# Core Gaps Reconciliation (Verified Against HEAD)

**Lifecycle:** `[bounded]` diagnostic reconciliation (non-authoritative)
**Verified against:** `main` (`1fcb7849`, 2026-11-28)
**Authority:** `prd/ARCHITECTURE.md` and `doc/adr/**`. This document records no human Review Case disposition, closes no TSG row, and promotes no ADR or product lifecycle.

## 1. Purpose

Separates **actually open** core-architecture gaps on `HEAD` from historical review findings already remediated in Rust (`M206`, `M211`, `M221`, `M222`), so engineering effort focuses on proving the Temporal CST/AST + Tokenizer/Context + `ChangeGrammar` core instead of re-auditing closed issues.

## 2. Open Review Case Findings (`review-case status`: 5 open / 35 total)

| Finding | Packet | Status in Ledger | Verified State on `HEAD` | Required Next Proof |
|---|---|---|---|---|
| **RC28-F13** | `RC-2026-09-10-001` | `open` | **True core gap (0 lines in `crates/`).** No amendment-text parser (`ChangeGrammar` / Pullenti `DecreeChange` pattern: `OWNER/KIND/CHILD/VALUE/PARAM/LOCVALUE`) producing typed `MicroOperation` candidates. M208 recorded `not-adopted` and remains parked. | Adopt `ChangeGrammar` contract + prove vertical `AmendingLaw -> MicroOperation -> Compiler Fold -> EditionOracle` (`drift=0`) on real C1 acts (`44-ФЗ` + `138-ФЗ`/`333-ФЗ`/`484-ФЗ` + non-44-ФЗ act). |
| **RC28-F16** | `RC-2026-09-10-001` | `open` | Seven R035 gates inventoried in M209; `punkt` admission remains `not-adopted` with `owner_admission_ref: none`. | Gate-specific executable integration evidence and explicit human scope decision for `punkt` admission. |
| **RC28-F17** | `RC-2026-09-10-001` | `open` | M209/M224 proved post-hoc 118-edition 44-ФЗ digest/provenance timeline, not causal compilation from amending provisions to edition deltas (`ln-temporal/src/domain.rs:2100,2320` explicitly disclaims compiler/MicroOperation). | Causal vertical replay binding amending provision, component, operation, commencement, and edition delta across >1 act. |
| **RC11-F13** | `RC-2026-08-11-001` | `open` | Intentionally deferred (`ADR-0022/0023` procurement profile). | Deferred until neutral core applicability protocol (`TSG-005/006`) advances beyond abstention-only v0. |
| **RC12-F19** | `RC-2026-08-12-001` | `open` | Living truth-oracle / trace hygiene (reconciled progressively via Compound Engineering). | Keep `prd/ARCHITECTURE.md`, `doc/adr/README.md`, and `adr-matrix.json` synchronized under `governor --fail-on-warn`. |

> **Verified already remediated in code (do not re-open blindly):** `RC28-F06` (profile-ranked sibling closure in `crates/ln-decode/src/document_context.rs:388-403`), `RC28-F07` (predicate-gated continuation in `crates/ln-decode/src/document_context.rs:1215-1230` via `npa_continuation`), `RC28-F08` (`ThisRefGrammarEvidence` propagation in `document_context.rs:546-620` and `npa_context_records.rs:517`), and `RC28-F11` (whole-token cue matching + negation scoping in `crates/ln-temporal/src/semantic_scope.rs:113-158`).

## 3. Open Post-M214 Audit Gaps (`assessment/34` & `review-29`)

| Source | Open Item | Verified State on `HEAD` |
|---|---|---|
| `assessment/34` (M221) | `semantic_acceptance = not_attempted` | Transport/seal verification (`verified_ok`) is proven, but no independent human-adjudicated golden semantic oracle exists (parser remains at G1). |
| `assessment/34` (M221) | `garant = uncovered` in `npa-corpus-acceptance-v2` | All 400 sampled corpus acceptance entries are Consultant WordML; Garant ODT has independent decoder tests + one tracked tracer (`44-fz.odt`), not multi-fixture corpus acceptance. |
| `review-29` (`R29-F06`) | Display cleaning vs retained source (`R1000`) | Retained `binData`/field codes are intentional in the lossless source substrate; display-cleaning rules remain open in `cleaned-projection-contract.md` §11. |

## 4. Cross-Cutting Structural Gaps Surfaced on `HEAD`

1. **Duplicated `document_context.rs` ownership:** `crates/ln-decode/src/document_context.rs` (1,688 lines) and `crates/ln-temporal/src/document_context.rs` (1,029 lines) both maintain document-context abstractions; consolidation behind one clear crate boundary is required before wiring `ChangeGrammar`.
2. **Deferred runtime morphology (`MorphEvidenceSet`):** `crates/ln-decode/src/lexer.rs` (`lex()`) and private `tokenize()` remain dual scanners (deliberate per ADR-0028), while dictionary/rule-backed `MorphEvidenceSet` remains deferred (`crates/ln-temporal/src/semantic_scope.rs:148`).
3. **Unresolved persistent storage fork (ADR-0014 vs ADR-0031):** `prd/ARCHITECTURE.md` carries `graph_vector=ruvector` (`[proposed]`), while `ADR-0031` references an unexecuted M217 store bake-off (`Oxigraph` / `Kuzu+DuckPGQ` / `XTDB` after D777). Resolution is intentionally sequenced *after* the Temporal CST/AST + `ChangeGrammar` vertical core proof, behind existing `ln-storage` / `ln-query` ports.
4. **Single-act multi-edition corpus bottleneck (`ADR-0031`):** In `consru_export` (36,458 cataloged documents), only `44-ФЗ` (118 editions) carries populated `edition_number` and distinguishable revision dates; proving non-hardcoded `WALK-T` / `WALK-I` requires adding at least one second dated multi-edition act or official-publication C0/C1 pair.

## 5. Non-Claims

- Does not close any `RC*` finding or `TSG-*` row.
- Does not replace `prd/ARCHITECTURE.md`, `doc/adr/**`, or `prd/architecture/capability-promotion-board.md`.
- Does not claim parser G2 readiness, legal correctness, or production storage readiness.
