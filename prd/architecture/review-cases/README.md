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

## Codecs and runtime contour

Measured S02–S06 shape under `src/law_nexus_harness/review_case/` and Governor:

- **Inner model (S02/S04):** pure stdlib frozen values, policy, ports, and
  application use cases. No pydantic, pathlib, CLI, Governor, or GSD imports.
  Pure `apply_event` / `replay_events` materialize state from a clean base packet
  plus ordered consequential events, including opaque `execution_linked` status.
- **Pydantic v2 (S03/S04, adapter-only):** strict `extra=forbid` JSON codec mapping
  `review-case/v1` packets and `review-case-event-ledger/v1` envelopes ↔ pure
  domain values. Public APIs return domain types only; `BaseModel` stays inside
  the adapter. Generated schema is diagnostic and must resolve through native
  `$ref` enums — it is not a second authority.
- **Filesystem + hashlib adapters (S03):** root-confined source reads and atomic
  packet persistence under
  `prd/architecture/review-cases/packets/` by default. Symlinks, path escape,
  forbidden local/historical prefixes, duplicate IDs, and corrupt packets fail
  closed.
- **Append-only event ledger (S04):** one immutable envelope file per sequence
  under `prd/architecture/review-cases/packets/<packet-id>/events/`. Envelopes
  carry sequence, previous-envelope hash, event hash, and envelope hash. Gaps,
  forks, hash tamper, duplicates, partial temps, and path escape fail closed.
  Application commands append only after pure apply succeeds, then rematerialize
  from durable ledger state. External IDs remain opaque references — no GSD or
  authority lifecycle is created or mirrored.
- **CLI (S03/S05):** `law-nexus-harness review-case {register,validate,status}`
  emits deterministic JSON reports. Exit `0` success, `1` validation/policy, `2`
  tool/adapter. `validate`/`status` rematerialize base packets through the ledger;
  `register` remains base-only. Commands do not record human disposition, promote
  authority, or create GSD work.
- **Governor (S05):** check `review-case-integrity` hard-fails on authority
  laundering, source-hash mismatch, orphan promotion, class-mismatched closure,
  and ledger chain defects. Undispositioned open findings are advisory inventory
  only and never elevate overall Governor status to failure. Portable process
  suite coverage includes CLI, schema, delta fixture, and Governor checks.
- **Delta map (S06):** pure `build_review_delta_map` plus tracked
  `review-11-12-delta-map.md` inventory residual open findings and candidate
  cross-review relations. Confirmed closures remain empty without human events.
- **Adaptix:** still deferred. No measured mapping pain required it on the v1
  critical path; it remains absent from runtime and tests.

Tracked JSON Schema remains the explicit wire contract. A generated schema may
be checked against it; it must not silently become a second authority.

## Two-review delta map

Tracked inventory:
[`review-11-12-delta-map.md`](review-11-12-delta-map.md)

Built from the pure `build_review_delta_map` projection over
`fixtures/review-11-12-delta-v1.json`. It classifies reassessed, refined,
duplicate, roadmap-proposal, new, and residual-open findings. Confirmed closures
and accepted promotions are empty until human disposition events exist.

## Non-claims

These **non-claims** are mandatory reading for any packet consumer:

- Packets are **non-authoritative**. Green schema validation or CLI exit 0 is not
  semantic acceptance, product readiness, or legal correctness.
- S05 process gates prove structural integrity and clean-clone coverage only.
  They do **not** auto-disposition real reviews, accept findings, or create GSD
  work. Open findings remain advisory inventory.
- No finding is accepted, rejected, or closed merely by existing as a packet or
  by being registered through the CLI.
- The S06 delta map is an inventory only. Real review-11/review-12 findings remain
  `open / unplanned / unverified` until explicit human disposition later. Ledger
  capability and the delta map do not themselves accept those findings.
- Roadmap proposals inside reviews remain proposals until separately adopted.
- Opaque `execution_linked` / `promoted_to` references do not mutate GSD,
  Product, Requirements, ADR, or roadmap lifecycle state.
- No product-domain Rust type, temporal resolver, applicability engine, parser
  completeness, RuVector, retrieval quality, or citation safety is claimed.
- The test-side structural oracle under `tests/test_review_case_schema.py` is
  not product authority; runtime validation is the pure domain/policy path plus
  the outer codec adapter and ledger integrity checks.
