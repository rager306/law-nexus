# M057/S03: Positive ACP runtime fixture proof

## Status

S03 positive runtime fixture proof passed. A synthetic ACP Decision fixture validated, synced, and was queryable through `git-lex query` after canonical full-spec ACP-kit initialization.

## Scope and authority boundary

This artifact records isolated runtime-smoke evidence only. It does not make git-lex or ACP-kit the ACP source-truth store, does not approve main `.lex` state, does not approve production adoption, and does not validate R035, R037, or R038.

Canonical runtime command used:

```text
git-lex init --kit rager306/git-lex-kit-acp <disposable-workspace>
```

All runtime proof was executed in a disposable workspace and removed after the proof. The main law-nexus checkout remained free of `.lex`, `Squad`, `Raw`, and `.artifacts`.

## Fixture

Synthetic file created inside the disposable workspace:

```text
ACP/Decision/S03PositiveDecision.md
```

Fixture frontmatter:

```yaml
acp.Decision.identifier: "s03-positive-decision"
acp.Decision.sourcePath: "prd/architecture/acp/M057-S03-POSITIVE-RUNTIME-FIXTURE.md"
acp.Decision.nonAuthoritative: true
```

Fixture body explicitly stated that it is diagnostic-only and does not validate R035, R037, or R038.

Fixture content hash observed during runtime smoke:

```text
sha256=c8b9707177cd0a7e386868e9cb2b5e53ee2256f46583ff7d3dba04495e8ed2de
```

## Validate proof

Command:

```text
git-lex validate
```

Result:

```text
validate_code=0
Validated 4 files ... all pass ✓
```

Interpretation: the positive ACP fixture is accepted by the generated ACP SHACL shapes and current git-lex validator. This is positive validation smoke only; it does not prove negative enforcement.

## Sync proof

After committing the fixture in the disposable repository, command:

```text
git-lex sync
```

Result:

```text
sync_code=0
+23 assertions
138 quads
4 commit(s)
23 events
42 annotations
Total sync graphs: 1
```

Interpretation: git-lex can sync the committed positive ACP fixture into its persistent graph store. The store path was disposable and is not a durable proof anchor.

## Query proof

Three targeted `git-lex query --json` probes exited 0.

### Fixture sourcePath query

A query filtering for `M057-S03-POSITIVE-RUNTIME-FIXTURE` returned two rows:

```text
fm predicate:  https://repolex.ai/ontology/git-lex/fm/acp.Decision.sourcePath
acp predicate: https://repolex.ai/ontology/kit/acp/sourcePath
object:        prd/architecture/acp/M057-S03-POSITIVE-RUNTIME-FIXTURE.md
```

This proves the ACP frontmatter field was extracted and queryable both through the frontmatter predicate surface and the ACP kit predicate surface.

### Fixture path and type query

Additional query/dump probes showed the fixture path and ACP typing:

```text
ACP/Decision/S03PositiveDecision.md
rdf:type lex:Document
rdf:type acp:Decision
acp:identifier "s03-positive-decision"
acp:nonAuthoritative "true"
acp:sourcePath "prd/architecture/acp/M057-S03-POSITIVE-RUNTIME-FIXTURE.md"
```

Interpretation: the positive fixture is queryable as an ACP Decision document with ACP-kit predicates after `sync`.

## Cleanup proof

```text
workspace_removed=yes
post_no_main_state=yes
```

The main law-nexus checkout remained free of:

```text
.lex
Squad
Raw
.artifacts
```

## Supported by S03

- Canonical ACP-kit init can support a synthetic positive ACP Decision fixture.
- `git-lex validate` accepts that positive fixture.
- `git-lex sync` succeeds after committing the fixture.
- `git-lex query --json` can retrieve ACP fixture facts, including `acp:sourcePath` and ACP typing.
- ACP dot-notation frontmatter maps to both `fm:` and ACP-kit predicate surfaces.

## Not supported yet

- Negative validation enforcement.
- Required-field failure behavior.
- Invalid datatype/cardinality behavior.
- Main `.lex` adoption.
- ACP source-truth migration.
- Production adoption.
- R035/R037/R038 validation.

## Downstream handoff

S04 should create an intentionally invalid ACP fixture in a disposable workspace and prove whether `git-lex validate` fails with a non-zero exit code and actionable diagnostic. If invalid fixtures still pass, negative validation enforcement must remain blocked and final synthesis must say so plainly.
