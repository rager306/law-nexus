---
milestone: M026-1uqmzc
slice: S01
task: T01
status: contract
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Held-out Semantic Descriptor Evaluation Contract

M026 tests whether the M025-remediated `safe_semantic_descriptor_v1` representation generalizes to held-out safe cases. The milestone is a bounded local scoring proof cycle, not requirement validation.

## Source boundary

M025 accepted `safe_semantic_descriptor_v1` only as bounded local scoring evidence. M026 may reuse the representation format, verifier concepts, local runtime boundary, and review discipline, but must not reuse M025 design cases as acceptance evidence.

Accepted prior inputs:

```text
prd/research/ontology_architecture_requirements/49-semantic-descriptor-derivation-remediation-proof.md
prd/research/ontology_architecture_requirements/50-m025-remediation-independent-review.md
prd/research/ontology_architecture_requirements/51-m025-final-cycle-closeout.md
```

## Held-out independence requirements

A held-out M026 case is eligible only when all requirements below are met:

```text
held_out_case_independence_required: true
m025_design_case_reuse_forbidden: true
m022_acceptance_case_reuse_forbidden: true
expected_answer_field_input_forbidden: true
selection_reason_input_forbidden: true
one_representation_change_per_cycle: true
```

Held-out cases must not copy the M022/M025 acceptance case IDs or query/candidate IDs as acceptance evidence. If a case is derived from the same legal source family, it must use a new safe case ID and a different structural retrieval situation so the case tests generalization rather than memorized descriptor design.

Forbidden reused acceptance identifiers include prefixes and exact IDs from M025 design/acceptance artifacts:

```text
CASE-M022-
QUERY-M022-
CAND-M022-
DESCQ-M025-
DESCC-M025-
```

S02 must either reject these identifiers in held-out acceptance data or classify such rows as calibration-only, not acceptance evidence.

## Allowed safe descriptor inputs

Allowed descriptor inputs are bounded enums, safe IDs, safe hashes, and tokenized descriptor strings that do not expose raw legal content or expected answers.

Allowed examples:

```text
case_id: CASE-M026-...
query_id: QUERY-M026-...
candidate_id: CAND-M026-...
representation_kind: safe_semantic_descriptor_v1
query_descriptor_count: <integer>
candidate_descriptor_count: <integer>
descriptor_tokens: [bounded enum tokens only]
source_hash: sha256:<digest>
```

Descriptor values must be bounded enums. Free-text descriptors are forbidden.

## Forbidden leakage fields

S02/S03 verifiers and tests must reject these field names if they appear in descriptor inputs, scoring inputs, or durable proof payloads:

```text
raw_legal_text
raw_text
source_excerpt
source_excerpts
query_text
prompt
provider_payload
secret
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

Durable proof artifacts must use `external_payloads_excluded` for external payload exclusion markers.

## Forbidden string fragments

S02/S03 verifiers and tests must reject fragments that indicate raw text, paths, secrets, generated answers, or execution artifacts:

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

If a future verifier needs additional fragments, it may add them fail-closed. It must not remove these fragments without independent review.

## Runtime boundary

M026 scoring must use local/open-weight runtime only:

```text
model_id: deepvk/USER-bge-m3
local_files_only: true
observed_vector_dimension: 1024
managed_api_used: false
network_used: false
raw_vectors_persisted: false
```

If the local runtime is unavailable, the scoring step must return `blocked`. It must not fall back to GigaChat, managed embedding APIs, network calls, or external provider payloads.

## Baseline comparison rules

M026 must compare held-out metrics against both the M024 safe-token baseline and the M025 bounded descriptor result.

M024 baseline:

```text
mrr: 0.875
recall_at_1: 0.75
recall_at_3: 1.0
positive_with_distractor_relevant_first: 0.0
runtime_boundary_confirmed: 1.0
```

M025 bounded descriptor result:

```text
mrr: 1.0
recall_at_1: 1.0
recall_at_3: 1.0
positive_with_distractor_relevant_first: 1.0
runtime_boundary_confirmed: 1.0
```

Held-out metrics must be reported as observed results, not as validation claims. Expected labels, expected candidate IDs, ranks, and diagnostic expectations may be used only after scoring for metric computation, never as descriptor/scoring inputs.

## Perturbation and ablation expectations

At least one S04 perturbation or ablation proof is required before closeout.

Required markers:

```text
ablation_changes_one_signal_at_a_time: true
candidate_descriptors_fixed_unless_declared: true
fixture_fixed_unless_declared: true
metrics_policy_fixed_unless_declared: true
runtime_model_fixed: deepvk/USER-bge-m3
changed_fields_recorded: true
source_digest_recorded: true
score_digest_recorded: true
dependency_diagnosis_required: true
```

Allowed dependency diagnoses:

```text
held_out_success_survives_ablation
held_out_success_depends_on_descriptor_signal
held_out_scoring_blocked
held_out_metric_mismatch
```

## Decision vocabulary

S05 closeout must use one of these decisions:

```text
accept_bounded
revise
reject
blocked
```

`accept_bounded` means the held-out result may inform future local scoring iterations only. It does not validate R035 or product behavior.

## Review gate

R038 applies to M026. Independent review must inspect:

- held-out independence from M025 design cases;
- forbidden field and fragment rejection;
- raw text/vector and external payload exclusion;
- local runtime boundary;
- metric computation after scoring;
- perturbation/ablation provenance;
- stale artifact markers;
- R035 and product-quality overclaims.

## Non-claims

M026 must not claim:

- R035 validation;
- product retrieval quality;
- legal-answer correctness;
- legal interpretation authority;
- parser completeness;
- parser-to-EvidenceSpan materialization;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- pilot readiness;
- managed embedding API authorization.

R035 remains active and not validated unless a separate broader proof milestone explicitly satisfies its architecture proof gates. R038 remains active as a standing independent proof-review gate.

## S02 handoff checklist

S02 must produce or verify these markers before scoring can begin:

```text
schema_version: held-out-semantic-descriptor-inputs/v1
representation_kind: safe_semantic_descriptor_v1
held_out_case_independence_required: true
m025_design_case_reuse_forbidden: true
forbidden_field_rejection_verified: true
forbidden_fragment_rejection_verified: true
local_runtime_boundary_declared: true
r035_non_validation_declared: true
r038_review_required: true
```
