# M034 S01 — prior parser evidence audit

## Status

- Milestone: `M034-mjdjn9 — Consultant XML Workline Recovery Audit`
- Slice: `S01 — Prior Parser Evidence Audit`
- Audit status: `t01_inventory`
- Scope: Consultant XML workline recovery from prior parser evidence through current state
- Non-validation boundaries: this audit does not validate R035, does not validate R037, and does not validate R038

## Purpose

This audit reconstructs the prior parser evidence chain so future work returns to the real Consultant XML parser foundation path instead of treating later source-lifecycle, discovery, or graph-context staging layers as a substitute for parser proof.

The key correction is that M009 already contains a bounded Consultant Plus full-act WordML hierarchy parser proof. The recovery question is therefore not "start Consultant XML parsing from zero", but: what exactly did M009 prove, what remains only prior art or staging, and where did M031-M033 drift away from the parser-foundation path?

## Prior parser evidence inventory

Marker: prior parser evidence inventory.

### Old_project and law-parser prior art

| Evidence area | Representative artifact | Role in this audit | Current trust level |
|---|---|---|---|
| Local prior-art mirror | `Old_project/sources/consultant_word2003xml.yaml` | Source-format hypothesis for Consultant Word 2003 XML. Namespaces and extraction rules are useful as observations. | Prior art only; not trusted implementation. |
| M009 prior-art inventory | `prd/parser/consultant_prior_art_inventory.md` | Maintained audit of 28 law-parser assets with classifications and hash checks. | Trusted as M009 audit evidence, not as legal truth. |
| Full tracked source fixture | `law-source/consultant/44-FZ-2026.xml` | Canonical full normative-act Consultant WordML fixture and source-shape/hash anchor. | Keep as source-shape fixture only. |
| Prior parser outputs | law-parser structure JSON / articles JSONL referenced by `consultant_prior_art_inventory.md` | Comparison baseline and record-shape hypotheses. | Adapt only after deterministic re-derivation in this repo. |
| Semantic/rule YAML prior art | law-parser semantic and structural rule YAML referenced by inventory | Hypotheses for future deterministic rules. | Structural rules adapt with tests; semantic rules defer. |

### M006 parser staging evidence

M006 proved a deterministic multi-document parser staging workflow over canonical fixtures, not full Consultant XML hierarchy parsing.

Key evidence:

- `scripts/inventory-parser-fixtures.py`
- `scripts/parser_records.py`
- `scripts/build-odt-smoke-records.py`
- `scripts/build-consultant-relation-candidates.py`
- `scripts/build-parser-staging-graph.py`
- `prd/parser/source_fixture_inventory.json`
- `prd/parser/consultant_relation_candidates.jsonl`
- `prd/parser/parser_staging_graph.json`
- tests under `tests/test_parser_fixture_inventory.py`, `tests/test_consultant_relation_candidates.py`, and `tests/test_parser_staging_graph.py`

M006 role: parser-record and staging proof. It established fixture inventory, typed parser-record contracts, ODT smoke records, Consultant document-list relation candidate evidence, and NetworkX staging graph invariants.

M006 limitation: it did not prove full Consultant XML structural hierarchy extraction from `44-FZ-2026.xml`.

### M009 Consultant full-act parser evidence

M009 is the main existing Consultant XML parser proof.

Key evidence:

- `scripts/build-consultant-hierarchy-records.py`
- `scripts/build-consultant-prior-art-expectations.py`
- `scripts/compare-consultant-hierarchy-prior-art.py`
- `prd/parser/consultant_hierarchy_records.jsonl`
- `prd/parser/consultant_hierarchy_records.json`
- `prd/parser/consultant_hierarchy_records.md`
- `prd/parser/consultant_hierarchy_prior_art_comparison.json`
- `prd/parser/consultant_parser_proof.md`
- `tests/test_consultant_hierarchy_records.py`
- `tests/test_consultant_prior_art_inventory.py`
- `tests/test_consultant_parser_proof.py`

M009 role: deterministic context-first Consultant WordML hierarchy extractor for the canonical full-act fixture.

Bounded result recorded by M009 proof:

- `2185` Consultant hierarchy records;
- `94` article records;
- `8` chapter records;
- `9` section records;
- `793` part records;
- `997` clause records;
- `283` subclause records;
- stable `HIER-CONS-*` IDs;
- `0` duplicate IDs;
- `0` non-authoritative false count;
- prior-art comparison status `needs-review` because one advisory invalidity-marker check remains unresolved.

M009 limitation: this proves bounded deterministic hierarchy extraction for the 44-FZ tracer only. It does not claim legal correctness, parser completeness beyond recorded artifacts, multi-document expansion, product ETL readiness, FalkorDB load readiness, retrieval quality, or Consultant legal authority.

### M031-M033 later source lifecycle and graph-context work

M031-M033 are later layers and must not be mistaken for base parser proof.

| Milestone | Evidence type | Relationship to Consultant XML parser foundation |
|---|---|---|
| M031 | Source lifecycle CLI foundation: register/classify/process/status/run-batch, review pack, verifier skeleton | Useful operational layer around sources; not a replacement for M009 parser proof. |
| M032 | MiniMax-assisted source discovery, candidate normalization, verifier integration, external review pack | Candidate discovery layer; LLM is non-authoritative and deterministic verifier gates adoption. Not parser foundation. |
| M033 | Graph-context staging from verified candidates, branch hardening, runtime ignore policy | Upper staging layer for later graph runtime planning. Useful later, but this is where work drifted away from Consultant XML parser foundation if treated as the next parser step. |

## Reuse classification

| Class | Artifacts | Reason | Downstream owner |
|---|---|---|---|
| `keep` | `law-source/consultant/44-FZ-2026.xml` only as canonical full-act source fixture; tracked M009 parser proof artifacts as evidence surfaces | The source fixture is tracked and hash-anchored; M009 proof artifacts are generated/verified inside this repo. Keep does not mean legal truth or parser completeness. | S02 fixture taxonomy recheck and future Consultant XML parser-foundation milestone. |
| `evidence-only` | M006 summaries, M009 summaries, `prd/parser/consultant_parser_proof.md`, `prd/parser/source_fixture_inventory.md`, `prd/parser/consultant_prior_art_inventory.md` | These explain what was proven and what remains bounded. They are audit inputs, not implementation code to copy blindly. | M034 S03 current-state ledger. |
| `adapt` | `Old_project/sources/consultant_word2003xml.yaml`; law-parser structure/record-shape/rule ideas captured in `consultant_prior_art_inventory.md`; `scripts/build-consultant-hierarchy-records.py` patterns if future parser work needs refactoring | Useful source-format observations and deterministic parser patterns exist, but any reuse must be reverified through current tests and source fixtures. | Future Consultant XML structural parser foundation milestone. |
| `defer` | Semantic rules, archived prompt/spec files, multi-source/Garant parity assumptions, retrieval/product implications | These require later deterministic parser records, citation-safe evidence, or product/runtime proof before use. | Later parser-quality, retrieval, or product milestones. |
| `reject` | Failed-experiment prior-art paths and any assumption that imports prior parser JSON/JSONL as authoritative legal data | Failed or unverified assumptions must remain warnings. Prior parser outputs may inform comparisons but cannot become canonical parsed law. | Audit and future parser review gates. |

No Old_project artifact is trusted implementation. Old_project and law-parser prior-art files may supply hypotheses, vocabulary, or comparison anchors only after current-repo deterministic checks rederive the evidence from tracked sources.

### Reuse implications

- The full-act fixture can be kept as a source-shape/hash anchor, not as parsed legal semantics.
- M009 parser code and proof can be reused as the current best bounded Consultant XML hierarchy baseline, but future changes still require impact analysis, tests, and artifact freshness checks.
- M031-M033 lifecycle/discovery/staging code can be reused around parser outputs only after S03 confirms which outputs are parser records versus candidate/staging records.
- No prior-art semantic rule may be promoted into legal-answer behavior without later source-span/citation-safe proof.

## Initial correction

The current evidence chain is:

```text
M006 fixture/parser-record/staging proof
→ M009 Consultant full-act WordML hierarchy parser proof
→ M031/M032 source lifecycle and candidate discovery
→ M033 graph-context staging
```

The drift was not that Consultant XML parser work never existed. The drift was treating M031-M033 as the active continuation while losing the already-proven M009 parser baseline and the remaining parser-foundation gaps.

## Boundary table

| Claim area | Verified evidence | Unverified or deferred | Correct interpretation |
|---|---|---|---|
| Consultant WordML XML source-shape proof | M009 fixture inventory and prior-art inventory identify `law-source/consultant/44-FZ-2026.xml` as `full-normative-act` with hash/shape provenance. | Source shape does not itself prove extracted hierarchy correctness or legal semantics. | Use as canonical full-act XML fixture anchor. |
| Consultant WordML XML parser proof | M009 `build-consultant-hierarchy-records.py` and proof package record 2185 deterministic non-authoritative hierarchy records with stable IDs and bounded prior-art comparison. | Parser completeness, legal correctness, multi-document expansion, and product extraction remain unproven. | Use M009 as the current bounded Consultant XML hierarchy baseline. |
| Consultant document-list XML | M006 relation-candidate proof over `law-source/consultant/Список документов (5).xml` preserves one candidate identity. | It is not the full normative act and must not drive full-act hierarchy assumptions. | Treat as document-list-prior-art relation evidence only. |
| Garant ODT | M001/S05 and M006 provide bounded ODT smoke/parser-record evidence and parser-direction findings. | Garant ODT parity, final hierarchy extraction, SourceBlock persistence, and product ETL remain unproven. | Keep separate from Consultant WordML XML; do not map WordML assumptions onto ODT without proof. |
| Old_project/law-parser prior art | M009 prior-art inventory tracks assets, hashes, classifications, and comparison baselines. | Prior parser JSON/JSONL outputs are not authoritative parsed legal data. | Adapt hypotheses only after deterministic current-repo checks. |
| M031/M032 lifecycle/discovery | Source lifecycle and candidate discovery commands exist with deterministic verifier boundaries. | These do not prove Consultant XML hierarchy parsing. | Useful orchestration around source work, not parser foundation. |
| M033 graph-context staging | Accepted/rejected/needs_review staging pipeline exists. | It does not prove parser extraction, legal truth, or FalkorDB runtime ingestion. | Later layer; should consume parser records only after parser path is clear. |

### Verified versus unverified parser assumptions

- Consultant WordML XML: verified source-shape proof and bounded parser proof exist through M009 for the 44-FZ tracer. This is the strongest current Consultant XML evidence.
- Garant ODT: verified smoke/parser-direction evidence exists, but it is a separate source format and does not validate Consultant WordML XML behavior.
- source-shape proof: verifies that a tracked source file exists, is well-formed or loadable enough for shape diagnostics, and has stable path/hash metadata.
- parser proof: verifies that a deterministic extractor produced typed, non-authoritative records with tests, schema checks, provenance, and explicit non-claims.
- graph/discovery proof: verifies candidate, verifier, or staging behavior; it is not parser proof unless it consumes parser records through an explicit parser-record contract.

This audit does not validate R035, does not validate R037, and does not validate R038.

The explicit recovery conclusion is: M009 is the current bounded Consultant XML hierarchy baseline.

## Guardrails for remaining S01 tasks

- No Old_project artifact is trusted implementation.
- Prior parser outputs are not authoritative parsed legal data.
- Consultant WordML XML and Garant ODT evidence must stay separate.
- Source-shape proof, parser proof, discovery proof, and staging proof must be labeled separately.
- This audit does not validate R035, does not validate R037, and does not validate R038.
- Durable audit artifacts must avoid raw legal text dumps; paths, counts, hashes, IDs, statuses, and bounded summaries are sufficient.
