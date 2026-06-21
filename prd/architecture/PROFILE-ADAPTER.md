# PROFILE-ADAPTER — law-nexus profile binding to external ACP/git-lex kit

## Status

Authoritative binding contract for `M067-538uby / S02` (D097 restructuring
programme). This artifact records how law-nexus binds to the externalized
ACP/git-lex reusable core at `/root/git-lex-kit-acp/` (published as
`rager306/git-lex-kit-acp`).

It supersedes the M049/S02 boundary work
(`prd/architecture/acp/M049-S02-PROFILE-ADAPTER-BOUNDARY.md`) for the
post-externalization context: M067 externalized the reusable core, so law-nexus
is now a **profile consumer**, not the ACP owner.

## Purpose

law-nexus consumes the external ACP/git-lex reusable core and adds
law-nexus-specific overrides. The binding rule is:

```text
External reusable core (this repo's generic ACP/git-lex): record, lifecycle,
evidence, proof-gate, projection, health mechanics, generic skills, kit content.
law-nexus profile: Russian legal evidence, Garant parser, FalkorDB, retrieval,
citation safety, generated-Cypher safety, and substantive R035/R037/R038 proof.
```

law-nexus must not promote git-lex, ACP projections, registry views, or polished
analysis into profile authority by shape alone.

## Binding contract

| Aspect | law-nexus (profile) | External `/root/git-lex-kit-acp/` (reusable core) |
|---|---|---|
| Role | Profile consumer; first proving ground | Reusable core; project-agnostic |
| ACP vocabulary | Consumes `acp.ttl` v0.2.0 | Owns `ontology/acp/acp.ttl` v0.2.0 (strengthened) |
| SHACL shapes | Consumes generated shapes | Owns shape generation (static + adaptive overlay) |
| Generic skills | Overrides with law-nexus-specific; references generic | Owns generic `skills/git-lex/`, `skills/acp/` |
| Kit mechanics | Consumes `kit.yml`, examples, install pattern | Owns kit content + `docs/APPLYING.md` |
| Capability matrix | Adapts generic dispositions with law-nexus evidence | Owns generic `docs/CAPABILITY-MATRIX.md` |

## What law-nexus OVERRIDES (profile-owned, lives in law-nexus)

These are law-nexus-specific and MUST NOT leak into the external reusable core.

| Override | Detail |
|---|---|
| Profile-owned requirements | R035 (ontology architecture proof boundaries), R037 (FalkorDB ingest/runtime loading path), R038 (independent review gate), plus all other law-nexus R-IDs in `.gsd/REQUIREMENTS.md` |
| Domain-specific evidence | Russian legal evidence (Garant ODT source), FalkorDB legal graph runtime, citation-safe retrieval, generated-Cypher safety, temporal modeling |
| Project-specific routing | `legalgraph-architecture-verification` skill; `gitnexus` repo `law-nexus` |
| Project-specific verification | `scripts/verify-m0xx-*.py` verifiers, law-nexus GSD state |
| Quick-start anchors | `prd/architecture/acp/M0xx-*.md` (law-nexus milestone history, 116 docs), `.gsd/REQUIREMENTS.md`, `.gsd/DECISIONS.md` |
| Operational state | `.lex/` (operational adoption, M066), law-nexus GSD milestones |

## What law-nexus CONSUMES generic from external (does NOT duplicate)

These are generic and authoritative in the external repo; law-nexus references
them rather than duplicating (drift discipline).

| Generic concern | External location |
|---|---|
| ACP vocabulary | `/root/git-lex-kit-acp/ontology/acp/acp.ttl` (v0.2.0) |
| Generic git-lex skill (runtime findings M051/M064/M065, workflows, claim-language) | `/root/git-lex-kit-acp/skills/git-lex/` |
| Generic ACP skill (ACP record rule, ACP-kit rule K0-K7, ACP→git-lex routing) | `/root/git-lex-kit-acp/skills/acp/` |
| Strengthened shapes design | `/root/git-lex-kit-acp/docs/SHAPE-CONTRACT.md`, `SHAPE-BASELINE.md` |
| Ontology rationale | `/root/git-lex-kit-acp/docs/ONTOLOGY-DESIGN.md` |
| Capability matrix (generic) | `/root/git-lex-kit-acp/docs/CAPABILITY-MATRIX.md` |
| Install + operational adoption | `/root/git-lex-kit-acp/docs/APPLYING.md` |
| Reusable-core vs profile contract | `/root/git-lex-kit-acp/docs/BOUNDARIES.md` |

## Drift discipline

- **Generic guidance authoritative source = external repo.** law-nexus skills
  **reference** generic guidance; they do **not** duplicate it inline. If the
  generic guidance changes in external, law-nexus inherits it automatically.
- **law-nexus overrides are law-nexus-owned.** Changes to law-nexus-specific
  constraints live in law-nexus and do not propagate to the external core.
- **The no-leak verifier** (`scripts/verify-m067-s01-externalization.py`)
  enforces that no law-nexus-specific material leaks into the external repo.
- **The profile-binding verifier** (`scripts/verify-m067-s02-profile-layer.py`)
  enforces that law-nexus skills reference the external generic skills and apply
  law-nexus-specific overrides, with no orphaned inline generic duplicates that
  would drift from external.

## Migration note

- **M066-k97nro** = last ACP-inline milestone (ACP/git-lex work done inside
  law-nexus).
- **M067-538uby** = externalization programme. S01 externalized the reusable
  core; S02 (this artifact) restructures law-nexus as a profile consumer; S03
  revises PROJECT.md/roadmap.
- After M067, the ACP/git-lex project **continues separately** in
  `/root/git-lex-kit-acp/`; law-nexus refocuses on product substance
  (parser/source-structuring, retrieval/citation, FalkorDB legal graph).

## Forbidden promotions (carried from M049/S02)

law-nexus must NOT, from ACP/git-lex/projection evidence alone:

- validate R035, R037, or R038;
- claim Russian legal correctness, Garant parser completeness, FalkorDB runtime
  behavior, retrieval quality, citation safety, or generated-Cypher safety;
- promote git-lex to source truth, L2 operational backend, or profile validator;
- treat projection shape (RDF/OWL/SHACL/SPARQL/JSON-LD/dashboard) as authority.

These remain profile-owned proof paths in law-nexus.

## Anti-drift enforcement role (D098)

ACP/git-lex exist in law-nexus as **anti-drift enforcement**, not endless
infrastructure building. The project's core pain is drift (scope creep, lost
trajectory, AI evidence-boundary smoothing); ACP/git-lex enforce record
discipline to prevent it. They do NOT make product decisions.

**Enforcement mode: CHECKPOINT** (detect + log + flag), NOT gate/block. ACP
does not block product work; it catches drift after and logs it. Gate-mode ACP
re-creates the M035-M063 "never-install" paralysis — checkpoint avoids that.

**Meta-work budget: ACP FROZEN until parser data ready.** law-nexus is on a
product-only track until the M034 Consultant XML Parser Hardening roadmap is
executed and parser data is prepared. ACP expands ONLY if (a) drift is
detected+logged as an ACP HealthFinding, or (b) explicit user decision. M067
closed the ACP-inline era; expanding ACP now = repeating meta-drift.

**Record rule scope: architectural/requirement/state claims** (NOT every prose
statement). Targeted enforcement where drift happens; all-claims enforcement =
friction that prevents work.

**Concrete enforcement mechanisms:**

1. **Mandatory lifecycle tagging** in AI state claims: `[bounded]` /
   `[smoke]` / `[validated]` / `[proposed]` / `[deferled]`. Structural
   prevention of evidence-boundary smoothing (the pattern where bounded→validated).
2. **Architecture oracle**: `prd/ARCHITECTURE.md` is the living truth. Read it
   FIRST, not memory/history. Updated at every milestone closeout (mandatory).
3. **Drift log**: detected drift → ACP HealthFinding record, not silently fixed.
4. **Record rule on architectural/requirement/state claims**: source category +
   lifecycle + evidence anchor + proof gate, not prose-only.
5. **git-lex traceability**: parser output → ACP SourceRecords (profile binding
   exercises external kit + traceable proof).
6. **Meta-work budget enforced**: product track until parser data ready; ACP
   frozen unless drift logged.

## References

- `prd/architecture/acp/M049-S02-PROFILE-ADAPTER-BOUNDARY.md` — prior boundary
  work (pre-externalization).
- `/root/git-lex-kit-acp/docs/BOUNDARIES.md` — external reusable-core vs profile
  contract.
- `/root/git-lex-kit-acp/README.md` — external repo entry point.
- `.gsd/DECISIONS.md` D097 — restructuring programme decision.
