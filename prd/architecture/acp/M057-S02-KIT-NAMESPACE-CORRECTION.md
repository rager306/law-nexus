# M057/S02: ACP-kit namespace correction and class discovery proof

## Status

S02 complete. The ACP-kit namespace mismatch diagnosed in S01 was corrected and canonical full-spec class discovery now works after publishing the corrected kit.

## Scope and authority boundary

This artifact records semantic-kit/runtime-smoke evidence only. It does not make ACP-kit an ACP source-truth store, does not approve main `.lex` state, does not approve production adoption, and does not validate R035, R037, or R038.

Canonical ACP-kit runtime command remains:

```text
git-lex init --kit rager306/git-lex-kit-acp <disposable-workspace>
```

Short `--kit acp` remains non-canonical for law-nexus proof because it resolves to the default owner/repo rather than the accepted `rager306` kit.

## Correction

S01 showed `git-lex list --json` returned `[]` because generated `acp-shapes.ttl` had no `sh:NodeShape` or `sh:targetClass` entries. The likely cause was namespace filtering in git-lex shape generation.

The ACP ontology namespace was changed from:

```text
https://legalgraph.example/ontology/acp/
```

to the git-lex kit namespace convention:

```text
https://repolex.ai/ontology/kit/acp/
```

Tracked law-nexus mirror updated:

```text
git-lex-kit-acp/ontology/acp/acp.ttl
```

External ACP-kit repository updated and published with explicit user approval:

```text
repo: rager306/git-lex-kit-acp
commit: 7d0166a977e8f097206fa8cac80fc52eeb180e32
subject: Align ACP ontology namespace for git-lex shapes
```

## Verification before publish

Before publishing, canonical full-spec init still fetched the old GitHub kit and reproduced the S01 failure:

```text
canonical_init_code=0
canonical_list_code=0
canonical_list_json=[]
canonical_namespace=https://legalgraph.example/ontology/acp/
workspace_removed=yes
post_no_main_state=yes
```

This confirmed that a local-only correction was insufficient for canonical proof, because `git-lex init --kit rager306/git-lex-kit-acp` fetches the kit from GitHub.

## Canonical proof after publish

After pushing commit `7d0166a977e8f097206fa8cac80fc52eeb180e32`, a fresh disposable workspace was initialized with:

```text
git-lex init --kit rager306/git-lex-kit-acp <disposable-workspace>
```

Runtime result:

```text
published_init_code=0
published_list_json_code=0
published_list_text_code=0
workspace_removed=yes
post_no_main_state=yes
```

Installed namespace:

```text
@prefix acp: <https://repolex.ai/ontology/kit/acp/> .
<https://repolex.ai/ontology/kit/acp> a owl:Ontology ;
```

Generated shape file:

```text
.lex/ontology/acp/acp-shapes.ttl
shape_line_count=86
```

The generated shapes now include `sh:NodeShape` and `sh:targetClass` entries for ACP classes, including:

```text
acp:RuntimeAdapterShape sh:targetClass acp:RuntimeAdapter
acp:ProfileConstraintShape sh:targetClass acp:ProfileConstraint
acp:ValidationClaimShape sh:targetClass acp:ValidationClaim
acp:AuthorityClassShape sh:targetClass acp:AuthorityClass
acp:LifecycleStateShape sh:targetClass acp:LifecycleState
acp:ProjectionShape sh:targetClass acp:Projection
acp:HealthFindingShape sh:targetClass acp:HealthFinding
acp:ProofGateShape sh:targetClass acp:ProofGate
acp:EvidenceAnchorShape sh:targetClass acp:EvidenceAnchor
acp:DecisionShape sh:targetClass acp:Decision
acp:RequirementShape sh:targetClass acp:Requirement
acp:SourceRecordShape sh:targetClass acp:SourceRecord
```

## Class discovery output

`git-lex list --json` returned 12 ACP classes:

```text
RuntimeAdapter
ProfileConstraint
ValidationClaim
AuthorityClass
LifecycleState
Projection
HealthFinding
ProofGate
EvidenceAnchor
Decision
Requirement
SourceRecord
```

Text output reported:

```text
acp (12 classes):
  acp:AuthorityClass
  acp:Decision
  acp:EvidenceAnchor
  acp:HealthFinding
  acp:LifecycleState
  acp:ProfileConstraint
  acp:Projection
  acp:ProofGate
  acp:Requirement
  acp:RuntimeAdapter
  acp:SourceRecord
  acp:ValidationClaim
```

The runtime also created top-level class folders under `ACP/`, including `ACP/Decision`, `ACP/Requirement`, `ACP/SourceRecord`, and the other discovered class directories.

## Interpretation

Supported by S02:

- The ACP-kit namespace correction fixes generated SHACL shape creation.
- Canonical `git-lex init --kit rager306/git-lex-kit-acp <workspace>` now fetches the corrected published kit.
- `git-lex list --json` is no longer empty and discovers 12 ACP classes.
- The main law-nexus checkout remains free of `.lex`, `Squad`, `Raw`, and `.artifacts` residue.

Not supported yet:

- `git-lex sync` semantics over ACP fixtures.
- `git-lex query` semantics over ACP fixtures.
- `git-lex validate` positive/negative fixture behavior beyond init hook smoke.
- Main `.lex` adoption.
- ACP source-truth migration.
- Production adoption.
- R035/R037/R038 validation.

## Downstream handoff

S03 can now proceed with a positive ACP fixture over the published full-spec kit. It should prove `sync`, graph visibility, and query behavior against tracked fixture content in a disposable workspace, while preserving the same no-main-state checks and non-authoritative ACP-kit boundary.
