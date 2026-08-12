---
id: ADR-0024
title: Review Case intake, disposition, and non-authority contour
status: Accepted
lifecycle: "[proposed]"
date: 2026-08-12
supersedes: none
related: [ADR-0007, ADR-0008, ADR-0010, ADR-0012, ADR-0015]
---

# ADR-0024: Review Case intake, disposition, and non-authority contour

## Status

**Accepted [proposed]** — the authority ceiling, onion boundaries, disposition
gate, versioned wire-contract shape and revision-bound closure rules are decided.
No Review Case domain implementation, packet codec, CLI command, Governor check,
canonical promotion, GSD integration or processed-review result exists merely
because this ADR is accepted.

The contour may move to `[bounded]` only after its pure application contracts,
strict persistence adapter, CLI contract, hostile authority-boundary tests and
portable Governor integrity checks pass. Documentation, a valid packet, an LLM
normalization or a green Governor report cannot establish semantic acceptance,
product implementation, legal correctness or review closure.

## Context

The repository receives consequential human and external architecture reviews.
Their original prose preserves context, but prose alone does not provide a
deterministic inventory of findings, source spans, dependencies, decisions,
partial implementation, proof or revision-bound closure. Chat history is not a
durable repository surface, and manually copying recommendations directly into
requirements or plans risks losing provenance and laundering reviewer or LLM
interpretations into project authority.

The repository already separates several responsibilities:

- ADR-0007 confines active Python to the repository-control harness;
- ADR-0008 separates candidate work from promotion and publication authority;
- ADR-0010 requires immutable evidence and closed relationship kinds;
- ADR-0012 requires consequential technology choices to preserve evidence,
  negative experience, transferability limits, proof ceilings and revisit gates;
- ADR-0015 requires class-appropriate proof, hostile paths and lifecycle honesty;
- GSD owns local execution lifecycle but is not a cold-reader architecture truth
  surface;
- `prd/ARCHITECTURE.md`, active ADRs, Product and Requirements retain their
  existing authority roles.

Two tracked reviews demonstrate the need for a durable intake contour:

- `doc/review/review-11-08-2026.md` reviews revision `60fd8245...`;
- `doc/review/review-12-08-2026.md` reviews revision `1092ef4...` and reassesses
  part of the earlier criticism.

The later review records both improvements and residual gaps and proposes a
future milestone sequence. Those proposals are review evidence, not an accepted
roadmap. A safe contour must preserve that distinction while making repeated,
refined, split, blocked, partial, rejected, deferred and stale outcomes visible.

## Decision

### 1. Adopt a six-layer Review Case contour

The repository-control model is:

```text
L0 immutable review source
  → L1 non-authoritative Review Case projection
  → L2 human disposition ledger
  → L3 existing canonical authority surfaces
  → L4 existing GSD or repository execution
  → L5 class-matched revision-bound evidence and closure
```

Each layer retains its own authority. A downstream link does not copy or replace
the target system's state.

### 2. Preserve the raw review as immutable source evidence

A Review Case source record identifies at least:

- a stable Review Case identifier;
- a repository-relative tracked source path;
- the source content SHA-256;
- the Git revision reviewed by the source;
- the receipt timestamp and source class.

The original review remains reconstructable. A changed source hash makes the
normalization stale; the system must not silently rewrite spans or prior events.
A corrected or expanded review is a new source revision with explicit relations
to earlier findings.

### 3. Treat the Review Case AST as a projection, never authority

Every persisted packet and report must declare:

```text
authoritative = false
authority_required = true
schema_version = review-case/v1
```

The v1 model is deliberately small: one `Finding` node shape with a closed
`kind` vocabulary, exact source spans, opaque candidate targets, a closed
relation vocabulary and append-only lifecycle events. It is not a general
architecture graph, legal ontology, requirements database or task engine.

Normalization may be manual, script-assisted or LLM-assisted. It may propose
summaries, kinds, links, duplicates and research needs. It cannot accept a
finding, create a canonical requirement or decision, adopt a roadmap proposal,
promote lifecycle or assert closure.

### 4. Require reconstructable source spans

Every actionable finding cites at least one source span containing:

- repository-relative source path;
- line range;
- optional heading;
- hash of the normalized cited text.

A packet whose source hash or span hash no longer matches is stale or invalid.
A paraphrase without reconstructable source evidence is not an actionable
finding.

### 5. Separate candidate mapping from accepted promotion

The relation vocabulary distinguishes:

```text
maps_to      candidate interpretation only
promoted_to accepted canonical relationship after human disposition
```

`maps_to` never implies acceptance, satisfaction or closure. `promoted_to`
requires an earlier append-only human disposition event with actor identity,
rationale, time, source revision and target. A tool or LLM may not issue an
accepting or promoting disposition.

Canonical targets remain the existing surfaces, including Product,
Requirements, active ADRs, the architecture oracle, tracked gap or defect
registers and the accepted roadmap. Review Case persistence stores references to
those targets, not copies of their lifecycle state.

### 6. Keep four lifecycle dimensions orthogonal

A finding records independent dimensions rather than one ambiguous status:

1. normalization: draft, source-verified, human-reviewed or stale;
2. disposition: open, discussion/research required, accepted by class, already
   satisfied, rejected, deferred, duplicate, superseded or not applicable;
3. execution: not required, unplanned, planned, blocked, in progress, partial,
   implemented or cancelled;
4. verification: not applicable, unverified, inconclusive, failed, bounded,
   smoke, validated or stale.

A generated roll-up may report open, blocked, partial, ready for closure, closed,
terminal without implementation or stale. The roll-up is derived and is never
an author-written source of truth.

### 7. Record disposition and closure as append-only events

Consequential lifecycle changes are events. They preserve the actor class,
actor identifier when available, timestamp, finding, rationale, repository
revision and event-specific payload. Verification additionally records the
tested revision, proof class, durable evidence anchors, residual scope and
explicit non-claims.

Reopening or marking stale appends an event and does not delete earlier human
decisions or verification history.

### 8. Match closure to the concern and proof class

The closed proof classes are:

```text
docs | design | implementation | evidence | process
```

A documentation change cannot close an implementation or evidence gap. A design
ADR cannot prove runtime behavior. Synthetic or InMemory proof cannot establish
representative legal correctness. A parent finding cannot close while a required
child or active blocker remains open.

Partial closure is first-class and must expose completed scope, residual scope,
blockers, tested revision, evidence class and non-claims. Rejected, duplicate,
superseded and not-applicable findings are terminal dispositions, not
implementation success.

### 9. Link execution without duplicating GSD

Review Cases may refer to existing milestone, slice and task identifiers after a
finding has been promoted through canonical authority. They do not store or
control GSD task lifecycle, retry history, verification authority or completion
state. GSD remains the execution system; the Review Case contour remains intake,
disposition and traceability.

No review recommendation may create a milestone automatically. In particular,
the M166–M176 sequence proposed in the 12 August review remains a
`roadmap_proposal` unless separately adopted through project planning authority.

### 10. Use a hexagonal and onion dependency direction

The active implementation remains in the Python repository-control harness and
contains no product or legal-domain logic.

```text
CLI and Governor adapters
  → application use cases
  → pure Review Case policy
  → ports
  ← filesystem, codec, authority-reference, execution-reference and evidence adapters
```

At the `[proposed]` design ceiling, inner domain and application contracts use
Python standard-library frozen data classes, enums and `Protocol` ports. They must not import filesystem,
`argparse`, Governor report types, GSD types, Pydantic, Adaptix or product-domain
packages. External adapters map wire data and external references to the pure
contracts.

### 11. Bound Pydantic and defer Adaptix

Pydantic v2 is selected only as the candidate strict JSON codec and JSON Schema
adapter for a later bounded probe because it is already a locked runtime
dependency and provides documented strict validation, extra-field rejection,
discriminated unions, structured field-path errors and JSON Schema generation.
It is not an inner-layer model framework and is not adopted until hostile decode,
deterministic serialization, schema-fidelity, typing and clean-runtime packaging
probes pass.

Adaptix remains deferred. It is currently a development-only dependency at a
locked beta version, while v1 has no demonstrated multi-shape migration or
mapping complexity that justifies a second conversion framework and error
surface. A future decision may revisit Adaptix only with measured mapping pain,
a pinned candidate, official API evidence, negative-experience review and local
compatibility probes under ADR-0012.

The tracked versioned JSON/JSONL wire contract remains explicit. A generated
schema may be checked against that contract but cannot silently become a second
schema authority.

### 12. Limit Governor to deterministic integrity checks

Governor may fail closed on malformed schema, missing source, source or span hash
drift, unknown relationship kinds, invalid references, authority laundering,
promotion without human disposition, impossible status combinations,
class-mismatched closure, missing tested revision and a closed parent with open
blocking children.

Governor may warn about open disposition, possible duplicates, extraction
coverage or stale candidate mappings. Heuristic and LLM findings remain advisory.
Governor may not decide whether reviewer criticism is correct, accept semantic
requirements, create ADRs or milestones, declare legal correctness, or close a
finding from prose or CI success alone.

## Verification contract

Each implementation wave must prove its own contour:

1. schema and pure-domain contract tests cover positive and hostile inputs;
2. source spans reconstruct from tracked reviews and fail on hash drift;
3. promotion by tool or LLM fails closed;
4. class-mismatched proof and blocked-parent closure fail closed;
5. codec output is byte-deterministic and diagnostics identify field paths;
6. vendor imports remain in adapters;
7. CLI reports are versioned and distinguish validation from tool errors;
8. Governor checks remain portable in a clean clone and do not depend on local
   GSD state or installed hooks;
9. real review packets retain explicit non-claims and receive human acceptance
   before any semantic disposition is presented as project authority.

The initial documentation and schema wave remains `[proposed]`. Pure synthetic
contracts and CLI integration may support `[bounded]` process claims only. No
process evidence validates product runtime or legal outcomes.

## Consequences

### Positive

- original review context remains reconstructable without chat history;
- repeated and refined reviews can be compared without deleting prior evidence;
- human acceptance is explicit and auditable;
- accepted work can be traced through canonical authority, execution and proof;
- partial work, blockers, stale proof and non-claims remain visible;
- strict onion boundaries keep vendor codecs and external systems replaceable;
- Governor can enforce integrity without becoming a semantic authority.

### Negative

- source spans, hashes, disposition events and proof anchors add process work;
- reviewers and maintainers must distinguish candidate mappings from promotion;
- schema and event evolution require explicit versioning and migrations;
- some findings will remain open or partial longer instead of being smoothed into
  a green status;
- Pydantic still requires bounded local probes despite already being installed;
- deferred Adaptix means migrations use explicit code until measured complexity
  justifies another adapter.

## Rejected alternatives

1. **Convert every review recommendation directly into requirements or GSD
   tasks.** Rejected because it launders external interpretation into authority
   and creates duplicate execution state.
2. **Use one mutable mega-JSON as source, disposition ledger and task tracker.**
   Rejected because it erases event history, causes merge conflicts and becomes
   a second source of truth.
3. **Store only summaries without exact spans.** Rejected because context and
   reviewer meaning cannot be reconstructed.
4. **Let Governor or an LLM decide semantic resolution.** Rejected because
   structural validation is not human architectural or legal judgment.
5. **Model Review Cases as OWL, a graph database or the existing quarantined
   architecture registry.** Rejected as unnecessary infrastructure and an
   authority-boundary regression.
6. **Use Pydantic models throughout all layers.** Rejected at `[proposed]`
   because serialization technology would own application policy and ports.
7. **Adopt Pydantic and Adaptix together immediately.** Rejected at `[proposed]`
   because v1 has
   no demonstrated mapping problem that warrants dual models and dual error
   dialects.
8. **Mirror GSD task states in Review Cases.** Rejected because lifecycle would
   drift between two systems.

## Revisit triggers

Revisit with a superseding ADR or explicit amendment when:

- the two-review vertical slice cannot preserve source context with the reduced
  finding and relation model;
- real packet migrations demonstrate material mapping complexity;
- Pydantic cannot meet strict decoding, deterministic rendering, typing,
  packaging or schema-fidelity requirements at the adapter boundary;
- Review Case status cannot link to GSD without duplicating lifecycle state;
- Governor integrity checks cannot remain portable or structurally bounded;
- the contour grows beyond traceable intake and disposition and begins to delay
  product-semantic work;
- another review source class requires a materially different authority model.

The milestone must end with an explicit stop, harden or extend decision based on
measured friction. Further tooling is not the default outcome.

## Non-claims

- `[proposed]` No Review Case runtime, codec, CLI, ledger or Governor integration is implemented by this ADR.
- Review Case packets and generated views are not architecture, Product,
  Requirements, ADR, roadmap, legal or execution authority.
- No finding from either saved review is accepted, rejected or closed by this
  decision alone.
- No M166–M176 roadmap proposal from a review is adopted by this ADR.
- `[deferred]` No product-domain Rust type, temporal resolver, applicability
  engine, parser, RuVector path, retrieval quality or citation safety is
  implemented or validated by this contour.
- Pydantic is not admitted into inner layers and has no positive adoption claim
  before the bounded adapter probes pass.
- Adaptix is deferred and is not required by the Review Case v1 critical path.
- Passing Review Case or Governor checks does not replace human architectural or
  legal judgment.

## References

- D151 — Review processing as non-authoritative intake and disposition
- D152 — vendor-neutral inner model, Pydantic adapter candidate and Adaptix
  deferral
- R075–R079 — Review Case source, lifecycle, authority, integration and quality
  requirements
- `doc/review/review-11-08-2026.md`
- `doc/review/review-12-08-2026.md`
- `prd/architecture/temporal-semantic-gap-register.md`
- ADR-0007 — Python repository-control boundary
- ADR-0008 — promotion and publication authority
- ADR-0010 — evidence kernel gates and closed relationship kinds
- ADR-0012 — consequential evidence protocol
- ADR-0015 — hexagonal verification and proof ceilings
