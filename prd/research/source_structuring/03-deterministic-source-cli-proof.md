# M031 S03 — Deterministic Consultant XML Inventory CLI Proof

## Status

- Milestone: `M031-oqgiow — Consultant XML Source Structuring CLI Foundation`
- Slice: `S03 — Deterministic Consultant XML Inventory CLI`
- Proof status: `passed_for_inventory_cli_foundation`
- Requirement advanced: `R039`
- Requirements not validated: `R035`, `R038`

## Scope proven

S03 implements a deterministic no-LLM ConsultantPlus XML lifecycle CLI foundation:

- `scripts/source_cli.py`
  - `register`
  - `classify`
  - `process`
  - `status`
  - `run-batch`
- `scripts/source_lifecycle.py`
  - manifest loading and validation;
  - incoming-path confinement;
  - symlink, parent traversal, non-file, and non-XML rejection;
  - SHA-256 content addressing;
  - safe registry JSONL writers;
  - WordML 2003 XML shape probing;
  - source family / document role / parser route separation;
  - inventory-only processed outputs;
  - lifecycle status summaries.

The implementation is manifest-driven and does not glob `law-source/consultant/` directly.

## Durable outputs proven

In temporary workspaces, the CLI emitted:

```text
registry/source_artifacts.jsonl
registry/source_revisions.jsonl
registry/batches.jsonl
registry/source_classification.safe.jsonl
processed/consultant-wordml-v1/<corpus_id>/source_inventory.safe.jsonl
processed/consultant-wordml-v1/<corpus_id>/diagnostics.safe.jsonl
processed/consultant-wordml-v1/<corpus_id>/metrics.safe.json
```

The proof deliberately used temporary workspaces for smoke outputs because `law-source/consultant/raw`, `inbox`, `registry`, `processed`, and `runs` are not currently gitignored. This avoids accidentally committing raw legal source copies or generated raw-store content before the tracking policy is reviewed.

## Final verification evidence

### Focused regression tests

Command:

```bash
uv run pytest tests/test_source_cli_lifecycle.py -q
```

Result:

```text
10 passed
```

Coverage includes:

- register success;
- classify success;
- duplicate SHA idempotence;
- WordML 2003 namespace detection;
- unknown XML routing to `unsupported_xml`;
- malformed manifest failure;
- parent path escape rejection;
- unsafe doctype/entity rejection;
- processed inventory, diagnostics, and metrics outputs;
- status summaries;
- CLI smoke for register/classify/process/status/run-batch;
- no raw test text or absolute temporary paths in durable registry/processed outputs.

### Lint and syntax checks

Commands:

```bash
uv run ruff check scripts/source_lifecycle.py scripts/source_cli.py tests/test_source_cli_lifecycle.py
uv run python -m py_compile scripts/source_lifecycle.py scripts/source_cli.py tests/test_source_cli_lifecycle.py
```

Result:

```text
All checks passed.
```

### Bounded real-fixture smoke

The final smoke copied the two tracked ConsultantPlus XML fixtures into a temporary batch incoming directory and ran the CLI against the temporary workspace:

- `law-source/consultant/44-FZ-2026.xml`
- `law-source/consultant/Список документов (5).xml`

Commands exercised:

```bash
uv run python scripts/source_cli.py --workspace <tmp>/workspace register <tmp>/batch/batch.manifest.json
uv run python scripts/source_cli.py --workspace <tmp>/workspace classify <tmp>/batch/batch.manifest.json
uv run python scripts/source_cli.py --workspace <tmp>/workspace process <tmp>/batch/batch.manifest.json
uv run python scripts/source_cli.py --workspace <tmp>/workspace status
uv run python scripts/source_cli.py --workspace <tmp>/runbatch-workspace run-batch <tmp>/batch/batch.manifest.json
```

Observed safe summary:

```json
{
  "registered_count": 2,
  "classified_count": 2,
  "processed_count": 2,
  "route_counts": {
    "full_act": 1,
    "relation_list": 1
  },
  "malformed_count": 0,
  "durable_file_count": 7,
  "artifact_count": 2,
  "corpus_id": "CORPUS-ef76c2da96af"
}
```

### Durable-output safety scan

The safety scan checked only durable registry and processed outputs, not raw-store copies. It failed the run if durable outputs contained:

- raw legal text marker examples;
- source fixture filename text;
- temporary absolute paths;
- repository absolute source paths.

Result: passed.

## Q3 gate follow-up closure

The Q3 gate flagged two local-input risks before implementation:

1. manifest path traversal / symlink ingestion;
2. XML parser hardening.

S03 addressed these risks by:

- rejecting absolute manifest artifact paths;
- rejecting `..` parent traversal;
- rejecting symlink artifact paths;
- requiring artifact paths to resolve under the batch `incoming/` directory;
- requiring `.xml` artifacts;
- bounding XML probe size;
- rejecting XML doctype/entity declarations before parsing;
- testing path escape and unsafe doctype/entity behavior.

## Q4 requirement impact

S03 advances `R039` by proving a reproducible deterministic ConsultantPlus WordML source inventory CLI foundation.

S03 does not validate `R035`. It does not claim:

- parser completeness;
- legal correctness;
- product retrieval quality;
- ontology validation;
- graph-vector behavior;
- production ETL readiness;
- pilot readiness;
- LLM legal authority.

S03 also does not validate `R038`; it provides reviewable evidence that a later independent review gate can inspect.

## Known limitations

- The CLI currently provides inventory-only processing, not legal hierarchy parsing.
- The CLI does not interpret legal meaning.
- The CLI does not run LLM, MiniMax, DSPy, RLM, embedding, graph, or retrieval behavior.
- Source workspace tracking policy remains unresolved for persistent real-corpus runs. Raw-store and generated workspace outputs should remain temporary or explicitly reviewed until ignore/tracking policy is decided.
- XML resource bounds are conservative but not a full streaming parser completeness proof.

## Conclusion

S03 passes for the deterministic CLI foundation scope. The project now has a manifest-driven, no-LLM ConsultantPlus XML lifecycle CLI that can register, classify, process inventory-only outputs, report status, and run a bounded batch in temporary workspaces while preserving non-authoritative and no-raw-durable-output boundaries.
