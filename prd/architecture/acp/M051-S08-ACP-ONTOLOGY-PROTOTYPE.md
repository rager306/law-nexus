# M051 S08 ACP Ontology Prototype

## Status

In progress for `M051-q6ctvc / S08`.

This artifact records the proposed ACP ontology prototype, sample records, audit queries, verifier results, JSON-LD decision, and SHACL/OWL subset decision for S08.

## Scope and guardrails

S08 materializes an ACP semantic integration prototype over git-lex vocabulary evidence while preserving ACP-native authority.

Hard boundaries:

- The prototype is proposed and non-authoritative.
- The prototype does not initialize or mutate `/root/law-nexus/.lex`.
- RDF, OWL, SHACL, SPARQL, JSON-LD, git-lex output, dashboards, and recovery views remain derived unless tied to ACP source records, lifecycle state, evidence anchors, and proof gates.
- The prototype does not validate R035, R037, or R038.
- Runtime-backed claims must remain within the M051/S10 evidence boundary.

## T01: Proposed ACP ontology prototype

### Created artifact

```text
prd/architecture/acp/ontology/M051-ACP-GIT-LEX-PROTOTYPE.ttl
```

The ontology declares:

```text
<urn:law-nexus:acp:prototype:m051>
  a owl:Ontology ;
  acp:nonAuthoritative true ;
  acp:blockedRequirementValidation "R035", "R037", "R038" .
```

### Core classes

The prototype defines these ACP classes:

| Class | Mapping | Rationale |
|---|---|---|
| `acp:SourceRecord` | `rdfs:subClassOf lex:Document` | ACP source records are tracked documents/records, but authority comes from ACP lifecycle/proof gates. |
| `acp:Requirement` | `rdfs:subClassOf acp:SourceRecord` | Requirements are ACP-native source records. |
| `acp:Decision` | `rdfs:subClassOf acp:SourceRecord, lex:Decision` | Decisions can reuse git-lex decision semantics while preserving ACP authority. |
| `acp:EvidenceAnchor` | `rdfs:subClassOf lex:Reference` | Evidence anchors point to tracked source/proof locations. |
| `acp:ProofGate` | `rdfs:subClassOf lex:Process` | Proof gates are executable or checkable processes. |
| `acp:HealthFinding` | `rdfs:subClassOf lex:Information` | Diagnostics are first-class information, not validation by themselves. |
| `acp:Projection` | `rdfs:subClassOf lex:Information` | RDF/SHACL/SPARQL/JSON-LD outputs are derived information. |
| `acp:LifecycleState` | `rdfs:subClassOf lex:Concept` | States such as proposed/accepted/blocked/deferred are concepts. |
| `acp:AuthorityClass` | `rdfs:subClassOf lex:Concept` | Authority classes distinguish source, projection, runtime-smoke, and diagnostic evidence. |
| `acp:ValidationClaim` | `rdfs:subClassOf lex:Information` | Validation claims are explicit records, not inferred from shape alone. |
| `acp:ProfileConstraint` | `rdfs:subClassOf lex:Concept` | law-nexus-specific constraints remain outside ACP core. |
| `acp:RuntimeAdapter` | `rdfs:subClassOf lex:Process` | git-lex integration is an optional adapter process, not ACP core runtime. |

### Core properties

The prototype defines object properties for:

- source record to evidence anchor: `acp:hasEvidenceAnchor`;
- source record to proof gate: `acp:requiresProofGate`;
- evidence anchor to proof gate: `acp:satisfiesProofGate`;
- health finding to validation claim: `acp:blocksClaim`;
- validation claim to requirement: `acp:validatesRequirement` and `acp:doesNotValidateRequirement`;
- projection provenance: `acp:derivedFrom`;
- lifecycle and authority classification: `acp:hasLifecycleState`, `acp:hasAuthorityClass`;
- law-nexus profile boundaries: `acp:constrainedByProfile`;
- optional runtime adapter boundaries: `acp:implementedByAdapter`;
- git provenance references: `acp:observedInCommit`.

The prototype defines datatype properties for:

- `acp:identifier`;
- `acp:sourcePath`;
- `acp:selector`;
- `acp:nonAuthoritative`;
- `acp:blockedRequirementValidation`;
- `acp:allowedNextAction`;
- `acp:blockedAction`;
- `acp:proofLevel`;
- `acp:verdict`;
- `acp:sourceArtifact`.

### Git-lex vocabulary usage

The prototype imports no runtime state and does not require `.lex` in the main repository. It references these git-lex namespaces as vocabulary prior art:

- `lex:` for document, decision, reference, information, process, concept, and relationship patterns;
- `git:` for commit provenance references;
- `fm:` for lightweight path/status/title-style metadata;
- `squad:` as a declared prefix for later sample/audit comparison, but not as ACP core dependency.

### Runtime adapter boundary

The prototype includes:

```text
acp:gitLexRuntimeAdapter a acp:RuntimeAdapter
```

It is explicitly deferred and blocked from:

- mutating `/root/law-nexus/.lex`;
- validating R035/R037/R038 from git-lex output.

Allowed next action is only an isolated adapter proof in `/tmp` or a dedicated worktree.

### T01 conclusion

T01 creates the minimal proposed ACP ontology prototype needed for S08. It links selected ACP concepts to git-lex semantics where justified, but preserves the M045/S05/S10 authority boundary: ontology shape is not source truth, projections are derived, and LegalGraph/law-nexus requirement validation stays proof-gated.

## T01 verification notes

T01 satisfies the draft ontology gate when the prototype file exists and contains `acp:SourceRecord`, `acp:Requirement`, `acp:Decision`, `acp:EvidenceAnchor`, `acp:ProofGate`, `acp:HealthFinding`, `acp:Projection`, `acp:ProfileConstraint`, `rdfs:subClassOf`, and `lex:`.

## T02: Sample ACP records and JSON-LD context decision

### Created artifacts

```text
prd/architecture/acp/examples/M051-ACP-SAMPLE-RECORDS.ttl
prd/architecture/acp/examples/M051-ACP-SAMPLE-RECORDS.jsonld
```

### Sample coverage

The Turtle sample records instantiate the T01 prototype with:

| Required sample | Record |
|---|---|
| One requirement | `ex:req-r035 a acp:Requirement` |
| One decision | `ex:decision-keep-acp-native a acp:Decision` |
| One evidence anchor | `ex:anchor-s10-runtime-gate a acp:EvidenceAnchor` plus additional anchors |
| One proof gate | `ex:gate-no-main-lex` and `ex:gate-r035-real-proof` |
| One health finding | `ex:finding-negative-validation-unproven` |
| One derived projection | `ex:projection-s08-samples a acp:Projection` |
| One blocked runtime adapter | `ex:adapter-git-lex-blocked a acp:RuntimeAdapter` |
| R035/R037/R038 non-validation examples | `ex:claim-r035-non-validation`, `ex:claim-r037-non-validation`, `ex:claim-r038-non-validation` |

### Evidence-anchor safety

The sample uses tracked repository-relative anchors only:

```text
prd/architecture/acp/M051-S05-GIT-LEX-ACP-INTEGRATION-DECISION.md
prd/architecture/acp/M051-S10-GIT-LEX-BINARY-RUNTIME-GATE.md
prd/architecture/acp/ontology/M051-ACP-GIT-LEX-PROTOTYPE.ttl
```

It does not use:

- absolute local proof paths;
- `.gsd/exec` as durable proof anchors;
- ignored paths;
- raw provider payloads;
- raw secrets;
- raw vectors;
- raw legal text.

### JSON-LD context decision

T02 creates a JSON-LD sample and local context in:

```text
prd/architecture/acp/examples/M051-ACP-SAMPLE-RECORDS.jsonld
```

Decision: JSON-LD is included as a proposed interchange surface for the ACP prototype, but remains non-authoritative and not runtime-verified by git-lex. This satisfies the S08 requirement to create a JSON-LD artifact for the sample records while preserving the S10 boundary that git-lex JSON-LD import/export remains unproven.

The JSON-LD file defines context terms for:

- `acp`, `ex`, `lex`, `git`, `fm`, `rdfs`, `xsd`;
- `id`, `label`, `comment`, `sourcePath`, `selector`, `proofLevel`, `verdict`;
- object links such as `hasEvidenceAnchor`, `requiresProofGate`, `doesNotValidateRequirement`, and `derivedFrom`;
- `nonAuthoritative` as `xsd:boolean`.

### T02 conclusion

T02 supplies concrete fixture records for later S08 audit queries and verifier checks. The samples demonstrate ACP source/proof/health/projection/runtime-adapter boundaries without promoting projection shape, JSON-LD shape, or git-lex runtime smoke into ACP authority.

## T02 verification notes

T02 satisfies the sample/context gate when both sample files exist, the Turtle file contains `R035`, `R037`, `R038`, `non-validation`, `EvidenceAnchor`, `ProofGate`, `Projection`, and `RuntimeAdapter`, the JSON-LD file parses as JSON, and no forbidden durable anchors appear.

## T03: Semantic audit query pack

### Created artifacts

```text
prd/architecture/acp/sparql/m051/find_projection_only_validations.rq
prd/architecture/acp/sparql/m051/find_decisions_without_proof_gate.rq
prd/architecture/acp/sparql/m051/find_unsafe_evidence_anchors.rq
prd/architecture/acp/sparql/m051/find_law_nexus_requirement_overclaims.rq
prd/architecture/acp/sparql/m051/find_blocked_runtime_adoption.rq
prd/architecture/acp/sparql/m051/trace_decision_to_evidence.rq
```

### Query intent

| Query | ACP risk detected |
|---|---|
| `find_projection_only_validations.rq` | A requirement is claimed validated only because a projection exists, without proof gate/evidence linkage. |
| `find_decisions_without_proof_gate.rq` | An accepted decision lacks a proof gate. |
| `find_unsafe_evidence_anchors.rq` | An evidence anchor points to absolute paths, `.gsd/exec`, raw provider payloads, secrets, raw vectors, or raw legal text. |
| `find_law_nexus_requirement_overclaims.rq` | R035/R037/R038 are claimed validated without profile-specific proof. |
| `find_blocked_runtime_adoption.rq` | A runtime adapter such as git-lex is accidentally promoted or still carries blocked actions. |
| `trace_decision_to_evidence.rq` | Recovery/audit query tracing decisions to proof gates and source anchors. |

### T03 conclusion

T03 creates a SPARQL audit pack for the prototype's main policy risks. The queries are handoff artifacts and static audit specifications until T04/T05 verifier work decides how much can be checked deterministically without adding a heavy RDF/SPARQL dependency.

## T03 verification notes

T03 satisfies the audit-query gate when the `prd/architecture/acp/sparql/m051` directory exists and the query files contain `SELECT`, `ASK` or `CONSTRUCT`-style query text plus risk terms for `R035`, `R037`, `R038`, `Projection`, `ProofGate`, and `EvidenceAnchor`.

## T04: Prototype verifier

### Created artifact

```text
scripts/verify-m051-s08-acp-ontology-prototype.py
```

### Verifier scope

The verifier is dependency-light and deterministic. It checks:

- required prototype files exist;
- required ACP ontology classes are present;
- required ACP ontology properties are present;
- ontology carries a non-authoritative marker;
- R035/R037/R038 boundaries are present;
- sample Turtle records contain required coverage terms;
- JSON-LD sample parses as JSON and contains `@context` plus non-empty `@graph`;
- all required query pack files exist;
- query files contain SPARQL query forms and risk comments;
- sample evidence anchors avoid forbidden durable anchor patterns;
- `/root/law-nexus/.lex` is absent.

### Verifier limitations

The verifier intentionally records parse limitations instead of implying stronger proof:

```text
Turtle and SPARQL are checked structurally without an RDF/SPARQL engine dependency.
JSON-LD is JSON-parsed for shape only; expansion/compaction is not verified.
```

This keeps T04 inside the S08 `prototype + static-check` proof level.

### First run result

Command:

```bash
uv run python scripts/verify-m051-s08-acp-ontology-prototype.py
```

Result:

```json
{
  "status": "ok",
  "failure_count": 0,
  "non_authoritative": true
}
```

The full output was captured in:

```text
.gsd/exec/cc52342c-b551-4f7f-b824-eaa0e2a60bbf.stdout
```

### T04 conclusion

T04 adds a static verifier that can be used by T05/T06 and downstream slices to keep the prototype bounded. It does not claim RDF engine execution, JSON-LD semantic expansion, SHACL validation, or git-lex runtime adoption.

## T04 verification notes

T04 satisfies the verifier gate when `uv run python scripts/verify-m051-s08-acp-ontology-prototype.py` exits 0 with `status: ok` and `failure_count: 0`.

## T05: Verifier result and prototype limits

### Fresh verifier result

Command:

```bash
uv run python scripts/verify-m051-s08-acp-ontology-prototype.py
```

Fresh result for T05:

```json
{
  "status": "ok",
  "failure_count": 0,
  "non_authoritative": true,
  "diagnostics": []
}
```

Output anchor:

```text
.gsd/exec/b35b3804-d664-4c06-b64a-dada51b8291f.stdout
```

### Verdict

```text
verdict: static prototype check passed
proof level: static-check
non-authoritative: true
```

### What the prototype proves

The S08 prototype currently proves only static artifact presence and policy coverage:

- proposed ACP ontology file exists;
- required ACP classes and properties are present;
- ontology carries non-authoritative and R035/R037/R038 boundary markers;
- sample Turtle records cover requirement, decision, evidence anchor, proof gate, health finding, projection, runtime adapter, and non-validation examples;
- JSON-LD sample has parseable JSON with `@context` and `@graph`;
- SPARQL audit pack files exist and carry risk comments;
- static checks reject forbidden durable anchor patterns in sample `acp:sourcePath` values;
- `/root/law-nexus/.lex` remains absent.

### What the prototype does not prove

The prototype does not prove:

- ACP ontology correctness;
- full RDF/Turtle parsing by an RDF engine;
- SPARQL execution by a SPARQL engine;
- JSON-LD expansion, compaction, framing, or round-trip behavior;
- SHACL validation semantics;
- OWL entailment or lossless SHACL/OWL subset behavior;
- git-lex runtime adoption;
- negative validation support;
- JSON-LD support in git-lex;
- SPARQL-star compatibility;
- FalkorDB ingest/runtime behavior;
- Russian legal parser completeness;
- citation-safe retrieval quality;
- legal answer correctness;
- R035, R037, or R038 validation.

### JSON-LD status

JSON-LD is created as a proposed ACP interchange/sample artifact:

```text
prd/architecture/acp/examples/M051-ACP-SAMPLE-RECORDS.jsonld
```

It is verified only as JSON shape:

```text
JSON-LD is JSON-parsed for shape only; expansion/compaction is not verified.
```

Therefore JSON-LD is not deferred as a file artifact, but semantic JSON-LD processing remains deferred/unproven.

### Consumption guidance

#### S05

S05 remains the accepted architecture decision boundary: ACP source authority stays ACP-native; git-lex is prior art and optional adapter candidate. S08 does not supersede S05.

#### S06

S06 may consume the ontology/report/query-pack vocabulary for skill updates, but must preserve:

- non-authoritative prototype status;
- runtime-backed/source-only/unproven split from S10;
- no-main-repo `.lex` policy;
- R035/R037/R038 non-validation boundaries.

#### S07

S07 may use the prototype findings as roadmap input for future ACP hardening. It should treat unresolved areas as backlog/proof gates, especially:

- negative SHACL validation;
- JSON-LD semantic processing;
- SPARQL-star user-facing proof;
- git-lex adapter adoption;
- profile-specific law-nexus proofs.

### T05 conclusion

T05 documents that the prototype has passed static verification and is useful as a proposed semantic/audit scaffold, not as source truth or requirement-validation proof. It is ready for T06's SHACL/OWL subset role decision.

## T05 verification notes

T05 satisfies the documentation gate when the verifier exits 0 and this report contains `verdict`, `proves`, `does not prove`, `JSON-LD`, `non-authoritative`, `S05`, `S06`, and `S07`.

## T06: SHACL and OWL subset role decision

### Evidence reviewed

T06 reviewed git-lex's SHACL/OWL subset guidance and source implementation:

```text
/root/vendor-source/git-lex/docs/2026_04_21_SHACL_OWL_LOSSLESS_SUBSET.md
/root/vendor-source/git-lex/src/shacl.rs
GitNexus: build_shacl_shapes, generate_shacl_shapes
```

Key source findings:

- git-lex treats SHACL shapes as the primary runtime schema input for frontmatter extraction and validation.
- Kit OWL ontologies are optional authoring/input artifacts; git-lex runtime reads generated shapes.
- The lossless subset includes class declarations, datatype/object properties, ranges, domains, cardinality, enum values, fixed values, functional properties, and simple boolean combinations.
- SHACL-only constructs such as `sh:pattern`, `sh:sparql`, `sh:closed`, `sh:message`, and UI metadata are not lossless OWL equivalents.
- OWL-only constructs such as `rdfs:subClassOf`, equivalence, disjointness, property characteristics, inverse properties, and property chains are not lossless SHACL equivalents.
- `generate_shacl_shapes()` loads kit ontology TTL into an Oxigraph store and derives NodeShape/property constraints from OWL classes/properties/restrictions.
- `build_shacl_shapes()` writes generated shapes next to the kit/adaptive ontology source.

### Decision

ACP should use a layered validation model:

```text
OWL/Turtle prototype        -> vocabulary and relationship documentation
minimal SHACL shapes        -> static structural smoke for source/projection records
SPARQL policy audit pack    -> explicit governance-risk queries
Python verifier             -> deterministic dependency-light CI/static check
runtime git-lex adapter     -> deferred optional proof surface only
```

This means:

1. OWL/Turtle is useful for declaring ACP vocabulary and git-lex mappings.
2. SHACL is useful for minimal source/projection shape smoke, especially required properties and non-authoritative markers.
3. SPARQL policy audits are best for ACP governance risks: projection-only validation, unsafe anchors, missing proof gates, overclaims, and runtime adoption drift.
4. The Python verifier remains the current executable proof layer because it runs without heavyweight RDF dependencies.
5. git-lex SHACL runtime remains adapter-later, not ACP core validation, until negative validation and runtime adoption are separately proven.

### Added SHACL artifact

T06 adds minimal proposed SHACL shapes:

```text
prd/architecture/acp/shacl/m051/acp-prototype.shacl.ttl
```

The shapes cover:

- `acp:EvidenceAnchorShape` requiring `acp:sourcePath` and `acp:proofLevel`;
- `acp:SourceRecordShape` requiring `acp:hasLifecycleState`;
- `acp:ProjectionShape` requiring `acp:nonAuthoritative` and `acp:derivedFrom`;
- `acp:RuntimeAdapterShape` requiring `acp:hasLifecycleState`.

These shapes are proposed static-check scaffolding only. They do not prove full ontology correctness, SHACL engine behavior, or git-lex validation semantics.

### Verifier update

The S08 verifier now checks the SHACL file for required structural terms:

```text
acp:EvidenceAnchorShape
acp:SourceRecordShape
acp:ProjectionShape
acp:RuntimeAdapterShape
sh:targetClass
sh:property
sh:minCount
```

Fresh verifier run:

```bash
uv run python scripts/verify-m051-s08-acp-ontology-prototype.py
```

Result:

```json
{
  "status": "ok",
  "failure_count": 0,
  "non_authoritative": true
}
```

Output anchor:

```text
.gsd/exec/d843a37c-e103-43ff-b81a-71984127ac31.stdout
```

### Supported, blocked, deferred

| Layer | Role | Status |
|---|---|---|
| OWL/Turtle prototype | Vocabulary, class/property mapping, non-authoritative declarations | supported as proposed static artifact |
| Minimal SHACL shapes | Static structural smoke for anchors, source records, projections, runtime adapter lifecycle | supported as proposed static artifact |
| SPARQL policy audit pack | Governance risk detection and recovery handoff | supported as static audit specification |
| Python verifier | Current executable static-check layer | supported and passing |
| RDF/SPARQL engine execution | Engine-level proof of Turtle/SPARQL semantics | deferred |
| JSON-LD expansion/round-trip | Semantic JSON-LD processing | deferred |
| git-lex SHACL runtime validation | Adapter runtime proof | blocked/deferred until negative validation and adoption gates pass |
| ACP requirement validation | R035/R037/R038 status changes | blocked; requires profile-specific proof outside this prototype |

### T06 conclusion

S08 should keep a layered validation approach. The current slice may claim static-check proof for the proposed ontology, samples, query pack, JSON shape, and minimal SHACL shape presence. It must not claim SHACL engine validation, OWL entailment, JSON-LD semantic processing, git-lex adapter adoption, or law-nexus requirement validation.

## T06 verification notes

T06 satisfies the SHACL/OWL decision gate when the report contains `SHACL`, `OWL`, `lossless subset`, `SPARQL policy audit`, `layered validation`, `deferred`, `supported`, and `blocked`, and when `uv run python scripts/verify-m051-s08-acp-ontology-prototype.py` exits 0.
