---
id: ADR-0012
title: Consequential architecture and implementation evidence protocol
status: Accepted
lifecycle: "[bounded]"
date: 2026-07-22
supersedes: none
related: [ADR-0004, ADR-0005, ADR-0008, ADR-0009, ADR-0010, ADR-0011, D121, D127, R071, M111-yokzin, M112-8zlrv6]
---

# ADR-0012: Consequential architecture and implementation evidence protocol

## Status

**Accepted `[bounded]` process decision.** M111 demonstrates the protocol across
material architecture selections, including independent negative-experience
reviews and explicit unknowns. R071 remains active because every future material
selection must repeat the protocol for its own decision context.

## Context

Architecture drift occurs when a familiar library, benchmark, package shape or
vendor claim becomes a default without checking the project's legal evidence,
authority, temporal, ownership and Rust-only constraints. External research can
also create false confidence when search summaries or unrelated production
numbers are treated as local proof.

## Decision

Adopt D121/R071 at the `[bounded]` process ceiling as an admission gate before
every material architecture, dependency, interface, pipeline or
implementation-planning selection.

A decision packet must record:

1. the exact decision question, scope and acceptance criteria;
2. primary or official provenance with URL/revision/date where applicable;
3. positive experience showing the candidate can satisfy the intended class of
   problem;
4. negative experience, incident evidence or known failure modes;
5. applicability and transferability limits for law-nexus;
6. independent confirmation from a second source or a bounded local probe for
   consequential claims;
7. explicit `adopt`, `adapt`, `reject`, `defer`, `unresolved` or equivalent
   disposition with rationale;
8. measured efficiency/capacity evidence for consequential performance claims,
   or an explicit `unknown` with measurement obligation;
9. proof ceiling and non-claims, including which runtime/legal/capacity outcomes
   remain unsupported;
10. owning ADR/contract, revisit conditions and objective verification.

Search summaries, generated research reports, popularity, ecosystem convention
and vendor benchmarks are discovery inputs only. They are not sufficient proof
for consequential selection.

### Application to future implementation decisions

A future crate, database, FalkorDB schema, storage design, queue/ledger, network
API, parser, serialization format, concurrency runtime, deployment topology or
test framework must pass this gate before selection. The gate evaluates a
concrete requirement; it does not require speculative research for decisions not
yet needed.

Comparable local probes must preserve the M111 authority, five-clock,
C10/C12/C13, KOF-DA, query/citation and diagnostic boundaries. A fast candidate
that violates those contracts is rejected rather than accepted as a tradeoff.
Consequential performance selection requires efficiency evidence or explicit
`unknown` with a measurement obligation.

## Rejected alternatives

- Select the most popular or familiar tool and document evidence afterward.
- Treat vendor/global benchmarks as law-nexus capacity or efficiency proof.
- Use one positive source without negative experience or transferability review.
- Require exhaustive research for trivial reversible choices.
- Treat search summaries, LLM output or generated projections as authority.
- Mark the protocol permanently validated after one milestone.
- Suppress unknowns by inventing plausible measurements or implementation facts.

## Consequences

### Positive

- Material choices retain exact provenance and failure lessons.
- Future agents can distinguish selected, deferred and unresolved technology.
- Capacity and performance claims remain measurable rather than rhetorical.
- ADR revisit decisions have durable context and evidence ceilings.

### Negative

- Material selections require more work before implementation.
- Some decisions remain deferred until a local probe is affordable.
- Evidence packages require maintenance when versions or operating assumptions
  change.

## Invalidation and revisit

A material decision is inadmissible if it lacks primary provenance, negative
experience, transferability limits, independent confirmation/probe, explicit
disposition or honest efficiency evidence/unknown.

Revisit a selected decision when its version, environment, scale, legal/evidence
contract, failure surface or governing requirement materially changes. Reusable
prior evidence may be cited, but the new context and applicability must still be
assessed.

## Proof and non-claims

- M111 proves bounded use of this protocol, not universal future compliance.
- R071 remains active as an ongoing quality attribute.
- Passing the evidence gate does not prove product runtime, legal correctness,
  source completeness, security or production capacity.
- This ADR selects no database, FalkorDB schema, storage, queue/ledger, crate,
  API, parser, runtime, deployment topology or test framework.
- External metrics do not establish E1-E3 or law-nexus efficiency without
  comparable local measurements.

## Storage, ledger and workspace candidate matrix

**Lifecycle:** `[bounded]` protocol application only. This matrix records
candidate dispositions and role boundaries; it does not select a product
backend or validate ledger runtime, legal authority, capacity or durability.

| Candidate | Role under review | Disposition | Current proof ceiling |
|---|---|---|---|
| SQLite | Authoritative local typed-event ledger comparison baseline | `adopt` as baseline only | Mature reference and bounded local mechanics; no product ledger cutover |
| Turso Database | Future pure-Rust SQLite-compatible ledger candidate | `defer` | Active pre-1.0 engine; incomplete compatibility, no Backup API, experimental critical surfaces and open crash/checkpoint failure reports; bounded local probe only |
| AgentFS | Agent copy-on-write workspace and audit | `defer`, `separate-role` | Beta documentation; no OS-sandbox, base-immutability or audit-completeness runtime proof |
| LadybugDB | Graph/vector/FTS projection | `separate-role` | Local GitNexus compatibility does not prove law-nexus authority, schema or capacity |
| ruVector | Agent runtime, memory, adaptive retrieval and optional graph/vector computation | `separate-role` | Bounded source/test evidence; never ledger or legal authority |

`adopt as baseline` identifies the reference implementation for comparison. It
is not a declaration that law-nexus currently ships a SQLite product ledger.
Turso remains `defer` regardless of a bounded probe result until a fresh
human-reviewed packet changes the disposition.

### Turso and AgentFS re-evaluation gates

Re-open Turso for an authoritative role only when required SQLite compatibility
and backup/restore surfaces exist; relevant checkpoint, corruption and namespace
failure classes are closed or proven inapplicable; no experimental MVCC,
encryption, multiprocess WAL, FTS, CDC, sync or MCP surface underwrites
authority; local crash/reopen, checkpoint, ENOSPC, restore and exit-to-stock-
SQLite probes pass at the exact proposed version; capacity is measured; and
agents cannot write the authority store.

AgentFS remains a non-authoritative workspace candidate. A `[bounded]` local
probe must establish base immutability, symlink/path behavior, crash/reopen, MCP
filtering, audit coverage and bounded resource growth. AgentFS does not replace an OS
process sandbox, Git isolation, rvAgent tool policy or the legal authority
ledger. Cloud sync and remote exposure are outside the candidate role.

The bounded evidence packet and exact primary anchors are maintained in
`prd/architecture/storage-ledger-workspace-candidate-assessment.md`; AgentFS
threat and probe details are maintained in
`prd/research/agentfs-filesystem-isolation-assessment-2026-07-23.md`.

## References

- `prd/architecture/m111-final-architecture-baseline.md`
- `prd/architecture/m111-prior-art-reconciliation.md`
- `prd/research/m111/hexagonal-onion-boundary-comparison.md`
- `prd/research/m111/whole-system-adversarial-closure.md`
- `prd/research/m112/active-adr-drift-audit.md`
- D121, D127 and R071
