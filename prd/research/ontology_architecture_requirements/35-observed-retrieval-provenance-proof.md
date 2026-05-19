---
milestone: M023-9rfkrs
slice: S02
status: proof
requirement_scope:
  - R035
  - R038
non_authoritative: true
created_at: 2026-05-18
---

# Observed Retrieval Provenance Proof

S02 created and verified safe query and source provenance artifacts for the observed retrieval remediation horizon. This addresses two M022 independent-review gaps: query hashes were not independently auditable, and source anchors proved file existence/hash but not candidate provenance.

## Artifacts

Query provenance registry:

```text
prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_query_provenance_registry.json
```

Source provenance manifest:

```text
prd/research/ontology_architecture_requirements/fixtures/observed_retrieval_source_provenance_manifest.json
```

Verifier:

```text
scripts/verify-observed-retrieval-provenance.py
```

Tests:

```text
tests/test_observed_retrieval_provenance.py
```

## Query provenance coverage

The query registry records 10 entries, one per representative EvidenceSpan retrieval case. Each entry includes safe fields only:

- `query_id`;
- `query_hash` derived from the fixture `query_text_sha256`;
- `query_hash_field`;
- `query_kind`;
- `scope_id`;
- `as_of_date`;
- source artifact refs;
- redacted template ID;
- controlled terms.

The registry does not store raw query text and does not duplicate expected answer lists such as expected candidate IDs, rejected IDs, or diagnostic codes.

## Source provenance coverage

The source manifest records 10 candidate entries. For every candidate, the verifier checks:

- candidate entry exists in the representative fixture;
- source artifact path is repo-relative and hash matches;
- candidate provenance fields match the fixture;
- `source_case_id` exists in the declared source artifact;
- `source_record_ids` exist in the declared source artifact;
- citation path IDs exist where required for relevant, distractor, or unsafe candidates.

Some stale or ambiguous candidates intentionally have citation-path IDs that are not required to resolve as valid graph bindings; those remain negative/boundary cases, not provenance pass claims.

## Verification

Final S02 verification evidence:

```text
gsd_exec[ecee8dcc-b305-4e95-9c5b-ae2d698a8fb2]
```

Command chain:

```bash
uv run python scripts/verify-observed-retrieval-provenance.py
uv run pytest tests/test_observed_retrieval_provenance.py -q
uv run ruff check scripts/verify-observed-retrieval-provenance.py tests/test_observed_retrieval_provenance.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```

Results:

```text
provenance verifier: status=ok, query_count=10, candidate_count=10
tests: 8 passed
ruff: All checks passed
architecture verifier: status=ok
GSD sync drift: status=OK
```

## Negative coverage

Focused tests prove fail-closed behavior for:

- unregistered query hash;
- bogus source case ID / manifest drift;
- bogus source record ID;
- source artifact hash mismatch;
- unsafe payload field;
- redaction boundary checks.

## Remaining boundary

S02 proves query/source provenance, not observed retrieval ranking. S03 must still produce or consume an observed-output artifact and compute metrics by comparing observed ranked candidate IDs/diagnostics to expected fixture fields.

## Non-claims

S02 does not claim:

- R035 validation;
- R037 validation;
- observed retrieval quality;
- product retrieval quality;
- parser completeness;
- legal-answer correctness;
- graph-vector or HNSW behavior;
- hybrid retrieval quality;
- production FalkorDB readiness;
- pilot readiness;
- managed embedding API authorization.
