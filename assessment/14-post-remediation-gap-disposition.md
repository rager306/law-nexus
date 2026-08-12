# Post-remediation gap disposition

**Assessment date:** 2026-08-12  
**Assessed revision:** `685f8723d55dd949ab523cb35e757530b355ea62`  
**Record role:** non-authoritative repository-control assessment  
**Lifecycle:** `[bounded]`  

## 1. Scope and authority boundary

This record evaluates the criticism and remediation backlog preserved by
`assessment/13-current-head-gap-audit.md` after the bounded Governor hardening
commits through `685f872`. It is not a successor external architecture
assessment, does not reopen D150, and does not extend D150's
`accepted-with-findings` disposition beyond packet revision
`120d44be610b20ee537f402140eb3828e8e9a0f4`.

Canonical architecture authority remains `prd/ARCHITECTURE.md` plus active
`doc/adr/**`. Governor output, this assessment, GitNexus, `.gsd` projections,
derived matrices and catalogs are process evidence only. They cannot satisfy a
requirement, validate legal behavior, promote lifecycle, or prove product
readiness.

## 2. Repository-control criticism disposition

| Criticism or gap | Disposition at assessed revision | Evidence | Residual limitation |
|---|---|---|---|
| Git archive inventory could fail open | Implemented `[bounded]` | `_git_tracked_paths` in `src/law_nexus_harness/governor.py`; hostile Git inventory test in `tests/test_harness_governor.py`; commit `e41206e` | Future inventory implementations must continue to use the shared tool-error boundary. |
| Derived ADR matrix could be the sole freshness companion | Implemented `[bounded]` | `prd/architecture/document-freshness-triggers.json`; live hostile catalog test; commit `e41206e` | Structural companion presence is not semantic freshness. |
| Ontology weave depended on local `.gsd` projections | Implemented for the published ontology check `[bounded]` | `adr-doc-matrix-coverage` targets `prd/PRODUCT.md` and `prd/REQUIREMENTS.md`; commit `e41206e` | Other workflow checks may inspect `.gsd` only as process state; those inputs remain non-authoritative. |
| D150 could be read as accepting later HEADs | Documented but human-owned `[bounded]` | Revision-currentness notice in `assessment/12-final-disposition.md`; current-head audit in `assessment/13-current-head-gap-audit.md` | A successor source-bound assessment is still required before claiming acceptance of a later revision. |
| ADR-0004 overstated storage, retrieval and KnowQL completion | Paper claim narrowed `[bounded]` | `doc/adr/0004-rust-migration-decision.md`; commit `5ca95cd` | Production storage/retrieval quality and complete KnowQL execution remain unproven. |
| Published trace contract covered only a subset | Implemented structurally `[bounded]` | `published-trace-contract` covers PC-001..020 and RQ-001..020 and rejects undeclared future IDs; commits `28a51fc`, `d54ce46` | Structural trace completeness is not requirement validation. |
| Active ADR metadata used legacy `superseds` | Implemented `[bounded]` | Active ADRs use `supersedes`/`superseded_by`; `adr-supersession-graph` rejects the legacy active key; commit `28a51fc` | Historical-input parser compatibility does not authorize the key on active ADRs. |
| Temporal vocabulary and semantic gaps were not durably inventoried | Implemented as non-authoritative inventory `[bounded]` | `prd/architecture/temporal-vocabulary-contract.json`; `prd/architecture/temporal-semantic-gap-register.md`; `temporal-vocabulary-contract`; commit `5ca95cd` | Presence checks do not establish semantic correctness or runtime behavior. |
| Deterministic scanner/loader/read failures were reclassified or swallowed | Implemented for audited paths `[bounded]` | Commits `4180276`, `34fcc64`; hostile unreadable and loader/inventory tests | New check runners still require explicit positive and tool-failure contracts. |
| Findings lacked exact repository-relative evidence | Substantially implemented `[bounded]` | Commits `121d488`, `8a46378`, `d54ce46`, `1d3fbf3`, `9722808`; exact `path:line` assertions | Missing surfaces and absent expected rows correctly remain path-only; aggregate checks added later must preserve this distinction. |
| Governor checks were not selectable or inspectable | Implemented `[bounded]` | `--only`, `--check`, `--explain`, text format, `--list-checks`, `--fail-on-warn`; commit `c3c1edc` | The inventory describes process controls only. |
| Optional ADR review scheduling had no signal | Implemented as optional warn-only metadata `[bounded]` | `adr-review-date-staleness`; exact metadata-line evidence and hostile stale/invalid/unreadable/default/strict tests; commit `685f872` | No dates are required and no human review disposition is inferred. |

## 3. Remaining process and governance work

### 3.1 Human-owned successor assessment

**Status:** not implemented; intentionally human-owned.

The assessed revision is not covered by D150 acceptance. A successor assessment
must bind its questions, evidence and disposition to an exact tested source
revision. Automated Governor success cannot supply that acceptance.

**Difficulty:** high authority sensitivity. A mechanical update would risk
turning self-assessment into acceptance and laundering post-packet changes.

### 3.2 Clean-tree and commit-range freshness

**Status:** not implemented.

`document-freshness-triggers` evaluates working-tree changes. It cannot detect a
clean working tree whose latest commit changed one consequential surface without
its required companion. A future policy needs an explicit comparison base or
review window and must remain structural rather than semantic.

**Difficulty:** medium. CI, local branches, merge commits, shallow clones and an
unspecified comparison base make a universal default unsafe. This requires a
human decision on the authoritative commit range before implementation.

### 3.3 External and periodic freshness

**Status:** not implemented; intentionally human-owned.

External-assessment refresh and elapsed-time review obligations are not inferred
from repository state. Optional ADR `review_by`/`revisit_by` metadata now exposes
only explicitly declared dates; it does not create a global 90-day policy.

**Difficulty:** medium. Repository timestamps are not reliable review evidence,
and automatic expiry cannot determine whether architecture meaning changed.

### 3.4 Stage D semantic advisory input

**Status:** not implemented.

An external or LLM semantic finding intake would require a stable cited-finding
schema, non-blocking severity coercion, explicit human disposition records and
proof that no advisory finding can promote lifecycle, close a requirement or
block by itself.

**Difficulty:** medium-high. The main risk is authority laundering rather than
code complexity. Stage D should not be built without a concrete consumer and a
human-owned disposition workflow.

### 3.5 Paper-rule to Governor parity

**Status:** partial and intentionally selective.

The implemented 29-check inventory is not an assertion that every paper rule
should become executable. Heuristic and semantic rules remain advisory and may
require human interpretation.

**Difficulty:** ongoing. Converting prose into deterministic checks can create
false precision and new false-pass surfaces.

## 4. Product, runtime and legal capabilities not implemented by this remediation

The following gaps remain open under their individual rows in
`prd/architecture/temporal-semantic-gap-register.md`:

- TSG-001 and TSG-014: self-contained temporal vocabulary/event taxonomy and
  formal API/result/error contracts;
- TSG-003: Component Temporal Versioning operations and structural amendment
  semantics;
- TSG-004: runtime `NormativeState` resolution;
- TSG-005: typed `NormRule` graph model;
- TSG-006: applicability protocol runtime ownership and typed ports;
- TSG-007: normative hierarchy, competence and conflict resolution;
- TSG-008: judicial/FAS practice overlay;
- TSG-009: transitional provisions and risk;
- TSG-010: industry profiles;
- TSG-011 through TSG-016: correction, evidence, publication and related closure
  proofs described by the register.

Related production storage, RuVector/TEI behavior, parser completeness, retrieval
quality, legal-answer correctness and release readiness also remain outside this
repository-control remediation.

**Difficulty:** high. These items require Rust domain/application/port behavior,
positive and hostile contracts, representative durable fixtures, real adapter or
real-document evidence where applicable, and explicit lifecycle decisions.
Governor checks and documentation alone cannot close them.

## 5. Final bounded disposition

At revision `685f872`, the concrete Governor false-pass, trace-coverage,
metadata-normalization, optional review-date, exact-evidence and audited
fail-closed concerns from the recovered criticism are remediated in repository
control scope `[bounded]`.

The remaining work is not one undifferentiated backlog:

1. **Human authority decisions:** successor revision-bound assessment and the
   comparison base for clean-tree/commit-range freshness.
2. **Optional future repository policy:** Stage D cited semantic intake and
   selective paper-rule automation.
3. **Product/runtime/legal delivery:** the open TSG rows and their required Rust,
   hostile-fixture and real-adapter evidence.

No current Governor, assessment or catalog result validates those remaining
product/runtime/legal capabilities. D150 remains frozen to its original packet
revision, and no lifecycle promotion is made by this record.
