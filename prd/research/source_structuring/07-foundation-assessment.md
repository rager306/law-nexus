# M031 S07 — Source Foundation Assessment

## Status

- Milestone: `M031-oqgiow — Consultant XML Source Structuring CLI Foundation`
- Slice: `S07 — Initial Corpus Run and Foundation Assessment`
- Assessment status: `draft_t01_foundation_inventory`
- Requirement advanced: `R039`
- Requirements not validated: `R035`, `R038`

## Purpose

This assessment integrates S01-S06 into a final foundation view before M031 closure. It records what is ready, what remains blocked or deferred, and what the next milestone should address.

This assessment is not a parser-completeness proof, legal correctness proof, retrieval-quality proof, R035 validation, R038 validation, graph-vector proof, production ETL proof, or pilot-readiness proof.

## Foundation inventory

| Slice | Output | Status | Ready for downstream use | Limitation |
| --- | --- | --- | --- | --- |
| `S01` | Prior-art assessment from `/root/law-parser`, source/dependency reuse map, corpus/spec evidence classification. | complete | Yes, as bounded prior-art and dependency baseline. | Prior art is not trusted implementation and not legal/parser completeness evidence. |
| `S02` | ConsultantPlus lifecycle workspace and CLI contract. | complete | Yes, as layout/schema/command contract. | Persistent lifecycle tracking policy is unresolved. |
| `S03` | Deterministic no-LLM CLI foundation: register, classify, process, status, run-batch, safe registry/processed outputs. | complete | Yes, for manifest-backed inventory-only source lifecycle work. | Inventory-only; no legal hierarchy parsing or legal meaning. |
| `S04` | Run envelopes, JSONL event/error logs, metrics, status summaries, and review packs. | complete | Yes, for temporary-workspace overnight-style run observability. | Persistent real-corpus runs should wait for tracking/ignore policy. |
| `S05` | Non-authoritative LLM/MiniMax/GPT-5.5/DSPy/RLM structural-hypothesis protocol with closed schemas. | complete | Yes, as protocol for future worker milestones. | No provider calls, no live worker behavior, no hypothesis validation. |
| `S06` | Deterministic no-LLM hypothesis verifier skeleton with accepted/rejected/needs_review decisions and review queue items. | complete | Yes, as executable skeleton for future structural-hypothesis proposals. | Safe-ref resolution is syntactic; no concrete artifact existence validation yet. |

## Ready items

- Manifest-driven ConsultantPlus WordML source lifecycle CLI.
- Safe SHA-addressed registry metadata and inventory-only processed outputs.
- Run envelopes, bounded JSONL events/errors, metrics, status, and review packs.
- Non-authoritative worker protocol with closed proposal and verifier schemas.
- Deterministic verifier skeleton with rejection taxonomy and needs_review queue.
- deterministic verifier skeleton is ready as a no-LLM executable acceptance gate for future structural-hypothesis proposals.
- Focused regression tests for CLI lifecycle, protocol markers, and verifier behavior.

## Blocked or unresolved items

- Lifecycle workspace tracking policy for `law-source/consultant/{inbox,raw,registry,processed,runs}` is unresolved.
- Persistent real-corpus overnight runs should not be performed in tracked source directories until that policy is decided.
- persistent real-corpus overnight runs should not be performed before the lifecycle workspace tracking policy is explicit.
- Verifier safe-ref checks are syntactic and do not yet check actual workspace/run artifact existence.
- No live MiniMax, GPT-5.5, DSPy, RLM, embedding, FalkorDB, or provider integration exists in M031.

## Deferred items

- Garant ODT source structuring remains deferred.
- Legal hierarchy parsing beyond inventory-only XML structure remains deferred.
- LLM/DSPy/RLM worker execution remains deferred until deterministic verifier and tracking policy are stronger.
- Product retrieval-quality and descriptor proof cycles remain paused until source foundation outputs are safe and reviewed.

## Non-claims

M031 S07 does not claim:

- legal correctness;
- parser completeness;
- product retrieval quality;
- ontology validation;
- graph-vector behavior;
- production ETL readiness;
- pilot readiness;
- LLM legal authority;
- R035 validation;
- R038 validation.

## Integrated focused verification

S07 T02 ran the integrated focused verification across the M031 source foundation implementation, protocol, and verifier tests.

Commands:

```bash
uv run pytest tests/test_source_cli_lifecycle.py tests/test_source_structuring_protocol.py tests/test_source_hypothesis_verifier.py -q
uv run ruff check scripts/source_lifecycle.py scripts/source_cli.py scripts/source_hypothesis_verifier.py tests/test_source_cli_lifecycle.py tests/test_source_structuring_protocol.py tests/test_source_hypothesis_verifier.py
uv run python -m py_compile scripts/source_lifecycle.py scripts/source_cli.py scripts/source_hypothesis_verifier.py tests/test_source_cli_lifecycle.py tests/test_source_structuring_protocol.py tests/test_source_hypothesis_verifier.py
```

Observed result:

```text
38 passed
All checks passed.
```

This is focused M031 verification only. It is not a broad project CI claim.

## Final bounded temp-workspace smoke

S07 T03 ran a final bounded smoke in a temporary workspace. It copied the two tracked ConsultantPlus XML fixtures into temporary batch input paths, then exercised:

```bash
uv run python scripts/source_cli.py --workspace <tmp>/workspace run-batch <tmp>/batch/batch.manifest.json
uv run python scripts/source_cli.py --workspace <tmp>/workspace review-pack <run_id>
uv run python scripts/source_cli.py --workspace <tmp>/workspace status
uv run python scripts/source_hypothesis_verifier.py <accepted.json> --output-dir <tmp>/verifier/accepted-out
uv run python scripts/source_hypothesis_verifier.py <needs_review.json> --output-dir <tmp>/verifier/needs-out
uv run python scripts/source_hypothesis_verifier.py <rejected.json> --output-dir <tmp>/verifier/rejected-out
```

Observed safe summary:

```json
{
  "run_status": "completed",
  "registered": 2,
  "processed": 2,
  "status_run_count": 1,
  "accepted": "accepted",
  "needs_review": "needs_review",
  "rejected": "rejected",
  "durable_file_count": 21
}
```

The rejected verifier smoke exited with code `1` as expected. The safety scan inspected temporary registry, processed, run, and verifier outputs and found no raw legal text examples, source fixture filename text, temporary absolute paths, repository absolute paths, provider secret names, secret-like prefixes, or provider payload markers.

## Recommendation

Recommended next milestone: **Lifecycle Workspace Tracking Policy and First Persistent Safe Corpus Run**.

Rationale:

- M031 now has enough deterministic source lifecycle machinery for a controlled run.
- The main blocker to a real persistent corpus run is not parser logic; it is workspace persistence policy for `law-source/consultant/{inbox,raw,registry,processed,runs}`.
- Resolving tracking policy first reduces the risk of accidentally staging raw source copies or bulky generated run artifacts.
- After that policy is explicit, the next milestone can run a persistent safe batch, verify generated safe artifacts, and decide whether to expand structural parsing or verifier artifact-existence checks.

Suggested next milestone slices:

1. Decide lifecycle output persistence policy: ignored local runtime workspace, tracked safe registry subset, or separate runtime path.
2. Add `.gitignore` or workspace redirection tests if a local runtime workspace is selected.
3. Run first persistent safe ConsultantPlus corpus batch under the selected policy.
4. Extend verifier safe-ref checks from syntactic validation to actual artifact existence checks.
5. Assess whether structural sample-pack extraction should be the next parser milestone.

Do not start provider-backed MiniMax/GPT-5.5/DSPy/RLM hypothesis work until the tracking policy and verifier artifact-existence checks are stronger.

## Final S07 proof status

S07 passes for foundation-assessment scope.

Evidence produced:

- S01-S06 source foundation inventory;
- integrated focused verification with `38 passed`;
- final temporary-workspace CLI and verifier smoke;
- explicit tracking-policy limitation;
- next-milestone recommendation;
- preserved R035 and R038 non-validation boundaries.

## Next-step placeholder

The likely next milestone should focus on one of these paths:

1. resolve lifecycle workspace tracking policy and run a persistent-but-safe initial ConsultantPlus corpus batch;
2. extend deterministic source parsing from inventory-only toward safe structural sample packs;
3. harden verifier safe-ref resolution against actual run/workspace artifacts;
4. only after those, consider a provider-backed structural-hypothesis milestone behind the S06 verifier.
