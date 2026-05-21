# M037 ACP to Architecture Registry Mapping Specification

**Date:** 2026-05-21

## Status

Source-backed mapping specification for `M037-pwepgo / S01`.

This document defines a preview-only mapping from ACP records to architecture-registry-like item and edge projections. It does not mutate `prd/architecture/architecture_items.jsonl` or `prd/architecture/architecture_edges.jsonl` and does not promote ACP records into canonical registry truth.

## Verdict

ACP records can be mapped into a **preview architecture projection**, but should not feed the canonical architecture registry until the preview exporter and a later integration decision prove the mapping is safe.

The safe next step is:

```text
ACP source records -> preview item/edge projection under prd/architecture/acp/derived/
```

not:

```text
ACP source records -> prd/architecture/architecture_items.jsonl
ACP source records -> prd/architecture/architecture_edges.jsonl
```

## Source inputs

| Source | Role |
| --- | --- |
| `prd/architecture/acp/schema.json` | ACP minimal record contract. |
| `prd/architecture/acp/derived/recovery-view.json` | Current derived ACP recovery graph. |
| `prd/architecture/acp/M036-S03-INTEGRATION-ASSESSMENT.md` | Prior recommendation to keep ACP separate until mapping proof. |
| `prd/architecture/README.md` | Canonical architecture registry source-of-truth and verifier contract. |
| `prd/architecture/architecture.schema.json` | Current canonical item/edge schema to compare against. |

## Mapping boundary

The M037 preview projection is derived and non-authoritative.

It may show how ACP records could become architecture-registry items and edges. It must not:

- edit canonical architecture JSONL files;
- bypass `scripts/extract-prd-architecture-items.py`;
- hand-write canonical registry truth;
- change proof levels;
- validate R035, R037, or R038;
- claim parser completeness, legal correctness, FalkorDB ingestion/runtime loading, retrieval quality, production readiness, or independent external review.

## Preview output target

S02 should generate:

```text
prd/architecture/acp/derived/architecture-projection.preview.json
```

Suggested shape:

```json
{
  "kind": "acp_architecture_projection_preview",
  "version": "0.1.0",
  "boundary": "Preview only; canonical architecture registry files are unchanged.",
  "source": "prd/architecture/acp/derived/recovery-view.json",
  "items": [],
  "edges": [],
  "non_mappable": [],
  "blocked_canonical_mutations": []
}
```

## Preview item shape

Preview items should be architecture-registry-like, but not canonical registry records.

Required preview fields:

| Field | Meaning |
| --- | --- |
| `preview_id` | Stable preview ID, derived from ACP record ID. |
| `source_record_id` | Original ACP record ID. |
| `source_record_kind` | Original ACP record kind. |
| `suggested_type` | Candidate architecture registry `type`. |
| `suggested_layer` | Candidate architecture registry `layer`. |
| `suggested_status` | Candidate architecture registry status. |
| `suggested_proof_level` | Candidate proof level, usually `source-anchor` or `static-check`. |
| `title` | ACP record title. |
| `summary` | Short bounded summary. |
| `source_anchors` | Converted source refs. |
| `non_claims` | Explicit non-claims preserving law-nexus boundaries. |
| `mapping_notes` | Explanation of mapping limitations. |

Preview IDs should not collide with canonical registry IDs. Recommended prefix:

```text
ACP-PREVIEW-<ACP-ID>
```

## ACP record kind mapping

| ACP record kind | Preview item type | Preview layer | Preview status | Preview proof level | Notes |
| --- | --- | --- | --- | --- | --- |
| `architecture_prompt_record` | `evidence` | `architecture-governance` | `bounded-evidence` | `source-anchor` | Provenance only; not proof of decisions or implementation. |
| `architecture_proposal` | `viewpoint` | `architecture-governance` | `proposed` or `bounded-evidence` | `source-anchor` | Proposal quality artifact, not accepted decision. |
| `decision_candidate` | `decision` | `architecture-governance` | `hypothesis` or `blocked` | `source-anchor` | Candidate only; not accepted doctrine. |
| `proof_gate` | `proof_gate` | `architecture-governance` | `blocked` | `static-check` if validator evidence exists; otherwise `source-anchor` | Defines evidence requirement; not evidence itself. |
| `architecture_health_finding` | `risk` | `architecture-governance` | `blocked` | `source-anchor` | Drift/blocker signal; not architecture proof. |

## Status mapping rules

| ACP status | Preview suggested status | Notes |
| --- | --- | --- |
| `policy_checked` | `bounded-evidence` | For prompt provenance only. |
| `complete` | `bounded-evidence` | Proposal complete means structurally complete, not accepted. |
| `candidate` | `hypothesis` | Candidate-only decision. |
| `blocking` | `blocked` | Proof gate blocks promotion/action. |
| `open` | `blocked` | Health finding remains unresolved. |

Unsupported ACP statuses should be emitted to `non_mappable` rather than guessed.

## Proof-level mapping rules

| ACP evidence condition | Preview proof level |
| --- | --- |
| Source record exists and validates | `source-anchor` |
| Validator command passes for fixture chain | `static-check` only for validator/proof-gate mechanics |
| Unit tests pass for exporter/validator | `unit-test` only for tooling mechanics, not product claims |

Do not project ACP records as validated product architecture. `validated` is not a default output for M037 preview.

## Source ref to source anchor mapping

ACP `source_refs` map to preview `source_anchors`:

| ACP field | Preview source anchor field |
| --- | --- |
| `path` | `path` |
| `role` | `kind` or `selector` note |
| `note` | `selector` or `mapping_notes` |

Mapping for `kind` should be conservative:

| ACP source role pattern | Preview source anchor kind |
| --- | --- |
| contains `contract`, `profile`, `plan`, `assessment` | `prd` |
| contains `fixture`, `schema`, `validator`, `exporter` | `manual-note` unless source code/test specific |
| path under `scripts/` | `source-code` |
| path under `tests/` | `test-artifact` |
| path under `prd/` | `prd` |

If kind cannot be determined safely, use `manual-note` and add a mapping note.

## Relationship mapping

Current ACP recovery relationships:

| ACP relationship | Preview edge type | Preview status | Notes |
| --- | --- | --- | --- |
| `producedProposal` | `informs` | `bounded-evidence` | Prompt provenance informs proposal. |
| `originPromptRecord` | `informs` | `bounded-evidence` | Reverse provenance relation; exporter may deduplicate with `producedProposal`. |
| `suggestedDecision` | `informs` | `hypothesis` | Proposal suggests candidate. |
| `originProposal` | `informs` | `hypothesis` | Reverse origin relation; exporter may deduplicate with `suggestedDecision`. |
| `requiresProof` | `checked_by` | `active` | Candidate requires proof gate. |
| `affects` | `blocks` | `active` | Health finding affects/blocks candidate or gate. |

Canonical architecture edge schema may not include every desired semantic edge directly. Therefore S02 preview edges should use preview-only edge objects, not canonical JSONL rows.

## Preview edge shape

Required preview edge fields:

| Field | Meaning |
| --- | --- |
| `preview_id` | Stable edge preview ID. |
| `source_preview_id` | Preview item ID for source record. |
| `target_preview_id` | Preview item ID for target record. |
| `relationship` | ACP relationship name. |
| `suggested_edge_type` | Candidate architecture edge relation such as `informs`, `checked_by`, or `blocks`. |
| `suggested_status` | Candidate edge status. |
| `mapping_notes` | Boundary/semantic notes. |

## Non-mappable fields and gaps

These ACP details should remain ACP-only in M037 preview:

| ACP detail | Reason |
| --- | --- |
| Full `safety` object | Too ACP-specific for canonical registry item schema. Keep summarized as non-claims. |
| `capture_mode` / `redaction_status` | Provenance policy detail; map only to notes unless schema is extended. |
| Full blocked action text | Useful for recovery view; registry may need separate health/drift schema. |
| Allowed next actions | Workflow guidance, not architecture claim. |
| Raw recovery view ordering | Visualization concern, not registry truth. |

Schema gaps to assess later:

- no first-class `architecture_prompt_record` item type;
- no explicit `health_finding` item type;
- limited edge vocabulary for `blockedBy`, `requiresProof`, and `producedProposal` semantics;
- no canonical place for capture/redaction policy;
- unclear whether ACP proof gates should be registry proof gates or separate governance proof gates.

## Blocked canonical mutations

M037 preview exporter must report these as blocked actions:

- writing `prd/architecture/architecture_items.jsonl`;
- writing `prd/architecture/architecture_edges.jsonl`;
- changing `prd/architecture/architecture.schema.json`;
- changing `scripts/extract-prd-architecture-items.py`;
- changing `scripts/build-architecture-graph.py`;
- promoting `DC-0001` to accepted decision;
- projecting ACP preview items as `validated` product architecture.

## S02 exporter acceptance criteria

The S02 exporter should:

1. read `prd/architecture/acp/derived/recovery-view.json`;
2. emit `prd/architecture/acp/derived/architecture-projection.preview.json`;
3. support `--check` freshness mode;
4. include `items`, `edges`, `non_mappable`, and `blocked_canonical_mutations`;
5. include non-claims for R035, R037, R038, parser completeness, legal correctness, FalkorDB ingestion/runtime loading, retrieval quality, production readiness, and independent external review;
6. not touch canonical registry JSONL files;
7. have focused tests for shape, freshness, and boundary constraints;
8. keep `uv run python scripts/verify-architecture-graph.py` green.

## Verification commands for M037 S01

```bash
uv run python scripts/verify-acp-records.py
uv run python scripts/export-acp-recovery-view.py --check
uv run python scripts/verify-architecture-graph.py
```

S02 will add:

```bash
uv run python scripts/export-acp-architecture-projection.py --check
uv run pytest tests/test_acp_architecture_projection.py
```

## Boundary preservation

This mapping spec does not validate:

- R035;
- R037;
- R038;
- parser completeness;
- legal correctness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- production readiness;
- independent external review.

ACP preview projection is an integration design artifact. It is not canonical registry truth.
