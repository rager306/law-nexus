# M032 S04 — Graph Context Candidate Normalization Proof

## Status

- Milestone: `M032-hy6i8r — MiniMax Assisted Source Discovery CLI`
- Slice: `S04 — Graph Context Candidate Normalization`
- Current task: `T01 — Design graph context candidate schema`
- Proof status: `draft_t01_candidate_schema`
- Requirement advanced: `R039`
- Requirements not validated: `R035`, `R038`

## Purpose

S04 turns MiniMax-assisted discovery output into structured graph-context candidate records. These candidates are proposed evidence for later deterministic checking; they are not accepted graph truth.

The source data is open legal data. Candidate records may preserve useful legal/source context when needed to understand a proposed structure, artifact, relationship, or graph-context signal. The normalization boundary should avoid practical hazards: fake accepted statuses from model output, fake verifier refs, untraceable source refs, raw provider transport internals, local absolute paths, secrets, and silent success on empty or malformed responses.

## Candidate artifact files

S04 writes candidate artifacts under:

```text
law-source/consultant/runtime/discovery/<run_id>/
  candidate_hypotheses.jsonl
  graph_context_signals.jsonl
  normalization_diagnostics.jsonl
```

The CLI result should reference these files by workspace-relative refs.

## Candidate kinds

The closed candidate kind vocabulary is:

- `source_pattern_observation`
- `artifact_candidate`
- `structure_candidate`
- `relationship_candidate`
- `graph_context_signal`

MiniMax may suggest any of these kinds, but normalization maps them into the closed vocabulary. Unknown kinds become `graph_context_signal` with `normalization_warnings` or are routed to diagnostics when the output cannot be understood.

## Candidate lifecycle status

S04 may emit only these lifecycle statuses:

- `proposed`
- `needs_review`
- `rejected`

S04 must not emit:

- `accepted`
- `verified`
- `validated`
- `production_ready`

`accepted` is reserved for S05 deterministic verifier decisions. If MiniMax output claims an accepted or verified status, S04 ignores that claim and records the candidate as `proposed` or emits a diagnostic.

## Candidate record schema

Each row in `candidate_hypotheses.jsonl` uses this shape:

```json
{
  "schema_version": "m032.s04.graph-context-candidate.v1",
  "candidate_id": "CAND-abc123def456",
  "run_id": "RUN-abc123def456",
  "attempt_id": "ATTEMPT-abc123def456",
  "candidate_kind": "relationship_candidate",
  "lifecycle_status": "proposed",
  "source_refs": ["processed:inventory-a"],
  "trajectory_refs": ["trajectory:STEP-source-structure"],
  "attempt_refs": ["attempt:ATTEMPT-abc123def456"],
  "candidate_summary": "A repeated amendment-reference structure may support a graph relationship candidate.",
  "supporting_context": "Useful open legal/source context that explains why this candidate exists.",
  "confidence_bucket": "medium",
  "normalization_warnings": [],
  "model_claims_ignored": [],
  "non_authoritative": true,
  "non_claims": [
    "Candidate is proposed only.",
    "No deterministic verifier acceptance.",
    "No legal correctness claim.",
    "No parser completeness claim.",
    "No R035 validation.",
    "No R038 validation."
  ]
}
```

Required refs:

- `run_id`
- `attempt_id`
- `candidate_id`
- `source_refs`
- `trajectory_refs`
- `attempt_refs`

Required explanation fields:

- `candidate_summary`
- `supporting_context`
- `confidence_bucket`
- `normalization_warnings`
- `model_claims_ignored`

## Graph context signal schema

Each row in `graph_context_signals.jsonl` is a compact projection for downstream graph-context planning:

```json
{
  "schema_version": "m032.s04.graph-context-signal.v1",
  "signal_id": "SIGNAL-abc123def456",
  "candidate_id": "CAND-abc123def456",
  "run_id": "RUN-abc123def456",
  "signal_type": "relationship_candidate",
  "signal_summary": "Repeated amendment-reference relation candidate.",
  "source_refs": ["processed:inventory-a"],
  "trajectory_refs": ["trajectory:STEP-source-structure"],
  "lifecycle_status": "proposed",
  "non_authoritative": true
}
```

## Normalization diagnostics schema

Malformed, empty, or untraceable discovery output must not be treated as successful candidate generation. S04 writes diagnostics to `normalization_diagnostics.jsonl`:

```json
{
  "schema_version": "m032.s04.normalization-diagnostic.v1",
  "diagnostic_id": "DIAG-abc123def456",
  "run_id": "RUN-abc123def456",
  "attempt_id": "ATTEMPT-abc123def456",
  "status": "rejected",
  "error_kind": "empty_discovery_output",
  "message": "MiniMax response summary did not contain candidate material.",
  "source_refs": ["processed:inventory-a"],
  "trajectory_refs": ["trajectory:STEP-source-structure"],
  "non_authoritative": true
}
```

Expected diagnostic statuses:

- `rejected`
- `needs_review`

Expected diagnostic error kinds:

- `empty_discovery_output`
- `malformed_candidate_payload`
- `untraceable_candidate_refs`
- `unsupported_candidate_kind`
- `model_claimed_accepted_status`

## Normalization strategy

S04 accepts either structured JSON from a mocked or future provider response, or a plain response summary.

Structured JSON path:

1. Parse response summary as JSON object or JSON array when possible.
2. Extract candidate-like entries from `candidates`, `graph_context_signals`, or the top-level array.
3. Normalize candidate kinds into the closed vocabulary.
4. Generate local candidate IDs and signal IDs.
5. Force lifecycle status to `proposed` unless a diagnostic is required.
6. Record any ignored model claims in `model_claims_ignored`.
7. Write candidate and signal rows.

Plain text fallback:

1. If response summary is non-empty text, create one `graph_context_signal` candidate.
2. Preserve useful source/legal context in `supporting_context`.
3. Mark confidence as `unknown` unless the text gives bounded rationale.
4. Keep lifecycle status `proposed`.

Empty or malformed path:

1. Write `normalization_diagnostics.jsonl`.
2. Do not claim candidate generation success.
3. Return a CLI/lifecycle result that reports `candidate_count=0` and diagnostic refs.

## Provenance and integrity guardrails

- Candidate IDs are generated locally, not accepted from MiniMax as authority.
- `lifecycle_status` is generated locally.
- `accepted` cannot appear in S04 candidate outputs.
- Verifier refs cannot be invented in S04 candidate outputs.
- Candidate rows must link to attempt refs and trajectory refs.
- Source refs must remain explicit and workspace/source-reference oriented.
- Raw provider transport internals are not candidate fields.
- Open legal/source context should be kept when useful for analysis.

## S04 implementation summary

S04 implemented candidate normalization in `scripts/source_lifecycle.py` and wired it into the existing `discover` CLI flow.

### Added lifecycle constants and helpers

- `CANDIDATE_SCHEMA_VERSION`
- `GRAPH_CONTEXT_SIGNAL_SCHEMA_VERSION`
- `NORMALIZATION_DIAGNOSTIC_SCHEMA_VERSION`
- `KNOWN_CANDIDATE_KINDS`
- `discovery_directory()`
- `normalize_candidate_kind()`
- `normalize_discovery_candidates()`

### Runtime outputs

Completed discovery attempts now write:

```text
runtime/discovery/<run_id>/candidate_hypotheses.jsonl
runtime/discovery/<run_id>/graph_context_signals.jsonl
```

Empty or malformed discovery output writes:

```text
runtime/discovery/<run_id>/normalization_diagnostics.jsonl
```

### CLI result extensions

The `discover` command now returns:

- `candidate_count`
- `signal_count`
- `candidate_refs`
- `discovery_output_refs`

These are added only for completed discovery attempts. Missing-config paths still return `blocked_missing_config` and do not create candidates.

### Normalization behavior proven

S04 tests prove:

- structured JSON candidate payloads normalize into `candidate_hypotheses.jsonl` and `graph_context_signals.jsonl`;
- plain text response summaries fall back to one `graph_context_signal` candidate;
- empty output produces an `empty_discovery_output` diagnostic;
- malformed JSON-looking output produces a `malformed_candidate_payload` diagnostic;
- model-claimed `accepted` status is ignored and recorded in `model_claims_ignored`;
- all emitted candidates remain `lifecycle_status: proposed`;
- CLI mocked smoke writes trajectory, attempt, candidate, and signal artifacts.

### Boundary preserved

S04 does not accept candidates as graph truth. It only normalizes proposed candidates. S05 owns deterministic verifier acceptance.

## Non-claims

This schema does not claim:

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

This draft intentionally names `source_pattern_observation`, `artifact_candidate`, `structure_candidate`, `relationship_candidate`, `graph_context_signal`, `candidate_hypotheses.jsonl`, `graph_context_signals.jsonl`, `normalization_diagnostics.jsonl`, `candidate_id`, `run_id`, `attempt_id`, `source_refs`, `trajectory_refs`, `attempt_refs`, `lifecycle_status`, `proposed`, `needs_review`, `rejected`, `model_claims_ignored`, `supporting_context`, `open legal/source context`, `non_authoritative`, `R035 validation`, and `R038 validation`.
