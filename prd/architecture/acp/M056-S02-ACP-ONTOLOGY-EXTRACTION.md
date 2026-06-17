# M056 S02 ACP Ontology Extraction

## Status

Completed for `M056-wjtuag / S02` ontology extraction closure.

This artifact extracts reusable ACP core ontology candidates from the M051/S08 static prototype and M049 ACP authority boundaries. S02 is ontology extraction only: it does not scaffold ACP-kit files, initialize main `.lex`, run git-lex runtime proof, approve ACP source-truth migration, or validate R035/R037/R038.

## Scope boundaries

- M051/S08 is a proposed static prototype, not accepted ACP authority by itself.
- RDF, OWL, SHACL, SPARQL, JSON-LD, JSONL, dashboards, and recovery views remain derived unless tied to ACP source category, lifecycle state, tracked evidence anchor, and proof gate or accepted decision.
- ACP-kit v0 packages reusable ACP core semantics only.
- law-nexus Russian legal evidence, Garant parser behavior, FalkorDB runtime, retrieval quality, citation safety, generated-Cypher safety, and R035/R037/R038 validation remain profile-owned.
- Durable anchors must be tracked repository-relative paths; S02 does not use local vendor paths, ignored artifacts, raw/session payloads, secrets, or raw vectors as proof anchors.

## T01 M051/S08 prototype inspection

### Source inspected

Tracked source artifact:

```text
prd/architecture/acp/M051-S08-ACP-ONTOLOGY-PROTOTYPE.md
```

Related S01 package contract:

```text
prd/architecture/acp/M056-S01-BASE-DOMAIN-KIT-INSPECTION.md
```

### Prototype status

M051/S08 explicitly describes itself as a proposed ACP semantic integration prototype over git-lex vocabulary evidence. It preserves ACP-native authority and states these hard boundaries:

- the prototype is proposed and non-authoritative;
- it does not initialize or mutate the main checkout `.lex` state;
- RDF/OWL/SHACL/SPARQL/JSON-LD/git-lex output/dashboards/recovery views are derived unless tied to ACP source records, lifecycle state, evidence anchors, and proof gates;
- it does not validate R035/R037/R038;
- runtime-backed claims remain within the earlier isolated runtime-smoke boundary.

Interpretation for M056:

- M051/S08 is valid source input for candidate ACP vocabulary.
- M051/S08 is not enough to accept ACP-kit runtime behavior, source-truth migration, production adoption, or law-nexus profile requirement validation.
- S02 may extract classes/properties, but must preserve non-authoritative and proof-gated semantics.

### Prototype artifacts referenced by M051/S08

M051/S08 records a static prototype package made of tracked artifacts such as:

```text
prd/architecture/acp/ontology/M051-ACP-GIT-LEX-PROTOTYPE.ttl
prd/architecture/acp/examples/M051-ACP-SAMPLE-RECORDS.ttl
prd/architecture/acp/examples/M051-ACP-SAMPLE-RECORDS.jsonld
prd/architecture/acp/sparql/m051/find_projection_only_validations.rq
prd/architecture/acp/sparql/m051/find_decisions_without_proof_gate.rq
prd/architecture/acp/sparql/m051/find_unsafe_evidence_anchors.rq
prd/architecture/acp/sparql/m051/find_law_nexus_requirement_overclaims.rq
prd/architecture/acp/sparql/m051/find_blocked_runtime_adoption.rq
prd/architecture/acp/sparql/m051/trace_decision_to_evidence.rq
scripts/verify-m051-s08-acp-ontology-prototype.py
```

These are tracked source/prototype artifacts and useful extraction inputs. Their existence does not make generated projections authoritative.

### Candidate ACP core classes from M051/S08

| Candidate class | M051/S08 mapping | T01 extraction classification | Notes for S02/T03 |
|---|---|---|---|
| `acp:SourceRecord` | `rdfs:subClassOf lex:Document` | Include candidate | Core ACP record abstraction; authority remains lifecycle/proof-bound. |
| `acp:Requirement` | `rdfs:subClassOf acp:SourceRecord` | Include candidate | Reusable ACP core can model requirements, but profile validation remains separate. |
| `acp:Decision` | `rdfs:subClassOf acp:SourceRecord, lex:Decision` | Include candidate | Reuses decision semantics while preserving ACP proof authority. |
| `acp:EvidenceAnchor` | `rdfs:subClassOf lex:Reference` | Include candidate | Must be tracked repository-relative and policy-checked. |
| `acp:ProofGate` | `rdfs:subClassOf lex:Process` | Include candidate | Executable/checkable proof or accepted decision gate. |
| `acp:HealthFinding` | `rdfs:subClassOf lex:Information` | Include candidate | Diagnostic information, not validation by itself. |
| `acp:Projection` | `rdfs:subClassOf lex:Information` | Include candidate | Derived governance/recovery/query surface. |
| `acp:LifecycleState` | `rdfs:subClassOf lex:Concept` | Include candidate | Needed for active/validated/deferred/blocked/rejected/superseded states. |
| `acp:AuthorityClass` | `rdfs:subClassOf lex:Concept` | Include candidate | Needed to classify source/derived/diagnostic/runtime-smoke/profile-proof/blocked. |
| `acp:ValidationClaim` | `rdfs:subClassOf lex:Information` | Include candidate | Makes validation explicit instead of inferred from shape alone. |
| `acp:ProfileConstraint` | `rdfs:subClassOf lex:Concept` | Include candidate with boundary | Core can represent profile constraint links, but profile proof remains outside ACP core. |
| `acp:RuntimeAdapter` | `rdfs:subClassOf lex:Process` | Include candidate with boundary | Optional adapter process; does not approve git-lex runtime adoption. |

### Candidate ACP core properties from M051/S08

Object-property candidates:

| Candidate property | Meaning | T01 extraction classification |
|---|---|---|
| `acp:hasEvidenceAnchor` | Source record to evidence anchor | Include candidate. |
| `acp:requiresProofGate` | Source record to proof gate | Include candidate. |
| `acp:satisfiesProofGate` | Evidence anchor to proof gate | Include candidate. |
| `acp:blocksClaim` | Health finding to validation claim | Include candidate. |
| `acp:validatesRequirement` | Validation claim to requirement | Include candidate only with proof-gate boundary. |
| `acp:doesNotValidateRequirement` | Non-validation claim to requirement | Include candidate. |
| `acp:derivedFrom` | Projection provenance | Include candidate. |
| `acp:hasLifecycleState` | Record/claim state | Include candidate. |
| `acp:hasAuthorityClass` | Record/claim authority class | Include candidate. |
| `acp:constrainedByProfile` | Core record to profile constraint | Include candidate with profile-owned proof boundary. |
| `acp:implementedByAdapter` | Runtime adapter relation | Include candidate with adoption boundary. |
| `acp:observedInCommit` | Git provenance reference | Include candidate if S03 chooses git provenance support. |

Datatype-property candidates:

| Candidate property | Meaning | T01 extraction classification |
|---|---|---|
| `acp:identifier` | Stable local identifier | Include candidate. |
| `acp:sourcePath` | Repository-relative source path | Include candidate with anchor policy. |
| `acp:selector` | Optional selector into source | Include candidate. |
| `acp:nonAuthoritative` | Non-authoritative marker | Include candidate. |
| `acp:blockedRequirementValidation` | Explicit blocked requirements | Include candidate for examples/guards. |
| `acp:allowedNextAction` | Explicit allowed action | Include candidate or defer to runtime adapter model. |
| `acp:blockedAction` | Explicit blocked action | Include candidate or defer to runtime adapter model. |
| `acp:proofLevel` | Proof class/level | Include candidate. |
| `acp:verdict` | Gate/verifier verdict | Include candidate. |
| `acp:sourceArtifact` | Source artifact reference | Include candidate with tracked-anchor policy. |

### Prototype-only and unproven surfaces

M051/S08 also created or described surfaces that are useful but must stay bounded:

| Surface | T01 classification | Boundary |
|---|---|---|
| Turtle ontology/sample files | Static prototype evidence | Structural extraction input only, not source truth by itself. |
| JSON-LD sample/context | Proposed interchange surface | JSON-LD runtime import/export by git-lex remains unproven. |
| SPARQL audit query pack | Static audit specification | Query files do not prove runtime SPARQL behavior or source validation. |
| SHACL subset/static checks | Static verifier surface | Generated/structural shape checks are diagnostic unless tied to ACP proof gates. |
| Runtime adapter record | Deferred adapter model | Does not approve main `.lex`, production, or source-truth migration. |
| R035/R037/R038 non-validation examples | Guardrail examples | These protect against overclaiming; they do not validate those requirements. |

### T01 conclusion

M051/S08 supplies a strong candidate vocabulary for ACP-kit v0, but only as a static, non-authoritative prototype. S02 should carry forward the core source/proof/projection/health/runtime-adapter vocabulary while preserving M049/M056 boundaries: no main `.lex`, no runtime claim, no source-truth migration, no production adoption, and no R035/R037/R038 validation.

## T01 handoff

T02 should apply M049 final binding synthesis and source/proof-gate rules to these candidates, then classify which concepts are ACP core, profile-owned, deferred, or excluded before S03 creates any ACP-kit scaffold files.

## T02 M049 authority boundary mapping

### Source inspected

Tracked source artifacts:

```text
prd/architecture/acp/M049-S05-FINAL-BINDING-SYNTHESIS.md
prd/architecture/acp/M049-S05-GIT-LEX-ACP-KIT-INTEGRATION-ROADMAP.md
.agents/skills/acp/references/source-truth-and-proof-gates.md
```

### M049 binding rule applied

M049 binds law-nexus architecture into ACP through ACP-native source/proof machinery, not through git-lex authority.

Safe core statement for ACP-kit v0:

```text
ACP-kit v0 packages reusable ACP source/proof/projection vocabulary while preserving ACP-native authority.
```

Unsafe inference rejected:

```text
ACP-kit v0 makes git-lex, RDF, generated shapes, or projection output the ACP source of truth.
```

### ACP authority checklist for vocabulary extraction

Every ontology term selected for ACP core must support this authority checklist rather than bypass it:

| ACP authority field | Core ontology support | Boundary |
|---|---|---|
| Source category | `SourceRecord`, `sourceArtifact`, `sourcePath` | A path or category is not authority without lifecycle/proof context. |
| Lifecycle state | `LifecycleState`, `hasLifecycleState` | State transitions require evidence/proof policy. |
| Evidence anchor | `EvidenceAnchor`, `hasEvidenceAnchor`, `sourcePath`, `selector` | Must be tracked repository-relative and policy-checked. |
| Proof gate | `ProofGate`, `requiresProofGate`, `satisfiesProofGate`, `proofLevel`, `verdict` | Placeholder gates and diagnostics are not proof by themselves. |
| Authority class | `AuthorityClass`, `hasAuthorityClass`, `nonAuthoritative` | Prevents projection/source imitation. |
| Validation claim | `ValidationClaim`, `validatesRequirement`, `doesNotValidateRequirement` | Validation must be explicit and proof-gated; no shape-only validation. |
| Projection boundary | `Projection`, `derivedFrom` | Derived outputs support diagnostics/recovery, not direct authority. |
| Health diagnostics | `HealthFinding`, `blocksClaim` | Health findings can block unsafe claims; they do not close profile requirements alone. |
| Profile boundary | `ProfileConstraint`, `constrainedByProfile` | Core can point to profile constraints; profile owns substantive proof. |
| Runtime boundary | `RuntimeAdapter`, `implementedByAdapter`, `allowedNextAction`, `blockedAction` | Adapter modeling does not approve main `.lex`, L2, source-truth migration, or production. |

### Core versus profile-owned mapping

| Candidate | T02 classification | Reason |
|---|---|---|
| `SourceRecord` | ACP core | Generic source/proof record abstraction. |
| `Requirement` | ACP core | Generic requirement modeling; validation remains proof-gated. |
| `Decision` | ACP core | Generic accepted/proposed decision modeling. |
| `EvidenceAnchor` | ACP core | Required for durable proof binding. |
| `ProofGate` | ACP core | Required for executable/checkable proof semantics. |
| `HealthFinding` | ACP core | Required for diagnostic blockers and lifecycle health. |
| `Projection` | ACP core | Required to classify derived RDF/OWL/SHACL/SPARQL/JSON-LD/JSONL surfaces. |
| `LifecycleState` | ACP core | Required for active/validated/deferred/blocked/rejected/superseded states. |
| `AuthorityClass` | ACP core | Required for source/derived/diagnostic/runtime-smoke/profile-proof/blocked classification. |
| `ValidationClaim` | ACP core | Required to prevent implicit validation from shape/projection alone. |
| `ProfileConstraint` | ACP core boundary concept | Generic hook only; law-nexus-specific proof remains profile-owned. |
| `RuntimeAdapter` | ACP core boundary concept | Generic optional diagnostic adapter model; runtime adoption remains future proof. |
| Russian legal evidence classes | Profile-owned, not ACP core | Requires real legal document/proof path. |
| Garant ODT parser classes | Profile-owned, not ACP core | Requires parser/runtime/real-document proof. |
| FalkorDB runtime/ingest classes | Profile-owned, not ACP core | Requires FalkorDB runtime proof. |
| Retrieval/citation quality classes | Profile-owned, not ACP core | Requires evaluation/proof fixtures. |
| Generated-Cypher safety classes | Profile-owned, not ACP core | Requires generated-Cypher safety proof. |

### Properties boundary mapping

| Property group | Include in ACP core? | Boundary |
|---|---|---|
| Source to anchor/gate links | Yes | Links are required but do not prove the target gate passed. |
| Anchor to proof gate link | Yes | Must be backed by accepted proof evidence before validating a claim. |
| Claim to requirement links | Yes | `validatesRequirement` is safe only when proof-gated; `doesNotValidateRequirement` is useful for guardrails. |
| Projection provenance | Yes | `derivedFrom` must preserve projection-derived status. |
| Lifecycle/authority classification | Yes | Required to prevent authority imitation. |
| Profile constraint link | Yes, generic only | Must not encode law-nexus proof inside reusable core. |
| Runtime adapter link/action fields | Include with blocked/deferred defaults | Must not approve runtime adoption or main checkout state. |
| Git commit provenance | Include or defer | Useful but optional; must not replace tracked evidence anchors. |
| JSON-LD/SPARQL/SHACL runtime support predicates | Defer | M051/M052 keep these runtime claims unproven or bounded. |

### Blocked claims preserved

T02 applies M049 by preserving these blocked claims in the ontology extraction boundary:

```text
main repository .lex approval
ACP source-truth migration
production git-lex runtime readiness
JSON-LD git-lex runtime support
broad SPARQL-star/RDF-star parity
raw/session/provider payload proof anchors
R035/R037/R038 validation from ACP-kit/git-lex/projection evidence
Russian legal evidence correctness
Garant ODT parser completeness
FalkorDB runtime behavior
retrieval quality or citation safety proof
generated-Cypher safety proof
canonical generated registry JSONL/report freshness
```

### Included authority markers for S03 ontology work

S03 ontology scaffold should include explicit markers that make unsafe promotion harder:

- `acp:nonAuthoritative` for prototype/example/projection records.
- `acp:blockedRequirementValidation` for examples that demonstrate blocked requirement proof.
- `acp:hasAuthorityClass` to label source, derived, diagnostic, runtime-smoke, profile-proof, and blocked records.
- `acp:doesNotValidateRequirement` to make non-validation examples explicit.
- `acp:blockedAction` / `acp:allowedNextAction` for runtime adapter records, if runtime boundary properties are included.

### T02 conclusion

M049 authority boundaries support carrying most M051/S08 source/proof/projection/health/runtime-adapter vocabulary into reusable ACP core, but only with explicit lifecycle, authority, anchor, proof-gate, and profile-boundary semantics. The ontology must represent validation as an explicit proof-gated claim, not as an inference from RDF/OWL/SHACL/SPARQL/JSON-LD shape or git-lex output.

## T02 handoff

T03 should select the final ACP core vocabulary v0 table: included core terms, excluded profile-owned terms, deferred runtime/interchange terms, and guardrail terms that must remain in examples/verifiers.

## T03 ACP core vocabulary v0 selection

### Selection rule

A term is selected for ACP core v0 only when it helps express ACP source/proof/projection governance without requiring law-nexus profile proof or git-lex runtime adoption.

Selection categories:

| Category | Meaning |
|---|---|
| Include | Reusable ACP core term for `acp.ttl`. |
| Include with boundary | Reusable term, but comments/examples must state what it does not prove. |
| Defer | Useful concept, but not needed or not safe for v0 ontology source. |
| Exclude | Profile-owned, runtime-owned, raw/local, or unsafe for reusable ACP core. |

### Classes selected for ACP core v0

| Class | Selection | Required boundary comment for S03 `acp.ttl` |
|---|---|---|
| `acp:SourceRecord` | Include | A tracked ACP record or source artifact; authority requires lifecycle/proof binding. |
| `acp:Requirement` | Include | A requirement record; validation is not inferred from projection shape. |
| `acp:Decision` | Include | A decision record; acceptance depends on accepted decision source and evidence. |
| `acp:EvidenceAnchor` | Include | A tracked repository-relative proof/source pointer; local/raw/ignored anchors are invalid. |
| `acp:ProofGate` | Include | An executable/checkable proof or accepted decision gate; placeholders are not proof. |
| `acp:HealthFinding` | Include | Diagnostic finding that may block claims; does not validate requirements alone. |
| `acp:Projection` | Include | Derived representation such as RDF/OWL/SHACL/SPARQL/JSON-LD/JSONL/dashboard/recovery view. |
| `acp:LifecycleState` | Include | State category for active/validated/deferred/blocked/rejected/superseded records. |
| `acp:AuthorityClass` | Include | Classification of source/derived/diagnostic/runtime-smoke/profile-proof/blocked authority. |
| `acp:ValidationClaim` | Include | Explicit claim linking requirement, proof, evidence, and verdict; never shape-inferred. |
| `acp:ProfileConstraint` | Include with boundary | Generic profile boundary marker; substantive profile proof is not ACP core. |
| `acp:RuntimeAdapter` | Include with boundary | Optional diagnostic adapter model; does not approve main `.lex`, L2, source-truth migration, or production. |

### Object properties selected for ACP core v0

| Property | Selection | Domain/range intent | Boundary |
|---|---|---|---|
| `acp:hasEvidenceAnchor` | Include | Source/claim to evidence anchor | Link only; the anchor must still satisfy durable anchor policy. |
| `acp:requiresProofGate` | Include | Source/claim to proof gate | Required gate is not proof until satisfied. |
| `acp:satisfiesProofGate` | Include | Evidence anchor/result to proof gate | Must be tied to actual proof evidence. |
| `acp:blocksClaim` | Include | Health finding to validation claim | Blocks unsafe closure; does not validate by itself. |
| `acp:validatesRequirement` | Include with boundary | Validation claim to requirement | Safe only with lifecycle, evidence anchor, proof gate, and accepted verdict. |
| `acp:doesNotValidateRequirement` | Include | Non-validation claim to requirement | Guardrail relation for blocked/insufficient evidence. |
| `acp:derivedFrom` | Include | Projection/diagnostic to source record/artifact | Preserves derived status. |
| `acp:hasLifecycleState` | Include | Record/claim to lifecycle state | Required to avoid ambiguous authority. |
| `acp:hasAuthorityClass` | Include | Record/claim/projection to authority class | Required to label source vs derived/diagnostic/etc. |
| `acp:constrainedByProfile` | Include with boundary | Core record to profile constraint | Generic link only; does not include profile proof. |
| `acp:implementedByAdapter` | Include with boundary | Runtime adapter relation | Adapter relation is not adoption proof. |
| `acp:observedInCommit` | Defer or optional | Record/evidence to git commit | Useful but optional; must not replace evidence anchors. |

### Datatype properties selected for ACP core v0

| Property | Selection | Boundary |
|---|---|---|
| `acp:identifier` | Include | Stable identifier only; not proof. |
| `acp:sourcePath` | Include | Must be tracked repository-relative when used as evidence. |
| `acp:selector` | Include | Optional location selector; not proof alone. |
| `acp:nonAuthoritative` | Include | Explicit marker for examples/projections/prototypes. |
| `acp:blockedRequirementValidation` | Include | Guardrail marker; does not validate or invalidate by itself. |
| `acp:proofLevel` | Include | Describes proof class/level; proof still needs evidence. |
| `acp:verdict` | Include | Gate/claim verdict; needs proof context. |
| `acp:sourceArtifact` | Include | Must follow tracked-anchor policy. |
| `acp:allowedNextAction` | Include with boundary | Useful for adapter/gate state; not an approval beyond the stated action. |
| `acp:blockedAction` | Include with boundary | Useful for blocked runtime/source-truth/profiling claims. |

### Authority class instances for examples or ontology individuals

S03 may define reusable authority-class individuals if the ontology style supports individuals:

| Authority class instance | Meaning |
|---|---|
| `acp:SourceAuthority` | Accepted source/proof machinery. |
| `acp:DerivedAuthority` | Derived projections or generated views. |
| `acp:DiagnosticAuthority` | Diagnostics/health findings. |
| `acp:RuntimeSmokeAuthority` | Isolated runtime-smoke evidence. |
| `acp:ProfileProofAuthority` | Profile-owned proof class. |
| `acp:BlockedAuthority` | Explicitly blocked or insufficient evidence. |

If S03 avoids individuals, these values can be documented as allowed string values or examples. The choice is a scaffold design detail, not an authority upgrade.

### Lifecycle state instances for examples or ontology individuals

S03 may define lifecycle-state individuals or enum-like examples:

```text
active
validated
deferred
blocked
rejected
superseded
proposed
```

Boundary: lifecycle labels do not move a record into a state without accepted evidence/proof policy.

### Deferred terms

| Term or surface | Reason deferred |
|---|---|
| Runtime JSON-LD import/export support terms | M052/M051 keep git-lex JSON-LD runtime support unproven. |
| Broad SPARQL-star/RDF-star compatibility terms | Runtime parity is blocked/unproven. |
| Generated SHACL shape authority terms | Shapes are verifier/diagnostic surfaces, not authority source. |
| Adaptive ontology mutation terms | ACP ontology mutation needs separate authority/review/rollback policy. |
| Git-lex save/create/raw workflow terms | Requires dedicated adapter/rehearsal proof and explicit decision. |
| Canonical registry freshness terms | Generated architecture JSONL/report freshness needs canonical verifier evidence. |

### Excluded profile-owned terms

| Excluded from ACP core v0 | Owning proof path |
|---|---|
| Russian legal evidence correctness | law-nexus real-document/legal evidence proof. |
| Garant ODT parser completeness | parser tests and real-document fixtures. |
| FalkorDB runtime or ingest behavior | FalkorDB runtime/source/smoke proof. |
| Retrieval quality and citation safety | retrieval/citation evaluation fixtures. |
| Generated-Cypher safety | generated-Cypher safety contract/proof. |
| R035/R037/R038 substantive validation | profile-specific accepted proof gates. |

### Guardrail terms that must remain visible

These terms should remain in S03 ontology comments, examples, or verifier fixtures because they prevent overclaiming:

```text
nonAuthoritative
blockedRequirementValidation
doesNotValidateRequirement
blockedAction
allowedNextAction
derivedFrom
hasAuthorityClass
constrainedByProfile
```

They should not be removed for aesthetic simplification; without them, future projections can imitate source authority too easily.

### T03 conclusion

ACP core vocabulary v0 is selected around source/proof/projection governance. It includes boundary concepts for profile constraints and runtime adapters, but excludes law-nexus substantive proof and defers runtime/interchange claims that remain unproven. This selection gives S03 a concrete ontology contract without approving ACP-kit runtime behavior, main `.lex`, source-truth migration, production adoption, or R035/R037/R038 validation.

## T03 handoff

T04 should verify that the S02 extraction artifact contains selected, deferred, and excluded terms; has no unsafe anchors; makes no source-truth/runtime/freshness/profile-validation overclaim; preserves no-main-state residue; and passes diff/GitNexus hygiene checks.
