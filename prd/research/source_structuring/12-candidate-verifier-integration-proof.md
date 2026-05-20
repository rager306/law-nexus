# M032 S05 — Discovery Candidate Verifier Integration Proof

## Status

- Milestone: `M032-hy6i8r — MiniMax Assisted Source Discovery CLI`
- Slice: `S05 — Discovery Candidate Verifier Integration`
- Current task: `T01 — Map candidate to verifier contract`
- Proof status: `draft_t01_adapter_contract`
- Requirement advanced: `R039`
- Requirements not validated: `R035`, `R038`

## Purpose

S05 routes S04 proposed graph-context candidates through deterministic verifier decisions. S05 is the first M032 slice allowed to emit an `accepted` candidate status, but only as bounded structural candidate acceptance. It does not create legal authority, parser completeness, product retrieval quality, ontology validation, R035 validation, or R038 validation.

## Existing verifier contract

`scripts/source_hypothesis_verifier.py` accepts `structural_hypothesis_proposal` records with:

- `schema_version: legalgraph-structural-hypothesis-proposal/v1`
- `proposal_id`
- `worker_attempt_id`
- `source_artifact_id`
- `source_revision_id`
- `run_id`
- `output_refs`
- `source_family`
- `document_role`
- `parser_route`
- `hypothesis_kind`
- `hypothesis_payload`
- `verifier_status: pending`
- `non_authoritative: true`
- required non-claims.

It emits verifier decisions with:

- `verifier_status: accepted | rejected | needs_review`
- `checked_refs`
- `acceptance_evidence_refs`
- `rejection_reasons`
- `decision_notes`
- non-claims.

## S04 candidate input contract

S04 provides `candidate_hypotheses.jsonl` rows with:

- `candidate_id`
- `run_id`
- `attempt_id`
- `candidate_kind`
- `lifecycle_status: proposed`
- `source_refs`
- `trajectory_refs`
- `attempt_refs`
- `candidate_summary`
- `supporting_context`
- `confidence_bucket`
- `normalization_warnings`
- `model_claims_ignored`
- `non_authoritative: true`

## Adapter mapping

S05 maps one S04 candidate into one verifier proposal.

| Candidate field | Verifier proposal field | Rule |
| --- | --- | --- |
| `candidate_id` | `proposal_id` | Convert `CAND-...` to `SHP-...` using deterministic local hash. |
| `attempt_id` | `worker_attempt_id` | Convert `ATTEMPT-...` to `WA-...` using deterministic local hash. |
| `run_id` | `run_id` | Preserve if safe `RUN-...`. |
| `source_refs` | `output_refs` and payload `evidence_refs` | Use only refs that are workspace-relative and resolvable or verifier-safe. |
| `candidate_kind` | `hypothesis_kind` | Map to closed verifier kinds. |
| `candidate_summary` | payload `safe_rule_id` seed | Do not let model-provided IDs control verifier identity. |
| `supporting_context` | payload `selector` seed or diagnostic context | Preserve useful open legal/source context only in bounded summaries or refs. |
| `confidence_bucket` | payload `confidence_bucket` | Map unsupported values to `low` or `needs_review` diagnostic. |
| `trajectory_refs` | S05 decision extension refs | Preserve for traceability outside the legacy verifier contract. |

## Candidate-kind mapping

S04 candidate kinds map to existing verifier hypothesis kinds as follows:

- `source_pattern_observation` → `structural_marker_rule`
- `artifact_candidate` → `diagnostic_bucket_hint`
- `structure_candidate` → `safe_section_boundary_hint`
- `relationship_candidate` → `structural_marker_rule`
- `graph_context_signal` → `diagnostic_bucket_hint`

Unknown candidate kinds are rejected before verifier proposal construction.

## Acceptance boundary

S05 may emit `accepted` only when:

1. the candidate row is schema-compatible;
2. candidate lifecycle status is exactly `proposed`;
3. candidate refs are traceable;
4. the adapted verifier proposal passes the deterministic verifier;
5. acceptance evidence refs are present.

S05 must reject or route to `needs_review` when refs are missing, candidate status is not `proposed`, candidate kind is unsupported, deterministic evidence is insufficient, or schema fields are malformed.

MiniMax remains non-authoritative. A model-claimed `accepted` status from S04 is ignored by S04 and must never be used by S05 as acceptance evidence.

## S05 verifier artifact outputs

S05 writes run-scoped verifier artifacts under:

```text
law-source/consultant/runtime/verifier/<run_id>/
  verifier_decisions.jsonl
  review_queue_items.jsonl
  rejection_reasons.jsonl
```

Each verifier decision row should include:

- `decision_id`
- `run_id`
- `candidate_id`
- `candidate_kind`
- `verifier_status`
- `checked_refs`
- `acceptance_evidence_refs`
- `rejection_reasons`
- `decision_notes`
- `trajectory_refs`
- `attempt_refs`
- `source_refs`
- `non_authoritative: true`

## CLI integration boundary

S05 may expose verifier integration as:

- `verify-candidates` command; or
- `discover --verify-candidates` option.

The default `discover` behavior from S03/S04 should remain stable unless verifier integration is explicitly requested.

## Q3 risk handling

S05 handles the flagged provenance/integrity risks by design:

- candidate-to-decision links are explicit and durable;
- candidate IDs, proposal IDs, worker attempt IDs, and decision IDs are generated locally;
- same-run refs are preserved and checked where practical;
- malformed candidates do not get default-filled into accepted proposals;
- MiniMax cannot move a candidate to `accepted`;
- decision artifacts carry non-claims for legal correctness, parser completeness, R035, and R038.

## S05 implementation summary

S05 implemented deterministic verifier integration for proposed discovery candidates.

### Added lifecycle helpers

- `CANDIDATE_VERIFIER_DECISION_SCHEMA_VERSION`
- `CANDIDATE_REVIEW_QUEUE_SCHEMA_VERSION`
- `CANDIDATE_REJECTION_SCHEMA_VERSION`
- `verifier_directory()`
- `candidate_to_verifier_proposal()`
- `verify_discovery_candidates()`

### Runtime outputs

S05 writes verifier artifacts under:

```text
runtime/verifier/<run_id>/verifier_decisions.jsonl
runtime/verifier/<run_id>/review_queue_items.jsonl
runtime/verifier/<run_id>/rejection_reasons.jsonl
```

### CLI integration

The `discover` command now supports:

```bash
--verify-candidates
```

Default discovery behavior is unchanged unless this flag is provided.

With `--verify-candidates`, completed discovery attempts can return:

- `verifier_status_counts`
- `verifier_output_refs`

### Behaviors proven

S05 verification proves:

- candidates with verifier-safe evidence refs can become `accepted` by the deterministic verifier;
- safe candidates without verifier evidence become `needs_review`;
- malformed or non-proposed candidate rows become `rejected`;
- `review_queue_items.jsonl` is written for needs_review decisions;
- `rejection_reasons.jsonl` is written for rejected candidates;
- CLI smoke writes trajectory, attempt, candidate, signal, and verifier decision artifacts;
- MiniMax remains non-authoritative;
- accepted means bounded structural candidate acceptance only.

## Non-claims

This integration does not claim:

- legal correctness;
- parser completeness;
- product retrieval quality;
- ontology validation;
- graph-vector behavior;
- production ETL readiness;
- pilot readiness;
- R035 validation;
- R038 validation.

## T01 verification markers

This draft intentionally names `structural_hypothesis_proposal`, `proposal_id`, `worker_attempt_id`, `source_artifact_id`, `source_revision_id`, `run_id`, `output_refs`, `hypothesis_kind`, `hypothesis_payload`, `verifier_status`, `accepted`, `rejected`, `needs_review`, `candidate_id`, `attempt_id`, `trajectory_refs`, `candidate_hypotheses.jsonl`, `verifier_decisions.jsonl`, `review_queue_items.jsonl`, `rejection_reasons.jsonl`, S05-first acceptance boundary, MiniMax non-authoritative boundary, `R035 validation`, and `R038 validation`.
