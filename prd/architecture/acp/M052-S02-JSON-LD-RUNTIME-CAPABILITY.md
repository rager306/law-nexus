# M052 S02 JSON-LD Runtime Capability Proof

## Status

In progress for `M052-idogd6 / S02`.

This artifact determines whether git-lex supports JSON-LD at runtime or whether JSON-LD remains an ACP-native static interchange/prototype surface only.

## T01: Source trace of JSON-LD support

### Scope

T01 traces source and dependency evidence only. It does not run new runtime JSON-LD import/export attempts and does not create or mutate `/root/law-nexus/.lex`.

Safety check before T01:

```text
main_lex_absent=0  # shell test exit code for `test ! -e .lex`; 0 means absent
```

### GitNexus and source search method

GitNexus queries used repo `git-lex-reference` with JSON-LD / RDF format / parser / serializer terms. Source search additionally inspected:

```text
/root/vendor-source/git-lex/src
/root/vendor-source/git-lex/Cargo.toml
/root/vendor-source/git-lex/Cargo.lock
/root/vendor-source/git-lex/README.md
```

Search terms included:

```text
JSON-LD, jsonld, json_ld, application/ld, RDFFormat::Json, RDFFormat, json
```

### Source anchors

| Surface | Source anchor | Finding |
|---|---|---|
| CLI command flags | `/root/vendor-source/git-lex/src/main.rs:70-160` | User-facing JSON flags are `query --json`, `list --json`, and `create --json`. Their documentation says SPARQL JSON Results, JSON array, or JSON summary; none mention JSON-LD. |
| Command dispatch | `/root/vendor-source/git-lex/src/main.rs:2450-2507` | Commands route to init/create/list/save/query/dump/extract/validate/hook/join/parse/nuke/kit-update/display/serve/history-verify/sync/raw. No JSON-LD import/export command exists. |
| Query store loading | `/root/vendor-source/git-lex/src/main.rs:2413-2446` | `cmd_query()` loads persistent store or fallback in-memory data from generated git N-Quads and `.lex/**/*.nq`; it does not load JSON-LD. |
| Query JSON output | `/root/vendor-source/git-lex/src/main.rs:2209-2399` | `query --json` emits W3C SPARQL 1.1 JSON Results for SELECT/ASK and a non-standard nested JSON representation for RDF triple terms. It is not JSON-LD. |
| Sync store loading | `/root/vendor-source/git-lex/src/main.rs:1706-1982` | Sync loads `RdfFormat::NQuads` for git/frontmatter/sync data. No JSON-LD format is loaded in the traced sync path. |
| Lex graph loading | `/root/vendor-source/git-lex/src/nquad.rs:378-411` | `load_lex_nquads()` recursively reads only `.lex/**/*.nq`. It does not read `.jsonld`, `.json`, `.ttl`, or `.spo` as RDF input. |
| Generated git file metadata | `/root/vendor-source/git-lex/src/nquad.rs:330-366` | Files ending `.jsonld` are tagged with git language `jsonld`. This is file metadata only, not JSON-LD parsing/import. |
| Kit ontology loading | `/root/vendor-source/git-lex/src/kit.rs:18`, `:171` | Kit ontologies are loaded using `RdfFormat::Turtle`. This is ontology TTL support, not JSON-LD. |
| SHACL validation RDF parsing | `/root/vendor-source/git-lex/src/main.rs:1299-1351` | SHACL shapes and generated document data use `rudof_rdf::RDFFormat::Turtle`. No JSON-LD validation path appears. |
| History loading | `/root/vendor-source/git-lex/src/spo_events.rs:1213-1229` | History events are loaded as `oxigraph::io::RdfFormat::NQuads`. |
| JSONL extractor | `/root/vendor-source/git-lex/src/extraction.rs:277-371` | Extracts Claude Code `.jsonl` session files for a kit-specific sidecar workflow. JSONL is not JSON-LD. |
| Serve JSON APIs | `/root/vendor-source/git-lex/src/bin/git-lex-serve.rs:65-350` | Server exposes JSON payloads/results for UI/API, not JSON-LD RDF import/export. |
| Dependencies | `/root/vendor-source/git-lex/Cargo.toml:31` | Direct JSON dependency is `serde_json = "1"`; no direct JSON-LD crate is declared. |
| Transitive lockfile | `/root/vendor-source/git-lex/Cargo.lock` | `oxjsonld` appears transitively through RDF/Oxigraph-related dependencies. No source route in git-lex was found that calls JSON-LD parser/serializer APIs. |

### GitNexus trace summary

GitNexus found relevant runtime JSON paths only around generic JSON output and query behavior:

```text
proc_70_cmd_query: Cmd_query -> Term_to_json
cmd_query -> run_query
cmd_query -> generate_git_nquads
cmd_query -> load_lex_nquads
```

No GitNexus flow showed a JSON-LD import/export command path.

The most relevant GitNexus/content result was `cmd_query`, which confirms fallback loading uses generated N-Quads and `.lex/**/*.nq`:

```rust
store.load_from_reader(RdfFormat::NQuads, Cursor::new(git_nq.as_bytes()))
...
store.load_from_reader(RdfFormat::NQuads, Cursor::new(lex_nq.as_bytes()))
```

### JSON vs JSON-LD distinction

The source contains several JSON surfaces that are easy to misread as JSON-LD support:

| Surface | What it is | What it is not |
|---|---|---|
| `query --json` | W3C SPARQL 1.1 JSON Results for SELECT/ASK. | Not JSON-LD RDF graph serialization. |
| `list --json` | JSON array of classes from installed shapes. | Not JSON-LD context/compaction/expansion. |
| `create --json` | JSON command summary with path/uri/class/id. | Not JSON-LD document generation. |
| `git-lex-serve` JSON API | UI/API payloads and SPARQL result JSON. | Not JSON-LD endpoint. |
| `.jsonl` extraction | Claude Code/session JSON Lines parsing. | Not JSON-LD. |
| `.jsonld` language tag | File extension classified as `git:language "jsonld"`. | Not parsing, importing, validating, querying, or exporting JSON-LD. |
| `oxjsonld` in lockfile | Transitive dependency availability. | Not proof that git-lex exposes JSON-LD behavior. |

### T01 conclusion

No source-backed git-lex runtime JSON-LD route was found.

Current classification:

```text
JSON-LD runtime support: source-rejected / unsupported by observed CLI and loader paths
```

What is supported instead:

- Turtle for kit ontology and SHACL/data validation paths.
- N-Quads for generated git/frontmatter/sync/history/store loading.
- W3C SPARQL JSON Results for `query --json` SELECT/ASK.
- Generic JSON/JSONL handling for command summaries, UI APIs, raw session extraction, and local state.
- `.jsonld` file extension language tagging as metadata.

T02 should therefore avoid inventing a JSON-LD import/export command. The correct runtime check is an absence proof over user-facing help/command surfaces and, optionally, a controlled `.jsonld` file metadata check showing that git-lex can tag a file as `jsonld` language without parsing it as JSON-LD RDF.

Until proven otherwise, ACP S08 JSON-LD sample records remain **ACP-native static interchange artifacts**, not git-lex runtime evidence.

## T02: Runtime absence proof and `.jsonld` metadata check

### Scope and safety

T02 did not invent unsupported JSON-LD commands. It ran user-facing help checks and a controlled isolated metadata test in `/tmp`.

Runtime evidence anchor:

```text
.gsd/exec/f69474d4-239d-466e-8206-14088173c214.stdout
```

Runtime workspace:

```text
/tmp/m052-s02-jsonld-absence-o7r52_bg
```

Main repository safety:

```text
main_lex_before: False
main_lex_after: False
```

No `/root/law-nexus/.lex` state was created.

### User-facing help absence proof

The following help commands exited `0` and did not expose JSON-LD import/export options:

| Command | Exit | JSON-LD import/export surface? |
|---|---:|---|
| `git-lex --help` | 0 | none |
| `git-lex query --help` | 0 | none; only SPARQL string and `--json` SPARQL Results JSON |
| `git-lex sync --help` | 0 | none; says `Sync git data + .lex/*.nq into the persistent store` |
| `git-lex dump --help` | 0 | none; says generated N-Quads |
| `git-lex list --help` | 0 | none; `--json` emits class array |
| `git-lex create --help` | 0 | none; `--json` emits command summary |
| `git-lex raw --help` | 0 | none; manages Raw/ harness-session mirror, including JSONL sessions |

This confirms there is no advertised runtime JSON-LD import/export command surface in the tested binary.

### Isolated `.jsonld` metadata check

T02 created an isolated squad repo and committed:

```text
data/sample.jsonld
```

The file body contained real-looking JSON-LD:

```json
{
  "@context": {"name": "http://schema.org/name"},
  "@id": "urn:m052:jsonld:test",
  "name": "M052 JSON-LD fixture"
}
```

Then T02 ran:

```text
git-lex sync
```

Result:

```text
exit: 0
Virtual: 392 git + 60 now
Sync /sync/5dec2fc5/: +17 assertions, -0 retracted (102 quads)
History: 3 commit(s), 17 events, 21 annotations
Store: /tmp/m052-s02-jsonld-absence-o7r52_bg/.git/lex/oxigraph
```

Query for file metadata:

```sparql
SELECT ?file ?lang WHERE { ?file git:language "jsonld" } LIMIT 10
```

Result:

```json
{"head":{"vars":["file","lang"]},"results":{"bindings":[{"file":{"type":"uri","value":"https://localhost/local/m052-s02-jsonld-absence-o7r52_bg/tree/5dec2fc55932fe6fb42e40585d9e971953c212b8/data/sample.jsonld"}}]}}
```

Interpretation:

- git-lex recognizes `.jsonld` as file language metadata via git tree extraction.
- The returned binding omits `?lang` in the JSON result because the query pattern fixed `git:language "jsonld"`; the file URI binding is enough to prove the language-tagged file metadata exists.
- This is not JSON-LD RDF parsing.

### Body import absence check

T02 also queried for RDF facts derived from the JSON-LD body ID:

```sparql
SELECT ?s ?p ?o WHERE { ?s ?p ?o FILTER(CONTAINS(STR(?s), "m052:jsonld")) } LIMIT 10
```

Result:

```json
{"head":{"vars":["s","p","o"]},"results":{"bindings":[]}}
```

Interpretation:

- The JSON-LD file body was not imported as RDF into the git-lex store.
- The `@id` value `urn:m052:jsonld:test` did not become a queryable subject.
- This matches source trace: git-lex generated git/file metadata and N-Quads from its own extractors, but no JSON-LD parser route was used.

### T02 conclusion

Runtime evidence supports the source conclusion:

```text
JSON-LD runtime import/export: unsupported / not present in tested CLI surfaces
.jsonld file metadata: runtime-backed as git:language tagging only
JSON-LD body RDF import: not observed; query returned 0 rows
```

Therefore JSON-LD remains blocked as a git-lex runtime claim. ACP may keep static JSON-LD artifacts only as ACP-native interchange/prototype evidence unless a future implementation adds or proves a JSON-LD route.

## T03: ACP static JSON-LD boundary reconciliation

### ACP S08 baseline

M051/S08 created:

```text
prd/architecture/acp/examples/M051-ACP-SAMPLE-RECORDS.jsonld
```

S08 explicitly classified it as:

```text
JSON-LD is included as a proposed interchange surface for the ACP prototype,
but remains non-authoritative and not runtime-verified by git-lex.
```

The JSON-LD sample contains an ACP context for `acp`, `ex`, `lex`, `git`, `fm`, `rdfs`, and `xsd`, plus sample records for requirement, decision, evidence anchor, proof gate, health finding, projection, runtime adapter, and R035/R037/R038 non-validation examples.

### Reconciliation with M052 evidence

| Claim | M051/S08 status | M052/S02 evidence | Final classification |
|---|---|---|---|
| ACP can keep static JSON-LD sample records | proposed, non-authoritative | No conflict; sample is ACP-owned file, not git-lex runtime output | ACP-native static interchange/prototype |
| git-lex imports JSON-LD RDF bodies | unproven | Source has no route; runtime query for JSON-LD body `@id` returned 0 rows | unsupported / not proven |
| git-lex exports JSON-LD | unproven | No CLI/help/source route found | unsupported / not proven |
| git-lex recognizes `.jsonld` files | not previously separated | Runtime query returned `data/sample.jsonld` as `git:language "jsonld"` metadata | runtime-backed file metadata only |
| `query --json` is JSON-LD | no | Source/help says SPARQL 1.1 JSON Results | reject as wording |
| Transitive `oxjsonld` means git-lex supports JSON-LD | no | Lockfile-only dependency, no source route found | reject as proof |

### Safe claim language

Safe:

```text
git-lex can tag committed `.jsonld` files as `git:language "jsonld"` metadata,
but current source and runtime proof do not show JSON-LD RDF import/export.
ACP JSON-LD artifacts remain ACP-native static interchange/prototype files.
```

Safe:

```text
M052/S02 found no user-facing git-lex JSON-LD import/export command. JSON-LD
support remains blocked as a git-lex runtime claim.
```

Unsafe:

```text
git-lex supports JSON-LD because `query --json` works.
```

Unsafe:

```text
git-lex supports JSON-LD because `oxjsonld` appears in Cargo.lock.
```

Unsafe:

```text
ACP S08 JSON-LD samples prove git-lex JSON-LD runtime support.
```

### Final S02 classification

```text
JSON-LD runtime support: blocked / unsupported by current git-lex source and runtime proof
.jsonld file metadata: runtime-backed as git tree language tagging
ACP JSON-LD sample records: ACP-native static interchange/prototype, non-authoritative
Production/adoption implication: no git-lex JSON-LD claim unless a future route is implemented or independently proven
```

### S02 conclusion

S02 resolves the M051 JSON-LD gap negatively. The result is not “untested” anymore: current git-lex runtime does **not** provide source-backed or help-backed JSON-LD import/export, and the isolated runtime check showed metadata tagging only. ACP may continue to use JSON-LD for its own static prototype/interchange files, but must not attribute that support to git-lex.
