# M031 S06 — Hypothesis Verifier Skeleton Proof

## Status

- Milestone: `M031-oqgiow — Consultant XML Source Structuring CLI Foundation`
- Slice: `S06 — Hypothesis Verifier Skeleton`
- Proof status: `passed_for_deterministic_verifier_skeleton_scope`
- Requirement advanced: `R039`
- Requirements not validated: `R035`, `R038`

## Scope proven

S06 implements a deterministic no-LLM verifier skeleton for the S05 source-structuring hypothesis protocol.

Implemented files:

- `scripts/source_hypothesis_verifier.py`
- `tests/test_source_hypothesis_verifier.py`

The verifier can:

- validate a closed `structural_hypothesis_proposal` payload;
- check safe IDs and safe refs;
- check allowed enum values;
- require `non_authoritative: true` and non-claim markers;
- reject extra top-level and nested fields;
- reject forbidden payload classes recursively;
- emit safe `verifier_decision` objects;
- produce `needs_review` for safe proposals with insufficient deterministic evidence;
- emit `review_queue_item` artifacts for needs-review decisions;
- write fixed output filenames via CLI `--output-dir`.

S06 does not call MiniMax, GPT-5.5, DSPy, RLM, embeddings, FalkorDB, network APIs, or provider APIs.

## Final verification evidence

### Focused tests

```bash
uv run pytest tests/test_source_hypothesis_verifier.py -q
```

Result:

```text
15 passed
```

Covered behavior:

- accepted proposal decision;
- closed schema enforcement;
- invalid enum rejection;
- missing non-claims rejection;
- unsafe ref rejection;
- recursive forbidden payload detection;
- raw text marker rejection;
- absolute path rejection;
- provider payload indicator rejection;
- legal-answer prose rejection;
- parser-completeness overclaim rejection;
- R035 validation overclaim rejection;
- raw vector/embedding marker rejection;
- bounded rejected decision notes;
- needs_review decision and review_queue_item creation;
- CLI accepted, rejected, and needs_review output smoke.

### Lint and syntax checks

```bash
uv run ruff check scripts/source_hypothesis_verifier.py tests/test_source_hypothesis_verifier.py
uv run python -m py_compile scripts/source_hypothesis_verifier.py tests/test_source_hypothesis_verifier.py
```

Result:

```text
All checks passed.
```

### CLI smoke

The final smoke created three temporary proposal payloads:

- accepted proposal;
- safe but insufficiently evidenced proposal;
- rejected proposal with forbidden vector marker.

Observed result:

```json
{
  "accepted": "accepted",
  "needs_review": "needs_review",
  "rejected": "rejected",
  "queue_item": "legalgraph-review-queue-item/v1"
}
```

Rejected CLI path exited with code `1`, while accepted and needs_review paths exited successfully.

### Durable-output safety scan

The smoke scanned generated decision and review queue JSON artifacts and rejected concrete forbidden examples including raw legal text examples, repository absolute paths, managed-provider secret names, secret-like prefixes, and provider payload markers.

Result: passed.

## Q3 gate closure

Q3 flagged these implementation risks:

1. nested payload bypass;
2. safe-ref/path confusion;
3. CLI output overwrite/artifact planting;
4. accidental provider/LLM boundary regression;
5. overclaim laundering in decision notes and summaries.

S06 addresses these risks by:

- recursive rendered-payload forbidden marker scanning;
- closed top-level and nested schema field checks;
- safe ID and safe ref validation;
- omission of unsafe refs from rejected decisions;
- fixed CLI output filenames only;
- no provider/network imports;
- bounded decision notes;
- explicit non-claims in verifier decisions and review queue items;
- negative tests for every planned rejection reason.

## Q4 requirement impact

S06 advances `R039` by providing an executable deterministic verifier skeleton for future structural hypotheses over source lifecycle artifacts.

S06 does not validate `R035`. It does not claim:

- parser completeness;
- legal correctness;
- product retrieval quality;
- ontology validation;
- graph-vector behavior;
- production ETL readiness;
- pilot readiness;
- LLM legal authority.

S06 supports future `R038` reviewability by producing verifier decisions and review queue artifacts, but it does not validate `R038` as an independent review gate.

## Known limitations

- The verifier checks schema, refs, forbidden payloads, and deterministic evidence presence; it does not prove legal or parser correctness.
- Safe-ref resolution is syntactic in S06. Future milestones may connect it to concrete workspace/run artifact existence checks.
- The verifier skeleton uses marker-based forbidden payload checks, not a complete data-loss-prevention engine.
- No live worker/provider output is tested in S06.

## Conclusion

S06 passes for deterministic verifier skeleton scope. Future worker integrations now have an executable fail-closed gate for structural hypothesis proposals before S07 assesses the source foundation and before any provider-backed hypothesis milestone is considered.
