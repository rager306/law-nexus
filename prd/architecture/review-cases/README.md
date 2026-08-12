# Review Cases

Tracked, non-authoritative projections of immutable architecture reviews.

Authority: **ADR-0024** `[proposed]`. Living architecture truth remains
`prd/ARCHITECTURE.md` and active `doc/adr/**`. Review Case packets never become
Product, Requirements, ADR, roadmap, legal, or GSD execution authority.

## Layers (L0–L5)

```text
L0 immutable review source          doc/review/*.md
L1 Review Case projection           this contour (authoritative: false)
L2 human disposition ledger         append-only events
L3 canonical authority              PRODUCT / REQUIREMENTS / ADR / oracle / gaps
L4 execution                        existing GSD or repository work (links only)
L5 evidence and closure             class-matched, revision-bound proof
```

Each layer keeps its own ownership. A link does not copy or replace the target
system's lifecycle state.

## Packet contract

Wire schema: [`../review-case.schema.json`](../review-case.schema.json)
(`schema_version = review-case/v1`).

Hard constants:

```text
authoritative = false
authority_required = true
```

v1 is deliberately small:

- one node type: `Finding` with a closed `kind` vocabulary;
- exact `source_spans` (repo-relative path, line range, quote hash);
- opaque `candidate_targets` (`maps_to` only until human promotion);
- closed `edges` and append-only `events`;
- four orthogonal status axes on each finding;
- no author-written `derived_status`.

Packets and events are immutable projections of evidence and decisions already
made. Correcting a review means a new source revision and new packet/events, not
silent rewrite of hashes or history. Every non-`open` disposition requires a
matching human `disposition_recorded` event; `human_reviewed` normalization
requires a human `normalization_reviewed` event. Event payload keys are closed by
the v1 wire schema so metadata cannot smuggle authority-like fields.

## Candidate mapping vs human promotion

| Relation | Meaning |
|---|---|
| `maps_to` | candidate interpretation only; its edge status is always `candidate` |
| `promoted_to` | accepted canonical relationship **after** a human disposition event |

Tool or LLM actors may extract and propose. They may not record accepting
dispositions or accepted promotions.

## Four status dimensions

1. **normalization** — draft / source-verified / human-reviewed / stale
2. **disposition** — open, research/discussion, accepted-by-class, already
   satisfied, rejected, deferred, duplicate, superseded, not applicable
3. **execution** — not required, unplanned, planned, blocked, in progress,
   partial, implemented, cancelled
4. **verification** — not applicable, unverified, inconclusive, failed,
   passed_bounded / smoke / validated, stale

Generated roll-ups (open, blocked, partial, closed, stale, …) are derived views,
not writable packet fields.

## Proof classes

```text
docs | design | implementation | evidence | process
```

Closure must match the finding's required proof class. Documentation or process
proof cannot close implementation or evidence gaps. Parent findings cannot close
while required children or active blockers remain open. Verification records need
proof class, tested revision, and durable evidence anchors.

## Codecs

- **Inner model (future S02+):** pure stdlib types / ports only.
- **Pydantic v2:** candidate **adapter-only** strict JSON codec and schema helper
  for a later bounded probe. Not an inner-layer domain model.
- **Adaptix:** deferred. Not on the v1 critical path.

Tracked JSON Schema remains the explicit wire contract. A generated schema may
be checked against it; it must not silently become a second authority.

## Non-claims

These **non-claims** are mandatory reading for any packet consumer:

- Packets are **non-authoritative**. Green schema validation is not semantic
  acceptance, product readiness, or legal correctness.
- No Review Case runtime, CLI, Governor check, or GSD integration is implied by
  this README alone.
- No finding is accepted, rejected, or closed merely by existing as a packet.
- Roadmap proposals inside reviews remain proposals until separately adopted.
- No product-domain Rust type, temporal resolver, applicability engine, parser
  completeness, RuVector, retrieval quality, or citation safety is claimed.
- The test-side structural oracle under `tests/test_review_case_schema.py` is
  not the future runtime validator.
