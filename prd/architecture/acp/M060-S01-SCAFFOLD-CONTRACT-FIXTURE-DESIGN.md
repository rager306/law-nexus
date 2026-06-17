# M060/S01: Law-nexus-kit v0 scaffold contract and fixture design

## Status

Design/contract artifact for M060. This slice does not implement the scaffold and does not run git-lex runtime proof.

## Scope and authority boundary

M060/S01 translates M059/S03 and M059/S04 into an implementation contract for future slices. It does not create a law-nexus-kit repository, does not initialize or mutate main `.lex`, does not change external repositories, does not approve source-truth migration, does not approve production adoption, and does not validate R035, R037, or R038.

The scaffold target remains:

```text
law-nexus-kit v0 as a deterministic configured domain kit
```

It is not a native runtime dependency child of ACP-kit:

```text
law-nexus-kit as a native runtime dependency child of ACP-kit
```

ACP-native artifacts, source/runtime proof, tests, accepted decisions, and real-document evidence remain authoritative. law-nexus-kit records are synthetic/diagnostic/profile evidence projections until a future proof gate accepts a specific category.

## Scaffold workspace contract

S02 may create a local scaffold only in one of these safe contexts:

```text
1. a disposable temporary workspace outside the main repository; or
2. an explicitly planned repository-local scaffold directory if GSD/task scope approves it.
```

S01 does not choose the final publishing location. External publishing or GitHub state changes require explicit user confirmation later.

Runtime install proof should use an explicit full kit spec or a clearly documented local equivalent in an isolated target repo. A short alias is not canonical for this project.

Suggested future full spec placeholder:

```text
<owner>/git-lex-kit-law-nexus
```

Do not treat this placeholder as an approved external repository name.

## Intended scaffold file inventory

Future scaffold should contain only deterministic, reviewable files:

```text
git-lex-kit-law-nexus/
  kit.yml
  README.md
  ontology/
    law-nexus/
      law-nexus.ttl
  content/
    AGENTS.md
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
      ACPBoundaryLink/
        example-acp-boundary-link.md
```

Do not include these blocked paths or payload categories:

```text
Raw/ (blocked)
.artifacts/ (blocked)
provider payload dumps (blocked)
raw legal text blobs (blocked)
session logs (blocked)
secrets (blocked)
raw vectors or embeddings (blocked)
absolute local anchors (blocked)
ignored/local proof paths (blocked)
main-checkout `.lex` state (blocked)
```

## Minimal kit.yml contract

Future scaffold should use this minimal deterministic shape:

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
dependencies: ...
```

Rationale:

```text
M059/S02 proved git-lex operates around one configured domain kit plus implicit base. Native dependency layering from ACP-kit is not proven. Therefore law-nexus-kit v0 should be self-contained enough for generated shapes and class discovery.
```

## Ontology contract

Future `ontology/law-nexus/law-nexus.ttl` should define law-nexus profile classes and properties in a namespace that is stable and distinct from ACP core.

Suggested namespace:

```text
https://repolex.ai/ontology/kit/law-nexus/
```

This namespace is a design proposal for isolated proof. It does not create source truth or production adoption by itself.

Minimum ontology expectations:

```text
- owl:Class for each v0 class.
- owl:DatatypeProperty and owl:ObjectProperty for each v0 property.
- rdfs:domain for every property expected to appear in generated class shapes.
- rdfs:range for datatype/object typing.
- no law-nexus-specific terms added to ACP core.
```

Required field and enum constraints may be included only as proof targets:

```text
- owl:Restriction + owl:minCardinality/cardinality for required-field proof.
- rdfs:Datatype + owl:oneOf for enum proof.
```

But hard enforcement claims remain blocked until S03 proves true negative runtime validation.

## Candidate class contract

| Class | Purpose | Example file | Boundary |
|---|---|---|---|
| `LegalDocument` | Synthetic legal-document metadata record. | `LawNexus/LegalDocument/example-legal-document.md` | Does not prove parser completeness. |
| `SourceProvider` | Source/provider category metadata. | `LawNexus/SourceProvider/example-source-provider.md` | Does not prove provider ingestion. |
| `ParserRun` | Synthetic or observed parser-run metadata. | `LawNexus/ParserRun/example-parser-run.md` | Runtime proof required for non-synthetic claims. |
| `SourceBlock` | Bounded structural block reference. | `LawNexus/SourceBlock/example-source-block.md` | No raw legal text blob. |
| `EvidenceSpan` | Citation-safe selector/span metadata. | `LawNexus/EvidenceSpan/example-evidence-span.md` | Selector/navigation only unless accepted by ACP proof. |
| `Citation` | Citation metadata used by answer fixtures. | `LawNexus/Citation/example-citation.md` | Not answer correctness proof. |
| `RetrievalQuery` | Synthetic retrieval query/test case. | `LawNexus/RetrievalQuery/example-retrieval-query.md` | Not Legal KnowQL quality proof. |
| `RetrievalAnswer` | Synthetic answer fixture. | `LawNexus/RetrievalAnswer/example-retrieval-answer.md` | Non-authoritative. |
| `FalkorDBGraphObservation` | Synthetic or observed graph-state metadata. | `LawNexus/FalkorDBGraphObservation/example-falkordb-graph-observation.md` | Not FalkorDB capability proof without runtime/source evidence. |
| `CypherSafetyCheck` | Synthetic Cypher safety check metadata. | `LawNexus/CypherSafetyCheck/example-cypher-safety-check.md` | Not full Legal KnowQL validation. |
| `ACPBoundaryLink` | Diagnostic link to ACP proof/source/decision concepts. | `LawNexus/ACPBoundaryLink/example-acp-boundary-link.md` | Navigation only; ACP artifacts remain authoritative. |

## Candidate frontmatter/property contract

Use safe, synthetic, repository-relative fields. Candidate names are design targets; implementation may refine them if S02 records why.

| Field | Intended property | Type target | Applies to | Notes |
|---|---|---|---|---|
| `lawNexus.synthetic` | `lawNexus:synthetic` | `xsd:boolean` | all examples | Must be true for synthetic fixtures. |
| `lawNexus.nonAuthoritative` | `lawNexus:nonAuthoritative` | `xsd:boolean` | all examples | Must be true unless a future accepted proof says otherwise. |
| `lawNexus.proofStatus` | `lawNexus:proofStatus` | string or enum target | all examples | Enum enforcement must wait for negative proof. |
| `lawNexus.sourcePath` | `lawNexus:sourcePath` | `xsd:string` | document, block, span, parser run | Durable paths must be repo-relative and safe. |
| `lawNexus.documentId` | `lawNexus:documentId` | `xsd:string` | LegalDocument | Synthetic ID only in v0. |
| `lawNexus.provider` | `lawNexus:provider` | object IRI | LegalDocument, ParserRun | Link to SourceProvider. |
| `lawNexus.observedAt` | `lawNexus:observedAt` | `xsd:dateTime` | ParserRun, graph observation, safety check | Runtime observation only if proven. |
| `lawNexus.parserName` | `lawNexus:parserName` | `xsd:string` | ParserRun | Synthetic or observed parser name. |
| `lawNexus.cites` | `lawNexus:cites` | object IRI | RetrievalAnswer | Link to Citation. |
| `lawNexus.answersQuery` | `lawNexus:answersQuery` | object IRI | RetrievalAnswer | Link to RetrievalQuery. |
| `lawNexus.supportsAcpGate` | `lawNexus:supportsAcpGate` | object IRI | observations/checks/spans | Diagnostic support link only. |

## Synthetic fixture contract

All S02 fixtures should be synthetic and bounded:

```yaml
lawNexus.synthetic: true
lawNexus.nonAuthoritative: true
lawNexus.proofStatus: "example-only"
```

Allowed fixture content:

```text
short synthetic titles
repo-relative safe paths
synthetic IDs
small selector examples
safe timestamps
links between synthetic records
```

Blocked fixture content:

```text
raw legal text
provider payloads
secrets
absolute local paths
ignored/local artifacts
raw model outputs treated as proof
raw vectors/embeddings
claims validating R035/R037/R038
```

## Positive runtime proof gates for S02

S02 should prove these gates in an isolated disposable target repo:

```text
P1: scaffold can be installed as the configured domain kit
P2: install creates base plus law-nexus kit state
P3: generated law-nexus shapes exist
P4: generated shapes contain expected target classes and selected properties
P5: git lex list --json discovers law-nexus classes
P6: synthetic examples validate positively
P7: sync/query retrieve safe frontmatter fields
P8: main checkout has no `.lex`, Squad, Raw, or `.artifacts` residue after proof
```

If full owner/repo install is not possible in S02 because the kit is local-only, S02 must document the local equivalent and keep external publishing blocked.

## Negative validation proof plan for S03

S03 should attempt at least one true negative fixture. Preferred negative targets:

```text
N1: boolean field malformed, e.g. lawNexus.synthetic: "not-a-boolean"
N2: dateTime field malformed, e.g. lawNexus.observedAt: "not-a-date"
N3: required field omitted if generated sh:minCount exists
N4: enum value outside allowed values if generated sh:in exists
```

Interpretation rules:

```text
- If a malformed fixture fails validation, hard validation claim is allowed only for that specific proven constraint.
- If malformed fixtures pass, record the root cause and keep hard validation claims blocked.
- Do not generalize one passing or failing fixture to all ACP/law-nexus validation behavior.
- Do not validate R035/R037/R038 from law-nexus-kit fixtures.
```

## Durable proof-anchor policy

Allowed durable proof anchors:

```text
tracked repo-relative artifacts under prd/architecture/acp/
tracked scaffold files if S02 creates them in repo scope
tracked test/verifier files if S02/S03 add them
GSD summaries and validation artifacts by lexical `.gsd/...` path only when appropriate
```

Blocked durable proof anchors:

```text
.gsd/exec outputs (blocked)
absolute local paths (blocked)
ignored/local temporary directories (blocked)
raw provider payloads (blocked)
raw legal text blobs (blocked)
secrets (blocked)
raw vectors or embeddings (blocked)
external repository paths unless separately approved and summarized through tracked artifacts (blocked)
```

## S01 implementation guard

S01 authorizes only design and contract work. It does not authorize:

```text
runtime git-lex init (blocked in S01)
law-nexus-kit publishing (blocked in S01)
main checkout `.lex` (blocked)
source-truth migration (blocked; do not authorize)
production adoption (blocked; do not authorize)
R035/R037/R038 validation claims (blocked)
```

## Handoff to S02

S02 may implement the scaffold only if it follows this contract or records a replan explaining why the contract is insufficient. The default safe path is:

```text
1. create minimal deterministic scaffold in an approved local/disposable context
2. use synthetic examples only
3. run runtime proof in disposable target repo
4. record generated shapes/list/validate/sync/query evidence in tracked artifacts
5. verify main checkout residue remains absent
```

## S01 conclusion

M060/S01 defines a bounded scaffold contract. The next slice may build and prove a minimal scaffold, but only under isolated configured-domain-kit semantics and without source-truth, production, or requirement-validation claims.
