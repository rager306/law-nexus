# M058/S01: Validate versus query root cause

## Status

Root-cause proof in progress. This artifact corrects the over-broad M057/S04 interpretation: the tested object-property literal fixture was not a true negative for the `git-lex validate` input graph, because the validate path normalizes object-property frontmatter values into IRIs before SHACL validation.

## Scope and authority boundary

This artifact is a diagnostic/root-cause correction. It does not make git-lex or ACP-kit the ACP source-truth store, does not approve main `.lex` state, does not approve production adoption, and does not validate R035, R037, or R038.

## M057/S04 issue being corrected

M057/S04 observed:

```text
acp.ValidationClaim.validatesRequirement: "R035"
acp.ValidationClaim.doesNotValidateRequirement: "R037"
acp.HealthFinding.blocksClaim: "not-an-iri-reference"
```

`git-lex validate` exited 0, while `git-lex sync/query` later exposed those values as literals on ACP predicate surfaces.

The too-broad conclusion was:

```text
negative validation enforcement does not work
```

The corrected interpretation is narrower:

```text
M057/S04 did not prove negative validation failure because the selected object-property fixture is normalized into IRIs by the validate path before SHACL validation. The sync/query graph exposes a different literal surface, so validate and query evidence must not be conflated.
```

## Source evidence

Local git-lex source inspection showed the validation command uses a per-file validation graph, not the synced persistent store.

`cmd_validate` behavior:

```text
- Collect installed SHACL shapes from `.lex/ontology/{short}/{short}-shapes.ttl`.
- Walk markdown files in the repository.
- For each file, call `frontmatter_to_turtle(filepath, root, kit)`.
- Parse that generated Turtle into an in-memory RDF graph.
- Run SHACL validation against that per-file graph.
```

The critical validation data source is:

```text
frontmatter_to_turtle(filepath, root, kit)
```

`frontmatter_to_turtle` behavior for object properties:

```text
- Read frontmatter keys matching `{kit}.{Class}.{property}`.
- Infer document class from the key.
- Load object-property names from generated shapes.
- If a property is an object property, split its frontmatter value and emit each value as an IRI-like `urn:entity:{slug}`.
```

Conceptual output for the M057/S04 fixture:

```yaml
acp.ValidationClaim.validatesRequirement: "R035"
```

becomes validation Turtle equivalent to:

```ttl
<urn:doc:...> acp:validatesRequirement <urn:entity:r035> .
```

not:

```ttl
<urn:doc:...> acp:validatesRequirement "R035" .
```

Therefore `sh:nodeKind sh:IRI` correctly passes for the validation graph.

## Consequence

M057/S04 still found an important mismatch, but not the originally stated one:

- It did not prove `git-lex validate` ignored a literal-vs-IRI violation in its own validation graph.
- It did prove that `validate` and `sync/query` can expose different representations for the same frontmatter object-property value.
- Therefore validation results cannot be interpreted directly from query surface literals without checking the validation Turtle conversion path.

## Runtime comparison evidence

T02 reproduced the M057/S04 object-property fixture pattern in a disposable workspace initialized with the canonical command.

Generated shape constraints were present:

```text
acp:doesNotValidateRequirement sh:nodeKind sh:IRI
acp:validatesRequirement sh:nodeKind sh:IRI
acp:blocksClaim sh:nodeKind sh:IRI
```

Fixture frontmatter used literal-looking values:

```yaml
acp.ValidationClaim.validatesRequirement: "R035"
acp.ValidationClaim.doesNotValidateRequirement: "R037"
acp.HealthFinding.blocksClaim: "not-an-iri-reference"
```

Runtime result:

```text
validate_code=0
Validated 5 files ... all pass ✓
commit_code=0
sync_code=0
query_code=0
```

After sync, the query surface exposed literal values:

```text
fm:acp.HealthFinding.blocksClaim -> not-an-iri-reference (literal)
fm:acp.ValidationClaim.doesNotValidateRequirement -> R037 (literal)
fm:acp.ValidationClaim.validatesRequirement -> R035 (literal)

acp:blocksClaim -> not-an-iri-reference (literal)
acp:doesNotValidateRequirement -> R037 (literal)
acp:validatesRequirement -> R035 (literal)
```

Cleanup result:

```text
workspace_removed=yes
post_no_main_state=yes
```

This confirms the source-level explanation: validation can pass because its per-file graph normalizes object-property values to IRIs, while sync/query can still expose literal values from extraction surfaces.

## Current recommendation impact

The corrected S01 conclusion should narrow M057's final recommendation:

- Keep blocking `git-lex validate` as a hard ACP proof gate until true negative fixtures are proven.
- Do not claim the object-property literal test proves validator enforcement is broken.
- Proceed to S02 true negative probing against constraints that survive `frontmatter_to_turtle` normalization.
