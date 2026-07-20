# Python capability parity matrix for the Rust transition

**Status:** `[bounded]` inventory, `baseline_not_frozen` until artifact reconciliation.

**Decisions:** ADR-0004, ADR-0005, ADR-0007; D103–D106.  
**Requirements:** R063–R066.

## Purpose

This document is the behavioral contract for the complete Rust product rewrite.
It does not authorize Python deletion or partial cutover. The current Python
product remains intact until every required row reaches whole-system Rust parity;
then Python product code moves wholesale to `python_archive/`.

The allowed Python repository harness is outside the product parity surface. It
may execute binaries and compare artifacts, but it must not implement any row
below.

## Baseline integrity warning

The M105 closeout reports 15,249 hierarchy records, 1,378 relation candidates,
1,567 norm candidates, and 271 hierarchy nodes in the staging graph. The current
tracked artifacts contain 15,249 hierarchy rows, 1,378 relation rows, **386 norm
rows**, 48 source blocks, 386 norm nodes, and 1,230 unresolved-reference nodes.
This mismatch likely reflects shared single-mode/corpus-mode output paths.

Therefore artifact hashes below are observational only. Before Rust parity work,
a cleanup milestone must:

1. separate single-document and corpus output paths;
2. rebuild the canonical corpus artifacts once;
3. prove deterministic `--check` without mutating tracked outputs;
4. update `prd/ARCHITECTURE.md`, proof JSON, tests, and this matrix together;
5. freeze hashes and semantic counts in a machine-readable manifest.

## Product capability matrix

| Capability | Current Python source | Inputs | Observable outputs | Failure/diagnostic contract | Rust owner | Parity gate |
|---|---|---|---|---|---|---|
| Source fixture inventory and classification | `src/law_nexus/adapters/sources/filesystem_inventory.py`; inventory/probe scripts | Consultant XML, Garant ODT, fixture paths | `source_fixture_inventory.json`, `probe_results.json`, document-type classification | malformed XML, unsupported shape/type, path/provenance diagnostics | `law-nexus-adapters` | identical fixture identities, classifications, reason codes and safe paths |
| Stable source/document identity | `domain/source_document.py`; parser/source adapters | source bytes and metadata | source IDs, source SHA-256, document IDs, FRBR `act_id`/`edition_id` | collision report, missing identity fields | `law-nexus-core` + parser | exact IDs and collision outcomes on all fixtures |
| Consultant WordML parsing | `adapters/parsers/consultant_wordml.py` | Consultant WordML XML | typed document metadata and raw structural blocks | namespace, malformed XML, confinement, missing title/properties | `law-nexus-parser` | structural equality and identical typed errors |
| Hierarchy extraction | `adapters/sources/consultant_hierarchy.py`; `ports/source_hierarchy.py` | raw blocks/text | hierarchy records for razdel/chapter/article/part/clause/subclause and diagnostics | unnumbered markers, parent resolution, zone diagnostics, stable order | `law-nexus-parser` | byte-stable canonical JSONL after normalized serialization; same counts by level/fixture |
| Preamble/appendix zones and diagnostic-only markers | `consultant_hierarchy.py` | block context | zone/counter fields without unauthorized hierarchy emission | preamble/appendix/abzac diagnostics remain non-structural | `law-nexus-parser` | same structural records and diagnostic counters |
| Internal references | `consultant_hierarchy.py`; staging builder | legal text + hierarchy index | internal relation candidates and resolved/unresolved edges | unresolved reason codes, no invented target | parser + application | same candidate set, resolution set and fail-closed unresolved set |
| External references and URLs | `consultant_hierarchy.py`; relation builder | legal text/hyperlinks | external/URL relation candidates | unsafe/malformed target bounded as candidate | parser | same normalized references and evidence excerpts |
| Temporal markers | `consultant_hierarchy.py` | legal text | entry-into-force, invalidity, secrecy markers | marker is candidate/diagnostic, not legal conclusion | parser/core | same marker category, span, source and non-authoritative state |
| Deontic lexemes and NormStatement candidates | `consultant_hierarchy.py`; `domain/norm_statement.py`; norm builder | legal text | obligation, permission, prohibition candidate records | candidate-only verification state, evidence hash, no legal authority claim | parser/core | same candidate set, modality and evidence anchors after baseline reconciliation |
| Parser-record validation | `adapters/sources/parser_records.py`; JSON schemas | JSON/JSONL records | validated typed records or structured diagnostics | stable reason codes; malformed records fail closed | `law-nexus-core` | positive and negative corpus/golden fixtures produce equivalent results |
| Golden cases | `adapters/sources/parser_golden_cases.py`; golden builder | tracked parser artifacts | evidence/no-answer/candidate-only golden cases | invalid promotion and missing unresolved refs fail closed | application/harness | same case outcomes; Rust cannot promote candidate-only evidence |
| Staging graph construction | `scripts/build-parser-staging-graph.py`; graph adapters | hierarchy, relation, norm artifacts | typed multigraph JSON and counts | diagnostics by severity, unresolved nodes preserved, readiness claims false | `law-nexus-app` + adapters | canonical graph equality and same diagnostic classes |
| FalkorDB graph access/ingestion | `ports/graph_store.py`; `adapters/graph/`; proof scripts | typed graph records | parameterized graph operations and bounded runtime evidence | connection/query/load errors, idempotency and cleanup surfaces | `law-nexus-adapters` | real FalkorDB integration tests with equivalent counts and cleanup |
| Generated-Cypher safety | domain/application validation and M002/M003 scripts | candidate Cypher + schema/policy | allow/reject decision with reason | fail closed before graph execution; LLM non-authoritative | `law-nexus-core` + application | complete safety corpus has equal-or-stricter rejection behavior |
| Embedding generation | `ports/embedder.py`; `adapters/embeddings/` | bounded source/evidence text | local/open-weight vectors + metadata | model/runtime errors; no managed GigaChat route | `law-nexus-adapters` | shape/dimension/runtime compatibility; quality separately proven |
| Retrieval and EvidenceSpan assembly | retrieval adapters/scripts; `domain/evidence_span.py`, `citation.py` | query, graph/source evidence, embeddings | ranked evidence spans, citations, no-answer output | unresolved evidence or citation fails closed | core/application/adapters | golden, real-artifact and graph-filtered cases match safety contract |
| Citation-safe answer validation | retrieval output validators | candidate answer + evidence graph | verified evidence pack or rejection | no raw legal authority from LLM; every citation resolves | core/application | Rust passes all rejection cases and never weakens evidence requirements |
| Application orchestration | `application/ingest.py`; `composition.py`; product scripts | CLI/request inputs | deterministic pipeline outputs | phase, reason, bounded stderr/diagnostics | `law-nexus-app` | end-to-end corpus and failure scenarios |
| Product CLI/binaries | product-facing build/verify scripts | explicit CLI args | stable JSON/human reports and exit codes | timeouts, malformed args, no secret/path leaks | `law-nexus-app/src/bin` | CLI contract tests and artifact parity |
| Observability | diagnostic/result records across adapters/scripts | phase transitions and failures | structured status, severity, duration, fingerprints | secrets and raw provider bodies never logged | all Rust crates | happy path plus one diagnostic signal for each subsystem |

## Domain model parity

Rust must cover at least these current domain forms before cutover:

- `SourceDocument`, `SourceBlock`, `ActEdition`;
- `SourceHierarchy` / hierarchy record types and levels;
- `LegalUnit`, `EvidenceSpan`, `Citation`, `NormStatement`;
- retrieval validation/result forms;
- source profile and parser record contracts.

Rust serialization is not required to mimic Pydantic internals. It must preserve
public schemas, required invariants, normalized JSON representations, stable IDs,
and rejection behavior.

## Parity classes

1. **Schema parity** — required/optional fields, enums, normalized JSON and JSON Schema.
2. **Deterministic parity** — same input bytes produce the same canonical artifacts.
3. **Failure parity** — every existing negative fixture still fails closed with a stable reason.
4. **Integration parity** — FalkorDB, source files and local embedding runtime are exercised.
5. **Safety parity** — citation, evidence and generated-Cypher policies are equal or stricter.
6. **Operational parity** — CLI exit codes, bounded diagnostics, timeouts and cleanup.
7. **Scale parity** — Rust meets accepted time, peak RSS and concurrency budgets.
8. **UAT parity** — complete import-to-evidence scenarios pass without Python product execution.

## Cutover gate

Python product code may move to `python_archive/` only when:

- every required capability row has a Rust owner and passing evidence;
- canonical corpus artifacts and hashes are frozen and reproduced by Rust;
- all required Rust unit, property, integration and UAT tests pass;
- performance, peak memory and multi-core scaling budgets pass;
- Rust CLIs cover every product entrypoint;
- Python harness contains no product/domain imports or rules;
- rollback is repository-history-only; there is no runtime bridge.
