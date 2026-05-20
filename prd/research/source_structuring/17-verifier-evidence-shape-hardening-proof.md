# M033 S03 — Verifier Evidence Shape Hardening Proof

## Status

- Milestone: `M033-1vpo4b — Graph Context Formation from Verified Candidates`
- Slice: `S03 — Verifier Evidence Shape Hardening`
- Proof status: `draft_t01_hardening_contract`
- Requirement advanced: follow-on bounded `R039`
- Requirements not validated: `R035`, `R037`, `R038`

## Purpose

S03 hardens deterministic verifier behavior for weak `graph_context_signal` candidates. M032/S07 observed that a weak graph-context signal could be accepted when it inherited run-level safe source refs. That behavior is too permissive for graph-context staging because it can make a vague signal look accepted even when the candidate itself lacks concrete evidence shape.

This slice narrows acceptance semantics without changing the non-authoritative LLM boundary. MiniMax may still propose candidates, but deterministic evidence-shape checks decide whether those candidates are accepted, rejected, or sent to `needs_review`.

## Failure mode from S07

Exploratory S07 smoke used two candidates:

- one `relationship_candidate` with useful structural summary;
- one weak `graph_context_signal` with low confidence and no candidate-specific source refs.

Both became accepted because the run-level source ref was inherited by normalization and passed the existing verifier adapter. S03 treats this as a hardening target: inherited run-level refs alone should not be enough to accept weak `graph_context_signal` candidates.

## Evidence-shape rule

For `graph_context_signal` candidates, accepted verifier output should require candidate-specific support beyond inherited run-level refs. Candidate-specific support may include a non-empty structural summary, supporting context, explicit evidence refs, or future richer shape fields. If this support is absent or too weak, the verifier adapter should produce a deterministic `needs_review` or `rejected` outcome instead of accepted.

Expected safe reason codes include:

- `graph-context-signal-weak-evidence-shape`
- `graph-context-signal-inherited-refs-only`
- `graph-context-signal-needs-review`

The exact status can be `needs_review` or `rejected`, but it must be deterministic and safe. It must not echo unsafe refs, raw provider payloads, raw legal text, raw vectors, secrets, or legal-answer prose.

## Compatibility expectation

S03 must preserve the accepted path for a supported `relationship_candidate`. A relationship candidate with safe source refs and a useful structural summary should still be accepted by the deterministic verifier and should still stage through S02's `graph-context-stage` path.

## Observability expectations

Verifier and staging artifacts should make the hardening visible through:

- verifier decision `verifier_status`;
- deterministic reason codes in rejection or review queue diagnostics;
- graph-context staging diagnostics when a non-accepted signal is skipped;
- summary counts showing staged vs skipped rows.

## Observed hardening evidence

T04 temporary-workspace smoke used two mocked candidates:

- supported `relationship_candidate`;
- weak `graph_context_signal` with low confidence and minimal summary.

Observed result:

```json
{
  "verifier_status_counts": {"accepted": 1, "needs_review": 0, "rejected": 1},
  "staged": 1,
  "skipped": 1,
  "weak_signal_reasons": [
    "graph-context-signal-needs-review",
    "graph-context-signal-weak-evidence-shape"
  ]
}
```

The weak signal was not silently accepted. It produced a rejected verifier decision and a graph-context staging diagnostic with `verifier-status-not-accepted`. The supported relationship candidate still staged. The first smoke assertion expected the inherited-ref reason code as well, but normalized CLI rows carried enough context that the observed deterministic reasons were weak evidence shape and needs review; this still satisfies the hardening goal.

## Non-claims

S03 hardening does not claim:

- legal correctness;
- parser completeness;
- product retrieval quality;
- production ETL readiness;
- FalkorDB graph ingestion;
- R035 validation;
- R037 validation;
- R038 validation.

S03 explicitly does not validate R035, does not validate R037, and does not validate R038.

## T01 verification markers

This proof intentionally includes `graph_context_signal`, inherited run-level refs, evidence-shape, `needs_review`, `rejected`, `R035`, `R037`, and `R038`.
