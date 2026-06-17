# M061/S02: Law-nexus profile conformance mapping

## Status

Law-nexus profile conformance mapping drafted for M061.

## Scope

This artifact defines how the law-nexus profile overlays reusable ACP-kit core semantics. It is a conformance design artifact, not runtime adoption, not main `.lex` adoption, not production approval, not external publishing approval, and not validation evidence for R035, R037, or R038.

Correct direction:

```text
ACP-kit core = universal governance/proof/source/evidence semantics
law-nexus profile = domain overlay that links to ACP core semantics
```

Incorrect direction:

```text
law-nexus profile duplicates ACP proof/source-truth semantics
law-nexus profile bypasses ACP proof gates
law-nexus-specific terms enter ACP core
```

## Source inputs

S02 uses these tracked inputs:

```text
prd/architecture/acp/M061-S01-UNIVERSAL-ACP-CORE-CONTRACT.md
git-lex-kit-law-nexus/ontology/law-nexus/law-nexus.ttl
git-lex-kit-law-nexus/content/LawNexus/*/example-*.md
```

The example inventory contains 11 law-nexus classes:

```text
ACPBoundaryLink
Citation
CypherSafetyCheck
EvidenceSpan
FalkorDBGraphObservation
LegalDocument
ParserRun
RetrievalAnswer
RetrievalQuery
SourceBlock
SourceProvider
```

All current examples are synthetic and non-authoritative.

## Conformance rule

Every validation-sensitive law-nexus profile record must be able to state:

```text
1. which ACP core source/proof/evidence concept it links to
2. which lifecycle or proof status applies
3. which evidence anchor or source path is involved
4. which proof gate or validation claim would be needed for authority
5. which claims remain blocked because they require profile-owned proof
```

If these fields are missing, the profile record remains diagnostic/profile-proof candidate only.

## Class mapping matrix

| law-nexus class | Profile role | ACP core link target | Required ACP conformance | Blocked inference |
|---|---|---|---|---|
| `lawNexus:LegalDocument` | Profile-only legal document metadata. | `acp:SourceRecord` and/or `acp:EvidenceAnchor`. | Must carry synthetic/non-authoritative status; source path/document ID must map to source/evidence semantics before authority. | Does not validate legal evidence, parser completeness, or R035/R037/R038. |
| `lawNexus:SourceProvider` | Profile-only legal/provider category metadata. | `acp:SourceRecord` when provider policy is a tracked source, otherwise profile metadata. | Must not replace evidence anchors; provider identity is context, not proof. | Does not validate source authority or provider correctness. |
| `lawNexus:ParserRun` | Profile-owned parser runtime/proof metadata. | `acp:ProofGate`, `acp:ValidationClaim`, and/or runtime/proof record semantics. | Requires observed timestamp, parser name, source path, and ACP proof gate link for authority-sensitive parser claims. | Does not prove Garant ODT parser correctness without parser tests/real-document proof. |
| `lawNexus:SourceBlock` | Profile-owned bounded source block reference. | `acp:EvidenceAnchor` or source selector semantics. | Must carry source path and selector; raw legal text remains outside durable profile proof unless separately approved. | Does not prove legal text extraction quality by itself. |
| `lawNexus:EvidenceSpan` | Profile-owned citation/evidence span metadata. | `acp:EvidenceAnchor` and `acp:ValidationClaim`. | Must link to source block and ACP gate before citation/answer validation. | Does not validate citation safety without profile proof. |
| `lawNexus:Citation` | Profile-owned citation metadata. | `acp:EvidenceAnchor` and/or `acp:ValidationClaim`. | Must link to source block/evidence span and claim context before authority. | Does not prove answer correctness or legal authority. |
| `lawNexus:RetrievalQuery` | Profile-owned retrieval test/query fixture. | `acp:ProofGate` when used as a test gate, otherwise profile fixture. | Query text can define a profile test input; proof requires paired answer/evidence/gate. | Does not prove retrieval quality alone. |
| `lawNexus:RetrievalAnswer` | Profile-owned non-authoritative answer fixture. | `acp:ValidationClaim` and `acp:EvidenceAnchor` through citations. | Must link to query and citations; non-authoritative unless accepted profile proof gate validates it. | Does not provide legal advice or validate Legal KnowQL quality. |
| `lawNexus:FalkorDBGraphObservation` | Profile-owned graph runtime observation metadata. | `acp:RuntimeAdapter`, `acp:ProofGate`, and `acp:EvidenceAnchor`. | Must link to proof gate/evidence for any capability claim; observation timestamp required for runtime claims. | Does not prove FalkorDB capability or production behavior alone. |
| `lawNexus:CypherSafetyCheck` | Profile-owned generated-Cypher safety check metadata. | `acp:ProofGate` and `acp:ValidationClaim`. | Must carry check name, observed timestamp, and ACP proof/claim context before safety validation. | Does not prove generated-Cypher safety without executable safety proof. |
| `lawNexus:ACPBoundaryLink` | Profile bridge/navigation record. | `acp:ProfileConstraint`, `acp:ProofGate`, `acp:ValidationClaim`, or `acp:SourceRecord` depending on target. | Must remain diagnostic unless it references accepted ACP source/proof machinery. | Does not make profile evidence authoritative by itself. |

## Property mapping matrix

| law-nexus property | Profile meaning | ACP core relationship | Candidate conformance constraint |
|---|---|---|---|
| `lawNexus:synthetic` | Marks synthetic profile fixtures. | Mirrors ACP non-authoritative fixture discipline. | Required boolean for all v0 profile fixtures. |
| `lawNexus:nonAuthoritative` | Marks profile record as non-authoritative. | Equivalent intent to `acp:nonAuthoritative`, but kept profile-local unless mapped by S03/S04. | Required boolean for all current examples. |
| `lawNexus:proofStatus` | Profile-local proof status enum. | Should align with ACP authority/lifecycle/verdict semantics without replacing them. | Enum: `example-only`, `observed-runtime`, `blocked`. |
| `lawNexus:sourcePath` | Profile source/evidence path reference. | Candidate map to `acp:sourcePath` or `acp:sourceArtifact`. | Required for LegalDocument, ParserRun, SourceBlock, EvidenceSpan, ACPBoundaryLink when evidence/source semantics are claimed. |
| `lawNexus:documentId` | Profile local legal-document identifier. | May support `acp:identifier` for linked SourceRecord. | String only; not proof. |
| `lawNexus:observedAt` | Profile runtime observation timestamp. | Supports runtime/proof context for ProofGate/RuntimeAdapter-linked records. | `xsd:dateTime` required for ParserRun, FalkorDBGraphObservation, CypherSafetyCheck when observed-runtime is claimed. |
| `lawNexus:parserName` | Profile parser identity. | Supports ProofGate context. | Required for parser-run proof claims. |
| `lawNexus:selector` | Profile selector into source block/evidence span/citation. | Supports EvidenceAnchor selector semantics. | Required for SourceBlock/EvidenceSpan/Citation when evidence claims are made. |
| `lawNexus:queryText` | Retrieval test input. | Supports ProofGate fixture input. | Required for RetrievalQuery. |
| `lawNexus:answerSummary` | Non-authoritative answer summary. | Supports ValidationClaim candidate only with citations/gate. | Required for RetrievalAnswer fixtures; never legal authority. |
| `lawNexus:checkName` | Cypher safety check name. | Supports ProofGate identity. | Required for CypherSafetyCheck. |
| `lawNexus:provider` | Link to SourceProvider. | Supports source context only. | Object-link correctness remains unproven after M060/S03; do not use as hard proof until S03/S04 improve negative strategy. |
| `lawNexus:sourceBlock` | Link to SourceBlock. | Supports EvidenceAnchor/source selector context. | Object-link proof blocked until better true negative strategy. |
| `lawNexus:cites` | RetrievalAnswer to Citation link. | Supports evidence/claim relation. | Object-link proof blocked until better true negative strategy. |
| `lawNexus:answersQuery` | RetrievalAnswer to RetrievalQuery link. | Supports proof fixture relation. | Object-link proof blocked until better true negative strategy. |
| `lawNexus:supportsAcpGate` | Link to ACPBoundaryLink. | Intended bridge to ACP ProofGate/ValidationClaim/SourceRecord semantics. | Must be diagnostic unless the boundary link references accepted ACP proof machinery. |

## Classification summary

| Classification | law-nexus classes | Meaning |
|---|---|---|
| Profile-only domain records | `LegalDocument`, `SourceProvider`, `SourceBlock`, `EvidenceSpan`, `Citation`, `RetrievalQuery`, `RetrievalAnswer` | Domain semantics owned by law-nexus profile; ACP core records only source/proof/evidence relationships. |
| ACP-linked profile proof records | `ParserRun`, `FalkorDBGraphObservation`, `CypherSafetyCheck`, `ACPBoundaryLink` | Must link to ACP proof/claim/evidence/adapter concepts before authority-sensitive use. |
| Deferred hard-validation records | Object-link-heavy relationships across provider/sourceBlock/cites/answersQuery/supportsAcpGate | Shape proof remains blocked until S03/S04 define a true negative strategy that is not defeated by IRI normalization. |

No law-nexus class belongs in ACP core.

## Required ACP fields for validation-sensitive profile claims

| Profile claim type | Required ACP/core fields before authority | Required profile fields | Status in S02 |
|---|---|---|---|
| Legal document accepted as evidence | `SourceRecord` or `EvidenceAnchor`, lifecycle state, authority class, proof gate or accepted decision. | `synthetic=false` only after future proof, `nonAuthoritative=false` only after future proof, `sourcePath`, `documentId`, provider context. | Blocked; S02 only maps fields. |
| Parser run validates extraction behavior | `ProofGate`, `ValidationClaim`, evidence anchor, lifecycle state, verdict. | `parserName`, `observedAt`, `sourcePath`, `proofStatus=observed-runtime`. | Blocked without parser tests/real-document proof. |
| Evidence span supports answer/citation | `EvidenceAnchor`, `ValidationClaim`, proof gate. | `sourcePath`, `selector`, `sourceBlock`. | Blocked without citation-safety proof. |
| Retrieval answer validates answer quality | `ValidationClaim`, `ProofGate`, evidence anchors for citations. | `answersQuery`, `cites`, `answerSummary`, non-authoritative marker. | Blocked without retrieval/citation proof. |
| FalkorDB observation supports capability claim | `RuntimeAdapter`, `ProofGate`, evidence anchor, lifecycle state. | `observedAt`, `supportsAcpGate`. | Blocked without FalkorDB runtime proof. |
| Cypher safety check validates generated Cypher | `ProofGate`, `ValidationClaim`, evidence anchor, verdict. | `checkName`, `observedAt`, `supportsAcpGate`. | Blocked without executable safety proof. |
| ACP boundary link points to accepted ACP proof | Target `SourceRecord`, `ProofGate`, `ValidationClaim`, or `ProfileConstraint` with accepted evidence. | `sourcePath`, `proofStatus`, non-authoritative marker. | Diagnostic until target proof is accepted. |

## Candidate S03/S04 conformance constraints

S03 should translate a small, testable subset into parser-compatible SHACL or overlay mechanics.

High-confidence candidates from M060/S03 lessons:

```text
lawNexus:synthetic -> sh:datatype xsd:boolean + sh:minCount 1 for all profile fixtures
lawNexus:nonAuthoritative -> sh:datatype xsd:boolean + sh:minCount 1 for all profile fixtures
lawNexus:proofStatus -> sh:in (example-only, observed-runtime, blocked) + sh:minCount 1
lawNexus:observedAt -> sh:datatype xsd:dateTime for ParserRun, FalkorDBGraphObservation, CypherSafetyCheck
lawNexus:sourcePath -> sh:minCount 1 for records that claim source/evidence context
```

Profile-to-ACP bridge candidates:

```text
lawNexus:ACPBoundaryLink.sourcePath -> required when supportsAcpGate is present
lawNexus:supportsAcpGate -> object link to ACPBoundaryLink, but hard negative proof remains blocked until object-link strategy is improved
lawNexus:proofStatus=observed-runtime -> should require observedAt for runtime-observation classes
lawNexus:proofStatus=blocked -> should allow blocked claim records without validation promotion
```

ACP core linkage candidate for S03/S04:

```text
A profile proof fixture may include paired ACP core records in the same isolated workspace:
- ACP/ProofGate/example-profile-proof-gate.md
- ACP/ValidationClaim/example-profile-validation-claim.md
- LawNexus/ParserRun/example-parser-run.md
- LawNexus/ACPBoundaryLink/example-acp-boundary-link.md
```

This tests conformance shape mechanics without claiming native multi-kit inheritance.

## Blocked claims

These remain blocked after S02:

```text
Blocked: law-nexus profile validates R035/R037/R038
```

```text
Blocked: law-nexus profile proves Russian legal evidence correctness
```

```text
Blocked: law-nexus profile proves Garant ODT parser correctness
```

```text
Blocked: law-nexus profile proves FalkorDB runtime capability or production behavior
```

```text
Blocked: law-nexus profile proves retrieval quality or citation safety
```

```text
Blocked: law-nexus profile proves generated-Cypher safety
```

```text
Blocked: law-nexus profile approves main `.lex`, source-truth migration, production adoption, adapter adoption, or external publishing
```

## Safe wording

```text
S02 maps law-nexus profile records to reusable ACP core source/proof/evidence semantics.
```

```text
S02 defines conformance requirements for future SHACL/runtime proof, but does not prove runtime validation by itself.
```

```text
law-nexus profile owns Russian legal, parser, FalkorDB, retrieval, citation, and generated-Cypher proof paths.
```

## Unsafe wording

```text
Unsafe wording: law-nexus profile requirements are validated by ACP-kit conformance mapping.
```

```text
Unsafe wording: law-nexus ontology can replace ACP source-truth and proof-gate semantics.
```

```text
Unsafe wording: ACPBoundaryLink makes profile evidence authoritative.
```

```text
Unsafe wording: S02 approves main `.lex`, source-truth migration, production adoption, adapter adoption, or external publishing.
```

## Final S02 decision

The law-nexus profile conformance mapping is accepted for M061 planning:

```text
law-nexus profile overlays ACP core and must carry ACP-compatible source/proof/evidence links before authority-sensitive use.
```

S03 should prove SHACL/profile mechanics over a small subset of constraints before S04 runtime validation. Object-link hard validation remains explicitly blocked unless S03 finds a true negative strategy that survives git-lex IRI normalization.
