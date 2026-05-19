---
milestone: M027-vxdy7c
slice: S05
status: final-closeout
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# M027 Final Closeout

## Final decision

```text
accept_bounded_with_remediation_recommendation
```

M027 closes as bounded parser-to-safe-candidate materialization evidence plus bounded local scoring evidence. It does not validate R035.

## What M027 added

M027 advanced the proof chain from controlled descriptor fixtures toward real source-derived structure:

```text
controlled ODT source structure
-> safe materialized candidate records
-> safe materialized-derived descriptors
-> local semantic scoring over descriptor tokens
-> independent bounded review
```

## Accepted evidence

### S01 — Contract

M027 defined the safe materialization contract:

```text
schema_version: parser-evidence-span-materialization/v1
representation_kind: safe_materialized_evidence_candidates_v1
controlled source: law-source/garant/44-fz.odt
```

### S02 — Tiny materialization smoke

Observed result:

```text
status: ok
materialized_candidate_count: 6
safe_source_anchors_verified: true
source_text_excluded: true
```

Accepted boundary:

```text
one controlled structural smoke from ODT content ordering to safe candidate records
```

### S03 — Descriptor bridge

Observed result:

```text
schema_version: materialized-descriptor-inputs/v1
representation_kind: safe_materialized_descriptor_v1
query_descriptor_count: 6
candidate_descriptor_count: 6
source_materialization_verified: true
```

Accepted boundary:

```text
safe structural descriptor derivation from materialized records only
```

### S04 — Local scoring

Observed result:

```text
score_count: 36
model_id: deepvk/USER-bge-m3
observed_vector_dimension: 1024
managed_api_used: false
network_used: false
raw_vectors_persisted: false
```

Metrics:

```text
mrr: 0.680555
recall_at_1: 0.5
recall_at_3: 0.833333
runtime_boundary_confirmed: 1.0
```

Accepted boundary:

```text
local scoring ran correctly and produced bounded negative evidence
```

Rejected boundary:

```text
materialized-derived structural descriptors are not accepted as retrieval-quality evidence
```

### S05 — Independent review

Review verdict:

```text
PASS_BOUNDED
```

Final review conclusion:

```text
artifact controls passed
runtime boundary passed
label separation passed
retrieval-quality claim rejected
R035 validation rejected
```

## Key lesson

The current materialized-derived structural descriptors are too coarse for retrieval-quality acceptance. Same-kind paragraph candidates share many structural descriptor tokens, so local semantic scoring cannot reliably discriminate them.

This is useful evidence: the next iteration should add safe discriminating structure before another materialized descriptor scoring attempt.

## Recommended remediation direction

Future work should test one representation change at a time, such as:

```text
safe local structural context window IDs
safe normalized citation-boundary class
safe intra-document neighborhood buckets
safe parser-style class markers
safe source-block adjacency markers
```

The remediation must preserve these constraints:

```text
no raw source text in durable artifacts
no label-derived descriptor fields
labels remain post-scoring-only
local/open-weight runtime only
no raw vector persistence
one representation change per cycle
independent review before acceptance
```

## Requirement outcomes

### R035

```text
status: active
validation: not validated by M027
```

M027 advances R035 with bounded materialization and scoring evidence, but the negative S04 metrics and limited parser smoke scope block validation.

### R038

```text
status: active
validation: standing independent proof-review gate remains required
```

M027 confirms R038 value: the independent review separates artifact-control success from retrieval-quality acceptance.

## Final non-claims

M027 does not prove:

```text
R035 validation
parser completeness
product retrieval quality
legal-answer correctness
legal interpretation authority
production ETL readiness
graph-vector or HNSW behavior
hybrid retrieval quality
pilot readiness
managed embedding API authorization
```

## Final verification status

```text
all S01-S04 proof artifacts present
S02 materialization verifier passed
S03 descriptor bridge verifier passed
S04 scoring verifier passed
S04 tests passed
architecture verifier passed
GSD sync drift passed
S05 review markers passed
S05 closeout markers passed
```

## Final disposition

```text
M027 may close as bounded evidence.
R035 remains active and not validated.
R038 remains active as standing review gate.
Next work should be a remediation/representation iteration, not a production-readiness claim.
```
