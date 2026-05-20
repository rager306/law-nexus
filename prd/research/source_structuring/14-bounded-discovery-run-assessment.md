# M032 S07 — bounded discovery run assessment

## Status

- Milestone: `M032-hy6i8r — MiniMax Assisted Source Discovery CLI`
- Slice: `S07 — Bounded Discovery Run Assessment`
- Assessment status: `draft_frame`
- Requirement focus: `R039`
- Requirements not validated by this assessment frame: `R035`, `R038`

## Purpose

This assessment closes M032 by checking whether the source-discovery CLI can run a bounded, reviewable path from mocked MiniMax-assisted discovery through candidate normalization, deterministic verifier decisions, and external review pack generation.

The assessment is intentionally narrow. It evaluates whether the CLI surfaces are analyzable and traceable. It does not claim legal correctness, parser completeness, retrieval quality, production ETL readiness, or independent external review completion.

## Assessment questions

1. Can a temporary-workspace run execute `discover --verify-candidates` and then `external-review-pack <run_id>` without writing generated runtime outputs into tracked source directories?
2. Does the trajectory evidence show enough phase, step, and status detail to reconstruct how the discovery attempt progressed?
3. Do MiniMax attempts remain non-authoritative and represented as proposal context rather than verified truth?
4. Are candidates normalized into graph-context-oriented records with stable candidate refs and ignored model authority claims?
5. Do verifier decisions provide bounded accepted/rejected/needs_review outcomes with traceable refs?
6. Does the external review pack summarize trajectory, MiniMax attempts, candidates, verifier outcomes, rejected branches, review queue state, missing sections, review questions, and non-claims?
7. Does the final evidence support a concrete next milestone without validating R035 or R038?

## Evidence sources

The assessment should draw from:

- `prd/research/source_structuring/08-runtime-workspace-policy.md`
- `prd/research/source_structuring/09-trajectory-log-contract.md`
- `prd/research/source_structuring/10-minimax-discovery-cli-proof.md`
- `prd/research/source_structuring/11-candidate-normalization-proof.md`
- `prd/research/source_structuring/12-candidate-verifier-integration-proof.md`
- `prd/research/source_structuring/13-external-gpt55-review-pack-proof.md`
- temporary workspace smoke outputs from `discover --verify-candidates`
- temporary workspace smoke outputs from `external-review-pack <run_id>`

## Bounded run shape

The final smoke should use a temporary workspace and mocked MiniMax response. The expected path is:

```text
discover --verify-candidates
  -> runtime/trajectory/<run_id>/discovery_steps.jsonl
  -> runtime/minimax-attempts/<run_id>/attempts.jsonl
  -> runtime/discovery/<run_id>/candidate_hypotheses.jsonl
  -> runtime/discovery/<run_id>/graph_context_signals.jsonl
  -> runtime/verifier/<run_id>/verifier_decisions.jsonl

external-review-pack <run_id>
  -> runtime/external-review/<run_id>/review_pack.json
  -> runtime/external-review/<run_id>/review_pack.md
  -> runtime/external-review/<run_id>/external_review_summary.md
```

The run may have missing optional rejected-branch or review-queue sections if the mock produces only accepted candidates. Those omissions must appear as explicit `missing_sections` in the review pack rather than being hidden.

## Observed evidence

T02 bounded smoke used a temporary workspace and mocked MiniMax response. The successful run executed:

```text
discover --verify-candidates
external-review-pack RUN-s07abc123456
```

Observed compact evidence:

- candidate count: `1`
- verifier status counts: `accepted: 1`
- review pack refs:
  - `runtime/external-review/RUN-s07abc123456/review_pack.md`
  - `runtime/external-review/RUN-s07abc123456/review_pack.json`
  - `runtime/external-review/RUN-s07abc123456/external_review_summary.md`
- explicit missing sections:
  - `diagnostics`
  - `review_queue`
  - `rejections`
- GPT-5.5 boundary: review pack states GPT-5.5 is external control over CLI outputs, not an embedded runtime judge.
- path hygiene: smoke assertions verified temporary absolute paths were not copied into durable review artifacts.

A first exploratory two-candidate smoke expected one weak graph-context signal to be rejected. It instead produced `accepted: 2` because the CLI run-level safe source ref gave both candidates enough structural evidence for the deterministic verifier. This is acceptable for S07 because model confidence is non-authoritative, but it is a limitation for future verifier design: weak graph-context signals may need stricter evidence-shape checks if the next milestone needs finer rejection behavior.

## Limitations

The bounded run proves a reviewable CLI path, not source-structuring completeness.

Current limitations:

- MiniMax was mocked; no live provider quality or latency was assessed.
- The accepted candidate demonstrates structural pipeline behavior, not legal correctness.
- Rejection and review-queue sections were represented as explicit missing sections in the successful smoke; they were not populated by that smoke.
- The exploratory two-candidate smoke showed that low-confidence graph-context signals can still be accepted when safe run-level source refs provide enough evidence. Future verifier work should decide whether candidate kind and confidence should influence stricter evidence-shape requirements.
- The runtime workspace policy says persistent generated outputs belong under `law-source/consultant/runtime/`, but actual `.gitignore` or tracking enforcement remains future work.
- No independent GPT-5.5 review was performed; only the review pack was prepared.
- This assessment does not validate R035 and does not validate R038.

## Requirement outcome

S07 supports validating the bounded M032 portion of `R039`: the CLI can run a reviewable MiniMax-assisted discovery path with deterministic candidate verification and an external review pack.

Evidence for R039:

- temporary-workspace `discover --verify-candidates` smoke passed;
- trajectory and MiniMax attempt artifacts were produced;
- candidate hypotheses and graph-context signals were normalized;
- verifier decisions were produced before review packaging;
- `external-review-pack` wrote `review_pack.json`, `review_pack.md`, and `external_review_summary.md`;
- missing optional sections were explicit in `missing_sections`;
- GPT-5.5 was kept external to runtime candidate acceptance.

Non-outcomes:

- S07 does not validate R035.
- S07 does not validate R038.
- S07 does not prove legal answer correctness.
- S07 does not prove parser completeness.
- S07 does not prove production-readiness or graph-vector retrieval quality.

## Recommended next milestone

Recommended next milestone: **Graph Context Formation from Verified Source-Discovery Candidates**.

Suggested scope:

1. Define the graph-context staging schema for accepted structural candidates.
2. Import accepted candidates into a temporary/staging graph context with provenance refs, not legal truth claims.
3. Add stricter verifier evidence-shape checks for weak graph-context signals, especially when model confidence is low or source refs are inherited from run-level context.
4. Add populated rejection/review-queue smoke cases so rejected and needs_review branches are exercised, not only represented as missing optional sections.
5. Decide and implement runtime tracking policy for `law-source/consultant/runtime/` outputs before any persistent corpus-scale discovery run.
6. Optionally run an actual external GPT-5.5 review over the S06 pack and record it separately; only that later evidence could advance R038.

The next milestone should preserve the M032 boundary: MiniMax and GPT-5.5 may suggest or review structures, but deterministic code remains the acceptance gate for graph-context staging.

## Non-claims

This bounded discovery run assessment does not claim:

- legal correctness;
- parser completeness;
- retrieval quality;
- ontology/product readiness;
- production ETL readiness;
- graph-vector behavior;
- live MiniMax quality;
- independent GPT-5.5 review completion;
- R035 validation;
- R038 validation.
