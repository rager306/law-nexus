# M058/S02: True negative constraint probe

## Status

Constraint inventory complete; runtime true-negative probing pending. Current generated ACP shapes expose only object-property `sh:nodeKind sh:IRI` constraints, which are neutralized by `frontmatter_to_turtle` normalization for validation. No generated `sh:datatype`, `sh:in`, or `sh:minCount` constraints were present in the inspected runtime shapes.

## Scope and authority boundary

This artifact is a diagnostic validation-semantics probe. It does not make git-lex or ACP-kit the ACP source-truth store, does not approve main `.lex` state, does not approve production adoption, and does not validate R035, R037, or R038.

## Canonical runtime command

```text
git-lex init --kit rager306/git-lex-kit-acp <disposable-workspace>
```

## T01 generated shape inventory

A disposable canonical ACP-kit workspace generated:

```text
shape_line_count=86
node_shape_count=12
target_class_count=12
property_count=3
nodeKind_count=3
datatype_count=0
in_count=0
minCount_count=0
workspace_removed=yes
post_no_main_state=yes
```

Generated property constraints:

```text
acp:ValidationClaimShape
  sh:path acp:doesNotValidateRequirement
  sh:nodeKind sh:IRI
  sh:message "doesNotValidateRequirement must be an IRI reference."

  sh:path acp:validatesRequirement
  sh:nodeKind sh:IRI
  sh:message "validatesRequirement must be an IRI reference."

acp:HealthFindingShape
  sh:path acp:blocksClaim
  sh:nodeKind sh:IRI
  sh:message "blocksClaim must be an IRI reference."
```

No generated constraints were found for:

```text
sh:datatype
sh:in
sh:minCount
```

## Why datatype and enum fields did not produce shapes

The ACP ontology contains datatype properties and enum-like datatypes, including:

```text
acp:nonAuthoritative rdfs:range xsd:boolean
acp:verdict rdfs:range acp:VerdictValue
acp:VerdictValue owl:oneOf (...)
```

However, the shape generator only attaches property constraints when properties have `rdfs:domain` values matching a class. The inspected ACP datatype properties define ranges but not domains. Therefore they are not emitted as class property constraints in `acp-shapes.ttl`.

## T01 interpretation

The current corrected ACP kit generated shapes do not expose a practical true negative fixture for datatype, enum, or required-field validation because those constraint classes are absent from generated shapes.

The only generated property constraints are object-property IRI constraints, and M058/S01 showed those are not true negatives when written as frontmatter strings because `frontmatter_to_turtle` converts object-property values to `urn:entity:*` IRIs for the validation graph.

## T02 runtime probe

T02 created invalid-looking datatype/enum/unknown-property fixtures in a disposable canonical ACP-kit workspace.

Invalid-looking ProofGate fixture:

```yaml
acp.ProofGate.identifier: "m058-invalid-enum-boolean"
acp.ProofGate.proofLevel: "negative-probe"
acp.ProofGate.verdict: "definitely-not-a-valid-verdict"
acp.ProofGate.nonAuthoritative: "not-a-boolean"
```

Invalid-looking Decision fixture:

```yaml
acp.Decision.identifier: "m058-unknown-property"
acp.Decision.nonAuthoritative: true
acp.Decision.unmodeledRequiredThing: "should-not-matter"
```

Runtime result:

```text
validate_code=0
Validated 5 files ... all pass ✓
commit_code=0
sync_code=0
query_code=0
workspace_removed=yes
post_no_main_state=yes
```

Query proof showed the invalid-looking values were extracted and queryable:

```text
acp:verdict -> definitely-not-a-valid-verdict
acp:nonAuthoritative -> not-a-boolean
acp:unmodeledRequiredThing -> should-not-matter
fm:acp.ProofGate.verdict -> definitely-not-a-valid-verdict
fm:acp.ProofGate.nonAuthoritative -> not-a-boolean
fm:acp.Decision.unmodeledRequiredThing -> should-not-matter
```

The generated shape file still had no:

```text
sh:datatype
sh:in
sh:minCount
```

## S02 conclusion

Current ACP generated shapes do not expose a practical true negative validation fixture. Object-property constraints are normalized into IRIs by the validation path, and datatype/enum/required-field constraints are absent from generated shapes.

This is a shape-generation/ontology-domain limitation, not evidence that every possible git-lex SHACL validation path is broken.

Corrected validation claim:

```text
For the current ACP kit, `git-lex validate` can accept positive ACP records, but current generated ACP shapes do not provide enough constraints to prove negative enforcement. Strengthening validation requires adding domains/restrictions or generator changes, then rerunning negative runtime proof.
```
