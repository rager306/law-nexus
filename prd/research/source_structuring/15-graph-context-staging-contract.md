# M033 S01 — Graph Context Staging Contract

## Status

- Milestone: `M033-1vpo4b — Graph Context Formation from Verified Candidates`
- Slice: `S01 — Staging Schema and Provenance Contract`
- Contract status: `draft_t01`
- Requirement advanced: follow-on bounded `R039`
- Requirements not validated: `R035`, `R037`, `R038`

## Purpose

This contract defines how accepted M032 source-discovery candidates become deterministic `graph_context` staging records. A staging record is a structural graph-context proposal with provenance refs. It is not legal truth, not production graph data, and not a product retrieval-quality claim.

The contract is intentionally deterministic-first. MiniMax may propose source-discovery candidates and GPT-5.5 may later review output packs, but neither provider is an acceptance authority. Only deterministic verifier decisions may feed accepted staging records.

## Safe output location

S02 and later slices should write staging outputs under the run-scoped runtime workspace:

```text
law-source/consultant/runtime/graph-context/<run_id>/
  graph_context_staging.jsonl
  graph_context_diagnostics.jsonl
  graph_context_summary.json
```

Proof runs should continue to use temporary workspaces unless a runtime tracking policy has been implemented and verified.

## Schema versions

Planned schema identifiers:

- `m033.s01.graph-context-staging.v1`
- `m033.s01.graph-context-diagnostic.v1`
- `m033.s01.graph-context-summary.v1`

## Record kinds

Allowed `graph_context` staging record kinds:

- `source_pattern_observation`
- `artifact_candidate`
- `structure_candidate`
- `relationship_candidate`
- `graph_context_signal`

These are structural context records only. They do not create legal obligations, legal interpretations, production graph nodes, production graph edges, or legal-answer evidence.

## Required accepted input status

A candidate may produce a staging record only when all are true:

1. normalized candidate row has a stable `candidate_id`;
2. verifier decision has a stable `decision_id`;
3. verifier status is `accepted`;
4. provenance refs are present and safe;
5. record kind is one of the allowed graph-context kinds.

Rejected and `needs_review` candidates must not become accepted staging records. They may produce diagnostics or skipped summaries.

## Required provenance refs

Every staging record must include explicit provenance refs:

- `candidate_refs`: refs to normalized candidate rows, for example `candidate:CAND-...`;
- `verifier_refs`: refs to deterministic verifier decisions, for example `decision:DECISION-...`;
- `trajectory_refs`: refs to discovery trajectory steps, for example `trajectory:STEP-...`;
- `source_refs`: safe workspace-relative source or derived artifact refs;
- `attempt_refs`: optional MiniMax attempt refs when available;
- `review_pack_refs`: optional external review pack refs when available.

The refs are provenance refs, not raw legal text, raw filenames, local absolute paths, raw vectors, provider payloads, secrets, or legal-answer prose.

## Staging record shape

A `graph_context` staging row should contain:

```json
{
  "schema_version": "m033.s01.graph-context-staging.v1",
  "graph_context_id": "GCTX-...",
  "run_id": "RUN-...",
  "record_kind": "relationship_candidate",
  "candidate_id": "CAND-...",
  "decision_id": "DECISION-...",
  "staging_status": "staged",
  "safe_summary": "bounded structural summary",
  "confidence_bucket": "medium",
  "candidate_refs": ["candidate:CAND-..."],
  "verifier_refs": ["decision:DECISION-..."],
  "trajectory_refs": ["trajectory:STEP-..."],
  "source_refs": ["processed/consultant-wordml-v1/CORPUS/source_inventory.safe.jsonl"],
  "attempt_refs": ["attempt:ATTEMPT-..."],
  "review_pack_refs": [],
  "non_authoritative": true,
  "non_claims": [
    "graph_context staging does not claim legal correctness",
    "graph_context staging does not claim parser completeness",
    "graph_context staging does not validate R035",
    "graph_context staging does not validate R037",
    "graph_context staging does not validate R038"
  ]
}
```

## Diagnostic shape

A diagnostic row should contain:

```json
{
  "schema_version": "m033.s01.graph-context-diagnostic.v1",
  "diagnostic_id": "GCTXDIAG-...",
  "run_id": "RUN-...",
  "candidate_id": "CAND-...",
  "decision_id": "DECISION-...",
  "diagnostic_status": "skipped",
  "reason_codes": ["verifier-status-not-accepted"],
  "safe_summary": "candidate was not staged",
  "non_authoritative": true
}
```

Reason codes should be deterministic and safe. They should explain missing provenance, unsupported kind, non-accepted verifier status, or unsafe refs without echoing local absolute paths or raw provider payloads.

## Downstream export scope

S02 may export accepted candidates into staging JSONL. That export is a graph-context staging export only.

S02 must not:

- create FalkorDB production graph data;
- validate R037;
- validate ontology architecture claims in R035;
- validate independent review process claims in R038;
- treat MiniMax or GPT-5.5 as authority;
- emit legal-answer prose.

## Implementation evidence

S01 implemented executable contract helpers in `scripts/source_lifecycle.py`:

- `GRAPH_CONTEXT_STAGING_SCHEMA_VERSION`
- `GRAPH_CONTEXT_DIAGNOSTIC_SCHEMA_VERSION`
- `GRAPH_CONTEXT_SUMMARY_SCHEMA_VERSION`
- `GRAPH_CONTEXT_RECORD_KINDS`
- `graph_context_candidate_to_record()`

Focused tests in `tests/test_source_graph_context_staging.py` prove:

- accepted verifier decisions become `graph_context` staging rows;
- candidate refs, verifier refs, trajectory refs, and source refs are required in staged records;
- non-accepted verifier statuses become skipped diagnostics;
- unsafe absolute source refs are not echoed into diagnostics;
- allowed record kinds stay bounded to the M032 source-discovery candidate vocabulary;
- staging rows preserve R035, R037, and R038 non-validation.

## Non-claims

This contract does not claim:

- legal correctness;
- parser completeness;
- product retrieval quality;
- production ETL readiness;
- FalkorDB ingestion readiness;
- graph-vector behavior;
- pilot readiness;
- R035 validation;
- R037 validation;
- R038 validation.

## T01 verification markers

This contract intentionally includes `graph_context`, provenance refs, candidate refs, verifier refs, trajectory refs, source refs, `R035`, `R037`, `R038`, safe output location, accepted input status, diagnostics, and downstream export scope.
