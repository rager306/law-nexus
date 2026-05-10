---
name: legalgraph-architecture-verification
description: Routes LegalGraph Nexus architecture registry, architecture verifier, proof-level, decision-fitness, and architecture-claim review work through the verified registry contract. Use for architecture planning, registry updates, architecture drift, verifier failures, source-of-truth questions, R017/M003 proof-boundary review, or claims touching FalkorDB and Russian legal evidence.
---

<objective>
Use this project-local router when work touches LegalGraph Nexus architecture planning, `prd/architecture/` registry artifacts, architecture claim review, proof-level classification, decision fitness functions, or failures from `scripts/verify-architecture-graph.py`. The goal is to keep architecture guidance tied to tracked source evidence while treating JSONL, graph reports, verifier output, and skills as derived, non-authoritative diagnostics.
</objective>

<quick_start>
For architecture-registry or verifier work, start from the tracked contract and run the canonical verifier before claiming current architecture state:

```bash
uv run python scripts/verify-architecture-graph.py
```

If diagnosing a freshness layer only, use the narrower read-only gates:

```bash
uv run python scripts/extract-prd-architecture-items.py --check
uv run python scripts/build-architecture-graph.py --check
```

Read `prd/architecture/README.md` and `prd/architecture/architecture.schema.json` before changing registry mappings, proof levels, verifier policy, or architecture-router prose.
</quick_start>

<source_of_truth_hierarchy>
- Source of truth: PRD/GSD/ADR/source-code/test/runtime/real-document evidence, especially `prd/09_architecture_planning_verification_research.md` and anchored GSD artifacts.
- Schema contract: `prd/architecture/architecture.schema.json` defines valid item and edge record shape, status, proof levels, source anchors, and decision metadata.
- Derived projections: `prd/architecture/architecture_items.jsonl` and `prd/architecture/architecture_edges.jsonl` are generated registry views; regenerate them, do not hand-edit to create authority.
- Derived reports: `prd/architecture/architecture_graph_report.json` and `prd/architecture/architecture_report.md` diagnose graph health but do not prove product readiness or legal correctness.
- Derived guidance: this skill and other router prose explain how to route work; they never override anchored PRD/GSD/ADR/source/runtime evidence.
</source_of_truth_hierarchy>

<canonical_workflow>
1. Update authoritative source evidence first when the claim itself changed.
2. Regenerate the conservative registry projection:

```bash
uv run python scripts/extract-prd-architecture-items.py
```

3. Rebuild graph/report views:

```bash
uv run python scripts/build-architecture-graph.py
```

4. Run the canonical architecture verifier:

```bash
uv run python scripts/verify-architecture-graph.py
```

A passing verifier means the current derived artifacts satisfy static registry, graph, source-anchor, decision-fitness, and claim-safety rules. It does not validate runtime behavior, parser completeness, retrieval quality, generated-Cypher safety, FalkorDB production scale, legal-answer correctness, or LLM authority.
</canonical_workflow>

<failure_classes>
When `verify-architecture-graph.py` fails, classify the failure before editing:
- **Extractor freshness drift**: `extract-prd-architecture-items.py --check` differs from tracked JSONL; fix source mapping or regenerate.
- **Graph/report freshness drift**: `build-architecture-graph.py --check` differs from tracked report output; rebuild from current JSONL.
- **Schema or JSONL shape failure**: malformed JSONL, duplicate IDs, wrong `record_kind`, invalid enum, date, path, or identifier; fix the source mapping, schema-aware fixture, or generated record source.
- **Unsafe source anchor**: absolute paths, ignored local-only paths, missing files, unbounded line ranges, or stale selectors; repair the repository-relative anchor or the authoritative source.
- **Graph integrity failure**: missing endpoints, orphan traceability-critical records, unresolved contradictions, or proof-gate metadata gaps; add anchored relationships or resolve/supersede the conflict.
- **Decision fitness failure**: active decisions without consequences, superseded decisions without successor coverage, or high/critical decisions lacking `checked_by`/`validated_by` proof-gate coverage; fix decision evidence and regenerate.
- **Positive overclaim failure**: prose asserts unproven runtime, parser, retrieval, FalkorDB, generated-Cypher, legal-answer, or LLM-authority claims; downgrade to bounded language or add matching proof before raising status.
</failure_classes>

<routing_rules>
- For broad LegalGraph Nexus architecture questions, load `legalgraph-nexus` first, then use this skill for registry/verifier/proof-level obligations.
- For FalkorDB, GraphBLAS, Cypher, vector/full-text, UDF, FalkorDBLite, driver, production-scale, or runtime-capability claims, route to `falkordb-legalgraph`; keep claims bounded unless tracked source/runtime proof supports them.
- For Russian legal evidence, ODT/Garant source evidence, EvidenceSpan, SourceBlock, citation-safe retrieval, Old_project prior art, legal authority, temporal-first evidence, or parser-sensitive claims, route to `russian-legal-evidence`.
- For R017, M003, or architecture proof-boundary review, inspect the registry source anchors and the verifier output before upgrading proof level or status.
- For architecture registry updates, preserve the source-of-truth hierarchy: source evidence first, derived JSONL/report/verifier/skill guidance second.
</routing_rules>

<proof_level_rules>
Use the lowest accurate `proof_level` from `architecture.schema.json`:
- `source-anchor` for PRD/GSD/ADR/source evidence without runtime proof.
- `static-check` for schema, graph integrity, verifier, or other static fitness evidence.
- `unit-test`, `integration-test`, `runtime-smoke`, `real-document-proof`, or `production-observation` only when the named evidence actually exists and is anchored.
- Keep FalkorDB production-scale, ODT/parser completeness, retrieval quality, generated-Cypher safety, legal-answer correctness, and LLM-authority claims below validated status until matching proof exists.
</proof_level_rules>

<guardrails>
- Negative boundary language such as “derived,” “non-authoritative,” “does not validate,” and “must not be used as legal authority” is required claim-safety language, not an overclaim.
- Do not treat custom-path verifier fixture success as evidence that tracked project architecture is current; default-path verifier runs are the currentness proof.
- Do not cite `.gsd/exec` or ignored local-only files as registry anchors.
- Do not duplicate domain-specific FalkorDB or Russian legal evidence rules here; route to the focused skills and cite tracked artifacts.
- Do not use LLM output as legal authority, architecture validation, source evidence, or proof-level upgrade evidence.
</guardrails>

<success_criteria>
A correct use of this router names the canonical verifier command, preserves the source of truth versus derived-artifact boundary, classifies verifier failures into actionable classes, routes FalkorDB and Russian legal evidence questions to focused skills, and avoids upgrading R017, M003, runtime, parser, retrieval, generated-Cypher, legal-answer, or LLM-authority claims beyond their anchored proof level.
</success_criteria>
