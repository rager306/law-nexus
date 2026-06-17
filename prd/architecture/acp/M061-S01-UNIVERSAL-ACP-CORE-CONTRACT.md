# M061/S01: Universal ACP core contract

## Status

Universal ACP core contract drafted for M061.

## Scope

This artifact defines ACP-kit core semantics that must remain reusable across projects. It is a design and validation-contract artifact, not runtime adoption, not main `.lex` adoption, not production approval, and not requirement validation for law-nexus profile requirements.

M061 corrects the post-M060 direction:

```text
ACP-kit = universal reusable governance/proof/source/evidence kit
law-nexus-kit = domain profile overlay on ACP semantics
```

M060 scaffold evidence remains useful as a runtime/scaffold spike, but it must not define the target architecture as an independent law-nexus kit that bypasses ACP.

## Authority rule

An ACP claim is authoritative only when all required fields exist:

```text
source category + lifecycle state + evidence anchor + proof gate or accepted decision
```

Projection shape alone is never authority.

Derived artifacts such as RDF, OWL, SHACL, SPARQL, JSON-LD, JSONL, dashboards, recovery views, git-lex query output, and generated shapes may support diagnostics, but they do not validate requirements or promote git-lex to source truth without accepted ACP proof machinery.

## ACP core purpose

ACP core should be usable by different projects to represent governance and proof state, regardless of domain.

ACP core owns:

```text
source record identity
evidence anchor policy
lifecycle state
proof gate relationship
authority class
validation claim framing
projection and diagnostic classification
profile constraint boundary
runtime adapter boundary
```

ACP core does not own:

```text
Russian legal evidence semantics
Garant ODT parser behavior
FalkorDB runtime or ingest behavior
retrieval quality
citation safety
generated-Cypher safety
Legal KnowQL answer correctness
R035/R037/R038 validation
```

Those are profile-owned for law-nexus or future domain profiles.

## Core class contract

| ACP core class | Reusable purpose | Required boundary |
|---|---|---|
| `acp:SourceRecord` | Represent a tracked source/proof/governance record. | Must carry or link to lifecycle, evidence, and proof context before authority is inferred. |
| `acp:Requirement` | Represent a requirement independent of project domain. | Validation requires explicit proof gate; projection does not validate it. |
| `acp:Decision` | Represent accepted or proposed decisions. | Acceptance comes from decision source/proof, not from RDF presence. |
| `acp:EvidenceAnchor` | Represent tracked repository-relative proof/source anchor. | Rejected durable anchors: absolute, ignored, raw, secret, vector, provider-payload, or `.gsd/exec` anchors. |
| `acp:ProofGate` | Represent executable/checkable proof gate or accepted decision gate. | Placeholder gate is not proof. |
| `acp:HealthFinding` | Represent diagnostic finding or blocker. | Blocking unsafe closure is not requirement validation. |
| `acp:Projection` | Represent derived views such as RDF/OWL/SHACL/SPARQL/JSON-LD/JSONL dashboards. | Always derived unless tied back to accepted ACP source/proof fields. |
| `acp:LifecycleState` | Represent proposed/active/validated/deferred/blocked/rejected/superseded state. | Labels do not transition records without accepted evidence policy. |
| `acp:AuthorityClass` | Distinguish source, derived, diagnostic, runtime-smoke, profile-proof, and blocked authority. | Must be explicit for validation-sensitive claims. |
| `acp:ValidationClaim` | Represent explicit validation claim with context. | Must link requirement, evidence/proof context, lifecycle, authority, and verdict. |
| `acp:ProfileConstraint` | Represent a generic profile boundary. | Profile owns substantive domain proof; ACP core only records the boundary. |
| `acp:RuntimeAdapter` | Represent optional diagnostic adapter model. | Does not approve main `.lex`, L2 integration, source-truth migration, or production use. |

These classes are project-agnostic and safe for reusable ACP-kit core.

## Core property contract

| ACP core property | Reusable purpose | Intended constraint |
|---|---|---|
| `acp:hasEvidenceAnchor` | Link record or claim to proof/source anchor. | Expected object link to `acp:EvidenceAnchor`; durable anchor policy still needs a verifier. |
| `acp:requiresProofGate` | State required proof gate. | Expected object link to `acp:ProofGate`; requirement is not proven until satisfied. |
| `acp:satisfiesProofGate` | Link evidence/result to satisfied gate. | Expected object link to `acp:ProofGate`; needs actual evidence. |
| `acp:blocksClaim` | Link finding to blocked validation claim. | Expected `HealthFinding -> ValidationClaim`. |
| `acp:validatesRequirement` | Link proof-gated claim to requirement. | Expected `ValidationClaim -> Requirement`; unsafe without authority fields. |
| `acp:doesNotValidateRequirement` | Link non-validation claim to requirement. | Expected `ValidationClaim -> Requirement`. |
| `acp:derivedFrom` | Preserve source/projection relationship. | Should not upgrade authority by itself. |
| `acp:hasLifecycleState` | Link record/claim to lifecycle state. | Expected object link to `acp:LifecycleState`. |
| `acp:hasAuthorityClass` | Link record/claim/projection to authority class. | Expected object link to `acp:AuthorityClass`. |
| `acp:constrainedByProfile` | Link ACP record to profile constraint. | Expected object link to `acp:ProfileConstraint`; profile owns substantive proof. |
| `acp:implementedByAdapter` | Link diagnostic process/record to adapter. | Adapter relation is not adoption proof. |
| `acp:observedInCommit` | Optional git provenance helper. | Does not replace evidence anchors or proof gates. |

## Core datatype contract

| ACP core datatype property | Reusable purpose | Intended constraint |
|---|---|---|
| `acp:identifier` | Stable local identifier. | `xsd:string`; not proof by itself. |
| `acp:sourcePath` | Repository-relative source path. | `xsd:string`; must be policy-checked when used as evidence. |
| `acp:selector` | Optional source selector. | `xsd:string`; not proof by itself. |
| `acp:nonAuthoritative` | Mark examples/projections/prototypes as non-authoritative. | `xsd:boolean`; should be required for synthetic fixtures. |
| `acp:blockedRequirementValidation` | Record blocked requirement-validation IDs. | `xsd:string`; must not validate the requirement. |
| `acp:proofLevel` | Record proof class/level label. | `xsd:string`; proof still requires evidence. |
| `acp:verdict` | Record gate/claim verdict. | Enum-like `pass`, `fail`, `needs-attention`, `needs-remediation`, `blocked`, `not-applicable`. |
| `acp:sourceArtifact` | Record tracked source artifact reference. | `xsd:string`; must be repository-relative and tracked for durable proof. |
| `acp:allowedNextAction` | Record narrow allowed action. | `xsd:string`; not approval beyond stated action. |
| `acp:blockedAction` | Record blocked action. | `xsd:string`; useful for adoption/source-truth guardrails. |

## Intended ACP core validation constraints

M061 should strengthen ACP-kit validation only for project-agnostic constraints first.

Candidate core constraints:

```text
SourceRecord.nonAuthoritative -> xsd:boolean for examples/projections
SourceRecord.sourcePath or EvidenceAnchor.sourceArtifact -> required for source/evidence records when claim authority is source/profile-proof
ValidationClaim.verdict -> enum
ValidationClaim.hasLifecycleState -> required for authority-sensitive claims
ValidationClaim.hasAuthorityClass -> required for authority-sensitive claims
ValidationClaim.requiresProofGate or satisfiesProofGate -> required before validatesRequirement can be treated as proven
Projection.hasAuthorityClass -> required and normally derived/diagnostic
RuntimeAdapter.blockedAction -> required for blocked adoption records
```

These are intended constraints, not yet all proven runtime constraints. S03/S04 own SHACL mechanics and output-sensitive runtime proof.

## Profile exclusion contract

ACP core must not include law-nexus-only terms. These belong to a law-nexus profile or a future domain profile:

| Domain/profile concept | ACP core status | Profile owner |
|---|---|---|
| `LegalDocument` | Excluded from core | law-nexus profile |
| `SourceProvider` for legal providers | Excluded from core except generic evidence/source references | law-nexus profile |
| `ParserRun` for Garant/ODT parsing | Excluded from core except generic runtime observation/proof gate relationship | law-nexus profile |
| `SourceBlock` / `EvidenceSpan` over legal text | Excluded from core | law-nexus profile |
| `Citation` for legal answer citation safety | Excluded from core | law-nexus profile |
| `RetrievalQuery` / `RetrievalAnswer` quality | Excluded from core | law-nexus profile |
| `FalkorDBGraphObservation` | Excluded from core except generic runtime observation boundary | law-nexus profile |
| `CypherSafetyCheck` | Excluded from core except generic proof/validation claim relationship | law-nexus profile |
| Russian legal source policy | Excluded from core | law-nexus profile |
| R035/R037/R038 validation | Excluded from core and blocked from projection-only proof | law-nexus profile with real proof gates |

## Required law-nexus profile direction

S02 must map law-nexus profile terms onto ACP core, not duplicate ACP core semantics.

Expected direction:

```text
law-nexus LegalDocument -> linked to ACP SourceRecord or EvidenceAnchor semantics
law-nexus ParserRun -> linked to ACP ProofGate or runtime/proof record semantics
law-nexus Citation -> linked to ACP EvidenceAnchor or ValidationClaim semantics
law-nexus CypherSafetyCheck -> linked to ACP ProofGate / ValidationClaim semantics
law-nexus FalkorDBGraphObservation -> linked to ACP RuntimeAdapter / ProofGate / EvidenceAnchor semantics
```

The exact mapping belongs to S02. S01 only fixes the rule: law-nexus profile extends ACP core; it does not replace or bypass it.

## Safe wording

```text
ACP-kit core defines reusable governance/proof/source/evidence semantics for project profiles.
```

```text
law-nexus profile should map domain terms to ACP core proof and source semantics without duplicating source-truth rules.
```

```text
SHACL and git-lex projections are derived diagnostics unless tied to accepted ACP source/proof machinery.
```

## Unsafe wording

```text
Unsafe wording: ACP-kit validates law-nexus requirements by itself.
```

```text
Unsafe wording: law-nexus-kit can bypass ACP proof gates because it has its own ontology.
```

```text
Unsafe wording: generated SHACL makes ACP records authoritative.
```

```text
Unsafe wording: git-lex projection validates R035/R037/R038.
```

```text
Unsafe wording: M061 approves main `.lex`, production adoption, source-truth migration, or adapter adoption.
```

## Downstream contract for S02

S02 must produce a profile conformance mapping that answers:

```text
1. Which law-nexus classes are profile-only?
2. Which law-nexus classes must link to ACP core classes?
3. Which ACP core fields are required for each validation-sensitive law-nexus claim?
4. Which law-nexus claims remain blocked without real legal/parser/FalkorDB/retrieval/Cypher proof?
5. Which shape constraints can be tested without claiming native multi-kit inheritance?
```

S02 must keep ACP core portable for other projects.

## Final S01 decision

The universal ACP core contract is accepted for M061 planning:

```text
ACP core first; law-nexus profile second.
```

M061 should strengthen validation and profile conformance only in ways that preserve ACP reuse across projects and keep domain proof in the owning profile.
