# Major Architecture Proof Track Split

> **Scope:** Derived, non-authoritative M007/S03 planning artifact. It groups open proof gates into future proof tracks and does not retire any gate.

## Summary

| Metric | Count |
| --- | ---: |
| Tracks | 6 |
| Assigned gates | 7 |
| Source gates | 7 |

## Tracks

| Track | Status | Gates | R04 Links | Proof Artifact | Next Unit |
| --- | --- | --- | --- | --- | --- |
| `TRACK-GENERATED-CYPHER-SAFETY` — Generated-Cypher validator safety proof | planned-proof | GATE-GENERATED-CYPHER-SAFETY | R017, R04-REC-003 | Validator suite report covering read-only enforcement, schema grounding, evidence-returning queries, injection rejection, and unsafe write rejection. | Future generated-Cypher safety proof slice before R017 validation. |
| `TRACK-PARSER-RETRIEVAL-GOLDEN` — Parser/retrieval golden-test proof | planned-proof | GATE-G008 | R04-REC-005 | Golden-test suite over tracked parser records with expected no-answer and non-claim cases. | Future parser/retrieval proof slice using M006 artifacts. |
| `TRACK-TEMPORAL-SEMANTICS` — Temporal conflict semantics decision and tests | needs-product-decision | GATE-G005 | R04-REC-006 | Temporal policy decision plus fixture tests for idempotent replay, source revision, new edition, and metadata conflict cases. | Future temporal semantics decision/proof slice. |
| `TRACK-LEGAL-NEXUS-ACCESS-CONTROL` — Legal Nexus access-control boundary | needs-product-decision | GATE-LEGAL-NEXUS-ACCESS-CONTROL | R04-REC-003 | Access-control decision record and negative-test plan for import operators, query users, reviewers, and administrators. | Future Legal Nexus API/access-control design slice. |
| `TRACK-RETRIEVAL-EMBEDDING-EXPERIMENT` — Retrieval quality and local embedding experiment | needs-runtime-experiment | GATE-EMBEDDING-SUPPLY-CHAIN, GATE-G011 | R04-REC-003, R04-REC-004, R04-REC-014 | Local embedding/retrieval experiment report with model provenance, revision/checksum, resource envelope, dataset skeleton, metrics, and leakage checks. | Future retrieval/embedding experiment slice. |
| `TRACK-RUNTIME-MIGRATION-SMOKE` — Runtime migration/import smoke proof | needs-runtime-experiment | GATE-G015 | R04-REC-004 | Runtime migration smoke report with import package, graph load shape, rollback/failure diagnostics, and explicit non-production boundary. | Future runtime migration smoke slice. |

## Track Boundaries and Acceptance Criteria

### TRACK-GENERATED-CYPHER-SAFETY: Generated-Cypher validator safety proof

- Status: `planned-proof`
- Scope boundary: Design and verify deterministic generated-Cypher validator behavior before any product Legal KnowQL readiness claim.
- Required inputs:
  - prd/06_m002_cypher_safety_contract.md
  - R017 active requirement context
  - Current architecture generated-Cypher proof gate
- Acceptance criteria:
  - Unsafe write/mutation Cypher candidates are rejected deterministically.
  - Queries must be schema-grounded and evidence-returning before execution is allowed.
  - Negative tests cover prompt-injection and non-evidence answer paths.
- Non-claims:
  - Does not prove provider generation quality.
  - Does not authorize executing raw generated Cypher.
  - Does not validate product Legal KnowQL readiness.

### TRACK-PARSER-RETRIEVAL-GOLDEN: Parser/retrieval golden-test proof

- Status: `planned-proof`
- Scope boundary: Turn bounded M006 parser artifacts into executable golden tests without claiming parser completeness or retrieval quality.
- Required inputs:
  - prd/parser/parser_record_contract.md
  - prd/parser/odt_smoke_records.md
  - prd/parser/consultant_relation_candidates.md
  - prd/parser/parser_staging_graph.md
- Acceptance criteria:
  - Golden tests consume tracked parser artifacts rather than rescanning undocumented sources.
  - Expected evidence/citation rows are asserted for bounded fixtures.
  - No-answer and candidate-only relation behavior is explicitly tested.
- Non-claims:
  - Does not prove parser completeness.
  - Does not prove citation-safe retrieval.
  - Does not prove legal-answer correctness.

### TRACK-TEMPORAL-SEMANTICS: Temporal conflict semantics decision and tests

- Status: `needs-product-decision`
- Scope boundary: Resolve same-date/source-revision/new-edition semantics before runtime import behavior is treated as valid.
- Required inputs:
  - prd/03_PRD.md temporal/idempotent import policy
  - DATA-TEMPORAL-PROPERTY-BUNDLE
  - REQ-TEMPORAL-STATUS-SEMANTICS
- Acceptance criteria:
  - Policy distinguishes same hash replay, changed hash same edition, new edition date, and metadata conflict.
  - Tests preserve prior source/edition records rather than mutating historical evidence.
  - Diagnostics expose temporal conflict state without LLM interpretation.
- Non-claims:
  - Does not specify temporal storage implementation.
  - Does not validate temporal conflict resolution yet.
  - Does not prove import runtime behavior.

### TRACK-LEGAL-NEXUS-ACCESS-CONTROL: Legal Nexus access-control boundary

- Status: `needs-product-decision`
- Scope boundary: Define caller roles, API boundary, authorization policy, and denial diagnostics before non-local Legal Nexus/API promotion.
- Required inputs:
  - prd/03_PRD.md Legal Nexus Module
  - COMP-LEGAL-NEXUS-ORCHESTRATOR
  - GATE-LEGAL-NEXUS-ACCESS-CONTROL
- Acceptance criteria:
  - Role/capability matrix is explicit before API implementation claims.
  - Denied operations have deterministic diagnostics and audit expectations.
  - Logs and metrics boundaries exclude secrets and unauthorized raw legal text exposure.
- Non-claims:
  - Does not assert current product is insecure.
  - Does not prove access-control enforcement.
  - Does not define a production API surface.

### TRACK-RETRIEVAL-EMBEDDING-EXPERIMENT: Retrieval quality and local embedding experiment

- Status: `needs-runtime-experiment`
- Scope boundary: Evaluate local/open-weight embedding and retrieval quality candidates without managed embedding fallback or product retrieval claims.
- Required inputs:
  - prd/03_PRD.md FR-28b embedding pipeline
  - GATE-EMBEDDING-SUPPLY-CHAIN
  - GATE-G011
  - Human decision excluding managed GigaChat/GigaChat API embedding paths
- Acceptance criteria:
  - Only local/open-weight embedding candidates are considered.
  - Model provenance and vector dimensions are recorded.
  - Retrieval metrics are reported as experiment results, not product readiness.
- Non-claims:
  - Does not promote any embedding model to product default.
  - Does not allow managed embedding API fallback.
  - Does not prove product retrieval quality or FalkorDB vector scale.

### TRACK-RUNTIME-MIGRATION-SMOKE: Runtime migration/import smoke proof

- Status: `needs-runtime-experiment`
- Scope boundary: Prove a bounded import/load/migration smoke path with diagnostics before runtime migration readiness is claimed.
- Required inputs:
  - Current parser staging graph artifacts
  - Future FalkorDB load-shape recommendation
  - GATE-G015
- Acceptance criteria:
  - Smoke proof uses bounded fixture data and reports exact graph load shape.
  - Failure diagnostics include phase, last error, and rollback/remediation guidance.
  - The result remains non-production unless scale and operational checks are separately proven.
- Non-claims:
  - Does not prove FalkorDB production loading behavior.
  - Does not prove production scale.
  - Does not prove product ETL readiness.

## Global Non-Claims

- This track split is planning evidence only.
- Track assignment does not retire proof gates.
- Track assignment does not prove product readiness, legal correctness, parser completeness, retrieval quality, generated-Cypher safety, FalkorDB production behavior, or LLM authority.

---

*Generated from `prd/architecture/remediation_matrix.json`. Source evidence remains authoritative.*
