---
id: T002
title: Clear the long-tail stale claims, re-pin m221, regenerate GitNexus
wave: 1
deps: []
status: pending
agent: null
base: null
worktree: null
task_branch: null
files:
  - README.md
  - AGENTS.md
  - prd/ARCHITECTURE.md
  - doc/adr/README.md
  - doc/adr-architecture-cross-matrix.md
  - prd/architecture/m221-s05-docs-reconciliation.yaml
  - law-source/consultant/README.md
  - docs/agent-stack/PHASE-ADAPTER.md
  - product-model/interfaces/terminal/interface.md
---

# T002 — Clear the long-tail stale claims, re-pin m221, regenerate GitNexus

## Context

Twenty stale claims remain after the projection fix: ARCHITECTURE parser counts and the one-page oracle budget (#25, #26), the ADR index table header (#27) and cross-matrix inventory through ADR-0031 (#28), the m221 hash-pinned binding that no longer matches the tracked contract file and fails `tests/test_m221_authority_reconciliation.py` (#29), the legacy-ledger line and transition preamble in roadmap.md (#30, #37), law-source README wording about gitignored `.deprecated/` (#31), the PHASE-ADAPTER header lagging its section 9 (#36), interface.md saying "four subcommands" (#44), README status band/assessments/ADR range (#45, #46, #49), AGENTS.md DB count and fixture counts (#47, #48), and the GitNexus tool block pinned at M001 numbers (#50, fix-code). Rulings recorded in DOCS-AUDIT.md `## User rulings` (#25-#31, #36-#37, #44-#50).

## Approach

- Per row, refresh the claim to the measured current value at HEAD with file:line evidence (N3: no raised lifecycle tags, no corpus-parity language); #26 trims the oracle to the 325-line budget instead of raising it; #29 re-pins `m221-s05-docs-reconciliation.yaml` to the sha256 of the tracked `prd/architecture/npa-analysis-jsonl-contract.md` at HEAD (E3: any mismatch must fail the suite, never be weakened); #30 date-bounds the M173 line as frozen legacy-ledger text; #37 rewrites the transition preamble for the post-bootstrap reality.
- #50: run `node .gitnexus/run.cjs analyze --force --name law-nexus` on the primary checkout and replace only the delimited GitNexus block in AGENTS.md with the numbers from that run's meta.json (E5: block span exact, markers preserved); keep the local-exclusion note.
- Touch only the declared files plus the regenerate output the tool writes locally (the index itself stays local-excluded and untracked).

## Interface contract

None

## Intent coverage

- SC3
- SC4
- SC5

## Acceptance criteria

1. Every refreshed claim (#25-#28, #30-#31, #36-#37, #44-#49) matches the live tree at HEAD with file:line evidence: parser counts or their removal, oracle at most 325 lines, ADR index table renders, cross-matrix through ADR-0031, date-bound legacy line, checkout wording, PHASE-ADAPTER header aligned with section 9, five subcommands in interface.md, README band/assessments/ADR range, AGENTS.md DB count (3,074 of 8,355) and 82 tracked fixtures.
2. `prd/architecture/m221-s05-docs-reconciliation.yaml` pins the tracked `prd/architecture/npa-analysis-jsonl-contract.md` digest at HEAD and `uv run --frozen pytest tests/test_m221_authority_reconciliation.py -q` passes.
3. The AGENTS.md GitNexus block carries the fresh analyze run's meta.json numbers with the block markers and the local-exclusion note intact, and no file outside the declared scope changed.

## Verify

```bash
grep -q 'npa-analysis-jsonl-contract.md' prd/architecture/m221-s05-docs-reconciliation.yaml && uv run --frozen pytest tests/test_m221_authority_reconciliation.py tests/test_repository_quality_gate.py -q
```

Heavy: no

## Log

- 2026-10-31 — created by orchestrator (quick mode, rows #25-#31, #36-#37, #44-#50)
