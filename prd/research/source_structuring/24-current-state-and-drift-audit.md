# M034 S03 — current state and drift audit

## Status

- Milestone: `M034-mjdjn9 — Consultant XML Workline Recovery Audit`
- Slice: `S03 — Current State and Drift Audit`
- Audit status: `draft-ledger`
- Proof level: contract
- Inputs: M034/S01 prior parser evidence audit, M034/S02 fixture taxonomy recheck, M006/M009/M031/M032/M033 summaries, parser proof artifacts
- Non-validation boundaries: this audit does not validate R035, does not validate R037, and does not validate R038

## Purpose

This ledger classifies the current project state by proof layer so the next roadmap does not continue from the wrong abstraction. It answers:

1. Which existing artifacts are source-shape proof?
2. Which are real Consultant XML parser proof?
3. Which are parser-record/staging, lifecycle, discovery, or graph-context staging layers?
4. Where did the workline drift away from the intended Consultant XML parser foundation continuation?

## Prior context recovery path

The recovery order used for S03 was:

1. Memory for fast recall of M009 source-role taxonomy and non-claims.
2. GSD summaries for M006, M009, M031, M032, and M033.
3. Current durable project artifacts under `prd/parser/` and `prd/research/source_structuring/`.

This follows the project rule: do not invent new classifications before recovering prior decisions, logs/summaries, and durable GSD files.

## Current proof-layer ledger

| Layer | Primary artifacts | What is proven | What is not proven | Correct downstream use |
|---|---|---|---|---|
| Source-shape proof | `prd/parser/source_fixture_inventory.json`, `prd/parser/source_fixture_inventory.md`, `prd/parser/README.md`, M034/S02 artifact | Canonical fixture paths, source roles, hashes, shape diagnostics, duplicate absence, non-authoritative boundaries. | Legal correctness, extracted hierarchy correctness, parser completeness, multi-source readiness. | S04 should consume this as the source-role contract and avoid raw source globbing. |
| Parser-record and staging proof | M006 summary, `scripts/parser_records.py`, `scripts/validate-parser-records.py`, ODT smoke records, Consultant relation candidates, NetworkX staging graph artifacts | Strict parser-record boundary, bounded ODT smoke records, candidate-only Consultant relation evidence, staging graph invariants. | Full Consultant hierarchy extraction, endpoint relation correctness, FalkorDB runtime load/query, legal-answer correctness. | Reuse record schemas and staging boundaries; do not treat M006 as full Consultant parser proof. |
| Consultant XML parser proof | M009 summary, `scripts/build-consultant-hierarchy-records.py`, `prd/parser/consultant_hierarchy_records.*`, `prd/parser/consultant_parser_proof.*`, `tests/test_consultant_parser_proof.py` | Deterministic context-first Consultant WordML hierarchy extraction for the canonical 44-FZ tracer; 2185 non-authoritative records; stable IDs; bounded prior-art comparison. | Legal correctness, parser completeness beyond recorded artifacts, multi-document expansion, Garant parity, product ETL, FalkorDB loading, retrieval quality. | This is the current bounded Consultant XML hierarchy baseline. S04 should plan hardening from here, not from zero. |
| Prior-art dependency and library assessment | `prd/research/source_structuring/01-law-parser-prior-art-assessment.md`, M034/S01, M034 transfer decision list | Old law-parser/Old_project ideas are classified for reuse; `lxml` is a positive MVP dependency candidate; `razdel` and `pymorphy3` are soon-after-MVP candidates; Old_project remains prior art only. | No legacy implementation or parsed output is trusted as legal truth. Library adoption still needs current-repo tests/proofs. | S04 can plan explicit evaluation slices, especially `lxml` equivalence/performance, without silently replacing M009. |
| Source lifecycle foundation | M031 summary and `prd/research/source_structuring/03` through `07` artifacts; `scripts/source_cli.py`, `scripts/source_lifecycle.py`, verifier skeleton | Safe deterministic source lifecycle CLI, run/review artifacts, non-authoritative worker protocol, deterministic verifier skeleton. | Parser completeness, legal correctness, product/retrieval quality, graph-vector behavior, production readiness. | Useful orchestration around source runs; not a substitute for M009 parser foundation. |
| MiniMax-assisted discovery | M032 summary and `prd/research/source_structuring/08` through `14` artifacts | Bounded provider-assisted source discovery with trajectory logs, candidate normalization, verifier integration, external review pack generation. MiniMax remains non-authoritative. | Independent external review completion, R038 validation, parser proof, legal truth, retrieval quality. | Candidate discovery may feed future reviewed hypotheses only after deterministic verification. |
| Graph-context staging | M033 summary and `prd/research/source_structuring/15` through `20` artifacts; graph-context staging functions/tests | Accepted verified candidates can be staged into deterministic graph-context rows; weak signals, rejected, and needs_review branches are visible; runtime output ignore policy exists. | FalkorDB ingestion, graph load/query proof, vector behavior, R037 validation, R035 validation, parser extraction proof. | Later layer. It should consume parser records only after parser path is clarified; it should not define the parser roadmap. |
| Old_project/law-parser prior art | `Old_project/**`, `/root/law-parser` references captured by inventories/research | Useful hypotheses, vocabulary, comparison anchors, and dependency history. | Trusted implementation, authoritative parsed legal data, current source truth. | Adapt through current tests only; never import old outputs as truth. |

## Drift diagnosis

The drift point is not that Consultant XML parser work was absent. The drift point is that after M009 proved the bounded Consultant full-act hierarchy baseline, subsequent work continued into source lifecycle, discovery, and graph-context staging layers while losing the M009 parser-hardening path as the active reference.

Correct chain:

```text
M006 parser-record/staging proof
→ M009 Consultant full-act WordML hierarchy parser proof
→ M031 source lifecycle CLI foundation
→ M032 MiniMax-assisted source discovery and verifier integration
→ M033 graph-context staging from verified candidates
```

Incorrect continuation to avoid:

```text
M031/M032/M033 staging layers
→ treated as if they are the Consultant XML parser foundation
→ roadmap jumps toward graph runtime or product ontology before parser hardening is reconciled
```

Correct continuation:

```text
M009 parser baseline
→ fixture taxonomy rechecked by S02
→ current-state drift ledger in S03
→ corrected M034/S04 roadmap for Consultant XML parser hardening
```

## Current-state findings

### M006

M006 is real and valuable, but it is a parser-record and staging milestone. Its strongest reusable pieces are:

- manifest-first fixture selection;
- strict Pydantic v2 parser-record boundary;
- JSONL validation diagnostics;
- bounded ODT smoke records;
- candidate-only Consultant relation evidence;
- NetworkX staging graph invariants and non-claims.

M006 does not prove full Consultant hierarchy extraction.

### M009

M009 is the current bounded Consultant XML hierarchy baseline. It produced:

- deterministic context-first Consultant WordML hierarchy extraction;
- `2185` non-authoritative hierarchy records;
- stable `HIER-CONS-*` IDs;
- bounded prior-art comparison;
- explicit Consultant-primary and Garant-deferred boundary.

The advisory invalidity-marker mismatch remains `needs-review` and must not be converted into legal truth.

### M031

M031 created source lifecycle infrastructure around Consultant XML work:

- register/classify/process/status/run-batch/review-pack CLI behavior;
- safe run artifacts;
- non-authoritative MiniMax/GPT-5.5/DSPy/RLM protocol;
- deterministic verifier skeleton.

M031 does not supersede M009 parser proof.

### M032

M032 added bounded MiniMax-assisted source discovery:

- runtime workspace policy;
- trajectory logs;
- discovery command;
- candidate normalization;
- verifier integration;
- external review pack output.

M032 validates bounded CLI/reviewability capability only. It does not validate R035 or R038 and does not prove parser correctness.

### M033

M033 added graph-context staging readiness:

- staging schema;
- export from accepted verifier decisions;
- weak-signal hardening;
- accepted/rejected/needs_review branch evidence;
- runtime ignore policy.

M033 is not FalkorDB ingestion. It does not validate R037, R035, or R038.

## Working-tree and artifact scope

Current expected uncommitted audit artifacts:

```text
prd/research/source_structuring/21-prior-parser-evidence-audit.md
prd/research/source_structuring/22-old-project-transfer-decision-list.md
prd/research/source_structuring/23-consultant-xml-fixture-taxonomy-recheck.md
prd/research/source_structuring/24-current-state-and-drift-audit.md
```

These are audit/research artifacts, not parser implementation changes. GitNexus may report no changed symbols for this stage because the active changes are Markdown artifacts outside code symbol extraction.

## S04 constraints derived from this ledger

S04 should produce a corrected next milestone that starts from M009 and includes proof gates such as:

1. M009 baseline freshness and proof-package check.
2. `lxml` equivalence/performance evaluation against M009 stdlib output, not silent replacement.
3. Structural rule hardening from Old_project/law-parser prior art through deterministic current-repo tests.
4. Semantic-rule downgrade only into diagnostics, not legal truth.
5. `razdel`/`pymorphy3` evaluation only for marker diagnostics or normalized structural checks after a concrete need is named.
6. Source-span, parent-path, stable-ID, and failure-diagnostic hardening.
7. Final proof package update that preserves R035/R037/R038 non-validation boundaries.

S04 should not plan FalkorDB ingestion, graph-vector work, product ontology readiness, independent external GPT-5.5 review completion, or legal-answer behavior as part of the immediate Consultant XML parser foundation correction.

## Verification evidence

### T01 baseline command

Command:

```bash
uv run pytest tests/test_consultant_parser_proof.py -q
```

Observed result:

- Exit code: `0`
- Result: `5 passed`

### T02 fixture command

Command:

```bash
uv run python scripts/inventory-parser-fixtures.py --check
```

Observed result:

- Exit code: `0`
- Status: `pass`
- Fixture count: `4`
- Duplicate absent: `true`
- Non-authoritative: `true`
- Unexpected duplicate paths: `[]`

### T03 working-tree command

Command:

```bash
git status --short
```

Observed result:

```text
?? prd/research/source_structuring/21-prior-parser-evidence-audit.md
?? prd/research/source_structuring/22-old-project-transfer-decision-list.md
?? prd/research/source_structuring/23-consultant-xml-fixture-taxonomy-recheck.md
?? prd/research/source_structuring/24-current-state-and-drift-audit.md
```

### T03 GitNexus scope check

Command:

```text
gitnexus_detect_changes({repo: "law-nexus", scope: "all"})
```

Observed result:

- Changed symbols: `0`
- Affected processes: `0`
- Risk level: `none`
- Message: `No changes detected.`

### T04 final focused test command

Command:

```bash
uv run pytest tests/test_parser_fixture_inventory.py tests/test_consultant_prior_art_inventory.py tests/test_consultant_parser_proof.py -q
```

Observed result:

- Exit code: `0`
- Result: `14 passed`

## Explicit non-claims

This S03 drift audit does not claim:

- parser completeness;
- legal correctness;
- authoritative legal interpretation;
- Consultant legal authority;
- Garant parity;
- multi-source parser readiness;
- product ETL readiness;
- FalkorDB loading/runtime readiness;
- graph-vector behavior;
- retrieval quality;
- citation-safe answer readiness;
- independent external GPT-5.5 review completion;
- R035 validation;
- R037 validation;
- R038 validation.

## Conclusion

The current state is recoverable and the drift is bounded:

```text
M009 is the parser baseline.
M031-M033 are useful upper layers.
The error to avoid is continuing upper-layer staging as if it replaced parser hardening.
```

S04 should therefore create a corrected Consultant XML parser-hardening roadmap that consumes M009 as the baseline and uses M031-M033 only as supporting lifecycle/discovery/staging infrastructure.
