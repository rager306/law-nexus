# M032 S06 — External GPT-5.5 Review Pack Proof

## Status

- Milestone: `M032-hy6i8r — MiniMax Assisted Source Discovery CLI`
- Slice: `S06 — External GPT 5.5 Review Pack`
- Current task: `T01 — Design external review pack protocol`
- Proof status: `draft_t01_review_pack_protocol`
- Requirement advanced: `R039`
- Requirements not validated: `R035`, `R038`

## Purpose

S06 packages CLI discovery outputs for external GPT-5.5 analysis. GPT-5.5 remains outside the runtime pipeline. It reviews generated artifacts and may provide critique, but it does not accept candidates, override deterministic verifier decisions, or act as a runtime judge.

The legal source data is open. The review pack should preserve useful source/context summaries needed to analyze discovered structures and relationships. The pack should avoid only practical hygiene issues: API keys, secrets, irrelevant local absolute paths, raw provider transport internals, noisy dumps, and ambiguous refs.

## Review pack outputs

S06 writes run-scoped external review artifacts under:

```text
law-source/consultant/runtime/external-review/<run_id>/
  review_pack.json
  review_pack.md
  external_review_summary.md
```

`review_pack.json` is the machine-readable bundle.

`review_pack.md` is the human/GPT-readable bundle.

`external_review_summary.md` is a short local summary explaining what an external reviewer should inspect. It is not the GPT-5.5 answer.

## Required input artifact classes

The pack should consume available artifacts from:

- `runtime/trajectory/<run_id>/discovery_steps.jsonl`
- `runtime/minimax-attempts/<run_id>/attempts.jsonl`
- `runtime/discovery/<run_id>/candidate_hypotheses.jsonl`
- `runtime/discovery/<run_id>/graph_context_signals.jsonl`
- `runtime/discovery/<run_id>/normalization_diagnostics.jsonl`
- `runtime/verifier/<run_id>/verifier_decisions.jsonl`
- `runtime/verifier/<run_id>/review_queue_items.jsonl`
- `runtime/verifier/<run_id>/rejection_reasons.jsonl`

Missing optional files should be reported as missing sections, not treated as success with hidden omissions.

## Review pack JSON schema

`review_pack.json` should include:

```json
{
  "schema_version": "m032.s06.external-review-pack.v1",
  "run_id": "RUN-abc123def456",
  "review_id": "REVIEW-abc123def456",
  "review_scope": "external_gpt55_cli_output_review",
  "trajectory_summary": {},
  "minimax_attempt_summary": {},
  "candidate_summary": {},
  "verifier_summary": {},
  "rejected_branch_summary": {},
  "review_queue_summary": {},
  "normalization_diagnostics_summary": {},
  "artifact_refs": [],
  "review_questions": [],
  "expected_external_review_output": {},
  "missing_sections": [],
  "non_authoritative": true,
  "non_claims": []
}
```

## Required summaries

### `trajectory_summary`

Should include:

- trajectory record count;
- event types observed;
- phase list;
- key step refs;
- any run failure or blocked path markers.

### `minimax_attempt_summary`

Should include:

- attempt count;
- statuses;
- model names;
- prompt summaries;
- response summaries;
- explicit non-authoritative boundary.

### `candidate_summary`

Should include:

- candidate count;
- candidate kinds;
- lifecycle statuses;
- candidate refs;
- useful open-source context summaries;
- model claims ignored.

### `verifier_summary`

Should include:

- verifier decision count;
- accepted count;
- rejected count;
- needs_review count;
- checked refs;
- acceptance evidence refs;
- decision notes.

### `rejected_branch_summary`

Should include:

- rejected candidate IDs;
- rejection reason categories;
- source refs;
- trajectory refs.

### `review_queue_summary`

Should include:

- needs_review item count;
- queue item IDs;
- review reasons;
- evidence refs.

### `normalization_diagnostics_summary`

Should include:

- diagnostic count;
- diagnostic error kinds;
- diagnostic statuses.

## Required review questions

The pack should ask GPT-5.5 to review the CLI outputs, not to decide legal truth.

Required questions:

1. Are the discovered structures and graph-context candidates understandable from the trajectory and supporting context?
2. Do accepted verifier decisions appear traceable to candidate refs, trajectory refs, and evidence refs?
3. Are any rejected or needs_review branches likely to reveal useful parser or graph-context improvements?
4. Are there patterns across MiniMax attempts and deterministic verifier outcomes that should influence the next source-structuring milestone?
5. Are there ambiguities in refs, trajectory steps, or candidate summaries that would block human review?
6. Does the pack avoid overclaiming legal correctness, parser completeness, retrieval quality, R035 validation, or R038 validation?

## Expected external review output shape

External GPT-5.5 review, if performed later, should return a separate review artifact with:

- `review_verdict`: `useful | needs_more_evidence | not_useful | blocked_by_traceability`
- `useful_findings`
- `candidate_concerns`
- `traceability_concerns`
- `recommended_next_actions`
- `non_claims`

S06 does not generate that review verdict. It only prepares the pack.

## Boundary language

The review pack must state:

- GPT-5.5 is external control over CLI outputs.
- GPT-5.5 is not an embedded runtime judge.
- GPT-5.5 does not accept candidates into graph truth.
- Deterministic verifier decisions remain the runtime candidate gate.
- External review does not validate R038 unless the independent review is actually performed and recorded.

## Q3 risk handling

S06 handles the flagged integrity risks by requiring:

- all available rejected and needs_review branches to be summarized;
- missing optional sections to be listed in `missing_sections`;
- artifact refs to be workspace-relative;
- pack language to keep GPT-5.5 external;
- no API keys, local absolute paths, or raw provider transport internals in review artifacts.

## S06 implementation summary

S06 implemented external review pack generation without calling GPT-5.5.

### Added lifecycle helpers

- `EXTERNAL_REVIEW_PACK_SCHEMA_VERSION`
- `external_review_directory()`
- `build_external_review_pack()`

### Runtime outputs

S06 writes:

```text
runtime/external-review/<run_id>/review_pack.json
runtime/external-review/<run_id>/review_pack.md
runtime/external-review/<run_id>/external_review_summary.md
```

### CLI integration

The source CLI now exposes:

```bash
uv run python scripts/source_cli.py --workspace <workspace> external-review-pack <run_id>
```

This command packages existing CLI outputs. It does not call GPT-5.5.

### Behaviors proven

S06 verification proves:

- review packs summarize trajectory records;
- MiniMax attempt summaries are included;
- candidate counts, kinds, and lifecycle statuses are included;
- verifier status counts, checked refs, and evidence refs are included;
- rejected branch and review queue sections are represented, with missing optional sections listed in `missing_sections`;
- review questions are included;
- `review_pack.md`, `review_pack.json`, and `external_review_summary.md` are written;
- GPT-5.5 is described as external control over CLI outputs, not an embedded runtime judge;
- external review pack preparation does not validate R038.

## Non-claims

This protocol does not claim:

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

This draft intentionally names `review_pack.json`, `review_pack.md`, `external_review_summary.md`, `trajectory_summary`, `minimax_attempt_summary`, `candidate_summary`, `verifier_summary`, `rejected_branch_summary`, `review_queue_summary`, `normalization_diagnostics_summary`, `review_questions`, `expected_external_review_output`, `missing_sections`, GPT-5.5 external control, not embedded runtime judge, deterministic verifier decisions, `R035 validation`, and `R038 validation`.
