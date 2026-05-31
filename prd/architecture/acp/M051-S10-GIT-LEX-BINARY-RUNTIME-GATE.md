# M051 S10 Git Lex Binary Runtime Gate

## Status

In progress for `M051-q6ctvc / S10`.

This artifact records upstream build research, local toolchain diagnostics, source-build attempts, isolated runtime proof, and final S08 inputs for git-lex binary/runtime availability.

## Scope and guardrails

S10 exists because S04 could not produce a runnable local `git-lex` / `git-lex-serve` binary, so semantic runtime checks remained blocked. The goal is to resolve or narrow that binary/runtime gate before S08 builds the ACP ontology prototype.

Hard boundaries:

- Do not create or mutate `/root/law-nexus/.lex`.
- Do not run `git lex init`, `git lex sync`, `git lex query`, or `git lex serve` in the main repository.
- Do not simulate runtime proof with ACP-native scripts.
- Keep passed runtime proof, blocked diagnostics, and source-only evidence separate.
- Licensing review is intentionally out of scope for this technical gate per user direction.

## T01: Upstream build issues and known workarounds

### Question

Before trying another local build, check whether the upstream repository or relevant dependency ecosystem already documents the `oxrocksdb-sys` / `stdbool.h` / RocksDB / clang/sysroot build failure and a known workaround.

### Upstream `repolex-ai/git-lex` findings

Local vendor source:

```text
/root/vendor-source/git-lex
commit: eaa4b24d144a78a8b8e4969404d74cf22267df1f
remote: https://github.com/repolex-ai/git-lex
```

GitHub API summary for `repolex-ai/git-lex`:

- Repository is reachable.
- Default branch: `main`.
- `open_issues_count`: 1.
- Issues/PRs returned by `state=all&per_page=100`: 3.
- No issue title/body matched the relevant build terms `build`, `rocksdb`, `oxrocksdb`, `stdbool`, `clang`, `cmake`, `linux`, or `cargo`, except closed PR #1 about cross-repo binary sync into `subtext-mcp`.
- Releases API returned zero releases.

Interpretation: no upstream `git-lex` issue or release note was found that directly documents this local `oxrocksdb-sys` / `stdbool.h` failure or a project-specific workaround.

### Local `git-lex` build documentation findings

Source-backed files checked:

- `/root/vendor-source/git-lex/README.md`
- `/root/vendor-source/git-lex/Cargo.toml`
- `/root/vendor-source/git-lex/Cargo.lock`
- `/root/vendor-source/git-lex/.github/workflows/build.yml`
- `/root/vendor-source/git-lex/.github/workflows/sync-binaries-to-plugin.yml`

Relevant findings:

- README documents source install with:

```text
cargo install --path . --locked
```

- README states `--locked` is required because the `rudof` crate family has sibling-crate API coupling and `Cargo.lock` is the compatibility source of truth.
- GitHub Actions build matrix uses:

```text
cargo build --release --locked --target ${{ matrix.target }}
```

- The Linux x86_64 workflow target is `x86_64-unknown-linux-gnu` on `ubuntu-latest`.
- The workflow omits `aarch64-unknown-linux-gnu` with an explicit comment: the default `cross` image's `g++` is too old for `oxrocksdb-sys` C++20 requirements and needs a newer Ubuntu base.
- `Cargo.lock` includes `oxrocksdb-sys`, `bindgen`, and `clang-sys`.

Interpretation: upstream source and workflows confirm native build sensitivity around `oxrocksdb-sys`, C++20, `bindgen`, and clang/libclang surfaces. They do not directly mention the x86_64 `stdbool.h` failure, but they make C/C++ toolchain correctness a first-class build prerequisite.

### Relevant dependency ecosystem findings

Searches for exact `repolex-ai/git-lex` + `oxrocksdb-sys` / `stdbool.h` returned no direct upstream result.

A directly relevant Rust RocksDB issue exists:

- `rust-rocksdb/rust-rocksdb#903`: `fatal error: 'stdbool.h' file not found`
- The reported failure occurred while generating RocksDB bindings:

```text
rocksdb/include/rocksdb/c.h:65:10: fatal error: 'stdbool.h' file not found
unable to generate rocksdb bindings: ClangDiagnostic(...)
```

- The reporter had GCC and a GCC-provided `stdbool.h`, and a plain C program including `stdbool.h` compiled successfully.
- Installing `clang` resolved the RocksDB binding generation failure for that reporter.

A second related issue in another Rust C-binding crate reinforces the same pattern:

- `DelSkayn/rquickjs#589`: `Compilation error when missing clang`
- The discussion includes a failure on `fatal error: 'stdbool.h' file not found` during bindgen-style C binding generation.
- One comment states: `you don't need clang but you do need a compiler C99 at least and for the basic std to be in path`.
- The issue links back to `rust-rocksdb/rust-rocksdb#903` as a common C-based project failure pattern.

Interpretation: the closest dependency evidence says `stdbool.h` can fail inside bindgen/ClangDiagnostics even when GCC can compile a simple C program. Installing clang/libclang or otherwise making the C standard headers visible to clang/bindgen is a plausible issue-backed workaround, not merely speculation.

### Local read-only toolchain and header diagnostics

Host summary:

```text
Linux vmi2929903 6.8.0-117-generic #117-Ubuntu SMP PREEMPT_DYNAMIC Tue May 5 19:26:24 UTC 2026 x86_64 GNU/Linux
```

Detected commands:

| Command | Status |
|---|---|
| `cc` | present: `/usr/bin/cc` |
| `gcc` | present: `/usr/bin/gcc` |
| `g++` | present: `/usr/bin/g++` |
| `clang` | missing |
| `clang++` | missing |
| `cmake` | missing |
| `make` | present: `/usr/bin/make` |
| `pkg-config` | present: `/usr/bin/pkg-config` |
| `rustc` | present: `/root/.cargo/bin/rustc` |
| `cargo` | present: `/root/.cargo/bin/cargo` |

Versions:

| Tool | Version summary |
|---|---|
| `cc` | Ubuntu GCC 13.3.0 |
| `gcc` | Ubuntu GCC 13.3.0 |
| `g++` | Ubuntu GCC 13.3.0 |
| `make` | GNU Make 4.3 |
| `pkg-config` | 1.8.1 |
| `rustc` | 1.94.1 |
| `cargo` | 1.94.1 |

Local `stdbool.h` locations found:

```text
/usr/include/c++/13/tr1/stdbool.h
/usr/lib/gcc/x86_64-linux-gnu/13/include/stdbool.h
```

Simple local preprocessing checks:

| Check | Result |
|---|---|
| `cc` preprocesses `#include <stdbool.h>` | pass |
| `clang` preprocesses `#include <stdbool.h>` | blocked: `clang` missing |

Interpretation:

- The machine does have a working GCC C/C++ toolchain and GCC-visible `stdbool.h`.
- The machine does not have `clang`, `clang++`, or `cmake` on PATH.
- Because `Cargo.lock` includes `bindgen` and `clang-sys`, and the closest RocksDB issue shows the same `rocksdb/include/rocksdb/c.h:65:10: fatal error: 'stdbool.h' file not found` resolved by installing clang, the most likely next build blocker is not absence of GCC itself. It is missing clang/libclang or missing clang-visible standard include/sysroot configuration for bindgen.
- `cmake` may become a subsequent RocksDB/native build blocker after the clang/header problem is resolved, but T01 did not run a build and therefore does not claim that yet.

### Candidate workaround classification

| Candidate | Evidence class | Rationale | T02/T03 implication |
|---|---|---|---|
| Install or expose `clang`/`clang++` and libclang-compatible headers | Issue-backed and dependency-backed | `rust-rocksdb#903` reports the same RocksDB `stdbool.h` binding failure and says installing clang fixed it; `git-lex` lockfile includes `bindgen` and `clang-sys`; local `clang` is missing. | Strong candidate for T03 if T02 reproduces the same failure. |
| Ensure clang/bindgen can see GCC standard include path or sysroot | Issue-backed but environment-specific | Local GCC sees `stdbool.h`; bindgen may not. This is the common pattern in the external issues. | Check `LIBCLANG_PATH`, `BINDGEN_EXTRA_CLANG_ARGS`, compiler include paths only after fresh T02 reproduction. |
| Install or expose `cmake` | Source-backed as possible later native build prerequisite, but not yet proven for current failure | Local `cmake` is missing, and RocksDB-native builds often need it, but the known S04 failure occurred earlier at bindgen/header generation. | Do not treat as first fix until T02 shows a CMake error or build docs require it. |
| Use newer C++ compiler / Ubuntu base | Source-backed for linux-arm64 cross build only | Upstream workflow explicitly says old `g++` blocks `aarch64-unknown-linux-gnu` cross via C++20, but current host is x86_64 and has GCC/G++ 13.3. | Keep as context, not the first local remediation. |
| Use `cargo build --release --locked --target x86_64-unknown-linux-gnu` | Source-backed workflow parity | Upstream CI builds this target on `ubuntu-latest`; local prior S04 used `cargo build --locked --bins`. | T02 should compare local plain build with workflow-style target build if needed. |

### T01 conclusion

The user's hypothesis that a C compiler might be missing is close but not exact for the current host:

- GCC `cc`, `gcc`, and `g++` are present.
- GCC can preprocess `stdbool.h`.
- `clang` and `clang++` are missing.
- The dependency ecosystem has a direct RocksDB binding issue where `rocksdb/include/rocksdb/c.h:65:10: fatal error: 'stdbool.h' file not found` was resolved by installing clang.

Therefore the next action should not be blind system mutation, but T02 fresh reproduction followed by a T03 minimal remediation centered on clang/libclang/header visibility if the reproduced failure matches S04.

## T01 verification notes

T01 satisfies the upstream-research gate because this report contains:

- upstream issue/API findings;
- release and README/build workflow findings;
- `oxrocksdb-sys`, `stdbool.h`, RocksDB, clang, sysroot, and workaround discussion;
- local read-only toolchain/header diagnostics;
- candidate workaround classification before any new build attempt.

## T02: Reproduce and narrow git-lex source build blocker

### Command

Fresh local reproduction was run from the vendor checkout:

```bash
cd /root/vendor-source/git-lex
cargo build --locked --bins --message-format=short
```

Result:

```text
exit code: 101
```

The full command output was persisted by the harness at:

```text
/root/.local/share/rtk/tee/1780220830_cargo_build.log
```

A concise extraction was captured in `.gsd/exec/c79b090d-8a29-4595-a46a-ca075c1b7f81.stdout`.

### Reproduced failure

The fresh failure matches the S04 blocker and the issue-backed RocksDB pattern from T01:

```text
error: failed to run custom build command for `oxrocksdb-sys v0.5.7`
process didn't exit successfully: `/root/vendor-source/git-lex/target/debug/build/oxrocksdb-sys-fea869c19657c90a/build-script-build` (exit status: 101)
rocksdb/include/rocksdb/c.h:65:10: fatal error: 'stdbool.h' file not found
called `Result::unwrap()` on an `Err` value: ClangDiagnostic("rocksdb/include/rocksdb/c.h:65:10: fatal error: 'stdbool.h' file not found\n")
```

This is not a missing `git-lex` Rust source file and not a missing Cargo lockfile issue. The failure occurs while `oxrocksdb-sys` generates RocksDB bindings through a ClangDiagnostic path.

### Environment comparison

Additional read-only diagnostics recorded in `.gsd/exec/c47f28e9-fd31-4b60-a684-a037bc0921ae.stdout`:

```text
rustc 1.94.1
host: x86_64-unknown-linux-gnu
LLVM version: 21.1.8
```

No relevant `CC`, `CXX`, `LIBCLANG`, `BINDGEN`, `CLANG`, or Cargo target environment variables were set.

GCC include search path includes the standard C header directory where local `stdbool.h` was found:

```text
/usr/lib/gcc/x86_64-linux-gnu/13/include
/usr/local/include
/usr/include/x86_64-linux-gnu
/usr/include
```

G++ include search path includes:

```text
/usr/include/c++/13
/usr/include/x86_64-linux-gnu/c++/13
/usr/include/c++/13/backward
/usr/lib/gcc/x86_64-linux-gnu/13/include
/usr/local/include
/usr/include/x86_64-linux-gnu
/usr/include
```

T01 already verified that `cc` can preprocess `#include <stdbool.h>`, while `clang` is missing.

### Upstream comparison

The reproduced error is nearly identical to `rust-rocksdb/rust-rocksdb#903`, where RocksDB binding generation failed at:

```text
rocksdb/include/rocksdb/c.h:65:10: fatal error: 'stdbool.h' file not found
unable to generate rocksdb bindings: ClangDiagnostic(...)
```

In that issue, GCC could compile a simple `stdbool.h` program, but installing `clang` resolved the binding-generation failure. Our host is aligned with that pattern:

- GCC/G++ are present.
- GCC sees `stdbool.h`.
- `clang`/`clang++` are missing.
- `oxrocksdb-sys` fails through `ClangDiagnostic` on `rocksdb/include/rocksdb/c.h`.

### T02 conclusion

The build blocker is now reproduced and narrowed:

```text
`oxrocksdb-sys v0.5.7` bindgen/ClangDiagnostic cannot resolve `stdbool.h` from RocksDB's C header on this host.
```

The leading T03 remediation is to make clang/libclang and clang-visible standard headers available, then rerun the locked build. `cmake` is still missing and may become a later blocker, but T02 did not observe a CMake failure. The next step should therefore focus first on clang/libclang/header visibility, not on arbitrary Rust source changes or ACP-native simulation.

## T02 verification notes

T02 satisfies the reproduction gate because this report contains:

- the exact `cargo build --locked --bins --message-format=short` command;
- the `oxrocksdb-sys v0.5.7` failing build script;
- the exact `rocksdb/include/rocksdb/c.h:65:10: fatal error: 'stdbool.h' file not found` diagnostic;
- `rustc`/host/toolchain environment details;
- upstream comparison against the issue-backed RocksDB pattern;
- an actionable T03 blocker hypothesis centered on clang/libclang/header visibility.

## T03: Obtain or fail-closed source-built git-lex binary

### Remediation applied

Based on T01/T02 evidence, the chosen minimal remediation was to install the missing native build tools needed for clang/bindgen/RocksDB visibility:

```bash
apt-get update
apt-get install -y clang cmake
```

Installed package set included `clang`, `clang-18`, `cmake`, `libclang-common-18-dev`, `libclang-rt-18-dev`, `llvm-18`, and related development packages. This was a system-level build-tool remediation, not a source-code change.

### Post-remediation toolchain check

After installation, the following checks passed:

```text
clang=/usr/bin/clang
Ubuntu clang version 18.1.3 (1ubuntu1)
Target: x86_64-pc-linux-gnu

clang++=/usr/bin/clang++
Ubuntu clang version 18.1.3 (1ubuntu1)
Target: x86_64-pc-linux-gnu

cmake=/usr/bin/cmake
cmake version 3.28.3

clang_stdbool=ok
```

This confirms the issue-backed remediation made clang visible and able to preprocess `#include <stdbool.h>`.

### Rebuild command

The locked source build was rerun from the vendor checkout:

```bash
cd /root/vendor-source/git-lex
cargo build --locked --bins --message-format=short
```

Result:

```text
cargo build passed
```

The build completed after compiling 9 crates and produced local debug binaries.

### Binary identity

Source and lockfile identity:

```text
source_commit=eaa4b24d144a78a8b8e4969404d74cf22267df1f
cargo_lock_sha256=3fbb6976b85c003fa50f6918f0aaa844665fd2d721dc2a6d7d5526fbbce793d7
```

Built binaries:

| Binary | Path | Mode | Size bytes | sha256 |
|---|---|---:|---:|---|
| `git-lex` | `/root/vendor-source/git-lex/target/debug/git-lex` | `755` | `431543616` | `40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c` |
| `git-lex-serve` | `/root/vendor-source/git-lex/target/debug/git-lex-serve` | `755` | `349467952` | `3c141d9de3c77379fc531a2047c46aaf4f3e7d92cf211b8218b4623e75ed8d20` |

### Help output smoke

`git-lex --help` passed and reports:

```text
Git extensions for knowledge graphs

Usage: git-lex <COMMAND>

Commands:
  init
  query
  dump
  sync
  list
  create
  save
  join
  parse
  nuke
  kit-update
  display
  serve
  history-verify
  raw
  help
```

`git-lex-serve --help` passed and reports:

```text
Servers for git-lex knowledge graphs

Usage: git-lex-serve <COMMAND>

Commands:
  viz
  listen
  help
```

### T03 conclusion

The binary gate is now open for local debug binaries:

```text
binary identity: recorded
sha256: recorded
git-lex --help: pass
git-lex-serve --help: pass
remaining blocker: none for source-built debug binary availability
fail-closed status: not needed for T03 because the source-built binaries exist
workaround: install clang/cmake native build tools so bindgen/oxrocksdb-sys can resolve `stdbool.h`
```

This does not yet prove `init`, `sync`, `query`, `validate`, RDF graph generation, SHACL behavior, named graphs, frontmatter extraction, or `.lex` state cleanup. Those remain T04/T05 isolated runtime responsibilities.

## T03 verification notes

T03 satisfies the binary availability gate because this report contains:

- the applied workaround;
- clang/cmake post-install version checks;
- `clang_stdbool=ok`;
- successful locked Cargo rebuild;
- binary identity, sizes, modes, sha256 hashes, source commit, and Cargo.lock hash;
- `git-lex --help` and `git-lex-serve --help` smoke results.

## T04: Run isolated help and init proof

### Command scope

T04 used the source-built debug binaries from T03 and created only isolated throwaway repositories under `/tmp`:

```text
base workspace:  /tmp/law-nexus-git-lex-s10-20260531T100840Z
squad workspace: /tmp/law-nexus-git-lex-s10-20260531T100840Z-squad
```

Main repository safety checks:

```text
main_lex_before=no
main_lex_after=no
```

This satisfies the no-main-repo guard for T04: `/root/law-nexus/.lex` was absent before and after the runtime checks.

### Help and init command surface

`git-lex --help` passed and exposed the expected runtime commands, including:

```text
init
query
dump
sync
list
create
save
kit-update
serve
history-verify
raw
```

`git-lex init --help` passed and documented:

```text
Usage: git-lex init [OPTIONS] [DIRECTORY]
--kit <KIT>  Use case kit (e.g., soul, squad, or org/repo). Defines valid document types and ontology. The base kit is always installed; this adds a domain-specific kit on top
```

`git-lex-serve --help` passed and exposed:

```text
viz
listen
```

### Base kit init proof

Command:

```bash
/root/vendor-source/git-lex/target/debug/git-lex init --kit base
```

Result:

```text
init_base_exit=0
base_init_status=passed
workspace_lex_after_base=yes
```

Observed stdout:

```text
Downloading base kit repolex-ai/git-lex-kit-base...
Base kit installed.
Installed 9 scaffold file(s) from kit(s)
Created class templates
Initialized .lex/ in /tmp/law-nexus-git-lex-s10-20260531T100840Z
Installed pre-commit hook (extract + validate on commit)
Identity: f530fd26f062711dd9f14638ad39e3ed0b25d20c
```

Observed `.lex` entries include:

```text
.lex/repo.yml
.lex/extract/
.lex/kit/repolex-ai/git-lex-kit-base
.lex/ontology/fm/fm.ttl
.lex/ontology/git/git.ttl
.lex/ontology/lex/lex.ttl
.lex/www/index.html
```

Observed stderr warning:

```text
git-lex not found on PATH or in ~/.claude/plugins/cache/repolex/subtext/*/bin/.
Install the subtext plugin (claude code: /plugin install subtext@repolex) or build from source.
```

Interpretation: base init passed and created expected isolated `.lex` state. The stderr warning is likely from installed hook/path detection because the proof invoked the binary by absolute path rather than putting `git-lex` on `PATH`. It did not fail init, but T05 should account for PATH when testing commands that trigger hooks or subprocesses.

### Squad kit init proof

Command in separate isolated repository:

```bash
/root/vendor-source/git-lex/target/debug/git-lex init --kit squad
```

Result:

```text
init_squad_exit=0
squad_init_status=passed
workspace_squad_lex_after=yes
```

Observed stdout:

```text
Downloading base kit repolex-ai/git-lex-kit-base...
Base kit installed.
Downloading additional kit repolex-ai/git-lex-kit-squad...
Additional kit installed.
Installed 15 scaffold file(s) from kit(s)
SHACL shapes generated: squad-shapes.ttl
Created type folders: Squad/{Bug, Freeform, Situation, Proclamation, Pod, Project, Task, Brief, Discovery, Decision, Message, Squaddie}
Created README.lex.md
Created class templates
Initialized .lex/ in /tmp/law-nexus-git-lex-s10-20260531T100840Z-squad
Installed pre-commit hook (extract + validate on commit)
Identity: 8822fcd47405ee6d173db0855080cce6adaf0d7e
```

Observed `.lex` entries include:

```text
.lex/kit/repolex-ai/git-lex-kit-base
.lex/kit/repolex-ai/git-lex-kit-squad
.lex/ontology/fm/fm.ttl
.lex/ontology/git/git.ttl
.lex/ontology/lex/lex.ttl
.lex/ontology/squad/squad.ttl
.lex/ontology/squad/squad-shapes.ttl
.lex/www/index.html
```

The same PATH/subtext warning appeared on stderr and did not fail init.

### T04 conclusion

T04 upgrades the previous S04 runtime status for init/kit installation:

| Capability | T04 result | Notes |
|---|---|---|
| `git-lex` help | passed | Source-built debug binary works. |
| `git-lex-serve` help | passed | Source-built debug binary works. |
| `git-lex init --kit base` | passed | Isolated `.lex` state created with base ontology and scaffold files. |
| `git-lex init --kit squad` | passed | Isolated `.lex` state created with base+squad ontologies, SHACL shapes, and type folders. |
| Main repo `.lex` safety | passed | `/root/law-nexus/.lex` absent before and after. |
| PATH/hook readiness | warning | Init succeeded, but stderr warns `git-lex` is not on PATH or plugin cache. T05 should use a controlled `PATH` including `/root/vendor-source/git-lex/target/debug` before testing sync/query/validate or commits that trigger hooks. |

This still does not prove sync, query, validate, RDF store behavior, frontmatter extraction, named graph inventory, or semantic claim correctness. Those remain T05 responsibilities.

## T04 verification notes

T04 satisfies the isolated help/init gate because this report contains:

- isolated workspace paths;
- no-main-repo `.lex` checks before and after;
- `git-lex` and `git-lex-serve` help evidence;
- base and squad init exit code 0;
- base and squad `.lex` creation evidence;
- explicit warning about PATH/hook readiness for T05;
- blocked/unproven scope retained for sync/query/validate semantics.

## T05: Run isolated sync query validate semantic smoke

### Command scope

T05 reused the isolated squad workspace from T04 and added the source-built binary directory to `PATH` so hooks/subprocesses can resolve `git-lex`:

```bash
export PATH=/root/vendor-source/git-lex/target/debug:$PATH
cd /tmp/law-nexus-git-lex-s10-20260531T100840Z-squad
```

Main repository safety checks passed again:

```text
main_lex_before=no
main_lex_after=no
main_lex_before_validate=no
main_lex_after_validate=no
```

### Fixture documents

T05 created and committed two minimal isolated fixture documents:

```text
Squad/Decision/S10Decision.md
Squad/Task/S10Task.md
```

Both include frontmatter with `title`, `status`, and `tags` fields. These files live only in the `/tmp` isolated workspace and are not part of `/root/law-nexus`.

### Command results

| Check | Exit | Result |
|---|---:|---|
| `git-lex list` before sync | `0` | Listed 12 `squad:` classes: `Brief`, `Bug`, `Decision`, `Discovery`, `Freeform`, `Message`, `Pod`, `Proclamation`, `Project`, `Situation`, `Squaddie`, `Task`. |
| `git-lex sync` | `0` | Built persistent store at `.git/lex/oxigraph`; reported `Virtual: 421 git + 77 now`, `+25 assertions`, `150 quads`, `2 commit(s)`, `25 events`, `29 annotations`, and `Total sync graphs: 1`. |
| `git-lex dump` | `0` | Emitted 498 N-Quads lines, including repo metadata, git commits, file tree/blob/path triples, and sidecar extraction references. |
| SPARQL class inventory query for `owl:Class` | `0` | Returned 0 rows from persistent store. This means ontology class inventory is not proven through this query shape, even though `git-lex list` can list classes from installed shapes. |
| SPARQL graph inventory query | `0` | Returned 11 named graphs including `repo`, `refs`, `history`, `commits`, `filetree/...`, `changeset/...`, `sync/...`, `meta`, and `now`. |
| SPARQL fixture/frontmatter query | `0` | Returned rows for `S10 Runtime Proof`, fixture paths, sidecar paths, and `fm:title` value `S10 Runtime Gate Decision`. |
| Negative empty query | `0` | Returned `(No results found)` and 0 rows, proving empty-result behavior is non-error for a missing predicate. |
| `git-lex validate --help` | `0` | Confirmed validate surface: `Validate documents against SHACL shapes from the kit ontology`. |
| `git-lex validate` | `0` | Reported `Validated 1 files in 34.7ms — all pass ✓`. |

### Runtime-backed upgrades from S03

| Claim area | T05 outcome | Classification after T05 |
|---|---|---|
| Runnable `git-lex` binary | Help/init/sync/query/dump/validate all ran from source-built binary. | runtime-backed smoke |
| Kit install/init for base and squad | T04 init succeeded; T05 used the squad workspace. | runtime-backed smoke |
| Persistent Oxigraph store creation | `sync` created `.git/lex/oxigraph`. | runtime-backed smoke |
| Git provenance graph | `dump` and query outputs include `git:Commit`, `git:path`, blob hashes, commit messages, authors, and named git graphs. | runtime-backed smoke |
| Frontmatter extraction | `.lex/extract/...fm.spo` sidecars exist and SPARQL returned `fm:title` for the S10 decision fixture. | runtime-backed smoke |
| Named graph inventory | SPARQL `GRAPH ?g` query returned 11 named graphs. | runtime-backed smoke |
| Negative/empty query behavior | Missing predicate query returned 0 rows with exit 0. | runtime-backed smoke |
| SHACL validation command | `git-lex validate` ran and returned all pass for one file. | runtime-backed smoke, narrow positive fixture only |

### Still unproven or partial after T05

| Claim area | Reason |
|---|---|
| Ontology class inventory through SPARQL `owl:Class` | Query returned 0 rows from persistent store. `git-lex list` sees squad classes from installed shapes, but the SPARQL class inventory query shape did not prove class triples in the persistent store. |
| Negative SHACL validation | T05 only ran a positive validate pass. No intentionally invalid fixture was created, so rejection behavior remains unproven. |
| JSON-LD support | No JSON-LD import/export command or round trip was tested. Remains blocked/unproven. |
| SPARQL-star compatibility | No SPARQL-star-specific query was tested. Remains blocked/unproven. |
| History equivalence semantics | Sync produced history events and annotations, but `history-verify` was not run in T05. Remains for a later focused proof if needed. |
| Production fitness or ACP adoption | T05 is isolated runtime smoke only. It does not validate R035/R037/R038 or approve main-repo `.lex` adoption. |

### Cleanup and safety

The isolated workspaces were intentionally retained under `/tmp` for follow-up inspection by T06/S08. No `/root/law-nexus/.lex` directory was created. Runtime outputs remain outside the main repository.

### T05 conclusion

T05 upgrades the git-lex runtime assessment substantially:

```text
sync: passed
query: passed
validate: passed
SPARQL: passed for graph inventory, fixture/frontmatter lookup, and empty query behavior
frontmatter: passed for positive fixture title extraction
graph inventory: passed
cleanup/no-main-repo: passed
```

But the upgrade is bounded: ontology class inventory via SPARQL, negative validation, JSON-LD, SPARQL-star, history equivalence, production fitness, and ACP requirement validation remain unproven or blocked.

## T05 verification notes

T05 satisfies the isolated semantic smoke gate because this report contains:

- `sync`, `query`, `validate`, `SPARQL`, `frontmatter`, `graph inventory`, `upgraded`, `unproven`, and `cleanup` evidence;
- exact pass/fail/partial classification for each tested semantic surface;
- explicit no-main-repo `.lex` safety checks;
- retained blocked/unproven boundaries for claims not covered by the smoke.

## T06: Checkpoint current smoke caveats before deeper investigation

### Checkpoint status

The current S10 runtime smoke is valuable but not final. T01-T05 moved git-lex from blocked binary/runtime status to bounded runtime-smoke evidence, but the final S08 handoff is intentionally deferred until T07-T10 complete deeper kit and SPARQL investigation.

### Runtime smoke passed with caveats

Passed smoke surfaces:

- source-built `git-lex` / `git-lex-serve` binary availability;
- `git-lex --help`, `git-lex init --help`, `git-lex-serve --help`;
- isolated `init --kit base`;
- isolated `init --kit squad`;
- isolated `sync` and persistent `.git/lex/oxigraph` creation;
- `dump` N-Quads output;
- SPARQL query execution for graph inventory, fixture/frontmatter lookup, and empty-result behavior;
- positive `validate` run;
- no-main-repo `.lex` safety before and after runtime checks.

Caveats that block final S08 inputs:

- SPARQL `owl:Class` inventory returned 0 rows, so ontology class query shape is unresolved.
- Negative SHACL validation was not tested.
- JSON-LD import/export remains unproven.
- SPARQL-star compatibility remains unproven.
- `history-verify` was not run, so history equivalence remains unproven.
- Additional demo kits `git-lex-kit-soul` and `git-lex-kit-autoknow` have not yet been acquired or compared.
- GitNexus-backed source analysis of the SPARQL query pipeline is still needed to explain store/query behavior rather than guessing from CLI output alone.

### Deferred finalization rule

Do not close S10 or hand S08 final query requirements from T05 alone. S08 inputs remain deferred until:

1. T07 records soul/autoknow kit inventory.
2. T08 maps the git-lex SPARQL/query pipeline through GitNexus and targeted source anchors.
3. T09 runs the deeper isolated SPARQL/validation matrix.
4. T10 synthesizes ACP-facing SPARQL requirements and S08 inputs.
5. T11 finalizes the S10 capability outcome.

### T06 conclusion

T06 is a checkpoint, not a final result:

```text
runtime smoke: passed with caveats
final S08 inputs: deferred
next evidence: additional kits + GitNexus SPARQL deep dive + deeper runtime matrix
```

## T06 verification notes

T06 satisfies the checkpoint gate because this report explicitly records current runtime-smoke caveats, names unresolved `owl:Class`, Negative SHACL, JSON-LD, SPARQL-star, and `history-verify` surfaces, and marks final S08 inputs as deferred.

## T07: Acquire and inventory soul and autoknow kit repos

### Acquisition results

Two additional demonstration kit repositories were cloned into `/root/vendor-source`:

| Repository | Local path | Remote | Commit | Working tree |
|---|---|---|---|---|
| `git-lex-kit-soul` | `/root/vendor-source/git-lex-kit-soul` | `https://github.com/repolex-ai/git-lex-kit-soul.git` | `5617ea7e4d99340fe905d04dc0f290e074247078` | clean |
| `git-lex-kit-autoknow` | `/root/vendor-source/git-lex-kit-autoknow` | `https://github.com/repolex-ai/git-lex-kit-autoknow.git` | `adba199028588d9e2ba6ad48aebf8074ecce182b` | clean |

### `git-lex-kit-soul` inventory

Top-level layout:

```text
content/
harness/
kit.yml
ontology/
README.md
www/
```

`kit.yml` facts:

```yaml
name: soul
install folders: true
folder base: Soul
folder ontology: soul.ttl
init_prompts:
  - agent_name
```

Ontology files:

```text
ontology/soul/soul.ttl
```

Content and harness surfaces:

```text
content/AGENTS.md
content/Raw/
content/Soul/
harness/.claude/hooks/SessionStart.sh
harness/.claude/soul-listener.py
```

Query/demo relevant files detected:

```text
content/AGENTS.md
content/Soul/Skill/check-mail.md
kit.yml
ontology/soul/soul.ttl
```

ACP scope classification:

| Surface | Classification | ACP relevance |
|---|---|---|
| `ontology/soul/soul.ttl` | ontology/model prior art | Useful to compare how a domain kit defines agent/persona/workflow concepts beyond base `lex/git/fm`. |
| `install folders: true`, `folder base: Soul` | runtime kit evidence | Useful for testing kit-driven folder generation and class listing beyond squad. |
| `init_prompts: agent_name` | runtime init behavior evidence | Important because init can require prompt variables; automated isolated tests must handle prompts or choose non-interactive-safe modes. |
| `harness/.claude/*` | harness/process evidence | Useful to understand agent integration patterns, but not ACP semantic correctness proof. |
| `content/Raw`, `content/Soul` | content scaffold evidence | Useful as prior art for source/raw capture and agent-facing skill records. |

### `git-lex-kit-autoknow` inventory

Top-level layout:

```text
content/
kit.yml
ontology/
README.md
www/
```

`kit.yml` facts:

```yaml
name: autoknow
adaptive: true
install folders: true
folder base: AutoKnow
folder ontology: autoknow.ttl
```

README pipeline claims:

```text
1. Drop source documents into AutoKnow/Source/
2. Subagents extract typed SPO triples with line-number provenance
3. Pipeline aggregates triples, generates entity pages with descriptions
4. git lex save commits and loads triples into the store
5. Query with git lex query or browse via viz
```

Ontology files:

```text
ontology/autoknow/autoknow.ttl
```

Content surfaces:

```text
content/AGENTS.md
content/AutoKnow/
content/_autoknow/
content/_autoknow/subagents/entity-writer.md
content/_autoknow/subagents/extractor.md
content/_autoknow/subagents/ontologist.md
```

Query/demo relevant files detected:

```text
README.md
content/AGENTS.md
content/_autoknow/subagents/entity-writer.md
content/_autoknow/subagents/extractor.md
content/_autoknow/subagents/ontologist.md
kit.yml
ontology/autoknow/autoknow.ttl
```

ACP scope classification:

| Surface | Classification | ACP relevance |
|---|---|---|
| `adaptive: true` | runtime kit evidence and architecture prior art | Important for ACP because adaptive ontology writes to `_ontology/`; this must remain separate from ACP source authority unless explicitly accepted. |
| `ontology/autoknow/autoknow.ttl` | ontology/model prior art | Useful for Source/Entity modeling and provenance semantics, but not LegalGraph correctness proof. |
| `AutoKnow/Source` and `AutoKnow/Entity` pattern | ACP-relevant prior art | Strong conceptual overlap with source records and derived entity pages; must preserve source/derived boundary. |
| Subagent extractor/ontologist/entity-writer files | harness/process evidence | Useful for understanding intended extraction pipeline; not deterministic proof and not legal evidence. |
| README query/viz claims | documentation claim | Useful as runtime test inspiration only; must be verified through local git-lex commands before ACP reliance. |

### T07 conclusion

T07 broadens S10 beyond base/squad:

- `soul` adds an agent/persona-oriented kit with init prompts and Claude harness files.
- `autoknow` adds an adaptive extraction kit with Source/Entity modeling and subagent-driven SPO extraction claims.
- Both are useful for understanding git-lex kit logic, folder installation, ontology packaging, and harness patterns.
- Neither repo by itself proves ACP semantics, LegalGraph correctness, query behavior, or adoption fitness.

T08/T09 should use these inventories to choose deeper GitNexus/source questions and runtime matrix checks. In particular, T09 should treat `autoknow`'s `adaptive: true` and `_ontology/` behavior as a separate proof surface from static kit ontology loading.

## T07 verification notes

T07 satisfies the kit acquisition/inventory gate because `/root/vendor-source/git-lex-kit-soul` and `/root/vendor-source/git-lex-kit-autoknow` exist with commit anchors, and this report records `kit.yml`, ontology, content, harness/process surfaces, and ACP scope classifications for both repositories.

## T08: GitNexus deep dive into git-lex SPARQL query pipeline

### Method

T08 used GitNexus on repo `git-lex-reference` plus targeted source reads from `/root/vendor-source/git-lex`.

GitNexus queries covered:

- `SPARQL query command Oxigraph persistent store named graphs union json results`
- `sync command NQuads spo sidecars ontology loading persistent store`
- `validate command SHACL shapes ontology validation`
- `history-verify command history graph now equivalence`

GitNexus contexts inspected: `cmd_query`, `cmd_list`, `load_lex_nquads`, `generate_frontmatter_nquads`, `cmd_validate`, and `add_prefixes`.

### Source anchors and findings

| Surface | Source anchor | Finding |
|---|---|---|
| `cmd_query` routing | `/root/vendor-source/git-lex/src/main.rs:2413-2446` | Query first opens persistent store with `open_store()`. If unavailable, it builds an in-memory store from `generate_git_nquads()` and `load_lex_nquads()`. It does not load kit ontology TTL or SHACL shapes into the query store in fallback mode. |
| SPARQL execution | `/root/vendor-source/git-lex/src/main.rs:2258-2411` | `run_query()` calls `add_prefixes()`, parses SPARQL, then sets `parsed_query.dataset_mut().set_default_graph_as_union()`. Queries therefore see a union default graph over named graphs in the active Oxigraph store. |
| JSON output | `/root/vendor-source/git-lex/src/main.rs:2286-2317` | `--json` SELECT output follows W3C SPARQL Results JSON shape: `head.vars` and `results.bindings`; boolean output uses `{ "head": {}, "boolean": ... }`. CONSTRUCT/DESCRIBE JSON is explicitly unsupported. |
| RDF triple-term JSON | `/root/vendor-source/git-lex/src/main.rs:2208-2256` | RDF 1.2 triple terms can be serialized in JSON as non-standard nested objects with `type: triple`. This is a query-output capability, not proof that all SPARQL-star query forms are accepted. |
| Prefix injection | `/root/vendor-source/git-lex/src/lib.rs:219-305` | `add_prefixes()` injects defaults for `git:`, `lex:`, `fm:`, `o:`, `rdf:`, `rdfs:`, `owl:`, `xsd:`, plus the configured kit prefix from `.lex/ontology/{short}/{short}-shapes.ttl`. Prefix support is syntactic convenience; it does not load ontology facts. |
| `git-lex list` | `/root/vendor-source/git-lex/src/main.rs:789-824` | `cmd_list()` does not query Oxigraph. It calls `ontology::all_classes()` and prints class names from shape files. |
| Runtime class discovery | `/root/vendor-source/git-lex/src/ontology.rs:1-9`, `48-77`, `318-343` | Runtime type information is read from SHACL shape files, not OWL. `all_classes()` walks `.lex/ontology/**/*-shapes.ttl` and `_ontology/**/*-shapes.ttl`, parses `sh:targetClass`, and returns `(prefix, class, namespace)`. |
| In-memory `.lex` graph loading | `/root/vendor-source/git-lex/src/nquad.rs:378-411` | `load_lex_nquads()` recursively reads only `.lex/**/*.nq`. It does not read `.ttl`, `.jsonld`, `.spo`, or shape files. |
| Now graph generation | `/root/vendor-source/git-lex/src/nquad.rs:416-616` | `generate_frontmatter_nquads()` emits frontmatter/wikilink-derived triples into `<base>/now` and writes `.fm.spo` sidecars. It skips dot directories and is separate from ontology class listing. |
| `sync` persistent store loading | `/root/vendor-source/git-lex/src/main.rs:1583-2203` | `cmd_sync()` opens `.git/lex/oxigraph`, builds adaptive shapes before fast-path, clears non-sync/non-history/non-meta graphs, loads git virtual triples, loads frontmatter `now` N-Quads, computes `.lex/extract/*.spo` deltas into `/sync/{HEAD}`, cleans stale class/frontmatter graphs, and updates `/history` plus `/meta`. |
| `dump` path | `/root/vendor-source/git-lex/src/main.rs:2450-2507` | `Commands::Dump` prints `generate_git_nquads()`, `generate_frontmatter_nquads()`, and `load_lex_nquads()` output. It is not a full persistent store dump and does not include history/meta/sync graphs created only in Oxigraph. |
| `validate` | `/root/vendor-source/git-lex/src/main.rs:1215-1401` | `cmd_validate()` concatenates kit shapes from `.lex/ontology/{short}/{short}-shapes.ttl` and adaptive shapes from `_ontology/*/*-shapes.ttl`, then validates per-file frontmatter Turtle. Parse/load/compile errors currently print diagnostics and return true for those setup failures. |
| `history-verify` | `/root/vendor-source/git-lex/src/main.rs:2645-2859` | `cmd_history_verify()` requires existing `.git/lex/oxigraph`; reconstructs live-at-HEAD triples from `<base>/history` using RDF-star reification, re-emits current `.spo` sidecars, then reports symmetric difference. It does not mutate law-nexus unless run in this repo, which remains forbidden. |

### Explanation: why `git-lex list` saw classes but `owl:Class` SPARQL returned zero rows

The behavior is explained by source separation, not by a failed query engine.

`git-lex list` is shape-file driven:

```text
cmd_list() -> ontology::all_classes() -> all_shape_files() -> parse sh:targetClass
```

Those classes live in SHACL shape files under `.lex/ontology/**/*-shapes.ttl` and `_ontology/**/*-shapes.ttl`.

`git-lex query` is graph-store driven:

```text
cmd_query() -> open_store() or in-memory Store -> run_query(default graph as union)
```

The store receives generated git triples, frontmatter/wikilink triples, `.lex/**/*.nq`, sync deltas, history, and meta graphs. The inspected code does not show automatic loading of kit OWL TTL classes into the query store. Prefix injection includes `owl:` but only supplies a prefix declaration. Therefore a query such as:

```sparql
SELECT ?c WHERE { ?c a owl:Class }
```

can legitimately return zero rows even when `git-lex list` shows classes, because `list` reads `sh:targetClass` from SHACL files while the SPARQL store may contain no `owl:Class` triples.

### Query requirements implied for T09

T09 should avoid treating `owl:Class` as the canonical class inventory query. Instead it should test these source-backed query shapes:

1. For runtime classes: compare CLI `git-lex list --json` output against shape files and, if querying graphs, look for `sh:targetClass` only if shapes are explicitly loaded or emitted into `.nq`.
2. For current working-tree facts: query the union/default graph for `lex:`, `git:`, and `fm:` facts derived from `generate_git_nquads()` and `generate_frontmatter_nquads()`.
3. For named graph checks: use `GRAPH ?g { ?s ?p ?o }` to enumerate available graphs after `sync`, and specific `<base>/now`, `<base>/sync/{sha}`, `<base>/history`, and `<base>/meta` graph shapes where possible.
4. For sidecar-backed semantics: inspect `.lex/extract/*.spo` and compare with `sync` results, because `.spo` is diffed into `/sync/{HEAD}` rather than simply loaded by `cmd_query` fallback.
5. For history equivalence: run `history-verify` only in an isolated repo after `sync`, because it depends on `.git/lex/oxigraph` and current `.spo` sidecars.
6. For JSON: test `git lex query --json` with SELECT and ASK/boolean queries; do not expect CONSTRUCT/DESCRIBE JSON.

### ACP boundary implications

- Runtime-backed SPARQL evidence may cover query execution, default-union behavior, prefixes, JSON SELECT/ASK output, graph inventory, and current/sync/history graph access after T09 proves them in isolation.
- `git-lex list` class inventory is runtime evidence for shape parsing, not proof that ontology TTL classes are queryable as `owl:Class` in Oxigraph.
- Source-only evidence remains required for ontology packaging and shape generation unless T09 explicitly loads or observes those triples in the store.
- JSON-LD remains unproven: no T08 source path showed JSON-LD loading into query or sync.
- SPARQL-star remains partially bounded: source uses RDF-star/triple-term reconstruction in `history-verify` and JSON serialization handles `Term::Triple`, but T09 must still run actual query forms before relying on SPARQL-star compatibility.
- Negative validation remains unproven until T09 constructs an invalid fixture and observes non-zero validation.
- ACP source-of-truth boundaries remain unchanged: git-lex store/query outputs are derived runtime evidence and do not validate R035/R037/R038.

### T08 conclusion

T08 resolves the main `owl:Class` confusion: `list` and `query` are intentionally different pipelines. `list` reads SHACL shapes directly; `query` reads Oxigraph/N-Quads data with default named-graph union semantics. The S08 prototype should therefore specify graph facts and shape/runtime class discovery separately instead of assuming OWL class triples are queryable by default.

## T08 verification notes

T08 satisfies the source deep-dive gate because this report records GitNexus usage, SPARQL query pipeline findings, Oxigraph persistent/in-memory store behavior, named graph union semantics, ontology loading boundaries, `.spo` handling, `dump`, `sync`, `validate`, `history-verify`, JSON output mode, and the source-backed explanation for the `owl:Class` zero-row result.

## T09: Deeper isolated SPARQL and validation matrix

### Method and safety

T09 ran only in throwaway `/tmp` repositories with the source-built binary on a controlled path:

```text
binary: /root/vendor-source/git-lex/target/debug/git-lex
corrected workspace root: /tmp/law-nexus-git-lex-s10-t09-corrected-20260531T142648Z
main repo .lex before/after: false / false
```

The first matrix attempt was discarded as non-diagnostic because its fixture repos had no commits and `git-lex sync` correctly returned `No commits yet. Nothing to sync.` The corrected run created a seed commit first, then initialized git-lex, committed a `Probe.md` fixture, and ran `sync` against a real `HEAD`.

Persisted evidence:

```text
full corrected matrix: .gsd/exec/3fb085b3-d26f-4ae0-bdff-bf37ae04f2aa.stdout
summary: .gsd/exec/5afbd8b4-8870-43ab-97fb-1235c6d66dd7.stdout
focused provenance/dump correction: .gsd/exec/d07ee83e-b299-4504-a86f-51d858e81c1e.stdout
```

Kits tested:

- `base`
- `squad`
- `soul` with `agent_name` supplied non-interactively as `Agent S10`
- `autoknow`

### Runtime matrix outcome

| Check | base | squad | soul | autoknow | Interpretation |
|---|---:|---:|---:|---:|---|
| `init --kit` | pass | pass | pass | pass | All four kits initialize in isolated repos. |
| `list --json` | pass | pass | pass | pass | Shape-driven class listing works. |
| `sync` with committed `HEAD` | pass | pass | pass | pass | Persistent `.git/lex/oxigraph` store is created and populated. |
| Graph inventory query | pass | pass | pass | pass | `GRAPH ?g { ?s ?p ?o }` returns named graphs after sync. |
| `owl:Class` SPARQL query | expected-empty | expected-empty | expected-empty | expected-empty | Confirms T08: class listing is shape-file driven, not `owl:Class` graph data. |
| `sh:targetClass` SPARQL query | expected-empty | expected-empty | expected-empty | expected-empty | Shapes are not query-store facts by default. |
| Probe/frontmatter query | pass | pass | pass | pass | Query sees generated git/frontmatter/now facts for the committed probe. |
| Git provenance query | pass | pass | pass | pass | Focused rerun found 5 `git:` predicate bindings for every kit. |
| `query --json` SELECT | pass | pass | pass | pass | JSON SELECT returns W3C-style `head.vars` and `results.bindings`. |
| `query --json` ASK | pass | pass | pass | pass | `ASK { ?s ?p ?o }` returns `boolean: true` after sync. |
| `dump` | pass | pass | pass | pass | Focused rerun showed `dump` exits 0 and contains `Probe` for every kit. |
| `.lex/extract/*.spo` sidecars | pass | pass | pass | pass | Probe and kit scaffold sidecars are emitted. |
| Positive `validate` | pass/skip | pass | pass | pass/0 files | Base skips due no SHACL shapes; autoknow validates 0 files; squad/soul validate positive files. |
| Negative malformed-frontmatter fixture | failed-to-fail | failed-to-fail | failed-to-fail | failed-to-fail | Validation did not reject the intentionally malformed frontmatter fixture. Negative SHACL/parse-failure proof remains missing. |
| `history-verify --show 5` | pass | pass | pass | pass | History equivalence held after corrected committed/synced setup. |

### Representative command outcomes

`sync` populated stores after corrected fixture setup:

```text
base:     Virtual: 252 git + 9 now;   Sync /sync/22b716e6/: +3 assertions;  Store: /tmp/.../base/.git/lex/oxigraph
squad:    Virtual: 693 git + 69 now;  Sync /sync/1e19f4eb/: +17 assertions; Store: /tmp/.../squad/.git/lex/oxigraph
soul:     Virtual: 917 git + 92 now;  Sync /sync/dd623d3e/: +18 assertions; Store: /tmp/.../soul/.git/lex/oxigraph
autoknow: Virtual: 497 git + 44 now;  Adaptive shapes: 1 built, 0 failed; Sync /sync/558301a3/: +17 assertions; Store: /tmp/.../autoknow/.git/lex/oxigraph
```

Graph inventory returned named graphs for all four kits. Examples included `blame`, `filetree`, `changeset`, `commit`, `now`, `sync`, `history`, and `meta` style graph URIs under `https://localhost/local/{kit}/...`.

Class inventory distinction was confirmed:

```text
list --json: non-empty for squad, soul, autoknow
SELECT ?c WHERE { ?c a owl:Class } LIMIT 20: empty for all kits
SELECT ?c WHERE { ?shape sh:targetClass ?c } LIMIT 20: empty for all kits
```

`query --json` worked for both SELECT and ASK forms:

```text
SELECT: { "head": { "vars": [...] }, "results": { "bindings": [...] } }
ASK:    { "boolean": true, "head": {} }
```

Focused rerun corrected two script-level false negatives from the large-output matrix:

```text
base:     git_provenance_bindings=5, dump_has_probe=True
squad:    git_provenance_bindings=5, dump_has_probe=True
soul:     git_provenance_bindings=5, dump_has_probe=True
autoknow: git_provenance_bindings=5, dump_has_probe=True
main_lex_after=False
```

`history-verify` passed after corrected sync:

```text
base:     history graph 3 triples;  current .spo 3;  matched 3;  only in history/current 0/0
squad:    history graph 18 triples; current .spo 18; matched 18; only in history/current 0/0
soul:     history graph 20 triples; current .spo 20; matched 20; only in history/current 0/0
autoknow: history graph 17 triples; current .spo 17; matched 17; only in history/current 0/0
```

### Validation caveat

The negative validation attempt used a committed `Invalid.md` with malformed YAML frontmatter:

```yaml
---
: [not valid yaml
---
Invalid malformed frontmatter.
```

Observed result:

- `base`: skipped validation because no SHACL shapes were found for `repolex-ai/git-lex-kit-base`.
- `squad`: `Validated 1 files ... all pass`.
- `soul`: `Validated 2 files ... all pass`.
- `autoknow`: `Validated 0 files ... all pass`.

This does not prove negative SHACL behavior. It shows only that this malformed fixture was not a sufficient negative test for the current validator path. T10/T11 should keep negative validation as unproven unless a stronger fixture is built from an actual shape-required class and observed to return non-zero.

### Autoknow adaptive behavior

`autoknow` produced a runtime-specific signal not seen in the other kits:

```text
Adaptive shapes: 1 built, 0 failed
```

This supports T07/T08 classification that `adaptive: true` is a separate proof surface. It proves adaptive shape generation can run in an isolated autoknow repo, but it does not prove ACP should adopt adaptive ontology mutation.

### T09 conclusion

T09 upgrades the following S08 inputs to runtime-backed evidence:

- isolated `base`, `squad`, `soul`, and `autoknow` initialization;
- shape-driven `list --json` class inventory;
- persistent Oxigraph store creation after committed `HEAD` sync;
- named graph inventory via `GRAPH ?g`;
- SELECT and ASK `query --json` output;
- git/frontmatter/probe queryability after sync;
- `.spo` sidecar emission;
- `dump` execution and fixture visibility;
- `history-verify` equivalence in the corrected isolated setup;
- no-main-repo `.lex` safety.

T09 keeps the following surfaces unproven or bounded:

- `owl:Class` and `sh:targetClass` graph class inventory are expected-empty by default;
- negative SHACL/parse-failure validation is still not proven;
- JSON-LD import/export remains untested;
- SPARQL-star remains only indirectly bounded by history code and not yet proven through explicit user-facing query forms;
- ACP runtime adoption remains unapproved.

## T09 verification notes

T09 satisfies the deeper runtime matrix gate because this report records the corrected isolated SPARQL matrix, `--json`, named graph-specific checks, ontology class query behavior, git provenance, frontmatter/probe queryability, `.spo` sidecar expectations, invalid fixture validation outcome, pass/fail/blocked/unproven classification, `history-verify`, and no-main-repo `.lex` safety.

## T10: Synthesize SPARQL requirements and S08 inputs

### S08 runtime-backed inputs

S08 may rely on these git-lex capabilities as runtime-backed evidence from S10:

| Capability | Status for S08 | Evidence |
|---|---|---|
| Source-built `git-lex` binary availability | runtime-backed | T03 source build and binary identity. |
| Isolated init for base/squad/soul/autoknow | runtime-backed | T04/T09 isolated `init --kit` checks. |
| `list --json` class discovery | runtime-backed, shape-driven | T08 source path plus T09 runtime matrix. |
| Persistent Oxigraph store after sync | runtime-backed | T05/T09 `sync` created `.git/lex/oxigraph` in `/tmp` repos. |
| Named graph inventory | runtime-backed | T09 `GRAPH ?g { ?s ?p ?o }` returned graphs after sync. |
| Current git/frontmatter/probe queryability | runtime-backed | T09 SELECT queries over probe/frontmatter and git facts. |
| `query --json` SELECT and ASK | runtime-backed | T09 JSON SELECT/ASK matrix passed. |
| `.spo` sidecar emission | runtime-backed | T05/T09 `.lex/extract/*.spo` checks. |
| `dump` execution | runtime-backed with bounded meaning | T09 focused rerun showed `dump` exits 0 and contains `Probe`; T08 source shows dump is generated N-Quads, not full persistent-store export. |
| `history-verify` equivalence | runtime-backed in corrected isolated setup | T09 `history-verify --show 5` matched history and current `.spo` for base/squad/soul/autoknow. |
| Autoknow adaptive shape build | runtime-backed in isolated autoknow repo | T09 reported `Adaptive shapes: 1 built, 0 failed`. |
| No main repo `.lex` mutation | runtime-backed guard | T04/T05/T09 checked `/root/law-nexus/.lex` absent before/after. |

### S08 source-only or bounded inputs

S08 must keep these as source-only, bounded, or unproven:

| Surface | Status | Boundary |
|---|---|---|
| `owl:Class` graph inventory | expected-empty by default | Do not use `SELECT ?c WHERE { ?c a owl:Class }` as ACP class inventory unless ontology TTL triples are explicitly loaded. |
| `sh:targetClass` graph inventory | expected-empty by default | Runtime list reads shapes directly; shapes are not graph facts by default. |
| Ontology TTL class queryability | source-only/unproven | T08 found no automatic kit ontology TTL loading into query store. |
| Negative SHACL/parse-failure validation | unproven | T09 malformed fixture failed to fail; stronger required-field fixture remains needed. |
| JSON-LD | untested/unproven | No S10 command or source path proved JSON-LD import/export. |
| SPARQL-star user-facing queries | partially source-bounded, runtime-unproven | T08 found RDF-star/triple-term use in history code and JSON term serialization, but T09 did not prove explicit user-facing SPARQL-star query forms. |
| Production fitness | unproven | S10 proves runtime smoke only, not release/distribution/security posture. |
| ACP adoption | not approved | git-lex runtime remains an optional/proof-gated adapter surface. |
| R035/R037/R038 validation | not validated | Derived git-lex evidence cannot validate LegalGraph/FalkorDB/parser requirements. |

### Recommended query shapes for S08 ACP audit prototypes

S08 should use the following query patterns if it prototypes ACP audit views against git-lex runtime evidence.

#### 1. Runtime class discovery

Use CLI shape discovery, not graph class triples:

```bash
git-lex list --json
```

Treat output as shape-driven runtime class inventory:

```json
[{ "prefix": "squad", "class": "Task", "namespace": "...", "uri": "...Task" }]
```

Do not use this as proof that `Task` exists as an `owl:Class` triple in Oxigraph.

#### 2. Named graph inventory

Use a named graph inventory query after `sync`:

```sparql
SELECT ?g (COUNT(*) AS ?count)
WHERE { GRAPH ?g { ?s ?p ?o } }
GROUP BY ?g
ORDER BY ?g
```

Expected S10-backed behavior: non-empty graph inventory after committed `HEAD` sync.

#### 3. Current/probe/frontmatter facts

Use broad fact discovery first, then narrow by `lex:`, `git:`, or `fm:` predicates:

```sparql
SELECT ?s ?p ?o
WHERE { ?s ?p ?o FILTER(CONTAINS(STR(?o), "Probe")) }
LIMIT 20
```

```sparql
SELECT ?s ?p ?o
WHERE { ?s ?p ?o FILTER(CONTAINS(STR(?p), "git-lex/git")) }
LIMIT 20
```

These are runtime-backed for S08 as queryability/provenance smoke, not as ACP source-of-truth proof.

#### 4. JSON result mode

For machine consumption, use SELECT or ASK with `--json`:

```bash
git-lex query --json 'ASK { ?s ?p ?o }'
```

```bash
git-lex query --json 'SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10'
```

Do not rely on CONSTRUCT/DESCRIBE JSON; T08 source shows JSON graph output is unsupported.

#### 5. History equivalence

After sync in an isolated repo, use:

```bash
git-lex history-verify --show 5
```

S08 may use this as runtime smoke for history/current `.spo` equivalence only when it reports:

```text
✓ history == now. the equivalence invariant holds.
```

### Query shapes to avoid or label as expected-empty

Avoid presenting these as failures if they return zero rows:

```sparql
SELECT ?c WHERE { ?c a owl:Class }
```

```sparql
SELECT ?c WHERE { ?shape <http://www.w3.org/ns/shacl#targetClass> ?c }
```

S10 source/runtime evidence says these are expected-empty unless shapes or ontology TTL are explicitly loaded into the graph store.

### Prefix requirements

S08 can rely on `add_prefixes()` injecting these prefix families for query convenience:

- `lex:`
- `git:`
- `fm:`
- `rdf:`
- `rdfs:`
- `owl:`
- `xsd:`
- `o:`
- configured kit prefix such as `squad:`, `soul:`, or `autoknow:` when present

But prefix injection is not ontology loading. A prefix being available does not mean matching triples exist in the store.

### Kit-specific implications

| Kit | S08 implication |
|---|---|
| `base` | Useful for minimal binary/init/sync/query smoke; validation may skip due no SHACL shapes. |
| `squad` | Useful for richer class list and shape-backed validation-positive smoke. |
| `soul` | Useful for prompt-handled init, larger class inventory, and harness prior art; still process evidence, not ACP proof. |
| `autoknow` | Useful for Source/Entity prior art and adaptive shape generation smoke; adaptive ontology behavior must not become ACP source authority without explicit adoption. |

### ACP adapter requirements if S08 uses git-lex

If S08 builds an ACP audit prototype over git-lex, it should enforce these adapter gates:

1. Run only in isolated workspaces until an explicit adoption decision exists.
2. Preserve no-main-repo `.lex` policy for `/root/law-nexus`.
3. Treat git-lex store outputs as derived runtime evidence, not ACP source truth.
4. Separate class discovery from graph queryability: `list --json` for classes, SPARQL for facts/graphs.
5. Record exact binary path, source commit, workspace path, and command outputs for every proof.
6. Keep negative validation, JSON-LD, SPARQL-star, and production-readiness claims out of validated requirement status until separately proven.
7. Never validate R035/R037/R038 from git-lex runtime evidence alone.

### S08 input summary

S08 may proceed with runtime-backed SPARQL requirements for:

- named graph inventory after sync;
- query JSON SELECT/ASK result parsing;
- `git:`, `lex:`, and `fm:` fact exploration;
- shape-driven class listing through `list --json`;
- `.spo` sidecar and history equivalence smoke.

S08 must keep these as blocked or source-only:

- ontology class queries via `owl:Class`;
- graph-shape queries via `sh:targetClass`;
- negative validation guarantees;
- JSON-LD;
- SPARQL-star user-facing query compatibility;
- ACP adoption and LegalGraph requirement validation.

## T10 verification notes

T10 satisfies the synthesis gate because this report records S08 inputs, SPARQL requirements, runtime-backed/source-only split, recommended and failed query shapes, `lex:`, `git:`, `fm:`, `squad:`, `soul`, `autoknow`, JSON-LD, SPARQL-star, `history-verify`, and no-main-repo policy implications.

## T11: Final S10 runtime gate outcome for S08

### Capability outcome table

| Area | Outcome | S08 status | Evidence |
|---|---|---|---|
| Upstream known issue/workaround | No direct `repolex-ai/git-lex` issue/release workaround found; closest dependency evidence points to clang/libclang/header visibility for RocksDB/bindgen `stdbool.h`. | diagnostic-backed | T01 |
| Initial build blocker | Reproduced `oxrocksdb-sys`/RocksDB `stdbool.h` bindgen failure with `cargo build --locked --bins --message-format=short`. | diagnostic-backed | T02 |
| Build remediation | Installing/exposing `clang` and `cmake` opened the local source-build gate. | runtime-backed for this host | T03 |
| Binary identity | Source-built debug `git-lex` and `git-lex-serve` exist under `/root/vendor-source/git-lex/target/debug`. | runtime-backed smoke candidate | T03 |
| Main repo `.lex` safety | `/root/law-nexus/.lex` absent before/after runtime checks. | runtime-backed guard | T04/T05/T09/T10 |
| Base/squad init | `init --kit base` and `init --kit squad` passed in isolated repos. | runtime-backed | T04/T09 |
| Soul/autoknow init | `init --kit soul` and `init --kit autoknow` passed in isolated repos; soul required prompt input, autoknow built adaptive shapes. | runtime-backed | T07/T09 |
| `sync` | Passed after committed `HEAD`, creating persistent `.git/lex/oxigraph` stores and `/sync/{sha}` graphs. | runtime-backed | T05/T09 |
| SPARQL named graph inventory | Passed via `GRAPH ?g` after sync. | runtime-backed | T09 |
| `query --json` SELECT/ASK | Passed for machine-readable SELECT and ASK queries. | runtime-backed | T09 |
| `owl:Class` inventory | Returned zero rows by design/default. | expected-empty; do not use as class inventory | T08/T09 |
| `sh:targetClass` graph inventory | Returned zero rows by design/default. | expected-empty; do not use as class inventory | T08/T09 |
| Class inventory | `list --json` reads SHACL shape files and returns classes. | runtime-backed shape discovery | T08/T09 |
| `.spo` sidecars | Emitted under `.lex/extract/*.spo` in isolated repos. | runtime-backed | T05/T09 |
| `dump` | Runs and includes fixture data, but source shows it prints generated N-Quads, not full persistent-store export. | runtime-backed with bounded meaning | T08/T09 |
| Positive validate | Passed or skipped according to kit shape availability. | bounded runtime-backed | T05/T09 |
| Negative validate | Malformed fixture did not fail validation. | unproven | T09 |
| `history-verify` | Passed in corrected committed/synced isolated setup. | runtime-backed smoke | T09 |
| JSON-LD | Not exercised and no source path proved import/export. | unproven | T08/T09 |
| SPARQL-star | Source uses RDF-star/triple terms in history path; explicit user-facing query forms not tested. | partially source-bounded; runtime-unproven | T08/T09 |
| Production fitness | Debug binary/runtime smoke only. | unproven | S10 scope |
| ACP adoption | No adoption decision; isolated proof only. | not approved | S05/S10 |
| R035/R037/R038 | Not validated by git-lex evidence. | not validated | ACP boundary |

### Acceptance criteria for S08

S08 may consume S10 as complete only if it preserves these acceptance criteria:

1. Treat git-lex as an optional isolated adapter/proof surface, not ACP source truth.
2. Do not create `/root/law-nexus/.lex`.
3. Use `git-lex list --json` for runtime class discovery.
4. Use SPARQL for graph/fact/provenance exploration only after `sync` against a committed isolated repo.
5. Use `query --json` only for SELECT/ASK machine parsing; do not require CONSTRUCT/DESCRIBE JSON.
6. Treat `owl:Class` and `sh:targetClass` graph queries as expected-empty unless ontology/shape triples are explicitly loaded.
7. Keep negative validation, JSON-LD, SPARQL-star user-facing queries, production fitness, and ACP adoption outside validated scope until separately proven.
8. Do not validate R035/R037/R038 from git-lex runtime output.
9. Preserve exact proof anchors: source commit, binary path, workspace path, command outputs, and no-main-repo guard.

### Source and proof anchors

Important S10 anchors:

```text
git-lex source: /root/vendor-source/git-lex
source commit: eaa4b24d144a78a8b8e4969404d74cf22267df1f
Cargo.lock sha256: 3fbb6976b85c003fa50f6918f0aaa844665fd2d721dc2a6d7d5526fbbce793d7
git-lex binary: /root/vendor-source/git-lex/target/debug/git-lex
git-lex binary sha256: 40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c
git-lex-serve binary: /root/vendor-source/git-lex/target/debug/git-lex-serve
git-lex-serve binary sha256: 3c141d9de3c77379fc531a2047c46aaf4f3e7d92cf211b8218b4623e75ed8d20
corrected T09 workspace: /tmp/law-nexus-git-lex-s10-t09-corrected-20260531T142648Z
```

Additional kit anchors:

```text
git-lex-kit-soul: /root/vendor-source/git-lex-kit-soul
soul commit: 5617ea7e4d99340fe905d04dc0f290e074247078
git-lex-kit-autoknow: /root/vendor-source/git-lex-kit-autoknow
autoknow commit: adba199028588d9e2ba6ad48aebf8074ecce182b
```

Durable report and skill anchors:

```text
report: prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md
git-lex skill: .agents/skills/git-lex/SKILL.md
```

The project-local `git-lex` skill was updated during S10 with runtime build playbook and runtime smoke findings so future agents preserve the clang/cmake build order, isolated workspace rule, and proven/unproven query boundaries.

### Claims upgraded by S10

S10 upgrades these claims from blocked/source-only to runtime-smoke-backed:

- local debug binaries can be built on this host after clang/cmake remediation;
- base/squad/soul/autoknow kits can initialize in isolated repos;
- committed isolated repos can sync into Oxigraph stores;
- named graph inventory and current facts are queryable;
- JSON SELECT/ASK output works;
- `.spo` sidecars are emitted;
- `history-verify` can prove history/current equivalence in corrected committed/synced repos;
- autoknow adaptive shape generation can run in isolation.

### Claims still blocked or not upgraded

S10 does not upgrade these claims:

- git-lex production binary distribution fitness;
- ontology TTL queryability as `owl:Class` graph data;
- shape queryability as `sh:targetClass` graph data;
- negative SHACL validation behavior;
- JSON-LD support;
- explicit user-facing SPARQL-star query compatibility;
- ACP backend/runtime adoption;
- LegalGraph requirement validation for R035/R037/R038.

### Next actions after S10

1. Feed T10/T11 S08 inputs into the ACP ontology prototype without main repo `.lex` mutation.
2. If negative validation matters for S08, build a shape-specific invalid fixture and require non-zero `validate` before claiming it.
3. If SPARQL-star matters for S08, add explicit user-facing query checks before relying on it.
4. If JSON-LD matters, run a dedicated source/runtime proof; S10 did not cover it.
5. Keep git-lex adoption behind a separate explicit decision and isolated proof gate.

### Final S10 verdict

```text
binary gate: opened for source-built debug runtime smoke
runtime gate: passed with bounded isolated evidence
S08 inputs: ready with explicit runtime-backed/source-only/unproven split
main repo .lex: absent
ACP adoption: not approved
R035/R037/R038: not validated
```

## T11 verification notes

T11 satisfies the finalization gate when the report contains S08 inputs, capability outcome, upstream findings, passed/failed/blocked/runtime-backed/source-only classification, SPARQL requirements, next actions, and git-lex skill update note, and when fresh architecture verifier and GitNexus change detection pass.
