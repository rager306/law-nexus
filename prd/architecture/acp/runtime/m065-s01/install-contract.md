# M065 S01 git-lex Install Contract (Stage 2 of D084)

## Status

Accepted contract for `M065-pqvr1r / S01`. This is **Stage 2 of the D084
adoption roadmap**: install `git-lex` as a real environment command. This slice
fixes the install contract and the CLI-install-only boundary **before** S02
executes the install, so the install *claim* is separated from the install
*proof*.

This contract is the materialization of **decision D089**. It does not install
anything and does not mutate the main law-nexus checkout.

## Reader and post-read action

**Reader:** an engineer (or a later slice executor) who must carry out the Stage 2
install of `git-lex` without overclaiming, without touching the main repository,
and without validating requirements that remain source-truth-owed.

**Post-read action:** execute the S02 release build + `cargo install` strictly
inside this contract, then prove cold-PATH resolution in an isolated disposable
repository — and nothing beyond the CLI-install-only boundary stated in
Section 6.

## Authority and scope guardrails

- This is an ACP architecture contract artifact, not a runtime proof. It records
  *what* S02/S03 must do and *what they must not do*; the runtime proof arrives
  in S02/S03.
- ACP, git-lex, RDF, SHACL, SPARQL, generated JSONL, dashboards, and recovery
  views are architecture governance/recovery surfaces, not source truth or
  requirement-validation proof (KNOWLEDGE rule 3).
- Do not initialize or mutate git-lex state (`.lex`, `Squad`, `Raw`,
  `.artifacts`) in the main `/root/law-nexus` checkout until an isolated proof
  succeeds and an explicit adoption decision is recorded (KNOWLEDGE rule 4,
  requirement R047).
- Keep law-nexus profile constraints in a profile/adapter layer. R035/R037/R038
  must not be validated from ACP/git-lex/projection evidence alone (KNOWLEDGE
  rule 5).
- This contract is **CLI-install-only** (Section 6). Stage 3 `.lex` adoption in
  a real repository is explicitly out of scope and blocked.

## 1. Canonical install command

The canonical Stage 2 install command is:

```bash
cargo install --path . --locked
```

run from the pinned source checkout `/root/vendor-source/git-lex`.

**`--locked` is mandatory, not optional.** The `rudof` crate family
(`shacl_validation`, `shacl_ir`, `shacl_rdf`, `rudof_rdf`, `sparql_service`,
`prefixmap`, `iri_s`) has sibling-crate API coupling: one patch version of
`shacl_ast`/`shacl_validation` may not match a freshly-resolved `prefixmap` or
`iri_s`, and pinning individual crates only relocates the failure to a sibling.
`Cargo.lock` is the correct source of compatibility truth. Plain
`cargo install --path .` re-resolves transitive deps and may fail to compile on
`shacl_ast` / `rudof_rdf`. This rationale is recorded in:

- `/root/vendor-source/git-lex/README.md` §Install ("`--locked` is required"),
- `/root/vendor-source/git-lex/Cargo.toml` dependency comment
  ("rudof family — always install with `cargo install --path . --locked`").

**BLOCKER rule (milestone vision):** if `cargo install --path . --locked` does
not build, Stage 2 is a BLOCKER. STOP and reassess the approach before making
any install claim. Do not fall back to an unlocked install, do not patch the
lockfile, and do not silently downgrade to the debug binary as the installed
command. This honors the D084 "foundation, not shadow-forever" principle while
preserving the legitimate correctness boundary that the install must be a real,
reproducible release build.

## 2. Source provenance

The install reuses the already-trusted, already-built-once source at
`/root/vendor-source/git-lex` (read-only vendor checkout, the canonical
reference root). Provenance is recomputed from that checkout at contract time:

```yaml
# provenance (recomputed at contract time from /root/vendor-source/git-lex)
source_remote: https://github.com/repolex-ai/git-lex
source_commit: eaa4b24d144a78a8b8e4969404d74cf22267df1f
cargo_toml_sha256: 2746659bd6a0441f2873fb59b4cc69434a0ac28b0d1ee76b9c15a5022d67a7a6
cargo_lock_sha256: 3fbb6976b85c003fa50f6918f0aaa844665fd2d721dc2a6d7d5526fbbce793d7
```

These values were recomputed during S01 and confirmed identical to the prior
trust anchors:

- `prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md` (scope pins the
  vendor checkout at this commit and records the lockfile),
- `prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md`
  (`source_commit=eaa4b24d...`, `cargo_lock_sha256=3fbb6976...`),
- `prd/architecture/acp/M052-S06-PRODUCTION-READINESS-PROVENANCE.md`
  (records both `Cargo.toml` and `Cargo.lock` sha256),
- `prd/architecture/acp/M054-S01-PINNED-SOURCE-ADAPTER-CONTRACT.md` (D077 pin,
  manifest hashes).

The deterministic verifier
(`scripts/verify-m065-s01-install-contract.py`) re-reads the contract, recomputes
`git rev-parse HEAD`, `sha256sum Cargo.toml`, and `sha256sum Cargo.lock` from
`/root/vendor-source/git-lex`, and asserts byte-for-byte equality with the
values recorded above. A mismatch is a contract failure.

## 3. Provenance policy reuse

Stage 2 does **not** re-derive acquisition trust from scratch. It reuses the
proven source-build policy and binary identity already accepted by prior
milestones:

- **M051/S09 §T04 "Allowed acquisition modes"** — source build from `git-lex`
  is the *preferred path* for any adapter/runtime adoption candidate. Its
  required evidence is: pin a full immutable commit, preserve `Cargo.lock`,
  build with the locked build in a controlled builder, and record builder
  OS/image, Rust toolchain, command transcript, binary sha256, binary
  size/mode, and source commit in a manifest. Stage 2 satisfies the full-commit
  pin + `Cargo.lock` + lockfile-hash requirements; the builder/toolchain record
  and installed-binary identity are S02's responsibility (Section 5).
- **M051/S09 §T04 "Proof gates"** — the source-build gate is met at the commit
  pin above; the repository-state gate (no-main-repo `.lex`) is enforced here
  and in S02/S03; the LegalGraph validation gate (R035/R037/R038) remains
  explicitly out of scope.
- **M054/S01 §T01 binary identity** — D077 pins this exact commit; the manifest
  hashes above match the M054-S01 record. Stage 2 is the release-profile
  continuation of the debug-profile source build already proven there.
- **M052/S06 §T03 production readiness** — this contract does **not** promote
  git-lex to production-ready. M052/S06 production adoption remains blocked.
  Stage 2 is strictly "install as a real environment command," which is below
  the M052/S06 production threshold and below D084 Stage 3 single-repo `.lex`
  adoption.

Note (MEM501): the S09 policy requires source-built pinned binaries with
provenance manifests. Stage 2 honors this by building from the pinned source
with `--locked`; S02 records the installed release-binary identity as the
manifest continuation.

## 4. Install targets

`cargo install --path . --locked` installs **both** binaries declared by
`Cargo.toml` (`[[bin]] name = "git-lex"` and `[[bin]] name = "git-lex-serve"`)
into the canonical Cargo bin directory:

```text
~/.cargo/bin/git-lex
~/.cargo/bin/git-lex-serve
```

Per `README.md` §Install: "This installs both `git-lex` and `git-lex-serve` to
`~/.cargo/bin/`."

`git-lex` is the git subcommand driver (`git lex ...`). `git-lex-serve` is the
server binary (`viz`, `listen`); it is installed for completeness and identity
continuity, but its server surfaces (`serve`, `viz`, `listen`) are **not** part
of the Stage 2 acceptance surface (Section 5) and remain out of scope for any
unattended automation.

## 5. S02 and S03 acceptance

Stage 2 acceptance is split across S02 (release build + install) and S03
(isolated install-rehearsal workflow).

### S02 — release build and cargo install to PATH

S02 must prove, all from a directory outside the vendor checkout (e.g. `/tmp`):

1. `cargo install --path . --locked` run from `/root/vendor-source/git-lex`
   completes and installs both `git-lex` and `git-lex-serve` into
   `~/.cargo/bin/` (release profile, not debug-only).
2. With `~/.cargo/bin` on a cold `PATH` (no vendor-dir on `PATH`),
   `git lex --help` exits 0 from outside the vendor directory.
3. `git-lex-serve --help` exits 0.
4. The `git lex` subcommand resolves through cold `PATH` (i.e. `git` finds the
   installed `git-lex` binary via PATH lookup and dispatches the `lex`
   subcommand), proven from `/tmp` outside the vendor-dir.
5. Main law-nexus checkout residue guard: `.lex`, `Squad`, `Raw`, `.artifacts`
   remain absent before and after (R047 contract-phase check).

**`--version` gap (do NOT claim a version number).** M051/S09 empirically
proved that `--version` is **not implemented**: both `git-lex --version` and
`git-lex-serve --version` exit `2` with `error: unexpected argument '--version'
found`. Therefore S02 must **not** claim or assert a version number. S02 proves
only launch + cold-PATH subcommand resolution (`--help` exit 0), never
`--version`. This is a hard contract constraint on S02.

### S03 — isolated install-rehearsal workflow proof

S03 must prove, in a **separate disposable repository** (never the main
law-nexus checkout):

1. The installed-from-cold-PATH `git lex` binary executes a full
   `init` / `sync` / `validate` / `query` workflow in an isolated throwaway git
   repository.
2. Main law-nexus checkout residue guard: `.lex`, `Squad`, `Raw`, `.artifacts`
   remain absent before and after the S03 run (R047 honored).

S03 runtime observability (structured per-operation diagnostics, before/after
residue checks, workspace cleanup) arrives in S03; this slice has no runtime
observability because it performs no install and no runtime.

## 6. CLI-install-only boundary

This slice and Stage 2 are **CLI-install-only**. The boundary is:

### Stage 2 WILL

- Release-build `git-lex` and `git-lex-serve` from the pinned source with
  `cargo install --path . --locked` into `~/.cargo/bin/`.
- Prove cold-PATH `--help` resolution and the S03 isolated workflow from a
  disposable repository.
- Keep the main law-nexus checkout residue-clean (R047, `.lex`/`Squad`/`Raw`/
  `.artifacts` absent).

### Stage 2 WILL NOT

- **No `.lex` initialization in the main law-nexus checkout** — requirement
  R047 preserved; KNOWLEDGE rule 4. Main-repo `.lex` adoption is Stage 3 and
  requires an isolated proof plus an explicit adoption decision (D084 Stage 3).
- **No R035/R037/R038 validation** — these requirements remain *active*, not
  source-truth; they cannot be validated from ACP/git-lex/projection evidence
  (KNOWLEDGE rule 5). Stage 2 does not touch them.
- **No ACP-kit source truth** — ACP-kit remains a derived semantic-packaging
  track, not source truth (KNOWLEDGE rule 3). Stage 2 is CLI install only.
- **No single-repo production adoption** — M052/S06 production readiness
  remains blocked; D084 Stage 3 single-repo `.lex` adoption is a separate,
  later stage.
- **No Stage 3 `.lex` adoption** — `.lex` adoption in a real repository is
  Stage 3, explicitly out of scope here.
- **No `nuke` / `kit-update` / `save` / `create` / `join` / `raw backfill`** —
  destructive/mutating/network git-lex surfaces are out of scope for any Stage 2
  unattended automation (consistent with M052/S06 and M054/S01 denylists).
- **No `serve` / `viz` / `listen` production exposure** — server surfaces are
  out of scope for Stage 2 unattended automation.

This boundary maps to the D084 stage map: Stage 1 (M058 root cause, M064) is
closed; Stage 2 (this milestone) is install-only; Stage 3+ remain blocked and
gated on their own proofs.

## Failure Modes

This contract is a documentation artifact with no runtime of its own, but it
fixes the failure policy that S02/S03 must obey. External dependencies and
their failure paths:

| Dependency | Failure path | Contract policy |
|---|---|---|
| `cargo install --path . --locked` build | Compilation failure (rudof sibling-crate API mismatch if `--locked` omitted, or `oxrocksdb-sys`/RocksDB native build failure) | **BLOCKER.** STOP and reassess. Do not fall back to unlocked install, do not patch the lockfile, do not silently use the debug binary as the installed command (Section 1). |
| Native build toolchain (`clang`, `cmake`, RocksDB C++20, `bindgen`/`stdbool.h`) | Missing `clang`/`cmake` blocks `oxrocksdb-sys` bindgen with `fatal error: 'stdbool.h' file not found` | M051/S10 T03 proved the remediation (`apt-get install -y clang cmake`). S02 must verify the toolchain before building; the failure is an explicitly-bubbled adoption blocker, never silently accepted. |
| `~/.cargo/bin/` write target | Permission denied, disk full, PATH not populated | S02 must record the install result; failure is an explicit blocker, not a silent skip. |
| Cold-PATH `git lex` resolution | `git-lex` not on PATH after install, `git` subcommand dispatch fails | S02 proves cold-PATH resolution explicitly (Section 5); failure is an explicit blocker. |
| Main checkout residue (`.lex`/`Squad`/`Raw`/`.artifacts`) | Accidental mutation of `/root/law-nexus` | Enforced as R047 contract-phase check in the verifier and as S02/S03 before/after guards. Any residue is a contract failure. |

All failures are explicitly bubbled as adoption blockers rather than silently
accepted, consistent with M051/S09 §T04 and M052/S06 §T03.

## Load Profile

This slice has no runtime load dimension (it performs no install and no runtime;
install/runtime load diagnostics arrive in S02/S03). This section is omitted.

## Negative Tests

The deterministic verifier
(`scripts/verify-m065-s01-install-contract.py`) is the negative-test surface for
this contract. It asserts the following negative conditions hold:

| Negative condition | How the verifier asserts it |
|---|---|
| Recorded provenance drift (contract hashes vs actual vendor source) | Recompute `git rev-parse HEAD`, `sha256sum Cargo.toml`, `sha256sum Cargo.lock` from `/root/vendor-source/git-lex` and assert byte-for-byte equality with the contract's recorded values (Section 2). Any mismatch → `provenance_mismatch`. |
| Missing contract section | Assert all six section headers (Sections 1–6) are present in the contract. Missing → `missing_section`. |
| Missing boundary marker | Assert canonical-command and CLI-install-only boundary markers are present. Missing → `missing_boundary_marker`. |
| Main checkout residue (`R047` contract-phase) | Assert `.lex`, `Squad`, `Raw`, `.artifacts` are absent in `/root/law-nexus`. Present → `main_state_residue`. |
| Unsafe runtime side effect from verifier | The verifier does **not** run `git lex`, does **not** initialize `.lex`, does **not** clone, and does **not** build. Any such behavior in the verifier itself would be a defect. |

The verifier exits non-zero on the first negative condition violated. This
covers the contract's negative surface; runtime negatives (cold-PATH failure,
`--version` overclaim, residue during install) are S02/S03's responsibility.

## Verification

```bash
uv run python scripts/verify-m065-s01-install-contract.py
```

The verifier is a deterministic inspection surface only. It checks that the
contract exists with all six sections, that the recorded provenance hashes
match the actual recomputation from `/root/vendor-source/git-lex`, that the
boundary markers are present, and that the main law-nexus checkout has no
residue (R047 contract-phase). It does not install, does not run `git lex`,
and does not mutate state.

## Decisions referenced

- **D084** — adoption-oriented roadmap; Stage 2 = install as a real environment
  command. KEEP correctness boundaries (records authoritative only with
  category+lifecycle+evidence+proof-gate; R035/R037/R038 require real
  source/runtime evidence), DROP paralysis rules.
- **D089** — this contract (Stage 2 install contract + CLI-install-only
  boundary).
- **D077** — git-lex source pin at commit
  `eaa4b24d144a78a8b8e4969404d74cf22267df1f` (M054 adapter spike pin; reused
  here as the Stage 2 source-build pin).

## References

- `prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md` — §T04 acquisition
  policy, proof gates, blocked uses.
- `prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md` — source-build
  remediation (clang/cmake), binary identity, isolated runtime smoke.
- `prd/architecture/acp/M052-S06-PRODUCTION-READINESS-PROVENANCE.md` — build/release
  provenance, production readiness gate (remains blocked).
- `prd/architecture/acp/M054-S01-PINNED-SOURCE-ADAPTER-CONTRACT.md` — D077 pin,
  manifest hashes, adapter denylist.
- `.gsd/milestones/M065-pqvr1r/M065-pqvr1r-ROADMAP.md` — Stage 2 slice map.
