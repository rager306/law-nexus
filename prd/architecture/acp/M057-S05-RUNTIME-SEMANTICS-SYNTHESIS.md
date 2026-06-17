# M057/S05: ACP-kit runtime semantics synthesis and L2 recommendation

## Status

M057 runtime semantics proof is complete. ACP-kit can be used as a diagnostic positive runtime surface for canonical install, class discovery, positive fixture validation, sync, and query. It must not be used as a validation-enforcing proof gate because negative validation enforcement failed in S04.

## Scope and authority boundary

This synthesis is based on isolated runtime-smoke evidence from M057/S01-S04. It does not make git-lex or ACP-kit the ACP source-truth store, does not approve main `.lex` state, does not approve production adoption, and does not validate R035, R037, or R038.

Canonical runtime command remains:

```text
git-lex init --kit rager306/git-lex-kit-acp <disposable-workspace>
```

Short `--kit acp` remains non-canonical for law-nexus proof.

## Evidence chain

### S01: layout and class-discovery diagnosis

Artifact:

```text
prd/architecture/acp/M057-S01-RUNTIME-LAYOUT-DIAGNOSIS.md
```

Findings:

- Full-spec ACP-kit init succeeded in a disposable workspace.
- Installed layout included `.lex/ontology/acp/acp.ttl`, generated `acp-shapes.ttl`, top-level `ACP/` scaffold files, extraction sidecars, and a disposable pre-commit hook.
- Initial `git-lex list --json` returned `[]`.
- Root cause was likely namespace mismatch: generated shapes were header-only because the ontology prefix did not match git-lex kit namespace filtering.

### S02: namespace correction and class discovery

Artifact:

```text
prd/architecture/acp/M057-S02-KIT-NAMESPACE-CORRECTION.md
```

Findings:

- ACP-kit namespace was corrected to `https://repolex.ai/ontology/kit/acp/`.
- External ACP-kit commit was published after explicit approval:

```text
7d0166a977e8f097206fa8cac80fc52eeb180e32
```

- Canonical full-spec init then generated non-empty ACP shapes.
- `git-lex list --json` returned 12 ACP classes:

```text
AuthorityClass
Decision
EvidenceAnchor
HealthFinding
LifecycleState
ProfileConstraint
Projection
ProofGate
Requirement
RuntimeAdapter
SourceRecord
ValidationClaim
```

### S03: positive ACP runtime fixture

Artifact:

```text
prd/architecture/acp/M057-S03-POSITIVE-RUNTIME-FIXTURE.md
```

Findings:

- A synthetic `ACP/Decision/S03PositiveDecision.md` fixture validated successfully.
- `git-lex sync` succeeded after committing the fixture.
- `git-lex query --json` retrieved the fixture through both frontmatter and ACP-kit predicate surfaces.
- Query/dump evidence showed:

```text
rdf:type lex:Document
rdf:type acp:Decision
acp:identifier "s03-positive-decision"
acp:nonAuthoritative "true"
acp:sourcePath "prd/architecture/acp/M057-S03-POSITIVE-RUNTIME-FIXTURE.md"
```

### S04: negative ACP validation fixture

Artifact:

```text
prd/architecture/acp/M057-S04-NEGATIVE-VALIDATION-FIXTURE.md
```

Findings:

- Generated ACP shapes contained `sh:nodeKind sh:IRI` constraints for object-property fields including:

```text
acp:validatesRequirement
acp:doesNotValidateRequirement
acp:blocksClaim
```

- Invalid fixtures used literal values where IRI references were required:

```text
R035
R037
not-an-iri-reference
```

- `git-lex validate` still returned exit 0 and reported all files passed.
- After sync, query proof showed those invalid literal values were extracted and queryable in ACP predicate surfaces.
- Therefore negative validation enforcement is blocked.

## Supported claims after M057

The following claims are now supported as isolated runtime-smoke evidence:

- Canonical owner/repo ACP-kit init works with `git-lex init --kit rager306/git-lex-kit-acp <workspace>`.
- ACP-kit generated shapes are non-empty after namespace correction.
- `git-lex list --json` discovers 12 ACP classes from the corrected published kit.
- Positive ACP Decision fixtures can pass current `git-lex validate`.
- Committed positive ACP fixtures can be synced with `git-lex sync`.
- Positive ACP fixture facts can be queried with `git-lex query --json`.
- ACP dot-notation frontmatter maps to both `fm:` and ACP-kit predicate surfaces.
- All M057 runtime work can be performed in disposable workspaces without main checkout `.lex`, `Squad`, `Raw`, or `.artifacts` residue.

## Blocked claims after M057

The following claims remain blocked:

- `git-lex validate` enforces ACP generated SHACL constraints for tested object-property violations.
- ACP-kit validation rejects invalid object-property literals.
- `git-lex validate` can be used as a hard ACP proof gate.
- Do not claim ACP-kit or git-lex validates R035, R037, or R038.
- Do not migrate ACP source truth into git-lex or `.lex`.
- Do not initialize `.lex` in the main law-nexus checkout.
- Do not treat ACP-kit as production-ready for LegalGraph runtime governance.
- Do not let L2 diagnostics rely on negative validation enforcement.

## L2 recommendation

Proceed to L2 operational diagnostics only under a constrained diagnostic profile:

Allowed:

- Use ACP-kit/git-lex in isolated disposable workspaces for diagnostic projections.
- Use canonical full-spec init only.
- Use class discovery, positive fixture sync, and query surfaces for diagnostic exploration.
- Treat queryable ACP facts as derived projections, not source truth.
- Keep ACP-native source records, accepted decisions, tracked evidence anchors, and proof gates authoritative.

Blocked:

- Do not initialize or mutate main checkout `.lex`.
- Do not use `git-lex validate` as a hard proof gate.
- Do not claim negative validation enforcement.
- Do not validate R035/R037/R038 from ACP-kit/git-lex evidence.
- Do not approve source-truth migration or production adoption.

Required before stronger adoption:

- Add a validator fix or configuration change that makes tested invalid object-property literals fail validation.
- Add regression tests for negative ACP validation fixtures.
- Re-run isolated canonical runtime proof showing non-zero `git-lex validate` exit and actionable diagnostics for invalid fixtures.
- Record a separate adoption decision before any main `.lex`, production, or source-truth use.

## Final M057 conclusion

M057 advances ACP/git-lex from install-only proof to bounded runtime semantics proof. The corrected ACP kit is useful for diagnostic positive runtime work: install, list, sync, and query. It is not yet a validation-enforcing ACP proof gate. The safe next step is constrained L2 diagnostic exploration that depends only on positive runtime/query behavior and explicitly avoids relying on negative validation enforcement.
