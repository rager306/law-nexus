---
id: T002
title: Clear the long-tail stale claims, re-pin m221, regenerate GitNexus
wave: 1
deps:
  - T001
status: done
agent: build_T002
base: 0d30fd13c801d1f831b7c6ea139d3118d2dac406
worktree: null
task_branch: null
files:
  - prd/project-state/roadmap.md
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
- 2026-10-31 — attempt 1 (resumed after the prior coder session died mid-task): inherited doc edits for #25-#28, #31, #36, #44-#49 and the #29 re-pin were present in the worktree; reviewed every inherited diff against the acceptance criteria and DOCS-AUDIT rulings; verified against the live tree: #25 counts exact (31 src modules + 14 bins, 358 int / 54 unit), #26 321 <= 325 lines, #27 table header restored, #28 cross-matrix through ADR-0031 with referenced artifacts checked, #29 binding sha256 equals the tracked contract file, #31 82 fixtures / .deprecated absent, #36 header aligned with section 9 (dispatch archives 001/002/003 measured), #44 five subcommands, #45-#49 band/assessments/ADR range/DB count 3,074 of 8,355/fixtures; #50 fresh analyze via alias law-nexus-t002 (--index-only, registry collision forced the alias): nodes=43375 edges=102959 processes=584, block updated, markers byte-identical, alias deregistered. Verify: 22 passed, exit 0.
- 2026-10-31 — NEEDS-ORCHESTRATOR logged: rows #30/#37 target prd/project-state/roadmap.md (sibling T001's declared file); readings (a) T001 absorbs, (b) authorize T002 after T001 lands, (c) defer out of SC3.
- 2026-10-31 — Orchestrator answer: the approved artifacts conflict — PLAN coverage SC3 -> T002/AC1 pins rows #30/#37 to this task while its declared files omitted roadmap.md. That is a documented plan defect (content ownership without file scope), so reading (b) is taken through the sanctioned repair: this task's `files` gains prd/project-state/roadmap.md and `deps` gains T001 (same-wave file sharing through an explicit dependency per PLAN gate rules); rows #30/#37 stay here. — citation: PLAN.md Intent coverage SC3 row; INTENT.md SC3; PLAN gate file-sharing rule. Structural repair executed through build recovery (build plan repair requested).
- 2026-10-31 — attempt-1 work preserved before isolate retirement: full diff sha256 c0bf5f06ac87636420935f1ac14b3568d9a6bbb2ec407e97be7355e33beb8aa9 at /tmp/t002-attempt1.patch (283 lines; paths: this task file, AGENTS.md, README.md, doc/adr/README.md, doc/adr-architecture-cross-matrix.md, docs/agent-stack/PHASE-ADAPTER.md, law-source/consultant/README.md, prd/ARCHITECTURE.md, prd/architecture/m221-s05-docs-reconciliation.yaml, product-model/interfaces/terminal/interface.md).
- 2026-11-01 — sanctioned retry at base `0d30fd13` (roadmap.md now owned): applied `/tmp/t002-attempt1.patch` (sha256 c0bf5f06…, `git apply --exclude='.project/tasks/*'`, clean); re-verified every applied row at this HEAD: #25 counts re-measured live (31 src modules incl. lib.rs + 14 `src/bin/` entrypoints, 358 integration / 54 unit `#[test]`), #26 oracle 321 ≤ 325 lines (content-preserving re-wrap; tracked budget untouched), #27 ADR index header/separator restored, #28 inventory+matrix through ADR-0031 (P0 note keeps the dated 2026-08-11 statement), #29 pinned sha256 `a3f51100…` equals a fresh hash of the tracked `npa-analysis-jsonl-contract.md`, #31 reworded (`.deprecated` gitignored, absent in fresh checkout), #36 header aligned with §9 (PARTIALLY, pilot 2026-10-25; dispatch records present in archives 001/002/003: 21/9/4 files), #44 five subcommands, #45 README band → roadmap.json through M224 + M011 note, #46 assessments 00–34 + `assessment/34`, #47 frozen-DB 3,074 of 8,355, #48 82 tracked fixtures, #49 ADR range 0004–0031.
- 2026-11-01 — net-new #30/#37 in `prd/project-state/roadmap.md`: #37 transition preamble rewritten for post-bootstrap reality (bootstrap PR #1 merged at `54a495cd` 2026-10-25 — commit subject/date re-verified; native Path state under `.project/`; native markers below record the Path-track shipments; legacy GSD-Pi M-IDs kept as history; LEGACY_CROSSWALK pointer and the `workflow_state.py` freshness adapter kept). #30 M173 line date-bound as frozen legacy-ledger text (2026-10-23 GSD-Pi ledger freeze), live product front named: `prd/project-state/data/roadmap.json` `completed_milestone_groups` through M224-M224, generated 2026-10-24 (re-read from the file).
- 2026-11-01 — net-new #50: `node .gitnexus/run.cjs analyze --force --name law-nexus` on the primary checkout, no alias, exit 0 in 246.2s; meta.json: lastCommit `0d30fd13`, indexedAt 2026-11-01T09:04:26Z, branch `gsd-path/M012`, stats nodes=43376 edges=102960 processes=584. AGENTS.md delimited block updated to exactly these numbers; diff vs HEAD is the single numbers line — markers and all other block prose byte-identical. Provenance note for the reviewer: the tracked block never carried a textual local-exclusion note (`git log -S 'local-excluded' -- AGENTS.md` over all commits: none; attempt-1 patch added none either), so the "byte-identical" mandate resolves to not touching anything but the numbers; the exclusion itself is `.gitnexus/` in `.git/info/exclude`, still in place.
- 2026-11-01 — N2 checked: `git status --porcelain` after the analyze run shows only this task file plus the ten declared files; `.claude/skills/gitnexus/*` touched by the runner is untracked. Verify: `grep -q 'npa-analysis-jsonl-contract.md' prd/architecture/m221-s05-docs-reconciliation.yaml && uv run --frozen pytest tests/test_m221_authority_reconciliation.py tests/test_repository_quality_gate.py -q` → 22 passed, exit 0.
- 2026-11-01 — orchestrator Verify (sidecar gsd-path-verify/task-t002-verify): pass, exit 0; output tail:
  ```
  ......................                                                   [100%]
  22 passed in 1.88s
  Using CPython 3.13.12 interpreter at: /root/.local/bin/python3.13
  Creating virtual environment at: .venv
     Building law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
        Built law-nexus @ file:///root/.allspark-home/.gsd-path/projects/b5ec5063eb548c9b143d844782944712ed19c26fd411d5c13ea0b40918388103/af6be3685b34e6bb6b9e3059f81aea526927728903829da8c0909b6afa25f01a/verify/task-t002-verify
  Installed 32 packages in 1.46s
  ```
