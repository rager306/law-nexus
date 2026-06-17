# M061/S05: Reusable ACP profile overlay synthesis

## Status

Pass. M061 close с reusable ACP core, law-nexus composed as profile overlay, proven overlay constraints named explicitly, blocked boundaries preserved, M062 entry conditions recorded.

This synthesis is a tracked planning and evidence summary, not ACP source truth by itself, not runtime compatibility proof, not production evidence, not main `.lex` adoption, and not validation evidence for R035, R037, or R038. Durable proof anchors are tracked repository-relative paths only.

## Reusable ACP core (per S01)

ACP-kit core defines reusable governance/proof/source/evidence semantics for project profiles. The reusable core is project-agnostic and safe for cross-project reuse.

### Class contract

| ACP core class | Reusable purpose | Required boundary |
|---|---|---|
| `acp:SourceRecord` | Represent tracked source/proof/governance record. | Must carry or link to lifecycle, evidence, and proof context before authority. |
| `acp:Requirement` | Represent a requirement independent of project domain. | Validation requires explicit proof gate; projection does not validate it. |
| `acp:Decision` | Represent accepted or proposed decisions. | Acceptance comes from decision source/proof, not from RDF presence. |
| `acp:EvidenceAnchor` | Represent tracked repository-relative proof/source anchor. | Rejected: absolute, ignored, raw, secret, vector, provider-payload, `.gsd/exec` anchors. |
| `acp:ProofGate` | Represent executable/checkable proof gate or accepted decision gate. | Placeholder gate is not proof. |
| `acp:HealthFinding` | Represent diagnostic finding or blocker. | Blocking unsafe closure is not requirement validation. |
| `acp:Projection` | Represent derived views (RDF/OWL/SHACL/SPARQL/JSON-LD/JSONL dashboards). | Always derived unless tied back to accepted ACP source/proof fields. |
| `acp:LifecycleState` | Represent proposed/active/validated/deferred/blocked/rejected/superseded state. | Labels do not transition records without accepted evidence policy. |
| `acp:AuthorityClass` | Distinguish source, derived, diagnostic, runtime-smoke, profile-proof, blocked authority. | Must be explicit for validation-sensitive claims. |
| `acp:ValidationClaim` | Represent explicit validation claim with context. | Must link requirement, evidence/proof context, lifecycle, authority, and verdict. |
| `acp:ProfileConstraint` | Represent a generic profile boundary. | Profile owns substantive domain proof; ACP core only records the boundary. |
| `acp:RuntimeAdapter` | Represent optional diagnostic adapter model. | Does not approve main `.lex`, L2 integration, source-truth migration, or production use. |

### Property contract (subset)

`acp:hasEvidenceAnchor`, `acp:requiresProofGate`, `acp:satisfiesProofGate`, `acp:blocksClaim`, `acp:validatesRequirement`, `acp:doesNotValidateRequirement`, `acp:derivedFrom`, `acp:hasLifecycleState`, `acp:hasAuthorityClass`, `acp:constrainedByProfile`, `acp:implementedByAdapter`, `acp:observedInCommit`.

### Datatype contract (subset)

`acp:identifier` (xsd:string), `acp:sourcePath` (xsd:string), `acp:selector` (xsd:string), `acp:nonAuthoritative` (xsd:boolean), `acp:blockedRequirementValidation` (xsd:string), `acp:proofLevel` (xsd:string), `acp:verdict` (enum), `acp:sourceArtifact` (xsd:string), `acp:allowedNextAction` (xsd:string), `acp:blockedAction` (xsd:string).

### Profile exclusion contract

ACP core must not include law-nexus-only terms. Excluded from core, owned by law-nexus profile or future domain profile: `LegalDocument`, `SourceProvider` for legal providers, `ParserRun` for Garant/ODT parsing, `SourceBlock`, `EvidenceSpan`, `Citation` for legal answer citation safety, `RetrievalQuery`, `RetrievalAnswer` quality, `FalkorDBGraphObservation`, `CypherSafetyCheck`, Russian legal source policy, R035/R037/R038 validation.

## Law-nexus profile overlay (per S02)

law-nexus profile maps domain terms to ACP core semantics without bypassing or duplicating source-truth rules.

### Class mapping matrix

| law-nexus class | Profile role | ACP core link | Required ACP conformance | Blocked inference |
|---|---|---|---|---|
| `lawNexus:LegalDocument` | Profile-only legal document metadata. | `acp:SourceRecord`, `acp:EvidenceAnchor` | Must carry synthetic/nonAuthoritative status; sourcePath/documentId must map to source/evidence semantics before authority. | Does not validate legal evidence, parser completeness, R035/R037/R038. |
| `lawNexus:ParserRun` | Profile-owned parser runtime/proof metadata. | `acp:ProofGate`, `acp:ValidationClaim`, runtime/proof record. | Requires observedAt, parserName, sourcePath, ACP proof gate link for authority-sensitive claims. | Does not prove Garant ODT parser correctness without parser tests/real-document proof. |
| `lawNexus:ACPBoundaryLink` | Profile bridge/navigation record. | `acp:ProfileConstraint`, `acp:ProofGate`, `acp:ValidationClaim`, `acp:SourceRecord` depending on target. | Must remain diagnostic unless it references accepted ACP source/proof machinery. | Does not make profile evidence authoritative by itself. |
| (other 8 classes) | Domain records with explicit ACP link targets. | Per S02 mapping table. | Per S02 conformance table. | Per S02 blocked inference column. |

Full mapping matrix in `prd/architecture/acp/M061-S02-LAW-NEXUS-PROFILE-CONFORMANCE-MAPPING.md`.

### Profile overlay classification

- **Profile-only domain records**: `LegalDocument`, `SourceProvider`, `SourceBlock`, `EvidenceSpan`, `Citation`, `RetrievalQuery`, `RetrievalAnswer`.
- **ACP-linked profile proof records**: `ParserRun`, `FalkorDBGraphObservation`, `CypherSafetyCheck`, `ACPBoundaryLink`.
- **Deferred hard-validation records**: object-link-heavy relationships across provider/sourceBlock/cites/answersQuery/supportsAcpGate.

## SHACL mechanics (per S03)

### Selected strategy

```text
1. Install or locally materialize ACP core records for proof fixtures.
2. Install or locally materialize law-nexus profile records for proof fixtures.
3. Add generated-style ACP core SHACL shapes.
4. Add generated-style law-nexus profile overlay SHACL shapes.
5. Run output-sensitive validation in S04 only.
```

This strategy proves profile-overlay mechanics; it does not prove native multi-kit inheritance.

### Shape formatting rule

Generated-style multiline SHACL formatting is required for `git-lex list --json` class discovery. Compact one-line target-class shapes for proof artifacts are rejected.

### Prefixes for composed proof shapes

```turtle
@prefix acp: <https://repolex.ai/ontology/kit/acp/> .
@prefix lawNexus: <https://repolex.ai/ontology/kit/law-nexus/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
```

### Shape subset used in S04

`acp:ValidationClaimShape`, `acp:ProofGateShape`, `acp:EvidenceAnchorShape`, `lawNexus:LegalDocumentShape`, `lawNexus:ParserRunShape`, `lawNexus:ACPBoundaryLinkShape`. Composed profile stored at `prd/architecture/acp/runtime/m061-s04/shapes/composed-profile.ttl`.

## Runtime validation proof (per S04)

S04 produced disposable-workspace runtime-smoke evidence in `/tmp/s061-s04-<uuid>` git repositories. Source: `prd/architecture/acp/runtime/m061-s04/diagnostics.jsonl`.

### Positive evidence (8 entries, all pass)

| Step | Command | Exit | Output signal |
|---|---|---|---|
| validate | `git-lex validate` | 0 | `Validated 6 files in 84.9ms — all pass ✓` |
| sync | `git-lex sync` | 0 | `+100 assertions, -0 retracted (600 quads)`, `Total sync graphs: 1`, `assertion_count_hint=1503` |
| query acp:ValidationClaim | `SELECT ?s WHERE { ?s a acp:ValidationClaim }` --json | 0 | rows bound |
| query acp:ProofGate | `SELECT ?s WHERE { ?s a acp:ProofGate }` --json | 0 | rows bound |
| query acp:EvidenceAnchor | `SELECT ?s WHERE { ?s a acp:EvidenceAnchor }` --json | 0 | rows bound |
| query lawNexus:ParserRun | `SELECT ?s WHERE { ?s a lawNexus:ParserRun }` --json | 0 | rows bound |
| query lawNexus:LegalDocument | `SELECT ?s WHERE { ?s a lawNexus:LegalDocument }` --json | 0 | rows bound |
| query lawNexus:ACPBoundaryLink | `SELECT ?s WHERE { ?s a lawNexus:ACPBoundaryLink }` --json | 0 | rows bound |

### Negative evidence (21 entries)

| Probe | Fixture mutation | validate exit | classification |
|---|---|---|---|
| acp-invalid-verdict | `verdict=bogus` on `acp:ValidationClaim` | 0 | pass-with-shape-violation |
| acp-missing-source-artifact | drop `acp:sourceArtifact` on `acp:ProofGate` | 0 | pass-with-shape-violation |
| lawNexus-invalid-observedAt | `observedAt=not-a-date` on `lawNexus:ParserRun` | 0 | pass-with-shape-violation |
| lawNexus-missing-synthetic | drop `lawNexus:synthetic` on `lawNexus:LegalDocument` | 0 | pass-with-shape-violation |
| lawNexus-invalid-proofStatus | `proofStatus=approved` on `lawNexus:LegalDocument` | 0 | pass-with-shape-violation |
| object-link-negative | (deferred per M058/M060) | n/a | blocked |

The 5 scalar negative probes reproduce the M058 root cause: generated SHACL shapes are underconstrained; datatype, enum, and minCount constraints are not currently attached to class shapes. Object-link negative is explicitly blocked per M058/M060 (IRI normalization). See `.gsd/milestones/M058-dncm69/M058-dncm69-SUMMARY.md` and `prd/architecture/acp/M061-S04-CORE-PLUS-PROFILE-OVERLAY-RUNTIME-VALIDATION-PROOF.md`.

## Proven overlay constraints

These are the constraints S04 actually exercised as evidence, classified by what was proven.

| Constraint | Target class | Path | Constraint kind | Proven in S04? |
|---|---|---|---|---|
| Non-authoritative marker | `acp:ValidationClaim`, `acp:ProofGate`, `acp:EvidenceAnchor`, `lawNexus:LegalDocument`, `lawNexus:ParserRun`, `lawNexus:ACPBoundaryLink` | `acp:nonAuthoritative` / `lawNexus:nonAuthoritative` | xsd:boolean minCount 1 | Yes (positive fixtures carry it; absence tested) |
| Lifecycle/authority link | `acp:ValidationClaim` | `acp:hasLifecycleState`, `acp:hasAuthorityClass` | minCount 1 | Yes (positive fixtures; absence not tested as a negative probe) |
| Verdict enum | `acp:ValidationClaim` | `acp:verdict` | sh:in (pass, fail, needs-attention, needs-remediation, blocked, not-applicable) | Honest blocker — current `git-lex validate` does not enforce enum (M058 reproduction) |
| Source artifact | `acp:ProofGate`, `acp:EvidenceAnchor` | `acp:sourceArtifact` | xsd:string minCount 1 | Honest blocker — current `git-lex validate` does not enforce minCount for this path |
| Synthetic marker | `lawNexus:LegalDocument`, `lawNexus:ParserRun`, `lawNexus:ACPBoundaryLink` | `lawNexus:synthetic` | xsd:boolean minCount 1 | Honest blocker — current `git-lex validate` does not enforce minCount for this path |
| Proof status enum | `lawNexus:LegalDocument`, `lawNexus:ParserRun`, `lawNexus:ACPBoundaryLink` | `lawNexus:proofStatus` | sh:in (example-only, observed-runtime, blocked) | Honest blocker — current `git-lex validate` does not enforce enum |
| Datatype observedAt | `lawNexus:ParserRun`, `lawNexus:FalkorDBGraphObservation`, `lawNexus:CypherSafetyCheck` | `lawNexus:observedAt` | xsd:dateTime | Honest blocker — current `git-lex validate` does not enforce xsd:dateTime |

Hard validation-gate adoption is blocked until ontology/generator strengthening plus rerun true negative runtime proof per M058.

## Blocked boundaries

These remain blocked after M061 and are not validated by M061 evidence.

```text
Blocked: hard validation gate adoption for ACP-kit / law-nexus-kit
Blocked: object-link validation as primary proof
Blocked: general validation correctness
Blocked: native ACP-kit -> law-nexus-kit runtime inheritance
Blocked: main .lex adoption
Blocked: source-truth migration
Blocked: production adoption
Blocked: external publishing of law-nexus-kit
Blocked: R035 / R037 / R038 validation from ACP-kit / git-lex / projection evidence
```

## Evidence ledger (M061 slices)

| Slice | Evidence anchor | What it supports | What it does not support |
|---|---|---|---|
| S01 | `prd/architecture/acp/M061-S01-UNIVERSAL-ACP-CORE-CONTRACT.md` | Reusable ACP core class/property/datatype contract; profile exclusion contract. | Law-nexus profile proof, runtime compatibility, main `.lex`, source-truth migration, R035/R037/R038 validation. |
| S02 | `prd/architecture/acp/M061-S02-LAW-NEXUS-PROFILE-CONFORMANCE-MAPPING.md` | law-nexus profile terms map to ACP core without bypassing or duplicating source-truth rules. | Parser/retrieval/citation/FalkorDB/Cypher-safety/parser-quality authority, R035/R037/R038 validation. |
| S03 | `prd/architecture/acp/M061-S03-ACP-PROFILE-OVERLAY-SHACL-MECHANICS.md` | Parser-compatible SHACL strategy for paired ACP + law-nexus fixtures in disposable workspace. | Native multi-kit inheritance, main `.lex`, source-truth migration, production adoption, R035/R037/R038 validation. |
| S04 | `prd/architecture/acp/M061-S04-CORE-PLUS-PROFILE-OVERLAY-RUNTIME-VALIDATION-PROOF.md`, `prd/architecture/acp/runtime/m061-s04/diagnostics.jsonl` | Positive paired ACP + law-nexus fixtures pass validate/sync/query in disposable workspace; 5 scalar negative probes reproduce M058 finding; object-link blocked. | Hard validation-gate adoption, object-link primary proof, general validation correctness, native multi-kit inheritance, main `.lex`, source-truth migration, production adoption, R035/R037/R038 validation. |
| S05 | This document. | Reusable ACP core + law-nexus profile overlay synthesis; M062 entry conditions. | Approval beyond synthesis; main `.lex`, source-truth migration, production adoption, R035/R037/R038 validation. |

## M062 entry conditions

M062 is the git-lex diagnostic adapter decision milestone. It must decide go, no-go, or limited-pilot for git-lex L2 diagnostic backend.

Entry conditions for M062:

1. M061 closed with reusable profile overlay synthesis recorded (this document).
2. M058/S04 hard-validation-gate blocker explicitly recorded as a precondition for any L2 promotion that depends on it.
3. Allowed evidence categories: positive runtime-smoke for paired ACP + law-nexus profile fixtures, derived projection diagnostics, and bounded adapter diagnostics.
4. ACP-native-only categories: R035/R037/R038, parser behavior, Garant ODT source evidence, FalkorDB runtime capability, retrieval quality, citation safety, generated-Cypher safety, raw payload anchors, source-truth statements, legal authority.
5. Rollback, residue, state ownership boundaries must be defined in M062/S02 before any pilot starts.
6. M062 may not approve main `.lex`, source-truth migration, production adoption, external publishing, or R035/R037/R038 validation unless separately proven and explicitly decided.

## Wording contract

Safe wording preserved:

```text
M061 delivered reusable ACP core and law-nexus profile overlay synthesis with bounded runtime-smoke proof in disposable workspace.
```

```text
M061/S04 reproduced the M058 underconstrained-shape finding on five scalar negative probes; hard validation-gate adoption is blocked until ontology/generator strengthening plus true negative runtime proof.
```

```text
law-nexus profile composes on top of ACP core semantics as a profile overlay, not as an independent source-truth kit.
```

Unsafe wording rejected:

```text
ACP-kit validates R035, R037, or R038.
```

```text
law-nexus-kit v0 is production-ready.
```

```text
git-lex validate enforces SHACL constraints for ACP-kit / law-nexus-kit.
```

```text
M061 proves native ACP-kit -> law-nexus-kit runtime inheritance.
```

```text
M061 authorizes main .lex adoption or source-truth migration.
```

## Next milestone

`M062-af4nqi` — git-lex diagnostic adapter decision. Sequence constraint: execute after M061, unless user explicitly replans order.
