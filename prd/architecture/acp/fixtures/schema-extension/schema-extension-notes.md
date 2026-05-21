# M038 Schema Extension Fixture Notes

These custom-path fixtures exercise the candidate ACP registry schema extension from `prd/architecture/acp/M038-SCHEMA-EXTENSION-DESIGN.md`.

## Files

- `custom-items.jsonl`
- `custom-edges.jsonl`

## Boundary

The fixtures are not canonical architecture registry outputs. They do not replace or mutate:

- `prd/architecture/architecture.schema.json`
- `prd/architecture/architecture_items.jsonl`
- `prd/architecture/architecture_edges.jsonl`

## Purpose

The fixtures test whether ACP governance concepts can be represented with explicit candidate schema fields before any canonical schema change.

They cover:

- `prompt_record`
- `proposal`
- `decision_candidate`
- `proof_gate`
- `health_finding`
- `capture_mode`
- `redaction_status`
- `authority_required`
- `blocked_actions`
- `allowed_next_actions`
- ACP relationship names and candidate canonical relations

## Non-claims

These fixtures do not validate:

- R035;
- R037;
- R038;
- parser completeness;
- legal correctness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- production readiness;
- independent external review.

Custom-path fixture success only proves candidate schema shape for ACP governance records.
