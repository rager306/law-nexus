---
milestone: M025-50be7n
slice: S06
task: T01
status: pass
review_type: independent-remediation-review
non_authoritative: true
created_at: 2026-05-19
---

# M025 Remediation Independent Review

## Verdict

```text
PASS
```

The independent review initially returned `REQUEST_CHANGES`; both findings were remediated and rechecked. The final recheck verdict is `PASS`.

## Reviewed scope

Primary S05 remediation package:

```text
scripts/build-semantic-descriptor-inputs.py
tests/test_semantic_descriptor_derivation.py
prd/research/ontology_architecture_requirements/fixtures/semantic_descriptor_inputs.json
prd/research/ontology_architecture_requirements/semantic_descriptor_derivation_remediation_proof.json
prd/research/ontology_architecture_requirements/semantic_descriptor_distractor_ablation_proof.json
prd/research/ontology_architecture_requirements/semantic_descriptor_scoring_proof.json
prd/research/ontology_architecture_requirements/49-semantic-descriptor-derivation-remediation-proof.md
```

Prior decision/review context:

```text
prd/research/ontology_architecture_requirements/47-m025-self-confirming-risk-review.md
prd/research/ontology_architecture_requirements/48-m025-iteration-decision-record.md
```

## Initial review findings

### Finding 1 — Stale scoring proof slice marker

Severity: medium

The scoring proof was refreshed during S05 but still carried:

```text
slice_id: S03
```

This made the proof provenance stale even though the score values reflected the remediated descriptor manifest.

Remediation:

- updated `scripts/verify-semantic-descriptor-scoring.py` to emit `slice_id: S05`;
- regenerated `prd/research/ontology_architecture_requirements/semantic_descriptor_scoring_proof.json`.

Verification:

```text
gsd_exec[be310aad-b483-4b4a-9cc0-a4e8a93b58c2]
gsd_exec[bebb5859-b92f-486b-a6c0-ea372160d990]
```

Current marker:

```text
semantic_descriptor_scoring_proof.json slice_id: S05
```

### Finding 2 — Ablation proof needed fuller provenance

Severity: medium

The ablation proof showed the result but did not fully record what changed and what stayed fixed.

Remediation:

`prd/research/ontology_architecture_requirements/semantic_descriptor_distractor_ablation_proof.json` now records:

```text
source_descriptor_manifest
source_descriptor_manifest_sha256
current_scoring_proof
current_scoring_proof_sha256
ablation_provenance.changed_fields
ablation_provenance.temporary_manifest_persisted: false
ablation_provenance.only_query_descriptor_changed: true
ablation_provenance.candidate_descriptors_changed: false
ablation_provenance.fixture_changed: false
ablation_provenance.metrics_policy_changed: false
ablation_provenance.unchanged_runtime_model: deepvk/USER-bge-m3
ablation_provenance.unchanged_expected_vector_dimension: 1024
ablation_provenance.unchanged_scoring_mode: local_user_bge_m3_safe_descriptor_similarity_v1
```

Verification:

```text
gsd_exec[be310aad-b483-4b4a-9cc0-a4e8a93b58c2]
gsd_exec[bebb5859-b92f-486b-a6c0-ea372160d990]
```

## Recheck result

The reviewer recheck focused on the two remediated findings and returned:

```text
PASS
```

Additional focused verification:

```text
15 passed
All checks passed
M025 S06 review remediation markers verified
```

## Boundary review

The remediated S05 package preserves the required boundaries:

- no raw legal text in durable proof artifacts;
- no raw query text in durable proof artifacts;
- no raw vectors persisted;
- no managed embedding API authorization or network scoring;
- local runtime remains `deepvk/USER-bge-m3`;
- observed vector dimension remains `1024`;
- descriptor derivation excludes expected-answer fields and `selection_reason`;
- ablation changes only the suspicious positive-with-distractor query descriptor;
- final proof note preserves non-claim boundaries.

## Non-claims

This review does not validate R035 and does not establish product retrieval quality, legal-answer correctness, parser completeness, graph-vector/HNSW behavior, hybrid retrieval quality, production readiness, pilot readiness, or managed embedding API authorization.

R035 remains active and not validated. R038 remains active as a standing independent proof-review gate.
