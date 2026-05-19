---
milestone: M022-5t4bzn
slice: S04
status: assessment
requirement_scope:
  - R035
non_authoritative: true
created_at: 2026-05-18
---

# M022 Representative Retrieval Quality Assessment

M022 expanded the M021 EvidenceSpan retrieval proof horizon from a six-case golden fixture to a ten-case representative corpus with bounded local/open-weight metrics. The milestone advances R035, but R035 remains active and not validated.

## Evidence compared

| Horizon | Evidence | What it proves | What it does not prove |
| --- | --- | --- | --- |
| M021/S04 | `prd/research/ontology_architecture_requirements/20-evidence-span-golden-retrieval-contract.md` and `prd/research/ontology_architecture_requirements/21-evidence-span-golden-retrieval-proof.md` | A six-case golden EvidenceSpan/SourceBlock fixture can express positive, stale, ambiguous, unsupported, and scoped no-answer retrieval expectations using safe IDs. | Representative retrieval quality, parser completeness, product retrieval, legal-answer correctness. |
| M021/S05 | `prd/research/ontology_architecture_requirements/23-evidence-span-local-retrieval-metrics-proof.md` | The approved local/open-weight `deepvk/USER-bge-m3` runtime produced bounded fixture metrics with observed 1024-dimensional vectors and no managed API fallback. | Product-quality retrieval, broad corpus robustness, graph-vector/HNSW behavior, raw vector persistence policy beyond the proof. |
| M021/S06 | `prd/research/ontology_architecture_requirements/25-graph-filtered-retrieval-integration-proof.md` | Safe fixture graph materialization can preserve citation bindings and apply ontology/temporal filtering over the six-case fixture. | Production FalkorDB behavior, graph-vector or hybrid retrieval quality, large-scale graph ingest. |
| M021/S07 | `prd/research/ontology_architecture_requirements/26-m021-lifecycle-horizon-assessment.md` and `prd/research/ontology_architecture_requirements/27-m021-final-verification-report.md` | M021 passed its bounded proof chain and left R035 active / strongly advanced, not validated. | R035 validation. |
| M022/S01 | `prd/research/ontology_architecture_requirements/28-representative-retrieval-quality-contract.md` | Defines a stricter representative-corpus contract with at least ten case classes, stable source anchors, redaction, metrics, runtime boundary, diagnostics, and non-claims. | Any runtime or quality result by itself. |
| M022/S02 | `prd/research/ontology_architecture_requirements/29-representative-evidence-span-corpus-proof.md` | A ten-case representative EvidenceSpan corpus fixture exists with required classes, safe IDs/hashes, stable source anchors, verifier, tests, and no raw text/vector/provider/runtime payloads. | Retrieval metrics or runtime quality. |
| M022/S03 | `prd/research/ontology_architecture_requirements/30-representative-evidence-span-metrics-proof.md` and `prd/research/ontology_architecture_requirements/representative_evidence_span_retrieval_metrics_proof.json` | The ten-case representative fixture met bounded deterministic metrics under the approved local/open-weight runtime boundary. | Product retrieval quality, parser completeness, legal-answer correctness, production readiness, graph-vector/HNSW or hybrid retrieval behavior. |

## What M022 added beyond M021

M022 added four concrete increments beyond M021:

1. Representative breadth increased from six golden cases to ten required classes.
2. The representative fixture includes `positive_with_distractor`, `citation_preservation_boundary`, `edition_mismatch_negative`, and `unsafe_payload_boundary` coverage beyond the M021 seed shape.
3. The S03 evaluator fail-closed on an actual fixture mismatch: the rank-2 distractor was not explicitly listed as rejected. The fixture was refined and re-verified before metrics passed.
4. The final metrics proof confirmed the same approved local/open-weight runtime boundary: `deepvk/USER-bge-m3`, `confirmed_runtime`, observed dimension `1024`, no managed API, no raw vector persistence, and no network use.

## Metrics outcome

M022/S03 produced these bounded representative fixture metrics:

```text
mrr: 1.0
recall_at_1: 1.0
recall_at_3: 1.0
distractor_rejection_rate: 1.0
stale_rejection_rate: 1.0
ambiguous_preservation_rate: 1.0
unsupported_scope_accuracy: 1.0
no_answer_accuracy: 1.0
citation_preservation_rate: 1.0
unsafe_rejection_rate: 1.0
runtime_boundary_confirmed: 1.0
```

These are deterministic fixture metrics, not product-quality metrics.

## R035 lifecycle assessment

Recommended R035 state after M022:

```text
active / strongly advanced with representative fixture metrics, not validated
```

Rationale:

- M020 normalized proof gates and lifecycle wording.
- M021 proved a bounded ingest-to-retrieval chain over safe EvidenceSpan fixtures.
- M022 expanded the retrieval-quality corpus to ten representative cases and verified bounded metrics with the approved local/open-weight runtime.
- The remaining R035 scope still includes proof gates that M022 did not and should not claim.

## Remaining R035 gaps

R035 remains open because these areas are not yet proven:

- parser-to-EvidenceSpan materialization from real source extraction;
- product retrieval quality over a larger and less curated corpus;
- legal-answer correctness;
- generated-query safety if generated queries become part of the product workflow;
- graph-vector/HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB behavior;
- production ingest behavior and resource profile;
- pilot or 1000-document readiness;
- registry extractor integration and regenerated registry outputs where required by R035 wording.

## R037 lifecycle assessment

M022 should not materially change R037. M022 did not add new FalkorDB ingest-scale evidence beyond M021's LOAD CSV, tiny bulk-loader smoke, and safe fixture graph materialization. R037 should remain:

```text
active / partially evidenced
```

## Safety and redaction boundary

M022 durable artifacts exclude:

- raw legal text;
- raw query text;
- source excerpts;
- raw vectors or embedding arrays;
- external provider payloads;
- generated answer prose;
- generated query/Cypher text;
- secrets;
- absolute paths;
- temporary paths;
- `.gsd/exec` paths as durable fixture anchors;
- raw FalkorDB rows.

## Non-claims

M022 does not claim:

- R035 validation;
- R037 validation;
- product retrieval quality;
- parser completeness;
- legal-answer correctness;
- legal interpretation authority;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- bulk-loader production readiness;
- pilot or 1000-document readiness;
- managed embedding API authorization.

## Next proof horizon

The next useful horizon is no longer another curated fixture-only metric pass. The next proof should connect representative EvidenceSpan retrieval to real parser/materialization outputs or broaden the corpus under a new threshold contract that explicitly handles non-curated ambiguity, failure classes, and reviewable legal-answer boundaries.
