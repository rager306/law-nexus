# M061/S03: ACP profile overlay SHACL mechanics proof

## Status

Static SHACL mechanics proof complete for the ACP core plus law-nexus profile overlay strategy.

## Scope

This artifact defines a parser-compatible SHACL strategy for S04 runtime validation. It does not run or claim runtime validation success. It keeps native multi-kit inheritance blocked, main `.lex` blocked, source-truth migration blocked, production adoption blocked, adapter adoption blocked, external publishing blocked, and R035/R037/R038 validation blocked.

Correct mechanics target:

```text
ACP-kit core = reusable governance/proof/source/evidence semantics
law-nexus profile = overlay constraints that map profile records to ACP core semantics
```

Incorrect mechanics target:

```text
law-nexus profile as independent source-truth kit
law-nexus profile bypassing ACP proof gates
law-nexus-specific classes added to ACP core
native ACP-kit -> law-nexus-kit runtime inheritance claim
```

## Selected S04 proof mechanics

S04 should use a disposable isolated workspace and a composed proof-shape profile.

Selected strategy:

```text
1. Install or locally materialize ACP core records for proof fixtures.
2. Install or locally materialize law-nexus profile records for proof fixtures.
3. Add generated-style ACP core SHACL shapes.
4. Add generated-style law-nexus profile overlay SHACL shapes.
5. Run output-sensitive validation in S04 only.
```

This strategy proves profile-overlay mechanics; it does not prove native multi-kit inheritance.

The proof-shape profile may be assembled in a disposable workspace even if current git-lex runtime supports one configured domain kit. The composed shapes are diagnostic proof inputs for S04, not ACP source truth and not production packaging.

## Rejected alternatives

| Alternative | Rejected because |
|---|---|
| Treat law-nexus-kit as standalone configured kit only | Bypasses the user goal: ACP-kit must remain the reusable core. |
| Put law-nexus classes into ACP core ontology | Pollutes ACP core and breaks cross-project reuse. |
| Claim native base -> ACP-kit -> law-nexus-kit inheritance | Not proven by current git-lex runtime mechanics. |
| Use object-link negatives as primary proof | M058/M060 showed literal-looking object values can normalize to IRIs and pass validation. |
| Treat generated shapes as authority | Shape/projection alone is derived; authority needs ACP source/proof machinery. |

## Shape formatting rule

S03 preserves generated-style multiline SHACL formatting because earlier proof showed compact one-line shapes may not be discovered by `git-lex list --json`.

Required style:

```turtle
lawNexus:ParserRunShape a sh:NodeShape ;
  sh:targetClass lawNexus:ParserRun ;
  sh:property [
    sh:path lawNexus:observedAt ;
    sh:datatype xsd:dateTime ;
    sh:minCount 1 ;
  ] .
```

Avoid compact one-line target-class shapes for proof artifacts.

## Prefixes for composed proof shapes

S04 proof shapes should use both ACP and law-nexus prefixes:

```turtle
@prefix acp: <https://repolex.ai/ontology/kit/acp/> .
@prefix lawNexus: <https://repolex.ai/ontology/kit/law-nexus/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
```

## ACP core shape subset for S04

S04 should test a small ACP core subset before broader strengthening.

### ACP validation claim shape

Purpose:

```text
Prove reusable ACP core validation claims require non-authoritative marker, authority class, lifecycle state, and verdict enum before they can be used as profile proof inputs.
```

Generated-style shape:

```turtle
acp:ValidationClaimShape a sh:NodeShape ;
  sh:targetClass acp:ValidationClaim ;
  sh:property [
    sh:path acp:nonAuthoritative ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path acp:verdict ;
    sh:in ("pass" "fail" "needs-attention" "needs-remediation" "blocked" "not-applicable") ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path acp:hasLifecycleState ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path acp:hasAuthorityClass ;
    sh:minCount 1 ;
  ] .
```

### ACP proof gate shape

Purpose:

```text
Prove proof-gate fixtures are non-authoritative by default and carry a source/proof marker before being linked from profile records.
```

Generated-style shape:

```turtle
acp:ProofGateShape a sh:NodeShape ;
  sh:targetClass acp:ProofGate ;
  sh:property [
    sh:path acp:nonAuthoritative ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path acp:sourceArtifact ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] .
```

### ACP evidence anchor shape

Purpose:

```text
Prove source/evidence anchors carry a repository-relative artifact string in the proof fixture. Durable-anchor policy still needs verifier checks beyond SHACL.
```

Generated-style shape:

```turtle
acp:EvidenceAnchorShape a sh:NodeShape ;
  sh:targetClass acp:EvidenceAnchor ;
  sh:property [
    sh:path acp:sourceArtifact ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path acp:nonAuthoritative ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] .
```

## Law-nexus profile overlay shape subset for S04

S04 should test a small law-nexus subset that maps to ACP core semantics but does not prove substantive legal/parser/FalkorDB/retrieval/Cypher behavior.

### Shared profile fixture properties

Purpose:

```text
Prove every current law-nexus profile fixture is explicitly synthetic, non-authoritative, and has bounded proof status.
```

Generated-style shape pattern:

```turtle
lawNexus:LegalDocumentShape a sh:NodeShape ;
  sh:targetClass lawNexus:LegalDocument ;
  sh:property [
    sh:path lawNexus:synthetic ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:nonAuthoritative ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:proofStatus ;
    sh:in ("example-only" "observed-runtime" "blocked") ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:sourcePath ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] .
```

This pattern can be repeated for selected S04 fixture classes. It should not be generalized to all law-nexus validation correctness until S04 proves each intended class/constraint.

### ParserRun profile proof shape

Purpose:

```text
Prove a runtime-observation profile record carries timestamp and parser metadata before it is linked to ACP proof machinery.
```

Generated-style shape:

```turtle
lawNexus:ParserRunShape a sh:NodeShape ;
  sh:targetClass lawNexus:ParserRun ;
  sh:property [
    sh:path lawNexus:synthetic ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:nonAuthoritative ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:proofStatus ;
    sh:in ("example-only" "observed-runtime" "blocked") ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:observedAt ;
    sh:datatype xsd:dateTime ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:parserName ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:sourcePath ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] .
```

### ACPBoundaryLink bridge shape

Purpose:

```text
Prove profile bridge records carry diagnostic boundary metadata before profile-to-ACP proof claims are attempted.
```

Generated-style shape:

```turtle
lawNexus:ACPBoundaryLinkShape a sh:NodeShape ;
  sh:targetClass lawNexus:ACPBoundaryLink ;
  sh:property [
    sh:path lawNexus:synthetic ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:nonAuthoritative ;
    sh:datatype xsd:boolean ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:proofStatus ;
    sh:in ("example-only" "observed-runtime" "blocked") ;
    sh:minCount 1 ;
  ] ;
  sh:property [
    sh:path lawNexus:sourcePath ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
  ] .
```

## Profile-to-ACP bridge constraint stance

S03 does not approve object-link hard validation.

Reason:

```text
M058/M060 showed object-property frontmatter values can normalize to IRIs, so literal-looking invalid values are unreliable true negatives.
```

S04 may still include bridge records, but the primary negative proof should use datatype, enum, or minCount constraints first.

Allowed S04 bridge claim:

```text
The proof fixture includes paired ACP and law-nexus records with boundary metadata.
```

Blocked S04 bridge claim unless a better negative is proven:

```text
Blocked: law-nexus object links enforce ACP proof-target correctness.
```

## S04 fixture plan

S04 should use paired fixtures with explicit non-authoritative status.

Positive fixture set:

```text
ACP/ProofGate/example-profile-proof-gate.md
ACP/ValidationClaim/example-profile-validation-claim.md
ACP/EvidenceAnchor/example-profile-evidence-anchor.md
LawNexus/ParserRun/example-parser-run.md
LawNexus/ACPBoundaryLink/example-acp-boundary-link.md
LawNexus/LegalDocument/example-legal-document.md
```

Core negative candidates:

```text
ACP/ValidationClaim/negative-invalid-verdict.md
- invalid acp:verdict value

ACP/ProofGate/negative-missing-source-artifact.md
- missing acp:sourceArtifact
```

Profile negative candidates:

```text
LawNexus/ParserRun/negative-invalid-observed-at.md
- invalid lawNexus:observedAt dateTime

LawNexus/LegalDocument/negative-missing-synthetic.md
- missing lawNexus:synthetic

LawNexus/LegalDocument/negative-invalid-proof-status.md
- invalid lawNexus:proofStatus enum
```

Object-link negative candidate:

```text
Deferred unless S04 identifies a strategy that avoids IRI-normalization false negatives.
```

## Constraints proven by S03

S03 proves only that the selected mechanics are concrete and ready for S04 proof:

```text
- ACP core and law-nexus profile overlay constraints are separated.
- Shape snippets use generated-style multiline `sh:targetClass` formatting.
- Shape snippets include specific `sh:minCount`, `sh:in`, `sh:datatype`, `xsd:boolean`, and `xsd:dateTime` terms.
- S04 fixture plan includes paired ACP core and law-nexus profile records.
- Object-link correctness remains blocked pending a better true-negative strategy.
```

S03 does not prove:

```text
runtime validation success (blocked)
general validation correctness (blocked)
native multi-kit inheritance (blocked)
main `.lex` adoption (blocked)
source-truth migration (blocked)
production adoption (blocked)
adapter adoption (blocked)
external publishing (blocked)
R035/R037/R038 validation (blocked)
```

## Safe wording

```text
S03 defines a composed proof-shape strategy for ACP core plus law-nexus profile overlay constraints.
```

```text
S03 prepares output-sensitive S04 validation but does not prove runtime validation itself.
```

```text
Object-link correctness remains blocked unless S04 proves a true negative that survives IRI normalization.
```

## Unsafe wording

```text
Unsafe wording: S03 proves law-nexus runtime validation.
```

```text
Unsafe wording: S03 proves native ACP-kit to law-nexus-kit inheritance.
```

```text
Unsafe wording: S03 validates R035/R037/R038.
```

```text
Unsafe wording: S03 approves main `.lex`, source-truth migration, production adoption, adapter adoption, or external publishing.
```

## Final S03 decision

The selected SHACL mechanics are accepted for S04 planning:

```text
Use a composed proof-shape profile in an isolated workspace to test paired ACP core plus law-nexus profile overlay fixtures without claiming native multi-kit inheritance.
```

The proof must remain output-sensitive in S04:

```text
record validation exit code + validation output
```

and claims must stay constraint-specific.
