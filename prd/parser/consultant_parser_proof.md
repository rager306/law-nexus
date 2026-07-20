# Consultant Parser Proof Package

This package assembles the Consultant-only parser proof chain for the 44-ФЗ tracer. Consultant Plus is the primary active parser priority for M009. The package links the S01 fixture/prior-art inventory, S02 hierarchy records, and S03 prior-art comparison without making Garant a completion gate.

## Scope

- Package scope: Consultant 44-FZ tracer proof package only
- Source kind: `consultant-wordml-xml`
- Document id: `DOC-CONS-44-FZ`
- Completion boundary: Consultant-only; Garant is deferred separately, remains lower-priority/deferred, and no M009 success criterion requires Garant regression proof.

## Commands

- `uv run pytest tests/test_consultant_parser_proof.py -q`
- `test -s prd/parser/consultant_parser_proof.md`

## Input Artifacts and Freshness

| Artifact | Exists | Size | SHA-256 |
|---|---:|---:|---|
| `prd/parser/consultant_prior_art_inventory.json` | True | 33820 | `e781c7e483809b51e19da1888c99d6211b3a8b1498d71891d0f3b97d145cb170` |
| `prd/parser/consultant_hierarchy_records.jsonl` | True | 4497057 | `103e6e9c9006aaab930c72c4a2d894d3c2fe083848ca2ea273db966d48d27ad2` |
| `prd/parser/consultant_hierarchy_prior_art_comparison.json` | True | 90224 | `165e241b6fd31d83af0f7cdd8edb9654d3a42a7c74c9e009e9ede9e7c5c502cc` |

Freshness status: **fresh-at-generation**; stale artifact count: **0**.

The historical single-fixture proof remains separate from the corpus parity
baseline. `prd/parser/consultant_hierarchy_baseline_manifest.json` freezes both
single (2,185 records) and corpus (15,249 records) output/source hashes under
`[bounded]` M109 evidence; it does not expand this M009 proof's scope.

## Fixture Inventory

- Inventory assets: **28**
- Classification counts: `{"adapt": 13, "defer": 13, "keep": 1, "reject": 1}`
- Missing assets: `[]`
- Hash mismatches: `[]`

Canonical Consultant fixture:
- `CPA-001` — Canonical Consultant full normative-act WordML fixture
  - Path: `law-source/consultant/44-FZ-2026.xml`
  - SHA-256: `69df0b9d9e2bcce6164fc4e3c74fb9bebfff36ae6b053c68917c804be4b52a86`
  - Boundary: Keep as the canonical tracked Consultant Plus WordML source-shape fixture and hash anchor only; do not treat as parsed legal semantics or multi-source readiness.

## Hierarchy Artifacts

- Total records: **2185**
- Duplicate ids: `[]`
- Non-authoritative false count: **0**

| Level | Count | First record | Last record |
|---|---:|---|---|
| `article` | 94 | `HIER-CONS-ARTICLE-0001` | `HIER-CONS-ARTICLE-0094` |
| `chapter` | 8 | `HIER-CONS-CHAPTER-0001` | `HIER-CONS-CHAPTER-0008` |
| `clause` | 997 | `HIER-CONS-CLAUSE-0001` | `HIER-CONS-CLAUSE-0997` |
| `document` | 1 | `HIER-CONS-DOCUMENT` | `HIER-CONS-DOCUMENT` |
| `part` | 793 | `HIER-CONS-PART-0001` | `HIER-CONS-PART-0793` |
| `section` | 9 | `HIER-CONS-SECTION-0001` | `HIER-CONS-SECTION-0009` |
| `subclause` | 283 | `HIER-CONS-SUBCLAUSE-0001` | `HIER-CONS-SUBCLAUSE-0283` |

## Prior-Art Comparison

- Overall status: **needs-review**
- Diagnostics bounded: **True**
- Blocked checks: **0**
- Fatal errors: **0**
- Needs-review checks: **1**
- Status counts: `{"accepted": 4, "needs-review": 1, "pass": 6}`

| Check | Class | Status | Rationale |
|---|---|---|---|
| `COUNT-CHAPTER` | `major-count` | `pass` | Major chapter/article counts must match prior-art structure safeguards exactly. |
| `COUNT-ARTICLE` | `major-count` | `pass` | Major chapter/article counts must match prior-art structure safeguards exactly. |
| `COUNT-PART` | `granular-count` | `accepted` | Granular drift is accepted as provider-boundary evidence: Consultant hierarchy records preserve more structural markers than compact prior-art article JSONL. |
| `COUNT-CLAUSE` | `granular-count` | `accepted` | Granular drift is accepted as provider-boundary evidence: Consultant hierarchy records preserve more structural markers than compact prior-art article JSONL. |
| `COUNT-SUBCLAUSE` | `granular-count` | `accepted` | Granular drift is accepted as provider-boundary evidence: Consultant hierarchy records preserve more structural markers than compact prior-art article JSONL. |
| `COUNT-SECTION` | `granular-count` | `accepted` | Granular drift is accepted as provider-boundary evidence: Consultant hierarchy records preserve more structural markers than compact prior-art article JSONL. |
| `ORDER-CHAPTER-ARTICLE-COUNTS` | `order-and-parentage` | `pass` | Articles must map to the same chapter-count distribution even when sections are present. |
| `ORDER-FIRST-LAST-ARTICLES` | `order-and-boundary-samples` | `pass` | First/last article marker order is the bounded sample for full order drift. |
| `STRUCT-PARENTS-AND-ORDER` | `structural-rules` | `pass` | Comparable structural rules require non-orphaned hierarchy records, deterministic IDs, and monotonic source order. |
| `INVALIDITY-MARKER-SAMPLES` | `advisory-invalidity-marker` | `needs-review` | Invalidity wording is compared as advisory marker evidence only; it does not determine amendment legal effect. |
| `INPUT-VALIDATION` | `freshness-and-schema` | `pass` | Comparison fails closed on malformed hierarchy JSONL records. |

## Deferred Boundaries

- **garant**: Deferred: Garant ODT parsing is not a completion gate for this Consultant-only proof package.
- **multi_source**: Not claimed: this package does not establish multi-source parser readiness or Consultant/Garant parity.
- **graph_loading**: Not claimed: this package does not establish FalkorDB/product ETL load readiness.

## Non-Claims

- Consultant parser proof is a deterministic evidence package for the Consultant 44-FZ tracer only.
- Does not claim legal correctness or authoritative legal interpretation.
- Does not claim parser completeness beyond the recorded Consultant hierarchy artifacts.
- Does not claim product ETL, FalkorDB load readiness, or multi-source parser readiness.
- Does not claim retrieval readiness, relation correctness, or legal-answer correctness.
- Does not wire Garant ODT parsing into this proof package as a completion gate; Garant remains deferred for separate verification.

## Diagnostics Summary

The proof intentionally preserves diagnostic status instead of flattening it to pass/fail: major chapter/article counts pass, granular count drift is accepted as provider-boundary evidence, and invalidity-marker drift remains needs-review advisory evidence rather than a legal conclusion.
