# M059/S03: Law-nexus-kit v0 configured domain design

## Status

Design artifact for a future law-nexus semantic kit v0. This is not an implementation artifact and does not create a kit repository.

## Scope and authority boundary

This design uses M059/S01 prior-art patterns and M059/S02 mechanics constraints. It does not initialize or mutate main `.lex`, does not create law-nexus-kit, does not change external repositories, does not approve ACP-kit or git-lex source-truth migration, does not approve production adoption, and does not validate R035, R037, or R038.

The design target is:

```text
law-nexus-kit v0 as a deterministic configured domain kit
```

It is not a native runtime dependency child of ACP-kit:

```text
law-nexus-kit as a native runtime dependency child of ACP-kit
```

ACP-native artifacts, accepted ACP decisions, source/runtime evidence, tests, and real-document proof remain authoritative. law-nexus-kit records are diagnostic/profile evidence projections unless a future proof gate accepts a specific record category.

## Design decision

M059/S02 proved current git-lex mechanics as:

```text
git-lex engine
+ implicit base kit
+ one configured domain/profile kit
+ optional adaptive _ontology shapes
```

Therefore law-nexus-kit v0 should be installed as the configured domain kit:

```text
git-lex init --kit <explicit-owner>/git-lex-kit-law-nexus <isolated-target-repo>
```

The exact owner/repo is intentionally unspecified in this design. Future runtime proof should use the explicit owner/repo spec, not a short alias, unless a separate decision approves default short-name resolution.

## Allowed, caution, and blocked behaviors

| Behavior | v0 classification | Rationale |
|---|---|---|
| Deterministic `kit.yml` with `install folders: true` | Allowed | Matches squad/ACP deterministic domain-kit pattern. |
| Static ontology file under `ontology/law-nexus/law-nexus.ttl` | Allowed | Required for generated shapes and type discovery. |
| Synthetic non-authoritative examples | Allowed | Useful for templates and smoke tests without raw legal text. |
| Explicit `rdfs:domain` and `rdfs:range` declarations | Allowed | Needed for generated shape usefulness per S02. |
| `owl:Restriction` for required fields | Caution, allowed only with future negative proof | Useful only after generated `sh:minCount` and validation failure are proven. |
| `owl:oneOf` enum declarations | Caution, allowed only with future negative proof | Useful only after generated `sh:in` and validation failure are proven. |
| References to ACP proof gates or source records | Allowed as diagnostic links | Links may support navigation but do not confer authority. |
| Static import/copy of ACP vocabulary terms | Caution | Acceptable only if source/runtime proof shows generated shapes see the intended triples. |
| Native dependency inheritance from ACP-kit | Blocked | Not proven by current git-lex mechanics. |
| Adaptive ontology mutation | Blocked | Unsafe for deterministic ACP/legal proof boundaries. |
| Raw folders, session logs, provider payload mirrors | Blocked | Unsafe proof anchors and possible secret/raw-content exposure. |
| Main checkout `.lex` initialization | Blocked | Runtime adoption gate remains closed. |
| R035/R037/R038 validation from law-nexus-kit records | Blocked | Those requirements require their own source/runtime/legal proof paths. |
| Source-truth migration or production adoption claims | Blocked | M059 is design/proof work only. |

## Minimal kit.yml sketch

Future scaffold should be boring and deterministic:

```yaml
name: law-nexus
install folders: true
folder base: LawNexus
folder ontology: law-nexus.ttl
```

Avoid in v0:

```yaml
adaptive: true
init_prompts: ...
harness: ...
raw_mirror: ...
```

Rationale:

```text
S01 found deterministic domain-folder kits reusable; S02 found configured-kit ontology and generated shapes are the operational center. Adaptive/schema-owning behavior is not acceptable for v0 ACP/legal proof boundaries.
```

## Folder layout sketch

Synthetic examples only:

```text
LawNexus/
  LegalDocument/
    example-legal-document.md
  SourceProvider/
    example-source-provider.md
  ParserRun/
    example-parser-run.md
  SourceBlock/
    example-source-block.md
  EvidenceSpan/
    example-evidence-span.md
  Citation/
    example-citation.md
  RetrievalQuery/
    example-retrieval-query.md
  RetrievalAnswer/
    example-retrieval-answer.md
  FalkorDBGraphObservation/
    example-falkordb-graph-observation.md
  CypherSafetyCheck/
    example-cypher-safety-check.md
```

Each example must include a clear non-authoritative marker, for example:

```yaml
lawNexus.synthetic: true
lawNexus.nonAuthoritative: true
lawNexus.proofStatus: "example-only"
```

Do not include these blocked paths or payload categories:

```text
Raw/ (blocked)
.artifacts/ (blocked)
provider payload dumps (blocked)
raw legal text blobs (blocked)
session logs (blocked)
absolute local anchors (blocked)
ignored/local proof paths (blocked)
```

## Candidate v0 classes

| Class | Purpose | Allowed proof claim |
|---|---|---|
| `LegalDocument` | Describes a legal source document identity and safe metadata. | May describe a synthetic or referenced document record; does not prove parser completeness. |
| `SourceProvider` | Describes source provenance category such as Garant or Consultant-style source. | May classify provider/source family; does not validate provider ingestion behavior. |
| `ParserRun` | Describes an observed parser run or planned parser proof. | May link to accepted runtime evidence; does not validate parser quality by itself. |
| `SourceBlock` | Describes a bounded structural block extracted from a source. | May support navigation; does not become legal text authority. |
| `EvidenceSpan` | Describes a citation-safe evidence span or selector. | May point to accepted evidence anchors; must not store large raw text blobs. |
| `Citation` | Describes citation metadata used by retrieval answers. | May support citation formatting; does not prove answer correctness. |
| `RetrievalQuery` | Describes an observed retrieval query or test case. | May support evaluation traceability; not a legal conclusion. |
| `RetrievalAnswer` | Describes a generated or deterministic answer artifact. | Non-authoritative unless accepted by a separate proof gate. |
| `FalkorDBGraphObservation` | Describes graph/runtime observations. | May record observed graph state or smoke proof; not a FalkorDB capability claim without source/runtime evidence. |
| `CypherSafetyCheck` | Describes query-safety checks or blocked query classes. | May support safety audit; does not validate full Legal KnowQL behavior. |
| `ACPBoundaryLink` | Describes diagnostic relation to ACP SourceRecord, Decision, Requirement, or ProofGate. | Navigation/linkage only; ACP artifacts remain authoritative. |

## Candidate v0 properties

Use explicit domain/range declarations from v0. These are design names, not implemented names.

| Property | Kind | Domain | Range / type | Notes |
|---|---|---|---|---|
| `lawNexus:documentId` | datatype | `LegalDocument` | `xsd:string` | Stable local identifier, not external authority by itself. |
| `lawNexus:sourcePath` | datatype | `LegalDocument`, `ParserRun`, `EvidenceSpan` | `xsd:string` | Must be repository-relative when durable. |
| `lawNexus:provider` | object | `LegalDocument`, `ParserRun` | `SourceProvider` | Object link, not provider-proof. |
| `lawNexus:observedAt` | datatype | `ParserRun`, `FalkorDBGraphObservation`, `CypherSafetyCheck` | `xsd:dateTime` | Runtime observation timestamp if proven. |
| `lawNexus:parserName` | datatype | `ParserRun` | `xsd:string` | Identifies parser/tool under proof. |
| `lawNexus:parserVersion` | datatype | `ParserRun` | `xsd:string` | Optional version/commit text. |
| `lawNexus:sourceBlock` | object | `EvidenceSpan`, `Citation` | `SourceBlock` | Navigation link. |
| `lawNexus:cites` | object | `RetrievalAnswer` | `Citation` | Citation linkage, not correctness. |
| `lawNexus:answersQuery` | object | `RetrievalAnswer` | `RetrievalQuery` | Evaluation linkage. |
| `lawNexus:supportsAcpGate` | object | `ParserRun`, `EvidenceSpan`, `CypherSafetyCheck`, `FalkorDBGraphObservation` | `ACPBoundaryLink` | Diagnostic support link only. |
| `lawNexus:nonAuthoritative` | datatype | all v0 example classes | `xsd:boolean` | Should be true for examples/projections until accepted otherwise. |
| `lawNexus:proofStatus` | datatype | all v0 example classes | `xsd:string` | Avoid hard enum claims until `sh:in` failure proof exists. |

## Generated-shape constraints target

Future scaffold should make shape generation useful by using triples that git-lex currently consumes:

```text
owl:Class for each v0 class
owl:DatatypeProperty / owl:ObjectProperty for each property
rdfs:domain for every property that should appear in class templates/shapes
rdfs:range for datatype and object property typing
```

Required fields may be introduced later using:

```text
owl:Restriction
owl:onProperty
owl:minCardinality or owl:cardinality
```

But v0 design should not claim enforcement until runtime proof shows generated `sh:minCount` and a true negative `git-lex validate` failure.

Enum fields may be introduced later using:

```text
rdfs:Datatype
owl:oneOf
```

But v0 design should not claim enforcement until runtime proof shows generated `sh:in` and a true negative `git-lex validate` failure.

## ACP boundary link model

law-nexus-kit may link to ACP concepts, but the authority direction must remain one-way:

```text
law-nexus observation -> supports/navigation link -> ACP proof gate/source/decision
```

not:

```text
law-nexus projection -> validates ACP requirement
```

Safe wording:

```text
This law-nexus-kit record is a diagnostic profile evidence projection that may support ACP review when paired with accepted source/runtime proof.
```

Unsafe wording:

```text
Unsafe wording: This law-nexus-kit record validates R035/R037/R038.
```

```text
ACP proof gates are satisfied because the law-nexus-kit projection exists.
```

```text
git-lex validation proves Russian legal parser completeness.
```

## Future scaffold proof gates

Before any implementation can be accepted, a future scaffold milestone should prove all of the following in an isolated disposable repository:

```text
1. explicit full kit spec install works
2. base plus law-nexus configured kit state is created
3. no main `.lex`, `Raw`, `Squad`, or `.artifacts` residue appears
4. `git lex list --json` discovers law-nexus classes from generated shapes
5. synthetic examples validate positively
6. sync/query can retrieve safe frontmatter fields
7. generated shape file contains expected target classes and properties
8. at least one true negative validation fixture fails before any hard validation claim
9. proof anchors remain repository-relative and do not use ignored/local/raw/secret artifacts
```

If static ACP imports or copied ACP terms are used, the scaffold milestone must additionally prove:

```text
10. generated shapes see the intended ACP-linked triples
11. imported/copied ACP terms do not invert authority or validate law-nexus profile requirements
```

## S03 design conclusion

law-nexus-kit v0 is feasible only as a bounded configured-domain-kit design:

```text
configured domain kit
static/profile semantics
synthetic examples only
explicit domain/range-driven shapes
ACP boundary links as diagnostic navigation
no native dependency-chain assumption
no adaptive/raw/session authority
no source-truth migration
no R035/R037/R038 validation
```

This gives S04 a safe synthesis path: proceed to a future scaffold proof only after accepting the configured-domain-kit interpretation and keeping ACP/native proof gates authoritative.
