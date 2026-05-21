# M038 ACP Registry Schema Extension Design

**Date:** 2026-05-21

## Status

Design artifact for `M038-oo34le / S01`.

This document proposes a candidate architecture-registry schema extension for ACP governance semantics. It does not change `prd/architecture/architecture.schema.json`, `prd/architecture/architecture_items.jsonl`, or `prd/architecture/architecture_edges.jsonl`.

## Verdict

Use a custom-path fixture proof before any canonical schema change.

The current architecture registry schema can approximate some ACP concepts, but canonical integration should wait until the schema can represent ACP governance semantics without overloading existing product-architecture concepts.

## Current schema constraints

Current canonical item records require fields such as:

```text
schema_version
record_kind
id
type
title
summary
layer
status
proof_level
risk_level
source_anchors
owner
verification
generated_draft
non_claims
```

Current `item_type` enum includes:

```text
requirement, decision, assumption, risk, proof_gate, component, interface, data_entity, quality_scenario, viewpoint, evidence, workflow_check
```

Current `layer` enum already includes:

```text
architecture-governance
```

Current `status` and `proof_level` enums are usable for ACP preview:

```text
status: proposed, active, hypothesis, bounded-evidence, validated, deferred, blocked, rejected, superseded, out-of-scope
proof_level: none, source-anchor, static-check, unit-test, integration-test, runtime-smoke, real-document-proof, production-observation
```

The schema gap is not basic status/proof vocabulary. The gap is first-class ACP governance semantics.

## Candidate schema extension goals

A future canonical schema extension should represent:

- prompt provenance as provenance, not proof;
- proposal records as structured architecture planning artifacts;
- decision candidates as not-yet-accepted decisions;
- ACP proof gates as governance proof gates;
- architecture health findings as first-class blockers/drift findings;
- capture/redaction policy for prompt provenance;
- blocked actions and allowed next actions;
- ACP relationship semantics without losing direction or authority boundary.

## Proposed item type extension

Candidate additions to `item_type`:

| Candidate item type | Purpose | Why existing type is insufficient |
| --- | --- | --- |
| `prompt_record` | Prompt provenance / `ArchitecturePromptRecord`. | `evidence` is too broad and may imply support for a claim. |
| `proposal` | Structured architecture proposal / `ArchitectureProposal`. | `viewpoint` is close but does not express proposal completeness/rubric fields. |
| `decision_candidate` | Candidate decision requiring authority. | `decision` risks implying accepted doctrine. |
| `health_finding` | ACP drift/blocker/overclaim finding. | `risk` is close but lacks lifecycle and blocked-action semantics. |

Existing `proof_gate` can remain, but ACP proof gates should receive additional governance metadata.

## Proposed item fields

Candidate optional fields for ACP-aware item records:

| Field | Type | Applies to | Purpose |
| --- | --- | --- | --- |
| `acp_record_kind` | enum/string | all ACP projections | Preserve original ACP kind. |
| `acp_source_record_id` | string | all ACP projections | Trace back to ACP source record. |
| `capture_mode` | enum | prompt records | Capture fidelity policy. |
| `redaction_status` | enum | prompt records | Safety/redaction state. |
| `authority_required` | boolean | decision candidates | Prevent candidate/accepted confusion. |
| `blocked_actions` | array of strings | proof gates and health findings | Explicit workflow blocks. |
| `allowed_next_actions` | array of strings | health/recovery records | Agent-facing recovery guidance. |
| `acp_non_mappable` | array of strings | all ACP projections | Preserve fields intentionally left out of canonical semantics. |

These fields should not be added canonically until S02 custom-path fixtures prove their shape and verifier behavior.

## Proposed edge relation extension

Candidate edge relations or edge metadata:

| ACP relationship | Candidate canonical relation | Notes |
| --- | --- | --- |
| `producedProposal` | `produced_proposal` | Prompt record produced proposal. |
| `originPromptRecord` | `origin_prompt_record` | Reverse provenance relation; may be redundant if `produced_proposal` exists. |
| `suggestedDecision` | `suggested_decision` | Proposal suggests decision candidate. |
| `originProposal` | `origin_proposal` | Reverse proposal origin relation; may be redundant if `suggested_decision` exists. |
| `requiresProof` | `requires_proof` or existing `checked_by` | Candidate or decision requires proof gate. |
| `affects` | `blocks` or `affects` | Health finding affects candidate/gate/action. |

Preferred S02 fixture strategy: include both ACP-native relationship and candidate canonical relation fields so a future decision can choose between schema extension and mapping-to-existing relation vocabulary.

## Rejected alternatives

### Reuse `evidence` for prompt records

Rejected for canonical integration. Prompt records explain origin and intent; they do not support product or implementation claims.

### Reuse `decision` for decision candidates

Rejected for canonical integration unless a clear `candidate` status and `authority_required` field exist. Otherwise future agents may treat candidates as accepted doctrine.

### Reuse `risk` for health findings without added fields

Rejected for canonical integration. ACP health findings include blocked actions, affected records, remediation, and recovery guidance.

### Store capture/redaction policy only in prose

Rejected. Capture policy is safety-critical and should be machine-checkable before ACP prompt records are canonicalized.

### Integrate preview projection as-is

Rejected. M037 preview output is useful evidence but intentionally not canonical JSONL.

## S02 custom-path fixture requirements

S02 should create candidate custom fixtures outside canonical registry outputs, for example:

```text
prd/architecture/acp/fixtures/schema-extension/custom-items.jsonl
prd/architecture/acp/fixtures/schema-extension/custom-edges.jsonl
prd/architecture/acp/fixtures/schema-extension/schema-extension-notes.md
```

The fixtures should include at least:

- one prompt record item with `prompt_record` and capture/redaction fields;
- one proposal item;
- one decision candidate item with `authority_required: true`;
- one proof gate item with `blocked_actions`;
- one health finding item with affected records and remediation;
- edges for produced proposal, suggested decision, required proof, and blocked/affected relationships.

S02 should not edit:

```text
prd/architecture/architecture.schema.json
prd/architecture/architecture_items.jsonl
prd/architecture/architecture_edges.jsonl
scripts/extract-prd-architecture-items.py
scripts/build-architecture-graph.py
```

## S02 validation requirements

S02 should add a custom fixture check that proves candidate shape without canonical mutation.

The check should verify:

- custom fixture files parse as JSONL;
- candidate item types and fields appear exactly as designed;
- source anchors are repository-relative;
- no transient execution-log anchors are used;
- no secrets, provider payloads, raw legal text, or local absolute paths are present;
- no item claims validated product/runtime/legal/parser/FalkorDB/retrieval readiness;
- edges reference existing custom fixture item IDs;
- canonical registry files are unchanged.

Custom-path verifier fixture success must remain scoped. It does not mean the tracked project architecture registry is current or integrated.

## Canonical verifier relationship

The canonical verifier remains:

```bash
uv run python scripts/verify-architecture-graph.py
```

M038 S01/S02 should keep this verifier green on tracked canonical outputs. If S02 uses custom fixture checks, their success is evidence for the proposed schema extension only, not evidence that canonical registry files changed or should be considered current.

## Boundary preservation

This design does not validate:

- R035;
- R037;
- R038;
- parser completeness;
- legal correctness;
- FalkorDB ingestion or runtime loading;
- graph-vector retrieval quality;
- production readiness;
- independent external review.

## S03 decision inputs

S03 should decide among:

1. Apply canonical schema changes now.
2. Defer canonical schema changes and keep ACP projection separate.
3. Revise mapping because custom fixtures revealed schema mismatch.

Default bias: do not apply canonical changes unless S02 custom fixtures and checks demonstrate a small, stable extension with no verifier drift.
