---
milestone: M024-eb6mo4
slice: S01
status: contract
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-18
---

# Semantic Observed Retrieval Scoring Contract

M024 defines the proof boundary for semantic observed retrieval scoring after M023. M023 remediated the self-confirming fixture-metrics issue at the safe-ID artifact-control layer, but explicitly did not prove semantic model retrieval quality. M024 asks whether local/open-weight semantic scoring can produce observed candidate rankings from safe, redacted representations without leaking raw legal text, raw query text, raw vectors, provider payloads, or generated answer prose.

## Triggering evidence

M023 final report:

```text
prd/research/ontology_architecture_requirements/38-m023-final-verification-report.md
```

M023 independent review:

```text
prd/research/ontology_architecture_requirements/37-m023-independent-proof-review.md
```

The residual M023 limitation to address:

```text
safe_id_provenance_rule_retrieval_v1 is safe-ID rule retrieval, not semantic model retrieval quality.
```

## Purpose

M024 must answer a narrower question than product retrieval quality:

```text
Can a local/open-weight semantic scorer produce observed candidate rankings from safe redacted query and candidate representations, then compare those rankings to expected EvidenceSpan fixture answers, without storing raw text, raw vectors, provider payloads, or legal-answer prose?
```

## Evidence classes

M024 artifacts must separate these evidence classes:

| Evidence class | Meaning | Must not substitute for |
| --- | --- | --- |
| Safe semantic input | Redacted query/candidate representations built from IDs, hashes, bounded enums, and controlled terms. | Raw legal text or raw query text. |
| Runtime boundary | Local/open-weight model availability and vector dimension, with no managed API, no network fallback, and no raw vector persistence. | Retrieval quality. |
| Observed semantic scores | Candidate IDs with observed model-derived similarity scores or explicit blocked diagnostics. | Expected fixture labels/ranks. |
| Metric comparison | Metrics computed by comparing observed semantic rankings to expected fixture answers. | Fixture-derived metric calculation. |
| Independent review | Read-only review of tests, mocks, hardcodes, safe inputs, observed scores, and overclaim risk. | Implementation-authored success reports. |

## Safe semantic input requirement

S02 must create a safe input manifest. The manifest may include:

- `semantic_input_id`;
- `case_id`;
- `query_id`;
- `candidate_id`;
- `query_hash`;
- `candidate_source_ref`;
- `source_record_ids`;
- `evidence_span_id`;
- `source_block_id`;
- `citation_key`;
- `act_edition_id`;
- `case_class`;
- `query_kind`;
- `scope_id`;
- `as_of_date`;
- bounded controlled terms such as class names, query kinds, scope IDs, and diagnostic-safe enums;
- deterministic synthetic representation tokens that do not contain raw legal text or raw query text.

The manifest must not include:

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
- `.gsd/exec` durable anchors;
- raw FalkorDB rows;
- expected labels;
- expected ranks;
- expected candidate/rejected answer lists as scoring inputs.

## Scoring input boundary

The scorer may consume only safe representation strings derived from the safe input manifest. Those strings may include IDs, hashes, and bounded enums. They must not include raw source text or raw query text.

If meaningful semantic scoring is impossible without raw text, the evaluator must emit blocked diagnostics instead of weakening the contract.

Required blocked diagnostics include:

- `semantic_input_missing`
- `unsafe_semantic_input`
- `expected_answer_leakage`
- `runtime_blocked`
- `managed_api_forbidden`
- `raw_vector_persistence_forbidden`
- `semantic_scoring_blocked`
- `metric_mismatch`
- `independent_review_findings_open`

## Runtime boundary

Allowed model boundary remains:

```text
deepvk/USER-bge-m3
local_open_weight
observed_vector_dimension: 1024
```

Managed embedding APIs, hosted LLMs, remote vector services, GigaChat/GigaEmbeddings managed fallback, network downloads, and raw vector persistence are forbidden.

Runtime confirmation is necessary but insufficient. It confirms the model/environment boundary, not retrieval quality.

## Observed semantic score artifact

S03 must produce an observed semantic score artifact. It may include:

- `case_id`;
- `query_id`;
- `candidate_id`;
- `observed_rank`;
- `observed_similarity_score` rounded to a bounded precision;
- `scoring_mode`;
- `semantic_input_ref`;
- `runtime_boundary_ref`;
- `observation_status`;
- `diagnostic_codes`;
- redaction flags;
- non-claims.

It must not include raw vectors. If similarities are computed from embeddings, only rounded scalar scores and ranking positions may be persisted.

## Metric comparison requirement

Metrics must compare observed semantic rankings to expected fixture answers. The scorer must not use expected labels, expected ranks, expected candidate lists, or expected diagnostics as scoring inputs.

Expected fixture answers may be used only by the evaluator after scoring, for metric comparison.

The evaluator must reject:

- missing semantic input manifest;
- semantic input records that contain expected answers;
- semantic input records that contain raw text or vectors;
- observed score artifacts without scores/ranks;
- observed score artifacts that copy expected rank/order without scoring-mode evidence;
- runtime confirmation without observed score artifacts;
- injected runtime JSON as acceptance proof;
- product-quality wording in proof reports.

## Threshold policy

M024 may use strict thresholds only for the bounded fixture if the contract and proof report call them fixture-level semantic scoring metrics. If semantic scoring over safe ID/enumeration representations performs poorly, the result must be reported honestly as blocked or below-threshold evidence; do not retune thresholds silently.

## Independent proof-review gate

S04 must run independent subagent review before closeout. The reviewer must check:

- whether safe semantic inputs leak raw text, raw vectors, or expected answers;
- whether scoring outputs are generated from model/scorer observation rather than expected fixture order;
- whether tests are non-vacuous and fail on leakage/missing-score/runtime-block cases;
- whether runtime proof uses local/open-weight execution for acceptance;
- whether reports overstate fixture-level semantic scoring as product retrieval quality;
- whether R035 remains active/not validated.

## Requirement lifecycle boundary

M024 can advance R035 if it produces honest semantic observed scoring evidence or blocked diagnostics. It must not validate R035 unless remaining R035 proof gates are also satisfied, including parser-to-EvidenceSpan materialization, product retrieval quality, legal-answer correctness, graph-vector/HNSW or hybrid retrieval behavior, production FalkorDB behavior, pilot readiness, and registry extractor/regenerated registry outputs.

R038 remains active as a standing proof-review requirement.

## Non-claims

M024 does not claim by contract:

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

## S01 acceptance criteria

This contract is accepted only if marker verification confirms:

- it cites M023 final/review artifacts;
- it names the residual safe-ID vs semantic retrieval limitation;
- it defines safe semantic input fields;
- it forbids raw text, raw vectors, provider payloads, expected labels, and expected ranks in scoring inputs;
- it defines observed semantic score artifact requirements;
- it preserves R035 non-validation and requires independent proof review.
