# Architecture Closure Roadmap

> **Scope:** Derived, non-authoritative M007/R04 closure artifact. It records architecture-governance closure and future proof destinations; it does not prove product readiness.

## Closure Statement

M007 closes R04 architecture governance triage, coverage, matrix, and track-split planning; it does not close product/runtime proof gates.

## Summary

| Metric | Count |
| --- | ---: |
| R04 recommendations | 18 |
| Future proof tracks | 6 |
| Assigned open gates | 7 |

### Recommendation Buckets

| Bucket | Count |
| --- | ---: |
| completed-in-m007 | 5 |
| completed-in-m007-with-open-gates | 1 |
| deferred-minor | 8 |
| future-proof-track | 2 |
| partial-follow-up | 2 |

## R04 Recommendation Final Disposition

| Recommendation | Priority | M007 Status | Final Bucket | Next |
| --- | --- | --- | --- | --- |
| `R04-REC-001` — Populate three empty schema layers | blocker | implemented-s01 | completed-in-m007 | Keep as coverage baseline; do not treat one record per layer as completeness. |
| `R04-REC-002` — Connect orphan nodes via existing edge types | blocker | implemented-s01 | completed-in-m007 | Keep connectivity visible in graph report; reassess if new orphan findings appear. |
| `R04-REC-003` — Add explicit proof gates for critical product surfaces with no records | blocker | implemented-s01-open-gates | completed-in-m007-with-open-gates | Use proof-gate rows to split concrete product/runtime proof work. |
| `R04-REC-004` — Project source PRDs into requirement records | major | downstream-s03 | future-proof-track | Project FR/NFR coverage only after S02 matrix classifies current gates and deferrals. |
| `R04-REC-005` — Bridge architecture registry to prd/parser/ evidence | major | implemented-s01 | completed-in-m007 | Use parser bridge records as inputs for parser/retrieval golden-test proof. |
| `R04-REC-006` — Add temporal data_entity and temporal requirement records | major | implemented-s01 | completed-in-m007 | Use temporal records as inputs for temporal conflict policy and fixture tests. |
| `R04-REC-007` — Tighten anchor stability with line ranges or quote_hash | minor | defer-s04 | deferred-minor | Handle anchor line ranges/quote hashes as a minor hardening pass. |
| `R04-REC-008` — Document schema evolution policy | minor | defer-s04 | deferred-minor | Document schema evolution policy after blocker/major proof tracks are split. |
| `R04-REC-009` — Disambiguate claims ledger by claim domain | minor | implemented-s01 | completed-in-m007 | Claims ledger now includes claim-domain separation. |
| `R04-REC-010` — Consolidate or differentiate health dashboard and architecture report | minor | defer-s04 | deferred-minor | Decide report/dashboard roles in minor recommendation disposition. |
| `R04-REC-011` — Document edge confidence semantics or remove the field | minor | defer-s04 | deferred-minor | Document edge confidence semantics or schedule schema v2 work. |
| `R04-REC-012` — Add CI/regenerate hook documentation | minor | defer-s04 | deferred-minor | Document CI/regenerate hook recipe after matrix/check workflow stabilizes. |
| `R04-REC-013` — Strengthen identifier conventions per record kind | minor | defer-s04 | deferred-minor | Decide schema-level versus extractor-level ID prefix enforcement. |
| `R04-REC-014` — Add coverage metrics to views generator | minor | downstream-s03 | future-proof-track | Use coverage metrics only with explicit non-readiness caveat. |
| `R04-REC-015` — Connect RISK-OVERCLAIM-RUNTIME to threatened records via risks edges | minor | partially-implemented-s01 | partial-follow-up | S04 should decide whether additional risks edges are necessary or whether current coverage is sufficient. |
| `R04-REC-016` — Either populate or fixture-test contradicts and supersedes branches | minor | defer-s04 | deferred-minor | Fixture-test contradiction/supersession branches without adding fake production edges. |
| `R04-REC-017` — Make verifier output state what success does not mean | minor | partially-implemented-s01 | partial-follow-up | Verifier summary has a non-authoritative boundary; S04 can decide whether to add a longer CLI prose card. |
| `R04-REC-018` — Document .gsd/ stability assumption or introduce a path-mapping layer | minor | defer-s04 | deferred-minor | Document .gsd path stability assumption or path-mapping response procedure. |

## Future Proof Tracks

| Track | Status | Gates | Proof Artifact | Next Unit |
| --- | --- | --- | --- | --- |
| `TRACK-GENERATED-CYPHER-SAFETY` — Generated-Cypher validator safety proof | planned-proof | GATE-GENERATED-CYPHER-SAFETY | Validator suite report covering read-only enforcement, schema grounding, evidence-returning queries, injection rejection, and unsafe write rejection. | Future generated-Cypher safety proof slice before R017 validation. |
| `TRACK-PARSER-RETRIEVAL-GOLDEN` — Parser/retrieval golden-test proof | planned-proof | GATE-G008 | Golden-test suite over tracked parser records with expected no-answer and non-claim cases. | Future parser/retrieval proof slice using M006 artifacts. |
| `TRACK-TEMPORAL-SEMANTICS` — Temporal conflict semantics decision and tests | needs-product-decision | GATE-G005 | Temporal policy decision plus fixture tests for idempotent replay, source revision, new edition, and metadata conflict cases. | Future temporal semantics decision/proof slice. |
| `TRACK-LEGAL-NEXUS-ACCESS-CONTROL` — Legal Nexus access-control boundary | needs-product-decision | GATE-LEGAL-NEXUS-ACCESS-CONTROL | Access-control decision record and negative-test plan for import operators, query users, reviewers, and administrators. | Future Legal Nexus API/access-control design slice. |
| `TRACK-RETRIEVAL-EMBEDDING-EXPERIMENT` — Retrieval quality and local embedding experiment | needs-runtime-experiment | GATE-EMBEDDING-SUPPLY-CHAIN, GATE-G011 | Local embedding/retrieval experiment report with model provenance, revision/checksum, resource envelope, dataset skeleton, metrics, and leakage checks. | Future retrieval/embedding experiment slice. |
| `TRACK-RUNTIME-MIGRATION-SMOKE` — Runtime migration/import smoke proof | needs-runtime-experiment | GATE-G015 | Runtime migration smoke report with import package, graph load shape, rollback/failure diagnostics, and explicit non-production boundary. | Future runtime migration smoke slice. |

## Non-Claims

- M007 closure does not prove product readiness.
- M007 closure does not retire generated-Cypher, access-control, parser/retrieval, temporal, embedding, or runtime migration proof gates.
- M007 closure does not prove legal-answer correctness, parser completeness, retrieval quality, FalkorDB production behavior, or LLM legal authority.
- Future tracks are planning destinations, not completed implementation slices.

---

*Generated from `prd/architecture/remediation_matrix.json` and `prd/architecture/major_track_split.json`. Source evidence remains authoritative.*
