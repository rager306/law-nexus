# M065 S04 Stage 3 Handoff (D084)

## Status

This is a **handoff artifact**, not a runtime proof. It is a tracked
governance/recovery surface (ACP rule 3): it records what M065 Stage 2 *proved*,
what D084 Stage 3 *must do*, and which boundaries *stay blocked* so that a
cold-start Stage-3 agent does not have to reconstruct the entry conditions from
scattered summaries and decisions.

ACP, git-lex, RDF, SHACL, SPARQL, generated JSONL, dashboards, and recovery
views are architecture governance/recovery surfaces — they are **not** source
truth and **not** requirement-validation proof (KNOWLEDGE rule 3). This document
does not itself validate any requirement; it points at the tracked proofs that
do, and names the gates Stage 3 still owes.

**Reader:** a cold-start engineer or Stage-3 executor landing on the D084
adoption roadmap without the M065 session context.

**Post-read action:** begin D084 Stage 3 (single-repo `.lex` adoption in the
main law-nexus checkout) *only* after confirming the R047 and R057 gates below,
carrying forward every preserved boundary in Section 4 verbatim.

## Stage 2 — proven

Stage 2 of D084 asked one question: **is git-lex a real environment command?**
The answer is proven across three tracked slices, each with its own
deterministic verifier and durable proof artifact. A cold agent confirms Stage 2
is closed with a single command,
`uv run python scripts/verify-m065-s04-stage2-closure.py`, which re-runs the
three prior verifiers, scans for forbidden overclaim, re-checks the live R047
residue guard, and asserts the contract-critical boundary markers.

### S01 — install contract

`prd/architecture/acp/runtime/m065-s01/install-contract.md` fixes the install
contract *before* the install is executed, separating the install *claim* from
the install *proof*. Canonical command
`cargo install --path . --locked` (`--locked` mandatory — the rudof-family
sibling-crate API coupling makes `Cargo.lock` the compatibility source of
truth; a locked-build failure is a BLOCKER, no unlocked/patch/debug fallback).
Source provenance at commit `eaa4b24d144a78a8b8e4969404d74cf22267df1f`
reuses the M051/S09-S10, M052/S06, and M054/S01 (D077) trust anchors.

### S02 — cold-PATH install proof

`prd/architecture/acp/runtime/m065-s02/install-proof.json` proves
`git-lex` and `git-lex-serve` resolve through an explicit cold `PATH`
(`~/.cargo/bin` on PATH, vendor-dir excluded) from `/tmp`. The git `lex`
subcommand dispatches to the installed `git-lex` binary (banner present,
rc=2 missing-subcommand, contrasted with a non-existent subcommand's rc=1).
The `--version` gap is re-proven (exits 2, so no version number is ever
claimed). Main-checkout residue guard clean before and after.

### S03 — workflow proof

`prd/architecture/acp/runtime/m065-s03/workflow-proof.json` proves the
release-installed `git lex` runs a full `init` / `sync` / `validate` /
`query` / `list` lifecycle in a separate disposable `/tmp` repository under
cold PATH. **MEM549 inversion:** with git-lex installed on cold PATH, the
pre-commit hook resolves `git-lex` via PATH lookup and runs extract+validate,
so `git lex init`'s auto-commit lands (`auto_commit_landed=true`,
`init_commit_count=1`) — inverting the M064 root cause where the hook could
not find git-lex and HEAD stayed empty. Main-checkout residue guard clean
before and after; the only durable out-of-checkout side effect is the global
`~/.lex/repos` machine registry, which is expected git-lex behavior and is not
R047 residue.

**What Stage 2 did NOT prove:** Stage 2 is CLI-install-only. It did not adopt
`.lex` in the main law-nexus checkout, did not touch R035/R037/R038 (they stay
active, non-source-truth), did not transfer ACP-kit to source truth, and did
not claim production readiness.

## Stage 3 — scope and gates

Stage 3 of D084 is the **single-repo `.lex` adoption in the main law-nexus
checkout**. It is the next gate after Stage 2 and is *not* done by M065 — this
milestone closes at Stage 2. Stage 3 must satisfy two gates before it begins,
and must carry every Section 4 boundary forward.

### Gate A — R047 full validation (main-repo `.lex` adoption)

Requirement R047 blocks main-checkout `.lex` initialization until (1) an
isolated proof succeeds and (2) an explicit adoption decision is recorded.
Stage 2 honored R047 as a **contract-phase** check: the isolated proof now
exists (S03 disposable `/tmp` workflow), but the explicit Stage-3 adoption
decision has not been recorded. Therefore R047's full validation is deferred
to Stage 3: the main-checkout `.lex` adoption is *permitted* only after the
Stage-3 adoption decision is explicitly made. Stage 2 did not, and could not,
close this gate — it only cleared the isolated-proof precondition.

### Gate B — R057 ACP closure

Requirement R057 is **pending** and is valid only when a tracked ACP closure
artifact records: final git-lex disposition, ACP-native implementation deltas,
adapter boundaries, and remaining blocked items — with downstream law-nexus
binding kept dependent on that closure. Stage 3 must produce (or explicitly
gate on) that closure artifact before any law-nexus binding proceeds. No
ACP closure artifact exists yet; R057 is the closure gate that Stage 3 owes.

## Preserved boundaries

These boundaries are carried forward from the S01 install contract verbatim.
Stage 3 may relax *only* the boundary its own gate explicitly addresses
(R047 main-repo adoption, after the adoption decision); every other boundary
stays.

- **R035 / R037 / R038 — active, non-source-truth.** These requirements are
  *active*, and Stage 2 did not validate them. They cannot be validated from
  ACP/git-lex/projection evidence alone (KNOWLEDGE rule 5). There is no
  R035/R037/R038 validation in Stage 2, and none is implied by this handoff.
- **R047 — contract-phase honored, full validation deferred to Stage 3.**
  No main `.lex` init was performed. Main-repo adoption is Stage 3 and requires
  the explicit adoption decision.
- **R053 — anti-feature (out-of-scope).** Preserved as an anti-feature.
- **R046 — source-truth / projection boundary.** ACP, git-lex, RDF, SHACL,
  SPARQL, and generated JSONL are not source truth; derived shapes must trace
  to the ontology.
- **R048 — reusable-core / profile boundary.** Keep law-nexus profile
  constraints in a profile/adapter layer; keep the core ontology universally
  reusable.

### CLI-install-only wont-list (carried forward from Stage 2)

Stage 2 was CLI-install-only. These items were out of scope for Stage 2 and
remain blocked unless a named later stage explicitly owns them:

- **No main `.lex` initialization** in the main law-nexus checkout (R047).
- **No R035/R037/R038 validation** — active, non-source-truth.
- **No ACP-kit source truth** — ACP-kit remains derived packaging, not source
  truth.
- **No single-repo / Stage-3 `.lex` adoption** in *this* milestone — that is
  D084 Stage 3, the next gate.
- **No `serve` / `viz` / `listen`** server exposure.
- **No `nuke` / `kit-update` / `save` / `create` / `join` / `raw`** mutating
  or destructive git-lex surfaces.

## Open revisit-triggers

These deferred triggers remain open after M065 and fire on the named future
events. They are recorded so a Stage-3+ agent knows what may need re-recording
into the requirement DB via `gsd_requirement_update` (which is phase-blocked
during execute-task; the slice-closeout lane owns the DB write).

- **D084 Stage 3 — single-repo `.lex` adoption.** The primary next gate. On
  landing, re-record R055 / R043 / R056 Validation/Notes (D088) and re-confirm
  the CLI-install-only boundary re-scope (D089).
- **D088 / D089 — remaining triggers.** R055 is a bounded advance (one
  authority field, `sourceArtifact sh:minCount`, proven as a true negative at
  M064/S04); R043 / R056 are supported-mappings; all three stay status `active`
  (UNCHANGED). The full requirement-DB Validation/Notes sync is still owed when
  the triggers fire. Remaining triggers: git-lex source pin updated away from
  `eaa4b24d144a78a8b8e4969404d74cf22267df1f`; static kit republished at v0.2.0
  carrying `sh:datatype` (the M064 adaptive overlay).
- **D072 / D084 Stage 5 — authority-model enforcement.** Full mandatory
  `hasLifecycleState` / `hasAuthorityClass` / `hasEvidenceAnchor` enforcement on
  authoritative records is deferred to Stage 5; R055's full anti-imitation
  enforcement depends on it.
- **R055 — full anti-imitation enforcement.** Only one authority field is
  proven today; full enforcement is deferred to D084 Stage 5 / D072.

## Verification

```bash
uv run python scripts/verify-m065-s04-stage3-handoff.py
```

This verifier is deterministic and inspection-only (stdlib only, no
subprocess): it asserts every required section header above is present, the
contract-critical boundary markers are present, the three proof-anchor paths
are referenced, the MEM549-inversion marker (`auto_commit_landed`) is present,
and there is zero affirmative overclaim. It does not run `git lex`, does not
initialize `.lex`, and does not mutate state. The companion Stage-2 closure
verifier (`scripts/verify-m065-s04-stage2-closure.py`) is the gate a cold agent
runs to confirm Stage 2 is *closed*.

## Decisions referenced

- **D084** — adoption-oriented roadmap; Stage 2 = install as a real environment
  command (proven by M065); Stage 3 = single-repo `.lex` adoption (next gate);
  Stage 5 = authority-model enforcement. KEEP correctness boundaries; DROP
  paralysis rules.
- **D089** — Stage 2 install contract + CLI-install-only boundary.
- **D088** — R055 bounded-advance + R043/R056 supported-mapping classification
  (all status active, UNCHANGED); triggers the deferred requirement-DB sync.
- **D077** — git-lex source pin at commit `eaa4b24d144a78a8b8e4969404d74cf22267df1f`.
