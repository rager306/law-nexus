# M056/S05: Isolated ACP-kit runtime proof

## Status

Preflight complete. Isolated runtime attempt completed and produced blocked-runtime evidence: base kit fetch/install started, but ACP-kit fetch failed because the remote ACP kit was unavailable or inaccessible.

## Scope and authority boundary

This artifact covers ACP-kit runtime preflight and any later isolated runtime smoke. It is not ACP source truth, not production evidence, not main `.lex` adoption, and not validation evidence for R035, R037, or R038.

Durable proof anchors in this artifact are tracked repository-relative files only:

- `git-lex-kit-acp/kit.yml`
- `git-lex-kit-acp/ontology/acp/acp.ttl`
- `git-lex-kit-acp/content/AGENTS.md`
- `scripts/verify-m056-acp-kit.py`
- `tests/test_verify_m056_acp_kit.py`
- `prd/architecture/acp/M056-S05-ISOLATED-RUNTIME-PROOF.md`

Environment-local binary paths and disposable workspaces may be described as runtime observations, but they are not durable ACP proof anchors.

## T01 preflight findings

### Main checkout residue precheck

Result: pass.

```text
.lex absent: yes
Squad absent: yes
Raw absent: yes
.artifacts absent: yes
```

### ACP-kit scaffold availability

Result: pass.

```text
git-lex-kit-acp/ exists: yes
scripts/verify-m056-acp-kit.py exists: yes
```

### Source-built git-lex binary availability

Result: available as environment-local runtime-smoke candidate.

Observed binary identity:

| Item | Value |
|---|---|
| Source commit | `eaa4b24d144a78a8b8e4969404d74cf22267df1f` |
| Cargo.lock sha256 | `3fbb6976b85c003fa50f6918f0aaa844665fd2d721dc2a6d7d5526fbbce793d7` |
| `git-lex` sha256 | `40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c` |
| `git-lex` mode | `755` |
| `git-lex` size | `431543616` |
| `git-lex-serve` sha256 | `3c141d9de3c77379fc531a2047c46aaf4f3e7d92cf211b8218b4623e75ed8d20` |
| `git-lex-serve` mode | `755` |
| `git-lex-serve` size | `349467952` |

Vendor checkout warning: the external git-lex checkout had three untracked local instruction/config files (`.claude/`, `AGENTS.md`, `CLAUDE.md`). This does not change the recorded source commit or binary hashes, but it means the checkout itself is not clean provenance evidence. Use the binary hashes and source commit only as runtime-smoke identity, not supply-chain acceptance.

### Help output summary

`git-lex --help` exits successfully and lists these bounded commands relevant to S05:

```text
init
list
sync
query
validate
dump
history-verify
kit-update
```

`git-lex-serve --help` exits successfully and lists server commands:

```text
viz
listen
```

Server commands are out of S05 scope unless a later task explicitly adds a disposable-server proof. S05 should prefer non-server CLI operations.

### Kit install mechanics risk

`git-lex init --help` confirms:

```text
Usage: git-lex init [OPTIONS] [DIRECTORY]
--kit <KIT>  Use case kit (e.g., soul, squad, or org/repo)
```

Vendor source inspection indicates short kit names resolve to GitHub repositories like `repolex-ai/git-lex-kit-{name}`, and `org/repo` is also fetched from GitHub. Local filesystem kit-path support is not confirmed by help output or the observed source search.

Implication: `git-lex init --kit acp` may attempt to fetch a remote `repolex-ai/git-lex-kit-acp`. Because the current ACP-kit scaffold is local and untracked in this repository, S05/T02 must treat runtime execution as an isolated attempt-or-block step, not guaranteed proof.

## Post-M056 correction: canonical full-spec install

After M056 closeout, the ACP kit was published as:

```text
rager306/git-lex-kit-acp
```

Use this explicit owner/repository spec everywhere for ACP-kit runtime proof:

```text
git-lex init --kit rager306/git-lex-kit-acp <disposable-workspace>
```

Do not use short `--kit acp` as the canonical project command. Short-name resolution may target `repolex-ai/git-lex-kit-acp`, which is not the accepted law-nexus ACP-kit repository.

Post-publication isolated evidence: full-spec init succeeds in a disposable workspace and keeps the main checkout clean. This upgrades the install-mechanics blocker for the full spec only; runtime semantics such as class discovery, sync/query/validate, and negative validation still require separate proof.

## T02 command plan

T02 originally proceeded with this containment plan:

1. Re-run main checkout residue precheck:

```text
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts
```

2. Create a disposable workspace outside the main checkout.
3. Initialize it as a fresh git repository.
4. Put the source-built debug binary directory on `PATH` for subprocess consistency.
5. Run only bounded non-server commands, preferably:

```text
git-lex --help
git-lex init --kit acp <disposable-workspace>
git-lex list --json
git-lex validate
```

6. If `init --kit acp` fails because the remote ACP kit is unavailable or local-path installation is unsupported, record the failure as blocked-runtime evidence.
7. Do not repair by copying local ACP-kit files into main `.lex`, creating main `.lex`, staging broad changes, running `git lex save`, or mutating the main checkout.
8. Re-run post-check:

```text
test ! -e .lex && test ! -e Squad && test ! -e Raw && test ! -e .artifacts
```

## T02 isolated runtime attempt

### Containment

Result: pass.

```text
pre_no_main_state=yes
workspace_class=disposable_tmp
git_init=ok
git_lex_help=ok
post_no_main_state=yes
workspace_removed=yes
```

The disposable workspace was outside the main checkout. It was removed after the attempt. Runtime-generated `.lex` existed only inside the disposable workspace before cleanup.

### Command attempted

```text
git-lex init --kit acp <disposable-workspace>
```

### Result

Result: blocked-runtime evidence.

```text
init_code=1
created_dotlex=yes
created_acp=no
created_raw=no
```

Relevant stdout:

```text
Downloading base kit repolex-ai/git-lex-kit-base...
Base kit installed.
Downloading additional kit repolex-ai/git-lex-kit-acp...
```

Relevant stderr:

```text
gzip: stdin: unexpected end of file
tar: Child returned status 1
tar: Error is not recoverable: exiting now
Failed to fetch kit 'acp' from GitHub.
Check that https://github.com/repolex-ai/git-lex-kit-acp exists and you have network access.
```

### Interpretation

The source-built git-lex binary can start `init` in a disposable repo and install the base kit, but the ACP domain kit is not fetchable through the current `--kit acp` remote-resolution path. This blocks ACP-kit runtime compatibility proof for the local scaffold. It does not invalidate the static ACP-kit scaffold; it means runtime proof needs a future accepted installation path such as a published ACP kit repository, a proven local-kit installation mechanism, or a scoped test harness that mirrors the expected remote layout without mutating the main checkout.

## Cleanup plan

- Disposable workspaces must live outside the repository.
- Any created disposable workspace must be removable without affecting the main checkout.
- If runtime commands create `.lex`, `ACP`, or generated files, they must be confined to the disposable workspace.
- Main checkout must remain residue-free before and after.

## Supported conclusions after T01-T02

- A source-built git-lex debug binary is available for isolated runtime-smoke attempts.
- ACP-kit static scaffold exists in the repository and has a passing static verifier from S04.
- The source-built git-lex binary can run help and start isolated init.
- Base kit installation begins successfully inside a disposable workspace.
- Main checkout remains free of `.lex`, `Squad`, `Raw`, and `.artifacts` residue after the blocked attempt.

## Blocked or unproven after T01-T02

- Runtime compatibility of `git-lex-kit-acp` remains unproven and currently blocked by ACP kit fetch/install mechanics.
- Local filesystem kit installation support remains unproven.
- Remote `repolex-ai/git-lex-kit-acp` availability is not proven; the isolated attempt failed while fetching it.
- RDF parser behavior, generated SHACL shape behavior, JSON-LD support, SPARQL-star support, negative validation, source-truth migration, production adoption, and R035/R037/R038 validation remain unproven.

## Result boundary classification

### Supports

- The source-built git-lex binary can run help commands in this environment.
- `git-lex init --kit acp` can be invoked inside a disposable git repository without mutating the main checkout.
- The base kit fetch/install path starts successfully in the disposable workspace.
- The current ACP-kit scaffold has static package evidence from S04.
- The blocked runtime attempt is actionable: the next proof needs an accepted way for git-lex to install the ACP kit.

### Blocks

- ACP-kit runtime compatibility is blocked because the ACP domain kit could not be fetched through the current `--kit acp` path.
- S06 must not recommend L2 operational diagnostics that depend on ACP-kit runtime behavior unless it first adds a new proof gate for ACP-kit installation mechanics.
- Main `.lex` rehearsal remains blocked.
- Source-truth migration and production/provenance adoption remain blocked.

### Does not validate

- R035: repository architecture registry coverage.
- R037: Russian legal evidence/profile proof.
- R038: retrieval/citation/profile proof.
- Garant parser behavior, FalkorDB behavior, generated-Cypher safety, negative SHACL validation, JSON-LD support, or SPARQL-star support.

### Recommended next proof gate

Before any ACP-kit runtime claim is upgraded, add one of these proof gates:

1. Use the explicit accepted repository spec `rager306/git-lex-kit-acp`, then rerun isolated `git-lex init --kit rager306/git-lex-kit-acp`.
2. Prove runtime semantics after init: class discovery, sync/query/validate, and negative validation.
3. Keep all proof runs in disposable workspaces with pre/post no-main-state checks.

## Must not infer

- Do not infer that ACP-kit makes git-lex ACP source truth.
- Do not infer that ACP-kit validates R035, R037, or R038.
- Do not infer that a passing static verifier proves runtime compatibility.
- Do not infer that the blocked isolated runtime attempt authorizes main `.lex` adoption.
