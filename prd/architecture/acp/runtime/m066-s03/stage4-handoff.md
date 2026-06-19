# M066 S03 Stage 4 Handoff (D084)

## Status

This is a **handoff artifact**, not a runtime proof. It is a tracked
governance/recovery surface (ACP rule 3): it records what M066 Stage 3 *proved*,
what D084 Stage 4 *must do*, and which boundaries *stay blocked* so that a
cold-start Stage-4 agent does not have to reconstruct the entry conditions from
scattered summaries and decisions.

ACP, git-lex, RDF, SHACL, SPARQL, generated JSONL, dashboards, and recovery
views are architecture governance/recovery surfaces — they are **not** source
truth and **not** requirement-validation proof (KNOWLEDGE rule 3). This document
does not itself validate any requirement; it points at the tracked proofs that
do, and names the gates Stage 4 still owes.

**Reader:** a cold-start engineer or Stage-4 executor landing on the D084
adoption roadmap without the M066 session context.

**Post-read action:** begin D084 Stage 4 (prove reusability with a second
project) *only* after confirming the R057 architecture-binding gate and the
preserved boundaries in Section 4, carrying forward every boundary verbatim.

## Stage 3 — proven

Stage 3 of D084 asked one question: **can git-lex adopt `.lex` operationally in
the main law-nexus checkout and track real law-nexus content?** The answer is
proven across three tracked slices, each with its own deterministic verifier and
durable proof artifact. A cold agent confirms Stage 3 is closed with a single
command, `uv run python scripts/verify-m066-s03-stage3-closure.py`, which
re-runs the M066 verifiers (with residue-transition awareness), scans for
forbidden overclaim, re-checks the live R047 residue *transition* guard, and
asserts the contract-critical boundary markers.

### S01 — adoption contract

`prd/architecture/acp/runtime/m066-s01/adoption-contract.md` fixes the Stage-3
operational adoption contract *before* the main-repo `git lex init` is executed,
separating the adoption *claim* from the adoption *proof*. It closes R047 Gate A
(isolated proof precondition met via M065 S03 disposable `/tmp` workflow; the
explicit adoption decision is recorded as **D093**). R057 is **explicitly
gated**: architecture binding is a separate future milestone, not this one. The
CLI-operational boundary and the pre-commit-hook consequence are documented.
Deterministic verifier: `scripts/verify-m066-s01-adoption-contract.py`.

### S02 — main-repo operational proof

`prd/architecture/acp/runtime/m066-s02/workflow-proof.json` proves `git lex init`
in the main law-nexus checkout creates `.lex/` AND lands its auto-commit in main
history — the **MEM549 inversion confirmed on the REAL repo** (not just the
disposable `/tmp` proof from M065 S03). `git lex sync` walks 335 law-nexus
commits and builds an oxigraph-backed knowledge graph (+1277 assertions). `git
lex query --json "SELECT ?c WHERE { ?c a git:Commit }"` returns all 335 commits
(real content). `git lex validate` exits 0 (base-kit no-op, MEM566, NOT
R035/R037/R038 validation). The pre-commit hook is installed at
`.git/hooks/pre-commit` and proven working on a content-commit without breaking
the commit workflow. Residue transitioned: `.lex` is now EXPECTED present;
`Squad` / `Raw` / `.artifacts` stay absent. Deterministic verifier:
`scripts/verify-m066-s02-main-repo-adoption.py` (with residue-transition logic:
`.lex` present = OK, missing = `lex_missing`; the others absent = OK, present =
`unexpected_residue`).

**What Stage 3 did NOT prove:** Stage 3 is operational adoption only. It did not
perform law-nexus architecture binding (R057 explicitly gated — ACP closure +
authoritative binding is a separate milestone), did not validate R035/R037/R038
(they stay active, non-source-truth), did not transfer ACP-kit to source truth
(base kit only), and did not prove reusability with a second project (that is
Stage 4).

## Stage 4 — scope and gates

Stage 4 of D084 is **proving reusability with a second project**. It is the next
gate after Stage 3 and is *not* done by M066 — this milestone closes at Stage 3.
Stage 4 must satisfy the R057 architecture-binding gate before any law-nexus
binding proceeds, and must carry every Section 4 boundary forward.

### Gate — R057 ACP closure (architecture binding)

Requirement R057 is **active** and is valid only when a tracked ACP closure
artifact records: final git-lex disposition, ACP-native implementation deltas,
adapter boundaries, and remaining blocked items — with downstream law-nexus
binding kept dependent on that closure. Stage 3 chose to **explicitly gate** on
R057 (not produce it): architecture binding is a separate future milestone. No
ACP closure artifact exists yet; R057 is the closure gate that Stage 4 (or a
dedicated closure milestone) owes. Stage 4 must either produce that closure
artifact or keep law-nexus binding explicitly gated on it.

### Stage 4 reusability proof

Stage 4 must prove git-lex can adopt `.lex` in a *second* project (not
law-nexus) — demonstrating the reusable-core / profile-adapter boundary (R048).
This validates that the operational adoption pattern proven in M066 generalizes
beyond law-nexus. The second project may be a disposable proof repository or a
real second project; the proof must show the same MEM549 inversion (installed
git-lex, pre-commit hook resolves via PATH, auto-commit lands) on the second
project.

## Preserved boundaries

These boundaries are carried forward from the S01 adoption contract verbatim.
Stage 4 may relax *only* the boundary its own gate explicitly addresses; every
other boundary stays.

- **R035 / R037 / R038 — active, non-source-truth.** These requirements are
  *active*, and Stage 3 did not validate them. They cannot be validated from
  ACP/git-lex/projection evidence alone (KNOWLEDGE rule 5). There is no
  R035/R037/R038 validation in Stage 3, and none is implied by this handoff.
- **R047 — operational adoption completed; runtime preservation proven.**
  Main-checkout `.lex` is now present (operational adoption). The residue guard
  transitions: `.lex` present is the new expected state; `Squad` / `Raw` /
  `.artifacts` remain absent. R047 stays *active* (its contract is satisfied
  operationally; full requirement tracking continues).
- **R053 — anti-feature (out-of-scope).** Preserved as an anti-feature. It must
  NOT be active and must NOT be validated.
- **R057 — explicitly gated (architecture binding).** ACP closure + law-nexus
  architecture binding is a separate future milestone. No closure artifact
  exists; Stage 4 must produce or keep gated.
- **R046 — source-truth / projection boundary.** ACP, git-lex, RDF, SHACL,
  SPARQL, and generated JSONL are not source truth; derived shapes must trace
  to the ontology.
- **R048 — reusable-core / profile boundary.** Keep law-nexus profile
  constraints in a profile/adapter layer; keep the core ontology universally
  reusable. Stage 4's second-project proof is the primary R048 exercise.

### CLI-operational wont-list (carried forward from Stage 3)

Stage 3 was operational adoption. These items were out of scope for Stage 3 and
remain blocked unless a named later stage explicitly owns them:

- **No R035/R037/R038 validation** — active, non-source-truth.
- **No ACP-kit source truth** — ACP-kit remains derived packaging, not source
  truth (base kit only in Stage 3).
- **No architecture binding** — R057 explicitly gated.
- **No `serve` / `viz` / `listen`** server exposure.
- **No `nuke` / `kit-update` / `save` / `create` / `join` / `raw`** mutating
  or destructive git-lex surfaces.
- **No authority-model enforcement** — deferred to D084 Stage 5 / D072.

## Residue-transition note (important for verifiers)

After Stage 3, `.lex` is EXPECTED present in the main checkout. The M065
verifiers (`verify-m065-s01/s02/s03`) and the M066 S01 verifier all assert
`.lex` *absent* (their R047 contract-phase posture). In the post-S02 state these
residue-absent checks regress. The Stage-3 closure verifier
(`scripts/verify-m066-s03-stage3-closure.py`) therefore invokes those prior
verifiers with `--skip-residue` and performs its OWN residue-transition check
(`.lex` present + `Squad`/`Raw`/`.artifacts` absent). This is not a regression;
it is the intended consequence of operational adoption. Stage 4's reusability
proof runs in a second project, so it does not perturb the law-nexus residue
state.

## Open revisit-triggers

These deferred triggers fired at Stage 3 landing and were honored in S03/T02.
They are recorded so a Stage-4+ agent knows what was re-confirmed.

- **D088 → fired (D094).** R055 bounded-advance, R043/R056 supported-mapping all
  re-confirmed status active UNCHANGED at Stage 3 landing; full anti-imitation
  enforcement deferred to D084 Stage 5 / D072.
- **D089 → fired (D095).** CLI-operational boundary re-confirmed: D089's
  CLI-install-only boundary was RESCOPED by D093 (no-main-`.lex` clause released
  for Stage 3; every other clause stays).
- **D091 → fired (D096).** Stage-3 revisit-triggers honored; git-lex source pin
  remains at `eaa4b24d144a78a8b8e4969404d74cf22267df1f` (update requires
  source/build/runtime recheck).
- **D072 / D084 Stage 5 — authority-model enforcement.** Full mandatory
  `hasLifecycleState` / `hasAuthorityClass` / `hasEvidenceAnchor` enforcement on
  authoritative records is deferred to Stage 5; R055's full anti-imitation
  enforcement depends on it.

## Verification

```bash
uv run python scripts/verify-m066-s03-stage3-closure.py
uv run python scripts/verify-m066-s03-stage4-handoff.py
```

The closure verifier is deterministic and inspection-only. It re-runs the M066
S01/S02 verifiers and the M065 S01/S02/S03 verifiers *with `--skip-residue`*
(their residue-absent checks regress post-S02 by design), performs its own
residue-transition check, scans the M066 proof set for overclaim, and asserts
the boundary markers. The handoff verifier asserts the required sections,
boundary markers, proof anchors, the MEM549-inversion marker, and zero overclaim
in this handoff document. Neither runs `git lex`.

## Decisions referenced

- **D084** — adoption-oriented roadmap; Stage 3 = single-repo operational `.lex`
  adoption (proven by M066); Stage 4 = prove reusability with a second project
  (next gate); Stage 5 = authority-model enforcement.
- **D093** — Stage 3 operational adoption contract (R047 Gate A closing +
  R057 explicitly-gated boundary).
- **D094 / D095 / D096** — D088/D089/D091 when_context fired at M066 S03.
- **D089** — Stage 2 install contract (rescoped by D093 for Stage 3).
- **D077** — git-lex source pin at commit
  `eaa4b24d144a78a8b8e4969404d74cf22267df1f`.

## References

- `prd/architecture/acp/runtime/m066-s01/adoption-contract.md` — Stage 3 adoption
  contract (R047 Gate A + R057 explicitly-gated + CLI-operational boundary).
- `prd/architecture/acp/runtime/m066-s02/workflow-proof.json` — Stage 3 main-repo
  operational proof (MEM549 inversion on REAL repo, 335 commits queryable,
  pre-commit hook proven).
- `prd/architecture/acp/runtime/m065-s04/stage3-handoff.md` — Stage 3 entry
  handoff (the gates S01/S02/S03 satisfied).
