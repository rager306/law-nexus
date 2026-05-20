# M034 S04 — corrected Consultant XML parser foundation roadmap

## Status

- Milestone: `M034-mjdjn9 — Consultant XML Workline Recovery Audit`
- Slice: `S04 — Corrected XML Parser Foundation Roadmap`
- Roadmap status: `proposed-next-milestone`
- Proof level: contract
- Inputs: M034/S01 prior parser evidence audit, M034/S02 fixture taxonomy recheck, M034/S03 current-state drift audit, M009 parser proof package, M031 prior-art dependency assessment
- Non-validation boundaries: this roadmap does not validate R035, does not validate R037, and does not validate R038

## Purpose

This artifact turns the recovery audit into a corrected next-milestone plan. It does not implement parser changes. It defines how the next Consultant XML parser work should proceed without restarting from zero and without continuing from graph-context staging as if staging replaced parser hardening.

## Recovered baseline

The next parser milestone should start from this baseline:

```text
M009 is the current bounded Consultant XML hierarchy baseline.
```

Baseline facts to preserve:

- Canonical full-act fixture: `law-source/consultant/44-FZ-2026.xml`.
- Source role: `full-normative-act`.
- Current extractor: deterministic context-first Consultant WordML hierarchy extractor using stdlib `xml.etree.ElementTree.iterparse`.
- Current proof result: `2185` non-authoritative Consultant hierarchy records.
- Current stable ID family: `HIER-CONS-*`.
- Current prior-art comparison: bounded checks with one advisory invalidity-marker `needs-review` item.
- Current non-claims: no legal correctness, parser completeness beyond recorded artifacts, multi-document expansion, Garant parity, product ETL, FalkorDB loading, retrieval quality, R035/R037/R038 validation.

## Corrected next milestone proposal

Proposed title:

```text
Consultant XML Parser Hardening from M009 Baseline
```

Proposed vision:

```text
Harden the existing M009 Consultant WordML hierarchy parser with explicit equivalence checks, structural diagnostics, dependency decisions, and source-span/stable-ID proof while preserving non-authoritative legal boundaries and avoiding graph/runtime overclaiming.
```

## Proposed slices

### S01 — M009 baseline freshness and proof-package lock

**Goal:** Re-run and lock the current M009 parser proof package as the comparison oracle before any parser changes.

**Consumes:**

- `scripts/build-consultant-hierarchy-records.py`
- `scripts/compare-consultant-hierarchy-prior-art.py`
- `prd/parser/consultant_hierarchy_records.*`
- `prd/parser/consultant_parser_proof.*`
- `tests/test_consultant_parser_proof.py`

**Proof gate:**

- Current M009 proof commands pass.
- Artifact freshness is checked.
- Record counts, level counts, duplicate IDs, and non-authoritative flags are captured as baseline metrics.
- Advisory invalidity-marker drift remains advisory, not legal truth.

**Demo:** A reviewer can see the exact baseline that all later parser changes must preserve or explicitly explain.

### S02 — `lxml` equivalence and performance evaluation

**Goal:** Evaluate `lxml` as a first-class parser dependency candidate without silently replacing the M009 stdlib parser.

**Why:** Prior M031 dependency assessment already classified `lxml` as a positive MVP dependency candidate for memory-efficient WordML XML parsing. S04 should not weaken that decision, but adoption requires current-repo equivalence and performance proof.

**Allowed work:**

- Add an optional `lxml` prototype path or isolated comparator.
- Compare output against M009 stdlib records.
- Measure bounded parse/runtime characteristics.
- Record namespace/streaming behavior differences.

**Not allowed:**

- Replace stdlib parser output as canonical before equivalence proof passes.
- Claim parser completeness or legal correctness from parser-library substitution.

**Proof gate:**

- Same hierarchy record IDs and parent/level structure as M009, or every difference is classified as accepted/needs-review/blocked.
- Performance/memory observations are recorded as engineering evidence only.
- Existing tests pass.

**Demo:** A reviewer can decide whether `lxml` should replace, supplement, or be deferred, with concrete equivalence evidence.

### S03 — Structural rule hardening from prior art

**Goal:** Convert useful Old_project/law-parser structural prior art into deterministic current-repo tests and diagnostics.

**Candidate inputs:**

- `Old_project/structures/44fz.yaml`
- `Old_project/validation/structural_rules.yaml`
- `prd/parser/consultant_prior_art_inventory.md`
- `prd/parser/consultant_hierarchy_prior_art_comparison.*`

**Allowed work:**

- Add structural diagnostics for parentage, ordering, duplicate markers, orphan markers, and level transitions.
- Classify checks as blocking or advisory.
- Preserve source-span and stable-ID behavior.

**Not allowed:**

- Import old JSON/JSONL as authoritative parsed law.
- Treat prior-art structure YAML as runtime legal authority.

**Proof gate:**

- New diagnostics are deterministic.
- Tests cover both passing current baseline and at least one fail-closed synthetic fixture or fixture subset.
- No raw legal text dumps are added to durable artifacts.

**Demo:** A reviewer can see structural hardening checks that protect hierarchy integrity without overclaiming legal semantics.

### S04 — Semantic-rule downgrade into diagnostics

**Goal:** Review semantic/legal prior-art rules and downgrade only safe items into deterministic diagnostics, not legal truth.

**Candidate inputs:**

- `Old_project/validation/semantic_rules.yaml`
- `prd/research/source_structuring/22-old-project-transfer-decision-list.md`
- Advisory invalidity-marker finding from M009.

**Allowed work:**

- Convert selected semantic rules into non-authoritative warning categories.
- Keep diagnostics source-span/citation-safe.
- Preserve advisory classification when legal-domain judgment would be required.

**Not allowed:**

- Emit legal-effect conclusions.
- Validate legal correctness.
- Resolve invalidity or amendment effects without domain/legal review and source-span proof.

**Proof gate:**

- Each diagnostic has a reason code and source anchor/hash.
- Tests prove warnings do not become accepted legal facts.
- M009 advisory invalidity-marker check remains bounded unless a separate proof resolves it.

**Demo:** A reviewer can inspect semantic-adjacent diagnostics without mistaking them for legal interpretation.

### S05 — `razdel` and `pymorphy3` diagnostic evaluation

**Goal:** Evaluate Russian tokenization and morphology only where a concrete parser diagnostic benefits from them.

**Prior decision:** M031 classified `razdel` and `pymorphy3` as soon-after-MVP candidates, not rejected dependencies.

**Candidate uses:**

- marker-family normalization;
- invalidity-marker diagnostics;
- sentence segmentation for bounded excerpts;
- less brittle structural warning rules.

**Not allowed:**

- Add NLP dependencies to parser core without a concrete test-backed diagnostic.
- Use NLP output as legal truth.
- Replace context-first hierarchy parsing with token-only matching.

**Proof gate:**

- A concrete diagnostic is named before dependency adoption.
- Tests compare behavior with and without the dependency where possible.
- Startup/runtime impact is recorded.
- If morphology dictionaries are required, version pinning and smoke evidence are documented.

**Demo:** A reviewer can decide whether tokenization/morphology materially improves parser diagnostics.

### S06 — Source-span, parent-path, and stable-ID hardening

**Goal:** Strengthen parser output observability and downstream safety surfaces without changing legal authority boundaries.

**Allowed work:**

- Verify every hierarchy record has stable source hash, excerpt hash, parent reference, level, marker metadata, and deterministic order.
- Add parent-path or ancestry diagnostics if needed.
- Add clearer failure reasons for context-rejected markers.

**Proof gate:**

- JSON Schema and JSONL validation pass.
- Tests cover parentage/order and fail-closed diagnostic behavior.
- No raw full legal text is written to durable outputs.

**Demo:** Future agents can debug parser changes without reading raw sources or guessing why a marker was rejected.

### S07 — Final parser hardening proof package

**Goal:** Assemble the hardened Consultant XML parser proof into a cold-reader package.

**Proof gate:**

- Fixture inventory check passes.
- Parser record validation passes.
- Hierarchy record generation/check passes.
- Prior-art comparison passes or preserves bounded needs-review diagnostics.
- New diagnostics and dependency decisions are summarized.
- Non-claims are repeated and test-enforced.

**Demo:** A reviewer can evaluate what changed since M009, what stayed equivalent, what is still advisory, and what remains out of scope.

## Dependency adoption boundaries

| Dependency / artifact | Corrected status | Proof required before adoption |
|---|---|---|
| M009 stdlib parser | Current comparison oracle | Keep until a replacement proves equivalence or explicitly accepted drift. |
| `lxml` | Positive first-class candidate for explicit evaluation | Equivalence/performance proof against M009 output. |
| `razdel` | Soon-after-MVP diagnostic candidate | Concrete marker/segmentation diagnostic and tests. |
| `pymorphy3` + dictionaries | Soon-after-MVP morphology candidate | Concrete normalization/diagnostic need, pinned dictionaries, smoke tests. |
| `pydantic` | Already adopted parser-record boundary | Continue using strict schema/JSONL validation. |
| `pyyaml` | Accepted for config/spec loading | YAML-driven behavior remains test-gated and non-authoritative. |
| `semantic_rules.yaml` | Adapt into diagnostics only | Reason-coded warnings with source anchors; no legal truth. |
| `structural_rules.yaml` | Adapt into deterministic checks | Blocking/advisory classification plus tests. |
| M031 source lifecycle CLI | Supporting infrastructure | Use around parser runs, not as parser proof. |
| M032 discovery pipeline | Supporting candidate discovery | Deterministic verifier remains acceptance gate; no parser authority. |
| M033 graph-context staging | Later staging layer | Consume parser records only after parser proof is clear; no R037 claim. |

## Explicit exclusions from the next parser-hardening milestone

The corrected next milestone should not include:

- FalkorDB ingestion or graph load/query proof;
- graph-vector index/query behavior;
- R037 validation;
- R035 ontology/product architecture validation;
- R038 independent external review validation;
- legal-answer generation;
- citation-safe retrieval quality validation;
- production ETL readiness;
- multi-source Consultant/Garant parity;
- importing Old_project parsed outputs as authoritative data;
- using MiniMax/GPT-5.5/DSPy/RLM as parser authority.

## Suggested verification contract for the next milestone

Minimum final verification should include:

```bash
uv run python scripts/inventory-parser-fixtures.py --check
uv run python scripts/validate-parser-records.py --check
uv run python scripts/build-consultant-hierarchy-records.py --check
uv run python scripts/compare-consultant-hierarchy-prior-art.py --check
uv run pytest tests/test_parser_fixture_inventory.py tests/test_consultant_prior_art_inventory.py tests/test_consultant_hierarchy_records.py tests/test_consultant_hierarchy_prior_art_comparison.py tests/test_consultant_parser_proof.py -q
```

Additional checks should be added for any new `lxml`, structural-rule, semantic-diagnostic, `razdel`, or `pymorphy3` work.

## M034 recovery conclusion

The corrected project direction is:

```text
Do not restart Consultant XML parsing from zero.
Do not continue graph-context staging as parser foundation.
Return to M009 as the bounded parser baseline and harden it through explicit proof gates.
```

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

### T03 compile command

Command:

```bash
uv run python -m py_compile scripts/build-consultant-hierarchy-records.py scripts/compare-consultant-hierarchy-prior-art.py
```

Observed result:

- Exit code: `0`
- Result: compile check passed with no output.

### T04 final focused test command

Command:

```bash
uv run pytest tests/test_parser_fixture_inventory.py tests/test_consultant_prior_art_inventory.py tests/test_consultant_parser_proof.py -q
```

Observed result:

- Exit code: `0`
- Result: `14 passed`

## Explicit non-claims

This roadmap does not claim:

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

The next productive milestone should be a proof-gated Consultant XML parser-hardening milestone from M009, with `lxml`, structural rules, semantic diagnostics, and NLP dependencies evaluated only through explicit deterministic tests and bounded artifacts.
