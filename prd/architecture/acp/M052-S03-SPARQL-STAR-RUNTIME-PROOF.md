# M052 S03 SPARQL-star Runtime Proof

## Status

In progress for `M052-idogd6 / S03`.

S03 resolves whether git-lex supports user-facing SPARQL-star / RDF-star query syntax, and separates that from internal history-graph triple-term machinery.

## Guardrails

- Do not create or mutate `/root/law-nexus/.lex`.
- Runtime proof must run in isolated `/tmp` repositories only.
- Do not reinterpret normal SPARQL named graph queries as SPARQL-star proof.
- Do not treat source-level triple-term serialization as user-facing support until an explicit runtime query passes.
- Record parser errors as blocked/unsupported evidence, not as bypassable noise.

## T01: Source trace of SPARQL-star semantics

### Source paths inspected

| Path | Relevant symbols / lines | Finding |
|---|---|---|
| `/root/vendor-source/git-lex/src/main.rs` | `run_query` lines 2259-2411 | `git-lex query` calls `add_prefixes(query)`, parses with `oxigraph::sparql::Query::parse(&prefixed, None)`, sets default graph as union, then executes against the store. Parse/eval failures exit `1`. |
| `/root/vendor-source/git-lex/src/main.rs` | `term_to_json` lines 2210-2246 | JSON query results explicitly handle `Term::Triple` as non-standard SPARQL JSON with `{ "type": "triple" }`. This proves output serialization can represent RDF 1.2 triple terms if returned by a query. |
| `/root/vendor-source/git-lex/src/main.rs` | `term_to_json_subject` lines 2248-2256 | Comment says this Oxigraph version supports RDF 1.2 triple terms as objects only; quoted-triple subjects are not supported in the subject helper. |
| `/root/vendor-source/git-lex/src/spo_events.rs` | `history_annotation` lines 913-978 | History ingest emits RDF-star style reification: `<ann-uri> rdf:reifies <<( s p o )>> <historyGraph> .` |
| `/root/vendor-source/git-lex/src/main.rs` | `cmd_history_verify` lines 2645-2859 | Reconstructs live triples using an internal SPARQL query pattern: `?ann rdf:reifies <<( ?s ?p ?o )>> .` |
| `/root/vendor-source/git-lex/src/spo_events.rs` | `history_walk_engine` lines 1036+ | Builds annotated triple-term N-Quads for history graph ingest from `.spo` diffs. |

### `git-lex query` parser path

`run_query` does not implement a custom SPARQL parser or a custom SPARQL-star feature flag. It delegates directly to Oxigraph:

```rust
let prefixed = add_prefixes(query);
let mut parsed_query = match oxigraph::sparql::Query::parse(&prefixed, None) { ... };
parsed_query.dataset_mut().set_default_graph_as_union();
let results = match store.query(parsed_query) { ... };
```

Implication:

- If Oxigraph accepts a user-provided SPARQL-star query string, `git-lex query` should parse it through the normal query path.
- If Oxigraph rejects that syntax, `git-lex query` exits `1` with `SPARQL parse error` or JSON parse error output.
- The source does not add a git-lex-specific SPARQL-star compatibility layer.

### Internal RDF-star evidence

Internal history code clearly uses RDF-star / RDF 1.2 triple-term syntax:

```sparql
?ann <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> <<( ?s ?p ?o )>> .
```

and emits N-Quads like:

```text
<ann-uri> rdf:reifies <<( s p o )>> <historyGraph> .
```

This proves git-lex's history subsystem is designed around triple terms, but only for the history graph generated during `sync` / `history-verify`.

### User-facing support hypothesis

The source supports this hypothesis for T02:

```text
Because `git-lex query` uses Oxigraph's normal parser and `history-verify` uses an
Oxigraph-parsed query with `<<( ?s ?p ?o )>>`, explicit user-facing SPARQL-star
queries may parse and run when the history graph contains triple-term annotations.
```

This is only a hypothesis until runtime fixtures run.

### Boundary: internal-only vs user-facing

| Evidence | What it proves | What it does not prove |
|---|---|---|
| `history_annotation` emits `rdf:reifies <<( s p o )>>` | git-lex can generate triple-term history annotations internally | arbitrary user-facing SPARQL-star query contract |
| `cmd_history_verify` parses `<<( ?s ?p ?o )>>` internally | Oxigraph parser path can parse at least this triple-term pattern in source code path | that `git-lex query` works on a synced repo with user-provided syntax |
| `term_to_json` handles `Term::Triple` | query result serialization can print triple terms | that a query will actually return triple terms |
| `term_to_json_subject` comment | current model does not support quoted-triple subjects in JSON subject helper | full RDF-star feature parity |
| `run_query` uses Oxigraph directly | no custom blocker visible in git-lex query path | no proof of runtime success without T02 |

### T01 classification

```text
Internal RDF-star/triple-term machinery: source-backed
User-facing SPARQL-star query support: source-plausible but not runtime-proven
Quoted-triple subject support: likely limited by current Oxigraph model/helper comment
Required next proof: isolated repo with synced history graph and explicit SELECT/ASK SPARQL-star fixtures
```

### T01 verification

This report intentionally separates:

1. internal history RDF-star generation and verification;
2. user-facing `git-lex query` parser/runner behavior;
3. output serialization for `Term::Triple`;
4. the open runtime question for S03/T02.

## T02: Explicit SPARQL-star runtime query matrix

### Runtime workspace

Final successful isolated workspace:

```text
/tmp/m052-s03-sparqlstar-7eyyo_vd
```

Evidence anchor:

```text
.gsd/exec/e7418ecc-ce38-4ec7-8acc-253bd5f6e7c8.stdout
```

Safety note: an earlier fixture-script attempt accidentally wrote untracked `Squad/` and `.lex/` fixture paths in the main repository because relative `Path(...)` calls were not rooted in `/tmp`. The files were inspected, identified as only the test fixture (`Squad/Bug/BugOne.md` and `.lex/extract/Squad/Bug/BugOne.md.spo`), removed, and final proof re-ran with explicit workspace-rooted paths. Final safety checks show `/root/law-nexus/.lex` and `/root/law-nexus/Squad` absent.

### Fixture setup

The final runtime proof created a disposable git repository, initialized git-lex with the squad kit, then force-added one `.spo` sidecar because `.lex` paths are ignored by default:

```text
A  .lex/extract/Squad/Bug/BugOne.md.spo
A  Squad/Bug/BugOne.md
```

The sidecar contained simple facts:

```text
BugOne | isA | Bug
BugOne | mentions | ThingOne
```

`git-lex sync` result:

```text
Sync /sync/565ad4e1/: +21 assertions, -0 retracted (126 quads)
History: 4 commit(s), 21 events, 27 annotations
Store: /tmp/m052-s03-sparqlstar-7eyyo_vd/.git/lex/oxigraph
```

`git-lex history-verify` exited `0`, so the history graph was populated enough for SPARQL-star query fixtures.

### Runtime query results

#### Control: bind triple terms normally

Query:

```sparql
SELECT ?ann ?t WHERE {
  ?ann <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> ?t
}
LIMIT 10
```

Result:

```text
exit: 0
10 results in persistent store
```

This confirms the history graph contains `rdf:reifies` triple-term objects.

#### Explicit SPARQL-star SELECT

Query:

```sparql
SELECT ?ann ?s ?p ?o WHERE {
  ?ann <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> <<( ?s ?p ?o )>> .
}
LIMIT 10
```

Result:

```text
exit: 0
10 results in persistent store
```

Interpretation:

- User-facing `git-lex query` accepted explicit `<<( ?s ?p ?o )>>` syntax.
- This is SPARQL-star/RDF 1.2 triple-term pattern proof for the observed Oxigraph/git-lex runtime.
- It is not merely an internal `history-verify` source path.

#### Explicit SPARQL-star ASK

Query:

```sparql
ASK {
  ?ann <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> <<( ?s ?p ?o )>> .
}
```

Result:

```text
exit: 0
stdout: true
```

Interpretation:

- Boolean SPARQL-star pattern matching works against the synced history graph.

#### Triple-term JSON binding

Query:

```sparql
SELECT ?t WHERE {
  ?ann <http://www.w3.org/1999/02/22-rdf-syntax-ns#reifies> ?t
}
LIMIT 10
```

Command used `--json`.

Result excerpt:

```json
{"t":{"type":"triple","value":{"subject":{"type":"uri"},"predicate":{"type":"uri"},"object":{"type":"literal"}}}}
```

Summary from the proof script:

```text
sparql_star_json_t_types=['triple', 'triple', 'triple', 'triple', 'triple', 'triple', 'triple', 'triple', 'triple', 'triple']
```

Interpretation:

- `term_to_json()`'s `Term::Triple` branch is runtime-observed, not just source-dead code.
- JSON output is explicitly non-standard SPARQL 1.1 JSON for this binding shape, as source comments already warned.

#### Quoted triple as subject probe

Query:

```sparql
SELECT ?p ?o WHERE {
  <<( <urn:a> <urn:b> <urn:c> )>> ?p ?o
}
LIMIT 1
```

Result:

```text
exit: 0
stdout: (No results found)
```

Interpretation:

- This query parsed and executed, but the fixture did not contain such a quoted-triple-subject assertion.
- It does not prove subject-position triple-term storage support.
- T01 source comments still require caution around quoted-triple subjects in output/helper paths.

### T02 classification

```text
User-facing SPARQL-star triple-term pattern queries over history graph: runtime-backed for observed SELECT and ASK fixtures
Triple-term JSON result serialization: runtime-backed for `?t` bindings, with non-standard JSON shape
Full RDF-star/SPARQL-star parity: not proven
Quoted-triple subject storage/query contract: not proven by this fixture
ACP implication: SPARQL-star may be cited only for git-lex history graph `rdf:reifies <<( ?s ?p ?o )>>` query patterns, not as broad RDF-star feature parity
```

### T02 verification

- Final proof script exited `0`.
- Final proof used `/tmp/m052-s03-sparqlstar-7eyyo_vd` only.
- Final proof asserted `/root/law-nexus/.lex` and `/root/law-nexus/Squad` were absent before and after.
- `git status --short -- prd/architecture/acp/M052-S03-SPARQL-STAR-RUNTIME-PROOF.md .lex Squad` shows only the intended new report file.

## T03: ACP query contract classification

### Final support classification

| Capability | Classification | Evidence |
|---|---|---|
| Internal history graph triple-term generation | source-backed and runtime-observed | `history_annotation`, `sync`, history graph query results. |
| User-facing SPARQL-star SELECT over history annotations | runtime-backed, narrow | T02 explicit `SELECT ?ann ?s ?p ?o WHERE { ?ann rdf:reifies <<( ?s ?p ?o )>> . }` exited `0` and returned rows. |
| User-facing SPARQL-star ASK over history annotations | runtime-backed, narrow | T02 explicit `ASK { ?ann rdf:reifies <<( ?s ?p ?o )>> . }` exited `0` and returned `true`. |
| Triple-term result serialization via `query --json` | runtime-backed, non-standard JSON shape | T02 returned ten `{"type":"triple"}` bindings. |
| Full RDF-star/SPARQL-star parity | not proven | Only history-graph triple-term patterns were tested. |
| Quoted-triple subject storage/query contract | not proven | Probe parsed but had no fixture-backed matching data; source helper comments still require caution. |
| Production support | not proven | T02 used source-built debug binary and disposable repo only. |

### ACP guidance

Safe wording:

```text
git-lex user-facing SPARQL-star support is runtime-backed for history-graph
`rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK patterns in the observed build.
```

Safe wording:

```text
`query --json` can serialize returned triple terms as a non-standard
`{"type":"triple"}` binding shape.
```

Unsafe wording:

```text
git-lex has full RDF-star/SPARQL-star feature parity.
```

Unsafe wording:

```text
SPARQL-star support is proven for ACP source/proof gates generally.
```

Unsafe wording:

```text
Quoted-triple subject semantics are proven.
```

### Durable guidance update

Updated:

```text
.agents/skills/git-lex/references/ontology-map.md
```

The new guidance records M052/S03 as a narrow upgrade: history-graph `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK patterns are runtime-backed, but broad RDF-star parity remains unproven.

### S03 conclusion

S03 resolves the M051 SPARQL-star gap positively but narrowly. The correct classification is:

```text
SPARQL-star user-facing query support: upgraded for git-lex history graph triple-term SELECT/ASK patterns
Full RDF-star/SPARQL-star support: still blocked / not proven
ACP production/adoption implication: query guidance may cite the narrow pattern only; it cannot validate ACP source authority, legal evidence, or proof gates by itself
```
