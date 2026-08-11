# EA-06 Derived registry quarantine assessment

**Assessment class:** frozen documentation/process review
**Status:** `[bounded]` process evidence; `PASS-WITH-FINDINGS`
**Disposition baseline:** `bfe2ee6b6462c137c8fdb05a5dd88491ca2678a5`
**Review date:** 2026-08-11
**Authority ceiling:** derived registry quarantine only; not product, legal or requirement validation

## 1. Scope

This assessment covers D7 quarantine of:

- `prd/architecture/architecture_items.jsonl`;
- `prd/architecture/architecture_edges.jsonl`;
- generated health, blocker and claims views;
- stale graph report labelling;
- generator and regression-test ownership of quarantine banners.

It does not accept registry content as architecture authority and does not require missing historical anchors to be invented.

## 2. Deterministic result

| Check | Result | Evidence |
|---|---|---|
| Item identity preservation | PASS | 63 item IDs retained |
| Edge identity preservation | PASS | 98 edge IDs retained |
| Era disposition | PASS | 11 era items `superseded`; remaining missing-anchor archaeology blocked |
| Edge authority removal | PASS | 29 edges `superseded`, 69 `hypothesis`, zero active edges |
| Active anchor integrity | PASS | no active/bounded/proposed row has a missing source path |
| Authority-like edge integrity | PASS | zero active `satisfies`/`validated_by`/`implements` edge |
| Quarantine tagging | PASS | 54 affected items and all 98 edges carry `d7-quarantined` |
| Generated views | PASS | generator `--check` green; banner/baseline regression test present |
| Derived registry staleness | WARN | graph verifier remains fail-closed on retired/missing anchors and absent extractor/builder |

## 3. Expected WARN

`verify-architecture-graph.py` remains red by design. The latest review observed:

```text
status=fail
items=63
edges=98
source-anchor-drift=243
graph-integrity-drift=11
freshness-drift=2
failure_count=256
```

The two freshness findings identify absent historical scripts:

- `scripts/extract-prd-architecture-items.py`;
- `scripts/build-architecture-graph.py`.

This WARN is visible and fail-closed. It is not repaired by fabricating anchors, restoring archived ACP builders, or promoting a derived row.

## 4. Independent review

Independent reviewer verdict: `PASS-WITH-FINDINGS`.

Advisories retained:

1. Keep `architecture_report.md` and graph JSON explicitly stale until a current non-ACP builder exists.
2. Preserve direct regression coverage for the D7 banner and baseline.
3. Keep prohibition wording distinguishable from active era adoption.
4. Treat restoration of a builder as separate process work, not product/lifecycle proof.

## 5. Gate disposition

- `derived-registry-quarantine`: **PASS**;
- `derived-registry-staleness`: **WARN**;
- lifecycle promotion: **none**;
- requirement validation: **none**;
- product/legal readiness: **none**.

## 6. Non-claims

- no derived item or edge becomes canonical architecture;
- no missing historical anchor is accepted as valid evidence;
- no ACP/git-lex/FalkorDB/Python-era behavior is restored;
- no runtime, parser, retrieval, citation, applicability or legal-correctness claim is validated.
