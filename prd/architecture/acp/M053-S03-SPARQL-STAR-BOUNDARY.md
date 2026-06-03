# M053 S03 SPARQL-star Boundary Expansion

## Status

In progress for `M053-2jp3nm / S03`.

S03 tests whether M052's narrow SPARQL-star classification can be expanded, or whether it should remain bounded to git-lex history graph `rdf:reifies <<( ?s ?p ?o )>>` patterns.

## Guardrails

- Main repository `.lex` must remain absent.
- Main repository `Squad` must remain absent.
- Runtime proof must use isolated `/tmp` repositories only.
- Do not reinterpret ordinary named-graph SPARQL as SPARQL-star proof.
- Do not treat parser success with no fixture-backed data as semantic support.
- Do not treat non-standard JSON triple bindings as standard SPARQL 1.1 JSON.
- git-lex query output is derived diagnostic evidence, not ACP source truth.
- R035/R037/R038 are not validated by this proof.

## Baseline from M052 and S01

M052/S03 established:

```text
SPARQL-star user-facing query support: runtime-backed for git-lex history graph triple-term SELECT/ASK patterns.
Triple-term JSON result serialization: runtime-backed, but with non-standard {"type":"triple"} binding shape.
Full RDF-star/SPARQL-star parity: not proven.
Quoted-triple subject semantics: not proven.
```

S01 rechecked source and confirmed:

```text
cmd_query -> run_query -> term_to_json
run_query delegates parsing to Oxigraph and does not add a git-lex-specific compatibility layer.
term_to_json has a runtime-relevant Term::Triple branch.
Broad RDF-star parity remains blocked unless runtime evidence expands it.
```

## Classification vocabulary

| Classification | Meaning |
|---|---|
| `runtime-backed` | Query exits 0 and returns fixture-backed rows or boolean evidence matching the tested claim. |
| `runtime-backed-nonstandard-json` | Query exits 0 and returns triple bindings, but in git-lex's non-standard JSON shape. |
| `no-match-only` | Query parses and executes but returns no rows because fixture data does not contain such facts; this is parser/runner evidence, not semantic support. |
| `parser-rejected` | Query exits non-zero with parse error; pattern is unsupported in the observed runtime. |
| `blocked` | Result is ambiguous, setup failed, or cannot support a safe claim. |
| `not-acp-proof` | Query behavior may be useful diagnostically but cannot validate ACP source truth or legal/product requirements. |

## Boundary matrix for T02

| Row | Query pattern | Purpose | Upgrade condition | Expected safe classification |
|---|---|---|---|---|
| positive SELECT control | `?ann rdf:reifies <<( ?s ?p ?o )>>` | Reproduce M052 positive control on a fresh workspace. | Exit 0 and rows > 0. | `runtime-backed` |
| positive ASK control | `ASK { ?ann rdf:reifies <<( ?s ?p ?o )>> }` | Reproduce boolean history graph support. | Exit 0 and `true`. | `runtime-backed` |
| triple binding JSON | `SELECT ?t WHERE { ?ann rdf:reifies ?t }` with `--json` | Confirm `Term::Triple` output shape. | JSON bindings contain `type: triple`. | `runtime-backed-nonstandard-json` |
| quoted subject probe | `<<( <urn:a> <urn:b> <urn:c> )>> ?p ?o` | Check parser/runner behavior for quoted triple in subject position. | Rows only if fixture explicitly supports it; parser success alone is not support. | `no-match-only` or `blocked`; upgrade only with fixture-backed rows. |
| nonexistent history triple | `?ann rdf:reifies <<( <urn:no-s> <urn:no-p> <urn:no-o> )>>` | Distinguish valid syntax/no result from support expansion. | Exit 0 and zero rows. | `no-match-only` |
| nested quoted triple | `?ann rdf:reifies <<( <<( ?s ?p ?o )>> ?p2 ?o2 )>>` | Probe unsupported/nested RDF-star forms. | Exit 1 parse error or blocked ambiguity. | `parser-rejected` or `blocked` |
| legacy double-angle syntax without parentheses | `<< ?s ?p ?o >>` | Check whether only RDF 1.2 `<<(...)>>` syntax is supported. | Exit 1 parse error if unsupported. | `parser-rejected` |
| construct/update-style probe | `CONSTRUCT { <<( ?s ?p ?o )>> ?p2 ?o2 } WHERE { ... }` | Avoid overclaiming query forms beyond SELECT/ASK. | Only upgrade if parse and output are interpretable. | likely `blocked` unless clearly supported. |

## Upgrade rules

M053 may expand beyond M052 only if a row has fixture-backed runtime evidence:

1. The workspace contains data that should match the pattern.
2. `git-lex query` exits 0.
3. The output contains rows or `true` proving the specific pattern.
4. The report names the exact query and output anchor.

Parser success with no matching fixture data is not an upgrade. It is only a syntax/no-match observation.

Parser failure is useful negative evidence and should be recorded as `parser-rejected`, not bypassed.

## Safe wording before T02

Safe:

> M052 proved user-facing SPARQL-star only for git-lex history graph `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK patterns. S03 will test whether additional patterns are supported.

Safe:

> Triple-term JSON bindings are currently treated as git-lex diagnostic JSON, not standard SPARQL 1.1 JSON.

Unsafe:

> git-lex supports full RDF-star/SPARQL-star parity.

Unsafe:

> A query that parses but returns no rows proves quoted-triple subject semantics.

Unsafe:

> SPARQL-star support validates ACP proof gates or Russian legal evidence.

## T01 conclusion

S03's matrix is intentionally conservative. It can expand the M052 claim only with fixture-backed runtime rows; otherwise it should preserve narrow support and record parser-rejected or no-match-only boundaries.

## T02: Isolated SPARQL-star boundary matrix

### Scope and safety

T02 ran only in disposable `/tmp` repositories using the source-built debug binary:

```text
binary: /root/vendor-source/git-lex/target/debug/git-lex
binary_sha256: 40ac81758a85e672a7774442add493c5e8c59ce58f945526197a11a8818a229c
workspace_root: /tmp/m053-s03-sparqlstar-mi33ro1q
main_lex_after: absent
main_squad_after: absent
```

Successful adjusted matrix evidence:

```text
.gsd/exec/61770074-e38a-4f17-8df2-f5dd322dd766.stdout
```

Useful failed-expectation evidence:

```text
.gsd/exec/2de7bd53-fc9f-4236-b943-a54f40f165c9.stdout
```

The first matrix expected nested and legacy syntax to be parser-rejected. Runtime showed they parsed and returned zero rows. The adjusted matrix therefore classifies them as `no-match-only`, not support upgrades.

### Fixture setup

The successful matrix created a disposable `squad` repo, committed a markdown fixture plus forced `.spo` sidecar, ran `git-lex sync`, and verified history equivalence:

```text
sync: +22 assertions, 132 quads, 4 commits, 22 events, 29 annotations
history-verify: ✓ history == now. the equivalence invariant holds.
```

### Runtime matrix result

| Row | Query surface | Exit | Result count | Classification | Interpretation |
|---|---|---:|---:|---|---|
| positive SELECT | `?ann rdf:reifies <<( ?s ?p ?o )>>` | 0 | 5 | `runtime-backed` | Reconfirms M052 user-facing history graph SELECT support. |
| positive ASK | `ASK { ?ann rdf:reifies <<( ?s ?p ?o )>> }` | 0 | 1 / `true` | `runtime-backed` | Reconfirms M052 boolean support. |
| triple JSON | `SELECT ?t WHERE { ?ann rdf:reifies ?t } --json` | 0 | 5 | `runtime-backed-nonstandard-json` | Reconfirms `type: triple` diagnostic JSON binding. |
| quoted subject probe | `<<( <urn:a> <urn:b> <urn:c> )>> ?p ?o` | 0 | 0 | `no-match-only` | Parser/runner accepts syntax, but no fixture-backed quoted-subject data. |
| nonexistent history triple | `rdf:reifies <<( <urn:no-s> <urn:no-p> <urn:no-o> )>>` | 0 | 0 | `no-match-only` | Valid no-match control; not an expansion. |
| nested quoted triple | `rdf:reifies <<( <<( ?s ?p ?o )>> ?p2 ?o2 )>>` | 0 | 0 | `no-match-only` | Contrary to initial expectation, syntax parsed; zero rows prevent support claim. |
| legacy no-parentheses syntax | `rdf:reifies << ?s ?p ?o >>` | 0 | 0 | `no-match-only` | Contrary to initial expectation, syntax parsed; zero rows prevent support claim. |
| CONSTRUCT quoted subject | `CONSTRUCT { <<( ?s ?p ?o )>> ?p2 ?o2 } WHERE ...` | 0 | 0 | `blocked` | git-lex prints `CONSTRUCT/DESCRIBE queries not yet supported in output`. |

### Key observed outputs

#### Positive SELECT

```text
5 results in 8.2ms (persistent store)
classification: runtime-backed
```

#### Positive ASK

```text
true
1 results in 5.9ms (persistent store)
classification: runtime-backed
```

#### Triple JSON

```json
{"t":{"type":"triple","value":{"object":{"type":"literal","value":"M053-SPARQLSTAR-BUG-1"}, ... }}}
```

```text
json_t_types: ["triple", "triple", "triple", "triple", "triple"]
classification: runtime-backed-nonstandard-json
```

#### No-match-only boundary rows

```text
(No results found)
0 results ...
classification: no-match-only
```

This was observed for quoted-subject probe, nonexistent history triple, nested quoted triple, and legacy no-parentheses syntax.

#### CONSTRUCT boundary

```text
CONSTRUCT/DESCRIBE queries not yet supported in output
classification: blocked
```

### What T02 upgrades

T02 does not expand git-lex into broad RDF-star/SPARQL-star parity. It does sharpen M052:

- M052 positive history graph SELECT/ASK support remains reproducible.
- Triple-term JSON support remains reproducible and non-standard.
- Some additional quoted-triple syntaxes parse and execute but return no rows; they are syntax/no-match observations only.
- CONSTRUCT/DESCRIBE output remains blocked in git-lex query output.

### What remains bounded

- No fixture-backed quoted-triple subject storage/query semantics were proven.
- No nested quoted-triple semantics were proven.
- No legacy `<< ?s ?p ?o >>` semantic support was proven.
- No CONSTRUCT/DESCRIBE adapter output contract was proven.
- No ACP proof-gate, legal evidence, production, or R035/R037/R038 claim was advanced.

T03 must now classify whether S03 leaves the M052 claim unchanged or adds the no-match-only parser/runner boundary observations as useful diagnostics.

## T03: Final SPARQL-star boundary classification

### Final classification

| Surface | M052 status | M053/S03 result | Final disposition |
|---|---|---|---|
| History graph `rdf:reifies <<( ?s ?p ?o )>>` SELECT | Runtime-backed narrow | Reproduced with 5 rows in fresh isolated workspace. | `confirmed runtime-backed` |
| History graph `rdf:reifies <<( ?s ?p ?o )>>` ASK | Runtime-backed narrow | Reproduced `true` in fresh isolated workspace. | `confirmed runtime-backed` |
| Triple-term JSON binding | Runtime-backed, non-standard | Reproduced five `type: triple` bindings. | `confirmed runtime-backed-nonstandard-json` |
| Quoted-triple subject query | Not proven | Parsed and returned zero rows without fixture-backed data. | `no-match-only`; not support proof |
| Nonexistent history triple | Not applicable control | Parsed and returned zero rows. | `no-match-only` control |
| Nested quoted triple | Not proven | Parsed and returned zero rows. | `no-match-only`; not support proof |
| Legacy no-parentheses `<< ?s ?p ?o >>` | Not proven | Parsed and returned zero rows. | `no-match-only`; not support proof |
| CONSTRUCT/DESCRIBE output | Not proven | Query path printed `CONSTRUCT/DESCRIBE queries not yet supported in output`. | `blocked` |
| Full RDF-star/SPARQL-star parity | Blocked | No fixture-backed evidence beyond history graph pattern. | `still blocked` |
| ACP proof-gate relevance | Not applicable | Query behavior remains derived diagnostic evidence. | `not-acp-proof` |

### Did S03 expand M052?

```text
M052 narrow support: confirmed
M053 expansion beyond M052: no semantic support expansion
M053 added value: no-match-only boundary observations and explicit CONSTRUCT output block
```

S03 does **not** upgrade git-lex to broad RDF-star/SPARQL-star support. It preserves the M052 narrow claim and adds a safer adapter interpretation:

- `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK over the git-lex history graph is runtime-backed.
- `query --json` can return diagnostic triple bindings in git-lex's non-standard JSON shape.
- Additional quoted/nested/legacy syntaxes may parse, but without fixture-backed rows they are no-match-only observations.
- CONSTRUCT/DESCRIBE output is blocked by git-lex query output handling.

### S06 adapter implications

A minimal adapter contract may expose SPARQL-star diagnostics only under these constraints:

1. Limit supported query templates to history graph `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK patterns unless later fixture-backed proof expands them.
2. Treat `type: triple` JSON as git-lex diagnostic JSON and normalize it before any downstream consumer assumes SPARQL 1.1 JSON compatibility.
3. Do not expose quoted-subject, nested quoted-triple, legacy no-parentheses, CONSTRUCT, or DESCRIBE patterns as supported adapter surfaces.
4. Preserve raw query, exit code, result count, output mode, and classification in structured logs.
5. Mark no-match-only rows as parser/runner observations, not semantic support.
6. Keep all query results non-authoritative: they may support diagnostics and recovery views, not ACP source truth or legal evidence validation.

### S08 synthesis implications

S08 should record S03 as:

```text
confirmed: M052 narrow SPARQL-star history graph SELECT/ASK support
confirmed: non-standard triple JSON diagnostic binding
new boundary: quoted/nested/legacy syntaxes parsed to no rows in this fixture but did not prove semantic support
blocked: CONSTRUCT/DESCRIBE output and broad RDF-star/SPARQL-star parity
```

### Final safe wording

Safe:

> git-lex user-facing SPARQL-star support is runtime-backed for history graph `rdf:reifies <<( ?s ?p ?o )>>` SELECT/ASK patterns in isolated smoke tests.

Safe:

> git-lex `query --json` can emit triple-term bindings as non-standard diagnostic JSON with `type: triple`.

Safe:

> Some additional quoted-triple syntaxes parsed and returned zero rows in the S03 fixture; this is no-match-only evidence and should not be treated as semantic support.

Unsafe:

> git-lex supports full RDF-star/SPARQL-star parity.

Unsafe:

> Quoted-triple subject, nested quoted triple, or legacy no-parentheses syntax is supported because it parsed once.

Unsafe:

> SPARQL-star query behavior validates ACP proof gates, LegalGraph requirements, or Russian legal evidence.

### Evidence anchors

```text
prd/architecture/acp/M053-S03-SPARQL-STAR-BOUNDARY.md
.gsd/exec/126ec295-24e4-43e1-9466-cb2849c655c0.stdout
.gsd/exec/2de7bd53-fc9f-4236-b943-a54f40f165c9.stdout
.gsd/exec/61770074-e38a-4f17-8df2-f5dd322dd766.stdout
.gsd/exec/8ca74207-d691-4b46-8c49-15d2d20a6e82.stdout
```

### T03 conclusion

```text
S03 disposition: confirmed-boundary
upgraded: none beyond M052 semantic support
confirmed: narrow history graph SELECT/ASK support and non-standard triple JSON binding
added boundary: no-match-only syntax observations for quoted/nested/legacy probes
blocked: CONSTRUCT/DESCRIBE output and full RDF-star/SPARQL-star parity
main repo safety: .lex absent; Squad absent
```
