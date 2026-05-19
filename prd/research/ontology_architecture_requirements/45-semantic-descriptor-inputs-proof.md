---
milestone: M025-50be7n
slice: S02
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Semantic Descriptor Inputs Proof

S02 created and verified the `safe_semantic_descriptor_v1` inputs for the first M025 local semantic scoring iteration. These descriptors are scoring inputs only. S02 does not run scoring, does not compare retrieval metrics, and does not validate R035.

## Artifacts

Descriptor manifest:

```text
prd/research/ontology_architecture_requirements/fixtures/semantic_descriptor_inputs.json
```

Verifier:

```text
scripts/verify-semantic-descriptor-inputs.py
```

Tests:

```text
tests/test_semantic_descriptor_inputs.py
```

## Coverage

```text
representation_kind: safe_semantic_descriptor_v1
query_descriptor_count: 10
candidate_descriptor_count: 10
```

The descriptor manifest covers the representative M022 cases and the candidate set needed by S03 scoring.

## Descriptor schema boundary

Descriptors use bounded enum fields only:

```text
topic_class
obligation_type
actor_role
document_scope
temporal_status
citation_granularity
procurement_phase
query_intent
candidate_role
ambiguity_handling
safety_boundary
citation_binding_status
```

Descriptor tokens are derived from these enum fields and must match the verifier's safe token grammar.

## Safety boundary

The manifest excludes:

- raw legal text;
- raw query text;
- source excerpts;
- raw vectors;
- provider or external payloads;
- generated legal-answer prose;
- generated query or Cypher text;
- secrets;
- absolute paths;
- `.gsd/exec` durable anchors;
- expected labels;
- expected ranks;
- expected candidate lists;
- expected rejected-candidate lists;
- expected diagnostic lists.

## Verification

Final S02 verification evidence:

```text
gsd_exec[31359915-535b-4418-8f11-c697877838f6]
```

Command chain:

```bash
uv run python scripts/verify-semantic-descriptor-inputs.py
uv run pytest tests/test_semantic_descriptor_inputs.py -q
uv run ruff check scripts/verify-semantic-descriptor-inputs.py tests/test_semantic_descriptor_inputs.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```

Results:

```text
descriptor verifier: status=ok, query_descriptor_count=10, candidate_descriptor_count=10
tests: 19 passed
ruff: All checks passed
architecture verifier: status=ok
GSD sync drift: status=OK
```

## Negative coverage

Focused tests prove fail-closed behavior for:

- unknown descriptor fields;
- free-text descriptor values;
- raw text fields;
- raw vector fields;
- provider payload fields;
- expected answer leakage;
- rank leakage;
- generated answer prose fields;
- generated query/Cypher fields;
- absolute paths;
- `.gsd/exec` anchors;
- bad enum values;
- descriptor token mismatch;
- missing candidate coverage;
- source hash mismatch;
- false redaction flags.

## S03 handoff

S03 must consume `semantic_descriptor_inputs.json` as the only descriptor input source and compare descriptor scoring metrics against the M024 baseline from `44-local-semantic-scoring-iteration-contract.md`. Expected fixture answers may be used only after scoring for metric comparison.

## Non-claims

S02 does not claim:

- semantic scoring result;
- metric improvement over M024;
- representative retrieval-quality validation;
- product retrieval quality;
- legal-answer correctness;
- parser completeness;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- R035 validation.
