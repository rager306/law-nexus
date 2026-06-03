# M054 S01 Pinned Source Adapter Contract

## Status

In progress for `M054-63ujns / S01`.

S01 freezes the proof-only adapter baseline for the tiny isolated source-built git-lex diagnostic adapter spike. This is not production adoption, not release/bundled binary trust, not main repository `.lex`, and not ACP authority transfer.

## Guardrails

- Use D077 pin: local git-lex source commit `eaa4b24d144a78a8b8e4969404d74cf22267df1f`.
- Do not update or fetch/checkout the observed newer remote HEAD in M054.
- Use source-built debug/proof-only binaries only.
- Do not run `git-lex init`, `sync`, `query`, or `validate` in the main repository.
- Runtime proof must use isolated `/tmp` workspace or explicit isolated worktree.
- Main repository `.lex`, `Squad`, and `Raw` must remain absent.
- No release binaries, plugin-bundled binaries, real Claude/session logs, provider payloads, raw legal text, or production server surfaces.
- Adapter output is non-authoritative diagnostics only and cannot validate R035/R037/R038.

## T01: Pinned source and binary identity

### Evidence anchor

```text
.gsd/exec/57573f50-10ea-46d9-8bc8-ac6d84782b60.stdout
```

### Pin decision

```text
decision: D077
pin_commit: eaa4b24d144a78a8b8e4969404d74cf22267df1f
path: /root/vendor-source/git-lex
remote: https://github.com/repolex-ai/git-lex
use_class: proof-only source-built local binary
```

D077 chose the M053-proven local pinned source instead of updating to the observed newer upstream remote HEAD. This keeps M054 narrow and reversible.

### Read-only remote observation

```text
local_HEAD: eaa4b24d144a78a8b8e4969404d74cf22267df1f
remote_HEAD_observed_by_ls_remote: aa10ab71c781565eb86078037b2dbb84f9886f9c
remote_tags_observed_by_ls_remote: none
```

Interpretation:

```text
M054 uses an explicit source pin, not current-upstream adoption evidence.
Remote HEAD drift remains a future update/recheck gate.
```

### Manifest hashes

```text
Cargo.toml: 2746659bd6a0441f2873fb59b4cc69434a0ac28b0d1ee76b9c15a5022d67a7a6
Cargo.lock: 3fbb6976b85c003fa50f6918f0aaa844665fd2d721dc2a6d7d5526fbbce793d7
```

### Source-built debug binary identity

| Binary | Mode | Size bytes | sha256 | Use class |
|---|---:|---:|---|---|
| `/root/vendor-source/git-lex/target/debug/git-lex` | `0755` | `431543616` | `40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c` | proof-only adapter spike |
| `/root/vendor-source/git-lex/target/debug/git-lex-serve` | `0755` | `349467952` | `3c141d9de3c77379fc531a2047c46aaf4f3e7d92cf211b8218b4623e75ed8d20` | help identity only; server surfaces out of scope |

M054's adapter candidate should use only `target/debug/git-lex`. `git-lex-serve` is recorded for identity continuity but server/viz/listen behavior is out of scope.

### Help surface summary

All help checks exited `0` and ran from the vendor checkout, not the main law-nexus repository.

| Command | Exit | Relevant surface |
|---|---:|---|
| `git-lex --help` | 0 | Commands include `init`, `query`, `dump`, `sync`, `list`, `create`, `save`, `join`, `parse`, `nuke`, `kit-update`, `display`, `serve`, `history-verify`, `raw`. |
| `git-lex init --help` | 0 | Supports `init [OPTIONS] [DIRECTORY]` and `--kit <KIT>`. |
| `git-lex query --help` | 0 | Supports SPARQL query string and `--json`. |
| `git-lex validate --help` | 0 | Validates documents against SHACL shapes from kit ontology. |
| `git-lex-serve --help` | 0 | Server commands `viz` and `listen`; out of scope for M054 wrapper. |

### Main repository safety check

Before and after read-only help/identity checks:

```text
main .lex exists: false
main Squad exists: false
main Raw exists: false
```

### T01 conclusion

```text
S01/T01 disposition: pinned-source-identity-ready
D077 pin reflected: yes
source-built git-lex binary identity recorded: yes
help surfaces recorded: yes
main repo residue: none
production/release/plugin binary adoption: still blocked
```

T01 provides enough identity evidence for S02 to define and implement a proof-only wrapper contract against the pinned local `git-lex` binary.

## T02: Adapter policy and diagnostic schema

### Adapter status

```text
adapter_status: proof-only contract
implementation_status: not yet implemented
binary_source: pinned local source-built debug binary
production_status: blocked
main_repo_lex_status: blocked
ACP_authority_status: unchanged; ACP-native source truth remains authoritative
```

### Command allowlist

Only these operations may be executed by the M054 proof-only wrapper:

| Adapter operation | Underlying command | Conditions |
|---|---|---|
| `help` | `git-lex --help` or subcommand help | Read-only; can run from vendor checkout. |
| `init` | `git-lex init --kit <kit> <workspace>` | Isolated workspace only; never main repo. |
| `sync` | `git-lex sync` | Isolated workspace only; after controlled synthetic fixtures are committed if needed. |
| `list_json` | `git-lex list --json` | Isolated workspace only; shape metadata, not ontology truth. |
| `query` | `git-lex query <bounded query>` | Isolated workspace only; allow only predefined query IDs. |
| `query_json` | `git-lex query --json <bounded query>` | Isolated workspace only; normalize/label non-standard triple bindings. |
| `validate_wrapped` | `git-lex validate` | Isolated workspace only; wrapper gates required. |

Optional diagnostics such as `dump` and `history-verify` are intentionally excluded from the first M054 implementation to keep the spike tiny.

### Command denylist

The wrapper must reject these without executing `git-lex`:

```text
save
create
raw
raw backfill
join
kit-update
nuke
display
serve
viz
listen
history-verify
dump
parse
```

Rationale:

- `save`, `create`, `raw`, `join`, `kit-update`, and `nuke` are mutating/risky surfaces from M052/M053.
- `serve`, `viz`, `listen`, and `display` are browser/server surfaces outside this spike.
- `dump`, `parse`, and `history-verify` are optional diagnostics but not needed for the first minimal adapter proof.

### Structured diagnostic record schema

Each adapter operation must emit one JSON record with these fields:

| Field | Required | Notes |
|---|---:|---|
| `schema_version` | yes | Use `m054.git_lex_diagnostic.v1`. |
| `operation_id` | yes | Stable UUID or deterministic run id. |
| `operation_type` | yes | `help`, `init`, `sync`, `list_json`, `query`, `query_json`, `validate_wrapped`, or `reject_denied`. |
| `classification` | yes | `pass`, `git-lex-fail`, `wrapper-fail`, `blocked`, `rejected`, or `not-run`. |
| `workspace_path` | yes | Isolated runtime workspace or `null` for read-only help. |
| `workspace_is_main_repo` | yes | Must be `false` for runtime operations. |
| `git_lex_binary` | yes | Path to pinned binary. |
| `git_lex_source_commit` | yes | Must equal D077 pin. |
| `binary_sha256` | yes | Must match T01 identity. |
| `command` | yes | Full executed command or rejected command intent; secrets redacted. |
| `exit_code` | yes | Raw exit code, or `null` for denied commands not executed. |
| `stdout_digest` | yes | Bounded digest, no secrets. |
| `stderr_digest` | yes | Bounded digest, no secrets. |
| `expected_shapes` | validation only | Required for `validate_wrapped`. |
| `expected_files` | validation only | Required for `validate_wrapped`. |
| `observed_validated_count` | validation only | Parsed from `Validated N files`, if present. |
| `query_id` | query only | Predefined query identifier, not arbitrary user text. |
| `result_count` | query/list only | Parsed when available. |
| `raw_payload_touched` | yes | Must be `false` in M054. |
| `main_lex_absent_before` | yes | Must be `true`. |
| `main_lex_absent_after` | yes | Must be `true`. |
| `main_squad_absent_before` | yes | Must be `true`. |
| `main_squad_absent_after` | yes | Must be `true`. |
| `main_raw_absent_before` | yes | Must be `true`. |
| `main_raw_absent_after` | yes | Must be `true`. |
| `cleanup_status` | yes | `not-needed`, `clean`, `residue-recorded`, or `failed`. |
| `authority` | yes | Always `non-authoritative-diagnostic`. |

### Validation wrapper gates

`validate_wrapped` may classify as `pass` only when all conditions hold:

1. workspace is isolated and not the main repo;
2. expected shape paths are provided;
3. expected fixture paths are provided;
4. expected shape paths exist before validation;
5. expected fixture paths exist before validation;
6. `git-lex validate` exits `0`;
7. stdout contains `Validated N files`;
8. parsed `N` equals expected validated file count;
9. stderr/stdout do not contain skipped/setup/load/parse/schema/compile/processor diagnostics;
10. main `.lex`, `Squad`, and `Raw` remain absent after validation.

For negative fixtures, the wrapper may classify `git-lex-fail` only when:

1. expected shape and fixture paths exist;
2. raw `git-lex validate` exits non-zero;
3. diagnostics identify a SHACL violation, not missing setup or skipped input;
4. main repo safety checks still pass.

Any missing shape, missing fixture, skipped file, malformed input ambiguity, or setup diagnostic must classify as `wrapper-fail`, `blocked`, or `rejected`, not `pass`.

### Query boundaries

The first implementation may use only predefined query IDs:

| Query ID | Purpose | Output expectation |
|---|---|---|
| `graph_inventory` | List named graphs or confirm graph presence. | Human or JSON count. |
| `frontmatter_fixture` | Find synthetic fixture frontmatter title/path. | At least one expected fixture row. |
| `negative_empty` | Confirm empty query can return zero rows safely. | Exit 0, zero rows. |
| `history_reifies_ask` | Optional narrow SPARQL-star ASK from M053 boundary. | Boolean result only if fixture supports it. |

No arbitrary query pass-through in M054. No CONSTRUCT, DESCRIBE, JSON-LD export, broad RDF-star, or unbounded dump.

### Isolation and payload policy

Runtime work must:

- create a synthetic isolated workspace under `/tmp`;
- set `PATH=/root/vendor-source/git-lex/target/debug:$PATH` only inside the proof command context;
- use synthetic ACP-like markdown/frontmatter fixtures only;
- avoid real legal text, provider output, Claude/session logs, secrets, vectors, and raw payloads;
- record workspace path and cleanup status;
- check main repo `.lex`, `Squad`, and `Raw` before and after.

### ACP authority statement

The wrapper output may support:

```text
adapter diagnostics
proof harness debugging
future implementation feasibility assessment
```

The wrapper output may not support:

```text
ACP source truth
requirement validation by itself
R035/R037/R038 validation
Russian legal evidence correctness
FalkorDB runtime proof
Garant ODT parser proof
production adoption
release or plugin-bundled binary trust
main .lex adoption
```

### T02 conclusion

```text
S01/T02 disposition: adapter-policy-ready
allowlist defined: yes
denylist defined: yes
structured schema defined: yes
validation wrapper gates defined: yes
query boundaries defined: yes
ACP non-authority boundary defined: yes
```

## T03: Downstream readiness and verification

### S02 wrapper acceptance criteria

S02 implementation must satisfy:

1. provide a minimal proof-only wrapper or harness in the repository;
2. load or embed the S01 binary identity and D077 pin;
3. reject denied commands without executing `git-lex`;
4. execute allowed commands only when workspace policy is satisfied;
5. emit one JSON diagnostic record per operation;
6. classify operations using `pass`, `git-lex-fail`, `wrapper-fail`, `blocked`, `rejected`, or `not-run`;
7. implement `validate_wrapped` count/shape/file gates;
8. include local tests or verification scripts for denied command rejection and record schema;
9. never create main `.lex`, `Squad`, or `Raw`;
10. keep output proof-only and non-authoritative.

### S03 runtime acceptance criteria

S03 isolated runtime proof must satisfy:

1. create a fresh isolated workspace under `/tmp`;
2. run only through the S02 wrapper;
3. execute runtime matrix:
   - `init`,
   - `sync`,
   - `list_json`,
   - bounded `query`,
   - bounded `query_json`,
   - positive `validate_wrapped`,
   - negative `validate_wrapped`,
   - denied command rejection;
4. use only synthetic/sanitized ACP-like fixtures;
5. record workspace path and cleanup status;
6. record structured diagnostics as tracked artifacts if safe;
7. verify no main `.lex`, `Squad`, or `Raw` before and after;
8. classify failures explicitly rather than bypassing them.

### S01 final contract status

```text
S01 final disposition: contract-ready-for-wrapper
source pin: D077 / eaa4b24d144a78a8b8e4969404d74cf22267df1f
binary identity: recorded
help surfaces: recorded
allowlist: recorded
denylist: recorded
diagnostic schema: recorded
validation gates: recorded
query gates: recorded
S02 readiness: ready
S03 readiness: ready
adoption status: unchanged no adoption
```

### S01 final verification notes

Verification must confirm:

```text
main .lex absent
main Squad absent
main Raw absent
git diff --check pass
GitNexus change scope low or expected
```
