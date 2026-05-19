---
milestone: M026-1uqmzc
slice: S02
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-19
---

# Held-out Semantic Descriptor Inputs Proof

S02 creates the held-out safe descriptor fixture for M026 and verifies that it satisfies the S01 contract before any local semantic scoring runs.

## Contract source

```text
prd/research/ontology_architecture_requirements/52-held-out-semantic-descriptor-evaluation-contract.md
```

## Artifacts

Held-out descriptor fixture:

```text
prd/research/ontology_architecture_requirements/fixtures/held_out_semantic_descriptor_inputs.json
```

Verifier:

```text
scripts/verify-held-out-semantic-descriptor-inputs.py
```

Regression tests:

```text
tests/test_held_out_semantic_descriptor_inputs.py
```

## Fixture summary

```text
schema_version: held-out-semantic-descriptor-inputs/v1
representation_kind: safe_semantic_descriptor_v1
query_descriptor_count: 5
candidate_descriptor_count: 10
held_out_case_independence_required: true
m025_design_case_reuse_forbidden: true
m022_acceptance_case_reuse_forbidden: true
```

The fixture uses M026-only identifiers:

```text
CASE-M026-...
QUERY-M026-...
CAND-M026-...
HO-DESCQ-M026-...
HO-DESCC-M026-...
```

The verifier rejects reuse of M022/M025 acceptance identifiers:

```text
CASE-M022-
QUERY-M022-
CAND-M022-
DESCQ-M025-
DESCC-M025-
```

## Safety and leakage controls

The verifier rejects unsafe fields and fragments including raw text, raw vectors, expected-answer fields, selection reasons, absolute paths, `.gsd/exec` anchors, and unsafe durable payload vocabulary.

Regression tests cover:

- valid fixture passes;
- CLI emits compact OK JSON;
- M022 case ID reuse fails;
- M025 descriptor ID reuse fails;
- `expected_label` fails;
- `selection_reason` fails;
- `rank` fails;
- raw text fragment fails;
- free-text descriptor value fails;
- vector field fails;
- absolute path fails;
- unsafe durable payload vocabulary fails;
- false redaction flag fails;
- bad contract hash fails.

## Verification

Final S02 verification evidence:

```text
gsd_exec[0df7760f-f455-45dd-9f3a-306e3e9d2df1]
```

Verification chain:

```text
uv run python scripts/verify-held-out-semantic-descriptor-inputs.py
uv run pytest tests/test_held_out_semantic_descriptor_inputs.py -q
uv run ruff check scripts/verify-held-out-semantic-descriptor-inputs.py tests/test_held_out_semantic_descriptor_inputs.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
uv run python held-out fixture marker verification
```

Observed result:

```text
held-out verifier: status ok
regression tests: 15 passed
ruff: passed
architecture verifier: status ok
GSD sync drift: status OK
fixture markers: verified
```

LSP diagnostics for the verifier reported no diagnostics.

## Handoff to S03

S03 may consume the fixture only as safe descriptor inputs. Expected labels, expected candidate IDs, ranks, diagnostic expectations, or selection reasons are not present in the descriptor fixture and must not be used as scoring inputs.

If S03 needs evaluation labels after scoring, they must be introduced as a separate post-scoring evaluation artifact and kept out of descriptor/scoring inputs.

## Non-claims

This proof does not validate R035 and does not prove held-out semantic retrieval quality, product retrieval quality, legal-answer correctness, parser completeness, parser-to-EvidenceSpan materialization, graph-vector/HNSW behavior, hybrid retrieval quality, production readiness, pilot readiness, or managed embedding API authorization.

R035 remains active and not validated. R038 remains active as a standing independent proof-review gate.
