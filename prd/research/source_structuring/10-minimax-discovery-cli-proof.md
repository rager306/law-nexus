# M032 S03 — MiniMax Discovery CLI Proof

## Status

- Milestone: `M032-hy6i8r — MiniMax Assisted Source Discovery CLI`
- Slice: `S03 — MiniMax Discovery CLI Command`
- Current task: `T01 — Map MiniMax discovery CLI seam`
- Proof status: `draft_t01_seam_mapping`
- Requirement advanced: `R039`
- Requirements not validated: `R035`, `R038`

## T01 objective

Identify the smallest implementation seam for adding MiniMax-assisted discovery to the existing ConsultantPlus source lifecycle CLI while preserving the S01 runtime workspace policy and S02 trajectory contract.

## Current CLI shape

`scripts/source_cli.py` is a small `argparse` boundary. It defines:

- `build_parser()`
- `run_register()`
- `run_classify()`
- `run_process()`
- `run_status()`
- `run_batch_command()`
- `run_review_pack()`
- `main()`

Each command delegates to `scripts/source_lifecycle.py` and prints one JSON result. The minimal CLI seam is therefore:

1. add a `discover` subcommand in `build_parser()`;
2. add a `run_discover()` handler;
3. delegate implementation to a lifecycle helper rather than putting discovery logic inside CLI parsing code.

## Current lifecycle seam

`scripts/source_lifecycle.py` already provides reusable primitives that S03 can extend:

- deterministic JSON and JSONL writers: `write_json`, `write_jsonl`, `append_jsonl`;
- workspace-safe run helpers: `run_directory`, `safe_run_id`, `safe_output_ref`, `output_summary`;
- existing run logs: `append_run_event`, `append_run_error`, `safe_log_row`;
- existing run envelope: `run_batch_with_envelope`;
- existing review pack: `build_review_pack`.

The smallest lifecycle extension is:

1. add trajectory directory helpers under `workspace / "runtime" / "trajectory"` or run-scoped trajectory refs following the S01/S02 contract;
2. add stable IDs for attempt, record, step, candidate placeholder refs where needed;
3. add append helpers for S02-compatible trajectory JSONL records;
4. add MiniMax attempt summary writer;
5. add `discover_with_minimax(...)` or equivalent orchestration helper that `run_discover()` can call.

## Current test seam

`tests/test_source_cli_lifecycle.py` already tests both helper-level behavior and subprocess CLI behavior. S03 can extend it with:

- mocked MiniMax success path;
- missing configuration path;
- trajectory files written;
- MiniMax attempt summaries written;
- CLI `discover` smoke using a temporary workspace;
- non-authoritative boundaries in durable output.

No new broad test framework is needed.

## Impact analysis result

GitNexus impact analysis was attempted before edits.

Observed results:

- `gitnexus_impact(repo="law-nexus", target="build_parser", direction="upstream")` returned ambiguous matches only from older indexed scripts, not the new `scripts/source_cli.py`.
- `gitnexus_impact(repo="law-nexus", target="run_batch_with_envelope", direction="upstream")` returned target not found.

Interpretation:

M031/M032 files are still new/untracked and have not been committed or reindexed, so GitNexus cannot yet resolve the source CLI/lifecycle symbols. This matches the known post-M031 limitation. For S03 edits, blast-radius control must rely on local LSP symbols, focused tests, subprocess smoke, and final `gitnexus_detect_changes` until commit and `npx gitnexus analyze` make these symbols visible.

Risk level from indexed graph: no actionable indexed blast radius for the new symbols.

## Chosen implementation seam

S03 should implement the smallest coherent seam:

1. In `scripts/source_lifecycle.py`:
   - add constants for trajectory and attempt schema versions;
   - add stable ID helpers for records, steps, attempts, and maybe placeholder candidates;
   - add `trajectory_directory(workspace_root, run_id)`;
   - add `minimax_attempt_directory(workspace_root, run_id)`;
   - add `append_trajectory_record(...)`;
   - add `write_minimax_attempt_summary(...)`;
   - add a minimal `discover_with_minimax(...)` helper that supports dependency injection for tests.
2. In `scripts/source_cli.py`:
   - add `discover` subcommand;
   - add arguments that consume existing workspace/run refs, not ad hoc corpus globbing;
   - add `run_discover()` delegating to lifecycle helper;
   - print one bounded JSON result.
3. In tests:
   - use a fake MiniMax client/callable for success;
   - use missing config to test clear failure diagnostics;
   - assert trajectory and attempt files exist and contain S02-compatible fields.

## Implementation guardrails

- MiniMax output is non-authoritative.
- MiniMax may create proposed discovery material only.
- Deterministic verifier is the first component that may accept a candidate.
- GPT-5.5 is not introduced as an embedded runtime judge.
- Discovery command should consume run/workspace artifacts, not arbitrary source globbing.
- Missing MiniMax configuration must be an explicit non-success diagnostic, not a silent no-op.
- Logs should preserve useful open legal/source context, not over-redact it.
- Logs should avoid secrets, irrelevant local absolute paths, raw provider transport internals, noisy dumps, and ambiguous refs.

## S03 implementation summary

S03 implemented the planned seam.

### Added lifecycle helpers

`scripts/source_lifecycle.py` now includes:

- `TRAJECTORY_SCHEMA_VERSION`
- `MINIMAX_ATTEMPT_SCHEMA_VERSION`
- `DEFAULT_MINIMAX_MODEL`
- `DEFAULT_MINIMAX_ENDPOINT`
- `DEFAULT_MINIMAX_API_KEY_ENV`
- `stable_discovery_id()`
- `trajectory_directory()`
- `minimax_attempt_directory()`
- `trajectory_record()`
- `append_trajectory_record()`
- `write_minimax_attempt_summary()`
- `discover_with_minimax()`

The helpers write run-scoped trajectory records under `runtime/trajectory/<run_id>/` and MiniMax attempt summaries under `runtime/minimax-attempts/<run_id>/`.

### Added CLI command

`scripts/source_cli.py` now exposes:

```bash
uv run python scripts/source_cli.py --workspace <workspace> discover \
  --run-id RUN-abc123def456 \
  --source-ref processed:inventory-a \
  --prompt-summary "Use open legal/source context to discover graph-context structures."
```

Test and deterministic-smoke usage can pass:

```bash
--mock-response <response.json>
```

When no mock response is provided and the MiniMax API key environment variable is missing, the command returns JSON with:

- `status: blocked_missing_config`
- `root_cause: minimax-credential-missing`
- exit code `2`

This is intentionally an explicit non-success diagnostic, not a silent no-op.

### Provider behavior

The command supports a credential-gated MiniMax OpenAI-compatible chat-completions call through stdlib `urllib` when the configured API key environment variable is present. T03 completion does not require live credentials; the verified paths are mocked success and missing configuration.

The durable interface stores normalized summaries, not raw provider transport internals.

### Output behavior

Both completed and blocked discovery attempts write:

- `runtime/trajectory/<run_id>/discovery_steps.jsonl`
- `runtime/minimax-attempts/<run_id>/attempts.jsonl`

The records include:

- `run_id`
- `step_id`
- `attempt_id`
- `source_refs`
- `prompt_summary`
- `response_summary`
- `model_name`
- `status`
- `decision_reason`
- `non_authoritative: true`

### Verification summary

S03 verification covers:

- helper-level trajectory and attempt writer tests;
- CLI mocked MiniMax success path;
- CLI missing-config path;
- policy and trajectory contract regression tests;
- ruff;
- py_compile;
- LSP diagnostics;
- mocked CLI smoke;
- GitNexus scope check.

## Non-claims

This T01 seam mapping does not claim:

- legal correctness;
- parser completeness;
- product retrieval quality;
- ontology validation;
- graph-vector behavior;
- production ETL readiness;
- pilot readiness;
- R035 validation;
- R038 validation.

## T01 verification

Verified by reading current CLI, lifecycle, and CLI lifecycle tests; collecting LSP symbols; attempting GitNexus impact analysis; and recording the chosen seam and index limitation.
