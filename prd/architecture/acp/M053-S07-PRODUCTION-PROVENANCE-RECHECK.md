# M053 S07 Production Provenance Recheck

## Status

In progress for `M053-2jp3nm / S07`.

S07 rechecks production provenance and binary trust after the S06 adapter boundary. It does **not** approve production adoption, release-binary adoption, bundled plugin-binary adoption, or main repository `.lex` use.

## Guardrails

- Do not create or mutate `/root/law-nexus/.lex`.
- Do not use production/bundled binaries as ACP adapter proof without source/build/release binding.
- Do not infer provenance from local debug runtime smoke, README install prose, or plugin-bundled binaries alone.
- Keep ACP source truth ACP-native; git-lex output remains adapter-later diagnostic evidence at most.
- Treat `.gsd/exec` outputs as GSD verification evidence, not durable product proof anchors.

## T01: Source release and workflow provenance delta

### Evidence inputs

| Input | Role in S07 |
|---|---|
| `prd/architecture/acp/M052-S06-PRODUCTION-READINESS-PROVENANCE.md` | Baseline production provenance review. |
| `prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md` | Prior plugin binary and supply-chain inventory. |
| `prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md` | Prior source-built debug runtime gate and build workaround evidence. |
| `prd/architecture/acp/M053-S06-MINIMAL-ACP-ADAPTER-BOUNDARY.md` | Current adapter boundary: production/main `.lex` remain blocked. |
| `.gsd/exec/843fb57a-fa36-4ae5-9968-315565c0c0b3.stdout` | Fresh S07 read-only provenance snapshot. |

### Fresh read-only snapshot

The S07 snapshot used local git metadata, `git ls-remote`, local file hashes, local binary hashes, and read-only GitHub releases API calls. It did not fetch, checkout, push, publish, or mutate remote state.

#### `git-lex` source identity

```text
local_path: /root/vendor-source/git-lex
remote: https://github.com/repolex-ai/git-lex
local_branch: main
local_HEAD: eaa4b24d144a78a8b8e4969404d74cf22267df1f
remote_HEAD_observed_by_ls_remote: aa10ab71c781565eb86078037b2dbb84f9886f9c
local_tag_count: 0
remote_tags: none returned by git ls-remote --tags origin
GitHub releases API: ok, count 0
```

Delta from M052:

- M052 already recorded no observed `git-lex` tags/releases.
- S07 still observes zero `git-lex` tags and zero GitHub releases.
- S07 newly records that remote `HEAD` differs from the local vendor `HEAD` used by the previous runtime proofs.

Interpretation:

```text
current local vendor checkout: still usable as pinned source-smoke evidence only
current upstream release evidence: absent
current upstream freshness for adoption: blocked until explicit update/recheck or pin decision
```

Remote `HEAD` drift does not improve adoption readiness. It makes production adoption less safe unless a later task fetches/reviews the new upstream commit and reruns the relevant source/runtime gates.

#### `subtext-mcp` plugin identity

```text
local_path: /root/vendor-source/subtext-mcp
remote: https://github.com/repolex-ai/subtext-mcp
local_branch: main
local_HEAD: bac5529bb1fdc0ee5c0d9d081a0208f2fefca005
remote_HEAD_observed_by_ls_remote: 53dc112e312b33d185b438b69072026d75968738
local_tag_count: 1
remote_tags: v0.1.3
GitHub releases API: ok, count 0
```

Delta from M052/M051:

- The plugin repository has a remote tag `v0.1.3`, but the GitHub releases API still returns zero releases.
- Local plugin `HEAD` differs from remote `HEAD` by read-only observation.
- The tag alone does not prove binary provenance because S07 did not observe a release artifact, binary manifest, signature, SBOM, or attestation bound to that tag.

Interpretation:

```text
subtext-mcp tag evidence: version marker only
release artifact proof: absent
bundled binary provenance: still research-only / blocked for production adoption
```

### Fresh file hashes

```text
2746659bd6a0441f2873fb59b4cc69434a0ac28b0d1ee76b9c15a5022d67a7a6  /root/vendor-source/git-lex/Cargo.toml
3fbb6976b85c003fa50f6918f0aaa844665fd2d721dc2a6d7d5526fbbce793d7  /root/vendor-source/git-lex/Cargo.lock
dbd1ccc7550c59a945cfc0f9daa3c17576a4243cfee9755bff4a755de03dabbc  /root/vendor-source/git-lex/.github/workflows/build.yml
e409d9e2cbd4c31663413d623ce1331c776fa62dbb0689a0bb4a9efeb06a8a0f  /root/vendor-source/git-lex/.github/workflows/sync-binaries-to-plugin.yml
7af9159787744955b92d5fab15fd7685cc8a37b2f73c4ebb8cce8dbc63ed1213  /root/vendor-source/subtext-mcp/.claude-plugin/plugin.json
3a96346d772adb949f546df4331999302ef1bbcdfdaa6ba17f633fb62bcc64e2  /root/vendor-source/subtext-mcp/lib/host-binaries.ts
```

These hashes prove local reviewed-file identity only. They do not prove that a production binary was built from these exact files.

### Fresh binary inventory snapshot

Local source-built debug binaries:

| Binary | Exists | Size bytes | sha256 | Classification |
|---|---:|---:|---|---|
| `/root/vendor-source/git-lex/target/debug/git-lex` | yes | 431543616 | `40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c` | source-built debug smoke only |
| `/root/vendor-source/git-lex/target/debug/git-lex-serve` | yes | 349467952 | `3c141d9de3c77379fc531a2047c46aaf4f3e7d92cf211b8218b4623e75ed8d20` | source-built debug smoke only |

Plugin-bundled platform binaries remain present and hashable:

| Platform binary | Size bytes | sha256 |
|---|---:|---|
| `bin/.platforms/aarch64-apple-darwin/git-lex` | 24961936 | `ba00bc508c42675a48393ea07b2d91f7a7f4ca17931fdfe117360b2c117253aa` |
| `bin/.platforms/aarch64-apple-darwin/git-lex-serve` | 17612816 | `6e4fa543306609d6e417b6543bcd52ec5556fad11e423d88bc965543865f37ff` |
| `bin/.platforms/x86_64-apple-darwin/git-lex` | 26909516 | `143069a5083e6410db0d75f06997a27d6055dec24e00ee87208099870737d612` |
| `bin/.platforms/x86_64-apple-darwin/git-lex-serve` | 19222688 | `38b512adb907ae22e0da7f9da5370c02d432713f54df289391d1db81f7101e57` |
| `bin/.platforms/x86_64-unknown-linux-gnu/git-lex` | 31082360 | `24817f908ca4f30ef13424783fc790dd6502b294fb6e5843d91ce99941b9d9c5` |
| `bin/.platforms/x86_64-unknown-linux-gnu/git-lex-serve` | 22416432 | `97c8c7f2a207de7af1bbaec10506d8b42b2be4b17c1122f72722a82fd018b53e` |

Hashability is inventory evidence, not provenance proof.

### Workflow provenance delta

The reviewed workflows are still the same local workflow surfaces recorded by M052:

| Workflow | Local hash | Source-backed finding | Remaining gap |
|---|---|---|---|
| `build.yml` | `dbd1ccc7550c59a945cfc0f9daa3c17576a4243cfee9755bff4a755de03dabbc` | CI intent to build release binaries with `cargo build --release --locked` and attach tarballs on `v*` tags. | No observed `git-lex` tags/releases/artifact/run binding. |
| `sync-binaries-to-plugin.yml` | `e409d9e2cbd4c31663413d623ce1331c776fa62dbb0689a0bb4a9efeb06a8a0f` | CI path to copy build artifacts into `subtext-mcp` plugin platform bins. | Direct main push via PAT, short-SHA-only message, no manifest/signature/SBOM/attestation. |
| `host-binaries.ts` | `3a96346d772adb949f546df4331999302ef1bbcdfdaa6ba17f633fb62bcc64e2` | Plugin runtime maps host platform and symlinks platform binaries. GitNexus query surfaced `setupHostBinaries` as the relevant runtime path. | Activation behavior does not prove binary integrity. |

### T01 delta ledger

| Question | M052 baseline | S07 recheck | Updated conclusion |
|---|---|---|---|
| Does `git-lex` have observed tags/releases? | No tags/releases observed. | Still no remote tags; GitHub releases count 0. | Release adoption remains blocked. |
| Is local `git-lex` source current with remote? | M052 used local pinned source. | Remote HEAD differs from local HEAD. | Local source is pinned smoke evidence, not current upstream adoption proof. |
| Does `subtext-mcp` have release artifacts? | Plugin binaries present locally; no provenance manifest. | Remote tag `v0.1.3`, GitHub releases count 0. | Tag is not enough; bundled binary adoption remains blocked. |
| Are workflow hashes and paths known? | Yes. | Same local hashes recorded. | Workflow intent remains source-backed, not artifact proof. |
| Are bundled binary hashes known? | Yes from M051. | Same inventory re-recorded. | Research-only inventory; not production provenance. |
| Are signature/SBOM/SLSA/attestation artifacts observed? | Not found. | Not observed in T01 snapshot. | Production provenance remains blocked. |

### T01 conclusion

```text
S07/T01 disposition: provenance-blocks-confirmed
release adoption: blocked
bundled plugin binary adoption: blocked
source-built debug use: still smoke/proof-only
remote freshness: local vendor checkout is behind observed remote HEAD, so adoption would require explicit update/recheck or pin decision
workflow proof: source-backed intent only, not artifact provenance
```

S07/T01 does not weaken the S06 adapter boundary. It strengthens it: a future adapter spike may at most use a controlled source-built binary in isolation, unless S07/T02/T03 or a later milestone supplies concrete release artifact provenance.

## T02: Production trust gate matrix

### Evidence anchor

```text
.gsd/exec/b23a77e3-80cd-430c-90cd-f5a0b89e4bce.stdout
```

T02 scanned the local build workflow, plugin sync workflow, `Cargo.toml`, README, plugin metadata, and host-binary activation source for these signals:

```text
attest, attestation, sbom, slsa, cosign, signature, sign, checksum, sha256,
provenance, manifest, release, --version, version, workflow_run,
upload-artifact, action-gh-release, SUBTEXT_MCP_PAT, git commit, git push
```

Observed high-level result:

```text
release/version/workflow terms: present
checksum/signature/SBOM/SLSA/cosign/attestation/provenance manifest lines: not observed in scan
```

### Gate matrix

| Gate | Status | Evidence | S07 classification |
|---|---|---|---|
| Source repository reachable | pass | `git ls-remote origin HEAD` for `repolex-ai/git-lex` returned `aa10ab71...`; local source is `eaa4b24...`. | Source exists, but local checkout is stale/pinned relative to observed remote HEAD. |
| Source commit pinned for local proofs | pass | M051/M052/M053 runtime proofs use local `eaa4b24...`; S07 re-recorded hashes. | Acceptable for source-smoke only. |
| Local lockfile present | pass | `Cargo.lock` hash `3fbb6976...`. | Build input, not provenance proof. |
| Local debug binary identity | pass for smoke | Debug binary hashes re-recorded. | Runtime proof-only; not release or production. |
| Warning-clean build | not proven | Prior M052 build completed with warnings. | Production hardening gap. |
| `--version` machine identity | absent | M051/M052 showed `--version` unsupported. | Production identity gap. |
| CI release build workflow | pass as source intent | `build.yml` hashes and uses `cargo build --release --locked`. | Workflow intent only. |
| Concrete successful workflow run binding | blocked | No run id/artifact digest recorded in S07. | Required before release adoption. |
| `git-lex` tags | blocked | `git ls-remote --tags origin` returned empty. | No tag-backed release candidate. |
| `git-lex` GitHub release artifacts | blocked | GitHub releases API returned count `0`. | Release adoption blocked. |
| Release checksums | absent | No checksum manifest observed. | Required before binary adoption. |
| Release signatures | absent | No signature/cosign signal observed. | Required before binary adoption. |
| SBOM | absent | No SBOM signal observed. | Required before production adoption. |
| SLSA/GitHub artifact attestation | absent | No attestation/SLSA signal observed. | Required before production adoption. |
| Reproducible build proof | absent | No byte-for-byte reproduction or deterministic build process recorded. | Required before high-trust adoption. |
| Plugin binary sync workflow | pass as source intent, risky as production | `sync-binaries-to-plugin.yml` downloads artifacts and pushes to `subtext-mcp` main using `SUBTEXT_MCP_PAT`. | Supply-chain risk; not a LegalGraph production gate. |
| Plugin tag | narrow pass | `subtext-mcp` remote tag `v0.1.3` exists. | Version marker only, not binary provenance. |
| Plugin GitHub release | blocked | GitHub releases API returned count `0`. | No release artifact proof. |
| Plugin bundled binary hashes | pass as inventory | Six platform binary hashes re-recorded. | Research-only inventory. |
| Plugin bundled binary source binding | absent | No manifest binds hashes to full source commit/run/workflow/lockfile. | Production/bundled binary adoption blocked. |
| Plugin activation behavior | pass as source behavior | GitNexus surfaced `setupHostBinaries`; `host-binaries.ts` maps target triples and symlinks binaries. | Activation behavior only, not integrity proof. |
| License readiness for plugin redistribution | blocked | M051 S09 found missing explicit subtext-mcp license. | Legal/compliance gate remains. |
| Rollback policy | absent | No adoption rollback plan for main `.lex`, plugin binaries, or local daemons. | Required before production/main adoption. |
| Security controls | absent/insufficient | No signing/SBOM/attestation; plugin can run Bun, symlink binaries, spawn services. | Explicit user consent and isolation needed. |

### Layered classification

| Layer | Max safe use after S07/T02 | Blocked use |
|---|---|---|
| Local source checkout | Source review and isolated smoke if explicitly pinned. | Current-upstream or production claim without recheck. |
| Local debug binaries | Controlled isolated proof harness. | Release, production, or deployed ACP backend. |
| CI workflows | Explain intended build/sync routes. | Prove any artifact was built safely. |
| `git-lex` releases | None observed. | Any release-binary adoption. |
| `subtext-mcp` bundled binaries | Inventory/help research only. | ACP adapter binary source of truth. |
| `subtext-mcp` plugin | Prior-art and host-binary activation source. | Unattended ACP/LegalGraph runtime integration. |

### Plugin binary boundary

The plugin binary path is operationally real but provenance-insufficient:

```text
build workflow -> plugin-bin-* artifacts -> sync-binaries-to-plugin.yml -> subtext-mcp/bin/.platforms/<target>/ -> setupHostBinaries symlink into bin/
```

This path is **not** acceptable for ACP production adoption because it lacks:

```text
full source commit to binary hash manifest
workflow run id
workflow file hash binding
Cargo.lock hash binding
target triple and builder image manifest
checksum manifest
signature or cosign verification
SBOM
SLSA/GitHub artifact attestation
release artifact URL and immutable tag binding
rollback and revocation plan
explicit plugin license grant
```

### Source-built proof-only boundary

A later tiny adapter spike may use a source-built binary only if it records:

```text
source commit
remote HEAD observation or explicit pin decision
Cargo.lock hash
Cargo.toml hash
build command
host toolchain identity
binary path, size, mode, sha256
help output
workspace isolation checks
cleanup result
```

Even then, this supports only isolated proof harness work, not production adoption.

### T02 conclusion

```text
S07/T02 disposition: trust-gates-blocked
release-binary adoption: blocked
plugin-bundled binary adoption: blocked
production ACP adapter adoption: blocked
maximum safe route: source-built isolated proof-only binary with explicit pin/update decision
```

The trust matrix confirms S06's production denial. It does not prevent S08 from recommending a tiny isolated source-built adapter spike, but it prevents S08 from recommending release/bundled-binary adoption.

## T03: Final provenance disposition for S08

### Final disposition

```text
S07 final disposition: production-provenance-blocked
release-binary adoption: blocked
plugin-bundled binary adoption: blocked
production ACP adapter adoption: blocked
main .lex adoption: blocked
source-built isolated adapter spike: possible only as proof-only follow-up, after explicit S08 decision
```

### Decision impact for S08

| S08 option | S07 impact |
|---|---|
| Stop git-lex runtime advancement | Fully supported; no production provenance is available. |
| Preserve patterns only | Fully supported; provenance gaps do not block ACP-native pattern reuse. |
| Tiny isolated adapter spike | Conditionally allowed, but only source-built proof-only with explicit pin/update decision. |
| Release binary adoption | Blocked. No `git-lex` tags/releases/artifacts observed. |
| Plugin-bundled binary adoption | Blocked. Hash inventory exists but source/build/release binding is absent. |
| Production/main `.lex` adoption | Blocked. Requires provenance, rollback, security, and explicit human adoption decision. |

### Required evidence before any future release or bundled-binary adoption

A later milestone must provide all of the following before using release or plugin binaries in ACP:

1. immutable source tag or full source commit;
2. release artifact URL and artifact digest;
3. workflow run id and workflow file hash;
4. builder image/OS/toolchain identity;
5. Cargo.lock hash;
6. binary hash manifest for every target triple;
7. signature or cosign verification;
8. SBOM;
9. SLSA or GitHub artifact attestation;
10. reproducible build or independent rebuild comparison, if required for the trust level;
11. machine-readable `--version` or embedded build identity;
12. plugin/license redistribution decision;
13. rollback/revocation plan;
14. explicit human approval before any main-repo `.lex` or production use.

### Required evidence before any future source-built isolated spike

A source-built proof-only spike is less demanding, but still must record:

1. whether the spike pins local `eaa4b24...` or updates to observed remote `aa10ab71...`;
2. source commit and remote observation;
3. `Cargo.lock` and `Cargo.toml` hashes;
4. build command and host toolchain identity;
5. binary path, mode, size, and sha256;
6. command help output;
7. isolated workspace path;
8. no main `.lex`, `Squad`, or `Raw` before/after;
9. no real session/provider/legal raw payloads;
10. cleanup/residue report;
11. explicit statement that output is non-authoritative diagnostics only.

### Safe wording

Safe:

> M053/S07 confirms that git-lex production provenance remains blocked. A future adapter spike, if S08 approves it, should use only a source-built proof-only binary in an isolated workspace.

Safe:

> Existing plugin-bundled binary hashes are inventory evidence only; they are not ACP production provenance because no source/build/release manifest, signature, SBOM, or attestation was observed.

Safe:

> The observed `git-lex` remote HEAD differs from the local pinned runtime-proof source, so future implementation must choose either an explicit pin or an update-and-recheck path.

Unsafe:

> subtext plugin binaries are trusted ACP runtime binaries.

Unsafe:

> local debug binary smoke proves production readiness.

Unsafe:

> S07 approves main `.lex`, release adoption, or production deployment.

### S07 conclusion

```text
S07 classification: production-provenance-blocked
new upgrade: none
confirmed: source-built debug binaries remain proof-only; workflows remain source intent; bundled plugin binaries remain inventory-only
new caution: local git-lex source is behind observed remote HEAD, so implementation requires pin/update decision
S08 allowed choices: stop, preserve patterns, or tiny isolated source-built spike
S08 disallowed choices from current evidence: release-binary adoption, bundled plugin-binary adoption, production/main .lex adoption
```
