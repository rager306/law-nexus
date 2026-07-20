---
id: ADR-0001
title: Onion package structure for src/law_nexus
status: Accepted
lifecycle: "[validated]"
date: 2026-06-21
superseds: none
related: [D046, D097, D098, D035, M068-xi4034]
---

# ADR-0001: Onion package structure for src/law_nexus

## Status

**Accepted [validated]** — the four-layer onion layering (`domain` → `ports` →
`application` → `adapters` + an explicit composition root) is validated: it
exists in the repository, type-checks clean (`basedpyright src/` → 0 errors),
and one real adapter proves the end-to-end seam through the whole stack.

The decision's **structural** claim is `[validated]`. Two nested claims are
intentionally weaker and are tagged inline, not smoothed to `[validated]`
(D098 anti-drift):

- the **Pydantic domain forms** are `[proposed]` — they are shapes that harden
  when real parser data arrives, not proof of the D046 ontology; and
- the **port contracts** are `[proposed]` — they declare the shape adapters
  satisfy but only one adapter and one use case exercise them so far.

## Context

Before M068, the repository was a verification-only workspace: domain logic,
parsing, and retrieval lived as standalone scripts under `scripts/` (137 files)
and tests (155 files), with no importable package. That shape served earlier
milestones but blocked three things:

1. **Dependency direction.** Scripts freely import each other and infrastructure
   (FalkorDB, embedding libraries, file I/O) wherever convenient. There is no
   enforced boundary between the legal domain model and the infrastructure that
   reads or persists it. As the product grows this becomes unmanageable and
   hides where the evidence/authority boundary actually is.
2. **Testability of the deterministic core.** D046 ([validated] governance
   record, `.gsd/DECISIONS.md`) fixes the project-local LegalGraph core as the
   internal contract and treats external ontologies (Akoma Ntoso, FRBR, LKIF,
   RusLegalCore, BFO, GOST, OWL) as reference/compatibility layers behind proof
   gates. To keep that core provable and free of premature infrastructure, the
   domain model must not import FalkorDB, embedding models, or HTTP clients.
3. **Profile boundary (D097).** Since M067, law-nexus is a **profile consumer**
   of the externalized reusable core at `/root/git-lex-kit-acp/`
   (`rager306/git-lex-kit-acp`). law-nexus owns the law-specific constraints
   (Russian legal evidence, FalkorDB, citation-safe retrieval, ODT/Consultant
   parsing) and the GSD anti-drift governance (D098). The package structure must
   make that product boundary concrete — the legal domain model and its ports
   are law-nexus-owned product substance, not generic kit material.

S01 of M068 turned the repository into the importable package `src/law_nexus`
along this onion layering and proved the end-to-end seam with one real adapter
(`ConsultantWordMLParser`). This ADR records that decision so the layering is a
reviewed architectural commitment, not an accident of the first slice.

The split with `.gsd/DECISIONS.md` (see `doc/adr/README.md`) is preserved here:
the `D0xx` rows are governance events; this ADR is the architectural substance.

## Decision

Adopt a **dependency-directed onion package structure** for `src/law_nexus`
with four layers and one composition root, where dependencies point **inward
only** (outer layers may depend on inner layers; inner layers never depend on
outer layers or infrastructure):

```
src/law_nexus/
├── domain/          # Pydantic v2 models — the D046 core [proposed]
├── ports/           # typing.Protocol contracts [proposed]
├── application/     # use cases [bounded]
├── adapters/        # infrastructure adapters [bounded] (outer ring — all I/O)
└── composition.py   # composition root [bounded]
```

The layers, with their lifecycle evidence status per D098:

- **`domain/`** — the D046 Pydantic v2 core (`[proposed]`). Pure data shapes —
  `SourceDocument`, `SourceBlock`, `LegalUnit`, `ActEdition`, `EvidenceSpan`,
  `NormStatement`, `Citation`, `source_hierarchy` — with basic validation
  (at-least-one, span/window ordering) and **no logic** (no conflict resolution,
  no temporal derivation). It imports only `pydantic`, `typing`, stdlib `enum`
  /`datetime`, and intra-domain references. It carries **zero infrastructure
  imports**. These forms harden toward `[validated]` only when real parser data
  arrives; until then they are `[proposed]` and do not prove the R035/R037/R038
  contracts they materialise.
- **`ports/`** — pure `typing.Protocol` contracts (`[proposed]`):
  `Parser`, `LLMClient`, `GraphStore`, `Embedder`. Each declares the *shape*
  adapters must satisfy with a docstring and `...` body only — no executable
  logic, no implementation. The domain layer is the ports' only dependency. The
  `LLMClient` port encodes the LLM Control Policy: its output is
  non-authoritative candidate signal, never legal authority. Ports are
  `[proposed]` until more than one adapter/use case exercises them.
- **`application/`** — use cases (`[bounded]`). Thin orchestration that depends
  on `ports` protocols and `domain` models, never on concrete adapters or
  infrastructure. `Ingest` is the first one: deterministic-first, returns a
  `SourceDocument`, leaves `imported_at` `None` for reproducibility.
- **`adapters/`** — infrastructure adapters (`[bounded]`), the **outer ring and
  the only layer permitted to do I/O** (filesystem, network, DB, model calls).
  Adapters structurally satisfy the ports. `adapters/parsers/
  consultant_wordml.py` is the first real one — a minimal document-level
  Consultant WordML reader via stdlib `xml.etree`, with path-confinement and a
  typed `ConsultantParseError`.
- **`composition.py`** — the composition root (`[bounded]`): a small set of
  explicit factory functions (`make_default_ingest()`) that wire concrete
  adapters into use cases. It is **not** a dependency-injection framework.

**Composition root is explicit factory functions, not a DI framework.** Each
factory is a single, readable wiring statement. The decision is deliberately to
avoid a DI container: at the current size a framework would add an abstraction
with no payoff, and explicit wiring keeps the trust boundary visible — you can
see exactly which adapter backs which port by reading one function.

**Static conformance is checked, not asserted at runtime for the happy path.**
Adapter-to-port conformance is checked statically by `basedpyright` (the parser
is assigned to a `Parser`-typed alias at the composition root). The ports are
`runtime_checkable` so structural conformance *can* be asserted in tests, but
the happy path does not pay an `isinstance` cost; that is a test affordance, not
a production check.

**D046 forms, not D046 proof.** The Pydantic models are the *forms* mandated by
D046; recording them as code does not validate the ontology or close any proof
gate. Per D098, promoting a `[proposed]` form to `[validated]` requires real
parser data and explicit review, never a silent lifecycle smoothing. This is the
exact drift pattern D098 exists to prevent.

## Consequences

- **Easier — dependency direction is now enforceable.** A new domain model that
  imports FalkorDB or an embedding library fails `basedpyright` (it breaks the
  ports' zero-infra invariant) and is visible in review. The deterministic legal
  core can be tested without standing up infrastructure. `[validated]` for the
  layering invariant; the tests enforcing it are part of the S01 verification
  suite.
- **Easier — trust boundary is one place.** All I/O is in `adapters/`. The S01
  threat model found exactly one product-layer trust surface
  (`consultant_wordml.py`); path-confinement and a typed error harden it. Adding
  a new source format means adding one adapter behind the `Parser` port without
  touching the domain. `[bounded]` — proven for one adapter, structural for the
  rest.
- **Easier — profile boundary (D097) is concrete.** The `domain`/`ports`
  package is law-nexus product substance; the external kit stays out of the
  import path. law-nexus-specific constraints (Russian legal evidence,
  citation-safe retrieval, generated-Cypher safety) live against the domain, not
  against generic kit code.
- **Harder — two Consultant readers must be reconciled.** `scripts/source_cli.py`
  (legacy) and the new `src/` adapter both read Consultant WordML. The M034
  roadmap must resolve this (single-source vs adapter-wraps-scripts) before they
  silently diverge. `[deferred]` to the next milestone — captured as the highest
  priority follow-up in the S01 summary.
- **Harder — lifecycle discipline must be maintained.** Every new `src/` module
  must carry a D098 lifecycle tag from day one. The S03 verify-adr-conformance
  gate will check this. The baseline gap: `scripts/` (137 legacy files) carry no
  tags; those are out of scope for this layering decision but are tracked.
- **We will revisit:** (1) the domain forms when real parser data arrives — then
  reassess `[proposed]` → `[bounded]`/`[validated]` per claim, never wholesale;
  (2) the port contracts when a second adapter exercises them; (3) whether the
  composition root should grow toward a thin DI layer only if wiring genuinely
  becomes repetitive — until then, explicit factories win.

## Alternatives Considered

### Option A: Keep the flat, scripts-first layout (status quo before M068)

**Pros:** no restructuring cost; scripts already work and are tested; no new
import boundaries to learn.
**Cons:** no enforced dependency direction — domain logic and infrastructure
co-mingle freely, so the deterministic core cannot be tested in isolation and
the trust/authority boundary is invisible. It is incompatible with D046 (pure
core) and with making the D097 profile boundary concrete. It does not scale to a
product that must keep FalkorDB/embedding out of the legal domain.

### Option B: Adopt a dependency-injection framework at the composition root

**Pros:** a container could auto-wire adapters to ports and reduce boilerplate
as the number of ports/adapters grows.
**Cons:** premature abstraction at the current size — a framework buys nothing
when there is one adapter and one use case, and it hides the exact adapter
backing each port behind configuration/magic. Explicit factory functions make
the trust boundary readable at a glance, which matters more here than wiring
brevity. We can revisit this only if wiring genuinely becomes repetitive; the
decision records that explicitly.

### Option C: Use dataclasses / attrs / Adaptix instead of Pydantic for the core

**Pros:** dataclasses/attrs avoid a runtime validation dependency; Adaptix
(D035) offers configurable conversion between boundary DTOs and internal
records.
**Cons:** D035 already settled this for parser I/O boundaries — Pydantic v2's
`BaseModel`/`TypeAdapter`/JSON Schema ecosystem is strongest for malformed
external records and is the most recognisable shape for future agents. Pydantic
also gives cheap frozen models (used by `EvidenceSpan`'s SHA-keyed immutability,
an R034 fail-closed contract). Adaptix remains available for
mapping/conversion when those mappings become non-trivial; it is not the
first-line domain form.

## References

- **D046** (`.gsd/DECISIONS.md`) — keep the project-local LegalGraph core as the
  internal contract; treat external ontologies as reference layers behind proof
  gates. The `[proposed]` domain forms are the D046 shapes; they are not D046
  *proof*.
- **D098** (`.gsd/DECISIONS.md`) — ACP/git-lex role is anti-drift enforcement;
  mandatory lifecycle tagging (`[proposed]`/`[bounded]`/`[smoke]`/
  `[validated]`/`[deferred]`) on architectural/state claims; never smooth a
  bounded or proposed claim up to `[validated]`. This ADR applies that discipline
  to every significant claim.
- **D097** (`.gsd/DECISIONS.md`) — law-nexus is a profile consumer of the
  externalized reusable core at `/root/git-lex-kit-acp/`; law-nexus owns
  law-specific substance and the GSD governance layer. The package structure
  makes that product boundary concrete.
- **D035** (`.gsd/DECISIONS.md`) — Pydantic at parser I/O boundaries (Option C
  provenance); Adaptix reserved for non-trivial mapping.
- **`doc/adr/README.md`** — the MADR standard, significance gating, D098 tag
  policy, and the split between ADRs and `.gsd/DECISIONS.md` that this ADR
  follows.
- **`prd/02_architecture.md`** — the architectural oracle for the evidence chain
  (`NormStatement → EvidenceSpan → LegalUnit → SourceBlock → SourceDocument`,
  with `ActEdition` carrying the temporal window), the LLM Control Policy, and
  the import-package seam the `Parser` port mirrors.
- **M068-xi4034 / S01** — the slice that built this structure and proved the
  end-to-end seam (`make_default_ingest().parse(...)` → `SourceDocument`);
  verification evidence is in the S01 summary.
