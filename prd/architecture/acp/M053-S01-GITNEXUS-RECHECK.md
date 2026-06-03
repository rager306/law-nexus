# M053 S01 GitNexus Recheck

## Status

In progress for `M053-2jp3nm / S01`.

S01 rechecks M052 conclusions before any deeper runtime or adapter work. T01 creates the recheck ledger: what must be confirmed, what GitNexus/source anchors already point to, and which later M053 slices should handle runtime proof.

## Guardrails

- No git-lex runtime command in the main law-nexus checkout.
- Main `/root/law-nexus/.lex` must remain absent.
- GitNexus/source evidence can confirm or challenge a conclusion, but runtime claims still require isolated runtime proof.
- ACP remains source of truth; git-lex output is diagnostic/derived until a later explicit adoption decision.

## T01: M052 conclusion recheck ledger

### Inputs read

- `prd/architecture/acp/M052-S07-GIT-LEX-CAPABILITY-HARDENING-SYNTHESIS.md`
- `.agents/skills/git-lex/references/runtime-adoption-gates.md`
- `.agents/skills/git-lex/references/ontology-map.md`
- `.agents/skills/git-lex/references/source-inventory.md`

### Safety and target state

```text
M053 report existed before T01: no
background processes: none
main_lex_absent: true
```

### GitNexus queries executed

| Repo | Query | Result summary | Index/staleness note |
|---|---|---|---|
| `git-lex-reference` | `cmd_validate SHACL frontmatter_to_turtle shapes validation fail open` | Returned validation process groups `proc_8_cmd_validate`, `proc_7_cmd_validate`, `proc_50_hook_pre_commit`, and `proc_20/21_frontmatter_to_turtl`; symbols include `cmd_validate`, `frontmatter_to_turtle`, `parse_shape_file`, `parse_kit_shapes`, `hook_pre_commit`. | No stale/degraded warning in this T01 run. |
| `git-lex-reference` | `JSON-LD jsonld import export oxjsonld file language metadata` | Did not return a concrete JSON-LD import/export process. Results clustered around unrelated save/raw/kit paths, which supports need for source absence recheck in T02. | No stale/degraded warning. |
| `git-lex-reference` | `SPARQL-star rdf:reifies Term::Triple run_query query JSON` | Returned history/triple-term processes and symbols: `history_annotation`, `take_term`, `history_walk_engine`, `generate_shacl_shapes`, and `emit_spo_line_nquads`; definitions include `term_to_json_subject`. | No stale/degraded warning. |
| `git-lex-reference` | `git-lex-serve viz listen api store-info routes notify events` | Returned store/server-query-related processes and symbols: `open_store_read_only`, `find_git_root`, `store_path`, `main`; definitions include `viz/js/main.js`, `updateSnapshotPill`, `cmd_display`. | No stale/degraded warning. |
| `subtext-mcp-reference` | `host binaries setup git-lex bundled platform version provenance` | Returned host-binary process groups: `server.ts::main -> setupHostBinaries -> detectTargetTriple`; symbols include `setupHostBinaries`, `detectTargetTriple`, `lstatExists`. | No stale/degraded warning. |

### GitNexus symbol context captured

| Symbol | Repo | Incoming | Outgoing | Process participation | Recheck implication |
|---|---|---|---|---|---|
| `cmd_validate` | `git-lex-reference` | `hook_pre_commit`, `main` | `frontmatter_to_turtle`, `get_kit`, `resolve_kit_spec` | `Cmd_validate -> Resolve_kit_spec`, `Cmd_validate -> ParsedShape`, `Cmd_validate -> ShapeProp`, `Hook_pre_commit -> Resolve_kit_spec` | Confirms validation is both direct CLI and pre-commit hook path; wrapper work must handle command and hook semantics. |
| `frontmatter_to_turtle` | `git-lex-reference` | `cmd_validate` | `resolve_kit_spec`, `get_kit_prefix_name`, `get_kit_namespace`, `get_object_properties`, `get_property_datatypes` | `Cmd_validate -> ...`, `Frontmatter_to_turtle -> ParsedShape/ShapeProp`, `Hook_pre_commit -> Resolve_kit_spec` | Confirms skipped/frontmatter conversion behavior is central to validation coverage. |
| `run_query` | `git-lex-reference` | `cmd_query` | `add_prefixes`, `term_to_json` | `Cmd_query -> Term_to_json`, `Cmd_query -> Resolve_kit_spec` | Confirms user-facing query path passes through Oxigraph parse/prefixing and JSON serialization. |
| `open_store_read_only` | `git-lex-reference` | none in indexed context | `store_path` | `Open_store_read_only -> Find_git_root` | Confirms server/store surfaces depend on git-root store location; S05 should recheck read-only store and lifecycle. |
| `setupHostBinaries` | `subtext-mcp-reference` | `server.ts::main` | `detectTargetTriple`, `lstatExists` | `Main -> DetectTargetTriple`, `Main -> LstatExists` | Confirms subtext binary activation is host-platform symlink setup, not provenance proof. |

### Source-anchor scan

Evidence anchor for the scan:

```text
.gsd/exec/6a40a7a5-4a05-49cf-bb6b-357e53956c09.stdout
```

Selected anchors:

| Surface | Source anchors found | T01 interpretation |
|---|---|---|
| SHACL validation | `/root/vendor-source/git-lex/src/main.rs:1216 fn cmd_validate`; `:1230 No kit configured — nothing to validate`; `:1273 No SHACL shapes found ... skipping validation`; `:1343 frontmatter_to_turtle(...)` | Confirms M052 wrapper-required question remains central. T02 should verify exact fail-open classes and wrapper policy. |
| SPARQL query and triple JSON | `/root/vendor-source/git-lex/src/main.rs:2260 fn run_query`; `:2264 Query::parse`; `:2275 set_default_graph_as_union`; `:2238 Term::Triple`; `:2239 "type": "triple"` | Confirms S03 should start from M052 positive control and test boundaries around the same parser/serializer path. |
| Serve/viz/listen | `/root/vendor-source/git-lex/src/bin/git-lex-serve.rs:278 /api/query`; `:308 /api/run-and-push`; `:344 /api/scene`; `:447 kit: squad/soul/lab`; `:471 /events`; `:487 /notify` | Confirms S05 should recheck missing `/api/store-info` and listen kit-string mismatch. |
| CLI surface | `/root/vendor-source/git-lex/src/main.rs:2456 Create`; `:2458 Save`; `:2481 Join`; `:2483 Nuke`; `:2484 KitUpdate`; `:2504 Raw` | Confirms S06 adapter contract must use allowlist/denylist rather than exposing full CLI. |
| JSON-LD | `/root/vendor-source/git-lex/src/nquad.rs:360 Some("jsonld") => Some("jsonld")`; docs mention JSON-LD as architecture/design text | No import/export call path found by source-anchor scan. T02 should recheck absence carefully before preserving rejection. |
| Build workflow | `/root/vendor-source/git-lex/.github/workflows/build.yml:47 cargo build --release --locked --target`; `:82 softprops/action-gh-release@v2`; `:25 TODO aarch64-unknown-linux-gnu` | Confirms S07 provenance recheck should inspect releases/tags/artifacts and not infer production from workflow intent. |
| Plugin binary sync | `/root/vendor-source/git-lex/.github/workflows/sync-binaries-to-plugin.yml:12 SUBTEXT_MCP_PAT`; `:80 Download plugin-bin artifacts`; `:135 binaries: sync git-lex @ ...` | Confirms plugin binary propagation path is real but provenance/attestation remains separate. |
| Subtext host binaries | `/root/vendor-source/subtext-mcp/lib/host-binaries.ts:12 detectTargetTriple`; `:31 setupHostBinaries`; `:40 bin/.platforms`; `:63 relative symlink` | Confirms bundled binary setup is platform symlink behavior, not source/build trust proof. |

### Recheck ledger

| M052 conclusion | M052 status | T01 GitNexus/source anchor | T01 disposition | Later slice |
|---|---|---|---|---|
| SHACL negative validation catches shape-derived valid-frontmatter violations, but raw `validate` is not a standalone ACP proof gate. | `upgraded` narrow, wrapper-required | `cmd_validate -> frontmatter_to_turtle`; `main.rs:1230`, `:1273`, `:1343`; context shows `cmd_validate` also used by `hook_pre_commit`. | `confirmed needs deeper wrapper proof` | S02 |
| JSON-LD runtime RDF import/export is unsupported/not observed; `.jsonld` is metadata-only. | `rejected` current runtime claim | GitNexus did not return import/export process; scan found only `nquad.rs:360 Some("jsonld")` and docs mention. | `confirmed source-absence candidate; recheck further` | S04 |
| SPARQL-star works for history graph `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK only. | `upgraded` narrow | `run_query -> term_to_json`; `history_annotation`; `Term::Triple`; `Query::parse`; `set_default_graph_as_union`. | `confirmed source path; needs boundary expansion` | S03 |
| `viz` local UI/core APIs work, but `/api/store-info` is missing and production/browser exposure is blocked. | `upgraded` local smoke, partial | Server routes include `/api/query`, `/api/run-and-push`, `/api/scene`; source scan found no `/api/store-info` route line while `viz/js/main.js` surfaced in GitNexus definitions. | `confirmed gap target` | S05 |
| `listen` works under short-kit config but standard initialized squad config is blocked by kit-string mismatch. | `upgraded` partial | `git-lex-serve.rs:447` checks literal `kit: squad`, `kit: soul`, `kit: lab`. | `confirmed source target; runtime reproduction needed` | S05 |
| Remaining CLI commands have known hazards; future adapter should use allowlist/denylist. | behavior knowledge upgraded; automation still blocked | `main.rs:2456`, `:2458`, `:2481`, `:2483`, `:2484`, `:2504`; raw/save/kit processes surfaced in GitNexus query. | `confirmed source surface` | S06 |
| `create/save` can leave invalid/staged states; `nuke` is rejected for automation; raw backfill is proof-anchor sensitive. | blocked/rejected as applicable | CLI dispatch anchors and raw/save processes. | `confirmed needs adapter policy` | S06 |
| Production provenance remains blocked: workflows exist but do not prove release/binary trust. | `still blocked` | `build.yml:47`, `build.yml:82`, `sync-binaries-to-plugin.yml:12`, `:80`, `:135`; `setupHostBinaries -> detectTargetTriple`. | `confirmed recheck target` | S07 |
| ACP authority, R035/R037/R038, and main `.lex` adoption remain blocked/not approved. | still blocked | Source inventory / runtime-adoption gates; no GitNexus source symbol can validate project authority. | `confirmed governance boundary` | S08 synthesis |

### Proof plan produced by T01

| Slice | Proof target from T01 | Expected proof class |
|---|---|---|
| S02 | Convert SHACL validation from raw exit-code check into wrapper policy covering skipped/fail-open classes. | Isolated runtime wrapper matrix. |
| S03 | Expand SPARQL-star boundary beyond M052 positive control or prove unsupported forms. | Isolated runtime query matrix. |
| S04 | Recheck JSON-LD absence and decide whether bridge must be ACP-native only. | Source absence proof plus optional runtime probe. |
| S05 | Reproduce/classify `/api/store-info` and `listen` kit-string mismatch; verify local server lifecycle. | Source trace plus browser/HTTP assertions. |
| S06 | Turn CLI hazards into adapter allowlist/denylist and structured output contract. | Contract plus optional isolated harness smoke. |
| S07 | Recheck release tags/artifacts, plugin binary sync, and provenance/attestation gaps. | Source/workflow/release trace. |
| S08 | Synthesize final M053 dispositions and update durable guidance only for changed conclusions. | Cross-slice synthesis and validation. |

### T01 conclusion

T01 found no immediate contradiction to M052 conclusions. It did find that each high-risk conclusion has a concrete source-flow anchor and a specific next proof target. The strongest T01 outputs are:

```text
confirmed for deeper proof: SHACL wrapper need, SPARQL-star narrow source path, serve/listen source gaps, CLI allowlist/denylist need, provenance blockers
source-absence candidate: JSON-LD runtime import/export
no further direct source proof: ACP authority and R035/R037/R038 remain governance/product boundaries, not git-lex source questions
```

## T02: SHACL and JSON-LD source recheck

### Additional GitNexus context

| Symbol | Repo | Relevant context | T02 implication |
|---|---|---|---|
| `parse_shape_file` | `git-lex-reference` | Called by `parse_kit_shapes` and `all_classes`; outgoing accesses include `ShapeProp.required`, `ShapeProp.datatype`, `ShapeProp.is_iri`, and `ShapeFile.prefix_name/namespace`; participates in `Cmd_validate -> ParsedShape/ShapeProp`, `Frontmatter_to_turtle -> ParsedShape/ShapeProp`, `Cmd_create`, `Cmd_history_verify`, and frontmatter N-Quads generation flows. | Shape parsing is shared across validate/create/history/frontmatter projection. Wrapper policy must not assume validation is the only consumer. |
| `parse_kit_shapes` | `git-lex-reference` | Called by `get_kit_prefix_name`, `get_kit_namespace`, `get_object_properties`, `get_property_datatypes`, and `get_kit_types`; calls `resolve_kit_spec`, `read_kit_shapes`, `parse_shape_file`. | Confirms frontmatter conversion gets namespace/object/datatype decisions from installed shapes. Missing/bad shapes can affect both validation and data generation. |
| `generate_shacl_shapes` | `git-lex-reference` | Called by `build_shacl_shapes`; calls `find_kit_ttl`, `load_kit_into_store`, `resolve_kit_spec`, and `generate_shapes_from_store`. | Confirms generated shape files are derived from kit TTL and are a precondition for validation; generation/build errors should be adapter-visible. |

### Source excerpts reviewed

| Source | Lines | Finding |
|---|---:|---|
| `/root/vendor-source/git-lex/src/main.rs` | 1215-1401 | `cmd_validate()` returns `true` for missing kit, missing SHACL shapes, failed shapes parse/load/schema/compile, generated data parse/load errors, and SHACL processor errors. It returns `false` only when a SHACL report exists and `!report.conforms()` increments `total_violations`. |
| `/root/vendor-source/git-lex/src/extraction.rs` | 159-274 | `frontmatter_to_turtle()` returns `None` for unreadable files, missing frontmatter delimiter, malformed YAML, no matching `short.class.property` keys, missing inferred doc type, empty usable values, and root-relative path failure. `cmd_validate()` silently skips `None` files. |
| `/root/vendor-source/git-lex/src/nquad.rs` | 330-390 | `.jsonld` appears only in a file-extension-to-language mapping: `Some("jsonld") => Some("jsonld")`. This emits `git:language "jsonld"` metadata for files, not RDF import/export. |
| `/root/vendor-source/git-lex/Cargo.toml` | 1-49 | Direct dependencies include `oxigraph`, SHACL/rudof crates, `serde_json`, `serde_yaml`, `axum`, etc.; no direct `oxjsonld` dependency is declared. |

### SHACL source conclusion

T02 confirms the M052 SHACL boundary.

Raw `git-lex validate` has two different kinds of outcomes:

| Class | Source behavior | ACP proof implication |
|---|---|---|
| Operational fatal | Not in a git repo exits `1`. | This is not semantic validation; it is only an execution precondition. |
| Missing kit | Prints `No kit configured — nothing to validate.` and returns `true`. | Fail-open for ACP validation. |
| Missing shapes | Prints `No SHACL shapes found ... skipping validation.` and returns `true`. | Fail-open for ACP validation. |
| Shapes parse/load/schema/compile failure | Logs diagnostic and returns `true`. | Fail-open setup error. |
| Frontmatter missing/malformed/irrelevant/empty | `frontmatter_to_turtle()` returns `None`; file is skipped and not counted. | Coverage gap; raw success does not imply all docs were checked. Explicit skipped-frontmatter marker: `frontmatter_to_turtle() returns `None`` is a validation coverage gap. |
| Generated Turtle parse/load error | Logs diagnostic and `continue`; no violation count. | Fail-open data-generation error. |
| SHACL processor error | Logs diagnostic but does not increment violations. | Fail-open processor error. |
| Actual SHACL non-conformance report | Increments `total_violations`; final return `false`; CLI exits non-zero through caller. | Valid negative proof path, already runtime-backed by M052 for selected fixtures. |

T02 disposition:

```text
SHACL wrapper requirement: confirmed
M052 narrow upgrade: still valid
Standalone raw validate as ACP proof gate: still blocked
Runtime follow-up: S02 should prove wrapper catches at least one skipped/fail-open class, not only normal SHACL violations
```

### JSON-LD source conclusion

Evidence anchors:

```text
.gsd/exec/d9abf153-a2a1-40bb-9761-24a8fecd1e93.stdout
.gsd/exec/d60bd8d6-a31a-45ba-867c-db8ecbe47dd4.stdout
.gsd/exec/586cf9da-74f1-4e7a-bda5-31d5c5e8ecbd.stdout
```

Findings:

| Check | Result | Interpretation |
|---|---|---|
| `rg jsonld` across source/docs/manifests | Matches only `src/nquad.rs` language mapping and design doc discussion. | No implementation route found. |
| `Cargo.toml` direct deps | No `oxjsonld` direct dependency. | git-lex package does not explicitly expose JSON-LD library use. |
| `Cargo.lock` / `cargo tree -i oxjsonld` | `oxjsonld` is present transitively via `oxrdfio` / `oxigraph` / `rudof_rdf` / `sparql_service`. | Transitive dependency presence is not a runtime capability claim. |
| CLI command enum | Contains `query --json`, `list --json`, `create --json`, `raw`, etc.; no JSON-LD import/export/roundtrip command. | Existing JSON flags are generic JSON output/input summaries, not JSON-LD RDF support. |
| Source file list mentioning JSON-LD | `src/nquad.rs`, `docs/2026_03_26_DESIGN_CONCEPTS.md`. | Confirms current implementation visibility is metadata + design idea only. |

T02 disposition:

```text
JSON-LD runtime import/export rejection: confirmed by source absence
M052 JSON-LD conclusion: still valid
Runtime follow-up: S04 may run an absence probe, but T02 found no source call path to upgrade
Safe wording: `.jsonld` can be recorded as file language metadata; git-lex does not currently prove JSON-LD RDF import/export
```

### T02 contradiction ledger

| Topic | M052 conclusion | T02 result | Contradiction? | Next action |
|---|---|---|---|---|
| SHACL negative validation | Upgraded narrowly, wrapper-required | Confirmed by source. Raw validate has multiple fail-open/skipped paths. | No | S02 wrapper proof. |
| JSON-LD runtime | Rejected / unsupported-not-observed | Confirmed by source absence and CLI/dependency scan. | No | S04 optional runtime absence probe and bridge decision. |
| Dependency presence | `oxjsonld` alone is not proof | Confirmed: transitive via RDF stack, no direct call path found. | No | Keep dependency-only claims unsafe. |
| Main repo safety | `.lex` must remain absent | Confirmed during source scans. | No | Continue no-main-runtime policy. |

### T02 conclusion

T02 strengthens, rather than changes, M052 conclusions:

```text
SHACL: M052 narrow runtime upgrade stands, but raw validate remains unsafe as ACP proof gate without wrapper coverage checks.
JSON-LD: current runtime import/export claim remains rejected; source only supports `.jsonld` file-language metadata plus design-doc interest.
```

## T03: Query, server, CLI, and provenance source recheck

### Additional GitNexus context

| Symbol / query | Repo | Relevant context | T03 implication |
|---|---|---|---|
| `term_to_json` | `git-lex-reference` | Incoming from `term_to_json_subject` and `run_query`; participates in `Cmd_query -> Term_to_json`. | Confirms `Term::Triple` JSON handling is on the user-facing `cmd_query` output path. |
| `cmd_display` | `git-lex-reference` | Incoming from `main`; source scan shows it is the local client for a viz server. | Confirms `display` should remain coupled to local `viz` API rather than treated as standalone graph proof. |
| `cmd_save` | `git-lex-reference` | Incoming from `main`; outgoing to `harness::sync`, `resolve_agent_identity`, `raw_mirror::run`, `MirrorReport.is_noop`; participates in raw mirror and git-root/status flows. | Confirms `save` has broad side effects and belongs outside unattended adapter allowlist. |
| `cmd_join` | `git-lex-reference` | Incoming from `main`; outgoing to `read_identity`. | Confirms join is a separate repo-identity mutation surface, not required for minimal adapter. |
| `cmd_raw_backfill` | `git-lex-reference` | Incoming from `main`; outgoing to `raw_mirror::backfill` and `MirrorReport.is_noop`; participates in harness path/state/matches_glob flows. | Confirms raw mirroring touches machine/harness state and requires separate policy. |
| `raw_mirror::run` | `git-lex-reference` | Called by `cmd_save`; reads config, expands watch paths, reads/writes state, matches globs, and writes mirror report counts. | Confirms `save` can implicitly touch raw mirror state. |
| `cmd_nuke` | `git-lex-reference` | Incoming from `main`; outgoing to `auto_commit_snapshot`, `remove_hook`, and `registry_remove`; processes include hook/registry cleanup. | Confirms `nuke` rejection for automation. |
| `cmd_kit_update` | `git-lex-reference` | Incoming from `main`; outgoing to `fetch_kit_from_github`, scaffold install, SHACL shape building, Claude substrate setup. | Confirms kit-update is network/scaffold/shape mutating and not safe as an implicit adapter step. |
| `host binaries setup` query | `subtext-mcp-reference` | `server.ts::main -> setupHostBinaries -> detectTargetTriple`; symlink setup over `bin/.platforms/<target>`. | Confirms subtext bundled binary activation is platform setup, not provenance proof. |

### Source-anchor scan

Evidence anchors:

```text
.gsd/exec/7a86526c-8174-42c4-a17e-68e90afca953.stdout
.gsd/exec/8958cddb-0062-49af-9fdb-c5ffac2cf3a8.stdout
```

Selected anchors:

| Surface | Source anchors | T03 interpretation |
|---|---|---|
| User-facing query path | `/root/vendor-source/git-lex/src/main.rs:2260 fn run_query`; `:2264 Query::parse`; `:2275 set_default_graph_as_union`; `:2238 Term::Triple`; `:2414 fn cmd_query` | Confirms M052 SPARQL-star proof was on the normal CLI query path. S03 should expand boundaries around this path, not invent a separate parser claim. |
| Triple-term JSON | `/root/vendor-source/git-lex/src/main.rs:2238 Term::Triple`; `:2343 format << ... >>`; `:2881 format << ... >>` | Confirms triple-term serialization exists in query/history code. JSON shape remains non-standard and should be adapter-normalized if consumed. |
| `display` | `/root/vendor-source/git-lex/src/main.rs:1489 fn cmd_display` | Confirms `display` is a local viz API client; it inherits `viz` server gaps. |
| `save` side effects | `/root/vendor-source/git-lex/src/main.rs:1021 fn cmd_save`; `:1057 raw_mirror::run`; `:1063`, `:1072`, `:1080` git commands | Confirms `save` is side-effectful and can touch raw mirror plus git add/commit paths. |
| `join` | `/root/vendor-source/git-lex/src/main.rs:1111 fn cmd_join` | Confirms separate membership/identity mutation surface. |
| `raw backfill` | `/root/vendor-source/git-lex/src/main.rs:2510 fn cmd_raw_backfill`; raw mirror context shows state paths/glob matching. | Confirms raw payload copying remains proof-anchor-sensitive. |
| `nuke` | `/root/vendor-source/git-lex/src/main.rs:2893 fn cmd_nuke`; `:2937` git command; `:2969 git add -A`; `:2970 git commit`; `:2982 git push` | Confirms automated ACP use remains rejected. |
| `kit-update` | `/root/vendor-source/git-lex/src/main.rs:2993 fn cmd_kit_update`; GitNexus context calls `fetch_kit_from_github`, scaffold install, SHACL shape building. | Confirms network/scaffold mutation and shape regeneration risk. |
| `viz` routes | `/root/vendor-source/git-lex/src/bin/git-lex-serve.rs:278 /api/query`; `:308 /api/run-and-push`; `:344 /api/scene`; `:367`, `:385 127.0.0.1`; `:394 open::that_detached` | Confirms local smoke route set and localhost binding; production exposure remains unproven. |
| Missing store-info route | `viz/js/main.js:1929 Contract (GET /api/store-info)`; `:1940 fetch('/api/store-info')`; no matching server route in `git-lex-serve.rs` scan. | Confirms M052 `/api/store-info` gap is source-backed. |
| `listen` kit check | `/root/vendor-source/git-lex/src/bin/git-lex-serve.rs:447 if !config.contains("kit: squad") && ...`; `:471 /events`; `:487 /notify`; `:498 127.0.0.1` | Confirms standard fully-qualified kit string mismatch remains a source-level target. |
| Build workflow | `.github/workflows/build.yml:47 cargo build --release --locked --target`; `:67`, `:74 upload-artifact`; `:82 softprops/action-gh-release`; `:25 TODO aarch64-unknown-linux-gnu` | Confirms workflow intent but not release/provenance proof. |
| Sync workflow | `.github/workflows/sync-binaries-to-plugin.yml:12 SUBTEXT_MCP_PAT`; `:80 download artifact`; `:135 binaries: sync git-lex @ ...`; `:139 git push origin main` | Confirms cross-repo binary propagation with PAT/direct push. |
| Host binaries | `subtext-mcp/lib/host-binaries.ts:12 detectTargetTriple`; `:17 linux arm64 -> aarch64-unknown-linux-gnu`; `:31 setupHostBinaries`; `:40 bin/.platforms`; `:65 symlinkSync`; `:67 warning on symlink failure` | Confirms platform symlink behavior and a Linux arm64 target mapping that may lack produced binaries. |
| Plugin metadata | `subtext-mcp/.claude-plugin/plugin.json:2 name subtext`; `:4 version 0.1.3`; no provenance fields found. | Confirms plugin metadata is not binary provenance manifest. |

### Provenance negative marker check

The workflow/plugin files were scanned for production-provenance keywords:

```text
sha256: 0
checksum: 0
attestation: 0
attest: 0
sbom: 0
cosign: 0
slsa: 0
provenance: 0
signature: 0
signed: 0
--version: 0
```

This is not a full supply-chain audit, but it confirms M052's immediate source-level observation: reviewed build/sync/plugin metadata does not expose checksum, signature, SBOM, SLSA/cosign, attestation, provenance manifest, or runtime version identity fields.

### T03 contradiction ledger

| Topic | M052 conclusion | T03 result | Contradiction? | Next action |
|---|---|---|---|---|
| SPARQL-star narrow path | Runtime-backed only for history-graph `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK. | Source/GitNexus confirms `cmd_query -> run_query -> term_to_json`, Oxigraph parser, default graph union, and `Term::Triple` serialization. | No | S03 boundary expansion runtime matrix. |
| Broad RDF-star parity | Still blocked. | Source does not add custom broad compatibility layer; query path delegates to Oxigraph. | No | S03 should test unsupported forms and keep safe wording narrow unless evidence expands. |
| `viz` local routes | Local `/`, `/api/query`, `/api/run-and-push`, `/api/scene` runtime smoke only. | Source confirms route set and localhost binding. | No | S05 may re-run browser/HTTP assertions if fixing/classifying gaps. |
| `/api/store-info` | Missing route/diagnostics gap. | UI source requests it; server route scan did not find implementation. | No | S05 classify as source gap, graceful degradation, or fix candidate. |
| `listen` kit-string mismatch | Standard init blocked; short-kit workaround works. | Source literal check requires `kit: squad|soul|lab`, matching M052 diagnosis. | No | S05 reproduce or decide adapter repo.yml policy. |
| CLI allowlist/denylist | Full CLI unsafe for adapter; minimal allowlist needed. | Source confirms side-effectful `save`, `join`, `raw`, `kit-update`, and destructive `nuke`. | No | S06 adapter contract should enforce allowlist/denylist. |
| Production provenance | Still blocked. | Workflows build/sync artifacts, but scans find no checksum/attestation/SBOM/signature/provenance/version fields. | No | S07 release/provenance recheck. |
| Subtext bundled binaries | Activation path exists but is not provenance proof. | `setupHostBinaries` symlinks platform binaries; plugin metadata lacks provenance. | No | S07 keep source-pinned acquisition default unless release proof upgrades. |

### T03 conclusion

T03 confirms M052's query/server/CLI/provenance conclusions and sharpens the next proof targets:

```text
SPARQL-star: source path confirmed, boundary expansion still needed.
serve/viz/listen: source gaps confirmed; browser/server runtime proof belongs in S05.
CLI: allowlist/denylist requirement confirmed by command side effects.
provenance: workflow/plugin metadata still lacks production trust markers; S07 must recheck release/artifact state before any upgrade.
```

## T04: Final contradiction ledger and proof plan

### Final contradiction ledger

| Area | M052 conclusion | M053 S01 source recheck | Disposition | Routed next step |
|---|---|---|---|---|
| SHACL negative validation | Narrow runtime upgrade; wrapper-required. | `cmd_validate`, `frontmatter_to_turtle`, `parse_kit_shapes`, and `generate_shacl_shapes` confirm real violation path plus multiple fail-open/skipped paths. | `confirmed` + `needs runtime proof` | S02 must prove wrapper catches skipped/fail-open classes, not only actual SHACL violations. |
| JSON-LD runtime | Current git-lex JSON-LD RDF import/export claim rejected. | Source scan found only `.jsonld` language metadata and design-doc interest; `oxjsonld` is transitive and no CLI/server/call path was found. | `confirmed` + `needs optional runtime absence proof` | S04 should run a minimal absence probe or bridge decision; do not promote JSON-LD runtime. |
| SPARQL-star narrow history graph support | Narrow `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK runtime-backed. | `cmd_query -> run_query -> term_to_json`, Oxigraph parser, and `Term::Triple` serializer confirmed. | `confirmed` + `needs boundary expansion` | S03 should test positive control plus unsupported/boundary forms. |
| Broad RDF-star/SPARQL-star parity | Still blocked. | No custom compatibility layer found; parser delegates to Oxigraph. | `blocked` | S03 may upgrade only with explicit runtime matrix; otherwise keep blocked. |
| `viz` local UI/API | Local smoke backed; production/browser exposure blocked. | Server routes and localhost binding confirmed. | `confirmed` | S05 can focus on gap classification and lifecycle, not route rediscovery. |
| `/api/store-info` | Missing route/diagnostics gap. | UI calls `/api/store-info`; server route scan did not find route. | `confirmed` + `needs runtime/contract decision` | S05 classify as graceful degradation, fix candidate, or adapter policy. |
| `listen` standard init mismatch | Short-kit works; standard fully-qualified kit string blocked. | Source literal check requires `kit: squad`, `kit: soul`, or `kit: lab`. | `confirmed` + `needs runtime reproduction/policy` | S05 reproduce and decide whether adapter rewrites `repo.yml` or treats listen as unsupported. |
| CLI allowlist/denylist | Full CLI unsafe; minimal allowlist required. | Side-effectful/destructive source paths confirmed for `save`, `join`, `raw`, `kit-update`, and `nuke`. | `confirmed` | S06 adapter contract must enforce denylist and structured logs. |
| `nuke` automated ACP use | Rejected. | Source confirms hook/registry cleanup, git add/commit, and push attempt. | `confirmed` / `rejected` | S06 must keep unreachable in adapter. |
| Raw mirror/backfill | Proof-anchor sensitive. | `cmd_save` calls `raw_mirror::run`; `cmd_raw_backfill` reaches harness path/state/glob flows. | `confirmed` / `blocked by default` | S06 must exclude raw mirror unless explicit sanitized workflow exists. |
| Production provenance | Blocked. | Workflow/plugin scan finds no checksum, attestation, SBOM, cosign/SLSA, signature, provenance, or version markers. | `confirmed` + `needs release recheck` | S07 checks tags/releases/artifacts and keeps source-pinned acquisition unless upgraded. |
| Subtext bundled binaries | Activation path exists, not provenance proof. | `setupHostBinaries` symlinks `bin/.platforms/<target>`; plugin metadata has no provenance manifest. | `confirmed` | S07 should keep plugin binaries research-only unless manifest/attestation found. |
| ACP authority / R035 R037 R038 | Not validated by git-lex. | No git-lex source symbol can validate LegalGraph product/legal/runtime requirements. | `no further work` in source recheck | S08 preserves governance boundary. |
| Main repo `.lex` adoption | Not approved. | All S01 checks kept main `.lex` absent. | `confirmed` / `blocked` | All later runtime slices must use `/tmp` or explicit isolation. |

### Prioritized proof plan for M053

| Priority | Slice | Why it comes next | Proof needed |
|---:|---|---|---|
| 1 | S02 SHACL fail closed wrapper proof | Validation is the highest-value adapter primitive and highest fail-open risk. | Isolated wrapper matrix: positive, negative, skipped/malformed/no-shape/setup failure classes; before/after status; no main `.lex`. |
| 2 | S03 SPARQL-star boundary expansion | Query semantics define what diagnostics an adapter can safely expose. | Positive M052 control plus boundary probes: unsupported quoted-subject forms, non-history graph assumptions, JSON compatibility. |
| 3 | S04 JSON-LD bridge and rejection recheck | JSON-LD is currently rejected; confirm whether to stop or keep ACP-native bridge only. | Source absence proof plus optional runtime absence probe; final bridge/non-goal wording. |
| 4 | S05 serve/viz/listen gap closure | Browser/server surfaces affect operator UX but are not core adapter proof. | HTTP/browser assertions for `/api/store-info` classification and `listen` mismatch reproduction/policy. |
| 5 | S06 minimal adapter harness contract | Should consume S02-S05 results before defining an adapter contract. | Allowlist/denylist, structured logs, cleanup contract, non-authoritative output model; optional isolated harness smoke. |
| 6 | S07 production provenance recheck | Needed before any binary/prebuilt adoption, but not before source-pinned adapter proof. | Tags/releases/artifacts, checksums/signatures/SBOM/attestations/version identity; keep source-pinned default if absent. |
| 7 | S08 synthesis | Final decision point. | Final disposition table, durable guidance updates, browser evidence chunk if browser/server claims appear, validation anchors. |

### S01 final disposition

```text
source contradictions found: none
stale/degraded GitNexus index warnings in S01: none observed
confirmed and routed to runtime proof: SHACL wrapper, SPARQL-star boundary, server/listen gaps
confirmed and routed to source/absence proof: JSON-LD, production provenance
confirmed and routed to adapter contract: CLI allowlist/denylist, raw/nuke/save hazards
no further source recheck: ACP authority and R035/R037/R038 remain governance/product proof questions
```

### T04 verification plan

T04 closeout must verify:

```text
test ! -e .lex
test ! -e Squad
git diff --check
gitnexus_detect_changes({repo:"law-nexus", scope:"all"})
gsd_checkpoint_db
```
