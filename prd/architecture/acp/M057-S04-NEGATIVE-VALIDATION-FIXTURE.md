# M057/S04: Negative ACP validation fixture proof

## Status

S04 completed with a blocker finding: current ACP-kit/git-lex validation did not reject intentionally invalid ACP object-property literals. Negative validation enforcement remains unproven and must be treated as blocked.

## Scope and authority boundary

This artifact records isolated runtime-smoke evidence only. It does not make git-lex or ACP-kit the ACP source-truth store, does not approve main `.lex` state, does not approve production adoption, and does not validate R035, R037, or R038.

Canonical runtime command used:

```text
git-lex init --kit rager306/git-lex-kit-acp <disposable-workspace>
```

All runtime proof was executed in disposable workspaces and removed after the proof. The main law-nexus checkout remained free of `.lex`, `Squad`, `Raw`, and `.artifacts`.

## Generated constraints targeted

Generated ACP shapes included object-property IRI constraints:

```text
acp:ValidationClaimShape
  sh:targetClass acp:ValidationClaim
  sh:path acp:doesNotValidateRequirement
  sh:nodeKind sh:IRI
  sh:message "doesNotValidateRequirement must be an IRI reference."

  sh:path acp:validatesRequirement
  sh:nodeKind sh:IRI
  sh:message "validatesRequirement must be an IRI reference."

acp:HealthFindingShape
  sh:targetClass acp:HealthFinding
  sh:path acp:blocksClaim
  sh:nodeKind sh:IRI
  sh:message "blocksClaim must be an IRI reference."
```

These constraints were chosen because they are concrete generated shape constraints, not arbitrary malformed text.

## Invalid fixtures

S04 used intentionally invalid fixtures with literal values where generated shapes require IRI references.

### Invalid ValidationClaim fixture

```yaml
acp.ValidationClaim.identifier: "s04-invalid-object-literal"
acp.ValidationClaim.validatesRequirement: "R035"
acp.ValidationClaim.doesNotValidateRequirement: "R037"
acp.ValidationClaim.nonAuthoritative: true
```

The values `R035` and `R037` are literals, not IRI references.

### Invalid HealthFinding fixture

```yaml
acp.HealthFinding.identifier: "s04-invalid-blocks-claim"
acp.HealthFinding.blocksClaim: "not-an-iri-reference"
acp.HealthFinding.nonAuthoritative: true
```

The value `not-an-iri-reference` is a literal, not an IRI reference.

## Validation result

Initial invalid fixture run:

```text
negative_validate_code=0
Validated 6 files ... all pass ✓
```

Committed invalid fixture run through the pre-commit hook:

```text
commit_code=0
validate_after_commit_code=0
sync_after_commit_code=0
query_after_commit_code=0
Validated 5 files ... all pass ✓
```

Interpretation: current runtime validation did not reject the shape-targeted invalid fixtures.

## Query proof that invalid values were not ignored

After commit and sync, a targeted query over object-property predicates returned literal values on both frontmatter and ACP-kit predicate surfaces:

```text
fm:acp.HealthFinding.blocksClaim              "not-an-iri-reference"
fm:acp.ValidationClaim.validatesRequirement   "R035"
fm:acp.ValidationClaim.doesNotValidateRequirement "R037"

acp:blocksClaim              "not-an-iri-reference"
acp:validatesRequirement     "R035"
acp:doesNotValidateRequirement "R037"
```

This proves the invalid values were extracted and queryable. They were not merely ignored by extraction.

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

## Supported by S04

- Generated ACP shapes contain object-property IRI constraints for `ValidationClaim` and `HealthFinding`.
- Invalid fixtures targeting those constraints can be extracted and queried.
- `git-lex validate` currently returns exit 0 for those invalid fixtures.
- Negative validation enforcement is therefore not proven.

## Blocked by S04

The following claims remain blocked:

- ACP-kit validation rejects invalid object-property literals.
- ACP-kit validation enforces generated `sh:nodeKind sh:IRI` constraints for tested fields.
- `git-lex validate` can be relied on as a hard ACP proof gate.
- ACP-kit runtime validation can validate R035, R037, or R038.
- Main `.lex`, ACP source-truth migration, or production adoption can proceed on validation-enforcement grounds.

## Downstream handoff

S05 final synthesis should recommend that ACP/git-lex may proceed only as a diagnostic positive runtime surface for class discovery and positive sync/query, not as a validation-enforcing proof gate. Any L2 operational diagnostic step must either avoid relying on negative validation enforcement or first fix/prove validator behavior with a separate regression test and runtime proof.
