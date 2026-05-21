# M039 S02 Verifier Migration Assessment

**Date:** 2026-05-21

## Verdict

No verifier or extractor code migration is required in S02.

The M039 S01 canonical schema patch is additive. Current verifier and extractor behavior remains compatible because:

- existing canonical registry records still validate;
- new ACP-aware item/edge vocabulary is accepted by `architecture.schema.json`;
- verifier decision-fitness rules still target accepted `decision` records, not `decision_candidate` records;
- ACP-aware records are not yet generated into canonical registry JSONL;
- current architecture verifier remains the guardrail for tracked canonical outputs.

## Evidence reviewed

| Surface | Assessment |
| --- | --- |
| `prd/architecture/architecture.schema.json` | Additive enum and optional-field changes only. |
| `tests/test_architecture_registry_schema.py` | Now tests ACP-aware canonical-shaped item and edge records. |
| `scripts/verify-architecture-graph.py` | Uses current canonical registry outputs and decision-fitness rules; no ACP-generated canonical records exist yet. |
| `scripts/extract-prd-architecture-items.py` | Continues generating existing project architecture records; no ACP source extraction added in M039. |
| `scripts/build-architecture-graph.py` | Reads canonical JSONL/schema outputs; no ACP-specific graph transformation required yet. |
| `scripts/verify-acp-schema-extension-fixtures.py` | Continues validating custom-path candidate fixtures separately. |

## Why no code migration is needed now

M039 S01 changed the schema contract, not the canonical registry generation flow.

The new schema vocabulary allows future ACP-aware records, but no source extractor currently emits those records. Therefore verifier/extractor code should not be changed until a later milestone decides whether ACP projection remains preview-only or gains a checked canonical-output mode.

This avoids two risks:

1. treating ACP fixture records as canonical architecture truth;
2. changing verifier semantics before canonical ACP generation rules exist.

## Current regression coverage

Current coverage is sufficient for S02 because it tests both sides of the boundary:

- canonical registry remains valid and current;
- ACP custom fixtures remain valid and scoped;
- canonical schema accepts ACP-aware canonical-shaped records;
- decision candidates remain distinct from accepted decisions;
- prompt provenance remains non-authoritative.

## Checks that must remain green

```bash
uv run python scripts/extract-prd-architecture-items.py --check
uv run python scripts/build-architecture-graph.py --check
uv run python scripts/verify-architecture-graph.py
uv run pytest tests/test_architecture_registry_schema.py
uv run python scripts/verify-acp-schema-extension-fixtures.py
uv run pytest tests/test_acp_schema_extension_fixtures.py
```

## Deferred migration work

A future ACP projection integration milestone may need to update:

- `scripts/export-acp-architecture-projection.py` if it gains a checked canonical-output mode;
- `scripts/extract-prd-architecture-items.py` if ACP records become source inputs for canonical registry generation;
- `scripts/verify-architecture-graph.py` if ACP-specific health findings or blocked actions need architecture-health diagnostics;
- graph/report builders if dashboards need ACP-specific views.

Those changes are intentionally out of scope for M039 S02.

## Boundary preservation

This assessment does not validate:

- R035;
- R037;
- R038;
- parser completeness;
- legal correctness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- production readiness;
- independent external review.

## S02 conclusion

M039 S02 should close as verification-only:

```text
No verifier/extractor code migration required until ACP canonical-output generation is explicitly designed and proof-gated.
```
