# M033 S04 — Rejected and Review Queue Coverage Proof

## Status

- Milestone: `M033-1vpo4b — Graph Context Formation from Verified Candidates`
- Slice: `S04 — Rejected and Review Queue Coverage`
- Proof status: `draft_t01_branch_coverage_contract`
- Requirement advanced: follow-on bounded `R039`
- Requirements not validated: `R035`, `R037`, `R038`

## Purpose

S04 proves that rejected and `needs_review` branches are populated and visible in verifier, external review pack, and graph-context staging evidence. M032/S06 could represent missing review queue or rejection sections. M033/S04 must prove those sections are populated when candidate outcomes require them.

This is structural branch coverage only. It does not claim legal correctness, parser completeness, FalkorDB ingestion, independent review completion, or production graph readiness.

## Fixture outcomes

The branch coverage smoke should include at least three candidate classes:

1. `relationship_candidate` with adequate structural support — expected `accepted` and staged.
2. weak `graph_context_signal` with inadequate evidence shape — expected `rejected`, with `rejection_reasons.jsonl` populated.
3. bounded ambiguous structural candidate — expected `needs_review`, with `review_queue_items.jsonl` populated.

The exact needs_review fixture can be implemented through deterministic evidence-shape rules, not LLM authority.

## Expected verifier artifacts

For the run, the verifier directory should include:

```text
runtime/verifier/<run_id>/verifier_decisions.jsonl
runtime/verifier/<run_id>/rejection_reasons.jsonl
runtime/verifier/<run_id>/review_queue_items.jsonl
```

Expected status counts:

```json
{"accepted": 1, "rejected": 1, "needs_review": 1}
```

`rejection_reasons.jsonl` should include safe reason codes for rejected candidates.

`review_queue_items.jsonl` should include safe queue item IDs, proposal refs, review reasons, evidence refs, and non-authoritative markers.

## Expected external review pack evidence

`external-review-pack <run_id>` should produce `review_pack.json` where:

- `rejected_branch_summary.rejected_count` is greater than zero;
- `review_queue_summary.needs_review_count` is greater than zero;
- `missing_sections` does not include `rejections` when `rejection_reasons.jsonl` exists;
- `missing_sections` does not include `review_queue` when `review_queue_items.jsonl` exists;
- `rejected_branch_summary` and `review_queue_summary` contain safe refs/reasons only.

## Expected graph-context staging evidence

`graph-context-stage <run_id>` should produce:

```text
runtime/graph-context/<run_id>/graph_context_staging.jsonl
runtime/graph-context/<run_id>/graph_context_diagnostics.jsonl
runtime/graph-context/<run_id>/graph_context_summary.json
```

Expected staging behavior:

- accepted candidate becomes a staging row;
- rejected candidate becomes a diagnostic row;
- needs_review candidate becomes a diagnostic row;
- `graph_context_diagnostics.jsonl` includes `verifier-status-not-accepted` for non-accepted candidates;
- summary shows `staged: 1`, `skipped: 2`, `diagnostics: 2`.

## Observed branch coverage evidence

T04 temporary-workspace smoke used three mocked candidates:

- supported `relationship_candidate`;
- weak `graph_context_signal`;
- ambiguous `graph_context_signal` requiring deterministic review.

Observed result:

```json
{
  "status_counts": {"accepted": 1, "needs_review": 1, "rejected": 1},
  "rejected_count": 1,
  "needs_review_count": 1,
  "staged": 1,
  "skipped": 2
}
```

The external review pack had populated `rejected_branch_summary` and `review_queue_summary`. `missing_sections` did not include `rejections` or `review_queue` because `rejection_reasons.jsonl` and `review_queue_items.jsonl` existed.

Graph-context staging wrote one staged record and two diagnostics. Both diagnostics included `verifier-status-not-accepted`, preserving rejected and needs_review visibility without treating either branch as graph truth.

## Non-claims

S04 does not validate R035, does not validate R037, and does not validate R038.

S04 does not claim:

- legal correctness;
- parser completeness;
- product retrieval quality;
- production ETL readiness;
- FalkorDB graph ingestion;
- independent GPT-5.5 review completion.

## T01 verification markers

This proof intentionally includes `rejected_branch_summary`, `review_queue_summary`, `review_queue_items.jsonl`, `rejection_reasons.jsonl`, `graph_context_diagnostics.jsonl`, `R035`, `R037`, and `R038`.
