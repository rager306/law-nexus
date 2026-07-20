# git-lex runtime adoption gates

Runtime adoption means using git-lex executable behavior, store behavior, extractors, `.lex` state, sync/query operations, or backend APIs as part of ACP. It is stricter than semantic-kit mapping.

## Required gates

1. Explicit user/adoption decision for the proof path.
2. Isolated workspace outside the main law-nexus checkout.
3. No main-repo `.lex` mutation before proof passes and adoption is explicitly accepted.
4. Reproducible acquisition:
   - source repository/package;
   - pinned commit/version;
   - build/install command;
   - license and dependency notes.
5. Smoke operations:
   - help/version command;
   - init in temporary repository;
   - sync or equivalent extraction;
   - query over generated graph;
   - frontmatter extraction with known and unknown keys;
   - git provenance extraction;
   - failure behavior and cleanup.
6. Semantic-web operations if claimed:
   - RDF/Turtle parse;
   - SPARQL named graph query;
   - RDF 1.2/SPARQL-star quoted-triple parse/query if used for ACP provenance;
   - JSON-LD context/export/import/roundtrip if JSON-LD interoperability is claimed.
7. ACP safety checks:
   - no source/projection authority inversion;
   - R035/R037/R038 not validated from projection/runtime evidence alone;
   - tracked repository-relative proof anchors only;
   - rollback plan and state cleanup.
8. Final per-capability disposition:
   - `use git-lex runtime`;
   - `absorb approach`;
   - `implement ACP-native`;
   - `adapter later`;
   - `reject`;
   - `blocked`.

## Baseline before gates pass

Use ACP-native records, ACP-native validation/lifecycle/proof/recovery, ordinary git, and derived semantic projections. Treat git-lex runtime as optional adapter-later until gates pass.

ACP-kit packaging is not runtime adoption by itself. Creating `git-lex-kit-acp` files, ontology, shapes, content folders, examples, and static verifiers is a semantic-kit implementation track. Runtime adoption gates begin when ACP-kit is initialized, synced, queried, validated, or served through a git-lex executable in an isolated workspace.


## M051 S10 refined gate outcomes

S10 opened the binary gate for source-built debug runtime smoke on this host:

- Source commit: `eaa4b24d144a78a8b8e4969404d74cf22267df1f`.
- Build blocker reproduced as `oxrocksdb-sys` / RocksDB bindgen `stdbool.h` ClangDiagnostic.
- Proven remediation on this host: install/expose `clang` and `cmake`, then run `cargo build --locked --bins --message-format=short`.
- Runtime matrix passed only in isolated `/tmp` repositories for base/squad/soul/autoknow.
- Main checkout `/root/law-nexus/.lex` remained absent.

Runtime-backed after S10:

- debug binary help/init/sync/query/dump/validate smoke;
- `list --json` shape-driven class discovery;
- named graph inventory after committed sync;
- JSON SELECT/ASK query output;
- `.spo` sidecar emission;
- `history-verify` equivalence in corrected committed/synced isolated repos;
- autoknow adaptive shape generation in isolation.

Still blocked or unproven after M051:

- production binary/distribution fitness;
- negative validation behavior;
- JSON-LD import/export;
- explicit user-facing SPARQL-star query compatibility;
- ACP runtime adoption;
- any R035/R037/R038 validation.

## M052 S01 SHACL negative validation update

M052/S01 upgrades one M051 gap:

- Negative validation is runtime-backed for shape-derived valid-frontmatter violations in isolated `/tmp` repositories.
- Proven kits: `squad`, `soul`, and `autoknow`.
- Positive controls exited 0.
- Negative fixtures exited 1 with concrete `sh:minCount`, `sh:in`, and `sh:datatype` violations.
- Evidence anchor: `prd/architecture/acp/M052-S01-SHACL-NEGATIVE-VALIDATION.md` and `.gsd/exec/8be9e02b-3e9b-47f9-9807-44cc1f84cf2e.stdout`.

This does **not** make validation a complete ACP proof gate by itself. Source trace still shows fail-open or skipped behavior for missing kit, missing shapes, bad shape parse/load/schema/compile, malformed YAML frontmatter, no usable kit-prefixed properties, generated Turtle parse/load errors, and SHACL processor errors.

Before ACP relies on git-lex validation, a wrapper or adapter gate must additionally verify:

1. expected shapes are present and compile;
2. expected target files are counted in `Validated N files`;
3. setup/parser/processor diagnostics are treated as hard failures;
4. positive and negative fixtures pass in the adapter environment;
5. main-repo `.lex` remains absent unless separately adopted.

## M052 S04 serve, viz, and listen update

M052/S04 upgrades local `git-lex-serve viz` from unproven to runtime-backed for a narrow local smoke surface:

- Source-backed entrypoint: `git lex serve ...` delegates to `git-lex-serve`; real server code is `src/bin/git-lex-serve.rs`.
- `viz` binds to `127.0.0.1`, serves `.lex/www`, opens `.git/lex/oxigraph` read-only, and exposes `/`, `/api/query`, `/api/run-and-push`, `/api/scene`, `/api/file`, `/api/push`, and `/ws`.
- Browser proof passed for local UI text on `http://127.0.0.1:8891/` and API proof passed for `/api/query`, `/api/run-and-push`, and `/api/scene`.
- Evidence anchor: `prd/architecture/acp/M052-S04-SERVE-VIZ-LISTEN-RUNTIME-PROOF.md`; local `.artifacts/browser/` bundles were produced during GSD validation but are intentionally excluded from durable proof anchors.

Known `viz` gap:

- The installed UI requests `/api/store-info`, but the observed server routes do not implement it.
- Browser diagnostics therefore show one 404/console error even though the UI degrades gracefully and core UI/API proof passes.

M052/S04 classifies `listen` as partial:

- Standard `git-lex init --kit squad` wrote `kit: repolex-ai/git-lex-kit-squad`.
- `cmd_listen` checks for literal `kit: squad`, `kit: soul`, or `kit: lab`, so standard init compatibility is blocked by kit-string mismatch.
- On an isolated copied workspace changed to short `kit: squad`, `listen` started on `127.0.0.1:8893`; `/notify` returned `{ "ok": true }`, and `/events` received the posted SSE payload.

Serve/viz/listen remain adapter-later for ACP. These proofs do not establish auth, TLS, CSRF, external exposure safety, production release provenance, rollback, or main-repo `.lex` adoption.

## M052 S05 remaining CLI update

M052/S05 maps the remaining CLI surface and upgrades several commands from untested to runtime-backed in disposable `/tmp` repositories. Evidence anchor: `prd/architecture/acp/M052-S05-REMAINING-CLI-COMMAND-MATRIX.md`.

Runtime-backed command classes:

- `parse`: read-only tree-sitter debug output.
- `display`: local API client for a running `viz` server; depends on `/api/run-and-push` and inherits S04 `viz` limits.
- `create`: creates a markdown document/template; does not commit.
- `save`: commits valid pending changes with explicit agent identity and runs hooks/extract/validate.
- `join`: writes membership/ticket files across two git-lex repos but does not commit either repo.
- `raw backfill`: no-op without config; copies harness files to `Raw/<Harness>/` when configured.
- hidden `extract`: writes derived `.spo` sidecars.
- `kit-update`: fetches base/domain kits from GitHub and mutates scaffold/shapes/templates.
- `nuke`: destructive removal of `.lex/` and `.git/lex/`, followed by a local commit and attempted `git push` in source.

Critical adoption cautions:

1. `create` can generate a document that is not immediately SHACL-valid. In S05, `create Task s05-task --json` succeeded, but `save` failed with `MinCount(1) not satisfied` until a separate valid README-only save path was tested.
2. `save` can leave staged derived files after validation failure. ACP adapters must inspect/clean `git status` after any failed save.
3. `kit-update` is network-dependent and may change generated shapes/templates even without `--force`; it is not safe as an implicit runtime step.
4. `nuke` is destructive and source attempts `git push`; never run it outside a disposable/no-remote repo or without explicit human confirmation and remote policy.
5. `join` mutates two repositories and leaves commit policy external.
6. `raw backfill` touches per-machine state (`XDG_STATE_HOME` or `~/.local/share/git-lex`) and copies raw harness data; keep raw payloads out of durable ACP proof anchors unless explicitly sanitized.

ACP adapter relevance after S05:

- Required candidates for a future adapter: `init`, `sync`, `query`, `list --json`, `validate` with wrapper gates, possibly `parse` for diagnostics.
- Optional local diagnostics: `dump`, `history-verify`, `display`/`viz` local UI.
- Optional but risky workflow helpers: `create`, `save`, `join`, `raw backfill`.
- Adoption-sensitive/update-only: `kit-update`.
- Unsafe/destructive: `nuke`.

## M052 S02 JSON-LD runtime update

M052/S02 rejects the current claim that git-lex provides JSON-LD RDF import/export at runtime.

Observed evidence:

- No CLI command, `git-lex-serve` endpoint, extractor, or store path was found that imports JSON-LD as RDF or exports graph state as JSON-LD.
- `.jsonld` is treated as file/language metadata when encountered, not as an RDF interchange operation.
- Transitive dependency presence such as `oxjsonld` is not capability proof without an observed call path and runtime behavior.
- ACP S08 JSON-LD remains ACP-native static interchange/prototype evidence, not git-lex runtime evidence.

Gate impact:

- Do not require JSON-LD support for the minimal git-lex adapter allowlist.
- Do not claim git-lex JSON-LD runtime support unless a future source trace and isolated runtime proof show concrete import/export/roundtrip behavior.
- Keep JSON-LD claims in ACP-native artifacts clearly separated from git-lex runtime claims.

## M052 S06 production provenance update

M052/S06 converts production readiness into explicit gates and keeps production adoption blocked.

Runtime-smoke evidence may use the source-built debug binaries from `/root/vendor-source/git-lex`, but production adoption additionally requires:

1. full source commit and lockfile pin;
2. build command, builder image/toolchain, and target triple;
3. binary hashes tied to source and workflow run;
4. release artifact URL or package source;
5. signature/attestation/SBOM or an explicitly accepted absence/risk decision;
6. reproducibility boundary or clean-room rebuild result;
7. runtime version/build identity surface;
8. rollback and cleanup plan for `.lex`, `.git/lex`, generated sidecars, commits, server processes, and raw payloads;
9. security policy for local servers and network/destructive commands;
10. ACP authority gate preserving git-lex output as derived diagnostics.

M052/S06 final status:

- production adoption: blocked;
- runtime adoption: adapter-later;
- release/bundled binary adoption: blocked;
- main repository `.lex` adoption: not approved;
- next safe path: isolated minimal adapter spike with command allowlist and wrapper gates.

## M053 S06 minimal ACP adapter boundary update

M053/S06 narrows the future ACP adapter surface to an `adapter-later` diagnostic contract only. It does not approve implementation, production adoption, release/bundled binary adoption, or main-repo `.lex` use.

Allowed candidate surfaces for a future isolated proof-only adapter spike:

- `git-lex init` in an isolated workspace only;
- `git-lex sync` in an isolated workspace only;
- `git-lex list --json` as shape-driven class metadata, not ontology truth;
- bounded `git-lex query` / `query --json` diagnostics;
- `git-lex validate` only behind M053/S02 fail-closed wrapper gates.

Excluded by default:

- main repo `.lex`, `Squad`, or `Raw`;
- `git lex save`, Claude/session Raw mirroring, `raw backfill`, `create`, `join`, `kit-update`, and `nuke`;
- git-lex JSON-LD RDF import/export claims;
- broad RDF-star/SPARQL-star parity claims;
- serve/viz/listen production use;
- release/bundled binary adoption;
- R035/R037/R038 validation.

Evidence anchor: `prd/architecture/acp/M053-S06-MINIMAL-ACP-ADAPTER-BOUNDARY.md`.

## M053 S07 production provenance update

M053/S07 keeps production provenance blocked:

- `git-lex` remote tags: none observed;
- `git-lex` GitHub releases: zero observed;
- local `git-lex` source commit `eaa4b24d144a78a8b8e4969404d74cf22267df1f` is pinned smoke evidence, but read-only remote HEAD observation differed (`aa10ab71c781565eb86078037b2dbb84f9886f9c`);
- `subtext-mcp` tag `v0.1.3` is a version marker only; GitHub releases count was zero;
- plugin-bundled binary hashes are inventory evidence only;
- no source/build/release manifest, checksum manifest, signature, SBOM, SLSA/GitHub attestation, reproducible build proof, machine-readable `--version`, plugin license decision, or rollback plan was observed.

Maximum safe route after S07:

```text
source-built isolated proof-only spike, with explicit pin-vs-update decision
```

Still blocked after S07:

```text
release-binary adoption
plugin-bundled binary adoption
production ACP adapter adoption
main .lex adoption
```

Evidence anchor: `prd/architecture/acp/M053-S07-PRODUCTION-PROVENANCE-RECHECK.md`.

## M054 proof-only diagnostic adapter spike update

M054 proves the tiny source-built isolated diagnostic adapter path recommended by M053, but only as proof-only instrumentation.

Evidence anchors:

- `prd/architecture/acp/M054-S01-PINNED-SOURCE-ADAPTER-CONTRACT.md`
- `scripts/git_lex_diagnostic_adapter.py`
- `tests/test_git_lex_diagnostic_adapter.py`
- `prd/architecture/acp/M054-S03-ISOLATED-RUNTIME-DIAGNOSTIC-MATRIX.md`
- `prd/architecture/acp/runtime/m054-s03/diagnostics.jsonl`

M054-proven wrapper surfaces:

```text
sync: pass
list_json: pass
bounded query: pass
bounded query_json: pass
validate_wrapped positive: pass
validate_wrapped negative: git-lex-fail with concrete SHACL enum violation
reject_denied nuke: rejected without execution
```

Reusable wrapper lessons:

1. Parse full stdout internally before truncating digests for emitted diagnostics.
2. Do not emit private raw stdout/stderr fields in durable diagnostics.
3. Runtime fixture commits that trigger git-lex hooks need `PATH=/root/vendor-source/git-lex/target/debug:$PATH`.
4. Negative SHACL diagnostics are useful only when they are concrete validation failures, not setup/skip ambiguity.
5. Every record must stay `authority: non-authoritative-diagnostic`.

M054 still does **not** approve:

```text
main .lex adoption
production runtime adoption
release or plugin-bundled binary trust
real legal payload ingestion
Claude/session logs as ACP proof
R035/R037/R038 validation
JSON-LD runtime support
broad RDF-star/SPARQL-star parity
```

## M055 L1 shadow backend decision update

M055 selects continued L1 shadow diagnostic/projection backend use as the next git-lex backend move.

Evidence anchors:

- `prd/architecture/acp/M055-S02-INTERNAL-DIAGNOSTIC-BACKEND-ADAPTER.md`
- `scripts/acp_git_lex_backend.py`
- `tests/test_acp_git_lex_backend.py`
- `prd/architecture/acp/M055-S03-ACP-SHAPED-SHADOW-BACKEND-RUNTIME.md`
- `prd/architecture/acp/runtime/m055-s03/diagnostics.jsonl`
- `prd/architecture/acp/M055-S04-GIT-LEX-REMAINING-ADOPTION-GATES.md`
- `prd/architecture/acp/M055-S05-GIT-LEX-BACKEND-NEXT-DECISION.md`

M055-approved current use:

```text
L1 shadow diagnostic/projection backend
non-authoritative ACP diagnostics
isolated backend workspace only
bounded sync/list/query/query_json/validate/reject_denied adapter operations
main .lex/Squad/Raw absent from /root/law-nexus
```

M055-selected next follow-up:

```text
plan L2 operational diagnostic integration
```

L2 is **not** promoted by M055. It still requires regular ACP workflow invocation, retention policy, failure-state persistence, observability, and fail-closed operational tests.

Still blocked or rejected after M055:

```text
main .lex adoption
ACP source-truth migration
production backend readiness
release or plugin-bundled binary trust
JSON-LD runtime support
broad SPARQL-star/RDF-star parity
raw/session/provider payload proof anchors
R035/R037/R038 validation
Russian legal evidence correctness
Garant ODT parser completeness
FalkorDB runtime behavior
serve/viz/listen operational use without security review
nuke/raw backfill/arbitrary SPARQL pass-through as ACP-safe primitives
```

## R058 knowledge-delta rule

For future work, every promotion from blocked/source-only to runtime-backed must be recorded as a knowledge-delta entry with:

1. prior assumption or open question;
2. evidence anchor;
3. proof class;
4. updated conclusion;
5. remaining boundary;
6. downstream implication for skill, ACP roadmap, or adoption gates.
