# M040 ACP Canonical Projection Contract

**Date:** 2026-05-21

## Status

Contract artifact for `M040-1x3noo / S01`.

This document defines how ACP records may be exported as canonical-shaped architecture registry JSONL records to a custom proof path. It does not authorize writing ACP records into `prd/architecture/architecture_items.jsonl` or `prd/architecture/architecture_edges.jsonl`.

## Verdict

Implement a checked custom-path canonical-shaped export mode, not canonical registry integration.

Safe target for S02:

```text
prd/architecture/acp/derived/canonical-projection.items.jsonl
prd/architecture/acp/derived/canonical-projection.edges.jsonl
```

Blocked targets:

```text
prd/architecture/architecture_items.jsonl
prd/architecture/architecture_edges.jsonl
```

## Inputs

| Input | Role |
| --- | --- |
| `prd/architecture/acp/derived/recovery-view.json` | ACP source recovery view. |
| `prd/architecture/acp/derived/architecture-projection.preview.json` | Existing preview mapping evidence. |
| `prd/architecture/architecture.schema.json` | Canonical schema that now accepts ACP-aware shapes. |
| `prd/architecture/acp/M039-PROJECTION-INTEGRATION-DECISION.md` | Decision to keep preview-only until this proof. |

## Output mode

S02 should add an explicit output mode, for example:

```bash
uv run python scripts/export-acp-architecture-projection.py \
  --canonical-jsonl \
  --items-output prd/architecture/acp/derived/canonical-projection.items.jsonl \
  --edges-output prd/architecture/acp/derived/canonical-projection.edges.jsonl
```

This mode must:

- write custom-path canonical-shaped item and edge JSONL records;
- support `--check` for both files;
- refuse canonical registry paths;
- leave existing preview JSON mode unchanged;
- emit structured JSON status including item and edge counts;
- keep all generated records non-authoritative and bounded.

## Canonical-shaped item mapping

Use canonical schema records with:

```json
{
  "schema_version": "legalgraph-architecture-registry/v1",
  "record_kind": "item",
  "id": "ACP-<source_record_id>",
  "type": "...",
  "layer": "architecture-governance",
  "status": "...",
  "proof_level": "...",
  "risk_level": "...",
  "source_anchors": [],
  "owner": "architecture-control-plane",
  "verification": "uv run python scripts/export-acp-architecture-projection.py --canonical-jsonl --check",
  "generated_draft": true,
  "non_claims": []
}
```

### Item ID policy

Canonical-shaped proof IDs should be stable and clearly ACP-scoped:

```text
ACP-APR-0001
ACP-AP-0001
ACP-DC-0001
ACP-PG-0001
ACP-AHF-0001
```

Do not reuse `ACP-PREVIEW-*` IDs for canonical-shaped JSONL records.

### Item type mapping

| ACP record kind | Canonical-shaped type | Status | Proof level | Notes |
| --- | --- | --- | --- | --- |
| `architecture_prompt_record` | `prompt_record` | `bounded-evidence` | `source-anchor` | Provenance only. |
| `architecture_proposal` | `proposal` | `proposed` | `source-anchor` | Planning artifact only. |
| `decision_candidate` | `decision_candidate` | `proposed` | `source-anchor` | Requires authority before acceptance. |
| `proof_gate` | `proof_gate` | `active` | `static-check` | Tooling/proof mechanics only. |
| `architecture_health_finding` | `health_finding` | `blocked` | `static-check` | Governance blocker, not product evidence. |

### Item metadata

Populate when available or applicable:

- `acp_record_kind`;
- `acp_source_record_id`;
- `capture_mode`;
- `redaction_status`;
- `authority_required` for decision candidates;
- `blocked_actions` for proof gates and health findings;
- `allowed_next_actions` for health findings;
- `acp_non_mappable` for source fields intentionally omitted from canonical semantics.

## Source-anchor rules

Source anchors must be repository-relative and tracked.

Allowed anchor kinds:

- `prd` for ACP docs and source records under `prd/`;
- `source-code` for scripts;
- `test-artifact` for tests;
- `manual-note` only for fixture notes or conservative fallback.

Do not use:

- absolute paths;
- ignored transient execution-log paths;
- raw provider payload paths;
- external URLs as proof anchors;
- raw legal-text payloads.

## Non-claims

Every canonical-shaped ACP item must include non-claims stating that it does not validate:

- R035;
- R037;
- R038;
- parser completeness;
- legal correctness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- production readiness;
- independent external review.

Prompt records must additionally state that prompt provenance is not implementation proof.

Decision candidates must additionally state that they are not accepted architecture doctrine.

## Canonical-shaped edge mapping

Use canonical schema records with:

```json
{
  "schema_version": "legalgraph-architecture-registry/v1",
  "record_kind": "edge",
  "id": "ACP-EDGE-<source>-<relation>-<target>",
  "from": "ACP-<source_record_id>",
  "to": "ACP-<target_record_id>",
  "type": "...",
  "status": "...",
  "rationale": "...",
  "source_anchors": [],
  "generated_draft": true,
  "owner": "architecture-control-plane",
  "verification": "uv run python scripts/export-acp-architecture-projection.py --canonical-jsonl --check",
  "acp_relationship": "..."
}
```

### Edge relation mapping

Do not reuse old preview `informs` suggestions. Use the M039 canonical relation vocabulary:

| ACP relationship | Canonical-shaped edge type | Status |
| --- | --- | --- |
| `producedProposal` | `produced_proposal` | `bounded-evidence` |
| `originPromptRecord` | `origin_prompt_record` | `bounded-evidence` |
| `suggestedDecision` | `suggested_decision` | `hypothesis` |
| `originProposal` | `origin_proposal` | `hypothesis` |
| `requiresProof` | `requires_proof` | `active` |
| `affects` when source is health finding and target is decision candidate | `blocks` | `active` |
| `affects` when source is health finding and target is proof gate | `affects` | `active` |

Unsupported relationships should be omitted with diagnostics rather than guessed.

## Omission and diagnostics rules

The exporter should emit diagnostics or `non_mappable` entries when:

- source record kind is unsupported;
- relationship is unsupported;
- source anchor cannot be made safe and repository-relative;
- status or proof-level mapping would imply validation;
- an output path targets canonical registry files.

Diagnostics must not include secrets, raw provider payloads, raw legal text, local absolute paths, or transient execution-log anchors.

## S02 verification requirements

S02 must prove:

1. Custom item and edge JSONL files are generated.
2. Generated records validate against `prd/architecture/architecture.schema.json`.
3. Generated item and edge counts match the current minimal ACP chain.
4. `--check` detects stale custom outputs.
5. Canonical registry output paths are refused.
6. Existing preview output remains current.
7. `uv run python scripts/verify-architecture-graph.py` remains green on tracked canonical outputs.

## Boundary preservation

This contract does not validate:

- R035;
- R037;
- R038;
- parser completeness;
- legal correctness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- production readiness;
- independent external review.

## S03 decision input

S03 should decide among:

1. keep canonical-shaped output custom-only;
2. plan a later integration into canonical extraction/build flow;
3. revise mapping if S02 exposes schema or verifier mismatch.

Default bias: keep custom-only until canonical generation ownership is explicitly designed.
