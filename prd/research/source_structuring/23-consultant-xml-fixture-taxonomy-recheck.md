# M034 S02 — Consultant XML fixture taxonomy recheck

## Status

- Milestone: `M034-mjdjn9 — Consultant XML Workline Recovery Audit`
- Slice: `S02 — Consultant XML Fixture Taxonomy Recheck`
- Recheck status: `taxonomy-confirmed`
- Proof level: contract
- Primary input evidence: M009 fixture inventory, M009 Consultant parser proof, M034/S01 prior parser evidence audit
- Non-validation boundaries: this recheck does not validate R035, does not validate R037, and does not validate R038

## Purpose

This recheck confirms the current repository fixture taxonomy before the recovery audit proceeds to drift analysis and corrected roadmap planning. The goal is to prevent the workline from mixing four separate evidence roles:

1. Consultant full-act WordML XML source-shape fixture.
2. Consultant document-list WordML XML prior-art relation fixture.
3. Garant ODT parser/smoke evidence.
4. Old_project and law-parser prior-art hypotheses.

The active recovery rule is: prior decisions are reused unless new evidence explicitly supersedes them. This S02 artifact therefore starts from the M009 fixture/source-role contract and checks whether current tracked artifacts still match it.

## Prior decision recovery

Recovered prior decisions from memory and durable artifacts:

| Source | Recovered decision | Current use |
|---|---|---|
| GSD memory `MEM314` | Consultant WordML fixture taxonomy uses `full-normative-act` for `law-source/consultant/44-FZ-2026.xml` and `document-list-prior-art` for the document-list XML. | Treated as the expected taxonomy for this recheck. |
| GSD memory `MEM312` | The full-act XML is canonical source-shape evidence only and does not supersede Garant ODT fixture evidence. | Preserves source-format separation. |
| `.gsd/milestones/M009/slices/S01/S01-SUMMARY.md` | M009 S01 added the full-act fixture and kept document-list XML as prior-art relation evidence. | Confirms the source-role split is historical, not newly invented. |
| `prd/parser/source_fixture_inventory.md` | Machine-generated inventory lists both Consultant XML fixtures with distinct `source_role` values and explicit non-claims. | Used as the current durable contract. |
| `prd/parser/README.md` | Future parser slices should inspect the manifest first and should not glob `law-source/` directly. | Downstream S03/S04 should consume inventory artifacts, not raw source discovery. |
| `prd/parser/consultant_parser_proof.md` | M009 parser proof is Consultant-only for the 44-FZ tracer and keeps Garant deferred. | Confirms S02 is taxonomy proof, not parser completeness proof. |

## Current fixture taxonomy

| Fixture path | Source kind | Source role | Current role in recovery audit | Boundary |
|---|---|---|---|---|
| `law-source/consultant/44-FZ-2026.xml` | `consultant-wordml-xml` | `full-normative-act` | Canonical full-act Consultant WordML source-shape fixture and M009 parser input anchor. | Source-shape/hash and bounded M009 parser evidence only; not legal truth, not parser completeness, not multi-source readiness. |
| `law-source/consultant/Список документов (5).xml` | `consultant-wordml-xml` | `document-list-prior-art` | Prior-art relation fixture used by earlier relation-candidate/staging evidence. | Not a full normative act and must not drive full-act hierarchy assumptions. |
| `law-source/garant/44-fz.odt` | `garant-odt` | `odt-document-fixture` | Separate Garant ODT fixture retained from earlier ODT work. | Does not validate Consultant WordML assumptions; ODT parser evidence remains separate. |
| `law-source/garant/PP_60_27-01-2022.odt` | `garant-odt` | `odt-document-fixture` | Separate Garant ODT fixture retained from earlier ODT work. | Earlier stated alternate filename is a documented mismatch and must not silently reappear. |

## Duplicate and hygiene status

Current `inventory-parser-fixtures.py --check` result:

```json
{
  "status": "pass",
  "fixture_count": 4,
  "duplicate_absent": true,
  "non_authoritative": true,
  "unexpected_duplicate_paths": []
}
```

Confirmed source roles from the same check:

```json
{
  "law-source/consultant/44-FZ-2026.xml": "full-normative-act",
  "law-source/consultant/Список документов (5).xml": "document-list-prior-art",
  "law-source/garant/44-fz.odt": "odt-document-fixture",
  "law-source/garant/PP_60_27-01-2022.odt": "odt-document-fixture"
}
```

The removed root-level Consultant document-list duplicate remains absent:

- Removed path: `law-source/Список документов (5).xml`
- Canonical replacement: `law-source/consultant/Список документов (5).xml`
- Failure condition: if the removed path reappears, the inventory check must fail.

The PP filename mismatch remains visible and bounded:

- Observed/canonical path: `law-source/garant/PP_60_27-01-2022.odt`
- Stated alternate path: `law-source/garant/PP_60_27-02-2022.odt`
- Current stated path exists: `false`
- Failure condition: if the stated alternate path reappears unexpectedly, the inventory check must fail.

## Relationship to M009 parser proof

M009 remains the current bounded Consultant XML hierarchy baseline. The taxonomy contract supports that conclusion but is not itself parser proof.

Current separation:

| Evidence layer | What it proves | What it does not prove |
|---|---|---|
| Fixture inventory | Tracked source paths, source roles, hashes, shape diagnostics, duplicate absence, and non-authoritative boundaries. | Extracted hierarchy correctness, legal semantics, parser completeness, relation correctness, product readiness. |
| M009 hierarchy records | Deterministic Consultant-only hierarchy records for the canonical full-act tracer with stable IDs and bounded prior-art comparison. | Legal correctness, multi-document expansion, Garant parity, product ETL, FalkorDB loading, retrieval quality. |
| Consultant document-list relation evidence | One candidate relation path over prior-art document-list XML. | Full-act hierarchy extraction or authoritative legal relation truth. |
| Garant ODT smoke/parser evidence | Separate ODT parser-record and smoke surfaces. | Consultant WordML behavior or Consultant/Garant parity. |

## Drift risks found by this recheck

| Risk | Status | Guardrail for S03/S04 |
|---|---|---|
| Treating document-list XML as full normative-act source | Controlled by `source_role=document-list-prior-art`. | S03 must flag any roadmap or code path that uses document-list XML for full hierarchy assumptions. |
| Treating full-act XML source-shape as legal truth | Controlled by inventory and parser proof non-claims. | S04 must keep parser output non-authoritative and source-span/citation-safe proof-gated. |
| Treating Garant ODT evidence as Consultant XML evidence, or vice versa | Controlled by separate `source_kind` and M009 source-priority text. | S03 must separate WordML and ODT evidence ledgers. |
| Treating Old_project/law-parser outputs as implementation | Controlled by M034/S01 and `22-old-project-transfer-decision-list.md`. | S04 may adapt ideas, not import outputs as truth. |
| Treating M031-M033 lifecycle/discovery/staging as parser baseline | Controlled by M034/S01 evidence chain. | S03 must classify these as upper layers around parser work, not parser foundation. |

## Implications for remaining M034 slices

### For S03 — Current State and Drift Audit

S03 should use this S02 taxonomy as the source-role contract:

- `44-FZ-2026.xml` belongs to Consultant full-act parser baseline review.
- `Список документов (5).xml` belongs to prior-art relation/staging review.
- Garant ODT belongs to separate ODT evidence review.
- Old_project/law-parser belongs to prior-art transfer review.

S03 should not infer current parser gaps by globbing raw source directories. It should read `prd/parser/source_fixture_inventory.json`, M009 parser proof artifacts, M031-M033 summaries, and the two M034/S01-S02 review artifacts.

### For S04 — Corrected XML Parser Foundation Roadmap

S04 should plan from M009, not from zero:

- M009 stdlib hierarchy parser is the comparison oracle until explicitly superseded.
- `lxml` is a positive prior dependency candidate but needs equivalence/performance proof before replacement.
- `razdel` and `pymorphy3` are later parser-diagnostic/enrichment candidates, not current taxonomy dependencies.
- `semantic_rules.yaml` can inform diagnostics only; it cannot become legal truth.
- No FalkorDB ingestion, graph-vector behavior, external review completion, R035 validation, R037 validation, or R038 validation should be claimed.

## Verification evidence

### T01 command

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
- Source roles confirmed:
  - `law-source/consultant/44-FZ-2026.xml` → `full-normative-act`
  - `law-source/consultant/Список документов (5).xml` → `document-list-prior-art`
  - `law-source/garant/44-fz.odt` → `odt-document-fixture`
  - `law-source/garant/PP_60_27-01-2022.odt` → `odt-document-fixture`

### T02 command

Command:

```bash
uv run pytest tests/test_parser_fixture_inventory.py tests/test_consultant_prior_art_inventory.py -q
```

Observed result:

- Exit code: `0`
- Result: `9 passed`

### T03 command

Command:

```bash
uv run python -m py_compile scripts/inventory-parser-fixtures.py scripts/build-consultant-hierarchy-records.py
```

Observed result:

- Exit code: `0`
- Result: compile check passed with no output.

### T04 final command

Command:

```bash
uv run pytest tests/test_parser_fixture_inventory.py tests/test_consultant_prior_art_inventory.py tests/test_consultant_parser_proof.py -q
```

Observed result:

- Exit code: `0`
- Result: `14 passed`

### T04 safety scan

Command:

```bash
uv run python scripts/check-m034-s02-artifact-markers.py
```

The actual scan was run inline during the session and checked required taxonomy/non-claim markers plus forbidden secret/provider markers. The marker list is not repeated here to avoid making the artifact self-match against the forbidden strings.

Observed result:

- Exit code: `0`
- Result: `{'m034_s02_taxonomy_recheck_scan': 'pass', 'required_markers': 10, 'forbidden_violations': 0}`

## Explicit non-claims

This S02 recheck does not claim:

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

The current fixture taxonomy is consistent with M009 and M034/S01:

```text
Consultant full-act WordML XML = full-normative-act parser baseline input.
Consultant document-list WordML XML = document-list-prior-art relation evidence.
Garant ODT = separate deferred/source-format evidence.
Old_project/law-parser = prior art only, to adapt through tests.
```

S02 therefore confirms the source-role contract needed for S03 drift audit and S04 corrected roadmap planning.
