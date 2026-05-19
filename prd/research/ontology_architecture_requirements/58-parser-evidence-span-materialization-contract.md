---
milestone: M027-vxdy7c
slice: S01
task: T01
status: contract
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Parser to EvidenceSpan Materialization Contract

M027 tests a tiny controlled path from real parsed legal source structure to safe `EvidenceSpan` and `SourceBlock` candidate records. The milestone is a bounded materialization proof, not parser completeness, product retrieval quality, or R035 validation.

## Purpose

M025 and M026 proved bounded safe descriptor scoring over controlled descriptor inputs. M027 addresses the next gap:

```text
real parsed legal source structure -> safe EvidenceSpan/SourceBlock candidate records -> safe descriptor bridge
```

The first proof target is a tiny materialization smoke. It must produce safe structural records or block honestly.

## Source evidence boundary

Allowed source evidence:

```text
controlled_repo_source: law-source/garant/44-fz.odt
parser_smoke_evidence_allowed: true
raw_content_xml_ordering_oracle_allowed: true
old_project_prior_art_only: true
```

Durable M027 artifacts must not include raw legal text copied from the source. They may include safe source identifiers, content hashes, parser diagnostic counts, bounded enums, and structural positions when those positions do not expose raw text.

## Materialized record schema

S02 materialization output must use this schema version:

```text
schema_version: parser-evidence-span-materialization/v1
milestone_id: M027-vxdy7c
representation_kind: safe_materialized_evidence_candidates_v1
```

Required root markers:

```text
source_text_excluded: true
query_text_excluded: true
raw_vectors_excluded: true
external_payloads_excluded: true
generated_answer_prose_excluded: true
generated_query_excluded: true
absolute_paths_excluded: true
gsd_exec_paths_excluded: true
r035_non_validation_declared: true
r038_review_required: true
```

Each materialized candidate record must contain only safe fields:

```text
candidate_id
candidate_kind
source_document_ref
source_document_sha256
source_anchor_id
source_anchor_sha256
source_order_index
structural_unit_kind
citation_granularity
content_role
temporal_status
materialization_method
parser_evidence_ref
non_authoritative
```

Allowed `candidate_kind` values:

```text
evidence_span
source_block
citation_boundary
temporal_scope_marker
blocked_candidate
```

Allowed `structural_unit_kind` values:

```text
document
article
clause
paragraph
table
list_item
unknown_structural_unit
```

Allowed `citation_granularity` values:

```text
act_edition
article_or_evidence_span
clause
source_block_marker
temporal_marker
unknown_granularity
```

Allowed `content_role` values:

```text
retrieval_candidate
citation_boundary
scope_boundary
temporal_boundary
blocked_unsafe
```

Allowed `temporal_status` values:

```text
current_edition
as_of_date_required
edition_consistency_required
unknown_temporal_status
```

Allowed `materialization_method` values:

```text
odt_structure_smoke
content_xml_order_anchor
parser_blocked
```

## Source anchor policy

Source anchors must be safe and reproducible:

```text
source_document_ref: law-source/garant/44-fz.odt
source_document_sha256: sha256:<digest>
source_anchor_id: SRC-M027-...
source_anchor_sha256: sha256:<digest>
source_order_index: <integer>
parser_evidence_ref: parser-smoke:<safe-id>
```

The `source_anchor_sha256` may hash a safe structural tuple. It must not be a hash of an untracked external payload or a secret. If a hash is derived from raw source structure, the raw text itself must not be persisted in the proof artifact.

## Forbidden fields

Materialization outputs, descriptor bridge inputs, scoring inputs, and durable proof artifacts must reject these field names:

```text
raw_legal_text
raw_text
source_excerpt
source_excerpts
query_text
prompt
user_prompt
provider_payload
provider_response_body
secret
secrets
vector
vectors
embedding
embedding_vector
runtime_row
falkordb_row
generated_answer_prose
generated_query
generated_cypher
legal_advice
llm_reasoning
expected_label
expected_rank
rank
expected_candidate_ids
expected_rejected_candidate_ids
expected_diagnostic_codes
selection_reason
expected_result
```

## Forbidden fragments

Durable artifacts must reject string fragments indicating raw text, path leakage, execution artifacts, secrets, or unsafe vocabulary:

```text
Федеральный закон
Статья 
raw_legal_text
source_excerpt
provider_payload
embedding_vector
expected_label
expected_candidate_ids
Bearer 
BEGIN PRIVATE KEY
api_key
.gsd/exec
/root/
/tmp/
```

Durable redaction markers must use:

```text
external_payloads_excluded
```

## Descriptor bridge handoff

S03 may derive descriptor inputs from materialized records only through safe structural fields:

```text
candidate_kind
structural_unit_kind
citation_granularity
content_role
temporal_status
materialization_method
source_order_index_bucket
```

S03 must not use expected labels, expected candidate IDs, ranks, legal-answer prose, generated queries, or raw source text as descriptor inputs.

## Scoring handoff

S04 scoring is optional. If it runs, it must preserve the existing local boundary:

```text
model_id: deepvk/USER-bge-m3
local_files_only: true
observed_vector_dimension: 1024
managed_api_used: false
network_used: false
raw_vectors_persisted: false
```

Evaluation labels, if needed, must be separate post-scoring artifacts.

## Blocked result policy

If safe materialization cannot be produced from the controlled source/parser evidence, S02 must output a blocked diagnostic rather than a synthetic success.

Allowed status values:

```text
ok
blocked
failed
```

Allowed blocked reasons:

```text
source_unavailable
parser_unavailable
raw_text_leakage_risk
schema_boundary_missing
insufficient_structural_evidence
```

## Review gate

R038 applies to M027. Independent review must inspect:

- source grounding and parser evidence refs;
- raw text leakage controls;
- safe source anchor hashes;
- materialized record schema;
- descriptor bridge derivation fields;
- optional scoring label separation;
- stale artifact markers;
- R035 and product-quality overclaims.

## Non-claims

M027 must not claim:

- R035 validation;
- parser completeness;
- legal-answer correctness;
- legal interpretation authority;
- production ETL readiness;
- product retrieval quality;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- pilot readiness;
- managed embedding API authorization.

R035 remains active and not validated unless a separate broader proof milestone explicitly satisfies its architecture proof gates. R038 remains active as a standing independent proof-review gate.

## S02 handoff checklist

S02 must produce or honestly block these markers:

```text
schema_version: parser-evidence-span-materialization/v1
representation_kind: safe_materialized_evidence_candidates_v1
source_text_excluded: true
safe_source_anchors_verified: true
materialized_candidate_count: <integer>
blocked_reason: <reason-or-none>
r035_non_validation_declared: true
r038_review_required: true
```
