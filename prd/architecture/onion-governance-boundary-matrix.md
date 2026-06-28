# Onion Governance Boundary Matrix

**Milestone:** M076-f3zxm8  
**Status:** [bounded] governance control artifact  
**Depends on:** `prd/architecture/onion-migration-contract.md`, `doc/adr/0003-library-boundary-contract.md`  
**Purpose:** make source-truth, projection, proof, package, and runtime authority boundaries explicit for the onion migration program.

## Scope

This matrix governs how agents and maintainers may cite architecture, proof, and product state during the M076 wrapper-first migration. It does not introduce new runtime behavior. It prevents drift where a derived projection, diagnostic, local smoke, generated query, embedding score, or script report is accidentally treated as legal truth, product proof, or production readiness.

## Source-truth hierarchy

| Rank | Source | May validate requirements? | May validate architecture claims? | Boundary |
|---:|---|---:|---:|---|
| 1 | Accepted PRD, ADR, GSD requirements, and recorded decisions | Yes, when the requirement explicitly cites them as normative | Yes | Normative planning and decision truth. Must still be matched with runtime/source evidence for implementation claims. |
| 2 | Source code under `src/law_nexus/`, stable `scripts/*.py` wrappers, and tests | Partially, when paired with passing targeted verification | Partially | Implementation truth for deterministic mechanics only. Does not prove legal correctness by itself. |
| 3 | Runtime proof artifacts from tracked fixtures, local scripts, and accepted UAT evidence | Partially, for the verified scenario only | Partially | Scenario-bounded evidence. Must state fixture/runtime boundary and failure class. |
| 4 | Architecture registry/verifier outputs and generated reports | No, unless backed by rank 1-3 evidence | Partially, as diagnostic support | Derived governance diagnostics. They can detect drift but cannot be source truth alone. |
| 5 | ACP, git-lex, RDF, JSON-LD, SPARQL, recovery views, and projection helpers | No | No, unless only restating their own projection mechanics | Non-authoritative projections/recovery surfaces. They do not validate product, legal, parser, retrieval, or runtime claims. |
| 6 | LLM output, generated Cypher, embeddings, ranking scores, and model-provider responses | No | No | Non-authoritative signals only. Must be validated by deterministic policy/tests/runtime proof before use. |

## Boundary matrix

| Artifact or layer | Lifecycle now | Allowed claims | Forbidden claims | Required proof anchor |
|---|---|---|---|---|
| `prd/ARCHITECTURE.md`, PRD docs, ADRs, GSD requirements/decisions | [validated] when accepted; otherwise [proposed] | Scope, intent, accepted decisions, source-truth hierarchy | Runtime success, parser completeness, legal correctness, retrieval quality | Tracked PRD/ADR/GSD artifact path and decision/requirement id when available |
| `prd/architecture/onion-migration-contract.md` | [bounded] | Wrapper-first migration rules and onion package boundary | Completion of downstream slices or production readiness | Tracked contract path plus slice/task verification |
| `src/law_nexus/domain` | [proposed] to [validated] per model/test evidence | Pure model invariants and deterministic transformations covered by tests | External IO, parser completeness, legal authority | Source file + targeted tests |
| `src/law_nexus/ports` | [bounded] | Protocol shape and non-claim contract | Adapter behavior, runtime availability, external service behavior | Source file + import-linter/type tests |
| `src/law_nexus/application` | [bounded] or [validated] per slice | Deterministic use-case behavior under tests | Adapter availability, provider behavior, graph runtime behavior | Source file + targeted tests + wrapper compatibility gate |
| `src/law_nexus/adapters` | [bounded] until runtime proof | Infrastructure adapter behavior for verified local/runtime scenario | Production readiness, network availability, managed provider correctness | Source file + adapter tests + local runtime proof when available |
| `src/law_nexus/composition.py` | [bounded] | Explicit wiring choices | Hidden dependency injection framework, runtime proof by existence | Source file + composition tests |
| Stable `scripts/*.py` wrappers | [bounded] or [validated] per script proof | CLI/report compatibility and scenario-specific proof | Package architecture truth, product completeness, legal correctness | Script path + command output + tracked report when generated |
| Architecture registry/verifier/remediation outputs | [bounded] diagnostic | Drift detection, missing proof anchors, decision fitness warnings | Requirement validation by themselves | Generated report + upstream PRD/ADR/source/test proof |
| ACP/git-lex/RDF/SPARQL/JSON-LD projections | [bounded] diagnostic/recovery | Projection mechanics, recovery navigation, relationship discovery | Source truth, requirement validation, legal/runtime proof | Projection artifact + original source record/proof anchor |
| Russian legal source fixtures and parser outputs | [bounded] until real-document parser proof validates scope | Fixture-specific extraction behavior and citation spans | Full legal corpus correctness, official legal advice | Tracked fixture/report + parser tests + source provenance |
| FalkorDB graph observations | [bounded] until live runtime proof validates scope | Observed graph behavior for the tested runtime/query only | Neo4j equivalence, GraphBLAS/vector/full-text/UDF availability without proof | Source/runtime evidence + exact query/report |
| Generated Cypher policy (`S16`) | [bounded] static validation | Deterministic acceptance/rejection of candidate query shapes | Generated query correctness, OpenCypher completeness, FalkorDB execution safety | Policy source + tests + existing M002 proof script |
| Local embedding adapter (`S17`) | [bounded] local adapter seam | Local adapter contract, dimension/count validation, managed API exclusion | Model availability, retrieval quality, legal correctness, production vector index readiness | Adapter source + tests + local runtime proof when available |

## Lifecycle tag discipline

Every architecture, state, proof, and capability claim must carry one of these tags when ambiguity is possible:

- `[validated]`: backed by tracked source/test/runtime evidence for the stated scope.
- `[bounded]`: true only inside an explicit fixture, runtime, static policy, diagnostic, or local adapter boundary.
- `[smoke]`: observed through a narrow smoke check; not broad capability proof.
- `[proposed]`: design intent or planned contract not yet validated.
- `[deferred]`: intentionally out of current scope.

Do not smooth `[bounded]`, `[smoke]`, `[proposed]`, or `[deferred]` into `[validated]` in summaries, roadmap prose, generated reports, or agent responses.

## Durable proof-anchor rules

Durable proof anchors must be repository-relative tracked paths or stable GSD evidence ids. They must not rely on local-only absolute paths or ignored raw execution payloads.

Allowed durable anchors:

- PRD/ADR/GSD artifacts committed to the repository.
- Source files under `src/`, stable script wrappers under `scripts/`, and tests under `tests/`.
- Tracked fixture/report artifacts when they intentionally contain no secrets or unnecessary raw legal text.
- GSD UAT/summary ids when cited from GSD artifacts.

Forbidden durable anchors:

- `.gsd/exec/*` stdout/stderr paths as standalone proof in architecture registry records.
- Absolute local paths.
- Secrets, credentials, provider payloads, raw vectors, or unnecessary raw legal text.
- Ignored build/cache artifacts.
- ACP/git-lex projection outputs without the original source/proof anchor.

## Non-claim guardrails

The following must not be claimed from this matrix or from derived governance/projection artifacts alone:

- Legal correctness or authoritative legal advice.
- Parser completeness for Russian legal sources.
- Retrieval quality or answer faithfulness.
- Production FalkorDB readiness.
- Neo4j-to-FalkorDB feature equivalence.
- OpenCypher completeness.
- Generated Cypher correctness or runtime safety.
- Local embedding model availability or embedding quality.
- Managed GigaChat/GigaChat API support in embedding paths.
- Requirement validation from ACP/git-lex/RDF/SPARQL/JSON-LD projections alone.

## S19 handoff

S19 may use this matrix to review ACP projection helper extraction. The expected outcome is not broader ACP authority. The expected outcome is a clearer helper boundary: projection helpers may improve recovery/navigation and drift diagnostics, but they must continue to point back to rank 1-3 proof anchors for validation claims.
