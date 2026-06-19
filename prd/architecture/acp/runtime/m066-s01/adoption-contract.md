# M066 S01 git-lex Operational Adoption Contract (Stage 3 of D084)

## Status

Accepted contract for `M066-k97nro / S01`. This is **Stage 3 of the D084
adoption roadmap**: adopt `.lex` operationally in the main law-nexus checkout.
This slice fixes the adoption contract and the operational-vs-binding boundary
**before** S02 executes the main-repo `git lex init`, so the adoption *claim*
is separated from the adoption *proof* (the same contract-first pattern proven
in M065 S01 install-contract).

This contract is the materialization of **decision D093**. It does not run
`git lex init` in the main checkout and does not mutate the main law-nexus
checkout (`.lex` stays absent on this slice; R047 contract-phase honored).

## Reader and post-read action

**Reader:** an engineer (or a later slice executor) who must carry out the
Stage 3 main-repo `git lex init` without overclaiming, without validating
requirements that remain source-truth-owed, and without crossing from
operational adoption into architecture binding.

**Post-read action:** execute the S02 main-repo `git lex init` strictly inside
this contract, then prove `init` / `sync` / `validate` / `query` operate on
REAL law-nexus content — and nothing beyond the CLI-operational boundary stated
in Section 4.

## Authority and scope guardrails

- This is an ACP architecture contract artifact, not a runtime proof. It records
  *what* S02 must do and *what it must not do*; the runtime proof arrives in S02.
- ACP, git-lex, RDF, SHACL, SPARQL, generated JSONL, dashboards, and recovery
  views are architecture governance/recovery surfaces, not source truth or
  requirement-validation proof (KNOWLEDGE rule 3).
- R047 blocks main-checkout `.lex` initialization until (1) an isolated proof
  succeeds AND (2) an explicit adoption decision is recorded. The isolated proof
  precondition is now MET (M065 S03 disposable `/tmp` workflow,
  `auto_commit_landed=true`); this contract records the explicit adoption
  decision (Section 1), closing **R047 Gate A**.
- Keep law-nexus profile constraints in a profile/adapter layer. R035/R037/R038
  must not be validated from ACP/git-lex/projection evidence alone (KNOWLEDGE
  rule 5).
- This contract is **CLI-operational** (Section 4). Architecture binding (ACP
  closure + law-nexus authoritative binding) is explicitly out of scope and
  gated on R057 (Section 2).

## 1. R047 Gate A closing — explicit adoption decision

Stage 3 of D084 asks one question: **should git-lex adopt `.lex` in the main
law-nexus checkout as an operational tracking layer?** The answer is decided
here, explicitly, per R047's two preconditions:

### Precondition (1) — isolated proof: MET

M065 S03 (`prd/architecture/acp/runtime/m065-s03/workflow-proof.json`) proved
that the release-installed `git lex` (cold PATH, `~/.cargo/bin`, no vendor-dir)
runs a full `init` / `sync` / `validate` / `query` / `list` lifecycle in a
disposable `/tmp` git repository. The MEM549 inversion was empirically
confirmed: with git-lex installed on cold PATH, the freshly-installed
pre-commit hook resolves `git-lex` via PATH lookup, runs extract+validate, and
`git lex init`'s auto-commit lands (`auto_commit_landed=true`,
`init_commit_count=1`). In M064 the source-debug binary was off-PATH, the hook
printed "git-lex not found" + exit 1, and HEAD stayed empty. The isolated proof
that an installed `git lex` can run a real workflow is therefore complete.

### Precondition (2) — explicit adoption decision: RECORDED HERE (D093)

The explicit Stage-3 adoption decision is: **adopt `.lex` operationally in the
main law-nexus checkout via `git lex init`, as an infrastructure tracking layer.
This is operational adoption, NOT architecture binding.** The main-checkout
`.lex` initialization is now PERMITTED (R047 Gate A closes). This decision was
confirmed by the user (collaborative) for the operational scope with
`isolation: none` (auto-commit lands in main history directly).

R047 therefore transitions on this slice from **contract-phase honored** (`.lex`
absent, the M065 posture) to **explicit adoption decision recorded** (this
contract). The main-checkout `.lex` creation itself is S02's responsibility;
S01 keeps `.lex` absent (Section 6) so the contract and the proof stay
separated.

## 2. Operational-vs-architecture-binding boundary (R057 explicitly gated)

Stage 3 is **operational adoption only**. This is the critical scope boundary
that separates Stage 3 from architecture binding:

### Stage 3 IS (operational adoption)

- `git lex init` creates `.lex/` in the main law-nexus checkout.
- git-lex begins tracking law-nexus commit history into a knowledge graph.
- The git-lex pre-commit hook runs extract+validate on future content commits.
- `init` / `sync` / `validate` / `query` / `list` operate on REAL law-nexus
  content.

### Stage 3 IS NOT (architecture binding — explicitly gated on R057)

- NOT law-nexus architecture binding — R057 requires an ACP closure artifact
  recording the final git-lex disposition, ACP-native implementation deltas,
  adapter boundaries, and remaining blocked items, BEFORE any law-nexus
  architecture binding proceeds. No such closure artifact exists. R057 is
  therefore **explicitly gated**: ACP closure + architecture binding is a
  separate, later milestone.
- NOT ACP-kit source truth (ACP-kit remains a derived semantic-packaging track).
- NOT validation of R035/R037/R038 (they stay active, non-source-truth).
- NOT authority-model enforcement (deferred to D084 Stage 5 / D072).

The handoff in `prd/architecture/acp/runtime/m065-s04/stage3-handoff.md` Gate B
permits Stage 3 to either "produce" OR "explicitly gate on" the R057 closure
artifact. Stage 3 chooses **explicitly gate**: architecture binding is a future
milestone that must satisfy R057 on its own.

## 3. Pre-commit hook consequence

`git lex init` installs a git pre-commit hook into `.git/hooks/pre-commit`. This
is an **inherent, intended consequence** of operational adoption, documented and
accepted here:

- After S02's `git lex init`, **every future `git commit` in the law-nexus
  repository** will trigger the git-lex pre-commit hook, which runs
  extract+validate on the staged content.
- Under the base kit (`repolex-ai/git-lex-kit-base`) the kit ships
  `install folders:false` and no SHACL shapes (MEM566), so `validate` is a
  no-op shape check (exit 0 trivially) and the hook's extract step is the active
  behavior. This satisfies operational adoption and does NOT constitute
  R035/R037/R038 validation (boundary preserved).
- This changes the commit workflow for the whole project going forward. The user
  explicitly accepted this consequence (collaborative decision, `isolation:
  none`). It is part of the operational adoption model, not a side effect to
  suppress.

A future milestone that wants to remove or change the hook must do so
explicitly; S02 must not silently disable it.

## 4. CLI-operational boundary

This slice and Stage 3 are **CLI-operational**. The boundary is:

### Stage 3 WILL (S02)

- Run `git lex init` in the main law-nexus checkout (releases the R047
  contract-phase hold via the Section 1 adoption decision).
- Run `git lex sync` to build a knowledge graph from real law-nexus commit
  history.
- Run `git lex validate` and `git lex query --json` and `git lex list --json`
  to prove the lifecycle operates on real content.
- Use the base kit only (`repolex-ai/git-lex-kit-base`).
- Record durable repo-relative proof anchors and a deterministic verifier.

### Stage 3 WILL NOT

- **No R035/R037/R038 validation** — these requirements remain *active*, not
  source-truth; they cannot be validated from ACP/git-lex/projection evidence
  (KNOWLEDGE rule 5). The base kit has no SHACL shapes (MEM566), so validate is
  a no-op; Stage 3 does not claim validation of these requirements.
- **No ACP-kit source truth** — ACP-kit remains a derived semantic-packaging
  track, not source truth (KNOWLEDGE rule 3). Stage 3 uses base kit only.
- **No architecture binding** — R057 explicitly gated (Section 2); ACP closure
  and law-nexus authoritative binding are a separate future milestone.
- **No `serve` / `viz` / `listen`** server exposure — out of scope for Stage 3
  unattended automation.
- **No `nuke` / `kit-update` / `save` / `create` / `join` / `raw`** mutating or
  destructive git-lex surfaces — out of scope (consistent with M052/S06 and
  M054/S01 denylists).
- **No Stage 4 reusability** — proving reusability with a second project is
  D084 Stage 4, a separate later stage.

This boundary maps to the D084 stage map: Stage 1 (M058 root cause, M064)
closed; Stage 2 (M065) install closed; Stage 3 (this milestone) operational
adoption only; Stage 4 (reusability) + Stage 5 (authority model) remain gated.

## 5. S02 acceptance

Stage 3 acceptance is the S02 main-repo operational proof. S02 must prove, in
the main law-nexus checkout (NOT a disposable `/tmp` repo):

1. `git lex init` creates `.lex/` in the main checkout, and its auto-commit
   lands in main history (`auto_commit_landed=true`, the MEM549 inversion now
   on the REAL repo, not just the disposable proof).
2. `git lex sync` exits 0 and builds a knowledge graph from real law-nexus
   commit history.
3. `git lex query --json "SELECT ?c WHERE { ?c a git:Commit }"` exits 0 and
   returns law-nexus commit results with `count >= 1` (real content, not the
   disposable repo's small fixture).
4. `git lex validate` exits 0 (base kit, MEM566 no-op shape check).
5. The git-lex pre-commit hook is installed at `.git/hooks/pre-commit` and runs
   extract+validate on a test content commit (hook active on real repo).
6. A durable repo-relative proof artifact and a deterministic verifier are
   tracked.

**Residue transition note (Section 6):** `.lex` transitions from absent (the
M065 contract-phase posture) to EXPECTED presence (S02 operational adoption).
The residue guard is updated, not removed: `.lex` present becomes OK; `Squad`,
`Raw`, `.artifacts` remain absent (these would indicate out-of-contract
surfaces).

## 6. Residue transition (R047 contract-phase → operational)

The R047 residue guard changes semantics between S01 and S02:

| Path | M065 / S01 (this slice) | S02 (after init) |
|---|---|---|
| `.lex` | absent (R047 contract-phase honored) | EXPECTED present (operational adoption) |
| `Squad` | absent | absent (out-of-contract surface) |
| `Raw` | absent | absent (out-of-contract surface) |
| `.artifacts` | absent | absent (out-of-contract surface) |

This slice's verifier asserts the S01 column: `.lex` / `Squad` / `Raw` /
`.artifacts` all absent, so the contract is recorded before any mutation. S02's
verifier will assert the S02 column: `.lex` present + the three others absent.
The transition is deliberate and tracked, not an accidental drift.

## Failure Modes

This contract is a documentation artifact with no runtime of its own, but it
fixes the failure policy that S02 must obey.

| Dependency | Failure path | Contract policy |
|---|---|---|
| `git lex init` in main checkout | Init fails, auto-commit does not land, or pre-commit hook not installed | **BLOCKER.** STOP and reassess. Do not force the commit, do not bypass the hook. The MEM549 inversion must hold on the real repo. |
| `git lex sync` / `query` on real history | Sync fails, query returns 0 commits (store not built / not queryable) | **BLOCKER.** git-lex must track real law-nexus content; failure is an explicit adoption blocker, not a silent skip. |
| Pre-commit hook breaks existing commit workflow | Hook errors on legitimate content commits, blocking normal development | **BLOCKER.** Document and surface explicitly; do not silently disable the hook. Reassess whether operational adoption is viable before proceeding. |
| Main checkout residue (`Squad` / `Raw` / `.artifacts`) | Out-of-contract surfaces appear | Contract failure. `.lex` is expected; the others are not. |
| Overclaim (affirmative R035/R037/R038 validation) | A proof artifact or script claims the requirements are validated | Contract failure. R035/R037/R038 stay active, non-source-truth. |

All failures are explicitly bubbled as adoption blockers rather than silently
accepted, consistent with M065 S01 and M051/S09 §T04.

## Load Profile

This slice has no runtime load dimension (it performs no `git lex init` and no
runtime; init/runtime load diagnostics arrive in S02). This section is omitted.

## Negative Tests

The deterministic verifier
(`scripts/verify-m066-s01-adoption-contract.py`) is the negative-test surface
for this contract. It asserts the following negative conditions hold:

| Negative condition | How the verifier asserts it |
|---|---|
| Missing contract section | Assert all six section headers (Sections 1–6) are present in the contract. Missing → `missing_section`. |
| Missing boundary marker | Assert the CLI-operational + R057-gated + R047 markers are present. Missing → `missing_boundary_marker`. |
| D093 not recorded | Assert D093 is present in `.gsd/DECISIONS.md`. Missing → `decision_not_recorded`. |
| Prior M065 verifier regression | Re-run `verify-m065-s01-install-contract.py` and `verify-m065-s04-stage2-closure.py` as child processes and assert exit 0. Non-zero → `prior_verifier_failed`. |
| Main checkout residue (`R047` contract-phase) | Assert `.lex`, `Squad`, `Raw`, `.artifacts` are absent in the main checkout. Present → `main_state_residue`. |
| Overclaim (affirmative R035/R037/R038 validation) | Scan the contract for affirmative validation-verb adjacency to R035/R037/R038 with a negation-context guard. Hit → `overclaim_detected`. |
| Unsafe runtime side effect from verifier | The verifier runs NO `git lex`, initializes NO `.lex`, and mutates NO state (it only re-runs prior *Python* verifiers as child processes). Any other side effect would be a defect. |

The verifier exits non-zero on the first negative condition violated.

## Verification

```bash
uv run python scripts/verify-m066-s01-adoption-contract.py
```

The verifier is a deterministic inspection surface only. It checks that the
contract exists with all six sections, that the boundary markers are present,
that D093 is recorded, that the prior M065 verifiers still pass, and that the
main law-nexus checkout has no residue (R047 contract-phase on this slice). It
does not run `git lex`, does not initialize `.lex`, and does not mutate state.

## Decisions referenced

- **D084** — adoption-oriented roadmap; Stage 3 = single-repo `.lex` adoption
  (this milestone). KEEP correctness boundaries; DROP paralysis rules.
- **D093** — this contract (Stage 3 operational adoption contract + R047 Gate A
  closing + R057 explicitly-gated boundary).
- **D089** — Stage 2 install contract (precondition; its CLI-install-only
  boundary is RESCOPED here: the "no main `.lex`" clause is released by the
  Section 1 adoption decision, every other clause stays).
- **D090 / D091** — D088/D089 when_context fired at M065 S04; their Stage-3
  revisit-triggers fire when Stage 3 lands (S03 closeout owns the requirement-DB
  sync).

## References

- `prd/architecture/acp/runtime/m065-s04/stage3-handoff.md` — Stage 3 handoff
  (R047 Gate A + R057 Gate B + preserved boundaries + open revisit-triggers).
- `prd/architecture/acp/runtime/m065-s01/install-contract.md` — Stage 2 install
  contract (template for this contract-first pattern; its provenance is the
  install precondition Stage 3 consumes).
- `prd/architecture/acp/runtime/m065-s03/workflow-proof.json` — the isolated
  proof (MEM549 inversion) that closes R047 precondition (1).
- `.gsd/milestones/M066-k97nro/M066-k97nro-ROADMAP.md` — Stage 3 slice map.
