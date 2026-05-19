---
milestone: M022-5t4bzn
slice: S02
status: proof
requirement_scope:
  - R035
non_authoritative: true
created_at: 2026-05-18
---

# Representative EvidenceSpan Corpus Proof

S02 produced a representative EvidenceSpan retrieval corpus fixture that expands beyond M021's six-case golden set while preserving citation-safe, local/open-weight, non-authoritative boundaries.

## Artifacts

Fixture:

```text
prd/research/ontology_architecture_requirements/fixtures/representative_evidence_span_retrieval_corpus.json
```

Verifier:

```text
scripts/verify-representative-evidence-span-retrieval-corpus.py
```

Tests:

```text
tests/test_representative_evidence_span_retrieval_corpus.py
```

## Fixture summary

Schema:

```text
representative-evidence-span-retrieval-corpus/v1
```

Case count:

```text
10
```

Candidate count:

```text
10
```

Required case classes present:

- `positive_evidence_span`
- `positive_source_block_marker`
- `positive_with_distractor`
- `stale_temporal_negative`
- `ambiguous_candidate_set`
- `unsupported_scope`
- `scoped_no_answer`
- `citation_preservation_boundary`
- `edition_mismatch_negative`
- `unsafe_payload_boundary`

## Source-anchor policy

The fixture follows the M022 stable source-anchor policy:

- stable source artifacts are preferred;
- mutable runtime proof-report hashes are avoided;
- `.gsd/exec` paths are forbidden as durable fixture anchors.

## Safety boundary

The fixture excludes:

- raw legal text;
- raw query text;
- source excerpts;
- raw vectors or embedding arrays;
- provider payloads;
- generated answer prose;
- generated query/Cypher text;
- secrets;
- absolute paths;
- temporary paths;
- `.gsd/exec` paths;
- raw FalkorDB rows.

## Verification

Final S02 verification evidence:

```text
gsd_exec[7533fd77-e308-4c9f-8097-3dec7ad5c30a]
```

Command chain:

```bash
uv run python scripts/verify-representative-evidence-span-retrieval-corpus.py
uv run pytest tests/test_representative_evidence_span_retrieval_corpus.py -q
uv run ruff check scripts/verify-representative-evidence-span-retrieval-corpus.py tests/test_representative_evidence_span_retrieval_corpus.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```

Results:

```text
verifier: status=ok, case_count=10, candidate_count=10
tests: 8 passed
ruff: All checks passed
architecture verifier: status=ok
GSD sync drift: status=OK
```

## Requirement boundary

S02 advances R035 by creating a broader representative corpus fixture for later metrics. It does not validate R035 and does not prove retrieval quality because metrics are S03-owned and product/parser/production/legal-answer gaps remain open.

## Non-claims

S02 does not claim:

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
