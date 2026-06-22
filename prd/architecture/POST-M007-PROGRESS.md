# Post-M007 Architecture Progress

> **Companion to:** `prd/architecture/closure_roadmap.md` (the derived, frozen
> M007/R04 closure snapshot).
> **Source of truth:** `prd/ARCHITECTURE.md` (living oracle) and
> `.gsd/milestones/*`. This note is a derived cold-reader pointer.
> Refreshed 2026-06-22 (post-M069).

## Why this note exists

`prd/architecture/closure_roadmap.md` is **generated** by
`scripts/generate-architecture-closure-roadmap.py` from
`prd/architecture/remediation_matrix.json` + `prd/architecture/major_track_split.json`.
It is a **deliberately frozen M007/R04 snapshot**: it captures the R04
architecture-governance closure (18 recommendations, 6 future-proof tracks, 7
assigned gates) and is self-consistent (`generate-architecture-closure-roadmap.py
--check` passes). It is **not** regenerated to reflect post-M007 progress, by
design — its contract pins `review_id: R04`, `milestone_id: M007`, and exact
counts (18 / 6 / 7).

That means the closure roadmap is **correct but frozen in the M007 era**. It does
not know about the architecture refactoring that happened afterwards. This note
fills that gap without changing the generator's contract.

## What the closure roadmap's 6 "future proof tracks" map to now

The 6 tracks remain conceptually valid (they are real product proof gates), but
their status has moved since M007:

| M007 future track | Post-M007 reality |
|---|---|
| `TRACK-GENERATED-CYPHER-SAFETY` | Still `[bounded]` synthetic proof (M003). Unchanged; downstream of a real graph schema. |
| `TRACK-PARSER-RETRIEVAL-GOLDEN` | **This is the active next milestone direction** — Consultant XML Parser Hardening (M034 corrected roadmap) produces the parser-record stream this track needs. |
| `TRACK-TEMPORAL-SEMANTICS` | `[proposed]` (prd/02_architecture.md §3); unchanged, needs product decision after parser data. |
| `TRACK-LEGAL-NEXUS-ACCESS-CONTROL` | `[proposed]` (§5); unchanged. |
| `TRACK-RETRIEVAL-EMBEDDING-EXPERIMENT` | `[bounded]`: USER-bge-m3 local embedding baseline established at 1024 dims (S10); runtime-compat only, not Russian-legal retrieval quality. |
| `TRACK-RUNTIME-MIGRATION-SMOKE` | `[bounded]` synthetic smoke; unchanged. |

## Structural foundation built since M007 (not in the closure snapshot)

- **M067** — ACP/git-lex reusable core **externalized** to
  `/root/git-lex-kit-acp/` (published v0.2.0); law-nexus became a profile consumer
  (D097). The M035-M067 ACP-inline era is **closed**.
- **D098** — anti-drift enforcement: ACP frozen to checkpoint mode
  (detect+log+flag, non-blocking) until parser data is ready; mandatory lifecycle
  tagging on architectural/state claims. The M035-M067 era is acknowledged as
  meta-drift.
- **M068** — repo turned into the `src/law_nexus` **onion package** (ADR-0001);
  MADR **ADR standard** + **compliance gate** (ADR-0002: import-linter layer
  contracts + `verify-adr-conformance` lifecycle/ADR checker, wired as hard-fail
  pre-commit hooks). D098 lifecycle retag of 13 `prd/02_architecture.md` layers.
- **M069** — **library boundary** contract recorded (ADR-0003: Pydantic = domain
  forms + parser boundary records + JSON Schema; stdlib `@dataclass` = verifier
  records; Adaptix = `[deferred]` boundary-record↔domain-form mapping). Standing
  `pre-commit run --all-files` rc=1 closed via a narrow Decision-section
  exempt-rule. Tree now fully gate-green.

## Where to read the current trajectory

`prd/project-state/roadmap.md` (refreshed post-M069) is the **current** roadmap.
The closure roadmap is the M007 governance-closure record; this note bridges it
to the present. When in doubt, `prd/ARCHITECTURE.md` is the living truth oracle.
