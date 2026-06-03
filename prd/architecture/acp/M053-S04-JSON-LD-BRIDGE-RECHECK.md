# M053 S04 JSON-LD Bridge and Rejection Recheck

## Status

In progress for `M053-2jp3nm / S04`.

S04 rechecks whether JSON-LD remains rejected as a git-lex runtime import/export claim and whether ACP should preserve only an ACP-native static bridge route. This slice does not adopt git-lex runtime and does not treat JSON-LD samples as authoritative proof.

## Guardrails

- Main repository `.lex` must remain absent.
- Main repository `Squad` must remain absent.
- Runtime proof must use isolated `/tmp` repositories only.
- Do not invent unsupported JSON-LD commands.
- Do not confuse `query --json`, `list --json`, `create --json`, JSONL extraction, server JSON APIs, or `.jsonld` file metadata with JSON-LD RDF import/export.
- Do not treat transitive dependency presence as capability proof.
- ACP JSON-LD artifacts are ACP-native static/prototype interchange surfaces unless a real runtime route is implemented and proven.
- R035/R037/R038 are not validated by JSON-LD or git-lex projection evidence.

## Claim taxonomy

| Claim | What would prove it | Current baseline | S04 expected disposition |
|---|---|---|---|
| git-lex imports JSON-LD RDF bodies | Source/help/runtime route that parses `.jsonld` or JSON-LD payload into RDF triples queryable from store. | M052 found no route; body `@id` query returned no rows. | likely `rejected` / `still blocked` |
| git-lex exports JSON-LD RDF graphs | Source/help/runtime route that serializes graph/store data as JSON-LD. | M052 found no route. | likely `rejected` / `still blocked` |
| `.jsonld` file metadata | Git/file metadata tags committed `.jsonld` paths as language `jsonld`. | M052 runtime-backed. | likely `confirmed metadata-only` |
| `query --json` JSON-LD | JSON output is JSON-LD graph serialization. | M052 source says SPARQL Results JSON / non-standard triple JSON, not JSON-LD. | `rejected wording` |
| `oxjsonld` dependency proof | Direct source call path uses JSON-LD parser/serializer. | M052 found only transitive lockfile dependency. | `rejected as proof` unless call path appears |
| ACP static JSON-LD bridge | ACP-owned artifact documents interchange/prototype records without claiming git-lex runtime support. | M051/M052 allow as ACP-native, non-authoritative. | `preserve ACP-native-only` |

## T02 source/help recheck contract

T02 should inspect current git-lex source and help surfaces for:

- JSON-LD terms: `jsonld`, `json_ld`, `JSON-LD`, `application/ld+json`, `ld+json`.
- RDF format routing: `RdfFormat`, `RDFFormat`, `Json`, `NQuads`, `Turtle`.
- User-facing commands and flags: `--json`, `query`, `list`, `create`, `sync`, `dump`, `raw`, `serve`.
- Loader/export paths: `.lex/**/*.nq`, generated git N-Quads, kit TTL, SHACL Turtle, history N-Quads.
- Dependency evidence: direct `Cargo.toml` dependencies versus transitive lockfile packages.

A positive upgrade requires a call path or command surface. A text mention, dependency, file extension branch, or generic JSON output is not enough.

## T02 runtime absence probe contract

If runtime is run, it should:

1. Assert `/root/law-nexus/.lex` and `/root/law-nexus/Squad` are absent before and after.
2. Create a disposable `/tmp` git repository.
3. Run `git-lex init --kit squad` with `PATH=/root/vendor-source/git-lex/target/debug:$PATH`.
4. Commit a file such as `data/m053-s04-sample.jsonld` containing a real JSON-LD `@context` and `@id`.
5. Run `git-lex sync`.
6. Query for `git:language "jsonld"` metadata.
7. Query for the JSON-LD body `@id` as a subject or string match.
8. Classify metadata hit as `metadata-only`.
9. Classify body import hit as a contradiction/upgrade; classify no body rows as runtime absence confirmation.

## Bridge decision rules

| Evidence | Bridge decision |
|---|---|
| No source/help route + metadata-only runtime | Keep ACP JSON-LD bridge as ACP-native static/prototype only; reject git-lex runtime claim. |
| Source/help route appears but runtime body import fails | Mark blocked; needs implementation or deeper runtime debugging. |
| Source/help route and body import/export runtime pass | Upgrade specific route only; still require adapter contract and authority boundaries. |
| Only dependency or generic JSON output appears | Reject as proof; preserve M052 conclusion. |

## Safe wording before T02

Safe:

> M052 found no source-backed or runtime-backed git-lex JSON-LD import/export route. S04 will recheck this and decide whether ACP keeps only its own static JSON-LD bridge.

Safe:

> `.jsonld` file metadata is separate from JSON-LD RDF body import.

Unsafe:

> git-lex supports JSON-LD because `query --json` works.

Unsafe:

> git-lex supports JSON-LD because `oxjsonld` appears in Cargo.lock.

Unsafe:

> ACP JSON-LD samples prove git-lex runtime support.

## T01 conclusion

S04's contract preserves the M052 boundary unless T02 finds a real source/help/runtime route. The expected safe result is an ACP-native static JSON-LD bridge plus continued rejection of git-lex JSON-LD runtime import/export.

## T02: Source/help and runtime absence recheck

### GitNexus recheck

GitNexus query against `git-lex-reference` again surfaced generic query JSON/N-Quads paths rather than JSON-LD import/export paths:

```text
cmd_query -> run_query -> term_to_json
cmd_query -> generate_git_nquads
cmd_query -> load_lex_nquads
```

Relevant GitNexus content confirmed `cmd_query()` loads generated git data and `.lex/**/*.nq` as `RdfFormat::NQuads`, while `run_query()` emits SPARQL Results JSON through `term_to_json`. This is not JSON-LD RDF import/export.

### Source/help/runtime evidence anchor

```text
.gsd/exec/c412f08c-664c-4002-b9d3-405349bc5af5.stdout
```

Runtime probe identity:

```text
binary: /root/vendor-source/git-lex/target/debug/git-lex
binary_sha256: 40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c
workspace: /tmp/m053-s04-jsonld-2ekbb6en
main_lex_after: absent
main_squad_after: absent
```

### Source scan summary

The bounded source scan found 25 hits, all consistent with M052:

| Source surface | Observed evidence | Interpretation |
|---|---|---|
| SHACL/data validation | `RDFFormat::Turtle` in `main.rs` and `shacl.rs` | Turtle support, not JSON-LD. |
| sync/query loaders | `RdfFormat::NQuads` in `main.rs` | N-Quads support, not JSON-LD. |
| kit ontology loading | `RdfFormat::Turtle` in `kit.rs` | TTL ontology support. |
| history loading | `RdfFormat::NQuads` in `spo_events.rs` | N-Quads support. |
| `.jsonld` branch | `nquad.rs:360 Some("jsonld") => Some("jsonld")` | File language metadata only. |
| lockfile | `oxjsonld` in `Cargo.lock` | Transitive dependency only, no source route. |

Classification:

```text
source_jsonld_route_found: false
```

### Help surface recheck

The following commands exited 0 and did not advertise JSON-LD import/export:

| Command | Mentions JSON-LD? | Relevant JSON surface |
|---|---:|---|
| `git-lex --help` | no | none |
| `git-lex query --help` | no | `--json` SPARQL 1.1 JSON Results |
| `git-lex sync --help` | no | `.lex/*.nq` persistent store sync |
| `git-lex dump --help` | no | generated N-Quads |
| `git-lex list --help` | no | JSON array of classes |
| `git-lex create --help` | no | JSON summary |
| `git-lex raw --help` | no | Raw/session JSONL mirror |

Classification:

```text
help_jsonld_surface_found: false
```

### Runtime metadata/body absence probe

The runtime probe created and committed:

```text
data/m053-s04-sample.jsonld
```

with a JSON-LD body containing:

```json
{
  "@id": "urn:m053:s04:jsonld:test",
  "name": "M053 S04 JSON-LD fixture"
}
```

After `git-lex sync`, metadata query returned one binding:

```sparql
SELECT ?file WHERE { ?file git:language "jsonld" } LIMIT 10
```

Observed:

```text
metadata_query.bindings: 1
file: .../data/m053-s04-sample.jsonld
```

Body import queries returned zero bindings:

```sparql
SELECT ?s ?p ?o WHERE { ?s ?p ?o FILTER(CONTAINS(STR(?s), "m053:s04:jsonld")) } LIMIT 10
SELECT ?s ?p ?o WHERE { ?s ?p ?o FILTER(CONTAINS(STR(?o), "M053 S04 JSON-LD fixture")) } LIMIT 10
```

Observed:

```text
body_subject_query.bindings: 0
body_object_query.bindings: 0
```

Runtime classification:

```text
metadata_only_runtime: true
runtime_body_import_observed: false
```

### T02 conclusion

T02 confirms M052 and S01:

```text
JSON-LD runtime import/export: still rejected / unsupported-not-observed
.jsonld file metadata: runtime-backed as git:language tagging only
JSON-LD body RDF import: not observed
query --json/list --json/create --json: generic JSON surfaces, not JSON-LD
oxjsonld: transitive dependency evidence only, not capability proof
main repo safety: .lex absent; Squad absent
```

T03 must now classify the bridge decision for S06/S08: preserve ACP-native static JSON-LD bridge, but do not attribute JSON-LD runtime support to git-lex.

## T03: Final JSON-LD bridge and rejection classification

### Final classification

| Surface | M052 status | M053/S04 result | Final disposition |
|---|---|---|---|
| git-lex JSON-LD RDF import | Unsupported / not present | Source/help route absent; runtime body `@id` query returned zero rows. | `rejected as current runtime claim` |
| git-lex JSON-LD RDF export | Unsupported / not present | Source/help route absent. | `rejected as current runtime claim` |
| `.jsonld` file metadata | Runtime-backed metadata only | Reconfirmed one `git:language "jsonld"` binding. | `confirmed metadata-only` |
| `query --json` | SPARQL Results JSON / diagnostic triple JSON | Help/source still describes generic JSON, not JSON-LD. | `rejected as JSON-LD wording` |
| `list --json` / `create --json` | Generic command JSON | Help says class array / command summary. | `rejected as JSON-LD wording` |
| JSONL raw/session extraction | JSON Lines/session handling | Help/source route is Raw mirror/session flow. | `not JSON-LD` |
| `oxjsonld` | Transitive lockfile dependency | No source/help/runtime call path found. | `rejected as proof` |
| ACP JSON-LD sample/bridge | ACP-native static prototype/interchange | No conflict with git-lex rejection if non-authoritative. | `preserve ACP-native-only` |
| ACP/legal/product proof | Not applicable | No ACP source truth or legal/runtime proof tested. | `not-acp-proof` |

### Did S04 change M052?

```text
M052 JSON-LD runtime rejection: confirmed
M053 upgrade: none for git-lex JSON-LD runtime
M053 preserved bridge: ACP-native static/prototype JSON-LD only
metadata support: confirmed as file-language tagging only
```

S04 therefore resolves the S01 follow-up as a negative confirmation, not an implementation path.

### S06 adapter implications

A minimal git-lex adapter contract should not expose JSON-LD import/export as a git-lex feature. It may include these rules:

1. Treat `.jsonld` files in git-lex query results as file metadata only.
2. Do not pass JSON-LD bodies to git-lex expecting RDF import.
3. Do not label `query --json`, `list --json`, `create --json`, server JSON APIs, or JSONL session extraction as JSON-LD.
4. If ACP needs JSON-LD interchange, keep it in an ACP-native adapter/export layer outside git-lex runtime.
5. If a future implementation adds JSON-LD support, require a new source/help/runtime proof with body import/export and authority-boundary checks.

### S08 synthesis implications

S08 should classify S04 as:

```text
rejected: git-lex JSON-LD RDF import/export runtime claim
confirmed: .jsonld file metadata tagging only
preserved: ACP-native static JSON-LD bridge/prototype files
blocked: attributing ACP JSON-LD bridge to git-lex runtime
```

### Final safe wording

Safe:

> Current git-lex runtime can tag committed `.jsonld` files as file metadata, but S04 found no source/help/runtime route for JSON-LD RDF body import or JSON-LD graph export.

Safe:

> ACP may preserve JSON-LD as an ACP-native static/prototype interchange surface, not as git-lex runtime evidence.

Safe:

> `query --json`, `list --json`, and `create --json` are generic JSON surfaces and must not be described as JSON-LD.

Unsafe:

> git-lex supports JSON-LD because `.jsonld` files appear in graph metadata.

Unsafe:

> git-lex supports JSON-LD because `oxjsonld` appears in `Cargo.lock`.

Unsafe:

> ACP JSON-LD samples prove git-lex JSON-LD runtime support.

### Evidence anchors

```text
prd/architecture/acp/M053-S04-JSON-LD-BRIDGE-RECHECK.md
.gsd/exec/75c0cd6e-ca96-415d-a0f6-ddc7ba694175.stdout
.gsd/exec/c412f08c-664c-4002-b9d3-405349bc5af5.stdout
.gsd/exec/ef68808f-27f0-45c7-8379-9de871ad9a5a.stdout
```

### T03 conclusion

```text
S04 disposition: rejected-runtime-preserve-acp-native
rejected: git-lex JSON-LD RDF import/export runtime support
confirmed: .jsonld file metadata tagging only
preserved: ACP-native static JSON-LD bridge/prototype route
blocked: claiming git-lex JSON-LD support from query --json, oxjsonld, or ACP samples
main repo safety: .lex absent; Squad absent
```
