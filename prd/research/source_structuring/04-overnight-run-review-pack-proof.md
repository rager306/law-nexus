# M031 S04 — Overnight Run Logging and Review Pack Proof

## Status

- Milestone: `M031-oqgiow — Consultant XML Source Structuring CLI Foundation`
- Slice: `S04 — Overnight Run Logging and Review Pack`
- Proof status: `passed_for_run_logging_and_review_pack_scope`
- Requirement advanced: `R039`
- Requirements not validated: `R035`, `R038`

## Scope proven

S04 adds safe run observability around the deterministic ConsultantPlus XML source CLI:

- `run-batch` now writes a run envelope under `runs/<run_id>/`.
- The run envelope includes:
  - `run.json`
  - `inputs.json`
  - `outputs.json`
  - `events.jsonl`
  - `errors.jsonl` when failures occur
  - `metrics.json`
- `review-pack` writes:
  - `review_pack.md`
  - `review_pack.json`
- `status` summarizes registry, processed corpus, and latest run state.

All run/review outputs are closed safe summaries: hashes, counts, output refs, route names, warning states, and non-claims. They do not include raw legal text, raw vectors, provider payloads, secrets, raw filenames, or absolute source paths.

## Final verification evidence

### Focused tests

```bash
uv run pytest tests/test_source_cli_lifecycle.py -q
```

Result:

```text
18 passed
```

Covered behavior:

- run ID generation;
- safe run directory validation;
- event/error JSONL allowlisting;
- hashed input summaries;
- workspace-relative output refs;
- output escape rejection;
- run metrics aggregation;
- workspace tracking warning;
- successful `run-batch` artifacts;
- malformed manifest failure diagnostics;
- lifecycle status run summaries;
- completed and failed review packs;
- review-pack non-claim markers;
- CLI smoke for `run-batch` and `review-pack`.

### Lint and syntax checks

```bash
uv run ruff check scripts/source_lifecycle.py scripts/source_cli.py tests/test_source_cli_lifecycle.py
uv run python -m py_compile scripts/source_lifecycle.py scripts/source_cli.py tests/test_source_cli_lifecycle.py
```

Result:

```text
All checks passed.
```

### Bounded real-fixture smoke

The smoke copied the two tracked ConsultantPlus XML fixtures into a temporary batch workspace:

- `law-source/consultant/44-FZ-2026.xml`
- `law-source/consultant/Список документов (5).xml`

It then ran:

```bash
uv run python scripts/source_cli.py --workspace <tmp>/workspace run-batch <tmp>/batch/batch.manifest.json
uv run python scripts/source_cli.py --workspace <tmp>/workspace review-pack <run_id>
uv run python scripts/source_cli.py --workspace <tmp>/workspace status
```

Observed safe summary:

```json
{
  "run_id": "RUN-fa8a2f2150eb",
  "status": "completed",
  "registered_count": 2,
  "classified_count": 2,
  "processed_count": 2,
  "route_counts": {
    "full_act": 1,
    "relation_list": 1
  },
  "error_count": 0,
  "durable_file_count": 14,
  "review_pack": true,
  "workspace_tracking_status": "warning"
}
```

The `workspace_tracking_status` warning is expected in the current repository because lifecycle output directories are not yet ignored/tracking-reviewed. It preserves the S04 Q3 safety concern instead of silently allowing persistent real-corpus run artifacts to be staged.

## Durable-output safety scan

The safety scan inspected durable files under temporary `registry`, `processed`, and `runs` outputs. It failed if these outputs contained:

- raw legal text marker examples;
- source fixture filename text;
- temporary absolute paths;
- repository absolute source paths.

Result: passed.

## Q3 gate closure

Q3 flagged local/operational data exposure risks:

1. persistent workspace tracking could leak raw/generated source material;
2. run/review artifacts could launder sensitive filenames, paths, diagnostics, secrets, provider payloads, or vectors.

S04 addresses these risks by:

- keeping run/review schemas closed and allowlisted;
- dropping unexpected event/error keys;
- recording `workspace_tracking` warning in run artifacts;
- writing hashed input summaries rather than raw filenames;
- writing workspace-relative output refs only;
- testing output escape rejection;
- testing durable-output safety for run and review artifacts;
- using temporary workspaces for real-fixture proof until tracking policy is settled.

## Q4 requirement impact

S04 advances `R039` by adding operational run evidence, JSONL event/error logs, metrics, status, and review packs around the deterministic source CLI.

S04 does not validate `R035`. It does not claim:

- parser completeness;
- legal correctness;
- product retrieval quality;
- ontology validation;
- graph-vector behavior;
- production ETL readiness;
- pilot readiness;
- LLM legal authority.

S04 supports future `R038` reviewability by producing inspectable proof artifacts, but it does not validate `R038` as an independent review gate.

## Known limitations

- Review packs summarize deterministic inventory runs only; they do not certify legal interpretation.
- Persistent real-corpus runs should wait for an explicit ignore/tracking policy for `law-source/consultant/{inbox,raw,registry,processed,runs}`.
- The proof uses temporary workspaces and copied source fixtures to avoid polluting tracked source directories.
- GitNexus will not see new S03/S04 symbols until the index is rebuilt after commit.

## Conclusion

S04 passes for overnight run logging and review-pack scope. The project now has safe run envelopes, event/error logs, metrics, status summaries, and review packs for deterministic ConsultantPlus XML inventory runs, while preserving R035/R038 non-validation boundaries and Q3 data-exposure safeguards.
