# M032 S02 — Detailed Trajectory Log Contract

## Status

- Milestone: `M032-hy6i8r — MiniMax Assisted Source Discovery CLI`
- Slice: `S02 — Detailed Trajectory Log Contract`
- Contract status: `draft_t01_schema_envelope`
- Upstream policy: `prd/research/source_structuring/08-runtime-workspace-policy.md`
- Requirement advanced: `R039`
- Requirements not validated: `R035`, `R038`

## Purpose

The source discovery CLI must leave a detailed trajectory log that is useful for analysis, not just operational debugging. A reviewer should be able to reconstruct how a run moved from source artifacts to observed structures, MiniMax-assisted hypotheses, filtering decisions, verifier decisions, rejected branches, and final conclusions.

The legal source data is open. Trajectory logs may preserve useful source/legal context when it is needed to understand a pattern, artifact, structure, relationship, or graph-context signal. The contract avoids only practical hygiene problems: secrets, API keys, irrelevant local absolute paths, raw provider transport internals, noisy low-value dumps, and ambiguous or tamper-prone references.

## Runtime file set

S02 defines these runtime trajectory files under `law-source/consultant/runtime/trajectory/`:

```text
trajectory.jsonl
  Append-only high-level run events and phase transitions.

discovery_steps.jsonl
  Detailed discovery operations, source observations, MiniMax attempt links, and generated output refs.

filtering_decisions.jsonl
  Candidate filtering, normalization, deduplication, and routing decisions.

rejected_branches.jsonl
  Rejected candidate branches with reasons and source/context references.

conclusion_trace.json
  Final run-level conclusion graph linking steps, candidates, verifier outcomes, rejected branches, open questions, and next actions.
```

Downstream slices may add specialized files, but these five are the minimum trajectory set.

## Event types

The common `event_type` vocabulary is:

- `run_started`
- `source_manifest_loaded`
- `source_artifact_observed`
- `source_structure_observed`
- `minimax_attempt_prepared`
- `minimax_attempt_completed`
- `candidate_extracted`
- `candidate_normalized`
- `candidate_filtered`
- `candidate_routed_to_verifier`
- `verifier_decision_recorded`
- `branch_rejected`
- `needs_review_recorded`
- `external_review_pack_prepared`
- `conclusion_recorded`
- `run_completed`
- `run_failed`

## Stable identifier model

Trajectory records must use stable IDs so a reviewer can connect files without relying on line order alone.

| ID | Meaning | Example shape |
| --- | --- | --- |
| `run_id` | One discovery run. | `RUN-<hash12>` |
| `step_id` | One trajectory or discovery step. | `STEP-<hash12>` |
| `parent_step_id` | Previous or parent step. | `STEP-<hash12>` or `null` |
| `attempt_id` | One MiniMax discovery attempt. | `ATTEMPT-<hash12>` |
| `candidate_id` | One normalized discovery candidate. | `CAND-<hash12>` |
| `decision_id` | One deterministic verifier decision. | `DECISION-<hash12>` |
| `review_id` | One external review pack or review result. | `REVIEW-<hash12>` |
| `source_ref` | Workspace-relative source or artifact reference. | `registry:<id>`, `processed:<id>`, `source:<id>` |

IDs should be deterministic when derived from stable content and run-scoped when tied to one execution. Local absolute paths are not stable IDs.

## Concrete record shapes

The common envelope is shared, but each trajectory file has additional required fields.

### `trajectory.jsonl` record

Purpose: high-level run events and phase transitions.

Required fields in addition to the common envelope:

- `run_status`: `started | running | completed | failed`
- `phase_status`: `entered | completed | failed | skipped`
- `artifact_counts`: object with counts for sources, attempts, candidates, decisions, and reviews when known
- `checkpoint_refs`: refs to durable run files or summaries

Example:

```json
{
  "schema_version": "m032.s02.trajectory.v1",
  "run_id": "RUN-abc123def456",
  "record_id": "REC-run-start",
  "event_type": "run_started",
  "phase": "run",
  "step_id": "STEP-run-start",
  "parent_step_id": null,
  "timestamp_utc": "2026-05-20T00:00:00Z",
  "source_refs": ["registry:corpus-a"],
  "input_refs": ["manifest:batch-a"],
  "output_refs": ["runs:run-json"],
  "summary": "Started bounded ConsultantPlus XML discovery run.",
  "observed_context": "Run will inspect open legal source structure for graph-context signals.",
  "decision": "started",
  "decision_reason": "Manifest loaded and runtime workspace prepared.",
  "next_action": "source_observation",
  "non_authoritative": true,
  "run_status": "started",
  "phase_status": "entered",
  "artifact_counts": {"sources": 2, "attempts": 0, "candidates": 0, "decisions": 0, "reviews": 0},
  "checkpoint_refs": ["runs:run-json"]
}
```

### `discovery_steps.jsonl` record

Purpose: detailed source observations, MiniMax preparation/completion links, and candidate-producing operations.

Required fields in addition to the common envelope:

- `operation`: operation name such as `observe_source_structure`, `prepare_minimax_prompt`, or `extract_candidates`
- `observed_structure`: structural observation name or summary
- `supporting_context`: useful open legal/source context needed for analysis
- `attempt_refs`: MiniMax attempt refs, if any
- `candidate_refs`: candidate refs produced by this step
- `confidence_bucket`: `low | medium | high | unknown`

Example:

```json
{
  "schema_version": "m032.s02.trajectory.v1",
  "run_id": "RUN-abc123def456",
  "record_id": "REC-discovery-step",
  "event_type": "source_structure_observed",
  "phase": "source_observation",
  "step_id": "STEP-source-structure",
  "parent_step_id": "STEP-run-start",
  "timestamp_utc": "2026-05-20T00:01:00Z",
  "source_refs": ["processed:artifact-a"],
  "input_refs": ["processed:inventory-a"],
  "output_refs": ["discovery:candidate-a"],
  "summary": "Observed repeated amendment-reference structure.",
  "observed_context": "Open source context shows repeated amendment references across structurally similar sections.",
  "decision": "candidate_extraction_needed",
  "decision_reason": "The repetition appears graph-relevant and has stable source refs.",
  "next_action": "candidate_normalization",
  "non_authoritative": true,
  "operation": "observe_source_structure",
  "observed_structure": "repeated_amendment_reference",
  "supporting_context": "Bounded source context sufficient to inspect the repeated structure.",
  "attempt_refs": [],
  "candidate_refs": ["CAND-abc123def456"],
  "confidence_bucket": "medium"
}
```

### `filtering_decisions.jsonl` record

Purpose: explain normalization, deduplication, routing, and candidate lifecycle decisions.

Required fields in addition to the common envelope:

- `candidate_id`
- `candidate_kind`
- `filter_name`
- `filter_result`: `kept | merged | rejected | routed_to_verifier | needs_review`
- `filter_reason`
- `merged_into_candidate_id`
- `verifier_decision_ref`

Example:

```json
{
  "schema_version": "m032.s02.trajectory.v1",
  "run_id": "RUN-abc123def456",
  "record_id": "REC-filtering",
  "event_type": "candidate_filtered",
  "phase": "candidate_normalization",
  "step_id": "STEP-filter-candidate",
  "parent_step_id": "STEP-source-structure",
  "timestamp_utc": "2026-05-20T00:02:00Z",
  "source_refs": ["processed:artifact-a"],
  "input_refs": ["discovery:candidate-a"],
  "output_refs": ["verifier:queue-a"],
  "summary": "Candidate routed to verifier after deduplication.",
  "observed_context": "Candidate remains useful because source structure is repeated and refs are stable.",
  "decision": "routed_to_verifier",
  "decision_reason": "Candidate is structurally plausible and not a duplicate.",
  "next_action": "verifier_gate",
  "non_authoritative": true,
  "candidate_id": "CAND-abc123def456",
  "candidate_kind": "relationship_candidate",
  "filter_name": "dedupe_and_route",
  "filter_result": "routed_to_verifier",
  "filter_reason": "No equivalent candidate with the same source refs exists.",
  "merged_into_candidate_id": null,
  "verifier_decision_ref": null
}
```

### `rejected_branches.jsonl` record

Purpose: preserve rejected paths so later analysis can learn from false starts and avoid repeating them.

Required fields in addition to the common envelope:

- `branch_id`
- `candidate_id`
- `rejection_stage`: `normalization | filtering | verifier | external_review`
- `rejection_reasons`
- `salvageable_observations`
- `retry_recommendation`: `do_not_retry | retry_with_more_context | retry_after_schema_change | needs_human_review`

Example:

```json
{
  "schema_version": "m032.s02.trajectory.v1",
  "run_id": "RUN-abc123def456",
  "record_id": "REC-rejected-branch",
  "event_type": "branch_rejected",
  "phase": "verifier_gate",
  "step_id": "STEP-reject-candidate",
  "parent_step_id": "STEP-filter-candidate",
  "timestamp_utc": "2026-05-20T00:03:00Z",
  "source_refs": ["processed:artifact-a"],
  "input_refs": ["discovery:candidate-a", "verifier:decision-a"],
  "output_refs": ["trajectory:rejected-branch-a"],
  "summary": "Rejected relationship candidate due to insufficient deterministic evidence.",
  "observed_context": "The source context showed a possible relationship, but refs did not support the proposed direction.",
  "decision": "rejected",
  "decision_reason": "Verifier could not confirm required source-reference consistency.",
  "next_action": "record_rejection_and_continue",
  "non_authoritative": true,
  "branch_id": "BRANCH-abc123def456",
  "candidate_id": "CAND-abc123def456",
  "rejection_stage": "verifier",
  "rejection_reasons": ["insufficient_source_ref_consistency"],
  "salvageable_observations": ["possible repeated structure remains worth reviewing"],
  "retry_recommendation": "retry_with_more_context"
}
```

### `conclusion_trace.json` object

Purpose: one run-level graph of what happened and what should happen next.

Required top-level fields:

- `schema_version`
- `run_id`
- `trajectory_refs`
- `candidate_summary`
- `verifier_summary`
- `rejected_branch_summary`
- `external_review_refs`
- `useful_discoveries`
- `open_questions`
- `next_actions`
- `non_claims`

Example:

```json
{
  "schema_version": "m032.s02.conclusion_trace.v1",
  "run_id": "RUN-abc123def456",
  "trajectory_refs": ["trajectory:STEP-run-start", "trajectory:STEP-source-structure"],
  "candidate_summary": {"proposed": 3, "accepted": 1, "rejected": 1, "needs_review": 1},
  "verifier_summary": {"accepted": 1, "rejected": 1, "needs_review": 1},
  "rejected_branch_summary": [{"branch_id": "BRANCH-abc123def456", "reason": "insufficient_source_ref_consistency"}],
  "external_review_refs": ["review:pack-a"],
  "useful_discoveries": ["Repeated amendment-reference structure may support graph-context relationship candidates."],
  "open_questions": ["Whether the same structure appears across a larger corpus subset."],
  "next_actions": ["Run candidate normalization and verifier checks on a broader fixture set."],
  "non_claims": ["No legal correctness claim.", "No parser completeness claim.", "No R035 validation.", "No R038 validation."]
}
```

## Cross-reference model

The trajectory system is useful only if each artifact can be followed forward and backward. M032 uses explicit refs rather than implicit filename or line-order coupling.

### Ref namespaces

| Namespace | Points to | Example |
| --- | --- | --- |
| `trajectory:` | `trajectory.jsonl` or `discovery_steps.jsonl` records by `step_id` or `record_id`. | `trajectory:STEP-source-structure` |
| `attempt:` | MiniMax attempt summaries by `attempt_id`. | `attempt:ATTEMPT-abc123def456` |
| `candidate:` | Normalized discovery candidates by `candidate_id`. | `candidate:CAND-abc123def456` |
| `verifier:` | Deterministic verifier decisions by `decision_id`. | `verifier:DECISION-abc123def456` |
| `branch:` | Rejected branch records by `branch_id`. | `branch:BRANCH-abc123def456` |
| `review:` | External GPT-5.5 review packs or summaries by `review_id`. | `review:REVIEW-abc123def456` |
| `assessment:` | Curated research assessment sections or artifacts. | `assessment:09-discovery-run-assessment` |
| `source:` | Source artifact refs from registry or processed outputs. | `source:ARTIFACT-abc123def456` |

### Forward links

A source observation should link forward like this:

```text
source:ARTIFACT -> trajectory:STEP-observe -> attempt:ATTEMPT -> candidate:CAND -> verifier:DECISION -> review:REVIEW -> assessment:09-discovery-run-assessment
```

A rejected path should link forward like this:

```text
source:ARTIFACT -> trajectory:STEP-observe -> candidate:CAND -> verifier:DECISION -> branch:BRANCH -> conclusion_trace rejected_branch_summary
```

A needs-review path should link forward like this:

```text
source:ARTIFACT -> trajectory:STEP-observe -> candidate:CAND -> verifier:DECISION(needs_review) -> review:REVIEW -> conclusion_trace open_questions
```

### Backward links

Each downstream artifact must contain enough refs to reconstruct upstream provenance:

- MiniMax attempt summary includes `source_step_id` and `source_refs`.
- Candidate includes `source_step_ids`, `attempt_refs`, and `source_refs`.
- Verifier decision includes `candidate_id`, `trajectory_step_ids`, and `checked_refs`.
- Rejected branch includes `candidate_id`, `decision_id`, `source_refs`, and `salvageable_observations`.
- External review pack includes trajectory refs, candidate refs, verifier decision refs, rejected branch refs, and conclusion trace refs.
- Final assessment includes promoted refs to the trajectory, candidates, verifier decisions, review pack, rejected branches, and conclusion trace.

### Candidate lifecycle states

Candidate lifecycle states are:

- `proposed`: created by deterministic observation or MiniMax-assisted discovery.
- `normalized`: converted into a closed candidate record shape.
- `filtered`: kept, merged, or rejected before verifier routing.
- `routed_to_verifier`: ready for deterministic verifier checks.
- `accepted`: verifier accepted the candidate for bounded graph-context use.
- `rejected`: verifier rejected the candidate.
- `needs_review`: verifier could not accept or reject deterministically and routed the candidate for external review.
- `promoted_summary`: curated into a research assessment or compact durable evidence artifact.

MiniMax can move a candidate only to `proposed`. It cannot move a candidate to `accepted`.

### MiniMax attempt refs

MiniMax attempt records must include:

- `attempt_id`
- `source_step_id`
- `source_refs`
- `prompt_summary_ref`
- `response_summary_ref`
- `candidate_refs`
- `trajectory_refs`
- `non_authoritative: true`

The prompt and response summaries should preserve enough task and source-structure context to understand the discovery. They should not default to raw provider transport dumps.

### Verifier decision refs

Verifier records must include:

- `decision_id`
- `candidate_id`
- `candidate_state_before`
- `candidate_state_after`
- `trajectory_step_ids`
- `checked_refs`
- `decision_reason`
- `rejection_reasons`
- `review_queue_ref`

The verifier is the first component that may move a candidate to `accepted`.

### External review refs

External GPT-5.5 review packs must include:

- `review_id`
- `trajectory_refs`
- `attempt_refs`
- `candidate_refs`
- `verifier_decision_refs`
- `rejected_branch_refs`
- `conclusion_trace_ref`
- `review_questions`
- `expected_review_output`

GPT-5.5 is external control over CLI outputs. It is not the runtime gate that accepts candidates.

### Conclusion trace refs

`conclusion_trace.json` must include forward and backward refs:

- from useful discoveries to supporting trajectory steps;
- from candidate counts to candidate refs;
- from verifier summaries to decision refs;
- from rejected branch summaries to branch refs;
- from open questions to review refs or needs_review candidates;
- from next actions to concrete candidate, source, or assessment refs.

## Common envelope fields

Every JSONL record in the trajectory family should include these fields unless the specific file contract says otherwise:

```json
{
  "schema_version": "m032.s02.trajectory.v1",
  "run_id": "RUN-abc123def456",
  "record_id": "REC-abc123def456",
  "event_type": "source_structure_observed",
  "phase": "source_observation",
  "step_id": "STEP-abc123def456",
  "parent_step_id": null,
  "timestamp_utc": "2026-05-20T00:00:00Z",
  "source_refs": ["registry:example"],
  "input_refs": ["processed:example"],
  "output_refs": ["discovery:example"],
  "summary": "Observed a repeated amendment-reference structure useful for graph context.",
  "observed_context": "Bounded open-source context needed to understand the observation.",
  "decision": "observed",
  "decision_reason": "The structure repeats across source sections and has stable source refs.",
  "next_action": "candidate_extraction",
  "non_authoritative": true
}
```

## Envelope field meanings

- `schema_version`: exact contract version.
- `run_id`: stable run reference.
- `record_id`: stable record reference for this line or object.
- `event_type`: one of the event types listed above.
- `phase`: coarse stage such as `source_observation`, `minimax_discovery`, `candidate_normalization`, `verifier_gate`, `external_review`, or `conclusion`.
- `step_id`: stable step reference.
- `parent_step_id`: parent step when this record is part of a branch.
- `timestamp_utc`: wall-clock timestamp for ordering, not a semantic ID.
- `source_refs`: source or artifact refs used by the step.
- `input_refs`: upstream artifacts consumed.
- `output_refs`: artifacts produced.
- `summary`: human-readable compact summary.
- `observed_context`: useful source/legal or structural context needed for analysis.
- `decision`: local decision or observation status.
- `decision_reason`: why the record moved to the next step.
- `next_action`: expected next step.
- `non_authoritative`: true for observations, MiniMax outputs, and candidates before deterministic verification.

## Open-data logging stance

Open legal/source context can appear in `summary`, `observed_context`, and specialized record fields. The goal is analyzability. Do not strip useful context simply because it is legal text.

Practical hygiene still applies:

- no API keys or secrets;
- no irrelevant local absolute paths;
- no raw provider transport internals by default;
- no noisy low-value retry dumps;
- no ambiguous references that cannot be followed later.

## Non-claims

This contract does not claim:

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

This draft intentionally names `trajectory.jsonl`, `discovery_steps.jsonl`, `filtering_decisions.jsonl`, `rejected_branches.jsonl`, `conclusion_trace.json`, `run_id`, `step_id`, `parent_step_id`, `attempt_id`, `candidate_id`, `decision_id`, `review_id`, `source_ref`, `common envelope fields`, `event_type`, `open legal/source context`, `non_authoritative`, `R035 validation`, and `R038 validation`.
