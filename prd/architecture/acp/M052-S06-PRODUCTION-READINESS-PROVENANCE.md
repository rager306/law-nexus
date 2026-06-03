# M052 S06 Production Readiness and Provenance

## Status

In progress for `M052-idogd6 / S06`.

S06 turns M052 runtime findings into production-readiness gates for any future ACP git-lex adapter. It does **not** approve production adoption by default.

## Guardrails

- Do not create or mutate `/root/law-nexus/.lex`.
- Do not infer production provenance from local debug binaries, release README text, or bundled plugin binaries alone.
- Separate source-build proof, workflow proof, release proof, prebuilt-binary proof, and missing attestations.
- Keep ACP authority ACP-native; git-lex remains adapter-later unless later gates pass.

## T01: Build and release provenance paths

### Source paths reviewed

| Surface | Source anchor | Finding |
|---|---|---|
| `Cargo.toml` | `/root/vendor-source/git-lex/Cargo.toml` | Package `git-lex` version `0.0.1`, edition `2024`, license `Unlicense`, repository `https://github.com/repolex-ai/git-lex`; declares two binaries: `git-lex` and `git-lex-serve`. Dependencies include native/build-sensitive surfaces: `oxigraph` with `rdf-12`, `git2` with vendored OpenSSL, `shacl_*`, `rudof_*`, `axum`, `tokio`, `reqwest`, `open`. Comment says rudof family requires `--locked`. |
| `Cargo.lock` | `/root/vendor-source/git-lex/Cargo.lock` | Present; hash recorded below. It is required compatibility evidence, not by itself proof of reproducible binaries. |
| README install docs | `/root/vendor-source/git-lex/README.md` | Documents release-binary install and source install with `cargo install --path . --locked`; explicitly says `--locked` is required because rudof sibling crates are lockfile-coupled. |
| Build workflow | `/root/vendor-source/git-lex/.github/workflows/build.yml` | Builds release binaries for three targets with `cargo build --release --locked --target <target>`, uploads tarball and plugin-bin artifacts, and attaches tarball on `v*` tag builds. Linux arm64 is omitted due C++20 / `oxrocksdb-sys` toolchain issue. |
| Plugin sync workflow | `/root/vendor-source/git-lex/.github/workflows/sync-binaries-to-plugin.yml` | After successful `build`, downloads `plugin-bin-*` artifacts, writes binaries into `repolex-ai/subtext-mcp/bin/.platforms/<target>/`, commits and pushes directly to `subtext-mcp` main using `SUBTEXT_MCP_PAT`. Commit message records short git-lex SHA only. |
| Plugin binary activation | `/root/vendor-source/subtext-mcp/lib/host-binaries.ts` | On plugin startup, maps host platform to Rust target triple and symlinks `bin/.platforms/<target>/*` into top-level `bin/*`. Missing platform logs warning and does not crash. |
| Plugin metadata | `/root/vendor-source/subtext-mcp/.claude-plugin/plugin.json` | Plugin `subtext` version `0.1.3`; metadata does not include binary provenance fields. |
| M051 S09 prior review | `prd/architecture/acp/M051-S09-SUPPLY-CHAIN-BINARY-TRUST.md` | Already recorded bundled binary hashes and trust gaps; S06 reuses it as prior evidence, not fresh production proof. |

### Local source and workflow identity

Local `git-lex` vendor checkout:

```text
path: /root/vendor-source/git-lex
remote: https://github.com/repolex-ai/git-lex
HEAD: eaa4b24d144a78a8b8e4969404d74cf22267df1f
local tag count: 0
remote tag sample: empty from `git ls-remote --tags origin`
```

Local workflow and manifest hashes:

```text
dbd1ccc7550c59a945cfc0f9daa3c17576a4243cfee9755bff4a755de03dabbc  .github/workflows/build.yml
e409d9e2cbd4c31663413d623ce1331c776fa62dbb0689a0bb4a9efeb06a8a0f  .github/workflows/sync-binaries-to-plugin.yml
3fbb6976b85c003fa50f6918f0aaa844665fd2d721dc2a6d7d5526fbbce793d7  Cargo.lock
2746659bd6a0441f2873fb59b4cc69434a0ac28b0d1ee76b9c15a5022d67a7a6  Cargo.toml
```

Local `subtext-mcp` vendor checkout:

```text
path: /root/vendor-source/subtext-mcp
remote: https://github.com/repolex-ai/subtext-mcp
HEAD: bac5529bb1fdc0ee5c0d9d081a0208f2fefca005
plugin version: 0.1.3
bundled targets:
  bin/.platforms/aarch64-apple-darwin/{git-lex,git-lex-serve}
  bin/.platforms/x86_64-apple-darwin/{git-lex,git-lex-serve}
  bin/.platforms/x86_64-unknown-linux-gnu/{git-lex,git-lex-serve}
```

### Build workflow proof vs release proof

What `build.yml` proves from source review:

- There is a CI intent to build release-mode binaries with `cargo build --release --locked`.
- The matrix targets macOS arm64, macOS x64, and Linux x64.
- Build artifacts include tarballs and plugin-bin layouts.
- On tag refs matching `v*`, tarballs are attached to a GitHub release via `softprops/action-gh-release@v2`.

What it does **not** prove here:

- That a release currently exists.
- That a specific local binary came from a specific workflow run.
- That artifacts were signed, attested, checksummed, or SBOM-backed.
- That the workflow ran for the local source commit.
- That build outputs are reproducible across hosts.

Observed release/tag status in this local review:

```text
local tags: 0
remote tags: none returned by git ls-remote --tags origin
```

Therefore S06/T01 treats release adoption as blocked unless a later task supplies a concrete release artifact, full source commit, workflow run id, artifact digest, and signature/attestation evidence.

### Cross-repository plugin binary propagation

`sync-binaries-to-plugin.yml` is a real binary propagation path:

1. It is triggered by successful `build` workflow completion on `main` or manual dispatch.
2. It downloads `plugin-bin-*` artifacts from the selected build run.
3. It writes binaries to `subtext-mcp/bin/.platforms/<target>/`.
4. It commits to `subtext-mcp` main with message:

```text
binaries: sync git-lex @ <short-sha>
```

This is useful operational evidence but not a LegalGraph production provenance gate because:

- It uses a cross-repository PAT (`SUBTEXT_MCP_PAT`) with write access.
- It pushes directly to `subtext-mcp` main.
- It records only a short source SHA in the commit message.
- No checked-in manifest binds each binary hash to full source commit, workflow run id, workflow file hash, target triple, builder image, Rust toolchain, Cargo.lock hash, or signer.
- No SLSA/cosign/GitHub artifact attestation/SBOM evidence was found in the reviewed workflow.

### Prebuilt plugin binary boundary

M051/S09 already recorded hashes for bundled `subtext-mcp` binaries and proved Linux `--help` behavior only. S06/T01 preserves that boundary:

```text
subtext-mcp bundled binaries: research-only / local help inventory
production provenance: blocked without manifest + attestation + source/build binding
```

`host-binaries.ts` proves runtime activation behavior: symlink platform binaries into top-level `bin/` on plugin startup. It does not prove binary integrity.

### Provenance classification

| Evidence type | Status after T01 | What it supports | What remains missing |
|---|---|---|---|
| Source checkout | present | Source review and source-built debug smoke candidate | Release provenance; production binary identity. |
| Lockfile | present, hash recorded | Dependency compatibility input for `--locked` builds | Reproducibility or supply-chain attestation. |
| CI build workflow | source-backed | Intended release build process and target matrix | Run id, successful run evidence for candidate artifact, signed artifact. |
| Release workflow | source-backed conditional on `v*` tags | Potential release attachment path | No observed tags/releases in local evidence. |
| Plugin binary sync | source-backed | Cross-repo propagation path to `subtext-mcp` | Full manifest, binary hash binding, attestation, license resolution. |
| Local debug binaries | present from M051/S10 | Runtime smoke only | Release build identity and reproducibility. |
| Bundled plugin binaries | present from M051/S09 | Research-only binary inventory/help checks | ACP adapter/runtime adoption proof. |
| Version command | absent | Nothing; `--version` is unsupported per M051/S09 | Machine-readable source/build identity. |
| Attestations/SBOM/signatures | not found | No production proof | Required before release adoption. |

### T01 conclusion

T01 distinguishes four layers:

```text
source-build proof: possible and previously smoke-tested locally, but debug-only unless T02 records fresh identity
workflow proof: source-backed CI scripts exist for release builds and plugin sync
release proof: blocked; no local/remote tags or concrete release artifact proven here
production provenance proof: blocked; no checked-in manifest, signature, SBOM, SLSA/cosign/GitHub attestation, or full binary-to-source binding found
```

Release or bundled-binary adoption must remain blocked. Future ACP adapter work may use a controlled source build only after T02/T03 gates record exact build identity, reproducibility limits, rollback, and security controls.

## T02: Local build identity and reproducibility boundary

### Evidence anchor

```text
.gsd/exec/541a46b9-a676-4c2b-981f-6b1f76862dd4.stdout
```

### Build command and source identity

T02 ran from:

```text
/root/vendor-source/git-lex
```

Command:

```bash
cargo build --locked --bins --message-format=short
```

Result:

```text
build_exit=0
Finished `dev` profile [unoptimized + debuginfo] target(s) in 0.73s
```

Source and manifest identity:

```text
source_commit=eaa4b24d144a78a8b8e4969404d74cf22267df1f
cargo_lock_sha256=3fbb6976b85c003fa50f6918f0aaa844665fd2d721dc2a6d7d5526fbbce793d7
cargo_toml_sha256=2746659bd6a0441f2873fb59b4cc69434a0ac28b0d1ee76b9c15a5022d67a7a6
```

Host toolchain identity:

```text
rustc 1.94.1 (e408947bf 2026-03-25)
rust host: x86_64-unknown-linux-gnu
LLVM version: 21.1.8
cargo 1.94.1 (29ea6fb6a 2026-03-24)
Ubuntu clang version 18.1.3 (1ubuntu1)
cmake version 3.28.3
```

### Local debug binary identity

T02 verifies the existing local debug binaries after the locked build:

| Binary | Mode | Size bytes | sha256 | Help surface |
|---|---:|---:|---|---|
| `target/debug/git-lex` | `0755` | `431543616` | `40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c` | `Git extensions for knowledge graphs`; usage `git-lex <COMMAND>`. |
| `target/debug/git-lex-serve` | `0755` | `349467952` | `3c141d9de3c77379fc531a2047c46aaf4f3e7d92cf211b8218b4623e75ed8d20` | `Servers for git-lex knowledge graphs`; usage `git-lex-serve <COMMAND>`. |

These hashes match the M051/S10 source-built debug binary identity recorded earlier.

### Build warnings

The locked build completed but emitted warnings, including:

- deprecated `oxigraph::store::Store::query` / `oxigraph::sparql::Query` usage;
- one unreachable pattern;
- multiple unused functions/structs;
- `git-lex` generated 23 warnings;
- `git-lex-serve` generated 4 warnings.

These warnings do not block local smoke, but they remain production-readiness evidence: the candidate is not warning-clean.

### Reproducibility boundary

T02 proves only this:

```text
On this host, this source checkout and lockfile can build dev-profile `git-lex` and `git-lex-serve` binaries whose current hashes are recorded.
```

T02 does **not** prove:

- release-mode reproducibility;
- deterministic byte-for-byte rebuilds after `cargo clean`;
- clean-room build reproducibility;
- equivalence to GitHub Actions release artifacts;
- equivalence to `subtext-mcp` bundled binaries;
- signer identity;
- SBOM/SLSA/cosign/GitHub attestation;
- production suitability.

### T02 conclusion

```text
local debug build identity: pass / runtime-smoke only
release build identity: blocked / not produced in T02
reproducibility: not proven
production provenance: blocked
main repository safety: `/root/law-nexus/.lex` absent
```

## T03: Production readiness gate

### Evidence consumed

T03 consumes S01-S05 report markers from:

```text
prd/architecture/acp/M052-S01-SHACL-NEGATIVE-VALIDATION.md
prd/architecture/acp/M052-S02-JSON-LD-RUNTIME-CAPABILITY.md
prd/architecture/acp/M052-S03-SPARQL-STAR-RUNTIME-PROOF.md
prd/architecture/acp/M052-S04-SERVE-VIZ-LISTEN-RUNTIME-PROOF.md
prd/architecture/acp/M052-S05-REMAINING-CLI-COMMAND-MATRIX.md
```

Verification anchor:

```text
.gsd/exec/f81448de-8bc6-4ba8-a739-9f269cfd6dad.stdout
```

### Production readiness checklist

Legend:

- `pass-smoke`: isolated runtime smoke exists but is insufficient for production.
- `blocked`: production adoption must not proceed until fixed/proven.
- `required-gate`: actionable gate required for any future adapter.
- `not-applicable`: not required for minimal ACP adapter.

| Gate | Status | Evidence | Required before production/adoption |
|---|---|---|---|
| Main repo `.lex` isolation | `pass-smoke` | S01-S05 and S06 checks kept `/root/law-nexus/.lex` absent. | Enforce automated pre/post guard in adapter tests and runtime wrapper. |
| Source acquisition pin | `pass-smoke` | Full local commit `eaa4b24d144a78a8b8e4969404d74cf22267df1f`; lock hash recorded. | Pin source by full commit in adapter manifest; disallow branch/short SHA. |
| Release artifact provenance | `blocked` | No local/remote tags; no concrete release artifact proven. | Record release URL/artifact digest/full source commit/workflow run/signature. |
| Binary attestation | `blocked` | No manifest, SBOM, SLSA/cosign/GitHub attestation found. | Provide machine-verifiable binary-to-source manifest and signature/attestation. |
| Reproducible build | `blocked` | T02 dev build passed but no clean-room/release deterministic rebuild. | Controlled release build, clean builder image, repeated hash comparison or accepted reproducibility boundary. |
| Version/runtime identity | `blocked` | M051/S09 found `--version` unsupported. | Add `--version` or manifest command exposing source commit, target, lock hash, build profile. |
| Dependency/native toolchain review | `required-gate` | Lockfile present; build sensitive to clang/cmake/RocksDB/C++20. | Capture builder image/toolchain/native dependency versions; review Rust/native/Bun lockfiles. |
| SHACL negative validation | `pass-smoke` with wrapper required | S01 proved valid-frontmatter negative fixtures fail; source has fail-open/skipped paths. | Adapter wrapper must hard-fail missing shapes, skipped files, setup/parser/processor diagnostics, and assert validated file counts. |
| JSON-LD runtime | `blocked` | S02 found `.jsonld` metadata only; no RDF import/export. | Do not claim JSON-LD runtime unless a future route is implemented and proven. |
| SPARQL-star runtime | `pass-smoke` narrow | S03 proved `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK over history graph. | Limit query contract to history graph pattern; do not claim full RDF-star parity. |
| Browser/viz UI | `pass-smoke` partial | S04 proved local UI/API; `/api/store-info` 404 remains. | Fix/accept route gap, add browser diagnostics gate, lifecycle cleanup, and auth/exposure policy. |
| Listen server | `blocked` for standard init, `pass-smoke` for short-kit workaround | S04 found fully-qualified kit-string mismatch; short `kit: squad` SSE works. | Fix kit detection or document adapter repo.yml policy; add endpoint lifecycle tests. |
| Local server exposure | `required-gate` | S04 source binds to `127.0.0.1`. | Keep localhost-only by policy; define port conflict cleanup, process ownership, and no-detached-leak checks. |
| CLI minimal adapter subset | `required-gate` | S05 identifies `init/sync/query/list/validate-wrapper` as candidates. | Implement only minimal subset first; exclude workflow/destructive commands from unattended automation. |
| `create/save` workflow | `blocked` for unattended ACP | S05 showed `create` can produce SHACL-invalid doc; `save` can fail after staging sidecars. | Design authoring workflow with fill/validate/cleanup semantics before any use. |
| `kit-update` | `blocked` for unattended ACP | S05 showed network/scaffold/shape mutation. | Use only in explicit maintenance flow with review, diff, rollback, and pinned kit source. |
| `nuke` | `blocked` / unsafe | S05 proved destructive removal and source attempts `git push`. | Never run automatically; require explicit human confirmation and remote policy. |
| `join` | `not-applicable` for ACP core | S05 proves cross-repo mutation. | Exclude unless a future multi-repo membership workflow is explicitly designed. |
| `raw backfill` | `blocked` for proof anchors | S05 proved raw payload copy and machine-state sensitivity. | Keep raw payloads out of durable ACP proof anchors unless sanitized and explicitly approved. |
| State rollback | `blocked` | Commands mutate `.lex`, `.git/lex`, `Raw/`, `.claude`, repo commits, and sometimes two repos. | Define rollback for each allowed command: filesystem, git index, commits, server processes, machine state. |
| Observability/failure modes | `required-gate` | M052 recorded several fail-open/partial/gap states. | Add structured wrapper logs: command, cwd, git status before/after, exit code, stderr, artifact paths, cleanup result. |
| Security controls | `blocked` | No auth/TLS/CSRF/rate limits for local server; destructive/network commands exist. | Threat model local server, browser opener, network fetches, PAT workflow, raw payload handling, and destructive commands. |
| LegalGraph requirements R035/R037/R038 | `blocked` | M052 remains git-lex capability proof only. | Validate via ACP-native registry/runtime/legal evidence, not git-lex projection/runtime alone. |

### Minimal future adapter gate set

Before any future ACP adapter spike can be considered production-adjacent, it must enforce:

1. **Isolation gate**: no main `.lex`; all fixture/adoption state explicit.
2. **Acquisition gate**: full source commit, lock hash, build manifest, binary hash, and provenance/attestation status.
3. **Command allowlist gate**: only `init`, `sync`, `query`, `list --json`, and `validate` wrapper allowed by default.
4. **Validation wrapper gate**: hard-fail skipped docs/setup errors and assert expected shapes/file counts.
5. **State cleanup gate**: before/after git status, `.lex`, `.git/lex`, server processes, and machine-state paths recorded.
6. **Server gate**: localhost-only, browser diagnostics, endpoint coverage, port cleanup, no detached leaks.
7. **Destructive command denylist gate**: `nuke`, `kit-update`, `join`, `raw backfill`, `create`, and `save` disabled unless a separate human-approved workflow is active.
8. **Authority gate**: git-lex output remains derived diagnostics; ACP source/proof lifecycle remains authoritative.

### T03 conclusion

```text
production readiness: blocked
adapter-later path: possible only as isolated/minimal allowlisted spike
required next proof: manifest-backed source/release build + wrapper gates + rollback/security tests
```

## T04: Production adoption status

### Final production classification

M052/S06 does **not** upgrade git-lex to production-ready or adopted for ACP.

Final status:

```text
production adoption: blocked
runtime adoption: adapter-later
release/bundled binary adoption: blocked
minimal future adapter spike: allowed only as isolated, allowlisted, non-authoritative proof
main repository `.lex` adoption: not approved
```

### What improved during M052

M052 materially improves evidence quality compared with M051:

| Area | M051 status | M052/S06 status |
|---|---|---|
| SHACL negative validation | unproven | runtime-backed for shape-derived valid-frontmatter violations, but wrapper-required due fail-open paths. |
| JSON-LD | unproven | current runtime import/export unsupported; `.jsonld` metadata only. |
| SPARQL-star | unproven | narrow history-graph `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK runtime-backed. |
| `git-lex-serve viz` | unproven/browser-facing | local browser/API smoke runtime-backed, with `/api/store-info` diagnostics gap. |
| `listen` | unproven | SSE/notify works under short-kit config; standard init blocked by kit-string mismatch. |
| Remaining CLI | low coverage | command-by-command matrix with side effects and adapter relevance. |
| Build identity | M051 debug build identity | refreshed local debug build identity; reproducibility/release still blocked. |
| Production gate | vague caution | concrete checklist and minimal adapter gate set. |

### Why production remains blocked

Production adoption remains blocked because these gates still fail or are missing:

1. No release artifact provenance: no tags/releases proven and no concrete release artifact reviewed.
2. No binary-to-source attestation: no manifest, SBOM, signature, SLSA/cosign/GitHub attestation.
3. No reproducible release build proof: only local dev/debug build identity was refreshed.
4. No runtime version identity: `--version` unsupported in prior evidence.
5. Validation is not fail-closed without wrapper logic.
6. JSON-LD runtime support is unsupported.
7. SPARQL-star proof is narrow, not full RDF-star parity.
8. Browser diagnostics are partial due missing `/api/store-info`.
9. `listen` fails in standard initialized squad config.
10. Dangerous CLI surfaces exist (`nuke`, `kit-update`, `save`, `join`, `raw backfill`) and require explicit policy/denylist.
11. Rollback, structured observability, server lifecycle cleanup, auth/exposure/security controls are not implemented as an adapter.
12. ACP source authority and R035/R037/R038 still require ACP-native/legal/runtime proof, not git-lex projection evidence.

### Allowed next path

The only safe next implementation path is an isolated adapter spike with this scope:

```text
Allowed:
  - build from pinned source with manifest
  - create `.lex` only in isolated fixture/worktree
  - run init/sync/query/list/validate-wrapper only
  - collect structured logs and before/after state
  - treat outputs as derived diagnostics
  - delete/rollback fixture state after proof

Not allowed by default:
  - main repo `.lex`
  - release/prebuilt binary adoption
  - nuke/kit-update/join/raw backfill/save/create in unattended ACP automation
  - browser/server production exposure
  - requirement validation from git-lex output alone
```

### Final S06 disposition

```text
S06 result: production readiness gate created
Production status: blocked
Adapter status: adapter-later, with a possible future isolated minimal spike
Release/binary status: blocked pending provenance and reproducibility proof
ACP authority: unchanged; ACP-native source/proof remains authoritative
```
