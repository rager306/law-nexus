# Architecture Remediation Matrix

> **Scope:** Derived, non-authoritative R04/M007 planning artifact. It classifies open proof gates and R04 recommendations so downstream work can be split safely. It does not prove product readiness.

## Summary

| Metric | Count |
| --- | ---: |
| Unresolved proof gates | 7 |
| R04 recommendations | 18 |

| Disposition | Gate Count |
| --- | ---: |
| defer | 0 |
| product-decision | 2 |
| proof-now | 2 |
| runtime-experiment | 3 |

## Gate Remediation Rows

| Gate | Layer | Risk | Disposition | R04 Links | Next Proof Artifact | Target Track |
| --- | --- | --- | --- | --- | --- | --- |
| `GATE-EMBEDDING-SUPPLY-CHAIN` | security-safety | high | runtime-experiment | R04-REC-003 | Embedding supply-chain experiment report with model revision/checksum, local runtime envelope, vector dimensions, and no-secret/no-raw-vector leakage checks. | M007/S03 retrieval-embedding track |
| `GATE-G005` | temporal-model | high | product-decision | R04-REC-006 | Temporal conflict policy plus fixture-backed same-date/new-edition/source-revision tests. | M007/S03 temporal-model track |
| `GATE-G008` | parser-ingestion | high | proof-now | R04-REC-005 | Parser/retrieval golden-test suite using tracked parser records and explicit no-answer/non-claim cases. | M007/S03 parser-retrieval track |
| `GATE-G011` | retrieval-embedding | high | runtime-experiment | R04-REC-004, R04-REC-014 | Retrieval quality and migration experiment report with dataset skeleton, metrics, fallback boundaries, and explicit non-readiness result states. | M007/S03 retrieval-embedding track |
| `GATE-G015` | graph-runtime | medium | runtime-experiment | R04-REC-004 | Runtime migration smoke proof with import package, graph load shape, rollback/failure diagnostics, and non-production boundary. | M007/S03 graph-runtime track |
| `GATE-GENERATED-CYPHER-SAFETY` | generated-cypher | critical | proof-now | R04-REC-003, R017 | Generated-Cypher validator suite covering read-only enforcement, schema grounding, evidence-returning queries, injection rejection, and unsafe write rejection. | M007/S03 generated-cypher track |
| `GATE-LEGAL-NEXUS-ACCESS-CONTROL` | security-safety | high | product-decision | R04-REC-003 | Legal Nexus access-control decision and negative-test plan defining caller roles, authorization boundaries, audit logging, and denied-operation diagnostics. | M007/S03 api-product/security track |

## Gate Non-Claims

| Gate | Non-Claims |
| --- | --- |
| `GATE-EMBEDDING-SUPPLY-CHAIN` | Does not promote any embedding model to product default.; Does not allow managed embedding API fallback.; Does not prove retrieval quality. |
| `GATE-G005` | Does not specify temporal storage implementation.; Does not validate temporal conflict resolution.; Does not prove import runtime behavior. |
| `GATE-G008` | Does not prove parser completeness.; Does not prove citation-safe retrieval.; Does not prove legal-answer correctness. |
| `GATE-G011` | Does not prove product retrieval quality.; Does not commit to a vector store topology.; Does not validate FalkorDB production scale. |
| `GATE-G015` | Does not prove FalkorDB production loading behavior.; Does not prove production scale.; Does not prove product ETL readiness. |
| `GATE-GENERATED-CYPHER-SAFETY` | Does not prove provider generation quality.; Does not authorize executing raw generated Cypher.; Does not validate product Legal KnowQL readiness. |
| `GATE-LEGAL-NEXUS-ACCESS-CONTROL` | Does not assert current product is insecure.; Does not prove access-control enforcement.; Does not define a production API surface. |

## R04 Recommendation Disposition

| Recommendation | Priority | Status | Next |
| --- | --- | --- | --- |
| `R04-REC-001` — Populate three empty schema layers | blocker | implemented-s01 | Keep as coverage baseline; do not treat one record per layer as completeness. |
| `R04-REC-002` — Connect orphan nodes via existing edge types | blocker | implemented-s01 | Keep connectivity visible in graph report; reassess if new orphan findings appear. |
| `R04-REC-003` — Add explicit proof gates for critical product surfaces with no records | blocker | implemented-s01-open-gates | Use proof-gate rows to split concrete product/runtime proof work. |
| `R04-REC-004` — Project source PRDs into requirement records | major | downstream-s03 | Project FR/NFR coverage only after S02 matrix classifies current gates and deferrals. |
| `R04-REC-005` — Bridge architecture registry to prd/parser/ evidence | major | implemented-s01 | Use parser bridge records as inputs for parser/retrieval golden-test proof. |
| `R04-REC-006` — Add temporal data_entity and temporal requirement records | major | implemented-s01 | Use temporal records as inputs for temporal conflict policy and fixture tests. |
| `R04-REC-007` — Tighten anchor stability with line ranges or quote_hash | minor | defer-s04 | Handle anchor line ranges/quote hashes as a minor hardening pass. |
| `R04-REC-008` — Document schema evolution policy | minor | defer-s04 | Document schema evolution policy after blocker/major proof tracks are split. |
| `R04-REC-009` — Disambiguate claims ledger by claim domain | minor | implemented-s01 | Claims ledger now includes claim-domain separation. |
| `R04-REC-010` — Consolidate or differentiate health dashboard and architecture report | minor | defer-s04 | Decide report/dashboard roles in minor recommendation disposition. |
| `R04-REC-011` — Document edge confidence semantics or remove the field | minor | defer-s04 | Document edge confidence semantics or schedule schema v2 work. |
| `R04-REC-012` — Add CI/regenerate hook documentation | minor | defer-s04 | Document CI/regenerate hook recipe after matrix/check workflow stabilizes. |
| `R04-REC-013` — Strengthen identifier conventions per record kind | minor | defer-s04 | Decide schema-level versus extractor-level ID prefix enforcement. |
| `R04-REC-014` — Add coverage metrics to views generator | minor | downstream-s03 | Use coverage metrics only with explicit non-readiness caveat. |
| `R04-REC-015` — Connect RISK-OVERCLAIM-RUNTIME to threatened records via risks edges | minor | partially-implemented-s01 | S04 should decide whether additional risks edges are necessary or whether current coverage is sufficient. |
| `R04-REC-016` — Either populate or fixture-test contradicts and supersedes branches | minor | defer-s04 | Fixture-test contradiction/supersession branches without adding fake production edges. |
| `R04-REC-017` — Make verifier output state what success does not mean | minor | partially-implemented-s01 | Verifier summary has a non-authoritative boundary; S04 can decide whether to add a longer CLI prose card. |
| `R04-REC-018` — Document .gsd/ stability assumption or introduce a path-mapping layer | minor | defer-s04 | Document .gsd path stability assumption or path-mapping response procedure. |

## Non-Claims

- This matrix is a planning artifact, not product readiness evidence.
- Disposition classes prioritize proof work; they do not validate runtime behavior.
- Open proof gates remain unresolved until their next_proof_artifact is produced and verified.
- Resolving all R04 recommendations does not prove legal-answer correctness, parser completeness, retrieval quality, generated-Cypher safety, FalkorDB production behavior, or LLM legal authority.

---

*Generated from `architecture_graph_report.json`, `architecture_items.jsonl`, and R04 recommendations. Source evidence remains authoritative.*
