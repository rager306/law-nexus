# M033 S06 — bounded staging assessment

## Status

- Milestone: `M033-1vpo4b — Graph Context Formation from Verified Candidates`
- Slice: `S06 — Bounded Staging Assessment`
- Assessment status: `finalized`
- Requirement focus: follow-on bounded `R039`
- Requirements not validated: `R035`, `R037`, `R038`

## Purpose

This bounded staging assessment closes M033 by checking whether verified source-discovery candidates can be converted into deterministic graph-context staging records with visible accepted, rejected, and needs_review branches, while generated runtime outputs remain ignored by git.

The assessment is intentionally bounded. It evaluates graph-context staging readiness only. It does not claim legal correctness, parser completeness, product retrieval quality, FalkorDB graph ingestion, independent external review completion, or production readiness.

## Assessment questions

1. Does the graph-context staging schema require candidate, verifier, trajectory, and source provenance refs?
2. Can accepted verifier decisions export to graph-context staging records in a temporary workspace?
3. Are weak graph-context signals prevented from silently staging when evidence-shape is weak?
4. Are rejected and needs_review branches populated in verifier artifacts, external review pack summaries, and staging diagnostics?
5. Does runtime ignore policy prevent generated outputs under `law-source/consultant/runtime/` from appearing in `git status`?
6. Does the milestone evidence support a next milestone, and what proof gate should it require?
7. Are R035, R037, and R038 kept non-validated?

## Evidence sources

- `prd/research/source_structuring/15-graph-context-staging-contract.md`
- `prd/research/source_structuring/16-graph-context-staging-export-proof.md`
- `prd/research/source_structuring/17-verifier-evidence-shape-hardening-proof.md`
- `prd/research/source_structuring/18-rejected-review-queue-coverage-proof.md`
- `prd/research/source_structuring/19-runtime-tracking-policy-proof.md`
- `tests/test_source_graph_context_staging.py`
- `tests/test_source_runtime_tracking_policy.py`
- temporary workspace smoke outputs from `discover --verify-candidates`, `external-review-pack`, and `graph-context-stage`

## Expected final smoke shape

The final smoke should use a temporary workspace and mocked MiniMax response with three candidates:

- supported `relationship_candidate` expected `accepted` and staged;
- weak `graph_context_signal` expected `rejected` and skipped;
- ambiguous `graph_context_signal` expected `needs_review` and skipped.

Expected final counts:

```json
{
  "verifier_status_counts": {"accepted": 1, "needs_review": 1, "rejected": 1},
  "staged": 1,
  "skipped": 2,
  "rejected_branch_summary.rejected_count": 1,
  "review_queue_summary.needs_review_count": 1
}
```

## Observed evidence

T02 final temporary-workspace smoke ran:

```text
discover --verify-candidates
external-review-pack RUN-finalstage1
graph-context-stage RUN-finalstage1
```

Observed compact evidence:

```json
{
  "verifier_status_counts": {"accepted": 1, "needs_review": 1, "rejected": 1},
  "rejected_count": 1,
  "needs_review_count": 1,
  "staged": 1,
  "skipped": 2,
  "diagnostics": 2,
  "refs": {
    "review_pack_json_ref": "runtime/external-review/RUN-finalstage1/review_pack.json",
    "staging_ref": "runtime/graph-context/RUN-finalstage1/graph_context_staging.jsonl",
    "diagnostics_ref": "runtime/graph-context/RUN-finalstage1/graph_context_diagnostics.jsonl",
    "summary_ref": "runtime/graph-context/RUN-finalstage1/graph_context_summary.json"
  }
}
```

The smoke verified that temporary absolute paths were not copied into durable review or staging artifacts.

## Limitations

M033 proves bounded graph-context staging readiness, not runtime graph capability.

Known limitations:

- The final smoke used a mocked provider response; it verifies deterministic CLI behavior and artifact shape, not live provider recall quality.
- Staging records are structural proposals. They are not legal answers, legal interpretations, production ontology facts, or accepted FalkorDB graph records.
- The deterministic verifier accepts only evidence-shaped candidates. It does not prove parser completeness or source-corpus completeness.
- `external-review-pack` remains an observability surface for later GPT-5.5 control; no independent external GPT-5.5 review was performed in M033.
- `graph-context-stage` writes JSONL staging and diagnostics only; it does not create labels, relationships, indexes, vectors, or FalkorDB data.
- Runtime ignore policy prevents accidental git tracking of generated outputs, but it does not implement retention, cleanup, storage quotas, or production artifact governance.

## Requirement outcome

M033 extends the already validated bounded source-discovery capability (`R039`) with graph-context staging evidence:

- staging schema exists with provenance refs and non-claims;
- accepted verified candidates export to deterministic staging rows;
- rejected and needs_review candidates remain visible in verifier/review/staging diagnostics;
- weak graph-context signals no longer silently stage through inherited run-level refs;
- generated runtime outputs under `law-source/consultant/runtime/` are ignored by git while source/proof/script/test paths remain trackable.

Boundary outcomes:

- M033 does not validate R035. No ontology/product architecture proof, production retrieval UX, or accepted architecture registry integration was completed here.
- M033 does not validate R037. No FalkorDB ingestion, graph loading, graph query, index creation, vector behavior, or runtime graph API proof was performed.
- M033 does not validate R038. Review packs were generated, but no independent external GPT-5.5 review result was obtained and applied.

## Recommended next milestone

Proceed to a proof-gated FalkorDB graph runtime ingestion milestone from staged graph-context records.

Recommended scope:

1. Load a small accepted `graph_context_staging.jsonl` fixture into FalkorDB in an isolated test graph.
2. Preserve candidate, verifier, source, and trajectory provenance on graph nodes/edges.
3. Query the loaded fixture deterministically and compare returned structure against the staging rows.
4. Keep LLMs non-authoritative: MiniMax and GPT-5.5 may propose or externally review, but runtime acceptance remains deterministic.
5. Gate any R037 movement on actual graph load/query evidence, not this M033 staging assessment.

Recommended proof gate for the next milestone:

```text
Given one accepted staging row, graph runtime ingestion creates only provenance-backed graph records, deterministic queries recover the staged structure, rejected/needs_review rows are not ingested as accepted facts, and all outputs preserve non-claims.
```

If FalkorDB runtime setup or schema mapping is not ready, the fallback next milestone should be verifier/schema hardening for staging-row cardinality, relation direction, and source-span support before ingestion.

## Non-claims

This bounded staging assessment does not validate R035, does not validate R037, and does not validate R038.

It does not claim:

- legal correctness;
- parser completeness;
- product retrieval quality;
- FalkorDB graph ingestion;
- production ETL readiness;
- graph-vector behavior;
- independent GPT-5.5 review completion;
- pilot readiness.
