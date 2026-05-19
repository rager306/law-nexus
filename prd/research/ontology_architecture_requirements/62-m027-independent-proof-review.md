---
milestone: M027-vxdy7c
slice: S05
status: independent-review
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# M027 Independent Proof Review

## Verdict

```text
PASS_BOUNDED
```

M027 passes as bounded evidence that a controlled local path can materialize safe candidate records from one real repository ODT source, bridge those records into safe structural descriptors, and score those descriptors with local USER-bge-m3 while preserving redaction and label-separation boundaries.

M027 does not pass as retrieval-quality evidence and does not validate R035.

## Reviewed evidence

```text
58-parser-evidence-span-materialization-contract.md
59-parser-evidence-span-materialization-proof.md
60-materialized-descriptor-bridge-proof.md
61-materialized-descriptor-scoring-proof.md
parser_evidence_span_materialization.json
materialized_descriptor_inputs.json
materialized_descriptor_scoring_proof.json
```

## Review questions

### Q1. Did S02 safely materialize records from controlled source structure?

Verdict: pass for bounded smoke.

Evidence:

```text
source_document_ref: law-source/garant/44-fz.odt
schema_version: parser-evidence-span-materialization/v1
representation_kind: safe_materialized_evidence_candidates_v1
materialized_candidate_count: 6
safe_source_anchors_verified: true
```

The materialization proof persists safe IDs, hashes, order indexes, bounded enums, and parser-smoke references. It does not persist raw source text.

Boundary:

```text
accepted: tiny structural materialization smoke
rejected: parser completeness, legal hierarchy correctness, citation correctness
```

### Q2. Did S03 derive descriptors only from safe materialized structural fields?

Verdict: pass for bounded descriptor bridge.

Allowed derivation fields:

```text
candidate_kind
structural_unit_kind
citation_granularity
content_role
temporal_status
materialization_method
source_order_index_bucket
```

The bridge records source materialization hash and verification summary. It keeps labels and score evaluation outside descriptor inputs.

Boundary:

```text
accepted: safe materialized-derived descriptor inputs
rejected: semantic adequacy or retrieval quality
```

### Q3. Did S04 keep scoring and labels separated?

Verdict: pass for artifact-control boundary.

Evidence:

```text
post_scoring_only: true
forbidden_as_descriptor_input: true
loaded_after_score_generation: true
score_count: 36
```

Each query descriptor was ranked against all six candidate descriptors, avoiding a trivial one-candidate metric path.

Boundary:

```text
accepted: label separation and non-trivial all-candidate ranking
rejected: claim that labels represent product search tasks
```

### Q4. Did S04 preserve the local runtime boundary?

Verdict: pass.

Evidence:

```text
model_id: deepvk/USER-bge-m3
observed_vector_dimension: 1024
managed_api_used: false
network_used: false
raw_vectors_persisted: false
runtime_boundary_confirmed: 1.0
```

Boundary:

```text
accepted: local open-weight scoring runtime confirmed
rejected: managed embedding API authorization or production embedding service readiness
```

### Q5. Do the S04 metrics support retrieval-quality acceptance?

Verdict: no.

Observed metrics:

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
```

Deltas:

```text
delta_vs_m024_mrr: -0.194445
delta_vs_m026_mrr: -0.319445
delta_vs_m026_recall_at_1: -0.5
```

Interpretation:

```text
materialized structural descriptors are currently too coarse for retrieval-quality acceptance
```

The negative result is useful because it identifies the next design gap: the materialized record bridge needs additional safe discriminating structure before descriptor scoring can be considered stronger evidence.

## Findings

### Finding 1 — bounded materialization evidence is accepted

M027 establishes a safe, reproducible, and verifiable smoke path from one controlled ODT source to safe materialized candidate records.

Severity: informational.

Disposition: accepted as bounded evidence.

### Finding 2 — descriptor bridge is artifact-safe but semantically coarse

The S03 bridge correctly avoids raw text and labels, but S04 metrics show the descriptor representation is not discriminative enough across same-kind paragraph candidates.

Severity: material limitation.

Disposition: accepted as a remediation target, not as failure of artifact controls.

### Finding 3 — S04 scoring result is negative relative to M024 and M026

The metric drop is explicitly recorded and should not be hidden by retrospective representation changes inside M027.

Severity: material limitation.

Disposition: close M027 with bounded evidence and remediation recommendation.

### Finding 4 — R035 must remain active and not validated

M027 does not prove production retrieval quality, parser completeness, legal answer correctness, or end-to-end ontology architecture acceptance.

Severity: blocking for R035 validation.

Disposition: keep R035 active and not validated.

### Finding 5 — R038 review gate remains useful

The independent review caught the correct interpretation of S04: pass artifact controls, reject retrieval-quality overclaim.

Severity: process-validating.

Disposition: keep R038 active as a standing proof-review gate.

## Accepted claims

```text
M027 safely materialized six bounded candidate records from one controlled ODT source.
M027 derived safe descriptor inputs from materialized structural fields.
M027 scored materialized-derived descriptors locally with USER-bge-m3.
M027 preserved label separation and runtime boundary.
M027 produced useful negative evidence about coarse structural descriptors.
```

## Rejected claims

```text
R035 is validated.
Parser completeness is proven.
Product retrieval quality is proven.
Legal-answer correctness is proven.
Legal interpretation authority is established.
Production ETL readiness is proven.
Graph-vector or HNSW behavior is proven.
Pilot readiness is proven.
Managed embedding API authorization is proven.
```

## Recommended closeout

```text
final_decision: accept_bounded_with_remediation_recommendation
remediation_direction: add safe discriminating structural signals before another materialized descriptor scoring attempt
r035_status: active_not_validated
r038_status: active_standing_gate
```
