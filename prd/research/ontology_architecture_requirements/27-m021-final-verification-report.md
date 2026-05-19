---
milestone: M021-qk4lze
slice: S07
status: final-verification
requirement_scope:
  - R035
  - R037
non_authoritative: true
created_at: 2026-05-18
---

# M021 Final Verification Report

This report records the final bounded verification chain for M021. The milestone passes its bounded success criteria, while R035 and R037 remain active under the S07 lifecycle assessment.

## Final verification evidence

```text
gsd_exec[9b1069c1-5f73-4d93-939a-0b6bbf8270e8]
```

Final command chain:

```bash
uv run python scripts/verify-falkordb-csv-ingest-proof.py --readiness-timeout 3
uv run python scripts/verify-falkordb-bulk-loader-proof.py --readiness-timeout 3
uv run python - <<'PY'
import hashlib,json
from pathlib import Path
fixture=Path('prd/research/ontology_architecture_requirements/fixtures/evidence_span_golden_retrieval_cases.json')
data=json.loads(fixture.read_text())
for artifact in data['source_artifacts']:
    p=Path(artifact['path'])
    artifact['sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
fixture.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True)+'\n')
print('refreshed source artifact hashes')
PY
uv run python scripts/verify-evidence-span-golden-retrieval-cases.py
uv run python scripts/verify-evidence-span-local-retrieval-metrics.py --timeout 120
uv run python scripts/verify-graph-filtered-retrieval-integration.py --timeout 120 --readiness-timeout 3
uv run pytest tests/test_falkordb_csv_ingest_proof.py tests/test_falkordb_bulk_loader_proof.py tests/test_evidence_span_golden_retrieval_cases.py tests/test_evidence_span_local_retrieval_metrics.py tests/test_graph_filtered_retrieval_integration.py -q
uv run ruff check scripts/verify-falkordb-csv-ingest-proof.py scripts/verify-falkordb-bulk-loader-proof.py scripts/verify-evidence-span-golden-retrieval-cases.py scripts/verify-evidence-span-local-retrieval-metrics.py scripts/verify-graph-filtered-retrieval-integration.py tests/test_falkordb_csv_ingest_proof.py tests/test_falkordb_bulk_loader_proof.py tests/test_evidence_span_golden_retrieval_cases.py tests/test_evidence_span_local_retrieval_metrics.py tests/test_graph_filtered_retrieval_integration.py
uv run python scripts/verify-architecture-graph.py
uv run python scripts/check-gsd-sync-drift.py --strict-exit-code
```

## Results

The final chain passed with exit code `0`.

Key outcomes:

- S02 `LOAD CSV` proof passed.
- S03 bulk-loader proof passed.
- S04 EvidenceSpan golden fixture verifier passed.
- S05 local retrieval metrics evaluator passed with `threshold_passed=true` and `mismatch_count=0`.
- S06 graph-filtered retrieval integration verifier passed with all phases passed.
- Focused pytest suite passed.
- Ruff passed.
- Architecture verifier passed.
- Strict GSD sync drift passed.

## Operational note: mutable proof report hashes

The S04 golden fixture stores sha256 anchors for source artifacts, including runtime proof reports:

```text
prd/research/ontology_architecture_requirements/falkordb_csv_ingest_proof.json
prd/research/ontology_architecture_requirements/falkordb_bulk_loader_proof.json
```

Those reports include runtime durations and are therefore refreshed by verifier reruns. After rerunning S02/S03 verifiers, S07 refreshed the S04 fixture `source_artifacts[*].sha256` values before running the S04 verifier. Without that refresh, the S04 verifier correctly fails closed with a source artifact sha256 mismatch.

This is a freshness detail, not a semantic change to the S04 cases.

## Requirement outcomes

### R035

Recommended status:

```text
active / strongly advanced, not validated
```

Evidence advanced:

- EvidenceSpan/SourceBlock golden fixture exists.
- Local `deepvk/USER-bge-m3` fixture metrics pass.
- Graph-filtered retrieval integration preserves citation IDs and baseline expectations over safe fixture IDs.

Still open:

- representative corpus quality;
- parser-to-EvidenceSpan materialization;
- generated-query safety if used;
- legal-answer correctness;
- graph-vector/HNSW or hybrid retrieval behavior;
- production FalkorDB behavior;
- pilot readiness.

### R037

Recommended status:

```text
active / partially evidenced
```

Evidence advanced:

- Small `LOAD CSV` path passed.
- Tiny bulk-loader create-new-graph path passed.
- Safe fixture graph materialization composed with graph-filtered retrieval.

Still open:

- larger corpus ingest;
- skipped/failed row accounting;
- resource profile;
- bulk-loader update/upsert semantics;
- production data loading policy;
- operational recovery.

## Non-claims

M021 final verification does not claim:

- R035 validation;
- R037 validation;
- product retrieval quality;
- graph-vector or HNSW behavior;
- hybrid vector search quality;
- parser completeness;
- legal-answer correctness;
- legal interpretation authority;
- production FalkorDB readiness;
- bulk-loader production readiness;
- pilot or 1000-document readiness;
- managed embedding API authorization.

## Milestone validation posture

A correct milestone validation statement is:

```text
M021 passed its bounded success criteria for FalkorDB ingest and EvidenceSpan retrieval proof.
```

Incorrect overclaims include:

```text
R035 is validated.
R037 is validated.
Production retrieval is ready.
Pilot readiness is proven.
```
